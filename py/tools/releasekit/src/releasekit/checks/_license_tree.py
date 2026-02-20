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

"""License dependency tree and Rust-style diagnostic formatting.

This module builds a structured representation of the license tree for
every publishable package and its dependencies, then renders it as
human-readable output with Rust-style error annotations.

Example tree output::

    license_compatibility: project license is Apache-2.0

    myapp (Apache-2.0)
    ├── utils-lib (MIT) ✓
    ├── logging-lib (BSD-3-Clause) ✓
    ├── gpl-lib (GPL-3.0-only) ✗ incompatible
    └── oracle-jdbc (Proprietary) ⊘ exempt

Example Rust-style diagnostic::

    error[license_compatibility]: license incompatibility
      --> plugins/myapp/pyproject.toml:12
       |
    10 |  [project]
    11 |  name = "myapp"
    12 |  dependencies = ["gpl-lib>=1.0"]
       |                  ^^^^^^^ incompatible: GPL-3.0-only cannot be used in Apache-2.0 project
    13 |
       |
       = hint: Either change the dependency, add it to exempt_packages, or adjust the project license.
"""

from __future__ import annotations

import enum
import json
import os
import sys
from dataclasses import asdict, dataclass, field

from releasekit.preflight import SourceContext, read_source_snippet

# ── ANSI helpers ─────────────────────────────────────────────────────


class _Ansi:
    """ANSI escape code constants."""

    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    BOLD_RED = '\033[1;31m'
    BOLD_GREEN = '\033[1;32m'
    BOLD_YELLOW = '\033[1;33m'
    BOLD_CYAN = '\033[1;36m'


def _c(text: str, code: str, *, color: bool) -> str:
    """Wrap *text* in ANSI *code* if *color* is True."""
    if not color:
        return text
    return f'{code}{text}{_Ansi.RESET}'


def should_use_color(*, force: bool | None = None) -> bool:
    """Determine whether to emit ANSI colors.

    Resolution order:
        1. Explicit *force* argument (from config ``color = true/false``).
        2. ``NO_COLOR`` env var (https://no-color.org/) → disable.
        3. ``FORCE_COLOR`` env var → enable.
        4. ``sys.stdout.isatty()`` → enable if TTY.

    Args:
        force: Explicit override from config. ``None`` means auto-detect.

    Returns:
        ``True`` if color should be used.
    """
    if force is not None:
        return force
    if os.environ.get('NO_COLOR', '') != '':
        return False
    if os.environ.get('FORCE_COLOR', '') != '':
        return True
    try:
        return sys.stdout.isatty()
    except Exception:  # noqa: BLE001
        return False


class DepStatus(enum.Enum):
    """Status of a single dependency in the license tree."""

    OK = 'ok'
    INCOMPATIBLE = 'incompatible'
    DENIED = 'denied'
    UNRESOLVED = 'unresolved'
    EXEMPT = 'exempt'
    ALLOWED = 'allowed'
    OVERRIDDEN = 'overridden'
    NO_LICENSE = 'no_license'


# Symbols for tree rendering.
_STATUS_SYMBOLS: dict[DepStatus, str] = {
    DepStatus.OK: '\u2713',  # ✓
    DepStatus.INCOMPATIBLE: '\u2717',  # ✗
    DepStatus.DENIED: '\u2718',  # ✘
    DepStatus.UNRESOLVED: '?',
    DepStatus.EXEMPT: '\u2298',  # ⊘
    DepStatus.ALLOWED: '\u2713',  # ✓
    DepStatus.OVERRIDDEN: '\u2713',  # ✓
    DepStatus.NO_LICENSE: '-',
}

# ANSI color per status.
_STATUS_COLORS: dict[DepStatus, str] = {
    DepStatus.OK: _Ansi.GREEN,
    DepStatus.INCOMPATIBLE: _Ansi.BOLD_RED,
    DepStatus.DENIED: _Ansi.BOLD_RED,
    DepStatus.UNRESOLVED: _Ansi.YELLOW,
    DepStatus.EXEMPT: _Ansi.DIM,
    DepStatus.ALLOWED: _Ansi.GREEN,
    DepStatus.OVERRIDDEN: _Ansi.GREEN,
    DepStatus.NO_LICENSE: _Ansi.DIM,
}

# Statuses that warrant showing extra metadata (URL, source).
_DETAIL_STATUSES: frozenset[DepStatus] = frozenset({
    DepStatus.INCOMPATIBLE,
    DepStatus.DENIED,
    DepStatus.NO_LICENSE,
    DepStatus.UNRESOLVED,
})


@dataclass(frozen=True)
class DepNode:
    """A single dependency edge in the license tree.

    Attributes:
        name: Dependency package name.
        license: Resolved SPDX ID or raw license string.
        status: Evaluation result for this edge.
        detail: Extra detail (e.g. 'blocked: AGPL-3.0-only').
        registry_url: URL to the package's registry page (e.g. PyPI,
            npm) for manual investigation.
        source: How the license was detected (e.g. 'PyPI registry',
            'pyproject.toml', 'LICENSE file').
    """

    name: str
    license: str = ''
    status: DepStatus = DepStatus.OK
    detail: str = ''
    registry_url: str = ''
    source: str = ''


def registry_url_for(name: str, ecosystem: str = 'python') -> str:
    """Build a registry project page URL for *name*.

    Args:
        name: Package name (e.g. ``"requests"``, ``"@types/node"``).
        ecosystem: Ecosystem identifier (``"python"``, ``"js"``, etc.).

    Returns:
        URL string, or ``""`` if the ecosystem is unknown.
    """
    eco = ecosystem.lower()
    if eco in ('python', 'uv', 'pip'):
        return f'https://pypi.org/project/{name}/'
    if eco in ('js', 'pnpm', 'npm', 'node'):
        return f'https://www.npmjs.com/package/{name}'
    if eco in ('rust', 'cargo'):
        return f'https://crates.io/crates/{name}'
    if eco in ('go',):
        return f'https://pkg.go.dev/{name}'
    if eco in ('dart', 'flutter', 'pub'):
        return f'https://pub.dev/packages/{name}'
    if eco in ('java', 'maven', 'gradle', 'kotlin'):
        return f'https://central.sonatype.com/search?q={name}'
    return ''


@dataclass
class PackageTree:
    """License tree for a single publishable package.

    Attributes:
        name: Package name.
        license: Resolved SPDX ID of this package.
        manifest_path: Path to the package's manifest file.
        deps: Ordered list of dependency nodes.
    """

    name: str
    license: str
    manifest_path: str = ''
    deps: list[DepNode] = field(default_factory=list)


@dataclass
class LicenseTree:
    """Full license tree for the workspace.

    Attributes:
        project_license: The resolved project SPDX ID.
        packages: Per-publishable-package trees.
    """

    project_license: str = ''
    packages: list[PackageTree] = field(default_factory=list)


def format_license_tree(tree: LicenseTree, *, color: bool = False) -> str:
    """Render the license tree as a human-readable string.

    Example::

        license_compatibility: project license is Apache-2.0

        myapp (Apache-2.0)
        ├── utils-lib (MIT) ✓
        ├── logging-lib (BSD-3-Clause) ✓
        ├── gpl-lib (GPL-3.0-only) ✗ incompatible
        └── oracle-jdbc (Proprietary) ⊘ exempt

    Args:
        tree: The license tree to render.
        color: Emit ANSI color codes.

    Returns:
        Multi-line string.
    """
    lines: list[str] = []
    header = _c(
        f'license_compatibility: project license is {tree.project_license}',
        _Ansi.BOLD_CYAN,
        color=color,
    )
    lines.append(header)
    lines.append('')

    for pkg in tree.packages:
        pkg_header = _c(f'{pkg.name}', _Ansi.BOLD, color=color) + f' ({pkg.license})'
        lines.append(pkg_header)
        for i, dep in enumerate(pkg.deps):
            is_last = i == len(pkg.deps) - 1
            connector = '\u2514\u2500\u2500' if is_last else '\u251c\u2500\u2500'  # └── or ├──
            continuation = '    ' if is_last else '\u2502   '  # │    or (space)
            symbol = _STATUS_SYMBOLS.get(dep.status, '?')
            status_color = _STATUS_COLORS.get(dep.status, '')
            lic_part = f' ({dep.license})' if dep.license else ''
            detail_part = f' {dep.detail}' if dep.detail else ''
            status_label = ''
            if dep.status not in (DepStatus.OK, DepStatus.ALLOWED, DepStatus.OVERRIDDEN):
                status_label = f' {dep.status.value}'
            # Color the symbol + status + detail together.
            colored_suffix = _c(
                f'{symbol}{status_label}{detail_part}',
                status_color,
                color=color,
            )
            dep_name_part = _c(dep.name, _Ansi.BOLD, color=color) if color else dep.name
            lines.append(f'{connector} {dep_name_part}{lic_part} {colored_suffix}')

            # Show registry URL and source as Rust-style note lines
            # for deps that need attention.
            if dep.status in _DETAIL_STATUSES:
                if dep.source:
                    note = _c('note', _Ansi.BOLD_CYAN, color=color)
                    src = _c(dep.source, _Ansi.DIM, color=color)
                    lines.append(f'{continuation}  {note}: detected via {src}')
                if dep.registry_url:
                    note = _c('note', _Ansi.BOLD_CYAN, color=color)
                    url = _c(dep.registry_url, _Ansi.CYAN, color=color)
                    lines.append(f'{continuation}  {note}: {url}')
        if pkg.deps:
            lines.append('')

    return '\n'.join(lines)


def format_license_diagnostic(
    *,
    severity: str,
    message: str,
    source: SourceContext | None = None,
    hint: str = '',
    color: bool = False,
) -> str:
    """Render a single Rust-style diagnostic message.

    Example::

        error[license_compatibility]: license incompatibility
          --> plugins/myapp/pyproject.toml:12
           |
        10 |  [project]
        11 |  name = "myapp"
        12 |> dependencies = ["gpl-lib>=1.0"]
           |                  ^^^^^^^ incompatible: GPL-3.0-only
        13 |
           |
           = hint: Either change the dependency ...

    Args:
        severity: ``'error'`` or ``'warning'``.
        message: The diagnostic message.
        source: Optional source context with file/line info.
        hint: Optional actionable suggestion.
        color: Emit ANSI color codes.

    Returns:
        Multi-line formatted string.
    """
    lines: list[str] = []
    sev_color = _Ansi.BOLD_RED if severity == 'error' else _Ansi.BOLD_YELLOW
    tag = _c(f'{severity}[license_compatibility]', sev_color, color=color)
    lines.append(f'{tag}: {message}')

    if source is not None:
        arrow = _c('-->', _Ansi.BLUE, color=color)
        lines.append(f'  {arrow} {source}')
        if source.line > 0:
            snippet = read_source_snippet(source.path, source.line)
            if snippet:
                gutter_width = len(str(snippet[-1][0]))
                pipe = _c('|', _Ansi.BLUE, color=color)
                lines.append(f'  {" " * gutter_width} {pipe}')
                for lineno, text in snippet:
                    marker = '>' if lineno == source.line else ' '
                    gutter = _c(f'{lineno:>{gutter_width}}', _Ansi.BLUE, color=color)
                    lines.append(f'  {gutter} {pipe}{marker} {text}')
                if source.label:
                    offending_text = next((t for n, t in snippet if n == source.line), '')
                    if source.key and source.key in offending_text:
                        col = offending_text.index(source.key)
                        underline = ' ' * col + _c(
                            '^' * len(source.key) + ' ' + source.label,
                            sev_color,
                            color=color,
                        )
                    else:
                        underline = _c(source.label, sev_color, color=color)
                    lines.append(f'  {" " * gutter_width} {pipe}  {underline}')
                lines.append(f'  {" " * gutter_width} {pipe}')

    if hint:
        eq = _c('=', _Ansi.CYAN, color=color)
        hint_label = _c('hint', _Ansi.BOLD_CYAN, color=color)
        lines.append(f'  {eq} {hint_label}: {hint}')

    return '\n'.join(lines)


# ── Export formats ───────────────────────────────────────────────────

LICENSE_TREE_FORMATS: frozenset[str] = frozenset({
    'tree',
    'json',
    'table',
    'mermaid',
    'd2',
    'dot',
})


def license_tree_to_json(tree: LicenseTree, *, indent: int = 2) -> str:
    """Serialize the license tree to JSON.

    Args:
        tree: The license tree.
        indent: JSON indentation level.

    Returns:
        JSON string.
    """

    def _serialize(obj: object) -> object:  # noqa: ANN401
        if isinstance(obj, enum.Enum):
            return obj.value
        return obj

    data = asdict(tree)
    return json.dumps(data, indent=indent, default=_serialize)


def license_tree_to_table(tree: LicenseTree) -> str:
    """Render the license tree as an ASCII table.

    Example::

        Project License: Apache-2.0
        ┌──────────┬────────────┬──────────────┬──────────────┬────────┐
        │ Package  │ Dependency │ License      │ Status       │ Detail │
        ├──────────┼────────────┼──────────────┼──────────────┼────────┤
        │ myapp    │ utils-lib  │ MIT          │ ok           │        │
        │ myapp    │ gpl-lib    │ GPL-3.0-only │ incompatible │ ...    │
        └──────────┴────────────┴──────────────┴──────────────┴────────┘

    Args:
        tree: The license tree.

    Returns:
        Multi-line ASCII table string.
    """
    rows: list[tuple[str, str, str, str, str]] = []
    for pkg in tree.packages:
        for dep in pkg.deps:
            rows.append((
                pkg.name,
                dep.name,
                dep.license or '(none)',
                dep.status.value,
                dep.detail,
            ))

    if not rows:
        return f'Project License: {tree.project_license}\n(no dependencies)'

    headers = ('Package', 'Dependency', 'License', 'Status', 'Detail')
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def _row_str(cells: tuple[str, ...]) -> str:
        parts = [f' {cells[i]:<{widths[i]}} ' for i in range(len(headers))]
        return '\u2502' + '\u2502'.join(parts) + '\u2502'

    top = '\u250c' + '\u252c'.join('\u2500' * (w + 2) for w in widths) + '\u2510'
    mid = '\u251c' + '\u253c'.join('\u2500' * (w + 2) for w in widths) + '\u2524'
    bot = '\u2514' + '\u2534'.join('\u2500' * (w + 2) for w in widths) + '\u2518'

    lines = [f'Project License: {tree.project_license}', top, _row_str(headers), mid]
    for row in rows:
        lines.append(_row_str(row))
    lines.append(bot)
    return '\n'.join(lines)


def license_tree_to_mermaid(tree: LicenseTree) -> str:
    """Render the license tree as a Mermaid flowchart.

    Example::

        flowchart TD
            subgraph "Project License: Apache-2.0"
                myapp["myapp<br/>Apache-2.0"]
                myapp --> |"MIT ✓"| utils_lib
            end

    Args:
        tree: The license tree.

    Returns:
        Mermaid flowchart string.
    """
    lines: list[str] = ['flowchart TD']
    lines.append(f'    subgraph "Project License: {tree.project_license}"')

    for pkg in tree.packages:
        pkg_id = _mermaid_id(pkg.name)
        lines.append(f'        {pkg_id}["{pkg.name}<br/>{pkg.license}"]')
        for dep in pkg.deps:
            dep_id = _mermaid_id(dep.name)
            symbol = _STATUS_SYMBOLS.get(dep.status, '?')
            lic = dep.license or '(none)'
            edge_label = f'{lic} {symbol}'
            lines.append(f'        {pkg_id} --> |"{edge_label}"| {dep_id}')

    lines.append('    end')

    bad_nodes: set[str] = set()
    for pkg in tree.packages:
        for dep in pkg.deps:
            if dep.status in (DepStatus.INCOMPATIBLE, DepStatus.DENIED):
                bad_nodes.add(_mermaid_id(dep.name))
    for node_id in sorted(bad_nodes):
        lines.append(f'    style {node_id} fill:#f99,stroke:#c00')

    return '\n'.join(lines) + '\n'


def _mermaid_id(name: str) -> str:
    """Convert a package name to a valid Mermaid node ID."""
    return name.replace('-', '_').replace('.', '_').replace('@', '_').replace('/', '_')


def license_tree_to_d2(tree: LicenseTree) -> str:
    """Render the license tree as a D2 diagram.

    Example::

        direction: down

        project: "Project License: Apache-2.0" {
          myapp: "myapp (Apache-2.0)"
          myapp -> utils-lib: "MIT ✓"
        }

    Args:
        tree: The license tree.

    Returns:
        D2 diagram string.
    """
    lines: list[str] = ['direction: down', '']
    lines.append(f'project: "Project License: {tree.project_license}" {{')

    declared: set[str] = set()
    for pkg in tree.packages:
        if pkg.name not in declared:
            lines.append(f'  {_d2_id(pkg.name)}: "{pkg.name} ({pkg.license})"')
            declared.add(pkg.name)
        for dep in pkg.deps:
            if dep.name not in declared:
                lic = dep.license or '(none)'
                lines.append(f'  {_d2_id(dep.name)}: "{dep.name} ({lic})"')
                declared.add(dep.name)
            symbol = _STATUS_SYMBOLS.get(dep.status, '?')
            lic = dep.license or '(none)'
            lines.append(f'  {_d2_id(pkg.name)} -> {_d2_id(dep.name)}: "{lic} {symbol}"')

    for pkg in tree.packages:
        for dep in pkg.deps:
            if dep.status in (DepStatus.INCOMPATIBLE, DepStatus.DENIED):
                lines.append(f'  {_d2_id(dep.name)}.style.fill: "#ffcccc"')
                lines.append(f'  {_d2_id(dep.name)}.style.stroke: "#cc0000"')

    lines.append('}')
    return '\n'.join(lines) + '\n'


def _d2_id(name: str) -> str:
    """Convert a package name to a valid D2 identifier."""
    return name.replace('@', '_').replace('/', '_')


def license_tree_to_dot(tree: LicenseTree) -> str:
    r"""Render the license tree as a Graphviz DOT digraph.

    Example::

        digraph license_tree {
          rankdir=TB;
          node [shape=box, style=rounded, fontname="Inter"];
          "myapp" [label="myapp\\nApache-2.0"];
          "myapp" -> "utils-lib" [label="MIT ✓"];
        }

    Usage::

        dot -Tsvg license_tree.dot -o license_tree.svg

    Args:
        tree: The license tree.

    Returns:
        DOT language string.
    """
    lines: list[str] = [
        'digraph license_tree {',
        '  rankdir=TB;',
        '  node [shape=box, style=rounded, fontname="Inter"];',
        '  edge [color="#666666"];',
        f'  label="Project License: {tree.project_license}";',
        '  labelloc=t;',
        '',
    ]

    declared: set[str] = set()
    for pkg in tree.packages:
        if pkg.name not in declared:
            lines.append(f'  "{pkg.name}" [label="{pkg.name}\\n{pkg.license}"];')
            declared.add(pkg.name)
        for dep in pkg.deps:
            if dep.name not in declared:
                lic = dep.license or '(none)'
                attrs = f'label="{dep.name}\\n{lic}"'
                if dep.status in (DepStatus.INCOMPATIBLE, DepStatus.DENIED):
                    attrs += ', style="rounded,filled", fillcolor="#ffcccc", color="#cc0000"'
                lines.append(f'  "{dep.name}" [{attrs}];')
                declared.add(dep.name)

            symbol = _STATUS_SYMBOLS.get(dep.status, '?')
            lic = dep.license or '(none)'
            edge_color = '#cc0000' if dep.status in (DepStatus.INCOMPATIBLE, DepStatus.DENIED) else '#666666'
            lines.append(f'  "{pkg.name}" -> "{dep.name}" [label="{lic} {symbol}", color="{edge_color}"];')

    lines.append('}')
    return '\n'.join(lines) + '\n'


def format_license_tree_as(
    tree: LicenseTree,
    fmt: str,
    *,
    color: bool = False,
) -> str:
    """Render the license tree in the requested format.

    Args:
        tree: The license tree data.
        fmt: One of ``'tree'``, ``'json'``, ``'table'``,
            ``'mermaid'``, ``'d2'``, ``'dot'``.
        color: Emit ANSI color codes (only affects ``'tree'`` format).

    Returns:
        Formatted string.

    Raises:
        ValueError: If *fmt* is not a recognized format.
    """
    if fmt == 'tree':
        return format_license_tree(tree, color=color)
    if fmt == 'json':
        return license_tree_to_json(tree)
    if fmt == 'table':
        return license_tree_to_table(tree)
    if fmt == 'mermaid':
        return license_tree_to_mermaid(tree)
    if fmt == 'd2':
        return license_tree_to_d2(tree)
    if fmt == 'dot':
        return license_tree_to_dot(tree)
    msg = f'Unknown license tree format: {fmt!r}. Choose from: {", ".join(sorted(LICENSE_TREE_FORMATS))}'
    raise ValueError(msg)
