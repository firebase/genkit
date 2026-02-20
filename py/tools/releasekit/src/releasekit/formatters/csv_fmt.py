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

"""CSV output with Unicode BOM.

Renders the dependency graph as RFC 4180 CSV with a UTF-8 BOM
(U+FEFF) so spreadsheet applications (Excel, Google Sheets,
LibreOffice) open the file with correct encoding automatically.

Example output (BOM omitted for readability)::

    level,package,version,dependencies
    0,genkit,0.5.0,
    1,genkit-plugin-google-genai,0.5.0,genkit
    1,genkit-plugin-vertex-ai,0.5.0,genkit
    2,provider-google-genai-hello,0.1.0,"genkit,genkit-plugin-google-genai"
"""

from __future__ import annotations

import csv
import io

from releasekit.graph import DependencyGraph, topo_sort
from releasekit.workspace import Package

_BOM = '\ufeff'


def format_csv(
    graph: DependencyGraph,
    packages: list[Package],
    *,
    bom: bool = True,
) -> str:
    """Render the dependency graph as CSV.

    Args:
        graph: The dependency graph.
        packages: Package list for metadata.
        bom: Prepend a UTF-8 BOM for spreadsheet compatibility
            (default ``True``).

    Returns:
        A CSV string with header row.
    """
    levels = topo_sort(graph)
    pkg_map = {p.name: p for p in packages}

    buf = io.StringIO()
    if bom:
        buf.write(_BOM)

    writer = csv.writer(buf, lineterminator='\n')
    writer.writerow(['level', 'package', 'version', 'dependencies'])

    for level_idx, level in enumerate(levels):
        for pkg in level:
            p = pkg_map.get(pkg.name, pkg)
            deps = ','.join(sorted(graph.edges.get(pkg.name, [])))
            writer.writerow([level_idx, pkg.name, p.version, deps])

    return buf.getvalue()


__all__ = ['format_csv']
