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

"""Rust/Cargo workspace backend for releasekit.

The :class:`CargoWorkspace` implements the
:class:`~releasekit.backends.workspace.Workspace` protocol by parsing
``Cargo.toml`` workspace and member manifests.

Cargo workspace layout (directory name is arbitrary)::

    rust/
    ├── Cargo.toml       ← workspace root ([workspace] with members)
    ├── Cargo.lock       ← shared lockfile
    ├── core/
    │   └── Cargo.toml   ← crate: my-core
    ├── utils/
    │   └── Cargo.toml   ← crate: my-utils (depends on my-core)
    └── cli/
        └── Cargo.toml   ← crate: my-cli (depends on my-core, my-utils)

Version handling:

    Rust crates store their version in ``Cargo.toml`` under
    ``[package].version``. Workspace-level version inheritance is
    supported via ``version.workspace = true`` in member crates,
    with the actual version in the root ``[workspace.package].version``.

    Dependencies between workspace members use ``{ workspace = true }``
    or explicit path/version references.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

import tomlkit
import tomlkit.exceptions

from releasekit._types import DetectedLicense
from releasekit.backends.workspace._io import read_file, write_file
from releasekit.backends.workspace._types import Package
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.workspace.cargo')

# Regex to extract workspace members from root Cargo.toml.
# Matches: members = ["core", "utils", "cli/*"]
_MEMBERS_RE = re.compile(r'members\s*=\s*\[([^\]]*)\]', re.DOTALL)

# Regex to extract a quoted string value.
_QUOTED_RE = re.compile(r'"([^"]+)"')

# Regex to extract package name from Cargo.toml.
_NAME_RE = re.compile(r'^\s*name\s*=\s*"([^"]+)"', re.MULTILINE)

# Regex to extract package version from Cargo.toml.
_VERSION_RE = re.compile(r'^\s*version\s*=\s*"([^"]+)"', re.MULTILINE)

# Regex to detect workspace version inheritance.
_VERSION_WORKSPACE_RE = re.compile(
    r'^\s*version\.workspace\s*=\s*true',
    re.MULTILINE,
)


class CargoWorkspace:
    """Rust :class:`~releasekit.backends.workspace.Workspace` implementation.

    Parses the root ``Cargo.toml`` to discover workspace members and
    each member's ``Cargo.toml`` for metadata and dependencies.

    Args:
        workspace_root: Path to the directory containing the workspace
            ``Cargo.toml`` with ``[workspace]``.
    """

    def __init__(self, workspace_root: Path) -> None:
        """Initialize with the Cargo workspace root."""
        self._root = workspace_root.resolve()

    async def discover(
        self,
        *,
        exclude_patterns: list[str] | None = None,
    ) -> list[Package]:
        """Discover all crates in the Cargo workspace.

        Args:
            exclude_patterns: Glob patterns to exclude crates by name.

        Returns:
            Sorted list of discovered Rust crate packages.
        """
        root_toml = self._root / 'Cargo.toml'
        if not root_toml.is_file():
            log.warning('cargo_toml_not_found', root=str(self._root))
            return []

        root_text = root_toml.read_text(encoding='utf-8')
        if '[workspace]' not in root_text:
            log.warning('not_a_workspace', root=str(self._root))
            return []

        # Parse workspace-level version (for inheritance).
        ws_version = _parse_workspace_version(root_text)

        # Extract member globs.
        member_globs = _parse_member_globs(root_text)
        if not member_globs:
            log.warning('no_members', root=str(self._root))
            return []

        # Expand globs to actual crate directories.
        crate_dirs = _expand_member_globs(self._root, member_globs)

        # First pass: collect all crate names for internal dep classification.
        all_crate_names: dict[str, Path] = {}
        for crate_dir in crate_dirs:
            cargo_toml = crate_dir / 'Cargo.toml'
            if cargo_toml.is_file():
                text = cargo_toml.read_text(encoding='utf-8')
                m = _NAME_RE.search(text)
                if m:
                    all_crate_names[m.group(1)] = crate_dir

        packages: list[Package] = []
        exclude = exclude_patterns or []

        for name, crate_dir in sorted(all_crate_names.items()):
            if any(fnmatch.fnmatch(name, pat) for pat in exclude):
                log.debug('excluded', crate=name, pattern=exclude)
                continue

            cargo_toml = crate_dir / 'Cargo.toml'
            text = cargo_toml.read_text(encoding='utf-8')

            # Parse version (may inherit from workspace).
            version = _parse_crate_version(text, ws_version)

            # Parse dependencies.
            deps = _parse_dependencies(text)
            internal_deps = [d for d in deps if d in all_crate_names]
            external_deps = [d for d in deps if d not in all_crate_names]

            # Check if crate is publishable (publish != false).
            is_publishable = 'publish = false' not in text

            packages.append(
                Package(
                    name=name,
                    version=version,
                    path=crate_dir,
                    manifest_path=cargo_toml,
                    internal_deps=internal_deps,
                    external_deps=external_deps,
                    all_deps=deps,
                    is_publishable=is_publishable,
                )
            )

        packages.sort(key=lambda p: p.name)
        log.info(
            'discovered',
            count=len(packages),
            crates=[p.name for p in packages],
        )
        return packages

    async def rewrite_version(
        self,
        manifest_path: Path,
        new_version: str,
    ) -> str:
        """Rewrite the ``version`` field in ``Cargo.toml``.

        Handles both direct version strings and workspace-inherited
        versions (rewrites the workspace root in the latter case).

        Returns:
            The old version string.
        """
        text = await read_file(manifest_path)

        # Check for workspace version inheritance.
        if _VERSION_WORKSPACE_RE.search(text):
            # Rewrite the workspace root Cargo.toml instead.
            root_toml = self._root / 'Cargo.toml'
            return await self._rewrite_workspace_version(root_toml, new_version)

        m = _VERSION_RE.search(text)
        old_version = m.group(1) if m else '0.0.0'

        new_text = _VERSION_RE.sub(
            f'version = "{new_version}"',
            text,
            count=1,
        )

        if new_text != text:
            await write_file(manifest_path, new_text)
            log.info(
                'version_rewritten',
                manifest=str(manifest_path),
                old=old_version,
                new=new_version,
            )

        return old_version

    async def _rewrite_workspace_version(
        self,
        root_toml: Path,
        new_version: str,
    ) -> str:
        """Rewrite ``[workspace.package].version`` in the root Cargo.toml."""
        text = await read_file(root_toml)

        # Match version under [workspace.package].
        ws_ver_re = re.compile(
            r'(^\s*version\s*=\s*)"([^"]+)"',
            re.MULTILINE,
        )
        m = ws_ver_re.search(text)
        old_version = m.group(2) if m else '0.0.0'

        new_text = ws_ver_re.sub(rf'\g<1>"{new_version}"', text, count=1)

        if new_text != text:
            await write_file(root_toml, new_text)
            log.info(
                'workspace_version_rewritten',
                manifest=str(root_toml),
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
        """Rewrite a dependency version in ``Cargo.toml``.

        Handles both simple string versions and inline table versions::

            foo = "1.0.0"           → foo = "2.0.0"
            foo = { version = "1.0" → foo = { version = "2.0"
        """
        text = await read_file(manifest_path)

        # Pattern 1: simple string — foo = "1.0.0"
        simple_re = re.compile(
            rf'(^\s*{re.escape(dep_name)}\s*=\s*)"[^"]*"',
            re.MULTILINE,
        )
        # Pattern 2: inline table — foo = { version = "1.0.0"
        table_re = re.compile(
            rf'(^\s*{re.escape(dep_name)}\s*=\s*\{{[^}}]*version\s*=\s*)"[^"]*"',
            re.MULTILINE,
        )

        new_text = simple_re.sub(rf'\g<1>"{new_version}"', text)
        if new_text == text:
            new_text = table_re.sub(rf'\g<1>"{new_version}"', text)

        if new_text != text:
            await write_file(manifest_path, new_text)
            log.info(
                'dependency_rewritten',
                manifest=str(manifest_path),
                dep=dep_name,
                version=new_version,
            )
        else:
            log.debug(
                'dependency_not_found',
                manifest=str(manifest_path),
                dep=dep_name,
            )

    async def detect_license(
        self,
        pkg_path: Path,
        pkg_name: str = '',
    ) -> DetectedLicense:
        """Detect license from ``Cargo.toml`` ``[package].license``."""
        if not pkg_name:
            pkg_name = pkg_path.name
        cargo = pkg_path / 'Cargo.toml'
        if not cargo.is_file():
            return DetectedLicense(value='', source='', package_name=pkg_name)
        try:
            text = await read_file(cargo)
            doc = tomlkit.parse(text)
        except Exception:  # noqa: BLE001
            return DetectedLicense(value='', source='', package_name=pkg_name)

        package = doc.get('package', {})
        lic = package.get('license')
        if isinstance(lic, str) and lic.strip():
            return DetectedLicense(
                value=lic.strip(),
                source='Cargo.toml [package].license',
                package_name=pkg_name,
            )
        return DetectedLicense(value='', source='', package_name=pkg_name)


def _parse_member_globs(root_text: str) -> list[str]:
    """Extract workspace member globs from root Cargo.toml."""
    m = _MEMBERS_RE.search(root_text)
    if not m:
        return []
    return _QUOTED_RE.findall(m.group(1))


def _expand_member_globs(root: Path, globs: list[str]) -> list[Path]:
    """Expand member globs to actual directories."""
    dirs: list[Path] = []
    for pattern in globs:
        if '*' in pattern or '?' in pattern:
            for match in sorted(root.glob(pattern)):
                if match.is_dir() and (match / 'Cargo.toml').is_file():
                    dirs.append(match)
        else:
            candidate = root / pattern
            if candidate.is_dir() and (candidate / 'Cargo.toml').is_file():
                dirs.append(candidate)
    return dirs


def _parse_workspace_version(root_text: str) -> str:
    """Extract ``[workspace.package].version`` from root Cargo.toml."""
    # Look for version after [workspace.package].
    in_ws_pkg = False
    for line in root_text.splitlines():
        stripped = line.strip()
        if stripped == '[workspace.package]':
            in_ws_pkg = True
            continue
        if stripped.startswith('[') and in_ws_pkg:
            break
        if in_ws_pkg:
            m = _VERSION_RE.match(line)
            if m:
                return m.group(1)
    return '0.0.0'


def _parse_crate_version(text: str, ws_version: str) -> str:
    """Extract the version from a crate's Cargo.toml.

    If the crate uses ``version.workspace = true``, returns the
    workspace-level version.
    """
    if _VERSION_WORKSPACE_RE.search(text):
        return ws_version
    m = _VERSION_RE.search(text)
    return m.group(1) if m else '0.0.0'


def _parse_dependencies(text: str) -> list[str]:
    """Extract dependency names from ``[dependencies]`` sections.

    Uses ``tomlkit`` to properly parse the TOML structure and inspect
    only dependency tables (``[dependencies]``, ``[dev-dependencies]``,
    ``[build-dependencies]``, and ``[target.*.dependencies]``), avoiding
    false positives from unrelated sections like ``[package]``.
    """
    try:
        doc = tomlkit.parse(text)
    except tomlkit.exceptions.ParseError:
        return []

    deps: set[str] = set()
    dep_table_keys = ('dependencies', 'dev-dependencies', 'build-dependencies')

    for key in dep_table_keys:
        table = doc.get(key)
        if isinstance(table, dict):
            deps.update(table.keys())

    # Also check [target.*.dependencies] tables.
    target = doc.get('target')
    if isinstance(target, dict):
        for _target_name, target_table in target.items():
            if isinstance(target_table, dict):
                for key in dep_table_keys:
                    sub = target_table.get(key)
                    if isinstance(sub, dict):
                        deps.update(sub.keys())

    return sorted(deps)


__all__ = [
    'CargoWorkspace',
]
