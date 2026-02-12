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

"""Formatter registry and dispatch.

Maps format names to their formatter functions, providing a single
``format_graph()`` entry point for the CLI.
"""

from __future__ import annotations

from collections.abc import Callable

from releasekit.formatters.ascii_art import format_ascii
from releasekit.formatters.csv_fmt import format_csv
from releasekit.formatters.d2 import format_d2
from releasekit.formatters.dot import format_dot
from releasekit.formatters.json_fmt import format_json
from releasekit.formatters.levels import format_levels
from releasekit.formatters.mermaid import format_mermaid
from releasekit.formatters.table import format_table
from releasekit.graph import DependencyGraph
from releasekit.workspace import Package

Formatter = Callable[..., str]

FORMATTERS: dict[str, Formatter] = {
    'ascii': format_ascii,
    'csv': format_csv,
    'd2': format_d2,
    'dot': format_dot,
    'json': format_json,
    'levels': format_levels,
    'mermaid': format_mermaid,
    'table': format_table,
}


def format_graph(
    graph: DependencyGraph,
    packages: list[Package],
    *,
    fmt: str = 'levels',
) -> str:
    """Format a dependency graph using the named formatter.

    Args:
        graph: The dependency graph.
        packages: Package list for metadata.
        fmt: Format name (one of :data:`FORMATTERS`).

    Returns:
        The formatted graph string.

    Raises:
        ValueError: If ``fmt`` is not a registered format name.
    """
    formatter = FORMATTERS.get(fmt)
    if formatter is None:
        available = ', '.join(sorted(FORMATTERS))
        msg = f'Unknown format {fmt!r}. Available: {available}'
        raise ValueError(msg)
    return formatter(graph, packages)


__all__ = [
    'FORMATTERS',
    'format_graph',
]
