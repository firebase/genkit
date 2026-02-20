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

"""Simple level-grouped text output.

Renders the dependency graph as a minimal text listing grouped by
topological level. This is the default ``releasekit graph`` format.

Example output::

    Level 0: genkit
    Level 1: genkit-plugin-google-genai, genkit-plugin-vertex-ai
    Level 2: provider-google-genai-hello
"""

from __future__ import annotations

from releasekit.graph import DependencyGraph, topo_sort
from releasekit.workspace import Package


def format_levels(
    graph: DependencyGraph,
    packages: list[Package],
    *,
    show_version: bool = False,
) -> str:
    """Render the dependency graph as a level-grouped text listing.

    Args:
        graph: The dependency graph.
        packages: Package list for metadata.
        show_version: Append version to each package name.

    Returns:
        A simple text listing.
    """
    levels = topo_sort(graph)
    pkg_map = {p.name: p for p in packages}

    lines: list[str] = []
    for level_idx, level in enumerate(levels):
        names: list[str] = []
        for pkg in level:
            if show_version:
                p = pkg_map.get(pkg.name, pkg)
                names.append(f'{pkg.name} ({p.version})')
            else:
                names.append(pkg.name)
        lines.append(f'  Level {level_idx}: {", ".join(names)}')

    return '\n'.join(lines) + '\n'


__all__ = ['format_levels']
