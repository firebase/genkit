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

"""ASCII art format output using box-drawing characters.

Renders the dependency graph as a terminal-friendly ASCII diagram
grouped by topological level. No external dependencies required.

Example output::

    ┌─────────────────────────────────────────────┐
    │ Level 0                                     │
    │   genkit (0.5.0)                            │
    ├─────────────────────────────────────────────┤
    │ Level 1                                     │
    │   genkit-plugin-google-genai (0.5.0)        │
    │   genkit-plugin-vertex-ai (0.5.0)           │
    ├─────────────────────────────────────────────┤
    │ Level 2                                     │
    │   provider-google-genai-hello (0.1.0)       │
    └─────────────────────────────────────────────┘
"""

from __future__ import annotations

from releasekit.graph import DependencyGraph, topo_sort
from releasekit.workspace import Package


def format_ascii(
    graph: DependencyGraph,
    packages: list[Package],
    *,
    show_deps: bool = False,
    min_width: int = 50,
) -> str:
    """Render the dependency graph as an ASCII art diagram.

    Args:
        graph: The dependency graph.
        packages: Package list for metadata.
        show_deps: Show dependency arrows below each package.
        min_width: Minimum box width.

    Returns:
        A string with box-drawing characters.
    """
    levels = topo_sort(graph)
    pkg_map = {p.name: p for p in packages}

    # Compute box width from longest line.
    max_name_len = 0
    for level in levels:
        for pkg in level:
            version = pkg_map.get(pkg.name, pkg).version
            line = f'  {pkg.name} ({version})' if version else f'  {pkg.name}'
            max_name_len = max(max_name_len, len(line))

    # Add deps lines if enabled.
    if show_deps:
        for _name, deps in graph.edges.items():
            if deps:
                dep_line = f'    → {", ".join(sorted(deps))}'
                max_name_len = max(max_name_len, len(dep_line))

    width = max(min_width, max_name_len + 4)

    lines: list[str] = []

    for level_idx, level in enumerate(levels):
        if level_idx == 0:
            lines.append(f'┌{"─" * width}┐')
        else:
            lines.append(f'├{"─" * width}┤')

        header = f'│ Level {level_idx}'
        lines.append(f'{header}{" " * (width - len(header) + 1)}│')

        for pkg in level:
            version = pkg_map.get(pkg.name, pkg).version
            if version:
                content = f'│   {pkg.name} ({version})'
            else:
                content = f'│   {pkg.name}'
            lines.append(f'{content}{" " * (width - len(content) + 1)}│')

            if show_deps:
                deps = graph.edges.get(pkg.name, [])
                if deps:
                    dep_line = f'│     → {", ".join(sorted(deps))}'
                    lines.append(f'{dep_line}{" " * (width - len(dep_line) + 1)}│')

    lines.append(f'└{"─" * width}┘')

    return '\n'.join(lines) + '\n'


__all__ = ['format_ascii']
