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

"""Parse lockfiles to extract transitive dependency graphs.

Supports ``uv.lock`` (TOML format with ``[[package]]`` sections).
Each package entry lists its direct dependencies, which allows us to
reconstruct the full transitive closure for any given root package.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Lockfile            │ A snapshot of every package version and its    │
    │                     │ dependencies, frozen at a point in time.       │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Transitive dep      │ If A needs B and B needs C, then C is a       │
    │                     │ transitive dependency of A.                    │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Closure             │ The full set of all transitive deps — every    │
    │                     │ package that ends up installed.                │
    └─────────────────────┴────────────────────────────────────────────────┘

Usage::

    from releasekit.checks._lockfile import parse_uv_lock, transitive_deps

    lock = parse_uv_lock(Path('uv.lock'))
    all_deps = transitive_deps(lock, 'genkit')
    # → {'pydantic', 'pydantic-core', 'typing-extensions', ...}
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from releasekit.logging import get_logger
from releasekit.utils.packaging import normalize_name as _normalize_name

logger = get_logger(__name__)


@dataclass(frozen=True)
class LockEntry:
    """A single package entry from a lockfile.

    Attributes:
        name: Normalized package name.
        version: Version string.
        deps: Direct dependency names (normalized).
        is_workspace: Whether this is a workspace member (editable).
    """

    name: str
    version: str
    deps: tuple[str, ...] = ()
    is_workspace: bool = False


@dataclass
class LockGraph:
    """Parsed lockfile as a dependency graph.

    Attributes:
        entries: Map of normalized name → :class:`LockEntry`.
        workspace_members: Set of normalized names that are workspace members.
    """

    entries: dict[str, LockEntry] = field(default_factory=dict)
    workspace_members: set[str] = field(default_factory=set)


def parse_uv_lock(lock_path: Path) -> LockGraph:
    """Parse a ``uv.lock`` file into a :class:`LockGraph`.

    The ``uv.lock`` file is TOML with repeated ``[[package]]`` sections.
    Each section has:

    - ``name`` — package name
    - ``version`` — version string
    - ``source`` — ``{ registry = "..." }`` for external,
      ``{ editable = "..." }`` for workspace members
    - ``dependencies`` — list of ``{ name = "..." }`` tables

    Args:
        lock_path: Path to the ``uv.lock`` file.

    Returns:
        A :class:`LockGraph` with all entries and workspace members.
    """
    import sys  # noqa: PLC0415

    if sys.version_info >= (3, 11):
        import tomllib  # noqa: PLC0415
    else:
        import tomli as tomllib  # noqa: PLC0415

    if not lock_path.is_file():
        logger.debug('uv_lock_not_found', path=str(lock_path))
        return LockGraph()

    try:
        text = lock_path.read_bytes()
        data = tomllib.loads(text.decode('utf-8'))
    except Exception as exc:  # noqa: BLE001
        logger.warning('uv_lock_parse_error', path=str(lock_path), error=str(exc))
        return LockGraph()

    graph = LockGraph()
    packages: list[dict[str, Any]] = data.get('package', [])

    for pkg_raw in packages:
        name = _normalize_name(pkg_raw.get('name', ''))
        if not name:
            continue

        version = pkg_raw.get('version', '')

        # Detect workspace members by checking for editable source.
        source = pkg_raw.get('source', {})
        is_workspace = bool(source.get('editable', '')) if isinstance(source, dict) else False

        # Parse direct dependencies.
        raw_deps: list[dict[str, Any]] = pkg_raw.get('dependencies', [])
        dep_names: list[str] = []
        for dep_entry in raw_deps:
            if isinstance(dep_entry, dict):
                dep_name = _normalize_name(dep_entry.get('name', ''))
                if dep_name:
                    dep_names.append(dep_name)

        entry = LockEntry(
            name=name,
            version=version,
            deps=tuple(sorted(set(dep_names))),
            is_workspace=is_workspace,
        )
        graph.entries[name] = entry

        if is_workspace:
            graph.workspace_members.add(name)

    logger.debug(
        'parsed_uv_lock',
        total=len(graph.entries),
        workspace=len(graph.workspace_members),
        external=len(graph.entries) - len(graph.workspace_members),
    )
    return graph


def transitive_deps(
    graph: LockGraph,
    root_name: str,
    *,
    include_workspace: bool = False,
) -> set[str]:
    """Compute the transitive closure of dependencies for *root_name*.

    BFS from *root_name* through the lockfile dependency graph.

    Args:
        graph: Parsed lockfile graph.
        root_name: Starting package name (normalized).
        include_workspace: If ``False`` (default), workspace members
            are traversed but not included in the result set. This
            gives you only external transitive deps.

    Returns:
        Set of normalized package names that *root_name* transitively
        depends on (not including *root_name* itself).
    """
    root = _normalize_name(root_name)
    visited: set[str] = set()
    queue: deque[str] = deque()

    # Seed with root's direct deps.
    entry = graph.entries.get(root)
    if entry is None:
        return set()

    queue.extend(entry.deps)

    while queue:
        current = queue.popleft()
        if current in visited or current == root:
            continue
        visited.add(current)

        current_entry = graph.entries.get(current)
        if current_entry is not None:
            queue.extend(current_entry.deps)

    if not include_workspace:
        visited -= graph.workspace_members

    return visited


def all_transitive_external_deps(
    graph: LockGraph,
    package_names: set[str],
) -> set[str]:
    """Collect all transitive external deps for a set of packages.

    Convenience wrapper that unions :func:`transitive_deps` for each
    package in *package_names*.

    Args:
        graph: Parsed lockfile graph.
        package_names: Set of package names to compute closures for.

    Returns:
        Union of all transitive external dependencies.
    """
    result: set[str] = set()
    for name in package_names:
        result |= transitive_deps(graph, name)
    return result
