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

"""Mermaid flowchart format output.

Renders the dependency graph as a Mermaid flowchart that renders
natively on GitHub, GitLab, and documentation sites.

Usage (in markdown)::

    ```mermaid
    flowchart TD
        genkit --> genkit-plugin-foo
    ```
"""

from __future__ import annotations

from releasekit.graph import DependencyGraph
from releasekit.workspace import Package


def format_mermaid(
    graph: DependencyGraph,
    packages: list[Package],
    *,
    direction: str = 'TD',
    title: str = '',
) -> str:
    """Render the dependency graph as a Mermaid flowchart.

    Args:
        graph: The dependency graph.
        packages: Package list for metadata.
        direction: Flow direction (``TD``, ``LR``, ``BT``, ``RL``).
        title: Optional diagram title (rendered as a comment).

    Returns:
        A Mermaid flowchart string.
    """
    lines: list[str] = []

    if title:
        lines.append('---')
        lines.append(f'title: {title}')
        lines.append('---')

    lines.append(f'flowchart {direction}')

    # Node declarations with labels.
    pkg_map = {p.name: p for p in packages}
    for name in graph.names:
        node_id = _sanitize_id(name)
        pkg = pkg_map.get(name)
        version = pkg.version if pkg else ''
        if version:
            lines.append(f'    {node_id}["{name}<br/><small>{version}</small>"]')
        else:
            lines.append(f'    {node_id}["{name}"]')

    lines.append('')

    # Edges (dependent → dependency).
    for dependent, deps in sorted(graph.edges.items()):
        dep_id = _sanitize_id(dependent)
        for dep in sorted(deps):
            lines.append(f'    {dep_id} --> {_sanitize_id(dep)}')

    return '\n'.join(lines) + '\n'


def _sanitize_id(name: str) -> str:
    """Convert a package name to a valid Mermaid node ID.

    Mermaid IDs cannot contain hyphens, so we replace them with
    underscores.
    """
    return name.replace('-', '_').replace('.', '_')


__all__ = ['format_mermaid']
