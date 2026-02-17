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

"""Pnpm workspace backend for releasekit.

The :class:`PnpmWorkspace` implements the
:class:`~releasekit.backends.workspace.Workspace` protocol for
`pnpm workspaces <https://pnpm.io/workspaces>`_.

Workspace structure::

    monorepo/
    ├── pnpm-workspace.yaml     # member globs
    ├── package.json             # root manifest (usually private)
    ├── pnpm-lock.yaml           # lockfile
    ├── packages/
    │   ├── core/
    │   │   └── package.json
    │   └── utils/
    │       └── package.json
    └── plugins/
        └── plugin-a/
            └── package.json

Dependency classification::

    "workspace:*"  → internal (participates in version propagation)
    "workspace:^"  → internal (participates in version propagation)
    "workspace:~"  → internal (participates in version propagation)
    "^1.2.3"       → external (pinned to npm registry)

All methods are async — file I/O is dispatched to ``aiofiles``
to avoid blocking the event loop.
"""

from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path
from typing import Any

from releasekit._types import DetectedLicense
from releasekit.backends.workspace._io import read_file as _read_file, write_file as _write_file
from releasekit.backends.workspace._types import Package
from releasekit.errors import E, ReleaseKitError
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.workspace.pnpm')

# pnpm workspace protocol prefixes that indicate an internal dep.
_WORKSPACE_PROTOCOL_RE = re.compile(r'^workspace:[*^~]')


def _is_workspace_dep(version_spec: str) -> bool:
    """Return True if the version spec uses the pnpm workspace protocol."""
    return bool(_WORKSPACE_PROTOCOL_RE.match(version_spec))


def _is_private(pkg_data: dict[str, object]) -> bool:
    """Return True if the package is marked private (not publishable)."""
    return pkg_data.get('private') is True


def _normalize_name(name: str) -> str:
    """Normalize an npm package name for comparison.

    npm names are case-insensitive, but unlike PyPI they
    don't have underscore/hyphen normalization.  We lowercase
    for comparison but preserve the original for display.
    """
    return name.lower()


def _parse_json(text: str, path: Path) -> dict[str, Any]:  # noqa: ANN401 - JSON dict values are inherently untyped
    """Parse JSON text, raising a ReleaseKitError on failure."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ReleaseKitError(
            code=E.WORKSPACE_PARSE_ERROR,
            message=f'Failed to parse {path}: {exc}',
            hint=f'Check that {path} contains valid JSON.',
        ) from exc
    if not isinstance(data, dict):
        raise ReleaseKitError(
            code=E.WORKSPACE_PARSE_ERROR,
            message=f'{path} is not a JSON object',
            hint=f'Expected a JSON object (dict) at the top level of {path}.',
        )
    return data


def _parse_yaml_simple(text: str) -> dict[str, list[str]]:
    """Minimal YAML parser for pnpm-workspace.yaml.

    pnpm-workspace.yaml has a very simple structure::

        packages:
          - 'packages/*'
          - 'plugins/*'
          - '!testapps/scratch'

    Rather than pulling in PyYAML as a dependency, we parse this
    simple format directly.  This avoids an extra dependency for
    what is always a flat list of strings.
    """
    result: dict[str, list[str]] = {}
    current_key: str | None = None

    for line in text.splitlines():
        stripped = line.strip()

        # Skip comments and blank lines.
        if not stripped or stripped.startswith('#'):
            continue

        # Key line: "packages:"
        if stripped.endswith(':') and not stripped.startswith('-'):
            current_key = stripped[:-1].strip()
            result[current_key] = []
            continue

        # List item: "  - 'packages/*'"
        if stripped.startswith('-') and current_key is not None:
            value = stripped[1:].strip()
            # Remove surrounding quotes.
            if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
                value = value[1:-1]
            result[current_key].append(value)

    return result


class PnpmWorkspace:
    """Workspace implementation for pnpm monorepos.

    Reads ``pnpm-workspace.yaml`` for member globs and ``package.json``
    files for package metadata. Dependencies using the
    ``workspace:*`` / ``workspace:^`` / ``workspace:~`` protocol are
    classified as internal.

    Args:
        root: Path to the workspace root (containing ``pnpm-workspace.yaml``).
    """

    def __init__(self, root: Path) -> None:
        """Initialize with the workspace root path."""
        self._root = root

    async def discover(
        self,
        *,
        exclude_patterns: list[str] | None = None,
    ) -> list[Package]:
        """Discover all packages in the pnpm workspace.

        Reads ``pnpm-workspace.yaml`` for member globs, expands them,
        and parses each member's ``package.json``.
        """
        workspace_yaml_path = self._root / 'pnpm-workspace.yaml'
        text = await _read_file(workspace_yaml_path)
        config = _parse_yaml_simple(text)

        members = config.get('packages', [])
        if not members:
            raise ReleaseKitError(
                code=E.WORKSPACE_NO_MEMBERS,
                message='No packages defined in pnpm-workspace.yaml',
                hint='Add package globs, e.g. packages:\\n  - "packages/*"',
            )

        # Separate inclusion and exclusion patterns.
        include_patterns: list[str] = []
        exclude_from_yaml: list[str] = []
        for pattern in members:
            if pattern.startswith('!'):
                exclude_from_yaml.append(pattern[1:])
            else:
                include_patterns.append(pattern)

        # Expand globs to find package directories.
        pkg_dirs = self._expand_member_globs(include_patterns, exclude_from_yaml)
        if not pkg_dirs:
            raise ReleaseKitError(
                code=E.WORKSPACE_NO_MEMBERS,
                message=f'No packages found matching: {members}',
                hint='Check that your globs match directories with package.json files.',
            )

        # First pass: collect all names for internal dep classification.
        all_names: set[str] = set()
        for pkg_dir in pkg_dirs:
            pkg_json_path = pkg_dir / 'package.json'
            try:
                quick_text = await _read_file(pkg_json_path)
                quick_data = _parse_json(quick_text, pkg_json_path)
                name = quick_data.get('name', '')
                if isinstance(name, str) and name:
                    all_names.add(_normalize_name(name))
            except ReleaseKitError:
                pass  # Will be caught in full parse.

        internal_names = frozenset(all_names)

        # Second pass: full parse with dependency classification.
        packages: list[Package] = []
        seen_names: set[str] = set()
        for pkg_dir in pkg_dirs:
            pkg = await self._parse_package(pkg_dir, internal_names)
            if pkg is None:
                # Nameless package.json (workspace root) — skip silently.
                log.debug('skipped_nameless_package', path=str(pkg_dir))
                continue
            if pkg.name in seen_names:
                raise ReleaseKitError(
                    code=E.WORKSPACE_DUPLICATE_PACKAGE,
                    message=f"Duplicate package name '{pkg.name}' found at {pkg_dir}",
                    hint='Each package in the workspace must have a unique name.',
                )
            seen_names.add(pkg.name)
            packages.append(pkg)

        if exclude_patterns:
            packages = [p for p in packages if not any(fnmatch.fnmatch(p.name, pat) for pat in exclude_patterns)]

        result = sorted(packages, key=lambda p: p.name)
        log.info('discovered_packages', count=len(result))
        return result

    async def rewrite_version(
        self,
        manifest_path: Path,
        new_version: str,
    ) -> str:
        """Rewrite ``version`` in a package.json file.

        Preserves formatting by using ``json.dumps`` with indent=2
        (the npm/pnpm convention) and a trailing newline.
        """
        text = await _read_file(manifest_path)
        data = _parse_json(text, manifest_path)

        if 'version' not in data:
            raise ReleaseKitError(
                code=E.VERSION_INVALID,
                message=f'No "version" key in {manifest_path}',
                hint='Add a "version" field to package.json.',
            )

        old_version = str(data['version'])
        data['version'] = new_version

        new_text = json.dumps(data, indent=2, ensure_ascii=False) + '\n'
        await _write_file(manifest_path, new_text)

        log.info(
            'manifest_version_rewritten',
            path=str(manifest_path),
            old=old_version,
            new=new_version,
        )
        return old_version

    async def rewrite_dependency_version(
        self,
        manifest_path: Path,
        dep_name: str,
        new_version: str,
    ) -> None:
        """Rewrite a dependency version in package.json.

        Replaces ``"workspace:*"`` (or similar workspace protocol
        references) with a pinned version for publishing.

        Searches all dependency sections: ``dependencies``,
        ``devDependencies``, ``peerDependencies``, and
        ``optionalDependencies``.
        """
        text = await _read_file(manifest_path)
        data = _parse_json(text, manifest_path)

        normalized_target = _normalize_name(dep_name)
        found = False

        dep_sections = ['dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies']
        for section_name in dep_sections:
            section = data.get(section_name)
            if not isinstance(section, dict):
                continue
            for key in list(section):
                if _normalize_name(key) == normalized_target:
                    old_spec = section[key]
                    section[key] = f'^{new_version}'
                    log.info(
                        'dependency_version_rewritten',
                        path=str(manifest_path),
                        dep=dep_name,
                        section=section_name,
                        old=str(old_spec),
                        new=f'^{new_version}',
                    )
                    found = True

        if found:
            new_text = json.dumps(data, indent=2, ensure_ascii=False) + '\n'
            await _write_file(manifest_path, new_text)

    async def detect_license(
        self,
        pkg_path: Path,
        pkg_name: str = '',
    ) -> DetectedLicense:
        """Detect license from ``package.json``."""
        if not pkg_name:
            pkg_name = pkg_path.name
        pj = pkg_path / 'package.json'
        if not pj.is_file():
            return DetectedLicense(value='', source='', package_name=pkg_name)
        try:
            text = await _read_file(pj)
            data = _parse_json(text, pj)
        except Exception:  # noqa: BLE001
            return DetectedLicense(value='', source='', package_name=pkg_name)

        # Standard: "license": "MIT" or "license": "MIT OR Apache-2.0"
        lic = data.get('license')
        if isinstance(lic, str) and lic.strip():
            return DetectedLicense(
                value=lic.strip(),
                source='package.json',
                package_name=pkg_name,
            )

        # Legacy: "license": { "type": "MIT" }
        if isinstance(lic, dict):
            lic_type = lic.get('type', '')
            if isinstance(lic_type, str) and lic_type.strip():
                return DetectedLicense(
                    value=lic_type.strip(),
                    source='package.json license.type',
                    package_name=pkg_name,
                )

        # Array form (deprecated): "licenses": [{"type": "MIT"}]
        licenses = data.get('licenses')
        if isinstance(licenses, list) and licenses:
            first = licenses[0]
            if isinstance(first, dict):
                lic_type = first.get('type', '')
                if isinstance(lic_type, str) and lic_type.strip():
                    return DetectedLicense(
                        value=lic_type.strip(),
                        source='package.json licenses[0].type',
                        package_name=pkg_name,
                    )

        return DetectedLicense(value='', source='', package_name=pkg_name)

    def _expand_member_globs(
        self,
        include: list[str],
        exclude: list[str],
    ) -> list[Path]:
        """Expand workspace member globs to package directories.

        Only directories containing a ``package.json`` are included.

        Handles special pnpm workspace patterns:

        - ``"."`` — the workspace root is itself a package.
        - ``"./*"`` or ``"./plugins/*"`` — normalized to ``"*"`` /
          ``"plugins/*"`` so ``pathlib.glob()`` doesn't crash on the
          leading ``"./"``.
        """
        found: set[Path] = set()
        for pattern in include:
            for candidate in self._glob_safe(pattern):
                if candidate.is_dir() and (candidate / 'package.json').is_file():
                    found.add(candidate.resolve())

        excluded: set[Path] = set()
        for pattern in exclude:
            for candidate in self._glob_safe(pattern):
                excluded.add(candidate.resolve())

        result = sorted(found - excluded)
        log.debug('expanded_member_globs', include=include, exclude=exclude, count=len(result))
        return result

    def _glob_safe(self, pattern: str) -> list[Path]:
        """Expand a single glob pattern, handling pnpm-specific patterns.

        ``"."`` refers to the workspace root itself.
        ``"./"`` prefix is stripped because ``pathlib.glob("./foo")``
        crashes with an ``IndexError`` on some Python versions.
        """
        # "." means the workspace root directory is itself a package.
        if pattern == '.':
            return [self._root]

        # Strip leading "./" — pathlib.glob can't handle it.
        if pattern.startswith('./'):
            pattern = pattern[2:]

        # Guard against empty pattern after stripping.
        if not pattern:
            return [self._root]

        return sorted(self._root.glob(str(pattern)))

    async def _parse_package(
        self,
        pkg_dir: Path,
        internal_names: frozenset[str],
    ) -> Package | None:
        """Parse a single package's package.json.

        Returns ``None`` for packages without a ``name`` field (e.g.,
        workspace-root ``package.json`` files that serve only as
        orchestrators and are not publishable packages).

        A dependency is internal if:
        1. Its name matches a workspace member.
        2. Its version spec uses the ``workspace:`` protocol.
        """
        pkg_json_path = pkg_dir / 'package.json'
        text = await _read_file(pkg_json_path)
        data = _parse_json(text, pkg_json_path)

        name = data.get('name', '')
        if not isinstance(name, str) or not name:
            return None

        version = str(data.get('version', '0.0.0'))

        internal_deps: list[str] = []
        external_deps: list[str] = []
        all_deps: list[str] = []

        # Collect from all dependency sections.
        dep_sections = ['dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies']
        seen_dep_names: set[str] = set()

        for section_name in dep_sections:
            section = data.get(section_name)
            if not isinstance(section, dict):
                continue
            for dep_name, dep_spec in section.items():
                dep_spec_str = str(dep_spec)
                normalized = _normalize_name(dep_name)

                # Avoid double-counting across sections.
                if normalized in seen_dep_names:
                    continue
                seen_dep_names.add(normalized)

                all_deps.append(f'{dep_name}@{dep_spec_str}')

                if normalized in internal_names and _is_workspace_dep(dep_spec_str):
                    internal_deps.append(dep_name)
                elif normalized not in internal_names:
                    external_deps.append(dep_name)

        return Package(
            name=name,
            version=version,
            path=pkg_dir,
            manifest_path=pkg_json_path,
            internal_deps=sorted(internal_deps),
            external_deps=sorted(external_deps),
            all_deps=sorted(all_deps),
            is_publishable=not _is_private(data),
        )


__all__ = [
    'PnpmWorkspace',
]
