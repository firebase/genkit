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

"""Tests for ecosystem-specific auto-fixer functions."""

from __future__ import annotations

import json
from pathlib import Path

from releasekit.checks._dart import DartCheckBackend
from releasekit.checks._dart_fixers import (
    fix_duplicate_dependencies as dart_fix_duplicate_dependencies,
    fix_metadata_completeness as dart_fix_metadata_completeness,
    fix_publish_to_consistency as dart_fix_publish_to_consistency,
)
from releasekit.checks._go import GoCheckBackend
from releasekit.checks._go_fixers import (
    fix_build_system as go_fix_build_system,
    fix_duplicate_dependencies as go_fix_duplicate_dependencies,
)
from releasekit.checks._java import JavaCheckBackend
from releasekit.checks._java_fixers import (
    fix_duplicate_dependencies as java_fix_duplicate_dependencies,
    fix_metadata_completeness as java_fix_metadata_completeness,
    fix_placeholder_urls as java_fix_placeholder_urls,
)
from releasekit.checks._js import JsCheckBackend
from releasekit.checks._js_fixers import (
    fix_duplicate_dependencies as js_fix_duplicate_dependencies,
    fix_metadata_completeness as js_fix_metadata_completeness,
    fix_private_field_consistency as js_fix_private_field_consistency,
)
from releasekit.checks._rust import RustCheckBackend
from releasekit.checks._rust_fixers import (
    fix_duplicate_dependencies as rust_fix_duplicate_dependencies,
    fix_metadata_completeness as rust_fix_metadata_completeness,
    fix_wildcard_dependencies as rust_fix_wildcard_dependencies,
)
from releasekit.logging import configure_logging
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
        manifest_path=manifest_path or p / 'pyproject.toml',
        internal_deps=internal_deps or [],
        external_deps=external_deps or [],
        all_deps=all_deps or [],
        is_publishable=is_publishable,
    )


# ===========================================================================
# Go fixers
# ===========================================================================


class TestGoFixBuildSystem:
    """Tests for go_fix_build_system."""

    def test_creates_go_mod(self, tmp_path: Path) -> None:
        """Test creates go.mod when missing."""
        pkg = _pkg('example.com/foo', path=tmp_path / 'foo')
        pkg.path.mkdir(parents=True)
        changes = go_fix_build_system([pkg])
        assert len(changes) == 1
        assert 'created go.mod' in changes[0]
        go_mod = pkg.path / 'go.mod'
        assert go_mod.is_file()
        text = go_mod.read_text()
        assert 'module example.com/foo' in text
        assert 'go 1.21' in text

    def test_skips_existing_go_mod(self, tmp_path: Path) -> None:
        """Test skips when go.mod already exists."""
        pkg = _pkg('example.com/foo', path=tmp_path / 'foo')
        pkg.path.mkdir(parents=True)
        (pkg.path / 'go.mod').write_text('module example.com/foo\n')
        changes = go_fix_build_system([pkg])
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry run reports but does not create file."""
        pkg = _pkg('example.com/foo', path=tmp_path / 'foo')
        pkg.path.mkdir(parents=True)
        changes = go_fix_build_system([pkg], dry_run=True)
        assert len(changes) == 1
        assert not (pkg.path / 'go.mod').is_file()


class TestGoFixDuplicateDependencies:
    """Tests for go_fix_duplicate_dependencies."""

    def test_removes_duplicates(self, tmp_path: Path) -> None:
        """Test removes duplicate require directives."""
        pkg = _pkg('example.com/foo', path=tmp_path / 'foo')
        pkg.path.mkdir(parents=True)
        go_mod = pkg.path / 'go.mod'
        go_mod.write_text(
            'module example.com/foo\n\ngo 1.21\n\nrequire (\n'
            '\tgolang.org/x/text v0.3.0\n'
            '\tgolang.org/x/text v0.4.0\n'
            ')\n'
        )
        changes = go_fix_duplicate_dependencies([pkg])
        assert len(changes) == 1
        assert 'golang.org/x/text' in changes[0]
        text = go_mod.read_text()
        assert text.count('golang.org/x/text') == 1

    def test_no_duplicates(self, tmp_path: Path) -> None:
        """Test no changes when no duplicates."""
        pkg = _pkg('example.com/foo', path=tmp_path / 'foo')
        pkg.path.mkdir(parents=True)
        go_mod = pkg.path / 'go.mod'
        go_mod.write_text('module example.com/foo\n\ngo 1.21\n\nrequire (\n\tgolang.org/x/text v0.3.0\n)\n')
        changes = go_fix_duplicate_dependencies([pkg])
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry run reports but does not modify file."""
        pkg = _pkg('example.com/foo', path=tmp_path / 'foo')
        pkg.path.mkdir(parents=True)
        go_mod = pkg.path / 'go.mod'
        original = (
            'module example.com/foo\n\ngo 1.21\n\nrequire (\n'
            '\tgolang.org/x/text v0.3.0\n'
            '\tgolang.org/x/text v0.4.0\n'
            ')\n'
        )
        go_mod.write_text(original)
        changes = go_fix_duplicate_dependencies([pkg], dry_run=True)
        assert len(changes) == 1
        assert go_mod.read_text() == original


# ===========================================================================
# Dart fixers
# ===========================================================================


class TestDartFixPublishToConsistency:
    """Tests for dart_fix_publish_to_consistency."""

    def test_adds_publish_to_none(self, tmp_path: Path) -> None:
        """Test adds publish_to: none to non-publishable package."""
        pkg = _pkg('my_pkg', path=tmp_path / 'my_pkg', is_publishable=False)
        pkg.path.mkdir(parents=True)
        pubspec = pkg.path / 'pubspec.yaml'
        pubspec.write_text('name: my_pkg\nversion: 1.0.0\n')
        changes = dart_fix_publish_to_consistency([pkg])
        assert len(changes) == 1
        assert 'publish_to: none' in pubspec.read_text()

    def test_skips_publishable(self, tmp_path: Path) -> None:
        """Test skips publishable packages."""
        pkg = _pkg('my_pkg', path=tmp_path / 'my_pkg', is_publishable=True)
        pkg.path.mkdir(parents=True)
        pubspec = pkg.path / 'pubspec.yaml'
        pubspec.write_text('name: my_pkg\nversion: 1.0.0\n')
        changes = dart_fix_publish_to_consistency([pkg])
        assert changes == []

    def test_skips_already_has_publish_to(self, tmp_path: Path) -> None:
        """Test skips when publish_to: none already present."""
        pkg = _pkg('my_pkg', path=tmp_path / 'my_pkg', is_publishable=False)
        pkg.path.mkdir(parents=True)
        pubspec = pkg.path / 'pubspec.yaml'
        pubspec.write_text('name: my_pkg\npublish_to: none\nversion: 1.0.0\n')
        changes = dart_fix_publish_to_consistency([pkg])
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry run reports but does not modify file."""
        pkg = _pkg('my_pkg', path=tmp_path / 'my_pkg', is_publishable=False)
        pkg.path.mkdir(parents=True)
        pubspec = pkg.path / 'pubspec.yaml'
        original = 'name: my_pkg\nversion: 1.0.0\n'
        pubspec.write_text(original)
        changes = dart_fix_publish_to_consistency([pkg], dry_run=True)
        assert len(changes) == 1
        assert pubspec.read_text() == original


class TestDartFixMetadataCompleteness:
    """Tests for dart_fix_metadata_completeness."""

    def test_adds_missing_fields(self, tmp_path: Path) -> None:
        """Test adds missing description, repository, environment."""
        pkg = _pkg('my_pkg', path=tmp_path / 'my_pkg')
        pkg.path.mkdir(parents=True)
        pubspec = pkg.path / 'pubspec.yaml'
        pubspec.write_text('name: my_pkg\nversion: 1.0.0\n')
        changes = dart_fix_metadata_completeness([pkg])
        assert len(changes) == 1
        text = pubspec.read_text()
        assert 'description:' in text
        assert 'repository:' in text
        assert 'environment:' in text

    def test_skips_complete(self, tmp_path: Path) -> None:
        """Test skips when all fields present."""
        pkg = _pkg('my_pkg', path=tmp_path / 'my_pkg')
        pkg.path.mkdir(parents=True)
        pubspec = pkg.path / 'pubspec.yaml'
        pubspec.write_text(
            'name: my_pkg\nversion: 1.0.0\n'
            'description: A package\n'
            'repository: https://github.com/foo/bar\n'
            "environment:\n  sdk: '>=3.0.0 <4.0.0'\n"
        )
        changes = dart_fix_metadata_completeness([pkg])
        assert changes == []

    def test_skips_non_publishable(self, tmp_path: Path) -> None:
        """Test skips non-publishable packages."""
        pkg = _pkg('my_pkg', path=tmp_path / 'my_pkg', is_publishable=False)
        pkg.path.mkdir(parents=True)
        pubspec = pkg.path / 'pubspec.yaml'
        pubspec.write_text('name: my_pkg\nversion: 1.0.0\n')
        changes = dart_fix_metadata_completeness([pkg])
        assert changes == []


class TestDartFixDuplicateDependencies:
    """Tests for dart_fix_duplicate_dependencies."""

    def test_removes_duplicates(self, tmp_path: Path) -> None:
        """Test removes duplicate dependency entries."""
        pkg = _pkg('my_pkg', path=tmp_path / 'my_pkg', all_deps=['foo', 'foo', 'bar'])
        pkg.path.mkdir(parents=True)
        pubspec = pkg.path / 'pubspec.yaml'
        pubspec.write_text('name: my_pkg\nversion: 1.0.0\ndependencies:\n  foo: ^1.0.0\n  foo: ^2.0.0\n  bar: ^1.0.0\n')
        changes = dart_fix_duplicate_dependencies([pkg])
        assert len(changes) == 1
        text = pubspec.read_text()
        assert text.count('foo:') == 1

    def test_no_duplicates(self, tmp_path: Path) -> None:
        """Test no changes when no duplicates."""
        pkg = _pkg('my_pkg', path=tmp_path / 'my_pkg', all_deps=['foo', 'bar'])
        pkg.path.mkdir(parents=True)
        pubspec = pkg.path / 'pubspec.yaml'
        pubspec.write_text('name: my_pkg\nversion: 1.0.0\ndependencies:\n  foo: ^1.0.0\n  bar: ^1.0.0\n')
        changes = dart_fix_duplicate_dependencies([pkg])
        assert changes == []


# ===========================================================================
# JS fixers
# ===========================================================================


class TestJsFixPrivateFieldConsistency:
    """Tests for js_fix_private_field_consistency."""

    def test_adds_private_true(self, tmp_path: Path) -> None:
        """Test adds private:true to non-publishable package."""
        pkg = _pkg('my-pkg', path=tmp_path / 'my-pkg', is_publishable=False)
        pkg.path.mkdir(parents=True)
        pj = pkg.path / 'package.json'
        pj.write_text(json.dumps({'name': 'my-pkg', 'version': '1.0.0'}))
        changes = js_fix_private_field_consistency([pkg])
        assert len(changes) == 1
        data = json.loads(pj.read_text())
        assert data['private'] is True

    def test_skips_publishable(self, tmp_path: Path) -> None:
        """Test skips publishable packages."""
        pkg = _pkg('my-pkg', path=tmp_path / 'my-pkg', is_publishable=True)
        pkg.path.mkdir(parents=True)
        pj = pkg.path / 'package.json'
        pj.write_text(json.dumps({'name': 'my-pkg', 'version': '1.0.0'}))
        changes = js_fix_private_field_consistency([pkg])
        assert changes == []

    def test_skips_already_private(self, tmp_path: Path) -> None:
        """Test skips when private:true already set."""
        pkg = _pkg('my-pkg', path=tmp_path / 'my-pkg', is_publishable=False)
        pkg.path.mkdir(parents=True)
        pj = pkg.path / 'package.json'
        pj.write_text(json.dumps({'name': 'my-pkg', 'version': '1.0.0', 'private': True}))
        changes = js_fix_private_field_consistency([pkg])
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry run reports but does not modify file."""
        pkg = _pkg('my-pkg', path=tmp_path / 'my-pkg', is_publishable=False)
        pkg.path.mkdir(parents=True)
        pj = pkg.path / 'package.json'
        original = json.dumps({'name': 'my-pkg', 'version': '1.0.0'})
        pj.write_text(original)
        changes = js_fix_private_field_consistency([pkg], dry_run=True)
        assert len(changes) == 1
        assert 'private' not in json.loads(pj.read_text())


class TestJsFixMetadataCompleteness:
    """Tests for js_fix_metadata_completeness."""

    def test_adds_missing_fields(self, tmp_path: Path) -> None:
        """Test adds missing description, license, repository."""
        pkg = _pkg('my-pkg', path=tmp_path / 'my-pkg')
        pkg.path.mkdir(parents=True)
        pj = pkg.path / 'package.json'
        pj.write_text(json.dumps({'name': 'my-pkg', 'version': '1.0.0'}))
        changes = js_fix_metadata_completeness([pkg])
        assert len(changes) == 1
        data = json.loads(pj.read_text())
        assert 'description' in data
        assert 'license' in data
        assert 'repository' in data

    def test_skips_complete(self, tmp_path: Path) -> None:
        """Test skips when all fields present."""
        pkg = _pkg('my-pkg', path=tmp_path / 'my-pkg')
        pkg.path.mkdir(parents=True)
        pj = pkg.path / 'package.json'
        pj.write_text(
            json.dumps({
                'name': 'my-pkg',
                'version': '1.0.0',
                'description': 'A package',
                'license': 'MIT',
                'repository': 'https://github.com/foo/bar',
            })
        )
        changes = js_fix_metadata_completeness([pkg])
        assert changes == []

    def test_skips_non_publishable(self, tmp_path: Path) -> None:
        """Test skips non-publishable packages."""
        pkg = _pkg('my-pkg', path=tmp_path / 'my-pkg', is_publishable=False)
        pkg.path.mkdir(parents=True)
        pj = pkg.path / 'package.json'
        pj.write_text(json.dumps({'name': 'my-pkg', 'version': '1.0.0'}))
        changes = js_fix_metadata_completeness([pkg])
        assert changes == []


class TestJsFixDuplicateDependencies:
    """Tests for js_fix_duplicate_dependencies."""

    def test_removes_overlap(self, tmp_path: Path) -> None:
        """Test removes deps from devDependencies when in dependencies."""
        pkg = _pkg('my-pkg', path=tmp_path / 'my-pkg')
        pkg.path.mkdir(parents=True)
        pj = pkg.path / 'package.json'
        pj.write_text(
            json.dumps({
                'name': 'my-pkg',
                'version': '1.0.0',
                'dependencies': {'lodash': '^4.0.0'},
                'devDependencies': {'lodash': '^4.0.0', 'jest': '^29.0.0'},
            })
        )
        changes = js_fix_duplicate_dependencies([pkg])
        assert len(changes) == 1
        data = json.loads(pj.read_text())
        assert 'lodash' not in data['devDependencies']
        assert 'jest' in data['devDependencies']

    def test_no_overlap(self, tmp_path: Path) -> None:
        """Test no changes when no overlap."""
        pkg = _pkg('my-pkg', path=tmp_path / 'my-pkg')
        pkg.path.mkdir(parents=True)
        pj = pkg.path / 'package.json'
        pj.write_text(
            json.dumps({
                'name': 'my-pkg',
                'version': '1.0.0',
                'dependencies': {'lodash': '^4.0.0'},
                'devDependencies': {'jest': '^29.0.0'},
            })
        )
        changes = js_fix_duplicate_dependencies([pkg])
        assert changes == []


# ===========================================================================
# Rust fixers
# ===========================================================================


class TestRustFixMetadataCompleteness:
    """Tests for rust_fix_metadata_completeness."""

    def test_adds_missing_fields(self, tmp_path: Path) -> None:
        """Test adds missing description, license, repository."""
        pkg = _pkg('my-crate', path=tmp_path / 'my-crate')
        pkg.path.mkdir(parents=True)
        cargo = pkg.path / 'Cargo.toml'
        cargo.write_text('[package]\nname = "my-crate"\nversion = "1.0.0"\n')
        changes = rust_fix_metadata_completeness([pkg])
        assert len(changes) == 1
        text = cargo.read_text()
        assert 'description =' in text
        assert 'license =' in text
        assert 'repository =' in text

    def test_skips_complete(self, tmp_path: Path) -> None:
        """Test skips when all fields present."""
        pkg = _pkg('my-crate', path=tmp_path / 'my-crate')
        pkg.path.mkdir(parents=True)
        cargo = pkg.path / 'Cargo.toml'
        cargo.write_text(
            '[package]\nname = "my-crate"\nversion = "1.0.0"\n'
            'description = "A crate"\nlicense = "Apache-2.0"\n'
            'repository = "https://github.com/foo/bar"\n'
        )
        changes = rust_fix_metadata_completeness([pkg])
        assert changes == []

    def test_skips_non_publishable(self, tmp_path: Path) -> None:
        """Test skips non-publishable crates."""
        pkg = _pkg('my-crate', path=tmp_path / 'my-crate', is_publishable=False)
        pkg.path.mkdir(parents=True)
        cargo = pkg.path / 'Cargo.toml'
        cargo.write_text('[package]\nname = "my-crate"\nversion = "1.0.0"\n')
        changes = rust_fix_metadata_completeness([pkg])
        assert changes == []


class TestRustFixWildcardDependencies:
    """Tests for rust_fix_wildcard_dependencies."""

    def test_replaces_wildcards(self, tmp_path: Path) -> None:
        """Test replaces wildcard versions with >=0."""
        pkg = _pkg('my-crate', path=tmp_path / 'my-crate')
        pkg.path.mkdir(parents=True)
        cargo = pkg.path / 'Cargo.toml'
        cargo.write_text(
            '[package]\nname = "my-crate"\nversion = "1.0.0"\n\n[dependencies]\nserde = "*"\nrand = "0.8"\n'
        )
        changes = rust_fix_wildcard_dependencies([pkg])
        assert len(changes) == 1
        text = cargo.read_text()
        assert '"*"' not in text
        assert '">=0"' in text

    def test_no_wildcards(self, tmp_path: Path) -> None:
        """Test no changes when no wildcards."""
        pkg = _pkg('my-crate', path=tmp_path / 'my-crate')
        pkg.path.mkdir(parents=True)
        cargo = pkg.path / 'Cargo.toml'
        cargo.write_text('[package]\nname = "my-crate"\nversion = "1.0.0"\n\n[dependencies]\nserde = "1.0"\n')
        changes = rust_fix_wildcard_dependencies([pkg])
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry run reports but does not modify file."""
        pkg = _pkg('my-crate', path=tmp_path / 'my-crate')
        pkg.path.mkdir(parents=True)
        cargo = pkg.path / 'Cargo.toml'
        original = '[package]\nname = "my-crate"\nversion = "1.0.0"\n\n[dependencies]\nserde = "*"\n'
        cargo.write_text(original)
        changes = rust_fix_wildcard_dependencies([pkg], dry_run=True)
        assert len(changes) == 1
        assert cargo.read_text() == original


class TestRustFixDuplicateDependencies:
    """Tests for rust_fix_duplicate_dependencies."""

    def test_removes_duplicates(self, tmp_path: Path) -> None:
        """Test removes duplicate dependency entries."""
        pkg = _pkg('my-crate', path=tmp_path / 'my-crate')
        pkg.path.mkdir(parents=True)
        cargo = pkg.path / 'Cargo.toml'
        cargo.write_text(
            '[package]\nname = "my-crate"\nversion = "1.0.0"\n\n'
            '[dependencies]\nserde = "1.0"\nserde = "1.1"\nrand = "0.8"\n'
        )
        changes = rust_fix_duplicate_dependencies([pkg])
        assert len(changes) == 1
        text = cargo.read_text()
        assert text.count('serde =') == 1

    def test_no_duplicates(self, tmp_path: Path) -> None:
        """Test no changes when no duplicates."""
        pkg = _pkg('my-crate', path=tmp_path / 'my-crate')
        pkg.path.mkdir(parents=True)
        cargo = pkg.path / 'Cargo.toml'
        cargo.write_text(
            '[package]\nname = "my-crate"\nversion = "1.0.0"\n\n[dependencies]\nserde = "1.0"\nrand = "0.8"\n'
        )
        changes = rust_fix_duplicate_dependencies([pkg])
        assert changes == []


# ===========================================================================
# Java fixers
# ===========================================================================


class TestJavaFixPlaceholderUrls:
    """Tests for java_fix_placeholder_urls."""

    def test_clears_placeholder_url(self, tmp_path: Path) -> None:
        """Test clears example.com placeholder URL."""
        pkg = _pkg('my-module', path=tmp_path / 'my-module', manifest_path=tmp_path / 'my-module' / 'pom.xml')
        pkg.path.mkdir(parents=True)
        pom = pkg.manifest_path
        pom.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<project>\n'
            '  <url>http://example.com/placeholder</url>\n'
            '</project>\n'
        )
        changes = java_fix_placeholder_urls([pkg])
        assert len(changes) == 1
        assert 'cleared placeholder' in changes[0]

    def test_skips_real_url(self, tmp_path: Path) -> None:
        """Test skips real URLs."""
        pkg = _pkg('my-module', path=tmp_path / 'my-module', manifest_path=tmp_path / 'my-module' / 'pom.xml')
        pkg.path.mkdir(parents=True)
        pom = pkg.manifest_path
        pom.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<project>\n'
            '  <url>https://github.com/real/project</url>\n'
            '</project>\n'
        )
        changes = java_fix_placeholder_urls([pkg])
        assert changes == []

    def test_skips_non_xml(self, tmp_path: Path) -> None:
        """Test skips non-XML manifest files."""
        pkg = _pkg('my-module', path=tmp_path / 'my-module', manifest_path=tmp_path / 'my-module' / 'build.gradle')
        pkg.path.mkdir(parents=True)
        pkg.manifest_path.write_text('group = "com.example"\nversion = "1.0.0"\n')
        changes = java_fix_placeholder_urls([pkg])
        assert changes == []

    def test_dry_run(self, tmp_path: Path) -> None:
        """Test dry run reports but does not modify file."""
        pkg = _pkg('my-module', path=tmp_path / 'my-module', manifest_path=tmp_path / 'my-module' / 'pom.xml')
        pkg.path.mkdir(parents=True)
        pom = pkg.manifest_path
        original = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<project>\n'
            '  <url>http://example.com/placeholder</url>\n'
            '</project>\n'
        )
        pom.write_text(original)
        changes = java_fix_placeholder_urls([pkg], dry_run=True)
        assert len(changes) == 1
        # File should not be modified in dry run.
        assert 'example.com' in pom.read_text()


class TestJavaFixMetadataCompleteness:
    """Tests for java_fix_metadata_completeness."""

    def test_adds_missing_gradle_fields(self, tmp_path: Path) -> None:
        """Test adds missing group and version to build.gradle."""
        pkg = _pkg(
            'my-module',
            path=tmp_path / 'my-module',
            manifest_path=tmp_path / 'my-module' / 'build.gradle',
        )
        pkg.path.mkdir(parents=True)
        gradle = pkg.manifest_path
        gradle.write_text('apply plugin: "java"\n')
        changes = java_fix_metadata_completeness([pkg])
        assert len(changes) == 1
        text = gradle.read_text()
        assert 'group =' in text
        assert 'version =' in text

    def test_skips_complete_gradle(self, tmp_path: Path) -> None:
        """Test skips when group and version already present."""
        pkg = _pkg(
            'my-module',
            path=tmp_path / 'my-module',
            manifest_path=tmp_path / 'my-module' / 'build.gradle',
        )
        pkg.path.mkdir(parents=True)
        gradle = pkg.manifest_path
        gradle.write_text("group = 'com.example'\nversion = '1.0.0'\n")
        changes = java_fix_metadata_completeness([pkg])
        assert changes == []

    def test_skips_pom(self, tmp_path: Path) -> None:
        """Test skips POM files (only fixes Gradle)."""
        pkg = _pkg(
            'my-module',
            path=tmp_path / 'my-module',
            manifest_path=tmp_path / 'my-module' / 'pom.xml',
        )
        pkg.path.mkdir(parents=True)
        pkg.manifest_path.write_text('<project></project>')
        changes = java_fix_metadata_completeness([pkg])
        assert changes == []


class TestJavaFixDuplicateDependencies:
    """Tests for java_fix_duplicate_dependencies."""

    def test_removes_duplicate_pom_deps(self, tmp_path: Path) -> None:
        """Test removes duplicate dependency elements from POM."""
        pkg = _pkg('my-module', path=tmp_path / 'my-module', manifest_path=tmp_path / 'my-module' / 'pom.xml')
        pkg.path.mkdir(parents=True)
        pom = pkg.manifest_path
        pom.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<project>\n'
            '  <dependencies>\n'
            '    <dependency>\n'
            '      <groupId>com.google</groupId>\n'
            '      <artifactId>guava</artifactId>\n'
            '    </dependency>\n'
            '    <dependency>\n'
            '      <groupId>com.google</groupId>\n'
            '      <artifactId>guava</artifactId>\n'
            '    </dependency>\n'
            '  </dependencies>\n'
            '</project>\n'
        )
        changes = java_fix_duplicate_dependencies([pkg])
        assert len(changes) == 1
        assert 'com.google:guava' in changes[0]

    def test_no_duplicates(self, tmp_path: Path) -> None:
        """Test no changes when no duplicate deps."""
        pkg = _pkg('my-module', path=tmp_path / 'my-module', manifest_path=tmp_path / 'my-module' / 'pom.xml')
        pkg.path.mkdir(parents=True)
        pom = pkg.manifest_path
        pom.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<project>\n'
            '  <dependencies>\n'
            '    <dependency>\n'
            '      <groupId>com.google</groupId>\n'
            '      <artifactId>guava</artifactId>\n'
            '    </dependency>\n'
            '  </dependencies>\n'
            '</project>\n'
        )
        changes = java_fix_duplicate_dependencies([pkg])
        assert changes == []


# ===========================================================================
# run_fixes integration
# ===========================================================================


class TestRunFixesIntegration:
    """Test that run_fixes dispatches to the correct fixers."""

    def test_go_run_fixes(self, tmp_path: Path) -> None:
        """Test Go backend run_fixes creates go.mod."""
        pkg = _pkg('example.com/foo', path=tmp_path / 'foo')
        pkg.path.mkdir(parents=True)
        backend = GoCheckBackend()
        changes = backend.run_fixes([pkg])
        assert any('created go.mod' in c for c in changes)

    def test_dart_run_fixes(self, tmp_path: Path) -> None:
        """Test Dart backend run_fixes adds metadata."""
        pkg = _pkg('my_pkg', path=tmp_path / 'my_pkg')
        pkg.path.mkdir(parents=True)
        (pkg.path / 'pubspec.yaml').write_text('name: my_pkg\nversion: 1.0.0\n')
        backend = DartCheckBackend()
        changes = backend.run_fixes([pkg])
        assert any('added' in c for c in changes)

    def test_js_run_fixes(self, tmp_path: Path) -> None:
        """Test JS backend run_fixes adds private field."""
        pkg = _pkg('my-pkg', path=tmp_path / 'my-pkg', is_publishable=False)
        pkg.path.mkdir(parents=True)
        (pkg.path / 'package.json').write_text(json.dumps({'name': 'my-pkg', 'version': '1.0.0'}))
        backend = JsCheckBackend()
        changes = backend.run_fixes([pkg])
        assert any('private' in c for c in changes)

    def test_rust_run_fixes(self, tmp_path: Path) -> None:
        """Test Rust backend run_fixes adds metadata."""
        pkg = _pkg('my-crate', path=tmp_path / 'my-crate')
        pkg.path.mkdir(parents=True)
        (pkg.path / 'Cargo.toml').write_text('[package]\nname = "my-crate"\nversion = "1.0.0"\n')
        backend = RustCheckBackend()
        changes = backend.run_fixes([pkg])
        assert any('added' in c for c in changes)

    def test_java_run_fixes(self, tmp_path: Path) -> None:
        """Test Java backend run_fixes adds Gradle metadata."""
        pkg = _pkg(
            'my-module',
            path=tmp_path / 'my-module',
            manifest_path=tmp_path / 'my-module' / 'build.gradle',
        )
        pkg.path.mkdir(parents=True)
        pkg.manifest_path.write_text('apply plugin: "java"\n')
        backend = JavaCheckBackend()
        changes = backend.run_fixes([pkg])
        assert any('added' in c for c in changes)
