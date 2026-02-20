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

"""Tests for the license tree and Rust-style diagnostic formatting."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.checks._license_tree import (
    LICENSE_TREE_FORMATS,
    DepNode,
    DepStatus,
    LicenseTree,
    PackageTree,
    _Ansi,
    format_license_diagnostic,
    format_license_tree,
    format_license_tree_as,
    license_tree_to_d2,
    license_tree_to_dot,
    license_tree_to_json,
    license_tree_to_mermaid,
    license_tree_to_table,
    should_use_color,
)
from releasekit.checks._universal import (
    LicenseExemptions,
    _check_license_compatibility,
    _find_dep_line,
    _make_source_context,
)
from releasekit.preflight import PreflightResult, SourceContext
from releasekit.workspace import Package


def _ctx_str(result: PreflightResult, key: str, idx: int = 0) -> str:
    """Extract a context value as str (ty sees str | SourceContext)."""
    return str(result.context[key][idx])


def _ctx_tree(result: PreflightResult, key: str, idx: int = 0) -> LicenseTree:
    """Extract a context value as LicenseTree."""
    val = result.context[key][idx]
    assert isinstance(val, str) is False  # noqa: E712
    return val  # type: ignore[return-value]  # runtime LicenseTree


# ── Helpers ──────────────────────────────────────────────────────────


def _make_pkg(
    tmp_path: Path,
    name: str,
    license_value: str = '',
    *,
    is_publishable: bool = True,
    internal_deps: list[str] | None = None,
    external_deps: list[str] | None = None,
    manifest_content: str | None = None,
) -> Package:
    """Create a fake package directory with a pyproject.toml."""
    pkg_dir = tmp_path / name
    pkg_dir.mkdir(exist_ok=True)
    manifest = pkg_dir / 'pyproject.toml'
    if manifest_content is not None:
        manifest.write_text(manifest_content)
    elif license_value:
        manifest.write_text(f'[project]\nname = "{name}"\nlicense = "{license_value}"\n')
    else:
        manifest.write_text(f'[project]\nname = "{name}"\n')
    return Package(
        name=name,
        version='1.0.0',
        path=pkg_dir,
        manifest_path=manifest,
        internal_deps=internal_deps or [],
        external_deps=external_deps or [],
        all_deps=(internal_deps or []) + (external_deps or []),
        is_publishable=is_publishable,
    )


# ── format_license_tree ─────────────────────────────────────────────


class TestFormatLicenseTree:
    """Tests for format License Tree."""

    def test_empty_tree(self) -> None:
        """Test empty tree."""
        tree = LicenseTree(project_license='Apache-2.0')
        text = format_license_tree(tree)
        assert 'Apache-2.0' in text
        assert 'project license' in text

    def test_single_package_no_deps(self) -> None:
        """Test single package no deps."""
        tree = LicenseTree(
            project_license='Apache-2.0',
            packages=[PackageTree(name='myapp', license='Apache-2.0')],
        )
        text = format_license_tree(tree)
        assert 'myapp (Apache-2.0)' in text

    def test_ok_deps_show_checkmark(self) -> None:
        """Test ok deps show checkmark."""
        tree = LicenseTree(
            project_license='Apache-2.0',
            packages=[
                PackageTree(
                    name='myapp',
                    license='Apache-2.0',
                    deps=[
                        DepNode(name='utils', license='MIT', status=DepStatus.OK),
                        DepNode(name='logging', license='BSD-3-Clause', status=DepStatus.OK),
                    ],
                ),
            ],
        )
        text = format_license_tree(tree)
        assert 'utils (MIT) \u2713' in text
        assert 'logging (BSD-3-Clause) \u2713' in text

    def test_incompatible_dep_shows_cross(self) -> None:
        """Test incompatible dep shows cross."""
        tree = LicenseTree(
            project_license='MIT',
            packages=[
                PackageTree(
                    name='myapp',
                    license='MIT',
                    deps=[
                        DepNode(
                            name='gpl-lib',
                            license='GPL-3.0-only',
                            status=DepStatus.INCOMPATIBLE,
                            detail='cannot be used in MIT project',
                        ),
                    ],
                ),
            ],
        )
        text = format_license_tree(tree)
        assert 'gpl-lib (GPL-3.0-only) \u2717 incompatible' in text
        assert 'cannot be used in MIT project' in text

    def test_denied_dep_shows_heavy_cross(self) -> None:
        """Test denied dep shows heavy cross."""
        tree = LicenseTree(
            project_license='Apache-2.0',
            packages=[
                PackageTree(
                    name='myapp',
                    license='Apache-2.0',
                    deps=[
                        DepNode(
                            name='agpl-lib',
                            license='AGPL-3.0-only',
                            status=DepStatus.DENIED,
                            detail='blocked by policy',
                        ),
                    ],
                ),
            ],
        )
        text = format_license_tree(tree)
        assert 'agpl-lib (AGPL-3.0-only) \u2718 denied' in text

    def test_exempt_dep_shows_symbol(self) -> None:
        """Test exempt dep shows symbol."""
        tree = LicenseTree(
            project_license='Apache-2.0',
            packages=[
                PackageTree(
                    name='myapp',
                    license='Apache-2.0',
                    deps=[
                        DepNode(
                            name='oracle-jdbc',
                            license='(exempt)',
                            status=DepStatus.EXEMPT,
                        ),
                    ],
                ),
            ],
        )
        text = format_license_tree(tree)
        assert 'oracle-jdbc ((exempt)) \u2298 exempt' in text

    def test_no_license_dep(self) -> None:
        """Test no license dep."""
        tree = LicenseTree(
            project_license='Apache-2.0',
            packages=[
                PackageTree(
                    name='myapp',
                    license='Apache-2.0',
                    deps=[
                        DepNode(name='unknown-lib', status=DepStatus.NO_LICENSE),
                    ],
                ),
            ],
        )
        text = format_license_tree(tree)
        assert 'unknown-lib' in text
        assert 'no_license' in text

    def test_tree_connectors(self) -> None:
        """Middle deps use \u251c\u2500\u2500, last dep uses \u2514\u2500\u2500."""
        tree = LicenseTree(
            project_license='Apache-2.0',
            packages=[
                PackageTree(
                    name='myapp',
                    license='Apache-2.0',
                    deps=[
                        DepNode(name='a', license='MIT', status=DepStatus.OK),
                        DepNode(name='b', license='ISC', status=DepStatus.OK),
                        DepNode(name='c', license='Zlib', status=DepStatus.OK),
                    ],
                ),
            ],
        )
        text = format_license_tree(tree)
        lines = text.splitlines()
        dep_lines = [ln for ln in lines if 'a (MIT)' in ln or 'b (ISC)' in ln or 'c (Zlib)' in ln]
        assert len(dep_lines) == 3
        # First two use \u251c\u2500\u2500, last uses \u2514\u2500\u2500
        assert dep_lines[0].startswith('\u251c\u2500\u2500')
        assert dep_lines[1].startswith('\u251c\u2500\u2500')
        assert dep_lines[2].startswith('\u2514\u2500\u2500')

    def test_multiple_packages(self) -> None:
        """Test multiple packages."""
        tree = LicenseTree(
            project_license='Apache-2.0',
            packages=[
                PackageTree(
                    name='app-a',
                    license='Apache-2.0',
                    deps=[DepNode(name='lib', license='MIT', status=DepStatus.OK)],
                ),
                PackageTree(
                    name='app-b',
                    license='Apache-2.0',
                    deps=[DepNode(name='lib', license='MIT', status=DepStatus.OK)],
                ),
            ],
        )
        text = format_license_tree(tree)
        assert 'app-a (Apache-2.0)' in text
        assert 'app-b (Apache-2.0)' in text


# ── format_license_diagnostic ───────────────────────────────────────


class TestFormatLicenseDiagnostic:
    """Tests for format License Diagnostic."""

    def test_basic_error(self) -> None:
        """Test basic error."""
        text = format_license_diagnostic(
            severity='error',
            message='license incompatibility',
        )
        assert text.startswith('error[license_compatibility]: license incompatibility')

    def test_with_hint(self) -> None:
        """Test with hint."""
        text = format_license_diagnostic(
            severity='error',
            message='license incompatibility',
            hint='Change the dependency.',
        )
        assert '= hint: Change the dependency.' in text

    def test_warning_severity(self) -> None:
        """Test warning severity."""
        text = format_license_diagnostic(
            severity='warning',
            message='could not resolve license',
        )
        assert text.startswith('warning[license_compatibility]')

    def test_with_source_context_no_file(self) -> None:
        """Test with source context no file."""
        ctx = SourceContext(path='/nonexistent/pyproject.toml', line=5, key='gpl-lib')
        text = format_license_diagnostic(
            severity='error',
            message='incompatible',
            source=ctx,
        )
        assert '--> /nonexistent/pyproject.toml:5' in text

    def test_with_source_context_and_file(self, tmp_path: Path) -> None:
        """Test with source context and file."""
        f = tmp_path / 'pyproject.toml'
        f.write_text('[project]\nname = "myapp"\ndependencies = ["gpl-lib>=1.0"]\nversion = "1.0.0"\n')
        ctx = SourceContext(
            path=str(f),
            line=3,
            key='gpl-lib',
            label='incompatible: GPL-3.0-only',
        )
        text = format_license_diagnostic(
            severity='error',
            message='license incompatibility',
            source=ctx,
            hint='Change the dependency.',
        )
        assert f'--> {f}:3' in text
        # Should contain the source line
        assert 'dependencies = ["gpl-lib>=1.0"]' in text
        # Should contain the underline
        assert '^^^^^^^ incompatible: GPL-3.0-only' in text
        assert '= hint: Change the dependency.' in text

    def test_source_context_line_zero_no_snippet(self) -> None:
        """Test source context line zero no snippet."""
        ctx = SourceContext(path='/some/file.toml', line=0)
        text = format_license_diagnostic(
            severity='error',
            message='test',
            source=ctx,
        )
        assert '--> /some/file.toml' in text
        # No snippet lines when line=0
        assert '|' not in text


# ── _find_dep_line ──────────────────────────────────────────────────


class TestFindDepLine:
    """Tests for find Dep Line."""

    def test_finds_dep_in_manifest(self, tmp_path: Path) -> None:
        """Test finds dep in manifest."""
        f = tmp_path / 'pyproject.toml'
        f.write_text('[project]\nname = "myapp"\ndependencies = ["gpl-lib>=1.0", "other"]\n')
        assert _find_dep_line(f, 'gpl-lib') == 3

    def test_returns_zero_when_not_found(self, tmp_path: Path) -> None:
        """Test returns zero when not found."""
        f = tmp_path / 'pyproject.toml'
        f.write_text('[project]\nname = "myapp"\n')
        assert _find_dep_line(f, 'nonexistent') == 0

    def test_returns_zero_for_missing_file(self, tmp_path: Path) -> None:
        """Test returns zero for missing file."""
        assert _find_dep_line(tmp_path / 'nope.toml', 'anything') == 0


# ── _make_source_context ────────────────────────────────────────────


class TestMakeSourceContext:
    """Tests for make Source Context."""

    def test_creates_context_with_line(self, tmp_path: Path) -> None:
        """Test creates context with line."""
        f = tmp_path / 'pyproject.toml'
        f.write_text('[project]\nname = "myapp"\ndependencies = ["gpl-lib>=1.0"]\n')
        ctx = _make_source_context(f, 'gpl-lib', 'incompatible: GPL-3.0-only')
        assert ctx.path == str(f)
        assert ctx.line == 3
        assert ctx.key == 'gpl-lib'
        assert ctx.label == 'incompatible: GPL-3.0-only'

    def test_creates_context_line_zero_when_not_found(self, tmp_path: Path) -> None:
        """Test creates context line zero when not found."""
        f = tmp_path / 'pyproject.toml'
        f.write_text('[project]\nname = "myapp"\n')
        ctx = _make_source_context(f, 'nonexistent', 'test')
        assert ctx.line == 0


# ── Integration: tree built during check ────────────────────────────


class TestLicenseTreeIntegration:
    """Tests for license Tree Integration."""

    def test_tree_stored_in_result_on_pass(self, tmp_path: Path) -> None:
        """Test tree stored in result on pass."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['lib-a'],
        )
        lib_a = _make_pkg(tmp_path, 'lib-a', 'MIT')
        result = PreflightResult()
        _check_license_compatibility(
            [app, lib_a],
            result,
            project_license='Apache-2.0',
        )
        assert 'license_compatibility' in result.passed
        assert 'license_tree' in result.context
        tree_text = _ctx_str(result, 'license_tree')
        assert 'myapp (Apache-2.0)' in tree_text
        assert 'lib-a (MIT) \u2713' in tree_text

    def test_tree_stored_on_failure(self, tmp_path: Path) -> None:
        """Test tree stored on failure."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'MIT',
            internal_deps=['gpl-lib'],
        )
        gpl_lib = _make_pkg(tmp_path, 'gpl-lib', 'GPL-3.0-only')
        result = PreflightResult()
        _check_license_compatibility(
            [app, gpl_lib],
            result,
            project_license='MIT',
        )
        assert 'license_compatibility' in result.failed
        assert 'license_tree' in result.context
        tree_text = _ctx_str(result, 'license_tree')
        assert 'gpl-lib (GPL-3.0-only) \u2717 incompatible' in tree_text

    def test_tree_shows_exempt_dep(self, tmp_path: Path) -> None:
        """Test tree shows exempt dep."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['oracle-jdbc', 'lib-a'],
        )
        oracle = _make_pkg(tmp_path, 'oracle-jdbc', 'Proprietary')
        lib_a = _make_pkg(tmp_path, 'lib-a', 'MIT')
        result = PreflightResult()
        _check_license_compatibility(
            [app, oracle, lib_a],
            result,
            project_license='Apache-2.0',
            exemptions=LicenseExemptions(
                exempt_packages=frozenset(['oracle-jdbc']),
            ),
        )
        assert 'license_compatibility' in result.passed
        tree_text = _ctx_str(result, 'license_tree')
        assert 'oracle-jdbc ((exempt)) \u2298 exempt' in tree_text
        assert 'lib-a (MIT) \u2713' in tree_text

    def test_violation_context_is_source_context(self, tmp_path: Path) -> None:
        """Violations should produce SourceContext objects, not plain strings."""
        manifest_content = '[project]\nname = "myapp"\nlicense = "MIT"\ndependencies = ["gpl-lib>=1.0"]\n'
        app = _make_pkg(
            tmp_path,
            'myapp',
            'MIT',
            internal_deps=['gpl-lib'],
            manifest_content=manifest_content,
        )
        gpl_lib = _make_pkg(tmp_path, 'gpl-lib', 'GPL-3.0-only')
        result = PreflightResult()
        _check_license_compatibility(
            [app, gpl_lib],
            result,
            project_license='MIT',
        )
        assert 'license_compatibility' in result.failed
        contexts = result.context['license_compatibility']
        assert len(contexts) >= 1
        ctx = contexts[0]
        assert isinstance(ctx, SourceContext)
        assert ctx.key == 'gpl-lib'
        assert ctx.line == 4  # line with "gpl-lib"
        assert 'incompatible' in ctx.label

    def test_tree_with_mixed_statuses(self, tmp_path: Path) -> None:
        """Test tree with mixed statuses."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'MIT',
            internal_deps=['ok-lib', 'bad-lib', 'exempt-lib'],
        )
        ok_lib = _make_pkg(tmp_path, 'ok-lib', 'ISC')
        bad_lib = _make_pkg(tmp_path, 'bad-lib', 'GPL-3.0-only')
        exempt_lib = _make_pkg(tmp_path, 'exempt-lib', 'Proprietary')
        result = PreflightResult()
        _check_license_compatibility(
            [app, ok_lib, bad_lib, exempt_lib],
            result,
            project_license='MIT',
            exemptions=LicenseExemptions(
                exempt_packages=frozenset(['exempt-lib']),
            ),
        )
        assert 'license_compatibility' in result.failed
        tree_text = _ctx_str(result, 'license_tree')
        assert 'ok-lib (ISC) \u2713' in tree_text
        assert 'bad-lib (GPL-3.0-only) \u2717 incompatible' in tree_text
        assert 'exempt-lib ((exempt)) \u2298 exempt' in tree_text


# ── should_use_color ────────────────────────────────────────────────


class TestShouldUseColor:
    """Tests for should Use Color."""

    def test_force_true(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test force true."""
        monkeypatch.delenv('NO_COLOR', raising=False)
        monkeypatch.delenv('FORCE_COLOR', raising=False)
        assert should_use_color(force=True) is True

    def test_force_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test force false."""
        monkeypatch.setenv('FORCE_COLOR', '1')
        assert should_use_color(force=False) is False

    def test_no_color_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test no color env."""
        monkeypatch.setenv('NO_COLOR', '1')
        monkeypatch.delenv('FORCE_COLOR', raising=False)
        assert should_use_color() is False

    def test_force_color_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test force color env."""
        monkeypatch.delenv('NO_COLOR', raising=False)
        monkeypatch.setenv('FORCE_COLOR', '1')
        assert should_use_color() is True

    def test_no_color_takes_precedence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test no color takes precedence."""
        monkeypatch.setenv('NO_COLOR', '1')
        monkeypatch.setenv('FORCE_COLOR', '1')
        assert should_use_color() is False


# ── Colored tree output ─────────────────────────────────────────────


class TestColoredTree:
    """Tests for colored Tree."""

    def test_no_color_has_no_ansi(self) -> None:
        """Test no color has no ansi."""
        tree = LicenseTree(
            project_license='Apache-2.0',
            packages=[
                PackageTree(
                    name='myapp',
                    license='Apache-2.0',
                    deps=[
                        DepNode(name='lib', license='MIT', status=DepStatus.OK),
                    ],
                ),
            ],
        )
        text = format_license_tree(tree, color=False)
        assert '\033[' not in text

    def test_color_has_ansi_codes(self) -> None:
        """Test color has ansi codes."""
        tree = LicenseTree(
            project_license='Apache-2.0',
            packages=[
                PackageTree(
                    name='myapp',
                    license='Apache-2.0',
                    deps=[
                        DepNode(name='lib', license='MIT', status=DepStatus.OK),
                    ],
                ),
            ],
        )
        text = format_license_tree(tree, color=True)
        assert '\033[' in text
        assert _Ansi.RESET in text

    def test_color_ok_is_green(self) -> None:
        """Test color ok is green."""
        tree = LicenseTree(
            project_license='Apache-2.0',
            packages=[
                PackageTree(
                    name='myapp',
                    license='Apache-2.0',
                    deps=[
                        DepNode(name='lib', license='MIT', status=DepStatus.OK),
                    ],
                ),
            ],
        )
        text = format_license_tree(tree, color=True)
        assert _Ansi.GREEN in text

    def test_color_incompatible_is_bold_red(self) -> None:
        """Test color incompatible is bold red."""
        tree = LicenseTree(
            project_license='MIT',
            packages=[
                PackageTree(
                    name='myapp',
                    license='MIT',
                    deps=[
                        DepNode(
                            name='gpl-lib',
                            license='GPL-3.0-only',
                            status=DepStatus.INCOMPATIBLE,
                        ),
                    ],
                ),
            ],
        )
        text = format_license_tree(tree, color=True)
        assert _Ansi.BOLD_RED in text

    def test_color_exempt_is_dim(self) -> None:
        """Test color exempt is dim."""
        tree = LicenseTree(
            project_license='Apache-2.0',
            packages=[
                PackageTree(
                    name='myapp',
                    license='Apache-2.0',
                    deps=[
                        DepNode(
                            name='oracle',
                            license='(exempt)',
                            status=DepStatus.EXEMPT,
                        ),
                    ],
                ),
            ],
        )
        text = format_license_tree(tree, color=True)
        assert _Ansi.DIM in text

    def test_color_header_is_bold_cyan(self) -> None:
        """Test color header is bold cyan."""
        tree = LicenseTree(project_license='Apache-2.0')
        text = format_license_tree(tree, color=True)
        assert _Ansi.BOLD_CYAN in text

    def test_color_package_name_is_bold(self) -> None:
        """Test color package name is bold."""
        tree = LicenseTree(
            project_license='Apache-2.0',
            packages=[
                PackageTree(
                    name='myapp',
                    license='Apache-2.0',
                    deps=[
                        DepNode(name='lib', license='MIT', status=DepStatus.OK),
                    ],
                ),
            ],
        )
        text = format_license_tree(tree, color=True)
        assert _Ansi.BOLD in text


# ── Colored diagnostic output ───────────────────────────────────────


class TestColoredDiagnostic:
    """Tests for colored Diagnostic."""

    def test_no_color_has_no_ansi(self) -> None:
        """Test no color has no ansi."""
        text = format_license_diagnostic(
            severity='error',
            message='test',
            color=False,
        )
        assert '\033[' not in text

    def test_error_has_bold_red(self) -> None:
        """Test error has bold red."""
        text = format_license_diagnostic(
            severity='error',
            message='test',
            color=True,
        )
        assert _Ansi.BOLD_RED in text

    def test_warning_has_bold_yellow(self) -> None:
        """Test warning has bold yellow."""
        text = format_license_diagnostic(
            severity='warning',
            message='test',
            color=True,
        )
        assert _Ansi.BOLD_YELLOW in text

    def test_hint_has_cyan(self) -> None:
        """Test hint has cyan."""
        text = format_license_diagnostic(
            severity='error',
            message='test',
            hint='do something',
            color=True,
        )
        assert _Ansi.BOLD_CYAN in text

    def test_source_has_blue_gutter(self, tmp_path: Path) -> None:
        """Test source has blue gutter."""
        f = tmp_path / 'pyproject.toml'
        f.write_text('[project]\nname = "myapp"\ndependencies = ["gpl-lib>=1.0"]\n')
        ctx = SourceContext(
            path=str(f),
            line=3,
            key='gpl-lib',
            label='incompatible',
        )
        text = format_license_diagnostic(
            severity='error',
            message='test',
            source=ctx,
            color=True,
        )
        assert _Ansi.BLUE in text


# ── Color integration through check ─────────────────────────────────


class TestColorIntegration:
    """Tests for color Integration."""

    def test_color_true_produces_ansi(self, tmp_path: Path) -> None:
        """Test color true produces ansi."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['lib-a'],
        )
        lib_a = _make_pkg(tmp_path, 'lib-a', 'MIT')
        result = PreflightResult()
        _check_license_compatibility(
            [app, lib_a],
            result,
            project_license='Apache-2.0',
            color=True,
        )
        tree_text = _ctx_str(result, 'license_tree')
        assert '\033[' in tree_text

    def test_color_false_no_ansi(self, tmp_path: Path) -> None:
        """Test color false no ansi."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['lib-a'],
        )
        lib_a = _make_pkg(tmp_path, 'lib-a', 'MIT')
        result = PreflightResult()
        _check_license_compatibility(
            [app, lib_a],
            result,
            project_license='Apache-2.0',
            color=False,
        )
        tree_text = _ctx_str(result, 'license_tree')
        assert '\033[' not in tree_text


# ── JSON export ──────────────────────────────────────────────────────


class TestLicenseTreeToJson:
    """Tests for license Tree To Json."""

    def _sample_tree(self) -> LicenseTree:
        """Sample tree."""
        return LicenseTree(
            project_license='Apache-2.0',
            packages=[
                PackageTree(
                    name='myapp',
                    license='Apache-2.0',
                    deps=[
                        DepNode(name='lib-a', license='MIT', status=DepStatus.OK),
                        DepNode(
                            name='gpl-lib',
                            license='GPL-3.0-only',
                            status=DepStatus.INCOMPATIBLE,
                            detail='cannot be used',
                        ),
                    ],
                ),
            ],
        )

    def test_valid_json(self) -> None:
        """Test valid json."""
        import json

        text = license_tree_to_json(self._sample_tree())
        data = json.loads(text)
        assert data['project_license'] == 'Apache-2.0'

    def test_packages_present(self) -> None:
        """Test packages present."""
        import json

        data = json.loads(license_tree_to_json(self._sample_tree()))
        assert len(data['packages']) == 1
        assert data['packages'][0]['name'] == 'myapp'

    def test_deps_serialized(self) -> None:
        """Test deps serialized."""
        import json

        data = json.loads(license_tree_to_json(self._sample_tree()))
        deps = data['packages'][0]['deps']
        assert len(deps) == 2
        assert deps[0]['status'] == 'ok'
        assert deps[1]['status'] == 'incompatible'

    def test_empty_tree(self) -> None:
        """Test empty tree."""
        import json

        data = json.loads(license_tree_to_json(LicenseTree(project_license='MIT')))
        assert data['packages'] == []


# ── ASCII table export ───────────────────────────────────────────────


class TestLicenseTreeToTable:
    """Tests for license Tree To Table."""

    def _sample_tree(self) -> LicenseTree:
        """Sample tree."""
        return LicenseTree(
            project_license='Apache-2.0',
            packages=[
                PackageTree(
                    name='myapp',
                    license='Apache-2.0',
                    deps=[
                        DepNode(name='lib-a', license='MIT', status=DepStatus.OK),
                        DepNode(
                            name='gpl-lib',
                            license='GPL-3.0-only',
                            status=DepStatus.INCOMPATIBLE,
                        ),
                    ],
                ),
            ],
        )

    def test_contains_header_row(self) -> None:
        """Test contains header row."""
        text = license_tree_to_table(self._sample_tree())
        assert 'Package' in text
        assert 'Dependency' in text
        assert 'License' in text
        assert 'Status' in text

    def test_contains_data(self) -> None:
        """Test contains data."""
        text = license_tree_to_table(self._sample_tree())
        assert 'myapp' in text
        assert 'lib-a' in text
        assert 'MIT' in text
        assert 'incompatible' in text

    def test_contains_box_drawing(self) -> None:
        """Test contains box drawing."""
        text = license_tree_to_table(self._sample_tree())
        assert '\u250c' in text  # ┌
        assert '\u2514' in text  # └
        assert '\u2502' in text  # │

    def test_project_license_header(self) -> None:
        """Test project license header."""
        text = license_tree_to_table(self._sample_tree())
        assert 'Project License: Apache-2.0' in text

    def test_empty_tree(self) -> None:
        """Test empty tree."""
        text = license_tree_to_table(LicenseTree(project_license='MIT'))
        assert '(no dependencies)' in text


# ── Mermaid export ───────────────────────────────────────────────────


class TestLicenseTreeToMermaid:
    """Tests for license Tree To Mermaid."""

    def _sample_tree(self) -> LicenseTree:
        """Sample tree."""
        return LicenseTree(
            project_license='Apache-2.0',
            packages=[
                PackageTree(
                    name='myapp',
                    license='Apache-2.0',
                    deps=[
                        DepNode(name='lib-a', license='MIT', status=DepStatus.OK),
                        DepNode(
                            name='gpl-lib',
                            license='GPL-3.0-only',
                            status=DepStatus.INCOMPATIBLE,
                        ),
                    ],
                ),
            ],
        )

    def test_starts_with_flowchart(self) -> None:
        """Test starts with flowchart."""
        text = license_tree_to_mermaid(self._sample_tree())
        assert text.startswith('flowchart TD')

    def test_contains_subgraph(self) -> None:
        """Test contains subgraph."""
        text = license_tree_to_mermaid(self._sample_tree())
        assert 'subgraph' in text
        assert 'end' in text

    def test_contains_nodes_and_edges(self) -> None:
        """Test contains nodes and edges."""
        text = license_tree_to_mermaid(self._sample_tree())
        assert 'myapp' in text
        assert 'lib_a' in text  # hyphens replaced
        assert '-->' in text

    def test_bad_nodes_styled_red(self) -> None:
        """Test bad nodes styled red."""
        text = license_tree_to_mermaid(self._sample_tree())
        assert 'style gpl_lib fill:#f99' in text

    def test_ok_nodes_not_styled(self) -> None:
        """Test ok nodes not styled."""
        text = license_tree_to_mermaid(self._sample_tree())
        assert 'style lib_a' not in text


# ── D2 export ────────────────────────────────────────────────────────


class TestLicenseTreeToD2:
    """Tests for license Tree To D2."""

    def _sample_tree(self) -> LicenseTree:
        """Sample tree."""
        return LicenseTree(
            project_license='Apache-2.0',
            packages=[
                PackageTree(
                    name='myapp',
                    license='Apache-2.0',
                    deps=[
                        DepNode(name='lib-a', license='MIT', status=DepStatus.OK),
                        DepNode(
                            name='gpl-lib',
                            license='GPL-3.0-only',
                            status=DepStatus.INCOMPATIBLE,
                        ),
                    ],
                ),
            ],
        )

    def test_starts_with_direction(self) -> None:
        """Test starts with direction."""
        text = license_tree_to_d2(self._sample_tree())
        assert text.startswith('direction: down')

    def test_contains_project_block(self) -> None:
        """Test contains project block."""
        text = license_tree_to_d2(self._sample_tree())
        assert 'project:' in text
        assert 'Apache-2.0' in text

    def test_contains_edges(self) -> None:
        """Test contains edges."""
        text = license_tree_to_d2(self._sample_tree())
        assert 'myapp -> lib-a' in text
        assert 'myapp -> gpl-lib' in text

    def test_bad_nodes_styled(self) -> None:
        """Test bad nodes styled."""
        text = license_tree_to_d2(self._sample_tree())
        assert 'gpl-lib.style.fill' in text

    def test_ok_nodes_not_styled(self) -> None:
        """Test ok nodes not styled."""
        text = license_tree_to_d2(self._sample_tree())
        assert 'lib-a.style.fill' not in text


# ── DOT export ───────────────────────────────────────────────────────


class TestLicenseTreeToDot:
    """Tests for license Tree To Dot."""

    def _sample_tree(self) -> LicenseTree:
        """Sample tree."""
        return LicenseTree(
            project_license='Apache-2.0',
            packages=[
                PackageTree(
                    name='myapp',
                    license='Apache-2.0',
                    deps=[
                        DepNode(name='lib-a', license='MIT', status=DepStatus.OK),
                        DepNode(
                            name='gpl-lib',
                            license='GPL-3.0-only',
                            status=DepStatus.INCOMPATIBLE,
                        ),
                    ],
                ),
            ],
        )

    def test_starts_with_digraph(self) -> None:
        """Test starts with digraph."""
        text = license_tree_to_dot(self._sample_tree())
        assert text.startswith('digraph license_tree {')

    def test_contains_nodes(self) -> None:
        """Test contains nodes."""
        text = license_tree_to_dot(self._sample_tree())
        assert '"myapp"' in text
        assert '"lib-a"' in text
        assert '"gpl-lib"' in text

    def test_contains_edges(self) -> None:
        """Test contains edges."""
        text = license_tree_to_dot(self._sample_tree())
        assert '"myapp" -> "lib-a"' in text
        assert '"myapp" -> "gpl-lib"' in text

    def test_bad_nodes_red(self) -> None:
        """Test bad nodes red."""
        text = license_tree_to_dot(self._sample_tree())
        assert 'fillcolor="#ffcccc"' in text

    def test_bad_edges_red(self) -> None:
        """Test bad edges red."""
        text = license_tree_to_dot(self._sample_tree())
        assert 'color="#cc0000"' in text


# ── format_license_tree_as dispatcher ────────────────────────────────


class TestFormatLicenseTreeAs:
    """Tests for format License Tree As."""

    def _sample_tree(self) -> LicenseTree:
        """Sample tree."""
        return LicenseTree(
            project_license='Apache-2.0',
            packages=[
                PackageTree(
                    name='myapp',
                    license='Apache-2.0',
                    deps=[
                        DepNode(name='lib-a', license='MIT', status=DepStatus.OK),
                    ],
                ),
            ],
        )

    def test_tree_format(self) -> None:
        """Test tree format."""
        text = format_license_tree_as(self._sample_tree(), 'tree')
        assert '\u251c' in text or '\u2514' in text

    def test_json_format(self) -> None:
        """Test json format."""
        import json

        text = format_license_tree_as(self._sample_tree(), 'json')
        data = json.loads(text)
        assert 'project_license' in data

    def test_table_format(self) -> None:
        """Test table format."""
        text = format_license_tree_as(self._sample_tree(), 'table')
        assert 'Package' in text

    def test_mermaid_format(self) -> None:
        """Test mermaid format."""
        text = format_license_tree_as(self._sample_tree(), 'mermaid')
        assert 'flowchart' in text

    def test_d2_format(self) -> None:
        """Test d2 format."""
        text = format_license_tree_as(self._sample_tree(), 'd2')
        assert 'direction: down' in text

    def test_dot_format(self) -> None:
        """Test dot format."""
        text = format_license_tree_as(self._sample_tree(), 'dot')
        assert 'digraph' in text

    def test_unknown_format_raises(self) -> None:
        """Test unknown format raises."""
        with pytest.raises(ValueError, match='Unknown license tree format'):
            format_license_tree_as(self._sample_tree(), 'csv')

    def test_color_only_affects_tree(self) -> None:
        """Test color only affects tree."""
        text = format_license_tree_as(self._sample_tree(), 'tree', color=True)
        assert '\033[' in text
        for fmt in ('json', 'table', 'mermaid', 'd2', 'dot'):
            text = format_license_tree_as(self._sample_tree(), fmt, color=True)
            assert '\033[' not in text

    def test_all_formats_in_constant(self) -> None:
        """Test all formats in constant."""
        assert LICENSE_TREE_FORMATS == frozenset({'tree', 'json', 'table', 'mermaid', 'd2', 'dot'})


# ── license_tree_obj integration ─────────────────────────────────────


class TestLicenseTreeObjIntegration:
    """Tests for license Tree Obj Integration."""

    def test_tree_obj_stored_in_context(self, tmp_path: Path) -> None:
        """Test tree obj stored in context."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['lib-a'],
        )
        lib_a = _make_pkg(tmp_path, 'lib-a', 'MIT')
        result = PreflightResult()
        _check_license_compatibility(
            [app, lib_a],
            result,
            project_license='Apache-2.0',
        )
        objs = result.context.get('license_tree_obj', [])
        assert len(objs) == 1
        assert isinstance(objs[0], LicenseTree)
        assert objs[0].project_license == 'Apache-2.0'

    def test_tree_obj_can_be_rerendered(self, tmp_path: Path) -> None:
        """Test tree obj can be rerendered."""
        app = _make_pkg(
            tmp_path,
            'myapp',
            'Apache-2.0',
            internal_deps=['lib-a'],
        )
        lib_a = _make_pkg(tmp_path, 'lib-a', 'MIT')
        result = PreflightResult()
        _check_license_compatibility(
            [app, lib_a],
            result,
            project_license='Apache-2.0',
        )
        ltree = _ctx_tree(result, 'license_tree_obj')
        for fmt in LICENSE_TREE_FORMATS:
            text = format_license_tree_as(ltree, fmt)
            assert len(text) > 0
