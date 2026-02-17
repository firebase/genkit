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

"""Tests for releasekit.backends.pm.maven module."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends.pm import MavenBackend, PackageManager
from releasekit.logging import configure_logging

configure_logging(quiet=True)


def _make_maven_dir(tmp_path: Path) -> Path:
    """Create a directory with pom.xml (Maven project)."""
    pkg = tmp_path / 'java-lib'
    pkg.mkdir()
    (pkg / 'pom.xml').write_text('<project><version>1.0.0</version></project>')
    return pkg


def _make_gradle_dir(tmp_path: Path, *, with_wrapper: bool = False) -> Path:
    """Create a directory with build.gradle (Gradle project)."""
    pkg = tmp_path / 'gradle-lib'
    pkg.mkdir()
    (pkg / 'build.gradle').write_text("version = '1.0.0'\n")
    if with_wrapper:
        wrapper = pkg / 'gradlew'
        wrapper.write_text('#!/bin/sh\nexec gradle "$@"\n')
        wrapper.chmod(0o755)
    return pkg


def _make_gradle_kts_dir(tmp_path: Path) -> Path:
    """Create a directory with build.gradle.kts (Kotlin DSL)."""
    pkg = tmp_path / 'kts-lib'
    pkg.mkdir()
    (pkg / 'build.gradle.kts').write_text('version = "1.0.0"\n')
    return pkg


class TestMavenBackendProtocol:
    """Verify MavenBackend implements the PackageManager protocol."""

    def test_implements_protocol(self, tmp_path: Path) -> None:
        """Test implements protocol."""
        backend = MavenBackend(workspace_root=tmp_path)
        assert isinstance(backend, PackageManager)

    def test_init_stores_root(self, tmp_path: Path) -> None:
        """Test init stores root."""
        backend = MavenBackend(workspace_root=tmp_path)
        assert backend._root == tmp_path


class TestMavenBackendIsGradle:
    """Tests for MavenBackend._is_gradle() detection."""

    def test_detects_build_gradle(self, tmp_path: Path) -> None:
        """Test detects build gradle."""
        pkg = _make_gradle_dir(tmp_path)
        assert MavenBackend._is_gradle(pkg) is True

    def test_detects_build_gradle_kts(self, tmp_path: Path) -> None:
        """Test detects build gradle kts."""
        pkg = _make_gradle_kts_dir(tmp_path)
        assert MavenBackend._is_gradle(pkg) is True

    def test_not_gradle_for_maven(self, tmp_path: Path) -> None:
        """Test not gradle for maven."""
        pkg = _make_maven_dir(tmp_path)
        assert MavenBackend._is_gradle(pkg) is False

    def test_not_gradle_for_empty_dir(self, tmp_path: Path) -> None:
        """Test not gradle for empty dir."""
        assert MavenBackend._is_gradle(tmp_path) is False


class TestMavenBackendGradleCmd:
    """Tests for MavenBackend._gradle_cmd()."""

    def test_uses_wrapper_when_present(self, tmp_path: Path) -> None:
        """Test uses wrapper when present."""
        pkg = _make_gradle_dir(tmp_path, with_wrapper=True)
        cmd = MavenBackend._gradle_cmd(pkg)
        assert 'gradlew' in cmd

    def test_falls_back_to_gradle(self, tmp_path: Path) -> None:
        """Test falls back to gradle."""
        pkg = _make_gradle_dir(tmp_path, with_wrapper=False)
        cmd = MavenBackend._gradle_cmd(pkg)
        assert cmd == 'gradle'


class TestMavenBackendBuild:
    """Tests for MavenBackend.build()."""

    @pytest.mark.asyncio
    async def test_build_maven_dry_run(self, tmp_path: Path) -> None:
        """Test build maven dry run."""
        pkg = _make_maven_dir(tmp_path)
        backend = MavenBackend(workspace_root=tmp_path)
        result = await backend.build(pkg, dry_run=True)
        assert result.ok
        assert result.dry_run
        assert 'mvn' in result.command
        assert 'package' in result.command
        assert '-DskipTests' in result.command

    @pytest.mark.asyncio
    async def test_build_gradle_dry_run(self, tmp_path: Path) -> None:
        """Test build gradle dry run."""
        pkg = _make_gradle_dir(tmp_path)
        backend = MavenBackend(workspace_root=tmp_path)
        result = await backend.build(pkg, dry_run=True)
        assert result.ok
        assert 'build' in result.command
        assert '-x' in result.command
        assert 'test' in result.command

    @pytest.mark.asyncio
    async def test_build_gradle_with_wrapper(self, tmp_path: Path) -> None:
        """Test build gradle with wrapper."""
        pkg = _make_gradle_dir(tmp_path, with_wrapper=True)
        backend = MavenBackend(workspace_root=tmp_path)
        result = await backend.build(pkg, dry_run=True)
        assert 'gradlew' in result.command[0]


class TestMavenBackendPublish:
    """Tests for MavenBackend.publish()."""

    @pytest.mark.asyncio
    async def test_publish_maven_dry_run(self, tmp_path: Path) -> None:
        """Test publish maven dry run."""
        pkg = _make_maven_dir(tmp_path)
        backend = MavenBackend(workspace_root=tmp_path)
        result = await backend.publish(pkg, dry_run=True)
        assert result.ok
        assert 'mvn' in result.command
        assert 'deploy' in result.command
        assert '-DskipTests' in result.command

    @pytest.mark.asyncio
    async def test_publish_maven_with_registry_url(self, tmp_path: Path) -> None:
        """Test publish maven with index url."""
        pkg = _make_maven_dir(tmp_path)
        backend = MavenBackend(workspace_root=tmp_path)
        result = await backend.publish(
            pkg,
            registry_url='https://oss.sonatype.org/content/repositories/releases/',
            dry_run=True,
        )
        assert any('-DaltDeploymentRepository=' in arg for arg in result.command)

    @pytest.mark.asyncio
    async def test_publish_gradle_dry_run(self, tmp_path: Path) -> None:
        """Test publish gradle dry run."""
        pkg = _make_gradle_dir(tmp_path)
        backend = MavenBackend(workspace_root=tmp_path)
        result = await backend.publish(pkg, dry_run=True)
        assert result.ok
        assert 'publish' in result.command

    @pytest.mark.asyncio
    async def test_publish_gradle_with_registry_url(self, tmp_path: Path) -> None:
        """Test publish gradle with index url passes -PmavenUrl."""
        pkg = _make_gradle_dir(tmp_path)
        backend = MavenBackend(workspace_root=tmp_path)
        result = await backend.publish(
            pkg,
            registry_url='https://maven.example.com/releases/',
            dry_run=True,
        )
        assert any('-PmavenUrl=' in arg for arg in result.command)


class TestMavenBackendLock:
    """Tests for MavenBackend.lock()."""

    @pytest.mark.asyncio
    async def test_lock_maven_default(self, tmp_path: Path) -> None:
        """Test lock maven default."""
        pkg = _make_maven_dir(tmp_path)
        backend = MavenBackend(workspace_root=pkg)
        result = await backend.lock(dry_run=True)
        assert result.ok
        assert 'mvn' in result.command
        assert 'dependency:resolve' in result.command

    @pytest.mark.asyncio
    async def test_lock_gradle_default(self, tmp_path: Path) -> None:
        """Test lock gradle default."""
        pkg = _make_gradle_dir(tmp_path)
        backend = MavenBackend(workspace_root=pkg)
        result = await backend.lock(dry_run=True)
        assert result.ok
        assert 'dependencies' in result.command
        assert '--refresh-dependencies' in result.command

    @pytest.mark.asyncio
    async def test_lock_gradle_check_only(self, tmp_path: Path) -> None:
        """Test lock gradle check_only omits --refresh-dependencies."""
        pkg = _make_gradle_dir(tmp_path)
        backend = MavenBackend(workspace_root=pkg)
        result = await backend.lock(check_only=True, dry_run=True)
        assert result.ok
        assert 'dependencies' in result.command
        assert '--refresh-dependencies' not in result.command

    @pytest.mark.asyncio
    async def test_lock_custom_cwd(self, tmp_path: Path) -> None:
        """Test lock custom cwd."""
        pkg = _make_maven_dir(tmp_path)
        backend = MavenBackend(workspace_root=tmp_path)
        result = await backend.lock(cwd=pkg, dry_run=True)
        assert result.ok


class TestMavenBackendVersionBump:
    """Tests for MavenBackend.version_bump()."""

    @pytest.mark.asyncio
    async def test_version_bump_maven(self, tmp_path: Path) -> None:
        """Test version bump maven."""
        pkg = _make_maven_dir(tmp_path)
        backend = MavenBackend(workspace_root=tmp_path)
        result = await backend.version_bump(pkg, '2.0.0', dry_run=True)
        assert result.ok
        assert 'mvn' in result.command
        assert 'versions:set' in result.command
        assert '-DnewVersion=2.0.0' in result.command
        assert '-DgenerateBackupPoms=false' in result.command

    @pytest.mark.asyncio
    async def test_version_bump_gradle_returns_synthetic(self, tmp_path: Path) -> None:
        """Test version bump gradle returns synthetic."""
        pkg = _make_gradle_dir(tmp_path)
        backend = MavenBackend(workspace_root=tmp_path)
        result = await backend.version_bump(pkg, '2.0.0', dry_run=True)
        assert result.ok
        assert result.return_code == 0
        assert '2.0.0' in result.stdout


class TestMavenBackendResolveCheck:
    """Tests for MavenBackend.resolve_check()."""

    @pytest.mark.asyncio
    async def test_resolve_check_maven_dry_run(self, tmp_path: Path) -> None:
        """Test resolve check maven dry run."""
        backend = MavenBackend(workspace_root=tmp_path)
        result = await backend.resolve_check(
            'com.google.genkit:genkit-core',
            '0.5.0',
            dry_run=True,
        )
        assert result.ok
        assert 'dependency:get' in result.command
        assert '-Dartifact=com.google.genkit:genkit-core:0.5.0' in result.command
        assert '-Dtransitive=false' in result.command

    @pytest.mark.asyncio
    async def test_resolve_check_gradle_dry_run(self, tmp_path: Path) -> None:
        """Test resolve check gradle uses dependencyInsight."""
        pkg = _make_gradle_dir(tmp_path)
        backend = MavenBackend(workspace_root=pkg)
        result = await backend.resolve_check(
            'com.example:core',
            '1.0.0',
            dry_run=True,
        )
        assert result.ok
        assert 'dependencyInsight' in result.command
        assert '--dependency=com.example:core' in result.command


class TestMavenBackendSmokeTest:
    """Tests for MavenBackend.smoke_test()."""

    @pytest.mark.asyncio
    async def test_smoke_test_maven_delegates_to_resolve_check(self, tmp_path: Path) -> None:
        """Test smoke test delegates to resolve check."""
        backend = MavenBackend(workspace_root=tmp_path)
        result = await backend.smoke_test(
            'com.google.genkit:genkit-core',
            '0.5.0',
            dry_run=True,
        )
        assert result.ok
        assert 'dependency:get' in result.command

    @pytest.mark.asyncio
    async def test_smoke_test_gradle_delegates_to_resolve_check(self, tmp_path: Path) -> None:
        """Test smoke test gradle delegates to resolve check."""
        pkg = _make_gradle_dir(tmp_path)
        backend = MavenBackend(workspace_root=pkg)
        result = await backend.smoke_test(
            'com.example:core',
            '1.0.0',
            dry_run=True,
        )
        assert result.ok
        assert 'dependencyInsight' in result.command
