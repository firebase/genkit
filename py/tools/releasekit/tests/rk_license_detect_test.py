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

"""Tests for license detection from package manifests."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Coroutine
from pathlib import Path
from typing import TypeVar

from releasekit.backends.workspace.bazel import BazelWorkspace
from releasekit.backends.workspace.cargo import CargoWorkspace
from releasekit.backends.workspace.clojure import ClojureWorkspace
from releasekit.backends.workspace.dart import DartWorkspace
from releasekit.backends.workspace.go import GoWorkspace
from releasekit.backends.workspace.maven import MavenWorkspace
from releasekit.backends.workspace.pnpm import PnpmWorkspace
from releasekit.backends.workspace.uv import UvWorkspace
from releasekit.checks._license_detect import (
    DetectedLicense,
    detect_license,
    detect_license_from_path,
)

# ── Python (pyproject.toml) ──────────────────────────────────────────


class TestPythonDetection:
    """Tests for python Detection."""

    def test_pep639_string_license(self, tmp_path: Path) -> None:
        """Test pep639 string license."""
        (tmp_path / 'pyproject.toml').write_text('[project]\nname = "mypkg"\nlicense = "Apache-2.0"\n')
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.found
        assert r.value == 'Apache-2.0'
        assert 'pyproject.toml' in r.source
        assert r.package_name == 'mypkg'

    def test_legacy_license_table(self, tmp_path: Path) -> None:
        """Test legacy license table."""
        (tmp_path / 'pyproject.toml').write_text('[project]\nname = "mypkg"\n[project.license]\ntext = "MIT License"\n')
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.found
        assert r.value == 'MIT License'
        assert 'license.text' in r.source

    def test_classifier_fallback(self, tmp_path: Path) -> None:
        """Test classifier fallback."""
        (tmp_path / 'pyproject.toml').write_text(
            '[project]\nname = "mypkg"\n'
            'classifiers = [\n'
            '    "License :: OSI Approved :: MIT License",\n'
            '    "Programming Language :: Python :: 3",\n'
            ']\n'
        )
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.found
        assert r.value == 'License :: OSI Approved :: MIT License'
        assert 'classifier' in r.source

    def test_pep639_takes_priority_over_classifier(self, tmp_path: Path) -> None:
        """Test pep639 takes priority over classifier."""
        (tmp_path / 'pyproject.toml').write_text(
            '[project]\nname = "mypkg"\nlicense = "Apache-2.0"\n'
            'classifiers = ["License :: OSI Approved :: MIT License"]\n'
        )
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.value == 'Apache-2.0'

    def test_no_license_field(self, tmp_path: Path) -> None:
        """Test no license field."""
        (tmp_path / 'pyproject.toml').write_text('[project]\nname = "mypkg"\n')
        r = detect_license_from_path(tmp_path, 'mypkg')
        # Falls through to LICENSE file detection.
        assert not r.found

    def test_empty_license_string(self, tmp_path: Path) -> None:
        """Test empty license string."""
        (tmp_path / 'pyproject.toml').write_text('[project]\nname = "mypkg"\nlicense = ""\n')
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert not r.found

    def test_spdx_expression(self, tmp_path: Path) -> None:
        """Test spdx expression."""
        (tmp_path / 'pyproject.toml').write_text('[project]\nname = "mypkg"\nlicense = "MIT OR Apache-2.0"\n')
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.value == 'MIT OR Apache-2.0'


# ── JavaScript (package.json) ────────────────────────────────────────


class TestJsDetection:
    """Tests for js Detection."""

    def test_string_license(self, tmp_path: Path) -> None:
        """Test string license."""
        (tmp_path / 'package.json').write_text(json.dumps({'name': 'mypkg', 'license': 'MIT'}))
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.found
        assert r.value == 'MIT'
        assert r.source == 'package.json'

    def test_spdx_expression(self, tmp_path: Path) -> None:
        """Test spdx expression."""
        (tmp_path / 'package.json').write_text(json.dumps({'name': 'mypkg', 'license': 'MIT OR Apache-2.0'}))
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.value == 'MIT OR Apache-2.0'

    def test_legacy_object_form(self, tmp_path: Path) -> None:
        """Test legacy object form."""
        (tmp_path / 'package.json').write_text(
            json.dumps({
                'name': 'mypkg',
                'license': {'type': 'ISC', 'url': 'https://...'},
            })
        )
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.value == 'ISC'
        assert 'license.type' in r.source

    def test_deprecated_licenses_array(self, tmp_path: Path) -> None:
        """Test deprecated licenses array."""
        (tmp_path / 'package.json').write_text(
            json.dumps({
                'name': 'mypkg',
                'licenses': [{'type': 'BSD-3-Clause'}],
            })
        )
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.value == 'BSD-3-Clause'
        assert 'licenses[0]' in r.source

    def test_no_license_field(self, tmp_path: Path) -> None:
        """Test no license field."""
        (tmp_path / 'package.json').write_text(json.dumps({'name': 'mypkg'}))
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert not r.found

    def test_invalid_json(self, tmp_path: Path) -> None:
        """Test invalid json."""
        (tmp_path / 'package.json').write_text('{invalid json}')
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert not r.found


# ── Rust (Cargo.toml) ────────────────────────────────────────────────


class TestRustDetection:
    """Tests for rust Detection."""

    def test_package_license(self, tmp_path: Path) -> None:
        """Test package license."""
        (tmp_path / 'Cargo.toml').write_text(
            '[package]\nname = "mypkg"\nversion = "0.1.0"\nlicense = "MIT OR Apache-2.0"\n'
        )
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.found
        assert r.value == 'MIT OR Apache-2.0'
        assert 'Cargo.toml' in r.source

    def test_no_license(self, tmp_path: Path) -> None:
        """Test no license."""
        (tmp_path / 'Cargo.toml').write_text('[package]\nname = "mypkg"\nversion = "0.1.0"\n')
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert not r.found


# ── Java (pom.xml) ───────────────────────────────────────────────────


class TestJavaDetection:
    """Tests for java Detection."""

    def test_pom_license(self, tmp_path: Path) -> None:
        """Test pom license."""
        (tmp_path / 'pom.xml').write_text(
            '<project>\n'
            '  <licenses>\n'
            '    <license>\n'
            '      <name>Apache License, Version 2.0</name>\n'
            '    </license>\n'
            '  </licenses>\n'
            '</project>\n'
        )
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.found
        assert r.value == 'Apache License, Version 2.0'
        assert r.source == 'pom.xml'

    def test_no_pom(self, tmp_path: Path) -> None:
        """Test no pom."""
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert not r.found


# ── LICENSE file fallback ────────────────────────────────────────────


class TestLicenseFileDetection:
    """Tests for license File Detection."""

    def test_apache_license_file(self, tmp_path: Path) -> None:
        """Test apache license file."""
        (tmp_path / 'LICENSE').write_text('Apache License\nVersion 2.0, January 2004\n...')
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.found
        assert r.value == 'Apache-2.0'
        assert r.source == 'LICENSE'

    def test_mit_license_file(self, tmp_path: Path) -> None:
        """Test mit license file."""
        (tmp_path / 'LICENSE').write_text(
            'MIT License\n\nCopyright (c) 2024 ...\n\nPermission is hereby granted, free of charge...'
        )
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.value == 'MIT'

    def test_gpl3_license_file(self, tmp_path: Path) -> None:
        """Test gpl3 license file."""
        (tmp_path / 'COPYING').write_text('GNU GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007\n...')
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.value == 'GPL-3.0-only'
        assert r.source == 'COPYING'

    def test_bsl_license_file(self, tmp_path: Path) -> None:
        """Test bsl license file."""
        (tmp_path / 'LICENSE.txt').write_text('Boost Software License - Version 1.0\n...')
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.value == 'BSL-1.0'

    def test_unlicense_file(self, tmp_path: Path) -> None:
        """Test unlicense file."""
        (tmp_path / 'LICENSE').write_text(
            'This is free and unencumbered software released into the public domain.\nThe Unlicense\n...'
        )
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.value == 'Unlicense'

    def test_licence_spelling(self, tmp_path: Path) -> None:
        """Test licence spelling."""
        (tmp_path / 'LICENCE').write_text('MIT License\n...')
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.value == 'MIT'
        assert r.source == 'LICENCE'

    def test_license_md(self, tmp_path: Path) -> None:
        """Test license md."""
        (tmp_path / 'LICENSE.md').write_text('# MIT License\n...')
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.value == 'MIT'

    def test_no_license_file(self, tmp_path: Path) -> None:
        """Test no license file."""
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert not r.found
        assert r.value == ''
        assert r.source == ''

    def test_unrecognized_license_content(self, tmp_path: Path) -> None:
        """Test unrecognized license content."""
        (tmp_path / 'LICENSE').write_text('This is a custom proprietary license.\nAll rights reserved.\n')
        r = detect_license_from_path(tmp_path, 'mypkg')
        # Custom text doesn't match any pattern.
        assert not r.found


# ── Priority: manifest > LICENSE file ────────────────────────────────


class TestDetectionPriority:
    """Tests for detection Priority."""

    def test_pyproject_takes_priority_over_license_file(self, tmp_path: Path) -> None:
        """Test pyproject takes priority over license file."""
        (tmp_path / 'pyproject.toml').write_text('[project]\nname = "mypkg"\nlicense = "Apache-2.0"\n')
        (tmp_path / 'LICENSE').write_text('MIT License\n...')
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.value == 'Apache-2.0'

    def test_package_json_takes_priority_over_license_file(self, tmp_path: Path) -> None:
        """Test package json takes priority over license file."""
        (tmp_path / 'package.json').write_text(json.dumps({'name': 'mypkg', 'license': 'ISC'}))
        (tmp_path / 'LICENSE').write_text('MIT License\n...')
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.value == 'ISC'

    def test_cargo_takes_priority_over_license_file(self, tmp_path: Path) -> None:
        """Test cargo takes priority over license file."""
        (tmp_path / 'Cargo.toml').write_text(
            '[package]\nname = "mypkg"\nversion = "0.1.0"\nlicense = "MIT OR Apache-2.0"\n'
        )
        (tmp_path / 'LICENSE').write_text('Apache License\n...')
        r = detect_license_from_path(tmp_path, 'mypkg')
        assert r.value == 'MIT OR Apache-2.0'


# ── detect_license() with Package-like object ───────────────────────


class TestDetectLicenseApi:
    """Tests for detect License Api."""

    def test_with_package_like_object(self, tmp_path: Path) -> None:
        """Test with package like object."""
        (tmp_path / 'package.json').write_text(json.dumps({'name': 'test-pkg', 'license': 'MIT'}))

        class FakePkg:
            """Tests for fake Pkg."""

            path = tmp_path
            name = 'test-pkg'

        r = detect_license(FakePkg())
        assert r.found
        assert r.value == 'MIT'
        assert r.package_name == 'test-pkg'

    def test_default_name_from_path(self, tmp_path: Path) -> None:
        """Test default name from path."""
        r = detect_license_from_path(tmp_path)
        assert r.package_name == tmp_path.name


# ── DetectedLicense properties ───────────────────────────────────────


class TestDetectedLicenseProperties:
    """Tests for detected License Properties."""

    def test_found_true(self) -> None:
        """Test found true."""
        r = DetectedLicense(value='MIT', source='package.json', package_name='x')
        assert r.found is True

    def test_found_false(self) -> None:
        """Test found false."""
        r = DetectedLicense(value='', source='', package_name='x')
        assert r.found is False


# ── Workspace backend detect_license methods ─────────────────────────


_T = TypeVar('_T')


def _run(coro: Coroutine[object, object, _T]) -> _T:
    """Run."""
    return asyncio.run(coro)


class TestPnpmDetectLicense:
    """Tests for pnpm Detect License."""

    def test_standard_license_field(self, tmp_path: Path) -> None:
        """Test standard license field."""
        (tmp_path / 'package.json').write_text(json.dumps({'name': 'mypkg', 'license': 'MIT'}))
        ws = PnpmWorkspace.__new__(PnpmWorkspace)
        r = _run(ws.detect_license(tmp_path, 'mypkg'))
        assert r.found
        assert r.value == 'MIT'
        assert r.source == 'package.json'

    def test_legacy_object_license(self, tmp_path: Path) -> None:
        """Test legacy object license."""
        (tmp_path / 'package.json').write_text(json.dumps({'name': 'mypkg', 'license': {'type': 'Apache-2.0'}}))
        ws = PnpmWorkspace.__new__(PnpmWorkspace)
        r = _run(ws.detect_license(tmp_path, 'mypkg'))
        assert r.found
        assert r.value == 'Apache-2.0'

    def test_deprecated_licenses_array(self, tmp_path: Path) -> None:
        """Test deprecated licenses array."""
        (tmp_path / 'package.json').write_text(json.dumps({'name': 'mypkg', 'licenses': [{'type': 'BSD-3-Clause'}]}))
        ws = PnpmWorkspace.__new__(PnpmWorkspace)
        r = _run(ws.detect_license(tmp_path, 'mypkg'))
        assert r.found
        assert r.value == 'BSD-3-Clause'

    def test_no_package_json(self, tmp_path: Path) -> None:
        """Test no package json."""
        ws = PnpmWorkspace.__new__(PnpmWorkspace)
        r = _run(ws.detect_license(tmp_path, 'mypkg'))
        assert not r.found

    def test_no_license_field(self, tmp_path: Path) -> None:
        """Test no license field."""
        (tmp_path / 'package.json').write_text(json.dumps({'name': 'mypkg'}))
        ws = PnpmWorkspace.__new__(PnpmWorkspace)
        r = _run(ws.detect_license(tmp_path, 'mypkg'))
        assert not r.found

    def test_default_pkg_name_from_path(self, tmp_path: Path) -> None:
        """Test default pkg name from path."""
        ws = PnpmWorkspace.__new__(PnpmWorkspace)
        r = _run(ws.detect_license(tmp_path))
        assert r.package_name == tmp_path.name


class TestCargoDetectLicense:
    """Tests for cargo Detect License."""

    def test_cargo_toml_license(self, tmp_path: Path) -> None:
        """Test cargo toml license."""
        (tmp_path / 'Cargo.toml').write_text(
            '[package]\nname = "mycrate"\nversion = "0.1.0"\nlicense = "MIT OR Apache-2.0"\n'
        )
        ws = CargoWorkspace.__new__(CargoWorkspace)
        r = _run(ws.detect_license(tmp_path, 'mycrate'))
        assert r.found
        assert r.value == 'MIT OR Apache-2.0'
        assert 'Cargo.toml' in r.source

    def test_no_cargo_toml(self, tmp_path: Path) -> None:
        """Test no cargo toml."""
        ws = CargoWorkspace.__new__(CargoWorkspace)
        r = _run(ws.detect_license(tmp_path, 'mycrate'))
        assert not r.found

    def test_no_license_field(self, tmp_path: Path) -> None:
        """Test no license field."""
        (tmp_path / 'Cargo.toml').write_text('[package]\nname = "mycrate"\nversion = "0.1.0"\n')
        ws = CargoWorkspace.__new__(CargoWorkspace)
        r = _run(ws.detect_license(tmp_path, 'mycrate'))
        assert not r.found


class TestMavenDetectLicense:
    """Tests for maven Detect License."""

    def test_pom_xml_license(self, tmp_path: Path) -> None:
        """Test pom xml license."""
        (tmp_path / 'pom.xml').write_text(
            '<project>\n'
            '  <licenses>\n'
            '    <license>\n'
            '      <name>Apache-2.0</name>\n'
            '    </license>\n'
            '  </licenses>\n'
            '</project>\n'
        )
        ws = MavenWorkspace.__new__(MavenWorkspace)
        r = _run(ws.detect_license(tmp_path, 'mylib'))
        assert r.found
        assert r.value == 'Apache-2.0'
        assert r.source == 'pom.xml'

    def test_no_pom_xml(self, tmp_path: Path) -> None:
        """Test no pom xml."""
        ws = MavenWorkspace.__new__(MavenWorkspace)
        r = _run(ws.detect_license(tmp_path, 'mylib'))
        assert not r.found


class TestUvDetectLicense:
    """Tests for uv Detect License."""

    def test_pep639_string(self, tmp_path: Path) -> None:
        """Test pep639 string."""
        (tmp_path / 'pyproject.toml').write_text('[project]\nname = "mypkg"\nlicense = "Apache-2.0"\n')
        ws = UvWorkspace.__new__(UvWorkspace)
        r = _run(ws.detect_license(tmp_path, 'mypkg'))
        assert r.found
        assert r.value == 'Apache-2.0'

    def test_legacy_table(self, tmp_path: Path) -> None:
        """Test legacy table."""
        (tmp_path / 'pyproject.toml').write_text('[project]\nname = "mypkg"\n[project.license]\ntext = "MIT"\n')
        ws = UvWorkspace.__new__(UvWorkspace)
        r = _run(ws.detect_license(tmp_path, 'mypkg'))
        assert r.found
        assert r.value == 'MIT'

    def test_classifier_fallback(self, tmp_path: Path) -> None:
        """Test classifier fallback."""
        (tmp_path / 'pyproject.toml').write_text(
            '[project]\nname = "mypkg"\nclassifiers = [\n  "License :: OSI Approved :: MIT License",\n]\n'
        )
        ws = UvWorkspace.__new__(UvWorkspace)
        r = _run(ws.detect_license(tmp_path, 'mypkg'))
        assert r.found
        assert 'License ::' in r.value

    def test_no_pyproject(self, tmp_path: Path) -> None:
        """Test no pyproject."""
        ws = UvWorkspace.__new__(UvWorkspace)
        r = _run(ws.detect_license(tmp_path, 'mypkg'))
        assert not r.found


class TestFallbackBackendsDetectLicense:
    """Go, Dart, Bazel, Clojure have no manifest license field."""

    def test_go_returns_empty(self, tmp_path: Path) -> None:
        """Test go returns empty."""
        ws = GoWorkspace.__new__(GoWorkspace)
        r = _run(ws.detect_license(tmp_path, 'mymod'))
        assert not r.found
        assert r.package_name == 'mymod'

    def test_dart_returns_empty(self, tmp_path: Path) -> None:
        """Test dart returns empty."""
        ws = DartWorkspace.__new__(DartWorkspace)
        r = _run(ws.detect_license(tmp_path, 'mypkg'))
        assert not r.found

    def test_bazel_returns_empty(self, tmp_path: Path) -> None:
        """Test bazel returns empty."""
        ws = BazelWorkspace.__new__(BazelWorkspace)
        r = _run(ws.detect_license(tmp_path, 'mymod'))
        assert not r.found

    def test_clojure_returns_empty(self, tmp_path: Path) -> None:
        """Test clojure returns empty."""
        ws = ClojureWorkspace.__new__(ClojureWorkspace)
        r = _run(ws.detect_license(tmp_path, 'mylib'))
        assert not r.found
