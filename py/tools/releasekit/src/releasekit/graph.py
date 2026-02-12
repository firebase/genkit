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

"""Dependency graph operations for workspace packages.

Builds a directed acyclic graph (DAG) from workspace packages, detects
cycles, and computes topological sort with level grouping for parallel
publication.

Key Concepts (ELI5)::

    ┌─────────────────────────┬─────────────────────────────────────────────┐
    │ Concept                 │ ELI5 Explanation                            │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Dependency graph        │ A map of "who needs what". If package A    │
    │                         │ depends on B, draw an arrow A → B.         │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Topological sort        │ An ordering where every package comes      │
    │                         │ after all its dependencies. Like making    │
    │                         │ sure you bake the cake before frosting it. │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Levels                  │ Groups of packages that can be published   │
    │                         │ at the same time (no deps between them).   │
    │                         │ Level 0 = no internal deps, level 1 =     │
    │                         │ depends only on level 0 packages, etc.    │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Cycle detection         │ Finding circular dependencies (A→B→C→A).  │
    │                         │ These make publishing impossible — you     │
    │                         │ can't publish A before B and B before A.  │
    └─────────────────────────┴─────────────────────────────────────────────┘

Architecture — Edge Direction::

    Forward edges (``edges``): dependent → dependency (who needs what)
    Reverse edges (``reverse_edges``): dependency → dependent (who uses me)

    genkit-plugin-foo ──→ genkit ←── genkit-plugin-bar
         (depends on)        (depended on by)

    edges["genkit-plugin-foo"] = ["genkit"]
    reverse_edges["genkit"] = ["genkit-plugin-foo", "genkit-plugin-bar"]

Data Flow — From Discovery to Publish Order::

    discover_packages()          build_graph()           topo_sort()
    ┌──────────────────┐    ┌────────────────────┐    ┌───────────────┐
    │ Walk workspace,  │    │ Build adjacency    │    │ Kahn's algo:  │
    │ parse pyproject, │───→│ lists (forward +   │───→│ group by      │
    │ classify deps    │    │ reverse edges)     │    │ publish level │
    └──────────────────┘    └────────────────────┘    └───────────────┘
          │                        │                        │
    list[Package]          DependencyGraph          list[list[Package]]

Topological Levels — Publish Order::

    Level 0 (no deps):    [genkit]
    Level 1 (deps on L0): [genkit-plugin-foo, genkit-plugin-bar, ...]
    Level 2 (deps on L1): [sample-app]

    Packages in the same level can be published in parallel.
    Each level must complete before the next starts.

Usage::

    from releasekit.graph import build_graph, topo_sort, detect_cycles
    from releasekit.workspace import discover_packages

    packages = discover_packages(Path('.'))
    graph = build_graph(packages)
    levels = topo_sort(graph)
    for level_num, level_pkgs in enumerate(levels):
        print(f'Level {level_num}: {[p.name for p in level_pkgs]}')
"""

from __future__ import annotations

import fnmatch
from collections import deque
from dataclasses import dataclass, field

from releasekit.errors import E, ReleaseKitError
from releasekit.logging import get_logger
from releasekit.workspace import Package

logger = get_logger(__name__)


@dataclass
class DependencyGraph:
    """A directed graph of workspace package dependencies.

    Edges point from dependents to their dependencies: if ``A`` depends
    on ``B``, there is an edge ``A → B`` in :attr:`edges` and a reverse
    edge ``B → A`` in :attr:`reverse_edges`.

    Attributes:
        packages: Mapping from package name to :class:`Package`.
        edges: Forward adjacency list (dependent → list of dependencies).
        reverse_edges: Reverse adjacency list (dependency → list of dependents).
    """

    packages: dict[str, Package] = field(default_factory=dict)
    edges: dict[str, list[str]] = field(default_factory=dict)
    reverse_edges: dict[str, list[str]] = field(default_factory=dict)

    @property
    def names(self) -> list[str]:
        """Sorted list of all package names in the graph."""
        return sorted(self.packages)

    def __len__(self) -> int:
        """Return the number of packages in the graph."""
        return len(self.packages)


def build_graph(packages: list[Package]) -> DependencyGraph:
    """Build a dependency graph from a list of workspace packages.

    Only internal dependencies (those within the workspace) are included
    as edges. External (PyPI) dependencies are ignored.

    Args:
        packages: List of :class:`Package` objects from
            :func:`~releasekit.workspace.discover_packages`.

    Returns:
        A :class:`DependencyGraph` with forward and reverse edges.
    """
    graph = DependencyGraph()
    pkg_names: set[str] = {p.name for p in packages}

    for pkg in packages:
        graph.packages[pkg.name] = pkg
        graph.edges[pkg.name] = []
        graph.reverse_edges[pkg.name] = []

    for pkg in packages:
        for dep_name in pkg.internal_deps:
            if dep_name in pkg_names:
                graph.edges[pkg.name].append(dep_name)
                graph.reverse_edges[dep_name].append(pkg.name)

    # Sort for deterministic output.
    for name in graph.edges:
        graph.edges[name].sort()
    for name in graph.reverse_edges:
        graph.reverse_edges[name].sort()

    logger.debug(
        'built_dependency_graph',
        packages=len(packages),
        edges=sum(len(deps) for deps in graph.edges.values()),
    )
    return graph


def detect_cycles(graph: DependencyGraph) -> list[list[str]]:
    """Detect all cycles in the dependency graph using DFS.

    A cycle means packages have circular dependencies (A→B→C→A), which
    makes topological sorting — and therefore ordered publishing —
    impossible.

    Args:
        graph: The dependency graph to check.

    Returns:
        A list of cycles, where each cycle is a list of package names
        forming the loop. Empty list if acyclic.
    """
    _white, _gray, _black = 0, 1, 2
    color: dict[str, int] = {name: _white for name in graph.packages}
    parent: dict[str, str | None] = {name: None for name in graph.packages}
    cycles: list[list[str]] = []

    def _dfs(node: str) -> None:
        color[node] = _gray
        for neighbor in graph.edges.get(node, []):
            if color[neighbor] == _gray:
                # Back edge found a cycle. Reconstruct it.
                cycle = [neighbor]
                current = node
                while current != neighbor:
                    cycle.append(current)
                    p = parent.get(current)
                    if p is None:
                        break
                    current = p
                cycle.append(neighbor)
                cycle.reverse()
                cycles.append(cycle)
            elif color[neighbor] == _white:
                parent[neighbor] = node
                _dfs(neighbor)
        color[node] = _black  # pyrefly: ignore[unbound-name] - closure variable from enclosing scope

    for name in sorted(graph.packages):
        if color[name] == _white:
            _dfs(name)

    if cycles:
        logger.warning('cycles_detected', count=len(cycles))
    else:
        logger.debug('no_cycles_detected')
    return cycles


def topo_sort(graph: DependencyGraph) -> list[list[Package]]:
    """Topological sort with level grouping (Kahn's algorithm).

    Returns packages grouped by "level": level 0 contains all packages
    with no internal dependencies, level 1 contains packages that depend
    only on level 0 packages, etc. Packages in the same level can be
    published in parallel.

    Args:
        graph: The dependency graph. Must be acyclic.

    Returns:
        A list of levels, where each level is a sorted list of
        :class:`Package` objects.

    Raises:
        ReleaseKitError: If the graph contains cycles.
    """
    # In-degree = number of dependencies. edges[A] = [B, C] means A
    # depends on B and C, so A's in-degree is 2 (B and C must be
    # published before A).
    in_degree = {name: len(graph.edges[name]) for name in graph.packages}

    queue: deque[str] = deque()
    for name in sorted(graph.packages):
        if in_degree[name] == 0:
            queue.append(name)

    levels: list[list[Package]] = []
    processed = 0

    while queue:
        # All nodes currently in the queue are at the same level.
        level_names = sorted(queue)
        queue.clear()
        level_packages = [graph.packages[name] for name in level_names]
        levels.append(level_packages)
        processed += len(level_names)

        for name in level_names:
            # For each dependent of this package (reverse edges),
            # decrease their in-degree.
            for dependent in graph.reverse_edges.get(name, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

    if processed != len(graph.packages):
        cycles = detect_cycles(graph)
        cycle_strs = [' → '.join(c) for c in cycles]
        raise ReleaseKitError(
            code=E.GRAPH_CYCLE_DETECTED,
            message=f'Circular dependencies detected: {cycle_strs}',
            hint='Remove circular dependencies between packages.',
        )

    logger.info('topo_sort_complete', levels=len(levels), packages=processed)
    return levels


def forward_deps(graph: DependencyGraph, name: str) -> set[str]:
    """Return all transitive dependencies of a package (BFS).

    If A depends on B, and B depends on C, then ``forward_deps("A")``
    returns ``{"B", "C"}``.

    Args:
        graph: The dependency graph.
        name: The package name to start from.

    Returns:
        Set of all transitive dependency names (not including ``name``).
    """
    visited: set[str] = set()
    queue: deque[str] = deque(graph.edges.get(name, []))
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        queue.extend(graph.edges.get(current, []))
    return visited


def reverse_deps(graph: DependencyGraph, name: str) -> set[str]:
    """Return all transitive dependents of a package (BFS).

    If B depends on A, and C depends on B, then ``reverse_deps("A")``
    returns ``{"B", "C"}``.

    Args:
        graph: The dependency graph.
        name: The package name to start from.

    Returns:
        Set of all transitive dependent names (not including ``name``).
    """
    visited: set[str] = set()
    queue: deque[str] = deque(graph.reverse_edges.get(name, []))
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        queue.extend(graph.reverse_edges.get(current, []))
    return visited


def filter_graph(
    graph: DependencyGraph,
    *,
    include_packages: list[str] | None = None,
    exclude_packages: list[str] | None = None,
    include_groups: dict[str, list[str]] | None = None,
    group_name: str | None = None,
) -> DependencyGraph:
    """Filter the graph to a subset of packages.

    When including specific packages, their transitive dependencies are
    automatically included (you can't publish A without first publishing
    its dep B).

    Args:
        graph: The full dependency graph.
        include_packages: Only include these packages (and their deps).
        exclude_packages: Exclude these packages (glob patterns).
        include_groups: Group definitions from config.
        group_name: Include only packages in this group.

    Returns:
        A new :class:`DependencyGraph` containing only the selected packages.
    """
    # Start with all packages.
    selected: set[str] = set(graph.packages)

    # Apply group filter.
    if group_name is not None and include_groups:
        if group_name not in include_groups:
            raise ReleaseKitError(
                code=E.CONFIG_INVALID_VALUE,
                message=f"Unknown group '{group_name}'",
                hint=f'Available groups: {sorted(include_groups)}',
            )
        patterns = include_groups[group_name]
        selected = {name for name in graph.packages if any(fnmatch.fnmatch(name, pat) for pat in patterns)}

    # Apply explicit include (with transitive deps).
    if include_packages:
        explicit = set()
        for name in include_packages:
            if name in graph.packages:
                explicit.add(name)
                explicit |= forward_deps(graph, name)
        selected &= explicit

    # Apply excludes.
    if exclude_packages:
        selected = {name for name in selected if not any(fnmatch.fnmatch(name, pat) for pat in exclude_packages)}

    # Build filtered graph.
    filtered_packages = [graph.packages[name] for name in sorted(selected)]
    return build_graph(filtered_packages)


__all__ = [
    'DependencyGraph',
    'build_graph',
    'detect_cycles',
    'filter_graph',
    'forward_deps',
    'reverse_deps',
    'topo_sort',
]
