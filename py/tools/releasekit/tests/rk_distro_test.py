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

"""Tests for releasekit.distro — distro packaging dependency sync.

Pure-function tests where possible; file I/O tests use tmp_path.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.distro import (
    Dep,
    DistroDepDiff,
    _brew_resource_name,
    _debian_pkg_name,
    _fedora_dep_name,
    _parse_brew_resources,
    _parse_debian_runtime_deps,
    _parse_fedora_requires,
    _strip_trailing_zeros,
    check_brew_deps,
    check_debian_deps,
    check_distro_deps,
    check_fedora_deps,
    expected_brew_resources,
    expected_debian_deps,
    expected_fedora_requires,
    fix_brew_formula,
    fix_debian_control,
    fix_distro_deps,
    fix_fedora_spec,
    parse_pyproject_deps,
)

# Dep dataclass


class TestDep:
    """Tests for Dep."""

    def test_frozen(self) -> None:
        """Test frozen."""
        d = Dep(name='aiofiles', min_version='24.1.0')
        with pytest.raises(AttributeError):
            d.name = 'other'  # type: ignore[misc]

    def test_equality(self) -> None:
        """Test equality."""
        a = Dep(name='rich', min_version='13.0.0')
        b = Dep(name='rich', min_version='13.0.0')
        assert a == b


# DistroDepDiff


class TestDistroDepDiff:
    """Tests for Distro Dep Diff."""

    def test_ok_when_empty(self) -> None:
        """Test ok when empty."""
        d = DistroDepDiff(distro='debian', missing=[], extra=[], version_mismatch=[])
        assert d.ok is True

    def test_not_ok_with_missing(self) -> None:
        """Test not ok with missing."""
        d = DistroDepDiff(distro='debian', missing=['python3-foo'], extra=[], version_mismatch=[])
        assert d.ok is False

    def test_not_ok_with_extra(self) -> None:
        """Test not ok with extra."""
        d = DistroDepDiff(distro='fedora', missing=[], extra=['python3dist(bar)'], version_mismatch=[])
        assert d.ok is False

    def test_not_ok_with_version_mismatch(self) -> None:
        """Test not ok with version mismatch."""
        d = DistroDepDiff(
            distro='debian', missing=[], extra=[], version_mismatch=['python3-foo: expected >= 1.0, got >= 2.0']
        )
        assert d.ok is False


# parse_pyproject_deps


class TestParsePyprojectDeps:
    """Tests for Parse Pyproject Deps."""

    def test_basic(self, tmp_path: Path) -> None:
        """Test basic."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '[project]\ndependencies = [\n    "aiofiles>=24.1.0",\n    "rich>=13.0.0",\n    "click>=8.0",\n]\n',
            encoding='utf-8',
        )
        deps = parse_pyproject_deps(pyproject)
        assert len(deps) == 3
        # Sorted by name.
        assert deps[0] == Dep(name='aiofiles', min_version='24.1.0')
        assert deps[1] == Dep(name='click', min_version='8.0')
        assert deps[2] == Dep(name='rich', min_version='13.0.0')

    def test_extras_stripped(self, tmp_path: Path) -> None:
        """Test extras stripped."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '[project]\ndependencies = ["rich[all]>=13.0.0"]\n',
            encoding='utf-8',
        )
        deps = parse_pyproject_deps(pyproject)
        assert len(deps) == 1
        assert deps[0].name == 'rich'
        assert deps[0].min_version == '13.0.0'

    def test_no_version(self, tmp_path: Path) -> None:
        """Test no version."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '[project]\ndependencies = ["requests"]\n',
            encoding='utf-8',
        )
        deps = parse_pyproject_deps(pyproject)
        assert len(deps) == 1
        assert deps[0].min_version == ''

    def test_complex_specifier(self, tmp_path: Path) -> None:
        """Test complex specifier."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text(
            '[project]\ndependencies = ["numpy>=1.24.0,<2.0"]\n',
            encoding='utf-8',
        )
        deps = parse_pyproject_deps(pyproject)
        assert deps[0].min_version == '1.24.0'

    def test_no_project_section(self, tmp_path: Path) -> None:
        """Test no project section."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[tool.ruff]\nline-length = 120\n', encoding='utf-8')
        assert parse_pyproject_deps(pyproject) == []

    def test_no_dependencies_key(self, tmp_path: Path) -> None:
        """Test no dependencies key."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\nname = "foo"\n', encoding='utf-8')
        assert parse_pyproject_deps(pyproject) == []

    def test_empty_dependencies(self, tmp_path: Path) -> None:
        """Test empty dependencies."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\ndependencies = []\n', encoding='utf-8')
        assert parse_pyproject_deps(pyproject) == []


# Debian name conversion (pure)


class TestDebianPkgName:
    """Tests for Debian Pkg Name."""

    def test_simple(self) -> None:
        """Test simple."""
        assert _debian_pkg_name('aiofiles') == 'python3-aiofiles'

    def test_underscore(self) -> None:
        """Test underscore."""
        assert _debian_pkg_name('rich_argparse') == 'python3-rich-argparse'

    def test_dot(self) -> None:
        """Test dot."""
        assert _debian_pkg_name('zope.interface') == 'python3-zope-interface'

    def test_mixed_case(self) -> None:
        """Test mixed case."""
        assert _debian_pkg_name('PyYAML') == 'python3-pyyaml'

    def test_dash(self) -> None:
        """Test dash."""
        assert _debian_pkg_name('rich-argparse') == 'python3-rich-argparse'


# expected_debian_deps (pure)


class TestExpectedDebianDeps:
    """Tests for Expected Debian Deps."""

    def test_with_versions(self) -> None:
        """Test with versions."""
        deps = [
            Dep(name='aiofiles', min_version='24.1.0'),
            Dep(name='click', min_version='8.0'),
        ]
        result = expected_debian_deps(deps)
        assert result == [
            'python3-aiofiles (>= 24.1.0)',
            'python3-click (>= 8.0)',
        ]

    def test_without_version(self) -> None:
        """Test without version."""
        deps = [Dep(name='requests', min_version='')]
        result = expected_debian_deps(deps)
        assert result == ['python3-requests']

    def test_empty(self) -> None:
        """Test empty."""
        assert expected_debian_deps([]) == []


# _parse_debian_runtime_deps (pure — operates on text)


class TestParseDebianRuntimeDeps:
    """Tests for Parse Debian Runtime Deps."""

    def test_basic_control(self) -> None:
        """Test basic control."""
        text = (
            'Source: releasekit\n'
            'Section: python\n'
            '\n'
            'Package: python3-releasekit\n'
            'Depends:\n'
            ' ${python3:Depends},\n'
            ' ${misc:Depends},\n'
            ' python3-aiofiles (>= 24.1.0),\n'
            ' python3-click (>= 8.0)\n'
            'Description: Release tool\n'
        )
        deps = _parse_debian_runtime_deps(text)
        assert deps == [
            'python3-aiofiles (>= 24.1.0)',
            'python3-click (>= 8.0)',
        ]

    def test_skips_substitution_vars(self) -> None:
        """Test skips substitution vars."""
        text = 'Package: foo\nDepends:\n ${python3:Depends},\n ${misc:Depends},\n python3-bar\nDescription: test\n'
        deps = _parse_debian_runtime_deps(text)
        assert deps == ['python3-bar']

    def test_no_binary_package(self) -> None:
        """Test no binary package."""
        text = 'Source: foo\nBuild-Depends: debhelper\n'
        assert _parse_debian_runtime_deps(text) == []

    def test_no_depends(self) -> None:
        """Test no depends."""
        text = 'Package: foo\nDescription: test\n'
        assert _parse_debian_runtime_deps(text) == []

    def test_deps_on_same_line(self) -> None:
        """Test deps on same line."""
        text = 'Package: foo\nDepends: ${misc:Depends}, python3-bar, python3-baz\nDescription: test\n'
        deps = _parse_debian_runtime_deps(text)
        assert deps == ['python3-bar', 'python3-baz']

    def test_sorted_output(self) -> None:
        """Test sorted output."""
        text = 'Package: foo\nDepends:\n python3-zlib,\n python3-aiofiles\nDescription: test\n'
        deps = _parse_debian_runtime_deps(text)
        assert deps == ['python3-aiofiles', 'python3-zlib']


# Fedora helpers (pure)


class TestStripTrailingZeros:
    """Tests for Strip Trailing Zeros."""

    def test_strip_one(self) -> None:
        """Test strip one."""
        assert _strip_trailing_zeros('24.1.0') == '24.1'

    def test_strip_two(self) -> None:
        """Test strip two."""
        assert _strip_trailing_zeros('3.0.0') == '3'

    def test_no_strip(self) -> None:
        """Test no strip."""
        assert _strip_trailing_zeros('24.1') == '24.1'

    def test_single_zero(self) -> None:
        """Test single zero."""
        assert _strip_trailing_zeros('0') == '0'

    def test_leading_zero(self) -> None:
        """Test leading zero."""
        assert _strip_trailing_zeros('0.27.0') == '0.27'

    def test_no_trailing_zero(self) -> None:
        """Test no trailing zero."""
        assert _strip_trailing_zeros('1.2.3') == '1.2.3'


class TestFedoraDepName:
    """Tests for Fedora Dep Name."""

    def test_simple(self) -> None:
        """Test simple."""
        assert _fedora_dep_name('aiofiles') == 'python3dist(aiofiles)'

    def test_uppercase(self) -> None:
        """Test uppercase."""
        assert _fedora_dep_name('PyYAML') == 'python3dist(pyyaml)'


class TestExpectedFedoraRequires:
    """Tests for Expected Fedora Requires."""

    def test_with_versions(self) -> None:
        """Test with versions."""
        deps = [
            Dep(name='aiofiles', min_version='24.1.0'),
            Dep(name='click', min_version='8.0'),
        ]
        result = expected_fedora_requires(deps)
        assert result == [
            'Requires:       python3dist(aiofiles) >= 24.1',
            'Requires:       python3dist(click) >= 8',
        ]

    def test_without_version(self) -> None:
        """Test without version."""
        deps = [Dep(name='requests', min_version='')]
        result = expected_fedora_requires(deps)
        assert result == ['Requires:       python3dist(requests)']

    def test_empty(self) -> None:
        """Test empty."""
        assert expected_fedora_requires([]) == []


class TestParseFedoraRequires:
    """Tests for Parse Fedora Requires."""

    def test_basic(self) -> None:
        """Test basic."""
        text = (
            'Name: releasekit\n'
            '%package -n python3-releasekit\n'
            'Summary: Release tool\n'
            'Requires:       python3dist(aiofiles) >= 24.1\n'
            'Requires:       python3dist(click) >= 8\n'
            '\n'
            '%description\n'
        )
        reqs = _parse_fedora_requires(text)
        assert reqs == [
            'Requires:       python3dist(aiofiles) >= 24.1',
            'Requires:       python3dist(click) >= 8',
        ]

    def test_normalises_whitespace(self) -> None:
        """Test normalises whitespace."""
        text = 'Requires:  python3dist(foo) >= 1.0\n'
        reqs = _parse_fedora_requires(text)
        assert reqs == ['Requires:       python3dist(foo) >= 1.0']

    def test_skips_non_python3dist(self) -> None:
        """Test skips non python3dist."""
        text = 'Requires: bash\nRequires: python3dist(foo)\n'
        reqs = _parse_fedora_requires(text)
        assert reqs == ['Requires:       python3dist(foo)']

    def test_empty(self) -> None:
        """Test empty."""
        assert _parse_fedora_requires('') == []


# check_debian_deps (file I/O)


class TestCheckDebianDeps:
    """Tests for Check Debian Deps."""

    def test_all_match(self, tmp_path: Path) -> None:
        """Test all match."""
        control = tmp_path / 'control'
        control.write_text(
            'Package: python3-foo\nDepends:\n ${python3:Depends},\n python3-aiofiles (>= 24.1.0)\nDescription: test\n',
            encoding='utf-8',
        )
        deps = [Dep(name='aiofiles', min_version='24.1.0')]
        diff = check_debian_deps(control, deps)
        assert diff.ok is True

    def test_missing_dep(self, tmp_path: Path) -> None:
        """Test missing dep."""
        control = tmp_path / 'control'
        control.write_text(
            'Package: python3-foo\nDepends:\n python3-aiofiles (>= 24.1.0)\nDescription: test\n',
            encoding='utf-8',
        )
        deps = [
            Dep(name='aiofiles', min_version='24.1.0'),
            Dep(name='click', min_version='8.0'),
        ]
        diff = check_debian_deps(control, deps)
        assert diff.ok is False
        assert 'python3-click (>= 8.0)' in diff.missing

    def test_extra_dep(self, tmp_path: Path) -> None:
        """Test extra dep."""
        control = tmp_path / 'control'
        control.write_text(
            'Package: python3-foo\nDepends:\n python3-aiofiles (>= 24.1.0),\n python3-obsolete\nDescription: test\n',
            encoding='utf-8',
        )
        deps = [Dep(name='aiofiles', min_version='24.1.0')]
        diff = check_debian_deps(control, deps)
        assert diff.ok is False
        assert 'python3-obsolete' in diff.extra

    def test_version_mismatch(self, tmp_path: Path) -> None:
        """Test version mismatch."""
        control = tmp_path / 'control'
        control.write_text(
            'Package: python3-foo\nDepends:\n python3-aiofiles (>= 20.0.0)\nDescription: test\n',
            encoding='utf-8',
        )
        deps = [Dep(name='aiofiles', min_version='24.1.0')]
        diff = check_debian_deps(control, deps)
        assert diff.ok is False
        assert len(diff.version_mismatch) == 1
        assert 'python3-aiofiles' in diff.version_mismatch[0]


# check_fedora_deps (file I/O)


class TestCheckFedoraDeps:
    """Tests for Check Fedora Deps."""

    def test_all_match(self, tmp_path: Path) -> None:
        """Test all match."""
        spec = tmp_path / 'foo.spec'
        spec.write_text(
            'Name: foo\n'
            '%package -n python3-foo\n'
            'Summary: test\n'
            'Requires:       python3dist(aiofiles) >= 24.1\n'
            '\n'
            '%description\n',
            encoding='utf-8',
        )
        deps = [Dep(name='aiofiles', min_version='24.1.0')]
        diff = check_fedora_deps(spec, deps)
        assert diff.ok is True

    def test_missing_dep(self, tmp_path: Path) -> None:
        """Test missing dep."""
        spec = tmp_path / 'foo.spec'
        spec.write_text(
            'Requires:       python3dist(aiofiles) >= 24.1\n',
            encoding='utf-8',
        )
        deps = [
            Dep(name='aiofiles', min_version='24.1.0'),
            Dep(name='click', min_version='8.0'),
        ]
        diff = check_fedora_deps(spec, deps)
        assert diff.ok is False
        assert any('click' in m for m in diff.missing)

    def test_extra_dep(self, tmp_path: Path) -> None:
        """Test extra dep."""
        spec = tmp_path / 'foo.spec'
        spec.write_text(
            'Requires:       python3dist(aiofiles) >= 24.1\nRequires:       python3dist(obsolete) >= 1.0\n',
            encoding='utf-8',
        )
        deps = [Dep(name='aiofiles', min_version='24.1.0')]
        diff = check_fedora_deps(spec, deps)
        assert diff.ok is False
        assert any('obsolete' in e for e in diff.extra)

    def test_version_mismatch(self, tmp_path: Path) -> None:
        """Test version mismatch."""
        spec = tmp_path / 'foo.spec'
        spec.write_text(
            'Requires:       python3dist(aiofiles) >= 20\n',
            encoding='utf-8',
        )
        deps = [Dep(name='aiofiles', min_version='24.1.0')]
        diff = check_fedora_deps(spec, deps)
        assert diff.ok is False
        assert len(diff.version_mismatch) == 1


# fix_debian_control (file I/O)


class TestFixDebianControl:
    """Tests for Fix Debian Control."""

    def test_adds_missing_dep(self, tmp_path: Path) -> None:
        """Test adds missing dep."""
        control = tmp_path / 'control'
        control.write_text(
            'Source: foo\n'
            '\n'
            'Package: python3-foo\n'
            'Depends:\n'
            ' ${python3:Depends},\n'
            ' ${misc:Depends},\n'
            ' python3-aiofiles (>= 24.1.0)\n'
            'Description: test\n',
            encoding='utf-8',
        )
        deps = [
            Dep(name='aiofiles', min_version='24.1.0'),
            Dep(name='click', min_version='8.0'),
        ]
        changes = fix_debian_control(control, deps)
        assert len(changes) == 1
        new_text = control.read_text(encoding='utf-8')
        assert 'python3-click (>= 8.0)' in new_text
        assert 'python3-aiofiles (>= 24.1.0)' in new_text

    def test_no_change_when_in_sync(self, tmp_path: Path) -> None:
        """Test no change when in sync."""
        control = tmp_path / 'control'
        control.write_text(
            'Package: python3-foo\n'
            'Depends:\n'
            ' ${python3:Depends},\n'
            ' ${misc:Depends},\n'
            ' python3-aiofiles (>= 24.1.0)\n'
            'Description: test\n',
            encoding='utf-8',
        )
        deps = [Dep(name='aiofiles', min_version='24.1.0')]
        changes = fix_debian_control(control, deps)
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry run."""
        control = tmp_path / 'control'
        original = 'Package: python3-foo\nDepends:\n ${python3:Depends},\n ${misc:Depends}\nDescription: test\n'
        control.write_text(original, encoding='utf-8')
        deps = [Dep(name='click', min_version='8.0')]
        changes = fix_debian_control(control, deps, dry_run=True)
        assert len(changes) == 1
        # File should not have changed.
        assert control.read_text(encoding='utf-8') == original

    def test_preserves_substitution_vars(self, tmp_path: Path) -> None:
        """Test preserves substitution vars."""
        control = tmp_path / 'control'
        control.write_text(
            'Package: python3-foo\n'
            'Depends:\n'
            ' ${python3:Depends},\n'
            ' ${misc:Depends},\n'
            ' python3-old\n'
            'Description: test\n',
            encoding='utf-8',
        )
        deps = [Dep(name='new', min_version='1.0')]
        fix_debian_control(control, deps)
        text = control.read_text(encoding='utf-8')
        assert '${python3:Depends}' in text
        assert '${misc:Depends}' in text
        assert 'python3-new (>= 1.0)' in text
        assert 'python3-old' not in text


# fix_fedora_spec (file I/O)


class TestFixFedoraSpec:
    """Tests for Fix Fedora Spec."""

    def test_adds_missing_dep(self, tmp_path: Path) -> None:
        """Test adds missing dep."""
        spec = tmp_path / 'foo.spec'
        spec.write_text(
            'Name: foo\n'
            '\n'
            '%package -n python3-foo\n'
            'Summary: test\n'
            'Requires:       python3dist(aiofiles) >= 24.1\n'
            '\n'
            '%description -n python3-foo\n'
            'Test package.\n',
            encoding='utf-8',
        )
        deps = [
            Dep(name='aiofiles', min_version='24.1.0'),
            Dep(name='click', min_version='8.0'),
        ]
        changes = fix_fedora_spec(spec, deps)
        assert len(changes) == 1
        new_text = spec.read_text(encoding='utf-8')
        assert 'python3dist(click) >= 8' in new_text
        assert 'python3dist(aiofiles) >= 24.1' in new_text

    def test_no_change_when_in_sync(self, tmp_path: Path) -> None:
        """Test no change when in sync."""
        spec = tmp_path / 'foo.spec'
        spec.write_text(
            'Name: foo\nRequires:       python3dist(aiofiles) >= 24.1\n',
            encoding='utf-8',
        )
        deps = [Dep(name='aiofiles', min_version='24.1.0')]
        changes = fix_fedora_spec(spec, deps)
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry run."""
        spec = tmp_path / 'foo.spec'
        original = 'Name: foo\n%package -n python3-foo\nSummary: test\n\n%description -n python3-foo\n'
        spec.write_text(original, encoding='utf-8')
        deps = [Dep(name='click', min_version='8.0')]
        changes = fix_fedora_spec(spec, deps, dry_run=True)
        assert len(changes) == 1
        assert spec.read_text(encoding='utf-8') == original


# check_distro_deps (high-level, file I/O)


def _write_pyproject(path: Path, deps: list[str]) -> None:
    """Helper to write a minimal pyproject.toml."""
    dep_lines = ', '.join(f'"{d}"' for d in deps)
    path.write_text(
        f'[project]\ndependencies = [{dep_lines}]\n',
        encoding='utf-8',
    )


class TestCheckDistroDeps:
    """Tests for Check Distro Deps."""

    def test_finds_debian_and_fedora(self, tmp_path: Path) -> None:
        """Test finds debian and fedora."""
        pyproject = tmp_path / 'pyproject.toml'
        _write_pyproject(pyproject, ['click>=8.0'])

        packaging = tmp_path / 'packaging'
        deb = packaging / 'debian'
        deb.mkdir(parents=True)
        (deb / 'control').write_text(
            'Package: python3-foo\nDepends:\n python3-click (>= 8.0)\nDescription: test\n',
            encoding='utf-8',
        )

        fed = packaging / 'fedora'
        fed.mkdir(parents=True)
        (fed / 'foo.spec').write_text(
            'Requires:       python3dist(click) >= 8\n',
            encoding='utf-8',
        )

        results = check_distro_deps(packaging, pyproject)
        assert len(results) == 2
        assert all(r.ok for r in results)

    def test_no_packaging_dir(self, tmp_path: Path) -> None:
        """Test no packaging dir."""
        pyproject = tmp_path / 'pyproject.toml'
        _write_pyproject(pyproject, ['click>=8.0'])
        packaging = tmp_path / 'packaging'
        packaging.mkdir()
        results = check_distro_deps(packaging, pyproject)
        assert results == []

    def test_no_deps_returns_empty(self, tmp_path: Path) -> None:
        """Test no deps returns empty."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\ndependencies = []\n', encoding='utf-8')
        packaging = tmp_path / 'packaging'
        packaging.mkdir()
        results = check_distro_deps(packaging, pyproject)
        assert results == []

    def test_debian_only(self, tmp_path: Path) -> None:
        """Test debian only."""
        pyproject = tmp_path / 'pyproject.toml'
        _write_pyproject(pyproject, ['requests>=2.0'])

        packaging = tmp_path / 'packaging'
        deb = packaging / 'debian'
        deb.mkdir(parents=True)
        (deb / 'control').write_text(
            'Package: python3-foo\nDepends:\n python3-requests (>= 2.0)\nDescription: test\n',
            encoding='utf-8',
        )

        results = check_distro_deps(packaging, pyproject)
        assert len(results) == 1
        assert results[0].distro == 'debian'
        assert results[0].ok is True

    def test_detects_mismatch(self, tmp_path: Path) -> None:
        """Test detects mismatch."""
        pyproject = tmp_path / 'pyproject.toml'
        _write_pyproject(pyproject, ['click>=8.0', 'rich>=13.0.0'])

        packaging = tmp_path / 'packaging'
        deb = packaging / 'debian'
        deb.mkdir(parents=True)
        (deb / 'control').write_text(
            'Package: python3-foo\nDepends:\n python3-click (>= 8.0)\nDescription: test\n',
            encoding='utf-8',
        )

        results = check_distro_deps(packaging, pyproject)
        assert len(results) == 1
        assert results[0].ok is False
        assert 'python3-rich (>= 13.0.0)' in results[0].missing


# fix_distro_deps (high-level, file I/O)


class TestFixDistroDeps:
    """Tests for Fix Distro Deps."""

    def test_fixes_debian_and_fedora(self, tmp_path: Path) -> None:
        """Test fixes debian and fedora."""
        pyproject = tmp_path / 'pyproject.toml'
        _write_pyproject(pyproject, ['click>=8.0', 'rich>=13.0.0'])

        packaging = tmp_path / 'packaging'
        deb = packaging / 'debian'
        deb.mkdir(parents=True)
        (deb / 'control').write_text(
            'Package: python3-foo\n'
            'Depends:\n'
            ' ${python3:Depends},\n'
            ' ${misc:Depends},\n'
            ' python3-click (>= 8.0)\n'
            'Description: test\n',
            encoding='utf-8',
        )

        fed = packaging / 'fedora'
        fed.mkdir(parents=True)
        (fed / 'foo.spec').write_text(
            'Name: foo\n'
            '%package -n python3-foo\n'
            'Summary: test\n'
            'Requires:       python3dist(click) >= 8\n'
            '\n'
            '%description -n python3-foo\n',
            encoding='utf-8',
        )

        changes = fix_distro_deps(packaging, pyproject)
        assert len(changes) == 2

        deb_text = (deb / 'control').read_text(encoding='utf-8')
        assert 'python3-rich (>= 13.0.0)' in deb_text

        fed_text = (fed / 'foo.spec').read_text(encoding='utf-8')
        assert 'python3dist(rich) >= 13' in fed_text

    def test_no_deps_returns_empty(self, tmp_path: Path) -> None:
        """Test no deps returns empty."""
        pyproject = tmp_path / 'pyproject.toml'
        pyproject.write_text('[project]\ndependencies = []\n', encoding='utf-8')
        packaging = tmp_path / 'packaging'
        packaging.mkdir()
        changes = fix_distro_deps(packaging, pyproject)
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry run."""
        pyproject = tmp_path / 'pyproject.toml'
        _write_pyproject(pyproject, ['click>=8.0'])

        packaging = tmp_path / 'packaging'
        deb = packaging / 'debian'
        deb.mkdir(parents=True)
        original = 'Package: python3-foo\nDepends:\n ${python3:Depends},\n ${misc:Depends}\nDescription: test\n'
        (deb / 'control').write_text(original, encoding='utf-8')

        changes = fix_distro_deps(packaging, pyproject, dry_run=True)
        assert len(changes) == 1
        assert (deb / 'control').read_text(encoding='utf-8') == original


# Homebrew helpers (pure)


class TestBrewResourceName:
    """Tests for _brew_resource_name."""

    def test_simple(self) -> None:
        """Test simple."""
        assert _brew_resource_name('aiofiles') == 'aiofiles'

    def test_underscore(self) -> None:
        """Test underscore."""
        assert _brew_resource_name('rich_argparse') == 'rich-argparse'

    def test_mixed_case(self) -> None:
        """Test mixed case."""
        assert _brew_resource_name('PyYAML') == 'pyyaml'

    def test_dash(self) -> None:
        """Test dash preserved."""
        assert _brew_resource_name('rich-argparse') == 'rich-argparse'


class TestExpectedBrewResources:
    """Tests for expected_brew_resources."""

    def test_sorted(self) -> None:
        """Test sorted output."""
        deps = [
            Dep(name='rich', min_version='13.0.0'),
            Dep(name='aiofiles', min_version='24.1.0'),
        ]
        result = expected_brew_resources(deps)
        assert result == ['aiofiles', 'rich']

    def test_empty(self) -> None:
        """Test empty."""
        assert expected_brew_resources([]) == []


class TestParseBrewResources:
    """Tests for _parse_brew_resources."""

    def test_basic(self) -> None:
        """Test basic."""
        text = (
            'class Foo < Formula\n'
            '  resource "aiofiles" do\n'
            '    url "https://example.com/aiofiles-1.0.tar.gz"\n'
            '    sha256 "abc123"\n'
            '  end\n'
            '  resource "rich" do\n'
            '    url "https://example.com/rich-13.0.tar.gz"\n'
            '    sha256 "def456"\n'
            '  end\n'
            'end\n'
        )
        assert _parse_brew_resources(text) == ['aiofiles', 'rich']

    def test_empty(self) -> None:
        """Test empty."""
        assert _parse_brew_resources('class Foo < Formula\nend\n') == []

    def test_sorted(self) -> None:
        """Test sorted output."""
        text = '  resource "zlib" do\n  end\n  resource "aiofiles" do\n  end\n'
        assert _parse_brew_resources(text) == ['aiofiles', 'zlib']


# check_brew_deps (file I/O)


class TestCheckBrewDeps:
    """Tests for check_brew_deps."""

    def test_all_match(self, tmp_path: Path) -> None:
        """Test all match."""
        formula = tmp_path / 'foo.rb'
        formula.write_text(
            'class Foo < Formula\n'
            '  resource "aiofiles" do\n'
            '    url "https://example.com/aiofiles-24.1.0.tar.gz"\n'
            '    sha256 "abc"\n'
            '  end\n'
            'end\n',
            encoding='utf-8',
        )
        deps = [Dep(name='aiofiles', min_version='24.1.0')]
        diff = check_brew_deps(formula, deps)
        assert diff.ok is True

    def test_missing_dep(self, tmp_path: Path) -> None:
        """Test missing dep."""
        formula = tmp_path / 'foo.rb'
        formula.write_text(
            'class Foo < Formula\n'
            '  resource "aiofiles" do\n'
            '    url "https://example.com/aiofiles-24.1.0.tar.gz"\n'
            '    sha256 "abc"\n'
            '  end\n'
            'end\n',
            encoding='utf-8',
        )
        deps = [
            Dep(name='aiofiles', min_version='24.1.0'),
            Dep(name='click', min_version='8.0'),
        ]
        diff = check_brew_deps(formula, deps)
        assert diff.ok is False
        assert 'click' in diff.missing

    def test_extra_dep(self, tmp_path: Path) -> None:
        """Test extra dep."""
        formula = tmp_path / 'foo.rb'
        formula.write_text(
            'class Foo < Formula\n'
            '  resource "aiofiles" do\n'
            '    url "https://example.com/aiofiles-24.1.0.tar.gz"\n'
            '    sha256 "abc"\n'
            '  end\n'
            '  resource "obsolete" do\n'
            '    url "https://example.com/obsolete-1.0.tar.gz"\n'
            '    sha256 "def"\n'
            '  end\n'
            'end\n',
            encoding='utf-8',
        )
        deps = [Dep(name='aiofiles', min_version='24.1.0')]
        diff = check_brew_deps(formula, deps)
        assert diff.ok is False
        assert 'obsolete' in diff.extra


# fix_brew_formula (file I/O)


class TestFixBrewFormula:
    """Tests for fix_brew_formula."""

    def test_adds_missing_dep(self, tmp_path: Path) -> None:
        """Test adds missing dep."""
        formula = tmp_path / 'foo.rb'
        formula.write_text(
            'class Foo < Formula\n'
            '  desc "Test"\n'
            '  license "Apache-2.0"\n'
            '  depends_on "python@3.13"\n'
            '\n'
            '  resource "aiofiles" do\n'
            '    url "https://example.com/aiofiles-24.1.0.tar.gz"\n'
            '    sha256 "abc"\n'
            '  end\n'
            '\n'
            '  def install\n'
            '    virtualenv_install_with_resources\n'
            '  end\n'
            'end\n',
            encoding='utf-8',
        )
        deps = [
            Dep(name='aiofiles', min_version='24.1.0'),
            Dep(name='click', min_version='8.0'),
        ]
        changes = fix_brew_formula(formula, deps)
        assert len(changes) == 1
        new_text = formula.read_text(encoding='utf-8')
        assert 'resource "aiofiles" do' in new_text
        assert 'resource "click" do' in new_text

    def test_no_change_when_in_sync(self, tmp_path: Path) -> None:
        """Test no change when in sync."""
        formula = tmp_path / 'foo.rb'
        formula.write_text(
            'class Foo < Formula\n'
            '  resource "aiofiles" do\n'
            '    url "https://example.com/aiofiles-24.1.0.tar.gz"\n'
            '    sha256 "abc"\n'
            '  end\n'
            'end\n',
            encoding='utf-8',
        )
        deps = [Dep(name='aiofiles', min_version='24.1.0')]
        changes = fix_brew_formula(formula, deps)
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry run."""
        formula = tmp_path / 'foo.rb'
        original = (
            'class Foo < Formula\n'
            '  depends_on "python@3.13"\n'
            '\n'
            '  def install\n'
            '    virtualenv_install_with_resources\n'
            '  end\n'
            'end\n'
        )
        formula.write_text(original, encoding='utf-8')
        deps = [Dep(name='click', min_version='8.0')]
        changes = fix_brew_formula(formula, deps, dry_run=True)
        assert len(changes) == 1
        assert formula.read_text(encoding='utf-8') == original

    def test_removes_extra_dep(self, tmp_path: Path) -> None:
        """Test removes extra resource and adds correct ones."""
        formula = tmp_path / 'foo.rb'
        formula.write_text(
            'class Foo < Formula\n'
            '  depends_on "python@3.13"\n'
            '\n'
            '  resource "obsolete" do\n'
            '    url "https://example.com/obsolete-1.0.tar.gz"\n'
            '    sha256 "old"\n'
            '  end\n'
            '\n'
            '  def install\n'
            '    virtualenv_install_with_resources\n'
            '  end\n'
            'end\n',
            encoding='utf-8',
        )
        deps = [Dep(name='click', min_version='8.0')]
        changes = fix_brew_formula(formula, deps)
        assert len(changes) == 1
        new_text = formula.read_text(encoding='utf-8')
        assert 'resource "click" do' in new_text
        assert 'obsolete' not in new_text


# check_distro_deps with homebrew (high-level, file I/O)


class TestCheckDistroDepsWithHomebrew:
    """Tests for check_distro_deps including Homebrew."""

    def test_finds_all_three(self, tmp_path: Path) -> None:
        """Test finds debian, fedora, and homebrew."""
        pyproject = tmp_path / 'pyproject.toml'
        _write_pyproject(pyproject, ['click>=8.0'])

        packaging = tmp_path / 'packaging'

        deb = packaging / 'debian'
        deb.mkdir(parents=True)
        (deb / 'control').write_text(
            'Package: python3-foo\nDepends:\n python3-click (>= 8.0)\nDescription: test\n',
            encoding='utf-8',
        )

        fed = packaging / 'fedora'
        fed.mkdir(parents=True)
        (fed / 'foo.spec').write_text(
            'Requires:       python3dist(click) >= 8\n',
            encoding='utf-8',
        )

        brew = packaging / 'homebrew'
        brew.mkdir(parents=True)
        (brew / 'foo.rb').write_text(
            'class Foo < Formula\n'
            '  resource "click" do\n'
            '    url "https://example.com/click-8.0.tar.gz"\n'
            '    sha256 "abc"\n'
            '  end\n'
            'end\n',
            encoding='utf-8',
        )

        results = check_distro_deps(packaging, pyproject)
        assert len(results) == 3
        assert all(r.ok for r in results)
        distros = {r.distro for r in results}
        assert distros == {'debian', 'fedora', 'homebrew'}

    def test_homebrew_only(self, tmp_path: Path) -> None:
        """Test homebrew only."""
        pyproject = tmp_path / 'pyproject.toml'
        _write_pyproject(pyproject, ['requests>=2.0'])

        packaging = tmp_path / 'packaging'
        brew = packaging / 'homebrew'
        brew.mkdir(parents=True)
        (brew / 'foo.rb').write_text(
            'class Foo < Formula\n'
            '  resource "requests" do\n'
            '    url "https://example.com/requests-2.0.tar.gz"\n'
            '    sha256 "abc"\n'
            '  end\n'
            'end\n',
            encoding='utf-8',
        )

        results = check_distro_deps(packaging, pyproject)
        assert len(results) == 1
        assert results[0].distro == 'homebrew'
        assert results[0].ok is True


# fix_distro_deps with homebrew (high-level, file I/O)


class TestFixDistroDepsWithHomebrew:
    """Tests for fix_distro_deps including Homebrew."""

    def test_fixes_all_three(self, tmp_path: Path) -> None:
        """Test fixes debian, fedora, and homebrew."""
        pyproject = tmp_path / 'pyproject.toml'
        _write_pyproject(pyproject, ['click>=8.0', 'rich>=13.0.0'])

        packaging = tmp_path / 'packaging'

        deb = packaging / 'debian'
        deb.mkdir(parents=True)
        (deb / 'control').write_text(
            'Package: python3-foo\n'
            'Depends:\n'
            ' ${python3:Depends},\n'
            ' ${misc:Depends},\n'
            ' python3-click (>= 8.0)\n'
            'Description: test\n',
            encoding='utf-8',
        )

        fed = packaging / 'fedora'
        fed.mkdir(parents=True)
        (fed / 'foo.spec').write_text(
            'Name: foo\n'
            '%package -n python3-foo\n'
            'Summary: test\n'
            'Requires:       python3dist(click) >= 8\n'
            '\n'
            '%description -n python3-foo\n',
            encoding='utf-8',
        )

        brew = packaging / 'homebrew'
        brew.mkdir(parents=True)
        (brew / 'foo.rb').write_text(
            'class Foo < Formula\n'
            '  depends_on "python@3.13"\n'
            '\n'
            '  resource "click" do\n'
            '    url "https://example.com/click-8.0.tar.gz"\n'
            '    sha256 "abc"\n'
            '  end\n'
            '\n'
            '  def install\n'
            '    virtualenv_install_with_resources\n'
            '  end\n'
            'end\n',
            encoding='utf-8',
        )

        changes = fix_distro_deps(packaging, pyproject)
        assert len(changes) == 3

        brew_text = (brew / 'foo.rb').read_text(encoding='utf-8')
        assert 'resource "rich" do' in brew_text
        assert 'resource "click" do' in brew_text
