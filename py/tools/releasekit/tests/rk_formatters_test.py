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

"""Tests for releasekit.formatters package."""

from __future__ import annotations

import csv as csv_mod
import io
import json
from pathlib import Path

from releasekit.formatters import FORMATTERS, format_graph
from releasekit.formatters.ascii_art import format_ascii
from releasekit.formatters.csv_fmt import format_csv
from releasekit.formatters.d2 import format_d2
from releasekit.formatters.dot import format_dot
from releasekit.formatters.json_fmt import format_json
from releasekit.formatters.levels import format_levels
from releasekit.formatters.mermaid import format_mermaid
from releasekit.formatters.table import format_table
from releasekit.graph import DependencyGraph, build_graph
from releasekit.workspace import Package


def _make_packages() -> list[Package]:
    """Create a small test package set."""
    return [
        Package(
            name='core',
            version='1.0.0',
            path=Path('/p/core'),
            manifest_path=Path('/p/core/pyproject.toml'),
        ),
        Package(
            name='plugin-a',
            version='1.0.0',
            path=Path('/p/plugin-a'),
            manifest_path=Path('/p/plugin-a/pyproject.toml'),
            internal_deps=['core'],
        ),
        Package(
            name='plugin-b',
            version='1.0.0',
            path=Path('/p/plugin-b'),
            manifest_path=Path('/p/plugin-b/pyproject.toml'),
            internal_deps=['core'],
        ),
        Package(
            name='app',
            version='0.1.0',
            path=Path('/p/app'),
            manifest_path=Path('/p/app/pyproject.toml'),
            internal_deps=['plugin-a', 'plugin-b'],
        ),
    ]


def _make_graph(packages: list[Package] | None = None) -> DependencyGraph:
    """Build a test graph."""
    if packages is None:
        packages = _make_packages()
    return build_graph(packages)


# ── Registry ────────────────────────────────────────────────────────


class TestRegistry:
    """Tests for the formatter registry."""

    def test_all_formats_registered(self) -> None:
        """All 6 format names are registered."""
        expected = {'ascii', 'csv', 'd2', 'dot', 'json', 'levels', 'mermaid', 'table'}
        if FORMATTERS.keys() != expected:
            missing = expected - FORMATTERS.keys()
            extra = FORMATTERS.keys() - expected
            msg = f'Missing: {missing}, Extra: {extra}'
            raise AssertionError(msg)

    def test_format_graph_dispatches(self) -> None:
        """format_graph dispatches to the correct formatter."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)

        for fmt_name in FORMATTERS:
            output = format_graph(graph, pkgs, fmt=fmt_name)
            if not isinstance(output, str):
                msg = f'{fmt_name} returned {type(output)}, expected str'
                raise AssertionError(msg)
            if not output.strip():
                msg = f'{fmt_name} returned empty output'
                raise AssertionError(msg)

    def test_format_graph_unknown_raises(self) -> None:
        """format_graph raises ValueError for unknown format."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        try:
            format_graph(graph, pkgs, fmt='unknown_format')
        except ValueError as exc:
            if 'unknown_format' not in str(exc):
                msg = f'Expected format name in error: {exc}'
                raise AssertionError(msg) from exc
        else:
            msg = 'Expected ValueError'
            raise AssertionError(msg)


# ── DOT format ──────────────────────────────────────────────────────


class TestDotFormat:
    """Tests for the DOT formatter."""

    def test_basic_output(self) -> None:
        """DOT output includes digraph header and nodes."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_dot(graph, pkgs)

        if 'digraph dependencies' not in output:
            raise AssertionError('Missing digraph header')
        if '"core"' not in output:
            raise AssertionError('Missing core node')
        if '"plugin-a" -> "core"' not in output:
            raise AssertionError('Missing edge plugin-a -> core')

    def test_custom_rankdir(self) -> None:
        """DOT output uses custom rankdir."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_dot(graph, pkgs, rankdir='LR')

        if 'rankdir=LR' not in output:
            raise AssertionError('Missing rankdir=LR')

    def test_with_label(self) -> None:
        """DOT output includes title label."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_dot(graph, pkgs, label='My Graph')

        if 'label="My Graph"' not in output:
            raise AssertionError('Missing label')

    def test_version_in_node(self) -> None:
        """DOT node labels include version."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_dot(graph, pkgs)

        if 'core\\n1.0.0' not in output:
            raise AssertionError('Missing version in node label')


# ── Mermaid format ──────────────────────────────────────────────────


class TestMermaidFormat:
    """Tests for the Mermaid formatter."""

    def test_basic_output(self) -> None:
        """Mermaid output includes flowchart header and nodes."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_mermaid(graph, pkgs)

        if 'flowchart TD' not in output:
            raise AssertionError('Missing flowchart header')
        if 'core' not in output:
            raise AssertionError('Missing core node')

    def test_sanitized_ids(self) -> None:
        """Mermaid IDs replace hyphens with underscores."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_mermaid(graph, pkgs)

        if 'plugin_a' not in output:
            raise AssertionError('Expected plugin_a (sanitized)')
        if 'plugin-a[' in output:
            raise AssertionError('Unsanitized plugin-a should not appear as ID')

    def test_edges(self) -> None:
        """Mermaid output includes edges."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_mermaid(graph, pkgs)

        if 'plugin_a --> core' not in output:
            raise AssertionError('Missing edge plugin_a --> core')

    def test_custom_direction(self) -> None:
        """Mermaid output uses custom direction."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_mermaid(graph, pkgs, direction='LR')

        if 'flowchart LR' not in output:
            raise AssertionError('Missing flowchart LR')

    def test_with_title(self) -> None:
        """Mermaid output includes title in frontmatter."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_mermaid(graph, pkgs, title='Dependencies')

        if 'title: Dependencies' not in output:
            raise AssertionError('Missing title')

    def test_no_version_package(self) -> None:
        """Package not in pkg_map renders without version."""
        orphan = Package(
            name='orphan',
            version='',
            path=Path('/p/orphan'),
            manifest_path=Path('/p/orphan/pyproject.toml'),
        )
        graph = build_graph([orphan])
        output = format_mermaid(graph, [])
        assert 'orphan["orphan"]' in output


# ── D2 format ───────────────────────────────────────────────────────


class TestD2Format:
    """Tests for the D2 formatter."""

    def test_basic_output(self) -> None:
        """D2 output includes direction and nodes."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_d2(graph, pkgs)

        if 'direction: down' not in output:
            raise AssertionError('Missing direction')
        if 'core:' not in output:
            raise AssertionError('Missing core node')

    def test_edges(self) -> None:
        """D2 output includes edges."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_d2(graph, pkgs)

        if 'plugin_a -> core' not in output:
            raise AssertionError('Missing edge plugin_a -> core')

    def test_custom_direction(self) -> None:
        """D2 output uses custom direction."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_d2(graph, pkgs, direction='right')

        if 'direction: right' not in output:
            raise AssertionError('Missing direction: right')

    def test_with_title(self) -> None:
        """D2 output includes title block when provided."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_d2(graph, pkgs, title='My Graph')

        assert 'title: My Graph {' in output
        assert 'shape: text' in output
        assert 'near: top-center' in output

    def test_no_version_package(self) -> None:
        """Package not in pkg_map renders without version."""
        # Create a graph with a package that has an empty version.
        orphan = Package(
            name='orphan',
            version='',
            path=Path('/p/orphan'),
            manifest_path=Path('/p/orphan/pyproject.toml'),
        )
        graph = build_graph([orphan])
        # Pass empty pkg list so pkg_map won't find 'orphan'.
        output = format_d2(graph, [])
        assert 'orphan: "orphan" {' in output


# ── ASCII art format ────────────────────────────────────────────────


class TestAsciiFormat:
    """Tests for the ASCII art formatter."""

    def test_basic_output(self) -> None:
        """ASCII output includes box-drawing characters."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_ascii(graph, pkgs)

        if '┌' not in output:
            raise AssertionError('Missing top-left corner')
        if '┘' not in output:
            raise AssertionError('Missing bottom-right corner')
        if 'Level 0' not in output:
            raise AssertionError('Missing Level 0 header')

    def test_contains_packages(self) -> None:
        """ASCII output lists all packages."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_ascii(graph, pkgs)

        for pkg in pkgs:
            if pkg.name not in output:
                msg = f'Missing package {pkg.name}'
                raise AssertionError(msg)

    def test_show_deps(self) -> None:
        """ASCII output shows dependency arrows with show_deps=True."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_ascii(graph, pkgs, show_deps=True)

        if '→' not in output:
            raise AssertionError('Missing dependency arrow')

    def test_no_version_package(self) -> None:
        """Package with empty version renders without version."""
        orphan = Package(
            name='orphan',
            version='',
            path=Path('/p/orphan'),
            manifest_path=Path('/p/orphan/pyproject.toml'),
        )
        graph = build_graph([orphan])
        output = format_ascii(graph, [orphan])
        assert 'orphan' in output
        # Should NOT have parenthesized version.
        assert '()' not in output


# ── JSON format ─────────────────────────────────────────────────────


class TestJsonFormat:
    """Tests for the JSON formatter."""

    def test_valid_json(self) -> None:
        """JSON output is valid JSON."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_json(graph, pkgs)

        data = json.loads(output)
        if data['packages'] != 4:
            msg = f'Expected 4 packages, got {data["packages"]}'
            raise AssertionError(msg)

    def test_contains_edges(self) -> None:
        """JSON output includes edges."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_json(graph, pkgs)

        data = json.loads(output)
        if 'edges' not in data:
            raise AssertionError('Missing edges')
        if 'core' not in data['edges'].get('plugin-a', []):
            raise AssertionError('Missing edge plugin-a -> core')

    def test_contains_levels(self) -> None:
        """JSON output includes level groups."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_json(graph, pkgs)

        data = json.loads(output)
        if data['levels'] < 2:
            msg = f'Expected at least 2 levels, got {data["levels"]}'
            raise AssertionError(msg)


# ── Levels format ───────────────────────────────────────────────────


class TestLevelsFormat:
    """Tests for the levels formatter."""

    def test_basic_output(self) -> None:
        """Levels output lists levels with package names."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_levels(graph, pkgs)

        if 'Level 0' not in output:
            raise AssertionError('Missing Level 0')
        if 'core' not in output:
            raise AssertionError('Missing core')

    def test_show_version(self) -> None:
        """Levels output includes versions with show_version=True."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_levels(graph, pkgs, show_version=True)

        if '1.0.0' not in output:
            raise AssertionError('Missing version')


# ── Empty graph ─────────────────────────────────────────────────────


class TestEmptyGraph:
    """Tests for formatters with an empty graph."""

    def test_all_formats_handle_empty(self) -> None:
        """All formatters handle an empty graph gracefully."""
        pkgs: list[Package] = []
        graph = _make_graph(pkgs)

        for fmt_name in FORMATTERS:
            output = format_graph(graph, pkgs, fmt=fmt_name)
            if not isinstance(output, str):
                msg = f'{fmt_name} returned {type(output)} for empty graph'
                raise AssertionError(msg)


class TestTableFormat:
    """Tests for the table formatter."""

    def test_basic_output(self) -> None:
        """Table output includes header row and separator."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_table(graph, pkgs)

        if '| Level' not in output:
            raise AssertionError('Missing Level header')
        if '| Package' not in output:
            raise AssertionError('Missing Package header')
        if '|---' not in output:
            raise AssertionError('Missing separator row')

    def test_contains_all_packages(self) -> None:
        """Table output lists every package."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_table(graph, pkgs)

        for pkg in pkgs:
            if pkg.name not in output:
                msg = f'Missing package {pkg.name}'
                raise AssertionError(msg)

    def test_includes_version_by_default(self) -> None:
        """Table output includes version column by default."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_table(graph, pkgs)

        if '| Version' not in output:
            raise AssertionError('Missing Version header')
        if '1.0.0' not in output:
            raise AssertionError('Missing version value')

    def test_no_version(self) -> None:
        """Table output omits version column when show_version=False."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_table(graph, pkgs, show_version=False)

        if 'Version' in output:
            raise AssertionError('Version column should be omitted')

    def test_includes_dependencies(self) -> None:
        """Table output includes dependency names."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_table(graph, pkgs)

        if '| Dependencies' not in output:
            raise AssertionError('Missing Dependencies header')
        # app depends on plugin-a and plugin-b
        if 'plugin-a' not in output:
            raise AssertionError('Missing dependency plugin-a')

    def test_empty_graph(self) -> None:
        """Table output handles empty graph."""
        pkgs: list[Package] = []
        graph = _make_graph(pkgs)
        output = format_table(graph, pkgs)

        if 'empty' not in output.lower():
            raise AssertionError(f'Expected empty indicator, got: {output!r}')

    def test_row_count(self) -> None:
        """Table has header + separator + one row per package."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_table(graph, pkgs)
        lines = [ln for ln in output.strip().splitlines() if ln.strip()]

        # header + separator + 4 packages = 6 lines
        if len(lines) != 6:
            msg = f'Expected 6 lines, got {len(lines)}: {lines}'
            raise AssertionError(msg)


class TestCsvFormat:
    """Tests for the CSV formatter."""

    def test_has_bom_by_default(self) -> None:
        """CSV output starts with UTF-8 BOM."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_csv(graph, pkgs)

        if not output.startswith('\ufeff'):
            raise AssertionError('Missing BOM')

    def test_no_bom(self) -> None:
        """CSV output omits BOM when bom=False."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_csv(graph, pkgs, bom=False)

        if output.startswith('\ufeff'):
            raise AssertionError('BOM should be omitted')

    def test_header_row(self) -> None:
        """CSV starts with the expected header."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_csv(graph, pkgs, bom=False)
        header = output.splitlines()[0]

        if header != 'level,package,version,dependencies':
            raise AssertionError(f'Unexpected header: {header!r}')

    def test_contains_all_packages(self) -> None:
        """CSV lists every package."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_csv(graph, pkgs, bom=False)

        for pkg in pkgs:
            if pkg.name not in output:
                msg = f'Missing package {pkg.name}'
                raise AssertionError(msg)

    def test_row_count(self) -> None:
        """CSV has header + one row per package."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_csv(graph, pkgs, bom=False)
        lines = [ln for ln in output.strip().splitlines() if ln.strip()]

        # header + 4 packages = 5 lines
        if len(lines) != 5:
            msg = f'Expected 5 lines, got {len(lines)}: {lines}'
            raise AssertionError(msg)

    def test_multi_dep_quoting(self) -> None:
        """Dependencies with commas are quoted by csv.writer."""
        pkgs = _make_packages()
        graph = _make_graph(pkgs)
        output = format_csv(graph, pkgs, bom=False)

        # app depends on plugin-a and plugin-b, so deps field contains a comma
        # csv.writer should quote it: "plugin-a,plugin-b"
        reader = csv_mod.reader(io.StringIO(output))
        rows = list(reader)
        app_rows = [r for r in rows if len(r) >= 2 and r[1] == 'app']
        if not app_rows:
            raise AssertionError('Missing app row')
        deps = app_rows[0][3]
        if 'plugin-a' not in deps or 'plugin-b' not in deps:
            raise AssertionError(f'Missing deps in app row: {deps!r}')

    def test_empty_graph(self) -> None:
        """CSV with empty graph has only header."""
        pkgs: list[Package] = []
        graph = _make_graph(pkgs)
        output = format_csv(graph, pkgs, bom=False)
        lines = [ln for ln in output.strip().splitlines() if ln.strip()]

        if len(lines) != 1:
            msg = f'Expected 1 line (header only), got {len(lines)}'
            raise AssertionError(msg)
