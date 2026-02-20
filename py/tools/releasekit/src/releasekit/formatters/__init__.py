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

"""Graph output formatters for releasekit.

Each formatter is a pure function: ``graph → str``. No side effects,
no I/O, no network calls. Easy to test, easy to compose.

Available formats:

- **ascii**: Box-drawing character rendering (no external deps)
- **dot**: Graphviz DOT language
- **mermaid**: Mermaid flowchart syntax (renders on GitHub)
- **d2**: D2 diagram language
- **json**: Machine-readable JSON
- **levels**: Simple level-grouped text output

Usage::

    from releasekit.formatters import format_graph

    output = format_graph(graph, packages, fmt='mermaid')
    print(output)
"""

from __future__ import annotations

from releasekit.formatters.registry import FORMATTERS, format_graph

__all__ = [
    'FORMATTERS',
    'format_graph',
]
