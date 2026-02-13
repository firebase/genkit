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

Reads ``releasekit.toml`` from the workspace root and returns a validated
:class:`ReleaseConfig` dataclass. The config file uses flat top-level keys
(no ``[tool.releasekit]`` nesting) so it works for any ecosystem — Python,
JS, Go, etc.

Key Concepts (ELI5)::

    ┌─────────────────────────┬────────────────────────────────────────────┐
    │ Concept                 │ ELI5 Explanation                           │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ ReleaseConfig           │ A settings object for the release tool.   │
    │                         │ Like the control panel on a washing       │
    │                         │ machine — knobs for how to run.           │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ load_config()           │ Read releasekit.toml + validate settings. │
    │                         │ Like reading and checking the recipe      │
    │                         │ before you start cooking.                 │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ Fuzzy key matching      │ If you typo a config key, we suggest the  │
    │                         │ closest valid key. Like "did you mean?"   │
    │                         │ in a search engine.                       │
    └─────────────────────────┴────────────────────────────────────────────┘

Validation Pipeline::

    releasekit.toml
    ┌──────────────────┐
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

Supported keys in ``releasekit.toml``::

    tag_format         = "{name}-v{version}"     # per-package tag format
    umbrella_tag       = "v{version}"            # umbrella tag format
    publish_from       = "local"                 # "local" or "ci"
    groups             = { core = ["genkit"], plugins = ["genkit-plugin-*"] }
    exclude            = ["sample-*"]            # glob patterns to exclude
    exclude_publish    = ["genkit-plugin-xai"]     # discovered + bumped but not published
    exclude_bump       = ["group:samples"]         # discovered + checked but not bumped
    changelog          = true                    # generate CHANGELOG.md
    prerelease_mode    = "rollup"                # "rollup" or "separate"
    http_pool_size     = 10                      # httpx connection pool
    smoke_test         = true                    # run install smoke test

Usage::

    from releasekit.config import load_config

    cfg = load_config(Path('/path/to/workspace'))
    print(cfg.tag_format)  # "{name}-v{version}"
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomlkit
import tomlkit.exceptions

from releasekit.errors import E, ReleaseKitError
from releasekit.logging import get_logger

logger = get_logger(__name__)

# The config file name at the workspace root.
CONFIG_FILENAME = 'releasekit.toml'

# Regex for valid workspace labels: lowercase letter followed by lowercase
# letters, digits, or hyphens.
_LABEL_RE = re.compile(r'[a-z][a-z0-9-]*')

# All recognized top-level keys in releasekit.toml.
VALID_KEYS: frozenset[str] = frozenset({
    'default_branch',
    'forge',
    'http_pool_size',
    'pr_title_template',
    'publish_from',
    'repo_name',
    'repo_owner',
    'workspace',
})

# Recognized keys inside each [workspace.<label>] section.
VALID_WORKSPACE_KEYS: frozenset[str] = frozenset({
    'auto_merge',
    'bootstrap_sha',
    'changelog',
    'core_package',
    'dist_tag',
    'ecosystem',
    'exclude',
    'exclude_bump',
    'exclude_publish',
    'extra_files',
    'groups',
    'library_dirs',
    'major_on_zero',
    'max_commits',
    'namespace_dirs',
    'plugin_dirs',
    'plugin_prefix',
    'prerelease_mode',
    'propagate_bumps',
    'provenance',
    'publish_branch',
    'root',
    'secondary_tag_format',
    'smoke_test',
    'synchronize',
    'tag_format',
    'tool',
    'umbrella_tag',
})

# Allowed ecosystem values for the ``ecosystem`` field.
ALLOWED_ECOSYSTEMS: frozenset[str] = frozenset({
    'dart',
    'go',
    'js',
    'jvm',
    'python',
    'rust',
})

# Default tool for each ecosystem (used when ``tool`` is not specified).
DEFAULT_TOOLS: dict[str, str] = {
    'dart': 'pub',
    'go': 'go',
    'js': 'pnpm',
    'jvm': 'gradle',
    'python': 'uv',
    'rust': 'cargo',
}

# Allowed values for enum-like config fields.
ALLOWED_PUBLISH_FROM: frozenset[str] = frozenset({'local', 'ci'})
ALLOWED_FORGES: frozenset[str] = frozenset({'github', 'gitlab', 'bitbucket', 'none'})
ALLOWED_PRERELEASE_MODES: frozenset[str] = frozenset({'rollup', 'separate'})


@dataclass(frozen=True)
class WorkspaceConfig:
    """Per-workspace configuration for a single release unit.

    Each ``[workspace.<label>]`` section in ``releasekit.toml`` produces
    one instance. The ``label`` is a user-chosen name for the workspace
    (e.g. ``"py"``, ``"js"``, ``"dotprompt-rust"``).

    Attributes:
        label: User-chosen workspace name from the TOML section key.
        ecosystem: Ecosystem identifier (``"python"``, ``"js"``,
            ``"go"``, ``"rust"``, ``"java"``, ``"dart"``).
        tool: Build/package-manager tool (``"uv"``, ``"pnpm"``,
            ``"cargo"``, ``"bazel"``, etc.). Defaults per ecosystem.
        root: Relative path from the monorepo root to the workspace
            root directory (e.g. ``"py"`` or ``"."`` for root-level).
        tag_format: Per-package git tag format string.
            Placeholders: ``{name}``, ``{version}``.
        umbrella_tag: Umbrella git tag format string.
            Placeholder: ``{version}``.
        groups: Named groups of package patterns for selective release.
        exclude: Glob patterns for packages to exclude from discovery.
        exclude_publish: Glob patterns (or ``group:<name>`` refs) for
            packages to skip during publish.
        exclude_bump: Glob patterns (or ``group:<name>`` refs) for
            packages to skip during version bumps.
        changelog: Whether to generate CHANGELOG.md entries.
        prerelease_mode: ``"rollup"`` or ``"separate"``.
        smoke_test: Whether to run install smoke test after publish.
        propagate_bumps: If ``True`` (default), bumping a library
            triggers transitive PATCH bumps in all its dependents.
            Set to ``False`` to release libraries independently
            without cascading bumps to consuming packages.
        synchronize: If ``True``, all packages share the same version.
        major_on_zero: If ``True``, breaking changes on ``0.x`` produce
            MAJOR bumps.
        core_package: Name of the core package for version checks.
        plugin_prefix: Expected prefix for plugin package names.
        namespace_dirs: Namespace directories requiring PEP 420 checks.
        library_dirs: Parent dirs whose children need ``py.typed``.
        plugin_dirs: Parent dirs whose children follow naming conventions.
        extra_files: Extra file paths with version strings to bump.
        dist_tag: npm dist-tag for ``pnpm publish --tag`` (e.g.
            ``"latest"``, ``"next"``). ``None`` means use the
            registry default (``latest``). Ignored for Python.
        publish_branch: Allow publishing from a non-default branch.
            Maps to ``pnpm publish --publish-branch``. ``None`` means
            use the default (``main``/``master``). Ignored for Python.
        provenance: Generate npm provenance attestation via
            ``pnpm publish --provenance``. Ignored for Python.
    """

    label: str = ''
    ecosystem: str = ''
    tool: str = ''
    root: str = '.'
    tag_format: str = '{name}-v{version}'
    secondary_tag_format: str = ''
    umbrella_tag: str = 'v{version}'
    groups: dict[str, list[str]] = field(default_factory=dict)
    exclude: list[str] = field(default_factory=list)
    exclude_publish: list[str] = field(default_factory=list)
    exclude_bump: list[str] = field(default_factory=list)
    changelog: bool = True
    prerelease_mode: str = 'rollup'
    smoke_test: bool = True
    propagate_bumps: bool = True
    synchronize: bool = False
    major_on_zero: bool = False
    core_package: str = ''
    plugin_prefix: str = ''
    namespace_dirs: list[str] = field(default_factory=list)
    library_dirs: list[str] = field(default_factory=list)
    plugin_dirs: list[str] = field(default_factory=list)
    extra_files: list[str] = field(default_factory=list)
    max_commits: int = 0
    bootstrap_sha: str = ''
    auto_merge: bool = False
    dist_tag: str = ''
    publish_branch: str = ''
    provenance: bool = False


@dataclass(frozen=True)
class ReleaseConfig:
    """Validated configuration for a releasekit run.

    Global settings live at the top level. Per-workspace settings
    live under ``[workspace.<label>]`` sections and are stored in
    the :attr:`workspaces` dict keyed by user-chosen label.

    Attributes:
        forge: Code forge platform: ``"github"``, ``"gitlab"``,
            ``"bitbucket"``, or ``"none"``.
        repo_owner: Repository owner or organization.
        repo_name: Repository name.
        default_branch: Override the default branch name.
        publish_from: ``"local"`` or ``"ci"``.
        http_pool_size: Max connections for the httpx connection pool.
        pr_title_template: Template for the Release PR title.
        workspaces: Per-workspace configs keyed by label
            (e.g. ``{"py": WorkspaceConfig(...), "js": ...}``).
        config_path: Path to the releasekit.toml that was loaded.
    """

    forge: str = 'github'
    repo_owner: str = ''
    repo_name: str = ''
    default_branch: str = ''
    publish_from: str = 'local'
    http_pool_size: int = 10
    pr_title_template: str = 'chore(release): v{version}'
    workspaces: dict[str, WorkspaceConfig] = field(default_factory=dict)
    config_path: Path | None = None


def _suggest_key(unknown: str) -> str | None:
    """Return the closest valid key for a typo, or None."""
    matches = difflib.get_close_matches(unknown, VALID_KEYS, n=1, cutoff=0.6)
    return matches[0] if matches else None


_GLOBAL_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    'publish_from': str,
    'http_pool_size': int,
    'forge': str,
    'repo_owner': str,
    'repo_name': str,
    'default_branch': str,
    'pr_title_template': str,
}

_WORKSPACE_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    'ecosystem': str,
    'tool': str,
    'root': str,
    'tag_format': str,
    'umbrella_tag': str,
    'groups': dict,
    'exclude': list,
    'exclude_bump': list,
    'exclude_publish': list,
    'changelog': bool,
    'prerelease_mode': str,
    'smoke_test': bool,
    'propagate_bumps': bool,
    'synchronize': bool,
    'major_on_zero': bool,
    'core_package': str,
    'plugin_prefix': str,
    'namespace_dirs': list,
    'library_dirs': list,
    'plugin_dirs': list,
    'auto_merge': bool,
    'bootstrap_sha': str,
    'secondary_tag_format': str,
    'dist_tag': str,
    'extra_files': list,
    'max_commits': int,
    'provenance': bool,
    'publish_branch': str,
}


def _validate_value_type(
    key: str,
    value: Any,  # noqa: ANN401 — dynamic config values
    type_map: dict[str, type | tuple[type, ...]],
    *,
    context: str = 'releasekit.toml',
) -> None:
    """Raise if a config value has the wrong type."""
    expected = type_map.get(key)
    if expected is None:
        return
    if not isinstance(value, expected):
        type_name = expected.__name__ if isinstance(expected, type) else str(expected)
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"'{key}' must be {type_name}, got {type(value).__name__}",
            hint=f'Check the value of {key} in {context}.',
        )


def _validate_forge(value: str) -> None:
    """Raise if forge is not a recognized value."""
    if value not in ALLOWED_FORGES:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"forge must be one of {sorted(ALLOWED_FORGES)}, got '{value}'",
            hint="Use 'github', 'gitlab', 'bitbucket', or 'none'.",
        )


def _validate_publish_from(value: str) -> None:
    """Raise if publish_from is not a recognized value."""
    if value not in ALLOWED_PUBLISH_FROM:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"publish_from must be one of {sorted(ALLOWED_PUBLISH_FROM)}, got '{value}'",
            hint="Use 'local' for publishing from your machine, 'ci' for CI pipelines.",
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


def _validate_string_list(key: str, items: list[object], context: str) -> None:
    """Raise if any item in a list is not a string."""
    for item in items:
        if not isinstance(item, str):
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_VALUE,
                message=f"'{key}' items must be strings, got {type(item).__name__}: {item!r}",
                hint=f'Each {key} entry should be a glob pattern string in {context}.',
            )


def _validate_workspace_label(label: str) -> None:
    """Raise if a workspace label contains invalid characters."""
    if not _LABEL_RE.fullmatch(label):
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_KEY,
            message=f"Workspace label '{label}' is invalid",
            hint='Labels must start with a lowercase letter and contain only lowercase letters, digits, and hyphens.',
        )


def _parse_workspace_section(
    label: str,
    raw: dict[str, Any],  # noqa: ANN401
) -> WorkspaceConfig:
    """Parse and validate a single ``[workspace.<label>]`` section."""
    context = f'[workspace.{label}]'

    _validate_workspace_label(label)

    for key in raw:
        if key not in VALID_WORKSPACE_KEYS:
            suggestion = difflib.get_close_matches(key, VALID_WORKSPACE_KEYS, n=1, cutoff=0.6)
            hint = f"Did you mean '{suggestion[0]}'?" if suggestion else f'Check valid keys for {context}.'
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_KEY,
                message=f"Unknown key '{key}' in {context}",
                hint=hint,
            )

    for key, value in raw.items():
        _validate_value_type(key, value, _WORKSPACE_TYPE_MAP, context=context)

    # Validate ecosystem.
    ecosystem = raw.get('ecosystem', '')
    if ecosystem and ecosystem not in ALLOWED_ECOSYSTEMS:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"ecosystem must be one of {sorted(ALLOWED_ECOSYSTEMS)}, got '{ecosystem}'",
            hint=f'Check the ecosystem value in {context}.',
        )

    if 'prerelease_mode' in raw:
        _validate_prerelease_mode(raw['prerelease_mode'])
    for list_key in ('exclude', 'exclude_publish', 'exclude_bump'):
        if list_key in raw:
            _validate_string_list(list_key, raw[list_key], context)

    kwargs: dict[str, Any] = dict(raw)  # noqa: ANN401
    if 'groups' in kwargs:
        kwargs['groups'] = _validate_groups(kwargs['groups'])

    # Default tool from ecosystem if not explicitly set.
    if not kwargs.get('tool') and ecosystem:
        kwargs['tool'] = DEFAULT_TOOLS.get(ecosystem, '')

    return WorkspaceConfig(label=label, **kwargs)


def load_config(workspace_root: Path) -> ReleaseConfig:
    """Load and validate configuration from ``releasekit.toml``.

    Global settings are top-level keys. Per-workspace settings live
    under ``[workspace.<label>]`` sections where ``<label>`` is a
    user-chosen name (e.g. ``[workspace.py]``, ``[workspace.js]``).

    Args:
        workspace_root: Directory containing ``releasekit.toml``.

    Returns:
        A validated :class:`ReleaseConfig`.

    Raises:
        ReleaseKitError: If the file contains invalid config.
    """
    config_path = workspace_root / CONFIG_FILENAME

    if not config_path.is_file():
        logger.debug('no_releasekit_config', path=str(config_path))
        return ReleaseConfig(config_path=None)

    try:
        text = config_path.read_text(encoding='utf-8')
    except OSError as exc:
        raise ReleaseKitError(
            code=E.CONFIG_NOT_FOUND,
            message=f'Failed to read {config_path}: {exc}',
        ) from exc

    try:
        doc = tomlkit.parse(text)
    except tomlkit.exceptions.TOMLKitError as exc:
        raise ReleaseKitError(
            code=E.CONFIG_NOT_FOUND,
            message=f'Failed to parse {config_path}: {exc}',
        ) from exc

    raw: dict[str, Any] = dict(doc)  # noqa: ANN401

    if not raw:
        logger.debug('empty_releasekit_config', path=str(config_path))
        return ReleaseConfig(config_path=config_path)

    # Separate workspace sections from global keys.
    workspace_raw: dict[str, Any] = {}  # noqa: ANN401
    if 'workspace' in raw:
        workspace_raw = dict(raw.pop('workspace'))

    # Validate global keys.
    for key in raw:
        if key not in VALID_KEYS:
            all_keys = VALID_KEYS | VALID_WORKSPACE_KEYS
            suggestion = difflib.get_close_matches(key, all_keys, n=1, cutoff=0.6)
            if suggestion and suggestion[0] in VALID_WORKSPACE_KEYS:
                hint = f"'{suggestion[0]}' is a workspace key. Move it under [workspace.<label>]."
            elif suggestion:
                hint = f"Did you mean '{suggestion[0]}'?"
            else:
                hint = 'Check the releasekit docs for valid keys.'
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_KEY,
                message=f"Unknown key '{key}' in releasekit.toml",
                hint=hint,
            )

    for key, value in raw.items():
        _validate_value_type(key, value, _GLOBAL_TYPE_MAP)

    if 'forge' in raw:
        _validate_forge(raw['forge'])
    if 'publish_from' in raw:
        _validate_publish_from(raw['publish_from'])

    # Parse [workspace.*] sections.
    workspaces: dict[str, WorkspaceConfig] = {}
    for ws_label, section in workspace_raw.items():
        if not isinstance(section, dict):
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_VALUE,
                message=f'[workspace.{ws_label}] must be a table, got {type(section).__name__}',
            )
        workspaces[ws_label] = _parse_workspace_section(ws_label, dict(section))

    # Cross-workspace validation.
    _validate_workspace_overlap(workspaces)

    global_kwargs: dict[str, Any] = dict(raw)  # noqa: ANN401
    return ReleaseConfig(**global_kwargs, workspaces=workspaces, config_path=config_path)


def _validate_workspace_overlap(workspaces: dict[str, WorkspaceConfig]) -> None:
    """Validate that workspace configurations do not conflict.

    Checks performed:

    1. **Overlapping roots** — Two workspaces whose ``root`` directories
       overlap (one is a prefix of the other) would discover the same
       packages, leading to duplicate version bumps, conflicting tags,
       and double publishes.

    2. **Conflicting tag formats** — Two workspaces with the same
       ``tag_format`` could produce colliding git tags for packages
       that happen to share a name across workspaces.

    Args:
        workspaces: Parsed workspace configs keyed by label.

    Raises:
        ReleaseKitError: If any overlap or conflict is detected.
    """
    if len(workspaces) < 2:
        return

    ws_list = list(workspaces.values())

    # Check 1: Overlapping roots.
    for i, ws_a in enumerate(ws_list):
        for ws_b in ws_list[i + 1 :]:
            root_a = Path(ws_a.root).resolve()
            root_b = Path(ws_b.root).resolve()
            if root_a == root_b:
                raise ReleaseKitError(
                    code=E.CONFIG_INVALID_VALUE,
                    message=(
                        f"Workspaces '{ws_a.label}' and '{ws_b.label}' "
                        f"share the same root '{ws_a.root}'. "
                        f'Each workspace must have a distinct root directory.'
                    ),
                    hint='Use different root directories so each package is discovered by exactly one workspace.',
                )
            # Check if one root is a parent of the other.
            try:
                root_b.relative_to(root_a)
                raise ReleaseKitError(
                    code=E.CONFIG_INVALID_VALUE,
                    message=(
                        f"Workspace '{ws_b.label}' root '{ws_b.root}' "
                        f"is inside workspace '{ws_a.label}' root '{ws_a.root}'. "
                        f'Overlapping roots cause packages to be discovered by both workspaces.'
                    ),
                    hint='Ensure workspace roots do not overlap. Use exclude patterns if needed.',
                )
            except ValueError:
                pass
            try:
                root_a.relative_to(root_b)
                raise ReleaseKitError(
                    code=E.CONFIG_INVALID_VALUE,
                    message=(
                        f"Workspace '{ws_a.label}' root '{ws_a.root}' "
                        f"is inside workspace '{ws_b.label}' root '{ws_b.root}'. "
                        f'Overlapping roots cause packages to be discovered by both workspaces.'
                    ),
                    hint='Ensure workspace roots do not overlap. Use exclude patterns if needed.',
                )
            except ValueError:
                pass

    # Check 2: Conflicting tag formats.
    tag_formats: dict[str, str] = {}  # tag_format → first label
    for ws in ws_list:
        if ws.tag_format in tag_formats:
            other = tag_formats[ws.tag_format]
            logger.warning(
                'conflicting_tag_formats',
                workspace_a=other,
                workspace_b=ws.label,
                tag_format=ws.tag_format,
                hint=(
                    'Two workspaces with the same tag_format may produce '
                    'colliding tags if packages share names across workspaces.'
                ),
            )
        else:
            tag_formats[ws.tag_format] = ws.label


# Prefix for group references in exclude lists.
_GROUP_PREFIX = 'group:'


def resolve_group_refs(
    patterns: list[str],
    groups: dict[str, list[str]],
) -> list[str]:
    """Expand ``group:<name>`` references into flat package-name patterns.

    Entries without the ``group:`` prefix are passed through unchanged.
    Group references are replaced with the package patterns from the
    named group. Groups can reference other groups recursively using
    the same ``group:<name>`` syntax — cycles are detected and raise
    an error.

    Args:
        patterns: List of glob patterns or ``group:<name>`` references.
        groups: The ``[groups]`` mapping from :class:`ReleaseConfig`.

    Returns:
        A flat list of glob patterns with all group refs expanded.

    Raises:
        ReleaseKitError: If a ``group:<name>`` reference points to an
            unknown group, or if a cycle is detected.

    Example::

        resolve_group_refs(
            ['group:all_plugins'],
            {
                'google': ['genkit-plugin-firebase'],
                'community': ['genkit-plugin-ollama'],
                'all_plugins': ['group:google', 'group:community'],
            },
        )
        # => ["genkit-plugin-firebase", "genkit-plugin-ollama"]
    """
    result: list[str] = []
    for pat in patterns:
        if pat.startswith(_GROUP_PREFIX):
            group_name = pat[len(_GROUP_PREFIX) :]
            result.extend(_resolve_group(group_name, groups, visiting=set()))
        else:
            result.append(pat)
    return result


def _resolve_group(
    name: str,
    groups: dict[str, list[str]],
    visiting: set[str],
) -> list[str]:
    """Recursively expand a single group, detecting cycles.

    Args:
        name: Group name to resolve.
        groups: All group definitions.
        visiting: Set of group names currently being resolved (for
            cycle detection).

    Returns:
        Flat list of package-name patterns.
    """
    if name not in groups:
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f"Unknown group '{name}' referenced as 'group:{name}'",
            hint=f'Available groups: {sorted(groups)}',
        )
    if name in visiting:
        cycle = ' → '.join([*visiting, name])
        raise ReleaseKitError(
            code=E.CONFIG_INVALID_VALUE,
            message=f'Cycle detected in group references: {cycle}',
            hint='Remove the circular group reference.',
        )

    visiting = visiting | {name}
    result: list[str] = []
    for pat in groups[name]:
        if pat.startswith(_GROUP_PREFIX):
            nested_name = pat[len(_GROUP_PREFIX) :]
            result.extend(_resolve_group(nested_name, groups, visiting))
        else:
            result.append(pat)
    return result


__all__ = [
    'ALLOWED_ECOSYSTEMS',
    'ALLOWED_FORGES',
    'ALLOWED_PRERELEASE_MODES',
    'ALLOWED_PUBLISH_FROM',
    'CONFIG_FILENAME',
    'DEFAULT_TOOLS',
    'VALID_KEYS',
    'VALID_WORKSPACE_KEYS',
    'ReleaseConfig',
    'WorkspaceConfig',
    'load_config',
    'resolve_group_refs',
]
