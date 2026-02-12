# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""Native model conformance test runner.

Replaces ``genkit dev:test-model`` entirely — no genkit CLI dependency.

Two execution modes (same validator/reporting logic):

1. **In-process (Python runtime):** Imports the conformance entry point
   module, which creates a ``Genkit`` instance and registers model actions.
   Tests are run directly via ``action.arun_raw()`` — no subprocess, no HTTP.

2. **Subprocess + async HTTP (JS, Go, other runtimes):** Starts the entry
   point as a subprocess (e.g. ``node entry.ts``), then communicates with
   the reflection server via ``ReflectionClient`` (httpx).

Canonical JS source (keep in sync):
    genkit-tools/cli/src/commands/dev-test-model.ts
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, cast

import yaml

from conform.config import ConformConfig
from conform.display import console
from conform.paths import REPO_ROOT
from conform.plugins import entry_point, spec_file
from conform.reflection import ReflectionClient
from conform.test_cases import TEST_CASES
from conform.validators import ValidationError, get_validator
from genkit.codec import dump_dict

logger = logging.getLogger(__name__)

# How long to wait for the runtime file to appear (seconds).
_RUNTIME_FILE_TIMEOUT = 30.0
_RUNTIME_FILE_POLL = 0.5


@dataclass
class TestResult:
    """Result of a single test case."""

    name: str
    passed: bool = False
    error: str = ''
    elapsed_s: float = 0.0


@dataclass
class SuiteResult:
    """Result of testing a single model."""

    model: str
    tests: list[TestResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        """Count of passed tests."""
        return sum(1 for t in self.tests if t.passed)

    @property
    def failed(self) -> int:
        """Count of failed tests."""
        return sum(1 for t in self.tests if not t.passed)


@dataclass
class RunResult:
    """Aggregate result of all test suites."""

    suites: list[SuiteResult] = field(default_factory=list)

    @property
    def total_passed(self) -> int:
        """Total passed tests across all suites."""
        return sum(s.passed for s in self.suites)

    @property
    def total_failed(self) -> int:
        """Total failed tests across all suites."""
        return sum(s.failed for s in self.suites)


class ActionRunner(Protocol):
    """Protocol for running model actions.

    Two implementations:
    - ``InProcessRunner``: Python-only, calls actions via the genkit SDK.
    - ``ReflectionRunner``: Any runtime, talks to reflection server via HTTP.
    """

    async def run_action(
        self,
        key: str,
        input_data: dict[str, Any],
        *,
        stream: bool = False,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Run a model action and return (response, chunks)."""
        ...

    async def close(self) -> None:
        """Clean up resources."""
        ...


class InProcessRunner:
    """Run model actions in-process by importing the entry point module.

    The entry point (e.g. ``conformance_entry.py``) creates a ``Genkit``
    instance at module level, registering all model actions.  We import
    it, grab the ``ai`` instance, and call actions via the registry.
    """

    def __init__(self, entry_path: Path) -> None:
        """Initialize with the path to the conformance entry point."""
        self._entry_path = entry_path
        self._ai: Any = None

    async def _load(self) -> None:
        """Import the entry point module and extract the Genkit instance."""
        if self._ai is not None:
            return

        # Import the module by file path without executing __main__ block.
        spec = importlib.util.spec_from_file_location(
            '_conform_entry',
            str(self._entry_path),
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f'Cannot load entry point: {self._entry_path}')

        module = importlib.util.module_from_spec(spec)

        # Ensure the entry point's directory is on sys.path so relative
        # imports work (e.g. if the entry point imports sibling modules).
        entry_dir = str(self._entry_path.parent)
        if entry_dir not in sys.path:
            sys.path.insert(0, entry_dir)

        spec.loader.exec_module(module)

        # Find the Genkit instance — by convention it's named `ai`.
        ai = getattr(module, 'ai', None)
        if ai is None:
            raise RuntimeError(
                f'Entry point {self._entry_path} does not expose an `ai` (Genkit) instance at module level.'
            )
        self._ai = ai
        console.print('[dim]Loaded entry point in-process.[/dim]')

    async def run_action(
        self,
        key: str,
        input_data: dict[str, Any],
        *,
        stream: bool = False,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Run a model action via the Genkit registry in-process."""
        await self._load()
        registry = self._ai.registry

        action = await registry.resolve_action_by_key(key)
        if action is None:
            raise RuntimeError(f'Action not found: {key}')

        chunks: list[dict[str, Any]] = []

        def on_chunk(chunk: Any) -> None:  # noqa: ANN401
            chunks.append(cast(dict[str, Any], dump_dict(chunk)))

        output = await action.arun_raw(
            raw_input=input_data,
            **(dict(on_chunk=on_chunk) if stream else {}),
        )
        response = cast(dict[str, Any], dump_dict(output.response))

        return response, chunks

    async def close(self) -> None:
        """No resources to clean up for in-process runner."""


class ReflectionRunner:
    """Run model actions via a subprocess reflection server.

    Starts the entry point subprocess, discovers the reflection server
    URL from the runtime file, and communicates via async HTTP.
    """

    def __init__(
        self,
        entry_cmd: list[str],
        cwd: str,
        required_keys: set[str],
    ) -> None:
        """Initialize with the entry command, working directory, and required keys."""
        self._entry_cmd = entry_cmd
        self._cwd = cwd
        self._required_keys = required_keys
        self._proc: asyncio.subprocess.Process | None = None
        self._client: ReflectionClient | None = None

    async def start(self) -> None:
        """Start the subprocess and wait for the reflection server."""
        project_root = REPO_ROOT

        # Clean up stale runtime files.
        runtimes_dir = project_root / '.genkit' / 'runtimes'
        if runtimes_dir.exists():
            for f in runtimes_dir.iterdir():
                if f.is_file():
                    try:
                        f.unlink()
                    except OSError:
                        pass

        env = {**os.environ, 'GENKIT_ENV': 'dev'}
        console.print(f'[dim]Starting entry point: {" ".join(self._entry_cmd)}[/dim]')

        self._proc = await asyncio.create_subprocess_exec(
            *self._entry_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._cwd,
            env=env,
        )

        # Discover the reflection server URL.
        url = await _find_runtime_url(project_root)
        if not url:
            raise RuntimeError('Runtime file not found after 30s.')

        self._client = ReflectionClient(url)

        if not await self._client.wait_for_health():
            raise RuntimeError('Reflection server not healthy after 30s.')

        if not await self._client.wait_for_actions(self._required_keys):
            console.print('[yellow]Warning:[/yellow] Not all model actions registered. Proceeding anyway.')

    async def run_action(
        self,
        key: str,
        input_data: dict[str, Any],
        *,
        stream: bool = False,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Run a model action via the reflection server."""
        if self._client is None:
            raise RuntimeError('ReflectionRunner not started. Call start() first.')
        return await self._client.run_action(key, input_data, stream=stream)

    async def close(self) -> None:
        """Stop the subprocess and close the HTTP client."""
        if self._client:
            await self._client.close()
        if self._proc and self._proc.returncode is None:
            self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._proc.kill()
                await self._proc.wait()


def _load_spec(spec_path: Path) -> list[dict[str, Any]]:
    """Load and parse a model-conformance.yaml file."""
    content = spec_path.read_text(encoding='utf-8')
    parsed = yaml.safe_load(content)
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        return [parsed]
    raise ValueError(f'Unexpected spec format in {spec_path}')


def _model_to_action_key(model: str) -> str:
    """Convert a model name to an action key."""
    return model if model.startswith('/') else f'/model/{model}'


async def _find_runtime_url(project_root: Path) -> str | None:
    """Poll for a runtime file and return the reflection server URL."""
    runtimes_dir = project_root / '.genkit' / 'runtimes'
    deadline = time.monotonic() + _RUNTIME_FILE_TIMEOUT

    while time.monotonic() < deadline:
        if runtimes_dir.exists():
            for f in sorted(runtimes_dir.iterdir(), reverse=True):
                if f.is_file():
                    try:
                        data = json.loads(f.read_text(encoding='utf-8'))
                        url = data.get('reflectionServerUrl')
                        if url:
                            logger.info('Found runtime at %s', url)
                            return url
                    except (json.JSONDecodeError, OSError):
                        pass
        await asyncio.sleep(_RUNTIME_FILE_POLL)

    return None


async def _run_single_test(
    runner: ActionRunner,
    model: str,
    test_case: dict[str, Any],
) -> TestResult:
    """Execute a single test case."""
    name = test_case.get('name', 'Unnamed Test')
    result = TestResult(name=name)
    start = time.monotonic()

    try:
        action_key = _model_to_action_key(model)
        should_stream = bool(test_case.get('stream'))
        input_data = test_case['input']

        response, chunks = await runner.run_action(
            action_key,
            input_data,
            stream=should_stream,
        )

        if should_stream and not chunks:
            raise ValidationError('Streaming requested but no chunks received.')

        # Run all validators.
        for v_spec in test_case.get('validators', []):
            parts = v_spec.split(':', 1)
            v_name = parts[0]
            v_arg = parts[1] if len(parts) > 1 else None
            validator = get_validator(v_name)
            validator(response, v_arg, chunks)

        result.passed = True
        console.print(f'  [green]✅ Passed:[/green] {name}')

    except ValidationError as exc:
        result.error = str(exc)
        console.print(f'  [red]❌ Failed:[/red] {name} — {exc}')
    except Exception as exc:
        result.error = str(exc)
        console.print(f'  [red]❌ Failed:[/red] {name} — {exc}')

    result.elapsed_s = time.monotonic() - start
    return result


async def _run_suite(
    runner: ActionRunner,
    suite: dict[str, Any],
    default_supports: list[str],
) -> SuiteResult:
    """Run all tests for a single model suite."""
    model = suite['model']
    supports = suite.get('supports') or ([] if suite.get('tests') else default_supports)

    console.print(f'\n[bold cyan]Testing model:[/bold cyan] {model}')

    result = SuiteResult(model=model)

    # Built-in conformance tests from supports list.
    for capability in supports:
        test_case = TEST_CASES.get(capability)
        if test_case:
            tr = await _run_single_test(runner, model, test_case)
            result.tests.append(tr)
        else:
            console.print(f'  [yellow]⚠ Unknown capability:[/yellow] {capability}')

    # Custom tests defined in the spec.
    for custom in suite.get('tests', []):
        test_case = {
            'name': custom.get('name', 'Custom Test'),
            'input': custom['input'],
            'validators': custom.get('validators', []),
            'stream': custom.get('stream', False),
        }
        tr = await _run_single_test(runner, model, test_case)
        result.tests.append(tr)

    return result


async def run_test_model(
    plugin: str,
    config: ConformConfig,
    *,
    default_supports: list[str] | None = None,
) -> RunResult:
    """Run model conformance tests for a plugin.

    For the Python runtime, tests run in-process (no subprocess, no HTTP).
    For other runtimes, starts the entry point subprocess and communicates
    via async HTTP with the reflection server.

    Args:
        plugin: Plugin name (e.g. ``google-genai``).
        config: Conform configuration.
        default_supports: Default capabilities to test if not specified
            in the suite.

    Returns:
        Aggregate test results.
    """
    if default_supports is None:
        default_supports = [
            'tool-request',
            'structured-output',
            'multiturn',
            'system-role',
            'input-image-base64',
            'input-image-url',
            'streaming-multiturn',
            'streaming-tool-request',
            'streaming-structured-output',
        ]

    spec = spec_file(plugin, config)
    entry = entry_point(plugin, config)

    if not spec.exists():
        console.print(f'[red]Error:[/red] Spec not found: {spec}')
        return RunResult()
    if not entry.exists():
        console.print(f'[red]Error:[/red] Entry point not found: {entry}')
        return RunResult()

    # Load test suites from spec.
    suites = _load_spec(spec)
    if not suites:
        console.print('[yellow]No test suites found in spec.[/yellow]')
        return RunResult()

    # Compute required action keys for readiness check.
    required_keys = {_model_to_action_key(s['model']) for s in suites if s.get('model')}

    # Choose runner based on runtime.
    runtime = config.runtime
    is_python = runtime.name == 'python'

    runner: ActionRunner

    if is_python:
        console.print('[dim]Using in-process runner (Python).[/dim]')
        runner = InProcessRunner(entry)
    else:
        entry_cmd = list(runtime.entry_command) + [str(entry)]
        cwd = str(runtime.cwd) if runtime.cwd else str(REPO_ROOT)
        runner = ReflectionRunner(entry_cmd, cwd, required_keys)
        await runner.start()

    run_result = RunResult()

    try:
        console.print(f'[bold green]All {len(required_keys)} model actions ready. Starting tests.[/bold green]')

        # Run test suites sequentially (each suite is one model).
        for suite in suites:
            if not suite.get('model'):
                console.print('[red]Error:[/red] Model name required in test suite.')
                continue
            sr = await _run_suite(runner, suite, default_supports)
            run_result.suites.append(sr)

        # Summary.
        console.print()
        console.print('[dim]' + '—' * 50 + '[/dim]')
        passed = run_result.total_passed
        failed = run_result.total_failed
        if failed > 0:
            console.print(f'[bold]Tests Completed:[/bold] [green]{passed} Passed[/green], [red]{failed} Failed[/red]')
        else:
            console.print(f'[bold green]Tests Completed: {passed} Passed, 0 Failed[/bold green]')

    finally:
        await runner.close()

    return run_result
