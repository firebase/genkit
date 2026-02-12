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

"""TOML configuration loader for the ``conform`` tool.

Reads ``[tool.conform]`` from the tool's own ``pyproject.toml``
(``py/tools/conform/pyproject.toml``).  CLI flags override values loaded
from config.

**Multi-runtime support:** Each runtime (Python, JS, Go, Dart, Java,
Rust) has its own ``[tool.conform.runtimes.<name>]`` section defining
how to locate specs, plugins, and the entry command to execute.
The ``--runtime`` CLI flag selects which runtime config to use
(default: ``python``).

Python 3.10 ships without ``tomllib``; the ``tomli`` backport is used
as a fallback.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from conform.paths import PY_DIR, REPO_ROOT, TOOL_DIR

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ModuleNotFoundError as exc:
        msg = "Python 3.10 requires the 'tomli' package: pip install tomli"
        raise SystemExit(msg) from exc

# Sentinel for "no CLI override".
_UNSET: int = -1


@dataclass(frozen=True)
class RuntimeConfig:
    """Configuration for a single runtime (e.g. python, js, go).

    Attributes:
        name: Runtime identifier (e.g. ``python``, ``js``, ``go``).
        specs_dir: Absolute path to the directory containing conformance
            specs (one subdirectory per plugin with ``model-conformance.yaml``
            and a runtime-specific entry file).
        plugins_dir: Absolute path to the directory containing plugin
            source trees (used by ``check-plugin`` for model marker
            scanning).
        entry_command: Command prefix used to run a conformance entry
            point.  The entry-point path is appended as the last argument.
            Example: ``["uv", "run", "--project", "/path/to/py", "--active"]``.
        cwd: Working directory for subprocess execution.  Defaults to
            the repo root.  JS needs ``js/`` so Node module resolution
            finds the pnpm workspace packages.
        entry_filename: The conformance entry point filename.
            Defaults to ``conformance_entry.py`` for Python,
            ``conformance_entry.ts`` for JS, etc.
        model_marker: Glob pattern to identify model provider plugins.
            The ``check-plugin`` subcommand scans for files matching this
            pattern under ``plugins_dir/*/src/``. Defaults to
            ``model_info.py`` for Python.
    """

    name: str
    specs_dir: Path
    plugins_dir: Path
    entry_command: list[str]
    cwd: Path | None = None
    entry_filename: str = 'conformance_entry.py'
    model_marker: str = 'model_info.py'


@dataclass(frozen=True)
class ConformConfig:
    """Resolved configuration for the ``conform`` tool.

    Attributes:
        concurrency: Maximum number of plugins to test in parallel.
        env: Mapping of plugin name → list of required environment variables.
        additional_model_plugins: Plugins that should have conformance specs
            but lack ``model_info.py`` (they use dynamic model registration).
        runtime: The active runtime configuration.
    """

    concurrency: int = 4
    env: dict[str, list[str]] = field(default_factory=dict)
    additional_model_plugins: list[str] = field(default_factory=list)
    runtime: RuntimeConfig = field(
        default_factory=lambda: RuntimeConfig(
            name='python',
            specs_dir=PY_DIR / 'tests' / 'conform',
            plugins_dir=PY_DIR / 'plugins',
            entry_command=['uv', 'run', '--project', str(PY_DIR), '--active'],
        )
    )


def _load_pyproject(path: Path) -> dict[str, object]:
    """Read and parse a ``pyproject.toml`` file."""
    with open(path, 'rb') as fh:
        return tomllib.load(fh)


def _resolve_path(raw: str) -> Path:
    """Resolve a path that may be relative to the repo root."""
    p = Path(raw)
    if p.is_absolute():
        return p
    return REPO_ROOT / p


# Default entry filenames and model markers per runtime.
_RUNTIME_DEFAULTS: dict[str, dict[str, str]] = {
    'python': {'entry_filename': 'conformance_entry.py', 'model_marker': 'model_info.py'},
    'js': {'entry_filename': 'conformance_entry.ts', 'model_marker': 'models.ts'},
    'go': {'entry_filename': 'conformance_entry.go', 'model_marker': 'model_info.go'},
}


def _parse_runtime(
    name: str,
    raw: dict[str, object],
) -> RuntimeConfig:
    """Parse a single ``[tool.conform.runtimes.<name>]`` section."""
    specs_dir_raw = raw.get('specs-dir', '')
    plugins_dir_raw = raw.get('plugins-dir', '')
    entry_cmd_raw = raw.get('entry-command', [])
    cwd_raw = raw.get('cwd', '')

    specs_dir = _resolve_path(str(specs_dir_raw)) if specs_dir_raw else PY_DIR / 'tests' / 'conform'
    plugins_dir = _resolve_path(str(plugins_dir_raw)) if plugins_dir_raw else PY_DIR / 'plugins'
    cwd = _resolve_path(str(cwd_raw)) if cwd_raw else None

    entry_command: list[str] = []
    if isinstance(entry_cmd_raw, list):
        entry_command = [str(v) for v in entry_cmd_raw]
    else:
        entry_command = ['uv', 'run', '--project', str(PY_DIR), '--active']

    # Runtime-specific defaults, overridable via TOML.
    defaults = _RUNTIME_DEFAULTS.get(name, _RUNTIME_DEFAULTS['python'])
    entry_filename = str(raw.get('entry-filename', defaults['entry_filename']))
    model_marker = str(raw.get('model-marker', defaults['model_marker']))

    return RuntimeConfig(
        name=name,
        specs_dir=specs_dir,
        plugins_dir=plugins_dir,
        entry_command=entry_command,
        cwd=cwd,
        entry_filename=entry_filename,
        model_marker=model_marker,
    )


def _default_python_runtime() -> RuntimeConfig:
    """Return the default Python runtime configuration."""
    return RuntimeConfig(
        name='python',
        specs_dir=PY_DIR / 'tests' / 'conform',
        plugins_dir=PY_DIR / 'plugins',
        entry_command=['uv', 'run', '--project', str(PY_DIR), '--active'],
    )


def load_config(
    *,
    concurrency_override: int = _UNSET,
    runtime_name: str = 'python',
    config_path: Path | None = None,
) -> ConformConfig:
    """Load configuration from TOML, applying CLI overrides.

    Args:
        concurrency_override: If positive, overrides the TOML concurrency.
        runtime_name: Which runtime section to load (default: ``python``).
        config_path: Explicit path to a ``pyproject.toml``.  Defaults to the
            tool's own ``pyproject.toml`` at ``py/tools/conform/pyproject.toml``.

    Returns:
        Fully resolved :class:`ConformConfig`.
    """
    if config_path is None:
        config_path = TOOL_DIR / 'pyproject.toml'

    raw: dict[str, object] = {}
    if config_path.is_file():
        data = _load_pyproject(config_path)
        tool: object = data.get('tool')
        if isinstance(tool, dict):
            conform_section: object = tool.get('conform')  # type: ignore[call-overload]
            if isinstance(conform_section, dict):
                raw = {str(k): v for k, v in conform_section.items()}

    # Parse concurrency.
    toml_concurrency = raw.get('concurrency', 4)
    if not isinstance(toml_concurrency, int) or toml_concurrency < 1:
        toml_concurrency = 4
    concurrency = concurrency_override if concurrency_override > 0 else toml_concurrency

    # Parse env vars.
    env_raw = raw.get('env', {})
    env: dict[str, list[str]] = {}
    if isinstance(env_raw, dict):
        for plugin, vars_list in env_raw.items():
            if isinstance(plugin, str) and isinstance(vars_list, list):
                env[plugin] = [v for v in vars_list if isinstance(v, str)]

    # Parse additional model plugins.
    amp_raw = raw.get('additional-model-plugins', [])
    additional_model_plugins: list[str] = []
    if isinstance(amp_raw, list):
        additional_model_plugins = [v for v in amp_raw if isinstance(v, str)]

    # Parse runtime config.
    runtimes_raw = raw.get('runtimes', {})
    runtime: RuntimeConfig = _default_python_runtime()

    if isinstance(runtimes_raw, dict):
        rt_section: object = runtimes_raw.get(runtime_name)  # type: ignore[union-attr]
        if isinstance(rt_section, dict):
            # Narrow to dict[str, object] for _parse_runtime.
            rt_dict: dict[str, object] = {str(k): v for k, v in rt_section.items()}
            runtime = _parse_runtime(runtime_name, rt_dict)

    return ConformConfig(
        concurrency=concurrency,
        env=env,
        additional_model_plugins=additional_model_plugins,
        runtime=runtime,
    )


def load_all_runtime_names(
    config_path: Path | None = None,
) -> list[str]:
    """Return the names of all configured runtimes.

    Reads ``[tool.conform.runtimes.*]`` sections from the TOML config.
    Falls back to ``['python']`` if no runtimes are configured.
    """
    if config_path is None:
        config_path = TOOL_DIR / 'pyproject.toml'

    if not config_path.is_file():
        return ['python']

    data = _load_pyproject(config_path)
    tool: object = data.get('tool')
    if not isinstance(tool, dict):
        return ['python']

    conform_section: object = tool.get('conform')  # type: ignore[call-overload]
    if not isinstance(conform_section, dict):
        return ['python']

    runtimes_raw: object = conform_section.get('runtimes')
    if not isinstance(runtimes_raw, dict):
        return ['python']

    names = [str(k) for k in runtimes_raw]
    return names if names else ['python']
