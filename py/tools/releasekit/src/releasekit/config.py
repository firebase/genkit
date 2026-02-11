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

"""Configuration reader for releasekit.

Reads ``[tool.releasekit]`` from the workspace root ``pyproject.toml``
and returns a validated :class:`ReleaseConfig` dataclass.

Key Concepts (ELI5)::

    ┌─────────────────────────┬────────────────────────────────────────────┐
    │ Concept                 │ ELI5 Explanation                           │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ ReleaseConfig           │ A settings object for the release tool.   │
    │                         │ Like the control panel on a washing       │
    │                         │ machine — knobs for how to run.           │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ load_config()           │ Read pyproject.toml + validate settings.  │
    │                         │ Like reading and checking the recipe      │
    │                         │ before you start cooking.                 │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ Fuzzy key matching      │ If you typo a config key, we suggest the  │
    │                         │ closest valid key. Like "did you mean?"   │
    │                         │ in a search engine.                       │
    └─────────────────────────┴────────────────────────────────────────────┘

Validation Pipeline::

    pyproject.toml
    ┌──────────────────┐
    │ [tool.releasekit] │
    │ tag_fromat = ...  │  ← typo!
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐     ┌──────────────────────────────┐
    │ 1. Unknown key   │────→│ RK-CONFIG-INVALID-KEY:       │
    │    detection     │     │ hint: "Did you mean          │
    └────────┬─────────┘     │       'tag_format'?"         │
             │               └──────────────────────────────┘
             ▼
    ┌──────────────────┐     ┌──────────────────────────────┐
    │ 2. Type check    │────→│ RK-CONFIG-INVALID-VALUE:     │
    │    each value    │     │ Expected str, got int        │
    └────────┬─────────┘     └──────────────────────────────┘
             │
             ▼
    ┌──────────────────┐     ┌──────────────────────────────┐
    │ 3. Value check   │────→│ RK-CONFIG-INVALID-VALUE:     │
    │    (enums, etc.) │     │ publish_from must be         │
    └────────┬─────────┘     │ "local" or "ci"              │
             │
             ▼
    ┌──────────────────┐
    │ ReleaseConfig()  │  ← frozen dataclass, ready to use
    └──────────────────┘

Supported keys in ``[tool.releasekit]``::

    tag_format         = "{name}-v{version}"     # per-package tag format
    umbrella_tag       = "v{version}"            # umbrella tag format
    publish_from       = "local"                 # "local" or "ci"
    groups             = { core = ["genkit"], plugins = ["genkit-plugin-*"] }
    exclude            = ["sample-*"]            # glob patterns to exclude
    changelog          = true                    # generate CHANGELOG.md
    prerelease_mode    = "rollup"                # "rollup" or "separate"
    http_pool_size     = 10                      # httpx connection pool
    smoke_test         = true                    # run install smoke test

Usage::

    from releasekit.config import load_config

    cfg = load_config(Path('pyproject.toml'))
    print(cfg.tag_format)  # "{name}-v{version}"
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomlkit
import tomlkit.exceptions

from releasekit.errors import E, ReleaseKitError
from releasekit.logging import get_logger

logger = get_logger(__name__)

# All recognized keys in [tool.releasekit].
VALID_KEYS: frozenset[str] = frozenset({
    'changelog',
    'exclude',
    'groups',
    'http_pool_size',
    'prerelease_mode',
    'publish_from',
    'smoke_test',
    'tag_format',
    'umbrella_tag',
})

# Allowed values for enum-like config fields.
ALLOWED_PUBLISH_FROM: frozenset[str] = frozenset({'local', 'ci'})
ALLOWED_PRERELEASE_MODES: frozenset[str] = frozenset({'rollup', 'separate'})


@dataclass(frozen=True)
class ReleaseConfig:
    """Validated configuration for a releasekit run.

    All fields have sensible defaults so ``ReleaseConfig()`` is usable
    without any ``[tool.releasekit]`` section present.

    Attributes:
        tag_format: Per-package git tag format string.
            Placeholders: ``{name}``, ``{version}``.
        umbrella_tag: Umbrella git tag format string.
            Placeholder: ``{version}``.
        publish_from: Where to publish from: ``"local"`` or ``"ci"``.
        groups: Named groups of package patterns for selective release.
            Keys are group names, values are lists of glob patterns.
        exclude: Glob patterns for packages to exclude from release.
        changelog: Whether to generate CHANGELOG.md entries.
        prerelease_mode: How to handle prerelease changelogs:
            ``"rollup"`` merges into the final release,
            ``"separate"`` keeps them distinct.
        http_pool_size: Max connections for the httpx connection pool.
        smoke_test: Whether to run ``pip install --dry-run`` after publish.
        config_path: Path to the pyproject.toml that was loaded.
    """

    tag_format: str = '{name}-v{version}'
    umbrella_tag: str = 'v{version}'
    publish_from: str = 'local'
    groups: dict[str, list[str]] = field(default_factory=dict)
    exclude: list[str] = field(default_factory=list)
    changelog: bool = True
    prerelease_mode: str = 'rollup'
    http_pool_size: int = 10
    smoke_test: bool = True
    config_path: Path | None = None


def _suggest_key(unknown: str) -> str | None:
    """Return the closest valid key for a typo, or None."""
    matches = difflib.get_close_matches(unknown, VALID_KEYS, n=1, cutoff=0.6)
    return matches[0] if matches else None


def _validate_value_type(key: str, value: Any) -> None:  # noqa: ANN401 — dynamic config values
    """Raise if a config value has the wrong type."""
    expected_types: dict[str, type | tuple[type, ...]] = {
        'tag_format': str,
        'umbrella_tag': str,
        'publish_from': str,
        'groups': dict,
        'exclude': list,
        'changelog': bool,
        'prerelease_mode': str,
        'http_pool_size': int,
        'smoke_test': bool,
    }
    expected = expected_types.get(key)
    if expected is None:
        return
    if not isinstance(value, expected):
        type_name = expected.__name__ if isinstance(expected, type) else str(expected)
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"[tool.releasekit] key '{key}' must be {type_name}, got {type(value).__name__}",
            hint=f'Check the value of {key} in your pyproject.toml.',
        )


def _validate_publish_from(value: str) -> None:
    """Raise if publish_from is not a recognized value."""
    if value not in ALLOWED_PUBLISH_FROM:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"publish_from must be one of {sorted(ALLOWED_PUBLISH_FROM)}, got '{value}'",
            hint="Use 'local' for publishing from your machine, 'ci' for GitHub Actions.",
        )


def _validate_prerelease_mode(value: str) -> None:
    """Raise if prerelease_mode is not a recognized value."""
    if value not in ALLOWED_PRERELEASE_MODES:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"prerelease_mode must be one of {sorted(ALLOWED_PRERELEASE_MODES)}, got '{value}'",
            hint="Use 'rollup' to merge prerelease entries into the final release.",
        )


def _validate_groups(groups: dict[str, Any]) -> dict[str, list[str]]:  # noqa: ANN401 — dynamic config
    """Validate and normalize the groups mapping."""
    result: dict[str, list[str]] = {}
    for group_name, patterns in groups.items():
        if not isinstance(patterns, list):
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_VALUE,
                message=f"Group '{group_name}' must be a list of glob patterns, got {type(patterns).__name__}",
                hint=f'Example: groups.{group_name} = ["genkit", "genkit-plugin-*"]',
            )
        for pattern in patterns:
            if not isinstance(pattern, str):
                raise ReleaseKitError(
                    code=E.CONFIG_INVALID_VALUE,
                    message=f"Group '{group_name}' patterns must be strings, got {type(pattern).__name__}",
                )
        result[group_name] = list(patterns)
    return result


def load_config(pyproject_path: Path) -> ReleaseConfig:
    """Load and validate ``[tool.releasekit]`` from a pyproject.toml.

    If the file exists but has no ``[tool.releasekit]`` section, returns
    a :class:`ReleaseConfig` with all defaults. If the file does not
    exist, raises :class:`ReleaseKitError`.

    Args:
        pyproject_path: Path to the pyproject.toml file.

    Returns:
        A validated :class:`ReleaseConfig`.

    Raises:
        ReleaseKitError: If the file is missing or contains invalid config.
    """
    if not pyproject_path.is_file():
        raise ReleaseKitError(
            code=E.CONFIG_NOT_FOUND,
            message=f'pyproject.toml not found at {pyproject_path}',
            hint="Run 'releasekit init' from your workspace root.",
        )

    try:
        text = pyproject_path.read_text(encoding='utf-8')
    except OSError as exc:
        raise ReleaseKitError(
            code=E.CONFIG_NOT_FOUND,
            message=f'Failed to read {pyproject_path}: {exc}',
        ) from exc

    try:
        doc = tomlkit.parse(text)
    except tomlkit.exceptions.TOMLKitError as exc:
        raise ReleaseKitError(
            code=E.CONFIG_NOT_FOUND,
            message=f'Failed to parse {pyproject_path}: {exc}',
        ) from exc

    tool_section = doc.get('tool', {})
    raw: dict[str, Any] = dict(tool_section.get('releasekit', {}))  # noqa: ANN401

    if not raw:
        logger.debug('no_releasekit_config', path=str(pyproject_path))
        return ReleaseConfig(config_path=pyproject_path)

    # Check for unknown keys with fuzzy suggestions.
    for key in raw:
        if key not in VALID_KEYS:
            suggestion = _suggest_key(key)
            hint = f"Did you mean '{suggestion}'?" if suggestion else 'Check the releasekit docs for valid keys.'
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_KEY,
                message=f"Unknown key '{key}' in [tool.releasekit]",
                hint=hint,
            )

    # Validate value types.
    for key, value in raw.items():
        _validate_value_type(key, value)

    # Validate specific values.
    if 'publish_from' in raw:
        _validate_publish_from(raw['publish_from'])
    if 'prerelease_mode' in raw:
        _validate_prerelease_mode(raw['prerelease_mode'])
    if 'exclude' in raw:
        for item in raw['exclude']:
            if not isinstance(item, str):
                raise ReleaseKitError(
                    code=E.CONFIG_INVALID_VALUE,
                    message=f"'exclude' items must be strings, got {type(item).__name__}: {item!r}",
                    hint='Each exclude entry should be a glob pattern string, e.g. "sample-*".',
                )

    # Normalize groups before passing to constructor.
    config_kwargs: dict[str, Any] = dict(raw)  # noqa: ANN401 — dynamic config values
    if 'groups' in config_kwargs:
        config_kwargs['groups'] = _validate_groups(config_kwargs['groups'])

    # Let the dataclass handle defaults for any missing keys.
    return ReleaseConfig(**config_kwargs, config_path=pyproject_path)


__all__ = [
    'ALLOWED_PRERELEASE_MODES',
    'ALLOWED_PUBLISH_FROM',
    'VALID_KEYS',
    'ReleaseConfig',
    'load_config',
]
