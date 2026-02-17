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

"""Tests for ClojureWorkspace backend.

Covers:
- Minimal EDN reader (maps, vectors, strings, keywords, symbols, comments)
- ``deps.edn`` parsing (dependency extraction, local roots)
- ``project.clj`` parsing (defproject, dependencies)
- ``ClojureWorkspace.discover()`` for both Leiningen and tools.deps layouts
- ``ClojureWorkspace.rewrite_version()`` for project.clj, pom.xml, version.edn
- ``ClojureWorkspace.rewrite_dependency_version()`` for project.clj and deps.edn
"""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends.workspace._edn import parse_edn
from releasekit.backends.workspace.clojure import (
    ClojureWorkspace,
    _extract_deps_edn_deps,
    _extract_deps_edn_local_deps,
    _parse_deps_edn,
    _parse_project_clj,
    _parse_project_clj_deps,
    _read_pom_version,
    _read_version_edn,
    _rewrite_deps_edn_dep_version,
    _rewrite_project_clj_dep_version,
    _rewrite_project_clj_version,
    _rewrite_version_edn,
)
from releasekit.logging import configure_logging

configure_logging(quiet=True)


# Minimal EDN reader


class TestParseEdn:
    """Tests for parse_edn()."""

    def test_parses_empty_map(self) -> None:
        """Should parse an empty map."""
        assert parse_edn('{}') == {}

    def test_parses_map_with_keyword_keys(self) -> None:
        """Should parse a map with keyword keys and string values."""
        result = parse_edn('{:name "hello" :version "1.0"}')
        assert result == {':name': 'hello', ':version': '1.0'}

    def test_parses_nested_map(self) -> None:
        """Should parse nested maps."""
        result = parse_edn('{:deps {org.clojure/clojure {:mvn/version "1.11.1"}}}')
        assert isinstance(result, dict)
        deps = result[':deps']  # type: ignore[index]
        assert isinstance(deps, dict)
        assert 'org.clojure/clojure' in deps
        coord = deps['org.clojure/clojure']  # type: ignore[index]
        assert isinstance(coord, dict)
        assert coord[':mvn/version'] == '1.11.1'  # type: ignore[index]

    def test_parses_vector(self) -> None:
        """Should parse a vector."""
        result = parse_edn('["src" "resources"]')
        assert result == ['src', 'resources']

    def test_parses_nil_true_false(self) -> None:
        """Should parse nil, true, false."""
        assert parse_edn('nil') is None
        assert parse_edn('true') is True
        assert parse_edn('false') is False

    def test_parses_integers(self) -> None:
        """Should parse integers."""
        assert parse_edn('42') == 42
        assert parse_edn('-7') == -7

    def test_parses_floats(self) -> None:
        """Should parse floats."""
        assert parse_edn('3.14') == 3.14

    def test_skips_comments(self) -> None:
        """Should skip ; comments."""
        result = parse_edn('{;; this is a comment\n:name "hello" ; inline comment\n}')
        assert result == {':name': 'hello'}

    def test_skips_commas(self) -> None:
        """Should treat commas as whitespace."""
        result = parse_edn('{:a 1, :b 2}')
        assert result == {':a': 1, ':b': 2}

    def test_parses_set_literal(self) -> None:
        """Should parse #{...} set literals."""
        result = parse_edn('#{1 2 3}')
        assert isinstance(result, set)
        assert result == {1, 2, 3}

    def test_parses_list(self) -> None:
        """Should parse (...) list literals."""
        result = parse_edn('(defproject foo "1.0")')
        assert isinstance(result, list)
        assert result == ['defproject', 'foo', '1.0']

    def test_parses_string_escapes(self) -> None:
        """Should handle string escape sequences."""
        result = parse_edn(r'"hello\nworld"')
        assert result == 'hello\nworld'

    def test_raises_on_empty_input(self) -> None:
        """Should raise ValueError on empty input."""
        with pytest.raises(ValueError, match='Unexpected end'):
            parse_edn('')

    def test_raises_on_unexpected_delimiter(self) -> None:
        """Should raise ValueError on unexpected closing delimiter."""
        with pytest.raises(ValueError, match='Unexpected closing'):
            parse_edn('}')

    def test_parses_discard_form(self) -> None:
        """Should handle #_ discard form."""
        result = parse_edn('#_ {:ignored true} {:kept true}')
        assert result == {':kept': True}

    def test_parses_deps_edn_example(self) -> None:
        """Should parse a realistic deps.edn file."""
        edn = """\
{:deps {org.clojure/clojure {:mvn/version "1.11.1"}
        org.clojure/tools.reader {:mvn/version "1.3.7"}
        my.lib/core {:local/root "../core"}}
 :paths ["src" "resources"]}
"""
        result = parse_edn(edn)
        assert isinstance(result, dict)
        assert ':deps' in result
        assert ':paths' in result
        deps = result[':deps']  # type: ignore[index]
        assert len(deps) == 3  # type: ignore[arg-type]


# deps.edn helpers


class TestParseDepsEdn:
    """Tests for _parse_deps_edn()."""

    def test_parses_valid_deps_edn(self, tmp_path: Path) -> None:
        """Should parse a valid deps.edn file."""
        deps = tmp_path / 'deps.edn'
        deps.write_text('{:deps {org.clojure/clojure {:mvn/version "1.11.1"}}}')
        result = _parse_deps_edn(deps)
        assert ':deps' in result

    def test_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        """Should return empty dict for missing file."""
        assert _parse_deps_edn(tmp_path / 'deps.edn') == {}

    def test_returns_empty_for_malformed_edn(self, tmp_path: Path) -> None:
        """Should return empty dict for malformed EDN."""
        deps = tmp_path / 'deps.edn'
        deps.write_text('{:deps {broken')
        assert _parse_deps_edn(deps) == {}


class TestExtractDepsEdnDeps:
    """Tests for _extract_deps_edn_deps()."""

    def test_extracts_dep_names(self) -> None:
        """Should extract dependency names from :deps map."""
        edn: dict[str, object] = {
            ':deps': {
                'org.clojure/clojure': {':mvn/version': '1.11.1'},
                'my.lib/core': {':local/root': '../core'},
            }
        }
        deps = _extract_deps_edn_deps(edn)
        assert 'org.clojure/clojure' in deps
        assert 'my.lib/core' in deps

    def test_returns_empty_when_no_deps(self) -> None:
        """Should return empty list when :deps is absent."""
        assert _extract_deps_edn_deps({}) == []
        assert _extract_deps_edn_deps({':paths': ['src']}) == []


class TestExtractDepsEdnLocalDeps:
    """Tests for _extract_deps_edn_local_deps()."""

    def test_extracts_local_roots(self) -> None:
        """Should extract :local/root paths."""
        edn: dict[str, object] = {
            ':deps': {
                'org.clojure/clojure': {':mvn/version': '1.11.1'},
                'my.lib/core': {':local/root': '../core'},
                'my.lib/plugin': {':local/root': '../plugin'},
            }
        }
        roots = _extract_deps_edn_local_deps(edn)
        assert '../core' in roots
        assert '../plugin' in roots
        assert len(roots) == 2

    def test_returns_empty_when_no_local_deps(self) -> None:
        """Should return empty list when no :local/root deps."""
        edn: dict[str, object] = {':deps': {'org.clojure/clojure': {':mvn/version': '1.11.1'}}}
        assert _extract_deps_edn_local_deps(edn) == []


# project.clj helpers


class TestParseProjectClj:
    """Tests for _parse_project_clj()."""

    def test_parses_defproject(self, tmp_path: Path) -> None:
        """Should parse defproject name and version."""
        proj = tmp_path / 'project.clj'
        proj.write_text('(defproject com.example/my-lib "1.2.3"\n  :description "A library")\n')
        meta = _parse_project_clj(proj)
        assert meta['name'] == 'com.example/my-lib'
        assert meta['version'] == '1.2.3'
        assert meta['group'] == 'com.example'
        assert meta['artifact'] == 'my-lib'

    def test_parses_unqualified_name(self, tmp_path: Path) -> None:
        """Should handle unqualified project names."""
        proj = tmp_path / 'project.clj'
        proj.write_text('(defproject mylib "0.1.0")\n')
        meta = _parse_project_clj(proj)
        assert meta['name'] == 'mylib'
        assert meta['group'] == 'mylib'
        assert meta['artifact'] == 'mylib'

    def test_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        """Should return empty dict for missing file."""
        assert _parse_project_clj(tmp_path / 'project.clj') == {}

    def test_returns_empty_for_malformed_file(self, tmp_path: Path) -> None:
        """Should return empty dict for file without defproject."""
        proj = tmp_path / 'project.clj'
        proj.write_text('(ns my.project)\n')
        assert _parse_project_clj(proj) == {}

    def test_parses_snapshot_version(self, tmp_path: Path) -> None:
        """Should parse SNAPSHOT versions."""
        proj = tmp_path / 'project.clj'
        proj.write_text('(defproject org.example/sample "1.0.0-SNAPSHOT"\n  :dependencies [])\n')
        meta = _parse_project_clj(proj)
        assert meta['version'] == '1.0.0-SNAPSHOT'


class TestParseProjectCljDeps:
    """Tests for _parse_project_clj_deps()."""

    def test_extracts_dependencies(self, tmp_path: Path) -> None:
        """Should extract dependency names from :dependencies."""
        proj = tmp_path / 'project.clj'
        proj.write_text(
            '(defproject com.example/my-lib "1.0.0"\n'
            '  :dependencies [[org.clojure/clojure "1.11.1"]\n'
            '                 [com.example/core "1.0.0"]\n'
            '                 [ring/ring-core "1.10.0"]])\n'
        )
        deps = _parse_project_clj_deps(proj)
        assert 'org.clojure/clojure' in deps
        assert 'com.example/core' in deps
        assert 'ring/ring-core' in deps

    def test_returns_empty_when_no_deps(self, tmp_path: Path) -> None:
        """Should return empty list when no :dependencies."""
        proj = tmp_path / 'project.clj'
        proj.write_text('(defproject mylib "1.0.0")\n')
        assert _parse_project_clj_deps(proj) == []


# Version reading helpers


class TestReadPomVersion:
    """Tests for _read_pom_version()."""

    def test_reads_version(self, tmp_path: Path) -> None:
        """Should read <version> from pom.xml."""
        pom = tmp_path / 'pom.xml'
        pom.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<project>\n'
            '  <groupId>com.example</groupId>\n'
            '  <artifactId>my-lib</artifactId>\n'
            '  <version>1.5.0</version>\n'
            '</project>\n'
        )
        assert _read_pom_version(pom) == '1.5.0'

    def test_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        """Should return empty string for missing file."""
        assert _read_pom_version(tmp_path / 'pom.xml') == ''


class TestReadVersionEdn:
    """Tests for _read_version_edn()."""

    def test_reads_quoted_version(self, tmp_path: Path) -> None:
        """Should read a quoted version string."""
        ver = tmp_path / 'version.edn'
        ver.write_text('"2.0.0"\n')
        assert _read_version_edn(ver) == '2.0.0'

    def test_reads_unquoted_version(self, tmp_path: Path) -> None:
        """Should read an unquoted version string."""
        ver = tmp_path / 'version.edn'
        ver.write_text('3.1.0\n')
        assert _read_version_edn(ver) == '3.1.0'

    def test_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        """Should return empty string for missing file."""
        assert _read_version_edn(tmp_path / 'version.edn') == ''


# Version rewriting


class TestRewriteProjectCljVersion:
    """Tests for _rewrite_project_clj_version()."""

    def test_rewrites_version(self, tmp_path: Path) -> None:
        """Should rewrite the version and return old version."""
        proj = tmp_path / 'project.clj'
        proj.write_text('(defproject com.example/my-lib "1.0.0"\n  :description "A library")\n')
        old = _rewrite_project_clj_version(proj, '2.0.0')
        assert old == '1.0.0'
        text = proj.read_text()
        assert '"2.0.0"' in text
        assert '"1.0.0"' not in text

    def test_preserves_other_content(self, tmp_path: Path) -> None:
        """Should not modify other content."""
        proj = tmp_path / 'project.clj'
        proj.write_text(
            '(defproject com.example/my-lib "1.0.0"\n'
            '  :description "A library"\n'
            '  :dependencies [[org.clojure/clojure "1.11.1"]])\n'
        )
        _rewrite_project_clj_version(proj, '2.0.0')
        text = proj.read_text()
        assert ':description "A library"' in text
        assert 'org.clojure/clojure "1.11.1"' in text

    def test_idempotent(self, tmp_path: Path) -> None:
        """Should be idempotent when called with same version."""
        proj = tmp_path / 'project.clj'
        original = '(defproject mylib "1.0.0")\n'
        proj.write_text(original)
        _rewrite_project_clj_version(proj, '1.0.0')
        assert proj.read_text() == original


class TestRewriteVersionEdn:
    """Tests for _rewrite_version_edn()."""

    def test_rewrites_version(self, tmp_path: Path) -> None:
        """Should rewrite the version and return old version."""
        ver = tmp_path / 'version.edn'
        ver.write_text('"1.0.0"\n')
        old = _rewrite_version_edn(ver, '2.0.0')
        assert old == '1.0.0'
        assert ver.read_text() == '"2.0.0"\n'


# Dependency version rewriting


class TestRewriteProjectCljDepVersion:
    """Tests for _rewrite_project_clj_dep_version()."""

    def test_rewrites_dep_version(self, tmp_path: Path) -> None:
        """Should rewrite a dependency version in project.clj."""
        proj = tmp_path / 'project.clj'
        proj.write_text(
            '(defproject mylib "1.0.0"\n'
            '  :dependencies [[org.clojure/clojure "1.11.1"]\n'
            '                 [com.example/core "1.0.0"]])\n'
        )
        assert _rewrite_project_clj_dep_version(proj, 'com.example/core', '2.0.0')
        text = proj.read_text()
        assert 'com.example/core "2.0.0"' in text
        assert 'org.clojure/clojure "1.11.1"' in text

    def test_returns_false_when_dep_not_found(self, tmp_path: Path) -> None:
        """Should return False when dependency is not found."""
        proj = tmp_path / 'project.clj'
        proj.write_text('(defproject mylib "1.0.0"\n  :dependencies [[org.clojure/clojure "1.11.1"]])\n')
        assert not _rewrite_project_clj_dep_version(proj, 'nonexistent/dep', '1.0.0')


class TestRewriteDepsEdnDepVersion:
    """Tests for _rewrite_deps_edn_dep_version()."""

    def test_rewrites_mvn_dep_version(self, tmp_path: Path) -> None:
        """Should rewrite a Maven dependency version in deps.edn."""
        deps = tmp_path / 'deps.edn'
        deps.write_text(
            '{:deps {org.clojure/clojure {:mvn/version "1.11.1"}\n        com.example/core {:mvn/version "1.0.0"}}}\n'
        )
        assert _rewrite_deps_edn_dep_version(deps, 'com.example/core', '2.0.0')
        text = deps.read_text()
        assert 'com.example/core {:mvn/version "2.0.0"}' in text
        assert 'org.clojure/clojure {:mvn/version "1.11.1"}' in text

    def test_returns_false_when_dep_not_found(self, tmp_path: Path) -> None:
        """Should return False when dependency is not found."""
        deps = tmp_path / 'deps.edn'
        deps.write_text('{:deps {org.clojure/clojure {:mvn/version "1.11.1"}}}\n')
        assert not _rewrite_deps_edn_dep_version(deps, 'nonexistent/dep', '1.0.0')


# ClojureWorkspace.discover() — Leiningen


def _setup_leiningen_workspace(root: Path) -> None:
    """Create a Leiningen multi-project workspace."""
    # Root project.clj (not a sub-project itself).
    (root / 'project.clj').write_text('(defproject com.example/parent "1.0.0"\n  :description "Parent project")\n')

    core = root / 'core'
    core.mkdir()
    (core / 'project.clj').write_text(
        '(defproject com.example/core "1.0.0"\n  :dependencies [[org.clojure/clojure "1.11.1"]])\n'
    )

    plugin = root / 'plugin'
    plugin.mkdir()
    (plugin / 'project.clj').write_text(
        '(defproject com.example/plugin "1.0.0"\n'
        '  :dependencies [[org.clojure/clojure "1.11.1"]\n'
        '                 [com.example/core "1.0.0"]])\n'
    )


class TestClojureWorkspaceDiscoverLeiningen:
    """Tests for ClojureWorkspace.discover() with Leiningen."""

    @pytest.mark.asyncio
    async def test_discovers_leiningen_subprojects(self, tmp_path: Path) -> None:
        """discover() should find Leiningen sub-projects."""
        _setup_leiningen_workspace(tmp_path)
        ws = ClojureWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        names = [p.name for p in packages]
        assert 'core' in names
        assert 'plugin' in names
        assert len(packages) == 2

    @pytest.mark.asyncio
    async def test_classifies_internal_deps(self, tmp_path: Path) -> None:
        """discover() should classify internal dependencies."""
        _setup_leiningen_workspace(tmp_path)
        ws = ClojureWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        plugin = next(p for p in packages if p.name == 'plugin')
        assert 'core' in plugin.internal_deps

    @pytest.mark.asyncio
    async def test_classifies_external_deps(self, tmp_path: Path) -> None:
        """discover() should classify external dependencies."""
        _setup_leiningen_workspace(tmp_path)
        ws = ClojureWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        core = next(p for p in packages if p.name == 'core')
        assert 'org.clojure/clojure' in core.external_deps

    @pytest.mark.asyncio
    async def test_excludes_by_pattern(self, tmp_path: Path) -> None:
        """discover() should exclude projects matching patterns."""
        _setup_leiningen_workspace(tmp_path)
        ws = ClojureWorkspace(workspace_root=tmp_path)
        packages = await ws.discover(exclude_patterns=['plugin'])
        names = [p.name for p in packages]
        assert 'plugin' not in names
        assert 'core' in names

    @pytest.mark.asyncio
    async def test_single_project(self, tmp_path: Path) -> None:
        """discover() should handle a single Leiningen project (no sub-projects)."""
        (tmp_path / 'project.clj').write_text(
            '(defproject com.example/solo "0.5.0"\n  :dependencies [[org.clojure/clojure "1.11.1"]])\n'
        )
        ws = ClojureWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        assert len(packages) == 1
        assert packages[0].name == 'solo'
        assert packages[0].version == '0.5.0'


# ClojureWorkspace.discover() — tools.deps


def _setup_deps_edn_workspace(root: Path) -> None:
    """Create a tools.deps multi-project workspace with :local/root refs."""
    (root / 'deps.edn').write_text(
        '{:deps {my.group/core {:local/root "core"}\n        my.group/plugin {:local/root "plugin"}}}\n'
    )

    core = root / 'core'
    core.mkdir()
    (core / 'deps.edn').write_text('{:deps {org.clojure/clojure {:mvn/version "1.11.1"}}}\n')
    (core / 'pom.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<project>\n'
        '  <groupId>my.group</groupId>\n'
        '  <artifactId>core</artifactId>\n'
        '  <version>1.0.0</version>\n'
        '</project>\n'
    )

    plugin = root / 'plugin'
    plugin.mkdir()
    (plugin / 'deps.edn').write_text(
        '{:deps {org.clojure/clojure {:mvn/version "1.11.1"}\n        my.group/core {:mvn/version "1.0.0"}}}\n'
    )
    (plugin / 'pom.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<project>\n'
        '  <groupId>my.group</groupId>\n'
        '  <artifactId>plugin</artifactId>\n'
        '  <version>1.0.0</version>\n'
        '</project>\n'
    )


class TestClojureWorkspaceDiscoverDepsEdn:
    """Tests for ClojureWorkspace.discover() with tools.deps."""

    @pytest.mark.asyncio
    async def test_discovers_deps_edn_subprojects(self, tmp_path: Path) -> None:
        """discover() should find tools.deps sub-projects via :local/root."""
        _setup_deps_edn_workspace(tmp_path)
        ws = ClojureWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        names = [p.name for p in packages]
        assert 'core' in names
        assert 'plugin' in names
        assert len(packages) == 2

    @pytest.mark.asyncio
    async def test_reads_version_from_pom(self, tmp_path: Path) -> None:
        """discover() should read version from sibling pom.xml."""
        _setup_deps_edn_workspace(tmp_path)
        ws = ClojureWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        core = next(p for p in packages if p.name == 'core')
        assert core.version == '1.0.0'

    @pytest.mark.asyncio
    async def test_classifies_internal_deps(self, tmp_path: Path) -> None:
        """discover() should classify internal deps via pom groupId/artifactId."""
        _setup_deps_edn_workspace(tmp_path)
        ws = ClojureWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        plugin = next(p for p in packages if p.name == 'plugin')
        assert 'core' in plugin.internal_deps

    @pytest.mark.asyncio
    async def test_excludes_by_pattern(self, tmp_path: Path) -> None:
        """discover() should exclude projects matching patterns."""
        _setup_deps_edn_workspace(tmp_path)
        ws = ClojureWorkspace(workspace_root=tmp_path)
        packages = await ws.discover(exclude_patterns=['plugin'])
        names = [p.name for p in packages]
        assert 'plugin' not in names
        assert 'core' in names

    @pytest.mark.asyncio
    async def test_single_project_with_pom(self, tmp_path: Path) -> None:
        """discover() should handle a single deps.edn project with pom.xml."""
        (tmp_path / 'deps.edn').write_text('{:deps {org.clojure/clojure {:mvn/version "1.11.1"}}}\n')
        (tmp_path / 'pom.xml').write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<project>\n'
            '  <artifactId>my-app</artifactId>\n'
            '  <version>0.5.0</version>\n'
            '</project>\n'
        )
        ws = ClojureWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        assert len(packages) == 1
        assert packages[0].name == 'my-app'
        assert packages[0].version == '0.5.0'

    @pytest.mark.asyncio
    async def test_single_project_with_version_edn(self, tmp_path: Path) -> None:
        """discover() should fall back to version.edn for version."""
        (tmp_path / 'deps.edn').write_text('{:deps {org.clojure/clojure {:mvn/version "1.11.1"}}}\n')
        (tmp_path / 'version.edn').write_text('"3.0.0"\n')
        ws = ClojureWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        assert len(packages) == 1
        assert packages[0].version == '3.0.0'

    @pytest.mark.asyncio
    async def test_discovers_subdirs_without_local_root(self, tmp_path: Path) -> None:
        """discover() should scan subdirs for deps.edn when no :local/root."""
        (tmp_path / 'deps.edn').write_text('{:deps {}}\n')
        sub = tmp_path / 'lib'
        sub.mkdir()
        (sub / 'deps.edn').write_text('{:deps {org.clojure/clojure {:mvn/version "1.11.1"}}}\n')
        (sub / 'pom.xml').write_text('<project><artifactId>lib</artifactId><version>1.0.0</version></project>\n')
        ws = ClojureWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        assert len(packages) == 1
        assert packages[0].name == 'lib'


# ClojureWorkspace.rewrite_version()


class TestClojureWorkspaceRewriteVersion:
    """Tests for ClojureWorkspace.rewrite_version()."""

    @pytest.mark.asyncio
    async def test_rewrites_project_clj(self, tmp_path: Path) -> None:
        """rewrite_version() should handle project.clj."""
        proj = tmp_path / 'project.clj'
        proj.write_text('(defproject com.example/my-lib "1.0.0")\n')
        ws = ClojureWorkspace(workspace_root=tmp_path)
        old = await ws.rewrite_version(proj, '2.0.0')
        assert old == '1.0.0'
        assert '"2.0.0"' in proj.read_text()

    @pytest.mark.asyncio
    async def test_rewrites_pom_xml(self, tmp_path: Path) -> None:
        """rewrite_version() should handle pom.xml."""
        pom = tmp_path / 'pom.xml'
        pom.write_text(
            '<project><groupId>com.example</groupId><artifactId>my-lib</artifactId><version>1.0.0</version></project>\n'
        )
        ws = ClojureWorkspace(workspace_root=tmp_path)
        old = await ws.rewrite_version(pom, '2.0.0')
        assert old == '1.0.0'
        assert '<version>2.0.0</version>' in pom.read_text()

    @pytest.mark.asyncio
    async def test_rewrites_version_edn(self, tmp_path: Path) -> None:
        """rewrite_version() should handle version.edn."""
        ver = tmp_path / 'version.edn'
        ver.write_text('"1.0.0"\n')
        ws = ClojureWorkspace(workspace_root=tmp_path)
        old = await ws.rewrite_version(ver, '2.0.0')
        assert old == '1.0.0'
        assert ver.read_text() == '"2.0.0"\n'


# ClojureWorkspace.rewrite_dependency_version()


class TestClojureWorkspaceRewriteDependencyVersion:
    """Tests for ClojureWorkspace.rewrite_dependency_version()."""

    @pytest.mark.asyncio
    async def test_rewrites_project_clj_dep(self, tmp_path: Path) -> None:
        """rewrite_dependency_version() should handle project.clj."""
        proj = tmp_path / 'project.clj'
        proj.write_text('(defproject mylib "1.0.0"\n  :dependencies [[com.example/core "1.0.0"]])\n')
        ws = ClojureWorkspace(workspace_root=tmp_path)
        await ws.rewrite_dependency_version(proj, 'com.example/core', '2.0.0')
        assert 'com.example/core "2.0.0"' in proj.read_text()

    @pytest.mark.asyncio
    async def test_rewrites_deps_edn_dep(self, tmp_path: Path) -> None:
        """rewrite_dependency_version() should handle deps.edn."""
        deps = tmp_path / 'deps.edn'
        deps.write_text('{:deps {com.example/core {:mvn/version "1.0.0"}}}\n')
        ws = ClojureWorkspace(workspace_root=tmp_path)
        await ws.rewrite_dependency_version(deps, 'com.example/core', '2.0.0')
        assert 'com.example/core {:mvn/version "2.0.0"}' in deps.read_text()
