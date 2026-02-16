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

"""Tests for ecosystem-specific check backends and the factory function."""

from __future__ import annotations

import json
from pathlib import Path

from releasekit.checks import (
    BaseCheckBackend,
    DartCheckBackend,
    GoCheckBackend,
    JavaCheckBackend,
    JsCheckBackend,
    PythonCheckBackend,
    RustCheckBackend,
    get_check_backend,
)
from releasekit.logging import configure_logging
from releasekit.preflight import PreflightResult
from releasekit.workspace import Package

configure_logging(quiet=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pkg(
    name: str,
    version: str = '1.0.0',
    path: Path | None = None,
    manifest_path: Path | None = None,
    internal_deps: list[str] | None = None,
    external_deps: list[str] | None = None,
    all_deps: list[str] | None = None,
    is_publishable: bool = True,
) -> Package:
    """Create a test Package."""
    p = path or Path('/fake') / name
    return Package(
        name=name,
        version=version,
        path=p,
        manifest_path=manifest_path or p / 'pom.xml',
        internal_deps=internal_deps or [],
        external_deps=external_deps or [],
        all_deps=all_deps or [],
        is_publishable=is_publishable,
    )


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


class TestGetCheckBackend:
    """Tests for get_check_backend() factory."""

    def test_returns_python_for_python(self) -> None:
        """Test returns PythonCheckBackend for python ecosystem."""
        backend = get_check_backend('python')
        assert isinstance(backend, PythonCheckBackend)

    def test_returns_java_for_java(self) -> None:
        """Test returns JavaCheckBackend for java ecosystem."""
        backend = get_check_backend('java')
        assert isinstance(backend, JavaCheckBackend)

    def test_returns_java_for_kotlin(self) -> None:
        """Test returns JavaCheckBackend for kotlin ecosystem."""
        backend = get_check_backend('kotlin')
        assert isinstance(backend, JavaCheckBackend)

    def test_returns_go_for_go(self) -> None:
        """Test returns GoCheckBackend for go ecosystem."""
        backend = get_check_backend('go')
        assert isinstance(backend, GoCheckBackend)

    def test_returns_rust_for_rust(self) -> None:
        """Test returns RustCheckBackend for rust ecosystem."""
        backend = get_check_backend('rust')
        assert isinstance(backend, RustCheckBackend)

    def test_returns_js_for_js(self) -> None:
        """Test returns JsCheckBackend for js ecosystem."""
        backend = get_check_backend('js')
        assert isinstance(backend, JsCheckBackend)

    def test_returns_dart_for_dart(self) -> None:
        """Test returns DartCheckBackend for dart ecosystem."""
        backend = get_check_backend('dart')
        assert isinstance(backend, DartCheckBackend)

    def test_returns_base_for_unknown(self) -> None:
        """Test returns BaseCheckBackend for unknown ecosystem."""
        backend = get_check_backend('unknown')
        assert type(backend) is BaseCheckBackend

    def test_passes_kwargs(self) -> None:
        """Test passes kwargs to backend constructor."""
        backend = get_check_backend('java', core_package='core')
        assert isinstance(backend, JavaCheckBackend)
        assert backend._core_package == 'core'


# ---------------------------------------------------------------------------
# BaseCheckBackend tests
# ---------------------------------------------------------------------------


class TestBaseCheckBackend:
    """Tests for BaseCheckBackend no-op defaults."""

    def test_all_checks_pass(self) -> None:
        """Test all checks pass by default."""
        backend = BaseCheckBackend()
        result = PreflightResult()
        packages = [_pkg('test')]
        backend.check_type_markers(packages, result)
        backend.check_version_consistency(packages, result)
        backend.check_naming_convention(packages, result)
        backend.check_build_system(packages, result)
        backend.check_version_field(packages, result)
        backend.check_duplicate_dependencies(packages, result)
        backend.check_self_dependencies(packages, result)
        assert result.ok
        assert len(result.passed) >= 7

    def test_run_fixes_returns_empty(self) -> None:
        """Test run_fixes returns empty list."""
        backend = BaseCheckBackend()
        assert backend.run_fixes([]) == []


# ---------------------------------------------------------------------------
# JavaCheckBackend tests
# ---------------------------------------------------------------------------

_POM_COMPLETE = """\
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <groupId>com.example</groupId>
    <artifactId>core</artifactId>
    <version>1.0.0</version>
    <name>Core</name>
    <description>Core library</description>
    <url>https://github.com/example/core</url>
    <licenses><license><name>Apache-2.0</name></license></licenses>
    <developers><developer><name>Dev</name></developer></developers>
    <scm><url>https://github.com/example/core</url></scm>
    <dependencies>
        <dependency>
            <groupId>com.google.guava</groupId>
            <artifactId>guava</artifactId>
            <version>33.0.0-jre</version>
        </dependency>
    </dependencies>
</project>
"""

_POM_SNAPSHOT_DEP = """\
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <groupId>com.example</groupId>
    <artifactId>plugin</artifactId>
    <version>1.0.0</version>
    <dependencies>
        <dependency>
            <groupId>com.example</groupId>
            <artifactId>core</artifactId>
            <version>1.0.0-SNAPSHOT</version>
        </dependency>
    </dependencies>
</project>
"""

_POM_INCOMPLETE = """\
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <artifactId>incomplete</artifactId>
</project>
"""


class TestJavaCheckBackend:
    """Tests for JavaCheckBackend."""

    def test_version_consistency_pass(self) -> None:
        """Test version consistency passes when all match."""
        backend = JavaCheckBackend(core_package='core')
        result = PreflightResult()
        packages = [_pkg('core', '1.0.0'), _pkg('plugin', '1.0.0')]
        backend.check_version_consistency(packages, result)
        assert result.ok

    def test_version_consistency_fail(self) -> None:
        """Test version consistency fails on mismatch."""
        backend = JavaCheckBackend(core_package='core')
        result = PreflightResult()
        packages = [_pkg('core', '1.0.0'), _pkg('plugin', '2.0.0')]
        backend.check_version_consistency(packages, result)
        assert not result.ok

    def test_version_consistency_skipped_no_core(self) -> None:
        """Test version consistency passes when no core_package."""
        backend = JavaCheckBackend()
        result = PreflightResult()
        backend.check_version_consistency([_pkg('a')], result)
        assert result.ok

    def test_metadata_completeness_pom(self, tmp_path: Path) -> None:
        """Test metadata completeness with complete POM."""
        pom = tmp_path / 'pom.xml'
        pom.write_text(_POM_COMPLETE)
        backend = JavaCheckBackend()
        result = PreflightResult()
        backend.check_metadata_completeness([_pkg('core', manifest_path=pom)], result)
        assert result.ok

    def test_metadata_completeness_incomplete_pom(self, tmp_path: Path) -> None:
        """Test metadata completeness fails with incomplete POM."""
        pom = tmp_path / 'pom.xml'
        pom.write_text(_POM_INCOMPLETE)
        backend = JavaCheckBackend()
        result = PreflightResult()
        backend.check_metadata_completeness([_pkg('incomplete', manifest_path=pom)], result)
        assert not result.ok

    def test_metadata_completeness_gradle(self, tmp_path: Path) -> None:
        """Test metadata completeness with Gradle build file."""
        build = tmp_path / 'build.gradle'
        build.write_text("group = 'com.example'\nversion = '1.0.0'\n")
        backend = JavaCheckBackend()
        result = PreflightResult()
        backend.check_metadata_completeness([_pkg('core', manifest_path=build)], result)
        assert result.ok

    def test_snapshot_dependencies_detected(self, tmp_path: Path) -> None:
        """Test SNAPSHOT dependencies are detected."""
        pom = tmp_path / 'pom.xml'
        pom.write_text(_POM_SNAPSHOT_DEP)
        backend = JavaCheckBackend()
        result = PreflightResult()
        backend.check_dependency_resolution([_pkg('plugin', manifest_path=pom)], result)
        assert not result.ok
        assert 'SNAPSHOT' in result.errors.get('snapshot_dependencies', '')

    def test_snapshot_dependencies_clean(self, tmp_path: Path) -> None:
        """Test no SNAPSHOT dependencies passes."""
        pom = tmp_path / 'pom.xml'
        pom.write_text(_POM_COMPLETE)
        backend = JavaCheckBackend()
        result = PreflightResult()
        backend.check_dependency_resolution([_pkg('core', manifest_path=pom)], result)
        assert result.ok

    def test_build_system_pom(self, tmp_path: Path) -> None:
        """Test build system check with pom.xml."""
        (tmp_path / 'core' / 'pom.xml').parent.mkdir()
        (tmp_path / 'core' / 'pom.xml').touch()
        backend = JavaCheckBackend()
        result = PreflightResult()
        backend.check_build_system([_pkg('core', path=tmp_path / 'core')], result)
        assert result.ok

    def test_build_system_gradle(self, tmp_path: Path) -> None:
        """Test build system check with build.gradle."""
        (tmp_path / 'core').mkdir()
        (tmp_path / 'core' / 'build.gradle').touch()
        backend = JavaCheckBackend()
        result = PreflightResult()
        backend.check_build_system([_pkg('core', path=tmp_path / 'core')], result)
        assert result.ok

    def test_build_system_missing(self, tmp_path: Path) -> None:
        """Test build system check fails when no build file."""
        (tmp_path / 'core').mkdir()
        backend = JavaCheckBackend()
        result = PreflightResult()
        backend.check_build_system([_pkg('core', path=tmp_path / 'core')], result)
        assert not result.ok

    def test_version_semver_pass(self) -> None:
        """Test SemVer check passes for valid versions."""
        backend = JavaCheckBackend()
        result = PreflightResult()
        backend.check_version_pep440([_pkg('core', '1.2.3')], result)
        assert result.ok

    def test_version_semver_fail(self) -> None:
        """Test SemVer check warns for invalid versions."""
        backend = JavaCheckBackend()
        result = PreflightResult()
        backend.check_version_pep440([_pkg('core', 'not-a-version')], result)
        assert len(result.warnings) > 0

    def test_self_dependencies(self) -> None:
        """Test self-dependency detection."""
        backend = JavaCheckBackend()
        result = PreflightResult()
        backend.check_self_dependencies([_pkg('core', internal_deps=['core'])], result)
        assert not result.ok

    def test_duplicate_dependencies(self) -> None:
        """Test duplicate dependency detection."""
        backend = JavaCheckBackend()
        result = PreflightResult()
        backend.check_duplicate_dependencies([_pkg('core', all_deps=['guava', 'guava'])], result)
        assert len(result.warnings) > 0

    def test_mixed_build_systems(self, tmp_path: Path) -> None:
        """Test mixed build systems warning."""
        (tmp_path / 'core').mkdir()
        (tmp_path / 'core' / 'pom.xml').touch()
        (tmp_path / 'core' / 'build.gradle').touch()
        backend = JavaCheckBackend()
        result = PreflightResult()
        backend.check_legacy_setup_files([_pkg('core', path=tmp_path / 'core')], result)
        assert len(result.warnings) > 0

    def test_maven_central_metadata(self, tmp_path: Path) -> None:
        """Test Maven Central metadata check passes with complete POM."""
        pom = tmp_path / 'pom.xml'
        pom.write_text(_POM_COMPLETE)
        backend = JavaCheckBackend()
        result = PreflightResult()
        backend.check_changelog_url([_pkg('core', manifest_path=pom)], result)
        assert result.ok


# ---------------------------------------------------------------------------
# GoCheckBackend tests
# ---------------------------------------------------------------------------


class TestGoCheckBackend:
    """Tests for GoCheckBackend."""

    def test_build_system_pass(self, tmp_path: Path) -> None:
        """Test build system check with go.mod."""
        (tmp_path / 'mod').mkdir()
        (tmp_path / 'mod' / 'go.mod').touch()
        backend = GoCheckBackend()
        result = PreflightResult()
        backend.check_build_system([_pkg('mod', path=tmp_path / 'mod')], result)
        assert result.ok

    def test_build_system_fail(self, tmp_path: Path) -> None:
        """Test build system check fails without go.mod."""
        (tmp_path / 'mod').mkdir()
        backend = GoCheckBackend()
        result = PreflightResult()
        backend.check_build_system([_pkg('mod', path=tmp_path / 'mod')], result)
        assert not result.ok

    def test_go_sum_present(self, tmp_path: Path) -> None:
        """Test go.sum presence check."""
        (tmp_path / 'mod').mkdir()
        (tmp_path / 'mod' / 'go.mod').touch()
        (tmp_path / 'mod' / 'go.sum').touch()
        backend = GoCheckBackend()
        result = PreflightResult()
        backend.check_dependency_resolution([_pkg('mod', path=tmp_path / 'mod')], result)
        assert result.ok

    def test_go_sum_missing(self, tmp_path: Path) -> None:
        """Test go.sum missing warning."""
        (tmp_path / 'mod').mkdir()
        (tmp_path / 'mod' / 'go.mod').touch()
        backend = GoCheckBackend()
        result = PreflightResult()
        backend.check_dependency_resolution([_pkg('mod', path=tmp_path / 'mod')], result)
        assert len(result.warnings) > 0

    def test_naming_convention_pass(self) -> None:
        """Test Go naming convention passes."""
        backend = GoCheckBackend()
        result = PreflightResult()
        backend.check_naming_convention([_pkg('github.com/example/core')], result)
        assert result.ok

    def test_naming_convention_fail(self) -> None:
        """Test Go naming convention warns on uppercase."""
        backend = GoCheckBackend()
        result = PreflightResult()
        backend.check_naming_convention([_pkg('MyPackage')], result)
        assert len(result.warnings) > 0

    def test_version_semver_pass(self) -> None:
        """Test Go SemVer check passes."""
        backend = GoCheckBackend()
        result = PreflightResult()
        backend.check_version_pep440([_pkg('mod', 'v1.2.3')], result)
        assert result.ok

    def test_version_semver_fail(self) -> None:
        """Test Go SemVer check warns."""
        backend = GoCheckBackend()
        result = PreflightResult()
        backend.check_version_pep440([_pkg('mod', 'bad')], result)
        assert len(result.warnings) > 0

    def test_version_consistency(self) -> None:
        """Test version consistency."""
        backend = GoCheckBackend(core_package='core')
        result = PreflightResult()
        packages = [_pkg('core', 'v1.0.0'), _pkg('plugin', 'v2.0.0')]
        backend.check_version_consistency(packages, result)
        assert not result.ok


# ---------------------------------------------------------------------------
# RustCheckBackend tests
# ---------------------------------------------------------------------------


class TestRustCheckBackend:
    """Tests for RustCheckBackend."""

    def test_build_system_pass(self, tmp_path: Path) -> None:
        """Test build system check with Cargo.toml."""
        (tmp_path / 'crate').mkdir()
        (tmp_path / 'crate' / 'Cargo.toml').touch()
        backend = RustCheckBackend()
        result = PreflightResult()
        backend.check_build_system([_pkg('crate', path=tmp_path / 'crate')], result)
        assert result.ok

    def test_build_system_fail(self, tmp_path: Path) -> None:
        """Test build system check fails without Cargo.toml."""
        (tmp_path / 'crate').mkdir()
        backend = RustCheckBackend()
        result = PreflightResult()
        backend.check_build_system([_pkg('crate', path=tmp_path / 'crate')], result)
        assert not result.ok

    def test_naming_convention_pass(self) -> None:
        """Test Rust naming convention passes."""
        backend = RustCheckBackend()
        result = PreflightResult()
        backend.check_naming_convention([_pkg('my-crate')], result)
        assert result.ok

    def test_naming_convention_fail(self) -> None:
        """Test Rust naming convention warns on uppercase."""
        backend = RustCheckBackend()
        result = PreflightResult()
        backend.check_naming_convention([_pkg('MyCrate')], result)
        assert len(result.warnings) > 0

    def test_metadata_completeness(self, tmp_path: Path) -> None:
        """Test metadata completeness for crates.io."""
        (tmp_path / 'crate').mkdir()
        cargo = tmp_path / 'crate' / 'Cargo.toml'
        cargo.write_text(
            '[package]\nname = "my-crate"\nversion = "1.0.0"\n'
            'description = "A crate"\nlicense = "MIT"\n'
            'repository = "https://github.com/example/crate"\n'
        )
        backend = RustCheckBackend()
        result = PreflightResult()
        backend.check_metadata_completeness([_pkg('my-crate', path=tmp_path / 'crate')], result)
        assert result.ok

    def test_metadata_incomplete(self, tmp_path: Path) -> None:
        """Test metadata completeness warns on missing fields."""
        (tmp_path / 'crate').mkdir()
        cargo = tmp_path / 'crate' / 'Cargo.toml'
        cargo.write_text('[package]\nname = "my-crate"\nversion = "1.0.0"\n')
        backend = RustCheckBackend()
        result = PreflightResult()
        backend.check_metadata_completeness([_pkg('my-crate', path=tmp_path / 'crate')], result)
        assert len(result.warnings) > 0

    def test_wildcard_deps(self, tmp_path: Path) -> None:
        """Test wildcard dependency detection."""
        (tmp_path / 'crate').mkdir()
        cargo = tmp_path / 'crate' / 'Cargo.toml'
        cargo.write_text('[package]\nname = "my-crate"\nversion = "1.0.0"\n[dependencies]\nserde = "*"\n')
        backend = RustCheckBackend()
        result = PreflightResult()
        backend.check_pinned_deps_in_libraries([_pkg('my-crate', path=tmp_path / 'crate')], result)
        assert len(result.warnings) > 0

    def test_version_semver_pass(self) -> None:
        """Test SemVer check passes."""
        backend = RustCheckBackend()
        result = PreflightResult()
        backend.check_version_pep440([_pkg('crate', '1.2.3')], result)
        assert result.ok

    def test_cargo_lock_present(self, tmp_path: Path) -> None:
        """Test Cargo.lock presence check."""
        (tmp_path / 'crate').mkdir()
        (tmp_path / 'crate' / 'Cargo.toml').touch()
        (tmp_path / 'Cargo.lock').touch()
        backend = RustCheckBackend()
        result = PreflightResult()
        backend.check_dependency_resolution([_pkg('crate', path=tmp_path / 'crate')], result)
        assert result.ok


# ---------------------------------------------------------------------------
# JsCheckBackend tests
# ---------------------------------------------------------------------------


class TestJsCheckBackend:
    """Tests for JsCheckBackend."""

    def test_build_system_pass(self, tmp_path: Path) -> None:
        """Test build system check with package.json."""
        (tmp_path / 'pkg').mkdir()
        (tmp_path / 'pkg' / 'package.json').write_text('{}')
        backend = JsCheckBackend()
        result = PreflightResult()
        backend.check_build_system([_pkg('pkg', path=tmp_path / 'pkg')], result)
        assert result.ok

    def test_build_system_fail(self, tmp_path: Path) -> None:
        """Test build system check fails without package.json."""
        (tmp_path / 'pkg').mkdir()
        backend = JsCheckBackend()
        result = PreflightResult()
        backend.check_build_system([_pkg('pkg', path=tmp_path / 'pkg')], result)
        assert not result.ok

    def test_naming_convention_scoped(self) -> None:
        """Test npm scoped naming passes."""
        backend = JsCheckBackend()
        result = PreflightResult()
        backend.check_naming_convention([_pkg('@genkit/core')], result)
        assert result.ok

    def test_naming_convention_unscoped(self) -> None:
        """Test npm unscoped naming passes."""
        backend = JsCheckBackend()
        result = PreflightResult()
        backend.check_naming_convention([_pkg('my-package')], result)
        assert result.ok

    def test_metadata_completeness(self, tmp_path: Path) -> None:
        """Test metadata completeness for npm."""
        (tmp_path / 'pkg').mkdir()
        pj = tmp_path / 'pkg' / 'package.json'
        pj.write_text(
            json.dumps({
                'name': '@example/core',
                'version': '1.0.0',
                'description': 'Core',
                'license': 'MIT',
                'repository': 'https://github.com/example/core',
            })
        )
        backend = JsCheckBackend()
        result = PreflightResult()
        backend.check_metadata_completeness([_pkg('@example/core', path=tmp_path / 'pkg')], result)
        assert result.ok

    def test_metadata_incomplete(self, tmp_path: Path) -> None:
        """Test metadata completeness warns on missing fields."""
        (tmp_path / 'pkg').mkdir()
        pj = tmp_path / 'pkg' / 'package.json'
        pj.write_text(json.dumps({'name': 'core', 'version': '1.0.0'}))
        backend = JsCheckBackend()
        result = PreflightResult()
        backend.check_metadata_completeness([_pkg('core', path=tmp_path / 'pkg')], result)
        assert len(result.warnings) > 0

    def test_type_declarations_ts(self, tmp_path: Path) -> None:
        """Test type declarations check for TypeScript projects."""
        (tmp_path / 'pkg').mkdir()
        (tmp_path / 'pkg' / 'package.json').write_text(
            json.dumps({'name': 'core', 'version': '1.0.0', 'types': './dist/index.d.ts'})
        )
        (tmp_path / 'pkg' / 'tsconfig.json').touch()
        backend = JsCheckBackend()
        result = PreflightResult()
        backend.check_type_markers([_pkg('core', path=tmp_path / 'pkg')], result)
        assert result.ok

    def test_type_declarations_missing(self, tmp_path: Path) -> None:
        """Test type declarations warns when missing for TS project."""
        (tmp_path / 'pkg').mkdir()
        (tmp_path / 'pkg' / 'package.json').write_text(json.dumps({'name': 'core', 'version': '1.0.0'}))
        (tmp_path / 'pkg' / 'tsconfig.json').touch()
        backend = JsCheckBackend()
        result = PreflightResult()
        backend.check_type_markers([_pkg('core', path=tmp_path / 'pkg')], result)
        assert len(result.warnings) > 0

    def test_version_semver_pass(self) -> None:
        """Test SemVer check passes."""
        backend = JsCheckBackend()
        result = PreflightResult()
        backend.check_version_pep440([_pkg('pkg', '1.2.3')], result)
        assert result.ok

    def test_private_field_consistency(self, tmp_path: Path) -> None:
        """Test private field consistency check."""
        (tmp_path / 'pkg').mkdir()
        (tmp_path / 'pkg' / 'package.json').write_text(
            json.dumps({'name': 'core', 'version': '1.0.0', 'private': True})
        )
        backend = JsCheckBackend()
        result = PreflightResult()
        backend.check_publish_classifier_consistency([_pkg('core', path=tmp_path / 'pkg', is_publishable=True)], result)
        assert len(result.warnings) > 0


# ---------------------------------------------------------------------------
# DartCheckBackend tests
# ---------------------------------------------------------------------------


class TestDartCheckBackend:
    """Tests for DartCheckBackend."""

    def test_build_system_pass(self, tmp_path: Path) -> None:
        """Test build system check with pubspec.yaml."""
        (tmp_path / 'pkg').mkdir()
        (tmp_path / 'pkg' / 'pubspec.yaml').write_text('name: my_pkg\nversion: 1.0.0\n')
        backend = DartCheckBackend()
        result = PreflightResult()
        backend.check_build_system([_pkg('my_pkg', path=tmp_path / 'pkg')], result)
        assert result.ok

    def test_build_system_fail(self, tmp_path: Path) -> None:
        """Test build system check fails without pubspec.yaml."""
        (tmp_path / 'pkg').mkdir()
        backend = DartCheckBackend()
        result = PreflightResult()
        backend.check_build_system([_pkg('my_pkg', path=tmp_path / 'pkg')], result)
        assert not result.ok

    def test_naming_convention_pass(self) -> None:
        """Test Dart naming convention passes."""
        backend = DartCheckBackend()
        result = PreflightResult()
        backend.check_naming_convention([_pkg('my_package')], result)
        assert result.ok

    def test_naming_convention_fail(self) -> None:
        """Test Dart naming convention warns on hyphens."""
        backend = DartCheckBackend()
        result = PreflightResult()
        backend.check_naming_convention([_pkg('my-package')], result)
        assert len(result.warnings) > 0

    def test_metadata_completeness(self, tmp_path: Path) -> None:
        """Test metadata completeness for pub.dev."""
        (tmp_path / 'pkg').mkdir()
        pubspec = tmp_path / 'pkg' / 'pubspec.yaml'
        pubspec.write_text(
            'name: my_pkg\nversion: 1.0.0\n'
            'description: A package\n'
            'repository: https://github.com/example/pkg\n'
            'environment:\n  sdk: ">=3.0.0 <4.0.0"\n'
        )
        backend = DartCheckBackend()
        result = PreflightResult()
        backend.check_metadata_completeness([_pkg('my_pkg', path=tmp_path / 'pkg')], result)
        assert result.ok

    def test_metadata_incomplete(self, tmp_path: Path) -> None:
        """Test metadata completeness warns on missing fields."""
        (tmp_path / 'pkg').mkdir()
        pubspec = tmp_path / 'pkg' / 'pubspec.yaml'
        pubspec.write_text('name: my_pkg\nversion: 1.0.0\n')
        backend = DartCheckBackend()
        result = PreflightResult()
        backend.check_metadata_completeness([_pkg('my_pkg', path=tmp_path / 'pkg')], result)
        assert len(result.warnings) > 0

    def test_version_semver_pass(self) -> None:
        """Test SemVer check passes."""
        backend = DartCheckBackend()
        result = PreflightResult()
        backend.check_version_pep440([_pkg('pkg', '1.2.3')], result)
        assert result.ok

    def test_publish_to_consistency(self, tmp_path: Path) -> None:
        """Test publish_to consistency check."""
        (tmp_path / 'pkg').mkdir()
        pubspec = tmp_path / 'pkg' / 'pubspec.yaml'
        pubspec.write_text('name: my_pkg\nversion: 1.0.0\npublish_to: none\n')
        backend = DartCheckBackend()
        result = PreflightResult()
        backend.check_publish_classifier_consistency(
            [_pkg('my_pkg', path=tmp_path / 'pkg', is_publishable=True)], result
        )
        assert len(result.warnings) > 0

    def test_version_consistency(self) -> None:
        """Test version consistency."""
        backend = DartCheckBackend(core_package='core')
        result = PreflightResult()
        packages = [_pkg('core', '1.0.0'), _pkg('plugin', '2.0.0')]
        backend.check_version_consistency(packages, result)
        assert not result.ok
