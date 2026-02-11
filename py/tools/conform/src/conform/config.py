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

Python 3.10 ships without ``tomllib``; the ``tomli`` backport is used
as a fallback.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

from conform.paths import TOOL_DIR

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ModuleNotFoundError as exc:
        msg = "Python 3.10 requires the 'tomli' package: pip install tomli"
        raise SystemExit(msg) from exc

# Sentinel for "no CLI override".
_UNSET: int = -1


@dataclass(frozen=True)
class ConformConfig:
    """Resolved configuration for the ``conform`` tool.

    Attributes:
        concurrency: Maximum number of plugins to test in parallel.
        env: Mapping of plugin name → list of required environment variables.
        additional_model_plugins: Plugins that should have conformance specs
            but lack ``model_info.py`` (they use dynamic model registration).
    """

    concurrency: int = 4
    env: dict[str, list[str]] = field(default_factory=dict)
    additional_model_plugins: list[str] = field(default_factory=list)


def _load_pyproject(path: Path) -> dict[str, object]:
    """Read and parse a ``pyproject.toml`` file."""
    with open(path, 'rb') as fh:
        return tomllib.load(fh)  # type: ignore[return-value]


def load_config(
    *,
    concurrency_override: int = _UNSET,
    config_path: Path | None = None,
) -> ConformConfig:
    """Load configuration from TOML, applying CLI overrides.

    Args:
        concurrency_override: If positive, overrides the TOML concurrency.
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
        tool = data.get('tool')
        if isinstance(tool, dict):
            conform_section = tool.get('conform')
            if isinstance(conform_section, dict):
                raw = conform_section

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

    return ConformConfig(
        concurrency=concurrency,
        env=env,
        additional_model_plugins=additional_model_plugins,
    )
