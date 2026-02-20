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

"""Graphviz DOT format output.

Renders the dependency graph as a DOT digraph suitable for Graphviz
tools (``dot``, ``neato``, ``fdp``).

Usage::

    dot -Tsvg graph.dot -o graph.svg
    dot -Tpng graph.dot -o graph.png
"""

from __future__ import annotations

from releasekit.graph import DependencyGraph
from releasekit.workspace import Package


def format_dot(
    graph: DependencyGraph,
    packages: list[Package],
    *,
    rankdir: str = 'TB',
    label: str = '',
) -> str:
    """Render the dependency graph as a Graphviz DOT string.

    Args:
        graph: The dependency graph.
        packages: Package list for metadata (used for display names).
        rankdir: Graph direction (``TB``, ``LR``, ``BT``, ``RL``).
        label: Optional graph title.

    Returns:
        A DOT language string.
    """
    lines: list[str] = []
    lines.append('digraph dependencies {')
    lines.append(f'  rankdir={rankdir};')
    lines.append('  node [shape=box, style=rounded, fontname="Inter"];')
    lines.append('  edge [color="#666666"];')

    if label:
        lines.append(f'  label="{label}";')
        lines.append('  labelloc=t;')

    lines.append('')

    # Node declarations.
    pkg_map = {p.name: p for p in packages}
    for name in graph.names:
        pkg = pkg_map.get(name)
        version = pkg.version if pkg else ''
        node_label = f'{name}\\n{version}' if version else name
        node_id = _sanitize_id(name)
        lines.append(f'  {node_id} [label="{node_label}"];')

    lines.append('')

    # Edges (dependent → dependency).
    for dependent, deps in sorted(graph.edges.items()):
        for dep in sorted(deps):
            lines.append(f'  {_sanitize_id(dependent)} -> {_sanitize_id(dep)};')

    lines.append('}')
    return '\n'.join(lines) + '\n'


def _sanitize_id(name: str) -> str:
    """Convert a package name to a valid DOT node ID."""
    return f'"{name}"'


__all__ = ['format_dot']
