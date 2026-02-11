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
    │                         │ this same workspace. We control it.       │
    ├─────────────────────────┼────────────────────────────────────────────┤
    │ External dep            │ A dependency from PyPI (requests, httpx). │
    │                         │ We don't control its release.             │
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

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomlkit
import tomlkit.exceptions
from packaging.requirements import InvalidRequirement, Requirement

from releasekit.errors import E, ReleaseKitError
from releasekit.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class Package:
    """A single package discovered in the workspace.

    Attributes:
        name: The package name from ``[project].name`` (e.g. ``"genkit"``).
        version: The version string from ``[project].version``.
        path: Absolute path to the package directory.
        pyproject_path: Absolute path to the package's ``pyproject.toml``.
        internal_deps: Names of workspace packages this package depends on.
        external_deps: Names of external (PyPI) packages this package depends on.
        all_deps: All dependency specifiers as raw strings.
        is_publishable: Whether this package should be published to PyPI.
            Packages with ``Private :: Do Not Upload`` classifier are not.
    """

    name: str
    version: str
    path: Path
    pyproject_path: Path
    internal_deps: list[str] = field(default_factory=list)
    external_deps: list[str] = field(default_factory=list)
    all_deps: list[str] = field(default_factory=list)
    is_publishable: bool = True


def _parse_dep_name(dep_spec: str) -> str:
    """Extract the normalized package name from a PEP 508 dependency specifier.

    Uses the ``packaging`` library for robust parsing of all valid PEP 508
    forms including extras, version specifiers, and environment markers.
    Falls back to basic string splitting if parsing fails.
    """
    try:
        return Requirement(dep_spec).name.lower()
    except InvalidRequirement:
        # Fallback for malformed specifiers: split at first specifier char.
        name = re.split(r'[<>=!~,;\[]', dep_spec, maxsplit=1)[0].strip()
        return name.lower()


def _normalize_name(name: str) -> str:
    """Normalize a package name per PEP 503 (lowercase, hyphens to hyphens)."""
    return name.lower().replace('_', '-')


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
        for candidate in sorted(workspace_root.glob(pattern)):
            if candidate.is_dir() and (candidate / 'pyproject.toml').is_file():
                found.add(candidate.resolve())

    # Apply exclusions.
    excluded: set[Path] = set()
    for pattern in excludes:
        for candidate in sorted(workspace_root.glob(pattern)):
            excluded.add(candidate.resolve())

    result = sorted(found - excluded)
    logger.debug('expanded_member_globs', members=members, excludes=excludes, count=len(result))
    return result


def _parse_package(pkg_dir: Path, internal_names: frozenset[str]) -> Package:
    """Parse a single package's pyproject.toml.

    Args:
        pkg_dir: Path to the package directory.
        internal_names: Set of normalized package names in the workspace.

    Returns:
        A :class:`Package` dataclass.

    Raises:
        ReleaseKitError: If the pyproject.toml is malformed.
    """
    pyproject_path = pkg_dir / 'pyproject.toml'
    try:
        text = pyproject_path.read_text(encoding='utf-8')
    except OSError as exc:
        raise ReleaseKitError(
            code=E.WORKSPACE_PARSE_ERROR,
            message=f'Failed to read {pyproject_path}: {exc}',
        ) from exc

    try:
        doc = tomlkit.parse(text)
    except tomlkit.exceptions.TOMLKitError as exc:
        raise ReleaseKitError(
            code=E.WORKSPACE_PARSE_ERROR,
            message=f'Failed to parse {pyproject_path}: {exc}',
        ) from exc

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
        if dep_name in internal_names:
            internal_deps.append(dep_name)
        else:
            external_deps.append(dep_name)

    return Package(
        name=_normalize_name(name),
        version=version,
        path=pkg_dir.resolve(),
        pyproject_path=pyproject_path.resolve(),
        internal_deps=sorted(internal_deps),
        external_deps=sorted(external_deps),
        all_deps=[spec.strip() for spec in dep_specs],
        is_publishable=_is_publishable(classifiers),
    )


def discover_packages(
    workspace_root: Path,
    *,
    exclude_patterns: list[str] | None = None,
) -> list[Package]:
    """Discover all packages in a uv workspace.

    Reads ``[tool.uv.workspace]`` from the root ``pyproject.toml``,
    expands member globs, parses each member, and classifies dependencies
    as internal (within workspace) or external (PyPI).

    Args:
        workspace_root: Path to the workspace root directory (containing
            the root ``pyproject.toml``).
        exclude_patterns: Additional glob patterns to exclude packages
            (on top of those in ``[tool.uv.workspace].exclude``).

    Returns:
        List of :class:`Package` objects, sorted by name.

    Raises:
        ReleaseKitError: If the workspace structure is invalid.
    """
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
        ) from exc

    try:
        doc = tomlkit.parse(text)
    except tomlkit.exceptions.TOMLKitError as exc:
        raise ReleaseKitError(
            code=E.WORKSPACE_NOT_FOUND,
            message=f'Failed to parse {root_pyproject}: {exc}',
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
        pyproject_path = pkg_dir / 'pyproject.toml'
        try:
            quick_doc = tomlkit.parse(pyproject_path.read_text(encoding='utf-8'))
            name = quick_doc.get('project', {}).get('name', '')
            if name:
                all_names.add(_normalize_name(name))
        except (tomlkit.exceptions.TOMLKitError, OSError):
            pass  # Will be caught in full parse.

    internal_names = frozenset(all_names)

    # Second pass: full parse with dependency classification.
    packages: list[Package] = []
    seen_names: set[str] = set()
    for pkg_dir in pkg_dirs:
        pkg = _parse_package(pkg_dir, internal_names)
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
