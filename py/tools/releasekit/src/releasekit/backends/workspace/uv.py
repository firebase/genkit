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

"""uv workspace backend for releasekit.

The :class:`UvWorkspace` implements the
:class:`~releasekit.backends.workspace.Workspace` protocol for
``pyproject.toml`` + ``[tool.uv.workspace]`` + ``[tool.uv.sources]``.

All file I/O is non-blocking via ``aiofiles``.
"""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Any

import aiofiles
import tomlkit
import tomlkit.exceptions
from packaging.requirements import InvalidRequirement, Requirement

from releasekit.backends.workspace._types import Package
from releasekit.errors import E, ReleaseKitError
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.workspace.uv')


def _parse_dep_name(dep_spec: str) -> str:
    """Extract the normalized package name from a PEP 508 dependency specifier."""
    try:
        return Requirement(dep_spec).name.lower()
    except InvalidRequirement:
        name = re.split(r'[<>=!~,;\[]', dep_spec, maxsplit=1)[0].strip()
        return name.lower()


def _normalize_name(name: str) -> str:
    """Normalize a package name per PEP 503 (lowercase, underscores to hyphens)."""
    return name.lower().replace('_', '-')


def _is_publishable(classifiers: list[str]) -> bool:
    """Check if any classifier indicates the package is private."""
    return not any('Private' in c and 'Do Not Upload' in c for c in classifiers)


async def _read_file(path: Path) -> str:
    """Read a file asynchronously via aiofiles."""
    try:
        async with aiofiles.open(path, encoding='utf-8') as f:
            return await f.read()
    except OSError as exc:
        raise ReleaseKitError(
            code=E.WORKSPACE_PARSE_ERROR,
            message=f'Failed to read {path}: {exc}',
        ) from exc


async def _write_file(path: Path, content: str) -> None:
    """Write a file asynchronously via aiofiles."""
    try:
        async with aiofiles.open(path, mode='w', encoding='utf-8') as f:
            await f.write(content)
    except OSError as exc:
        raise ReleaseKitError(
            code=E.WORKSPACE_PARSE_ERROR,
            message=f'Failed to write {path}: {exc}',
        ) from exc


def _parse_toml(text: str, path: Path) -> tomlkit.TOMLDocument:
    """Parse TOML text, raising a ReleaseKitError on failure."""
    try:
        return tomlkit.parse(text)
    except tomlkit.exceptions.TOMLKitError as exc:
        raise ReleaseKitError(
            code=E.WORKSPACE_PARSE_ERROR,
            message=f'Failed to parse {path}: {exc}',
        ) from exc


class UvWorkspace:
    """Workspace implementation for uv workspaces (``pyproject.toml``).

    Reads ``[tool.uv.workspace]`` for member globs and exclusions.
    Reads ``[tool.uv.sources]`` to determine which dependencies are
    workspace-sourced (``workspace = true``) vs pinned to PyPI.

    All file I/O is non-blocking via ``aiofiles``.

    Args:
        root: Path to the workspace root directory containing the
            root ``pyproject.toml``.
    """

    def __init__(self, root: Path) -> None:
        """Initialize instance."""
        self._root = root.resolve()

    @property
    def root(self) -> Path:
        """Return the workspace root path."""
        return self._root

    async def discover(
        self,
        *,
        exclude_patterns: list[str] | None = None,
    ) -> list[Package]:
        """Discover all packages in a uv workspace.

        Three-pass discovery:

        1. Quick-parse all member dirs to collect package names.
        2. Read ``[tool.uv.sources]`` to identify workspace-sourced deps.
        3. Full-parse each member with dependency classification.

        A dependency is classified as **internal** only if it satisfies
        BOTH conditions:

        - Its name matches a workspace member.
        - It is listed with ``workspace = true`` in ``[tool.uv.sources]``
          of the root ``pyproject.toml``.
        """
        root_pyproject = self._root / 'pyproject.toml'
        if not root_pyproject.is_file():
            raise ReleaseKitError(
                code=E.WORKSPACE_NOT_FOUND,
                message=f'No pyproject.toml found at {self._root}',
                hint='Point to the directory containing your workspace pyproject.toml.',
            )

        text = await _read_file(root_pyproject)
        doc = _parse_toml(text, root_pyproject)

        uv_section = doc.get('tool', {}).get('uv', {})
        workspace_section: dict[str, Any] = dict(uv_section.get('workspace', {}))  # noqa: ANN401
        members: list[str] = list(workspace_section.get('members', []))
        excludes: list[str] = list(workspace_section.get('exclude', []))

        if not members:
            raise ReleaseKitError(
                code=E.WORKSPACE_NO_MEMBERS,
                message='No members defined in [tool.uv.workspace]',
                hint='Add member globs, e.g. members = ["packages/*", "plugins/*"]',
            )

        pkg_dirs = self._expand_member_globs(members, excludes)
        if not pkg_dirs:
            raise ReleaseKitError(
                code=E.WORKSPACE_NO_MEMBERS,
                message=f'No packages found matching members={members}',
                hint='Check that your member globs match directories with pyproject.toml files.',
            )

        all_names: set[str] = set()
        for pkg_dir in pkg_dirs:
            pyproject_path = pkg_dir / 'pyproject.toml'
            try:
                member_text = await _read_file(pyproject_path)
                quick_doc = _parse_toml(member_text, pyproject_path)
                name = quick_doc.get('project', {}).get('name', '')
                if name:
                    all_names.add(_normalize_name(name))
            except ReleaseKitError:
                pass

        uv_sources: dict[str, Any] = dict(uv_section.get('sources', {}))  # noqa: ANN401
        workspace_sourced: set[str] = set()
        for src_name, src_config in uv_sources.items():
            normalized = _normalize_name(src_name)
            if normalized in all_names:
                if isinstance(src_config, dict) and src_config.get('workspace'):
                    workspace_sourced.add(normalized)

        internal_names = frozenset(all_names)
        ws_sourced = frozenset(workspace_sourced)

        if workspace_sourced:
            log.info(
                'workspace_sourced_deps',
                count=len(workspace_sourced),
                names=sorted(workspace_sourced),
            )

        pinned_members = all_names - workspace_sourced
        if pinned_members:
            log.info(
                'pinned_to_pypi',
                count=len(pinned_members),
                names=sorted(pinned_members),
                hint='These workspace members are NOT in [tool.uv.sources] with '
                'workspace=true; they will be excluded from the release graph.',
            )

        packages: list[Package] = []
        seen_names: set[str] = set()
        for pkg_dir in pkg_dirs:
            pkg = await self._parse_package(pkg_dir, internal_names, ws_sourced)
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
        """Rewrite ``[project].version`` in a pyproject.toml file.

        Uses tomlkit to preserve comments, formatting, and ordering.
        """
        text = await _read_file(manifest_path)
        doc = _parse_toml(text, manifest_path)

        project = doc.get('project')
        if not isinstance(project, dict) or 'version' not in project:
            raise ReleaseKitError(
                code=E.VERSION_INVALID,
                message=f'No [project].version key in {manifest_path}',
                hint='Add a version field to [project] in pyproject.toml.',
            )

        old_version = str(project['version'])
        project['version'] = new_version

        await _write_file(manifest_path, tomlkit.dumps(doc))

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
        """Rewrite a dependency version constraint in pyproject.toml.

        Finds the dependency in ``[project].dependencies`` and replaces
        its version specifier with ``==new_version``.
        """
        text = await _read_file(manifest_path)
        doc = _parse_toml(text, manifest_path)

        project = doc.get('project')
        if not isinstance(project, dict):
            return

        deps = project.get('dependencies')
        if not isinstance(deps, list):
            return

        normalized_target = _normalize_name(dep_name)
        for i, spec in enumerate(deps):
            spec_name = _normalize_name(_parse_dep_name(str(spec)))
            if spec_name == normalized_target:
                deps[i] = f'{dep_name}=={new_version}'
                log.info(
                    'dependency_version_rewritten',
                    path=str(manifest_path),
                    dep=dep_name,
                    old=str(spec),
                    new=f'{dep_name}=={new_version}',
                )
                break

        await _write_file(manifest_path, tomlkit.dumps(doc))

    def _expand_member_globs(
        self,
        members: list[str],
        excludes: list[str],
    ) -> list[Path]:
        """Expand workspace member globs into concrete package directories.

        Glob expansion uses synchronous ``Path.glob()`` which is
        metadata-only (readdir + stat) and sub-millisecond for typical
        workspace sizes.
        """
        found: set[Path] = set()
        for pattern in members:
            for candidate in sorted(self._root.glob(str(pattern))):
                if candidate.is_dir() and (candidate / 'pyproject.toml').is_file():
                    found.add(candidate.resolve())

        excluded: set[Path] = set()
        for pattern in excludes:
            for candidate in sorted(self._root.glob(str(pattern))):
                excluded.add(candidate.resolve())

        result = sorted(found - excluded)
        log.debug('expanded_member_globs', members=members, excludes=excludes, count=len(result))
        return result

    async def _parse_package(
        self,
        pkg_dir: Path,
        internal_names: frozenset[str],
        workspace_sourced: frozenset[str],
    ) -> Package:
        """Parse a single package's pyproject.toml.

        A dependency is internal only if it is both a workspace member
        AND workspace-sourced (has ``workspace = true`` in
        ``[tool.uv.sources]``).
        """
        pyproject_path = pkg_dir / 'pyproject.toml'
        text = await _read_file(pyproject_path)
        doc = _parse_toml(text, pyproject_path)

        project: dict[str, Any] = dict(doc.get('project', {}))  # noqa: ANN401
        name = project.get('name', '')
        if not name:
            raise ReleaseKitError(
                code=E.WORKSPACE_PARSE_ERROR,
                message=f'No [project].name in {pyproject_path}',
                hint='Every workspace member must have a [project] section with a name.',
            )

        version = project.get('version', '0.0.0')
        classifiers: list[str] = list(project.get('classifiers', []))
        dep_specs: list[str] = list(project.get('dependencies', []))

        internal_deps: list[str] = []
        external_deps: list[str] = []
        for spec in dep_specs:
            dep_name = _normalize_name(_parse_dep_name(spec))
            if dep_name in internal_names and dep_name in workspace_sourced:
                internal_deps.append(dep_name)
            else:
                if dep_name in internal_names:
                    log.info(
                        'dep_pinned_to_pypi',
                        package=_normalize_name(name),
                        dep=dep_name,
                        hint='Not in [tool.uv.sources] with workspace=true',
                    )
                external_deps.append(dep_name)

        # pkg_dir is already resolved by _expand_member_globs; pyproject_path
        # is derived from it.  No need to resolve again.
        return Package(
            name=_normalize_name(name),
            version=version,
            path=pkg_dir,
            manifest_path=pyproject_path,
            internal_deps=sorted(internal_deps),
            external_deps=sorted(external_deps),
            all_deps=[spec.strip() for spec in dep_specs],
            is_publishable=_is_publishable(classifiers),
        )


__all__ = [
    'UvWorkspace',
]
