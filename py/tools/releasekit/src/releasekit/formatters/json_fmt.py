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

"""JSON format output for dependency graphs.

Renders the dependency graph as machine-readable JSON with full
structure: nodes, edges, reverse edges, levels, and package metadata.
"""

from __future__ import annotations

import json

from releasekit.graph import DependencyGraph, topo_sort
from releasekit.workspace import Package


def format_json(
    graph: DependencyGraph,
    packages: list[Package],
    *,
    indent: int = 2,
) -> str:
    """Render the dependency graph as a JSON string.

    Args:
        graph: The dependency graph.
        packages: Package list for metadata.
        indent: JSON indentation level.

    Returns:
        A JSON string with full graph structure.
    """
    levels = topo_sort(graph)
    pkg_map = {p.name: p for p in packages}

    nodes: list[dict[str, object]] = []
    for name in graph.names:
        pkg = pkg_map.get(name)
        node: dict[str, object] = {'name': name}
        if pkg:
            node['version'] = pkg.version
            node['path'] = str(pkg.path)
        node['deps'] = sorted(graph.edges.get(name, []))
        node['rdeps'] = sorted(graph.reverse_edges.get(name, []))
        nodes.append(node)

    level_data: list[list[str]] = [sorted(p.name for p in level) for level in levels]

    data = {
        'packages': len(graph.names),
        'levels': len(levels),
        'nodes': nodes,
        'level_groups': level_data,
        'edges': {k: sorted(v) for k, v in sorted(graph.edges.items())},
        'reverse_edges': {k: sorted(v) for k, v in sorted(graph.reverse_edges.items())},
    }

    return json.dumps(data, indent=indent) + '\n'


__all__ = ['format_json']
