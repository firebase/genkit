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

"""Workspace package discovery for uv workspaces.

Reads ``[tool.uv.workspace]`` from the root pyproject.toml, expands
member globs, parses each member's ``pyproject.toml``, and classifies
dependencies as internal (within the workspace) or external.

Key Concepts (ELI5)::

    ┌─────────────────────────┬────────────────────────────────────────────┐
    │ Concept                 │ ELI5 Explanation                           │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ Package                 │ One Python package in the workspace.      │
    │                         │ Like one box in a warehouse — has a name, │
    │                         │ version, and list of things it needs.     │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ Internal dep            │ A dependency that's another package in    │
    │                         │ this workspace AND resolved from the      │
    │                         │ workspace source (not pinned to PyPI).    │
    │                         │ Must have ``workspace = true`` in         │
    │                         │ ``[tool.uv.sources]``.                   │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ PEP 503 normalization   │ Package names are lowercased and          │
    │                         │ underscores become hyphens: My_Pkg → my- │
    │                         │ pkg. Ensures consistent matching.         │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ discover_packages()     │ Walk the workspace, find all packages,    │
    │                         │ and figure out which ones depend on which.│
    │                         │ Like taking inventory of all the boxes    │
    │                         │ and reading their shipping labels.        │
    └─────────────────────────┴────────────────────────────────────────────┘

Data Flow — Two-Pass Discovery::

    Pass 1: Collect all package names (quick parse).
    Pass 2: Full parse with dependency classification.

    pyproject.toml                    discover_packages()
    ┌──────────────────┐        ┌──────────────────────────┐
    │ [tool.uv.workspace]│        │ 1. Read member globs     │
    │ members = [        │───────→│ 2. Expand to directories │
    │   "packages/*",    │        │ 3. Apply path excludes   │
    │   "plugins/*"      │        │ 4. Parse each pyproject  │
    │ ]                  │        │ 5. Classify deps         │
    │ exclude = [...]    │        │ 6. Apply name excludes   │
    └──────────────────┘        └──────────────────────────┘
                                          │
                                    list[Package]
                                          │
                      ┌───────────────────┼───────────────────┐
                      ▼                   ▼                   ▼
                  Package(             Package(           Package(
                    name="genkit",       name="plugin-a",   name="plugin-b",
                    internal=[],         internal=["genkit"],internal=["genkit"],
                    external=["pydantic"]external=["httpx"], external=[],
                  )                    )                   )

Exclusion — Two Separate Namespaces::

    Workspace excludes (path globs):      exclude_patterns (name globs):
    ┌──────────────────────────────┐     ┌──────────────────────────────┐
    │ From [tool.uv.workspace]    │     │ From [tool.releasekit]       │
    │ exclude = ["testapps/*"]    │     │ exclude = ["sample-*"]       │
    │                              │     │                              │
    │ Applied during glob          │     │ Applied after parsing        │
    │ expansion (step 3)           │     │ by package name (step 6)     │
    └──────────────────────────────┘     └──────────────────────────────┘

Usage::

    from releasekit.workspace import discover_packages

    packages = discover_packages(Path('.'))
    for pkg in packages:
        print(f'{pkg.name} v{pkg.version}  deps={pkg.internal_deps}')
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import fnmatch
from pathlib import Path
from typing import Any

import tomlkit
import tomlkit.exceptions

from releasekit.backends.workspace._types import Package
from releasekit.backends.workspace.bazel import BazelWorkspace
from releasekit.backends.workspace.cargo import CargoWorkspace
from releasekit.backends.workspace.clojure import ClojureWorkspace
from releasekit.backends.workspace.dart import DartWorkspace
from releasekit.backends.workspace.go import GoWorkspace
from releasekit.backends.workspace.maven import MavenWorkspace
from releasekit.backends.workspace.pnpm import PnpmWorkspace
from releasekit.errors import E, ReleaseKitError
from releasekit.logging import get_logger
from releasekit.utils.packaging import normalize_name as _normalize_name, parse_dep_name as _parse_dep_name

logger = get_logger(__name__)


# Re-exported from backends.workspace._types so all consumers can
# ``from releasekit.workspace import Package``.
__all__ = ['Package', 'discover_packages']


def _is_publishable(classifiers: list[str]) -> bool:
    """Check if any classifier indicates the package is private."""
    return not any('Private' in c and 'Do Not Upload' in c for c in classifiers)


def _expand_member_globs(
    workspace_root: Path,
    members: list[str],
    excludes: list[str],
) -> list[Path]:
    """Expand workspace member globs into concrete package directories.

    Args:
        workspace_root: The directory containing the root pyproject.toml.
        members: Glob patterns from ``[tool.uv.workspace].members``.
        excludes: Glob patterns from ``[tool.uv.workspace].exclude``.

    Returns:
        Sorted list of absolute paths to package directories (those
        containing a ``pyproject.toml``).
    """
    found: set[Path] = set()
    for pattern in members:
        for candidate in sorted(workspace_root.glob(str(pattern))):
            if candidate.is_dir() and (candidate / 'pyproject.toml').is_file():
                found.add(candidate.resolve())

    # Apply exclusions.
    excluded: set[Path] = set()
    for pattern in excludes:
        for candidate in sorted(workspace_root.glob(str(pattern))):
            excluded.add(candidate.resolve())

    result = sorted(found - excluded)
    logger.debug('expanded_member_globs', members=members, excludes=excludes, count=len(result))
    return result


def _parse_package(
    pkg_dir: Path,
    internal_names: frozenset[str],
    workspace_sourced: frozenset[str],
) -> Package:
    """Parse a single package's pyproject.toml.

    A dependency is classified as "internal" only if it satisfies BOTH:

    1. Its name is a workspace member (in ``internal_names``).
    2. It is resolved from the workspace source — i.e., listed with
       ``workspace = true`` in ``[tool.uv.sources]`` of the root
       ``pyproject.toml`` (in ``workspace_sourced``).

    If a workspace member pins to a PyPI version (e.g.
    ``genkit==1.0.0``) instead of using the workspace source, it is
    treated as an external dependency and excluded from the release
    graph. This lets packages opt out of version propagation.

    Args:
        pkg_dir: Path to the package directory.
        internal_names: Set of normalized package names in the workspace.
        workspace_sourced: Subset of ``internal_names`` that have
            ``workspace = true`` in ``[tool.uv.sources]``.

    Returns:
        A :class:`Package` dataclass.

    Raises:
        ReleaseKitError: If the pyproject.toml is malformed.
    """
    manifest_path = pkg_dir / 'pyproject.toml'
    try:
        text = manifest_path.read_text(encoding='utf-8')
    except OSError as exc:
        raise ReleaseKitError(
            code=E.WORKSPACE_PARSE_ERROR,
            message=f'Failed to read {manifest_path}: {exc}',
            hint=f'Check that {manifest_path} exists and is readable.',
        ) from exc

    try:
        doc = tomlkit.parse(text)
    except tomlkit.exceptions.TOMLKitError as exc:
        raise ReleaseKitError(
            code=E.WORKSPACE_PARSE_ERROR,
            message=f'Failed to parse {manifest_path}: {exc}',
            hint=f'Check that {manifest_path} contains valid TOML.',
        ) from exc

    project: dict[str, Any] = dict(doc.get('project', {}))  # noqa: ANN401
    name = project.get('name', '')
    if not name:
        raise ReleaseKitError(
            code=E.WORKSPACE_PARSE_ERROR,
            message=f'No [project].name in {manifest_path}',
            hint='Every workspace member must have a [project] section with a name.',
        )

    version = project.get('version', '0.0.0')
    classifiers: list[str] = list(project.get('classifiers', []))
    dep_specs: list[str] = list(project.get('dependencies', []))

    internal_deps: list[str] = []
    external_deps: list[str] = []
    for spec in dep_specs:
        dep_name = _normalize_name(_parse_dep_name(spec))
        # Internal iff the dep is both a workspace member AND
        # resolved from workspace source (not pinned to PyPI).
        if dep_name in internal_names and dep_name in workspace_sourced:
            internal_deps.append(dep_name)
        else:
            if dep_name in internal_names:
                # Workspace member but NOT workspace-sourced — pinned
                # to a specific version on PyPI. Excluded from the
                # release graph to avoid force-bumping.
                logger.info(
                    'dep_pinned_to_pypi',
                    package=_normalize_name(name),
                    dep=dep_name,
                    hint='Not in [tool.uv.sources] with workspace=true',
                )
            external_deps.append(dep_name)

    return Package(
        name=_normalize_name(name),
        version=version,
        path=pkg_dir.resolve(),
        manifest_path=manifest_path.resolve(),
        internal_deps=sorted(internal_deps),
        external_deps=sorted(external_deps),
        all_deps=[spec.strip() for spec in dep_specs],
        is_publishable=_is_publishable(classifiers),
    )


def _discover_js_packages(
    workspace_root: Path,
    *,
    exclude_patterns: list[str] | None = None,
) -> list[Package]:
    """Discover JS packages via :class:`PnpmWorkspace` (sync wrapper).

    Bridges the async ``PnpmWorkspace.discover()`` into the sync
    ``discover_packages()`` API by running it in a fresh event loop.
    The returned ``_types.Package`` objects are converted to the
    canonical :class:`Package` used throughout releasekit.
    """
    ws = PnpmWorkspace(workspace_root)

    async def _run() -> list[Package]:
        ws_pkgs = await ws.discover(exclude_patterns=exclude_patterns)
        return [
            Package(
                name=p.name,
                version=p.version,
                path=p.path,
                manifest_path=p.manifest_path,
                internal_deps=list(p.internal_deps),
                external_deps=list(p.external_deps),
                all_deps=list(p.all_deps),
                is_publishable=p.is_publishable,
            )
            for p in ws_pkgs
        ]

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        # Already inside an event loop — use a helper thread.
        # The Future.result() type is generic; we know _run() returns
        # list[Package] so the cast is safe.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            result: list[Package] = pool.submit(asyncio.run, _run()).result()  # type: ignore[arg-type]
            return result
    return asyncio.run(_run())


def _discover_via_backend(
    workspace_root: Path,
    ecosystem: str,
    *,
    exclude_patterns: list[str] | None = None,
) -> list[Package]:
    """Discover packages using a workspace backend (Go, Dart, Java, Rust).

    Creates the appropriate workspace backend and runs its async
    ``discover()`` method synchronously.

    Args:
        workspace_root: Path to the workspace root.
        ecosystem: One of ``"go"``, ``"dart"``, ``"java"``, ``"rust"``.
        exclude_patterns: Glob patterns to exclude packages by name.

    Returns:
        List of discovered packages.
    """
    _ws_type = (
        type[GoWorkspace]
        | type[DartWorkspace]
        | type[MavenWorkspace]
        | type[CargoWorkspace]
        | type[BazelWorkspace]
        | type[ClojureWorkspace]
    )
    backend_map: dict[str, _ws_type] = {
        'bazel': BazelWorkspace,
        'clojure': ClojureWorkspace,
        'dart': DartWorkspace,
        'go': GoWorkspace,
        'java': MavenWorkspace,
        'jvm': MavenWorkspace,
        'kotlin': MavenWorkspace,
        'rust': CargoWorkspace,
    }
    backend_cls = backend_map.get(ecosystem)
    if backend_cls is None:
        raise ReleaseKitError(
            code=E.WORKSPACE_NOT_FOUND,
            message=f'No workspace backend for ecosystem: {ecosystem}',
            hint=f"Supported ecosystems: python, js, go, dart, java, kotlin, rust. Got '{ecosystem}'.",
        )

    ws = backend_cls(workspace_root)

    async def _run() -> list[Package]:
        return await ws.discover(exclude_patterns=exclude_patterns)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            result: list[Package] = pool.submit(asyncio.run, _run()).result()  # type: ignore[arg-type]
            return result
    return asyncio.run(_run())


def discover_packages(
    workspace_root: Path,
    *,
    exclude_patterns: list[str] | None = None,
    ecosystem: str = 'python',
) -> list[Package]:
    """Discover all packages in a workspace.

    Dispatches to the appropriate workspace backend based on
    ``ecosystem``:

    - ``"python"`` (default): reads ``[tool.uv.workspace]`` from the
      root ``pyproject.toml``.
    - ``"js"``: reads ``pnpm-workspace.yaml`` and ``package.json``
      files via :class:`~releasekit.backends.workspace.pnpm.PnpmWorkspace`.
    - ``"go"``: reads ``go.work`` and ``go.mod`` files via
      :class:`~releasekit.backends.workspace.go.GoWorkspace`.
    - ``"dart"``: reads ``pubspec.yaml`` and ``melos.yaml`` via
      :class:`~releasekit.backends.workspace.dart.DartWorkspace`.
    - ``"java"``: reads ``pom.xml`` or ``settings.gradle`` via
      :class:`~releasekit.backends.workspace.maven.MavenWorkspace`.

    Args:
        workspace_root: Path to the workspace root directory.
        exclude_patterns: Additional glob patterns to exclude packages
            (on top of those in the workspace config).
        ecosystem: Ecosystem identifier.

    Returns:
        List of :class:`Package` objects, sorted by name.

    Raises:
        ReleaseKitError: If the workspace structure is invalid.
    """
    if ecosystem == 'js':
        return _discover_js_packages(workspace_root, exclude_patterns=exclude_patterns)

    if ecosystem in ('go', 'dart', 'java', 'jvm', 'kotlin', 'clojure', 'rust', 'bazel'):
        return _discover_via_backend(workspace_root, ecosystem, exclude_patterns=exclude_patterns)

    root_pyproject = workspace_root / 'pyproject.toml'
    if not root_pyproject.is_file():
        raise ReleaseKitError(
            code=E.WORKSPACE_NOT_FOUND,
            message=f'No pyproject.toml found at {workspace_root}',
            hint='Point to the directory containing your workspace pyproject.toml.',
        )

    try:
        text = root_pyproject.read_text(encoding='utf-8')
    except OSError as exc:
        raise ReleaseKitError(
            code=E.WORKSPACE_NOT_FOUND,
            message=f'Failed to read {root_pyproject}: {exc}',
            hint=f'Check that {root_pyproject} exists and is readable.',
        ) from exc

    try:
        doc = tomlkit.parse(text)
    except tomlkit.exceptions.TOMLKitError as exc:
        raise ReleaseKitError(
            code=E.WORKSPACE_NOT_FOUND,
            message=f'Failed to parse {root_pyproject}: {exc}',
            hint=f'Check that {root_pyproject} contains valid TOML.',
        ) from exc

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

    # Note: exclude_patterns are package *name* globs (e.g. "sample-*"),
    # not path globs. They are applied after package parsing (below),
    # not mixed into workspace path-based excludes.

    pkg_dirs = _expand_member_globs(workspace_root, members, excludes)
    if not pkg_dirs:
        raise ReleaseKitError(
            code=E.WORKSPACE_NO_MEMBERS,
            message=f'No packages found matching members={members}',
            hint='Check that your member globs match directories with pyproject.toml files.',
        )

    # First pass: collect all package names for internal dep classification.
    # We do a quick parse to get names before the full parse.
    all_names: set[str] = set()
    for pkg_dir in pkg_dirs:
        manifest_path = pkg_dir / 'pyproject.toml'
        try:
            quick_doc = tomlkit.parse(manifest_path.read_text(encoding='utf-8'))
            name = quick_doc.get('project', {}).get('name', '')
            if name:
                all_names.add(_normalize_name(name))
        except (tomlkit.exceptions.TOMLKitError, OSError):
            pass  # Will be caught in full parse.

    # Read [tool.uv.sources] to determine which deps use workspace paths.
    # Only deps with `workspace = true` are truly internal.
    uv_sources: dict[str, Any] = dict(uv_section.get('sources', {}))  # noqa: ANN401
    workspace_sourced: set[str] = set()
    for src_name, src_config in uv_sources.items():
        normalized = _normalize_name(src_name)
        if normalized in all_names:
            # Check if this source uses workspace resolution.
            if isinstance(src_config, dict) and src_config.get('workspace'):
                workspace_sourced.add(normalized)

    internal_names = frozenset(all_names)
    ws_sourced = frozenset(workspace_sourced)

    if workspace_sourced:
        logger.info(
            'workspace_sourced_deps',
            count=len(workspace_sourced),
            names=sorted(workspace_sourced),
        )

    pinned_members = all_names - workspace_sourced
    if pinned_members:
        logger.info(
            'pinned_to_pypi',
            count=len(pinned_members),
            names=sorted(pinned_members),
            hint='These workspace members are NOT in [tool.uv.sources] with '
            'workspace=true; they will be excluded from the release graph.',
        )

    # Second pass: full parse with dependency classification.
    packages: list[Package] = []
    seen_names: set[str] = set()
    for pkg_dir in pkg_dirs:
        pkg = _parse_package(pkg_dir, internal_names, ws_sourced)
        if pkg.name in seen_names:
            raise ReleaseKitError(
                code=E.WORKSPACE_DUPLICATE_PACKAGE,
                message=f"Duplicate package name '{pkg.name}' found at {pkg_dir}",
                hint='Each package in the workspace must have a unique name.',
            )
        seen_names.add(pkg.name)
        packages.append(pkg)

    # Apply releasekit exclude patterns.
    if exclude_patterns:
        packages = [p for p in packages if not any(fnmatch.fnmatch(p.name, pat) for pat in exclude_patterns)]

    result = sorted(packages, key=lambda p: p.name)
    logger.info('discovered_packages', count=len(result))
    return result


__all__ = [
    'Package',
    'discover_packages',
]
