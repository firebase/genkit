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

"""Tests for releasekit.backends.workspace.maven module."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends.workspace.maven import (
    MavenWorkspace,
    _parse_gradle_dependencies,
    _parse_pom_dependencies,
    _parse_pom_metadata,
    _parse_pom_modules,
    _parse_settings_gradle,
)
from releasekit.logging import configure_logging

configure_logging(quiet=True)

_POM_PARENT = """\
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <groupId>com.example</groupId>
  <artifactId>parent</artifactId>
  <version>1.0.0</version>
  <modules>
    <module>core</module>
    <module>plugins/google</module>
  </modules>
</project>
"""

_POM_CORE = """\
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <groupId>com.example</groupId>
  <artifactId>core</artifactId>
  <version>1.0.0</version>
</project>
"""

_POM_PLUGIN = """\
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <groupId>com.example</groupId>
  <artifactId>plugin-google</artifactId>
  <version>1.0.0</version>
  <dependencies>
    <dependency>
      <groupId>com.example</groupId>
      <artifactId>core</artifactId>
      <version>1.0.0</version>
    </dependency>
    <dependency>
      <groupId>com.google.guava</groupId>
      <artifactId>guava</artifactId>
      <version>33.0.0-jre</version>
    </dependency>
  </dependencies>
</project>
"""

_POM_NO_NS = """\
<project>
  <groupId>com.example</groupId>
  <artifactId>no-ns</artifactId>
  <version>2.0.0</version>
  <modules>
    <module>sub</module>
  </modules>
  <dependencies>
    <dependency>
      <artifactId>dep-a</artifactId>
    </dependency>
  </dependencies>
</project>
"""

_SETTINGS_GRADLE = """\
rootProject.name = 'my-project'
include ':core'
include ':plugins:google'
include ':plugins:vertex'
"""


def _setup_maven_workspace(root: Path) -> None:
    """Create a Maven multi-module workspace."""
    (root / 'pom.xml').write_text(_POM_PARENT)
    core_dir = root / 'core'
    core_dir.mkdir()
    (core_dir / 'pom.xml').write_text(_POM_CORE)
    plugin_dir = root / 'plugins' / 'google'
    plugin_dir.mkdir(parents=True)
    (plugin_dir / 'pom.xml').write_text(_POM_PLUGIN)


def _setup_gradle_workspace(root: Path) -> None:
    """Create a Gradle multi-project workspace with dependencies."""
    (root / 'settings.gradle').write_text(_SETTINGS_GRADLE)

    # core: no internal deps, one external dep.
    core_dir = root / 'core'
    core_dir.mkdir(parents=True, exist_ok=True)
    (core_dir / 'build.gradle').write_text(
        "group = 'com.example'\n"
        "version = '1.0.0'\n"
        'dependencies {\n'
        "    implementation 'com.google.guava:guava:33.0.0-jre'\n"
        '}\n'
    )

    # plugins/google: depends on core (internal) and gson (external).
    google_dir = root / 'plugins' / 'google'
    google_dir.mkdir(parents=True, exist_ok=True)
    (google_dir / 'build.gradle').write_text(
        "group = 'com.example'\n"
        "version = '1.1.0'\n"
        'dependencies {\n'
        "    implementation 'com.example:core:1.0.0'\n"
        "    implementation 'com.google.code.gson:gson:2.10.1'\n"
        '}\n'
    )

    # plugins/vertex: depends on core (internal).
    vertex_dir = root / 'plugins' / 'vertex'
    vertex_dir.mkdir(parents=True, exist_ok=True)
    (vertex_dir / 'build.gradle').write_text(
        "group = 'com.example'\nversion = '1.2.0'\ndependencies {\n    implementation 'com.example:core:1.0.0'\n}\n"
    )


class TestParsePomModules:
    """Tests for _parse_pom_modules()."""

    def test_parses_modules_with_namespace(self, tmp_path: Path) -> None:
        """Test parses modules with namespace."""
        pom = tmp_path / 'pom.xml'
        pom.write_text(_POM_PARENT)
        modules = _parse_pom_modules(pom)
        assert modules == ['core', 'plugins/google']

    def test_parses_modules_without_namespace(self, tmp_path: Path) -> None:
        """Test parses modules without namespace."""
        pom = tmp_path / 'pom.xml'
        pom.write_text(_POM_NO_NS)
        modules = _parse_pom_modules(pom)
        assert 'sub' in modules

    def test_returns_empty_for_no_modules(self, tmp_path: Path) -> None:
        """Test returns empty for no modules."""
        pom = tmp_path / 'pom.xml'
        pom.write_text(_POM_CORE)
        modules = _parse_pom_modules(pom)
        assert modules == []

    def test_returns_empty_for_invalid_xml(self, tmp_path: Path) -> None:
        """Test returns empty for invalid xml."""
        pom = tmp_path / 'pom.xml'
        pom.write_text('not xml at all')
        modules = _parse_pom_modules(pom)
        assert modules == []


class TestParsePomMetadata:
    """Tests for _parse_pom_metadata()."""

    def test_parses_group_artifact_version(self, tmp_path: Path) -> None:
        """Test parses group artifact version."""
        pom = tmp_path / 'pom.xml'
        pom.write_text(_POM_CORE)
        meta = _parse_pom_metadata(pom)
        assert meta['groupId'] == 'com.example'
        assert meta['artifactId'] == 'core'
        assert meta['version'] == '1.0.0'

    def test_parses_without_namespace(self, tmp_path: Path) -> None:
        """Test parses without namespace."""
        pom = tmp_path / 'pom.xml'
        pom.write_text(_POM_NO_NS)
        meta = _parse_pom_metadata(pom)
        assert meta['artifactId'] == 'no-ns'
        assert meta['version'] == '2.0.0'

    def test_returns_empty_for_invalid_xml(self, tmp_path: Path) -> None:
        """Test returns empty for invalid xml."""
        pom = tmp_path / 'pom.xml'
        pom.write_text('not xml')
        meta = _parse_pom_metadata(pom)
        assert meta == {}


class TestParsePomDependencies:
    """Tests for _parse_pom_dependencies()."""

    def test_parses_dependencies(self, tmp_path: Path) -> None:
        """Test parses dependencies."""
        pom = tmp_path / 'pom.xml'
        pom.write_text(_POM_PLUGIN)
        deps = _parse_pom_dependencies(pom)
        assert 'core' in deps
        assert 'guava' in deps

    def test_parses_without_namespace(self, tmp_path: Path) -> None:
        """Test parses without namespace."""
        pom = tmp_path / 'pom.xml'
        pom.write_text(_POM_NO_NS)
        deps = _parse_pom_dependencies(pom)
        assert 'dep-a' in deps

    def test_returns_empty_for_no_deps(self, tmp_path: Path) -> None:
        """Test returns empty for no deps."""
        pom = tmp_path / 'pom.xml'
        pom.write_text(_POM_CORE)
        deps = _parse_pom_dependencies(pom)
        assert deps == []

    def test_returns_empty_for_invalid_xml(self, tmp_path: Path) -> None:
        """Test returns empty for invalid xml."""
        pom = tmp_path / 'pom.xml'
        pom.write_text('not xml')
        deps = _parse_pom_dependencies(pom)
        assert deps == []


class TestParseSettingsGradle:
    """Tests for _parse_settings_gradle()."""

    def test_parses_includes(self, tmp_path: Path) -> None:
        """Test parses includes."""
        settings = tmp_path / 'settings.gradle'
        settings.write_text(_SETTINGS_GRADLE)
        includes = _parse_settings_gradle(settings)
        assert 'core' in includes
        assert 'plugins:google' in includes
        assert 'plugins:vertex' in includes

    def test_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        """Test returns empty for missing file."""
        includes = _parse_settings_gradle(tmp_path / 'settings.gradle')
        assert includes == []


class TestParseGradleDependencies:
    """Tests for _parse_gradle_dependencies()."""

    def test_parses_implementation_deps(self, tmp_path: Path) -> None:
        """Test parses implementation dependencies."""
        build = tmp_path / 'build.gradle'
        build.write_text(
            'dependencies {\n'
            "    implementation 'com.example:core:1.0.0'\n"
            "    implementation 'com.google.guava:guava:33.0.0-jre'\n"
            '}\n'
        )
        deps = _parse_gradle_dependencies(build)
        assert 'com.example:core' in deps
        assert 'com.google.guava:guava' in deps

    def test_parses_api_and_test_deps(self, tmp_path: Path) -> None:
        """Test parses api and testImplementation dependencies."""
        build = tmp_path / 'build.gradle'
        build.write_text(
            "dependencies {\n    api 'com.example:api-lib:2.0.0'\n    testImplementation 'junit:junit:4.13.2'\n}\n"
        )
        deps = _parse_gradle_dependencies(build)
        assert 'com.example:api-lib' in deps
        assert 'junit:junit' in deps

    def test_parses_compile_only_and_runtime_only(self, tmp_path: Path) -> None:
        """Test parses compileOnly and runtimeOnly dependencies."""
        build = tmp_path / 'build.gradle'
        build.write_text(
            'dependencies {\n'
            "    compileOnly 'javax.servlet:javax.servlet-api:4.0.1'\n"
            "    runtimeOnly 'org.postgresql:postgresql:42.7.1'\n"
            '}\n'
        )
        deps = _parse_gradle_dependencies(build)
        assert 'javax.servlet:javax.servlet-api' in deps
        assert 'org.postgresql:postgresql' in deps

    def test_returns_empty_for_no_deps(self, tmp_path: Path) -> None:
        """Test returns empty for no dependencies."""
        build = tmp_path / 'build.gradle'
        build.write_text("version = '1.0.0'\n")
        deps = _parse_gradle_dependencies(build)
        assert deps == []

    def test_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        """Test returns empty for missing file."""
        deps = _parse_gradle_dependencies(tmp_path / 'build.gradle')
        assert deps == []


class TestMavenWorkspaceInit:
    """Tests for MavenWorkspace initialization."""

    def test_stores_resolved_root(self, tmp_path: Path) -> None:
        """Test stores resolved root."""
        ws = MavenWorkspace(workspace_root=tmp_path)
        assert ws._root == tmp_path.resolve()


class TestMavenWorkspaceIsGradle:
    """Tests for MavenWorkspace._is_gradle()."""

    def test_detects_settings_gradle(self, tmp_path: Path) -> None:
        """Test detects settings gradle."""
        (tmp_path / 'settings.gradle').write_text('rootProject.name = "test"')
        ws = MavenWorkspace(workspace_root=tmp_path)
        assert ws._is_gradle() is True

    def test_detects_settings_gradle_kts(self, tmp_path: Path) -> None:
        """Test detects settings gradle kts."""
        (tmp_path / 'settings.gradle.kts').write_text('rootProject.name = "test"')
        ws = MavenWorkspace(workspace_root=tmp_path)
        assert ws._is_gradle() is True

    def test_not_gradle_for_maven(self, tmp_path: Path) -> None:
        """Test not gradle for maven."""
        (tmp_path / 'pom.xml').write_text(_POM_PARENT)
        ws = MavenWorkspace(workspace_root=tmp_path)
        assert ws._is_gradle() is False


class TestMavenWorkspaceDiscoverMaven:
    """Tests for MavenWorkspace.discover() with Maven."""

    @pytest.mark.asyncio
    async def test_discovers_maven_modules(self, tmp_path: Path) -> None:
        """Test discovers maven modules."""
        _setup_maven_workspace(tmp_path)
        ws = MavenWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        names = [p.name for p in packages]
        assert 'core' in names
        assert 'plugin-google' in names
        assert len(packages) == 2

    @pytest.mark.asyncio
    async def test_classifies_internal_deps(self, tmp_path: Path) -> None:
        """Test classifies internal deps."""
        _setup_maven_workspace(tmp_path)
        ws = MavenWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        plugin = next(p for p in packages if p.name == 'plugin-google')
        assert 'core' in plugin.internal_deps
        assert 'guava' in plugin.external_deps

    @pytest.mark.asyncio
    async def test_excludes_by_pattern(self, tmp_path: Path) -> None:
        """Test excludes by pattern."""
        _setup_maven_workspace(tmp_path)
        ws = MavenWorkspace(workspace_root=tmp_path)
        packages = await ws.discover(exclude_patterns=['plugin-*'])
        names = [p.name for p in packages]
        assert 'core' in names
        assert 'plugin-google' not in names

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_pom(self, tmp_path: Path) -> None:
        """Test returns empty when no pom."""
        ws = MavenWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        assert packages == []

    @pytest.mark.asyncio
    async def test_skips_modules_without_pom(self, tmp_path: Path) -> None:
        """Test skips modules without pom."""
        _setup_maven_workspace(tmp_path)
        # Add a module reference that has no pom.xml
        (tmp_path / 'pom.xml').write_text(_POM_PARENT.replace('</modules>', '<module>missing</module>\n  </modules>'))
        ws = MavenWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        names = [p.name for p in packages]
        assert 'missing' not in names


class TestMavenWorkspaceDiscoverGradle:
    """Tests for MavenWorkspace.discover() with Gradle."""

    @pytest.mark.asyncio
    async def test_discovers_gradle_projects(self, tmp_path: Path) -> None:
        """Test discovers gradle projects."""
        _setup_gradle_workspace(tmp_path)
        ws = MavenWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        names = [p.name for p in packages]
        assert 'core' in names
        assert 'plugins-google' in names
        assert 'plugins-vertex' in names

    @pytest.mark.asyncio
    async def test_reads_gradle_versions(self, tmp_path: Path) -> None:
        """Test reads gradle versions."""
        _setup_gradle_workspace(tmp_path)
        ws = MavenWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        core = next(p for p in packages if p.name == 'core')
        assert core.version == '1.0.0'

    @pytest.mark.asyncio
    async def test_excludes_by_pattern(self, tmp_path: Path) -> None:
        """Test excludes by pattern."""
        _setup_gradle_workspace(tmp_path)
        ws = MavenWorkspace(workspace_root=tmp_path)
        packages = await ws.discover(exclude_patterns=['plugins-*'])
        names = [p.name for p in packages]
        assert 'core' in names
        assert 'plugins-google' not in names

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_settings(self, tmp_path: Path) -> None:
        """Test returns empty when no settings."""
        ws = MavenWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        assert packages == []

    @pytest.mark.asyncio
    async def test_classifies_internal_deps(self, tmp_path: Path) -> None:
        """Test classifies internal dependencies."""
        _setup_gradle_workspace(tmp_path)
        ws = MavenWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        plugin = next(p for p in packages if p.name == 'plugins-google')
        assert 'core' in plugin.internal_deps
        assert 'com.google.code.gson:gson' in plugin.external_deps

    @pytest.mark.asyncio
    async def test_core_has_no_internal_deps(self, tmp_path: Path) -> None:
        """Test core has no internal dependencies."""
        _setup_gradle_workspace(tmp_path)
        ws = MavenWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        core = next(p for p in packages if p.name == 'core')
        assert core.internal_deps == []
        assert 'com.google.guava:guava' in core.external_deps

    @pytest.mark.asyncio
    async def test_all_deps_populated(self, tmp_path: Path) -> None:
        """Test all_deps is populated with raw coordinates."""
        _setup_gradle_workspace(tmp_path)
        ws = MavenWorkspace(workspace_root=tmp_path)
        packages = await ws.discover()
        plugin = next(p for p in packages if p.name == 'plugins-google')
        assert len(plugin.all_deps) == 2


class TestMavenWorkspaceRewriteVersion:
    """Tests for MavenWorkspace.rewrite_version()."""

    @pytest.mark.asyncio
    async def test_rewrites_pom_version(self, tmp_path: Path) -> None:
        """Test rewrites pom version."""
        pom = tmp_path / 'pom.xml'
        pom.write_text(_POM_CORE)
        ws = MavenWorkspace(workspace_root=tmp_path)
        old = await ws.rewrite_version(pom, '2.0.0')
        assert old == '1.0.0'
        assert '2.0.0' in pom.read_text()

    @pytest.mark.asyncio
    async def test_rewrites_gradle_version(self, tmp_path: Path) -> None:
        """Test rewrites gradle version."""
        build = tmp_path / 'build.gradle'
        build.write_text("version = '1.0.0'\n")
        ws = MavenWorkspace(workspace_root=tmp_path)
        old = await ws.rewrite_version(build, '2.0.0')
        assert old == '1.0.0'
        assert '2.0.0' in build.read_text()

    @pytest.mark.asyncio
    async def test_rewrites_gradle_kts_version(self, tmp_path: Path) -> None:
        """Test rewrites gradle kts version."""
        build = tmp_path / 'build.gradle.kts'
        build.write_text('version = "1.0.0"\n')
        ws = MavenWorkspace(workspace_root=tmp_path)
        old = await ws.rewrite_version(build, '3.0.0')
        assert old == '1.0.0'
        assert '3.0.0' in build.read_text()


class TestMavenWorkspaceRewriteDependencyVersion:
    """Tests for MavenWorkspace.rewrite_dependency_version()."""

    @pytest.mark.asyncio
    async def test_rewrites_pom_dependency(self, tmp_path: Path) -> None:
        """Test rewrites pom dependency."""
        pom = tmp_path / 'pom.xml'
        pom.write_text(_POM_PLUGIN)
        ws = MavenWorkspace(workspace_root=tmp_path)
        await ws.rewrite_dependency_version(pom, 'core', '2.0.0')
        text = pom.read_text()
        assert '<artifactId>core</artifactId>' in text
        assert '2.0.0' in text

    @pytest.mark.asyncio
    async def test_rewrites_gradle_dependency(self, tmp_path: Path) -> None:
        """Test rewrites gradle dependency."""
        build = tmp_path / 'build.gradle'
        build.write_text(
            'dependencies {\n'
            "    implementation 'com.example:core:1.0.0'\n"
            "    implementation 'com.google.guava:guava:33.0.0-jre'\n"
            '}\n'
        )
        ws = MavenWorkspace(workspace_root=tmp_path)
        await ws.rewrite_dependency_version(build, 'com.example:core', '2.0.0')
        text = build.read_text()
        assert 'com.example:core:2.0.0' in text
        assert 'com.google.guava:guava:33.0.0-jre' in text

    @pytest.mark.asyncio
    async def test_noop_when_dep_not_found(self, tmp_path: Path) -> None:
        """Test noop when dep not found."""
        pom = tmp_path / 'pom.xml'
        pom.write_text(_POM_CORE)
        ws = MavenWorkspace(workspace_root=tmp_path)
        await ws.rewrite_dependency_version(pom, 'nonexistent', '2.0.0')
        # Should not raise, just log debug
