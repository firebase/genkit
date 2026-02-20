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

"""Markdown-style table output.

Renders the dependency graph as a table with columns for level, package
name, version, and internal dependencies.

Example output::

    | Level | Package                       | Version | Dependencies            |
    |-------|-------------------------------|---------|-------------------------|
    | 0     | genkit                        | 0.5.0   |                         |
    | 1     | genkit-plugin-google-genai    | 0.5.0   | genkit                  |
    | 1     | genkit-plugin-vertex-ai       | 0.5.0   | genkit                  |
    | 2     | provider-google-genai-hello   | 0.1.0   | genkit, genkit-plugin-… |
"""

from __future__ import annotations

from releasekit.graph import DependencyGraph, topo_sort
from releasekit.workspace import Package


def _pad(text: str, width: int) -> str:
    """Left-align text, padded to the given width."""
    return text + ' ' * max(0, width - len(text))


def format_table(
    graph: DependencyGraph,
    packages: list[Package],
    *,
    show_version: bool = True,
) -> str:
    """Render the dependency graph as a Markdown-style table.

    Args:
        graph: The dependency graph.
        packages: Package list for metadata.
        show_version: Include a version column (default ``True``).

    Returns:
        A Markdown table string.
    """
    levels = topo_sort(graph)
    pkg_map = {p.name: p for p in packages}

    rows: list[tuple[str, str, str, str]] = []
    for level_idx, level in enumerate(levels):
        for pkg in level:
            p = pkg_map.get(pkg.name, pkg)
            deps = ', '.join(sorted(graph.edges.get(pkg.name, [])))
            rows.append((str(level_idx), pkg.name, p.version, deps))

    if not rows:
        return '(empty graph)\n'

    col_level = max(len('Level'), max(len(r[0]) for r in rows))
    col_pkg = max(len('Package'), max(len(r[1]) for r in rows))
    col_deps = max(len('Dependencies'), max(len(r[3]) for r in rows))

    if show_version:
        col_ver = max(len('Version'), max(len(r[2]) for r in rows))
        header = (
            f'| {_pad("Level", col_level)} '
            f'| {_pad("Package", col_pkg)} '
            f'| {_pad("Version", col_ver)} '
            f'| {_pad("Dependencies", col_deps)} |'
        )
        separator = f'|{"-" * (col_level + 2)}|{"-" * (col_pkg + 2)}|{"-" * (col_ver + 2)}|{"-" * (col_deps + 2)}|'
        lines = [header, separator]
        for lvl, name, ver, deps in rows:
            lines.append(
                f'| {_pad(lvl, col_level)} | {_pad(name, col_pkg)} | {_pad(ver, col_ver)} | {_pad(deps, col_deps)} |',
            )
    else:
        header = f'| {_pad("Level", col_level)} | {_pad("Package", col_pkg)} | {_pad("Dependencies", col_deps)} |'
        separator = f'|{"-" * (col_level + 2)}|{"-" * (col_pkg + 2)}|{"-" * (col_deps + 2)}|'
        lines = [header, separator]
        for lvl, name, _ver, deps in rows:
            lines.append(
                f'| {_pad(lvl, col_level)} | {_pad(name, col_pkg)} | {_pad(deps, col_deps)} |',
            )

    return '\n'.join(lines) + '\n'


__all__ = ['format_table']
