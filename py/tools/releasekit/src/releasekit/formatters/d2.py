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

"""D2 diagram language format output.

Renders the dependency graph in D2 format, a modern diagram language
with auto-layout. See https://d2lang.com/ for details.

Usage::

    d2 graph.d2 graph.svg
    d2 --watch graph.d2 graph.svg
"""

from __future__ import annotations

from releasekit.graph import DependencyGraph
from releasekit.workspace import Package


def format_d2(
    graph: DependencyGraph,
    packages: list[Package],
    *,
    direction: str = 'down',
    title: str = '',
) -> str:
    """Render the dependency graph as a D2 diagram.

    Args:
        graph: The dependency graph.
        packages: Package list for metadata.
        direction: Layout direction (``down``, ``right``, ``up``, ``left``).
        title: Optional diagram title.

    Returns:
        A D2 diagram string.
    """
    lines: list[str] = []

    lines.append(f'direction: {direction}')
    lines.append('')

    if title:
        lines.append(f'title: {title} {{')
        lines.append('  shape: text')
        lines.append('  near: top-center')
        lines.append('}')
        lines.append('')

    # Node declarations.
    pkg_map = {p.name: p for p in packages}
    for name in graph.names:
        node_id = _sanitize_id(name)
        pkg = pkg_map.get(name)
        version = pkg.version if pkg else ''
        if version:
            lines.append(f'{node_id}: "{name}\\n{version}" {{')
        else:
            lines.append(f'{node_id}: "{name}" {{')
        lines.append('  shape: rectangle')
        lines.append('}')

    lines.append('')

    # Edges (dependent → dependency).
    for dependent, deps in sorted(graph.edges.items()):
        dep_id = _sanitize_id(dependent)
        for dep in sorted(deps):
            lines.append(f'{dep_id} -> {_sanitize_id(dep)}')

    return '\n'.join(lines) + '\n'


def _sanitize_id(name: str) -> str:
    """Convert a package name to a valid D2 identifier."""
    return name.replace('-', '_').replace('.', '_')


__all__ = ['format_d2']
