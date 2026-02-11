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

"""Async parallel test runner for ``conform run``.

Uses ``asyncio.create_subprocess_exec`` to run ``genkit dev:test-model``
for each plugin, bounded by an ``asyncio.Semaphore`` for concurrency
control.  Results are collected as they arrive via
``asyncio.as_completed``.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from rich.live import Live

from conform.config import ConformConfig
from conform.display import (
    Status,
    build_progress_table,
    build_summary_table,
    console,
    print_summary_footer,
    rust_error,
    rust_warning,
)
from conform.paths import PY_DIR
from conform.plugins import check_env, entry_point, spec_file


@dataclass
class PluginResult:
    """Result of running conformance tests for a single plugin."""

    plugin: str
    status: Status = Status.PENDING
    elapsed_s: float = 0.0
    stdout: str = ''
    stderr: str = ''
    return_code: int = -1
    error_message: str = ''
    missing_env_vars: list[str] = field(default_factory=list)


async def _run_single_plugin(
    plugin: str,
    result: PluginResult,
    sem: asyncio.Semaphore,
    config: ConformConfig,
) -> PluginResult:
    """Run conformance tests for a single plugin.

    Pre-flight checks (missing files, env vars) are performed before
    acquiring the semaphore so they resolve instantly.
    """
    spec = spec_file(plugin)
    entry = entry_point(plugin)

    # Pre-flight: spec file.
    if not spec.exists():
        result.status = Status.ERROR
        result.error_message = f'spec not found: {spec}'
        return result

    # Pre-flight: entry point.
    if not entry.exists():
        result.status = Status.ERROR
        result.error_message = f'entry point not found: {entry}'
        return result

    # Pre-flight: environment variables.
    missing = check_env(plugin, config)
    if missing:
        result.status = Status.SKIPPED
        result.missing_env_vars = missing
        result.error_message = f'missing env: {", ".join(missing)}'
        return result

    async with sem:
        result.status = Status.RUNNING
        start = time.monotonic()

        try:
            proc = await asyncio.create_subprocess_exec(
                'genkit',
                'dev:test-model',
                '--from-file',
                str(spec),
                '--',
                'uv',
                'run',
                '--project',
                str(PY_DIR),
                '--active',
                str(entry),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_bytes, stderr_bytes = await proc.communicate()
            result.elapsed_s = time.monotonic() - start
            result.stdout = stdout_bytes.decode(errors='replace')
            result.stderr = stderr_bytes.decode(errors='replace')
            result.return_code = proc.returncode if proc.returncode is not None else -1

            if result.return_code == 0:
                result.status = Status.PASSED
            else:
                result.status = Status.FAILED
                # Extract last non-empty line as error summary.
                lines = [ln.strip() for ln in (result.stdout + result.stderr).splitlines() if ln.strip()]
                result.error_message = lines[-1] if lines else f'exit code {result.return_code}'

        except FileNotFoundError:
            result.elapsed_s = time.monotonic() - start
            result.status = Status.ERROR
            result.error_message = 'genkit CLI not found in PATH'
        except OSError as exc:
            result.elapsed_s = time.monotonic() - start
            result.status = Status.ERROR
            result.error_message = str(exc)

    return result


async def run_all(
    plugins: list[str],
    config: ConformConfig,
    *,
    verbose: bool = False,
) -> dict[str, PluginResult]:
    """Run conformance tests for all *plugins* with bounded concurrency.

    Args:
        plugins: List of plugin names to test.
        config: Resolved tool configuration.
        verbose: If ``True``, print full stdout/stderr for failures.

    Returns:
        Ordered dict mapping plugin names to their results.
    """
    sem = asyncio.Semaphore(config.concurrency)

    results: dict[str, PluginResult] = {p: PluginResult(plugin=p) for p in plugins}

    tasks: list[asyncio.Task[PluginResult]] = [
        asyncio.create_task(
            _run_single_plugin(plugin, results[plugin], sem, config),
            name=plugin,
        )
        for plugin in plugins
    ]

    # Live-update the table as results come in.
    with Live(
        build_progress_table(results),
        console=console,
        refresh_per_second=4,
        transient=True,
    ) as live:
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results[result.plugin] = result
            live.update(build_progress_table(results))

    # Print the final summary table with emojis.
    console.print()
    console.print(build_summary_table(results))
    print_summary_footer(results)

    # Verbose output for failures.
    if verbose:
        for plugin, result in results.items():
            if result.status in (Status.FAILED, Status.ERROR):
                console.print()
                console.rule(f'[bold red]{plugin}[/bold red] — output', style='red')
                if result.stdout:
                    console.print(result.stdout.rstrip())
                if result.stderr:
                    console.print(result.stderr.rstrip(), style='dim')

    # Rust-style error summaries.
    for plugin, result in results.items():
        if result.status == Status.SKIPPED:
            rust_warning(
                'W0001',
                f'skipping `{plugin}`: missing environment variables',
                note=', '.join(result.missing_env_vars),
            )
        elif result.status == Status.ERROR:
            rust_error(
                'E0002',
                f'internal error running `{plugin}`',
                note=result.error_message,
                hint='check that `genkit` CLI is installed and on PATH',
            )
        elif result.status == Status.FAILED:
            rust_error(
                'E0003',
                f'conformance tests failed for `{plugin}`',
                note=result.error_message,
                hint=f'run with --verbose or test individually: conform run {plugin} -v',
            )

    return results
