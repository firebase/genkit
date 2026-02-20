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

"""Tests for :class:`releasekit.backends.pm.bazel.BazelBackend`."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends.pm import PackageManager
from releasekit.backends.pm.bazel import PUBLISH_MODES, BazelBackend


class TestBazelBackendProtocol:
    """Verify BazelBackend satisfies the PackageManager protocol."""

    def test_is_instance_of_protocol(self, tmp_path: Path) -> None:
        """BazelBackend should be a runtime-checkable PackageManager."""
        backend = BazelBackend(workspace_root=tmp_path)
        assert isinstance(backend, PackageManager)

    def test_default_publish_mode(self, tmp_path: Path) -> None:
        """Default publish mode should be java_export."""
        backend = BazelBackend(workspace_root=tmp_path)
        assert backend.publish_mode == 'java_export'

    def test_custom_publish_mode(self, tmp_path: Path) -> None:
        """Custom publish mode should be stored."""
        backend = BazelBackend(workspace_root=tmp_path, publish_mode='npm_package')
        assert backend.publish_mode == 'npm_package'

    def test_invalid_publish_mode_falls_back(self, tmp_path: Path) -> None:
        """Invalid publish mode should fall back to java_export."""
        backend = BazelBackend(workspace_root=tmp_path, publish_mode='nonexistent')
        assert backend.publish_mode == 'java_export'

    def test_all_publish_modes_are_strings(self) -> None:
        """All publish modes should be strings."""
        for mode in PUBLISH_MODES:
            assert isinstance(mode, str)


class TestBazelBackendBuild:
    """Tests for BazelBackend.build()."""

    @pytest.mark.asyncio
    async def test_build_dry_run(self, tmp_path: Path) -> None:
        """build() dry run should produce a bazel build command."""
        pkg = tmp_path / 'core'
        pkg.mkdir()
        backend = BazelBackend(workspace_root=tmp_path)
        result = await backend.build(pkg, dry_run=True)
        assert result.dry_run
        assert 'bazel' in result.command
        assert 'build' in result.command

    @pytest.mark.asyncio
    async def test_build_target_derivation(self, tmp_path: Path) -> None:
        """build() should derive //pkg:all target from package dir."""
        pkg = tmp_path / 'core'
        pkg.mkdir()
        backend = BazelBackend(workspace_root=tmp_path)
        result = await backend.build(pkg, dry_run=True)
        assert '//core:all' in result.command

    @pytest.mark.asyncio
    async def test_build_nested_package(self, tmp_path: Path) -> None:
        """build() should handle nested package paths."""
        pkg = tmp_path / 'plugins' / 'google'
        pkg.mkdir(parents=True)
        backend = BazelBackend(workspace_root=tmp_path)
        result = await backend.build(pkg, dry_run=True)
        assert '//plugins/google:all' in result.command


class TestBazelBackendPublish:
    """Tests for BazelBackend.publish() across publish modes."""

    @pytest.mark.asyncio
    async def test_publish_java_export(self, tmp_path: Path) -> None:
        """publish() with java_export should use .publish suffix."""
        pkg = tmp_path / 'core'
        pkg.mkdir()
        backend = BazelBackend(workspace_root=tmp_path, publish_mode='java_export')
        result = await backend.publish(pkg, dry_run=True)
        assert 'bazel' in result.command
        assert 'run' in result.command
        assert '//core:core.publish' in result.command

    @pytest.mark.asyncio
    async def test_publish_kt_jvm_export(self, tmp_path: Path) -> None:
        """publish() with kt_jvm_export should use .publish suffix."""
        pkg = tmp_path / 'kotlin-lib'
        pkg.mkdir()
        backend = BazelBackend(workspace_root=tmp_path, publish_mode='kt_jvm_export')
        result = await backend.publish(pkg, dry_run=True)
        assert '//kotlin-lib:kotlin-lib.publish' in result.command

    @pytest.mark.asyncio
    async def test_publish_npm_package(self, tmp_path: Path) -> None:
        """publish() with npm_package should use .publish suffix."""
        pkg = tmp_path / 'js-pkg'
        pkg.mkdir()
        backend = BazelBackend(workspace_root=tmp_path, publish_mode='npm_package')
        result = await backend.publish(pkg, dry_run=True)
        assert '//js-pkg:js-pkg.publish' in result.command

    @pytest.mark.asyncio
    async def test_publish_py_wheel(self, tmp_path: Path) -> None:
        """publish() with py_wheel should use .publish suffix."""
        pkg = tmp_path / 'py-pkg'
        pkg.mkdir()
        backend = BazelBackend(workspace_root=tmp_path, publish_mode='py_wheel')
        result = await backend.publish(pkg, dry_run=True)
        assert '//py-pkg:py-pkg.publish' in result.command

    @pytest.mark.asyncio
    async def test_publish_dart_pub_publish(self, tmp_path: Path) -> None:
        """publish() with dart_pub_publish should use dart_pub_publish target."""
        pkg = tmp_path / 'dart-pkg'
        pkg.mkdir()
        backend = BazelBackend(workspace_root=tmp_path, publish_mode='dart_pub_publish')
        result = await backend.publish(pkg, dry_run=True)
        assert '//dart-pkg:dart_pub_publish' in result.command

    @pytest.mark.asyncio
    async def test_publish_oci_push(self, tmp_path: Path) -> None:
        """publish() with oci_push should use push target."""
        pkg = tmp_path / 'container'
        pkg.mkdir()
        backend = BazelBackend(workspace_root=tmp_path, publish_mode='oci_push')
        result = await backend.publish(pkg, dry_run=True)
        assert '//container:push' in result.command

    @pytest.mark.asyncio
    async def test_publish_mvn_deploy(self, tmp_path: Path) -> None:
        """publish() with mvn_deploy should use publish target."""
        pkg = tmp_path / 'java-lib'
        pkg.mkdir()
        backend = BazelBackend(workspace_root=tmp_path, publish_mode='mvn_deploy')
        result = await backend.publish(pkg, dry_run=True)
        assert '//java-lib:publish' in result.command

    @pytest.mark.asyncio
    async def test_publish_custom(self, tmp_path: Path) -> None:
        """publish() with custom mode should use publish target."""
        pkg = tmp_path / 'custom-pkg'
        pkg.mkdir()
        backend = BazelBackend(workspace_root=tmp_path, publish_mode='custom')
        result = await backend.publish(pkg, dry_run=True)
        assert '//custom-pkg:publish' in result.command

    @pytest.mark.asyncio
    async def test_publish_explicit_target(self, tmp_path: Path) -> None:
        """publish() with explicit publish_target should use it directly."""
        pkg = tmp_path / 'core'
        pkg.mkdir()
        backend = BazelBackend(
            workspace_root=tmp_path,
            publish_target='//custom:my_deploy',
        )
        result = await backend.publish(pkg, dry_run=True)
        assert '//custom:my_deploy' in result.command

    @pytest.mark.asyncio
    async def test_publish_with_registry_url(self, tmp_path: Path) -> None:
        """publish() with registry_url should pass --define REGISTRY_URL."""
        pkg = tmp_path / 'core'
        pkg.mkdir()
        backend = BazelBackend(workspace_root=tmp_path)
        result = await backend.publish(
            pkg,
            registry_url='https://custom-registry.example.com',
            dry_run=True,
        )
        assert '--define' in result.command
        assert 'REGISTRY_URL=https://custom-registry.example.com' in result.command

    @pytest.mark.asyncio
    async def test_publish_npm_with_dist_tag(self, tmp_path: Path) -> None:
        """publish() npm_package with dist_tag should pass --define DIST_TAG."""
        pkg = tmp_path / 'js-pkg'
        pkg.mkdir()
        backend = BazelBackend(workspace_root=tmp_path, publish_mode='npm_package')
        result = await backend.publish(pkg, dist_tag='next', dry_run=True)
        assert '--define' in result.command
        assert 'DIST_TAG=next' in result.command

    @pytest.mark.asyncio
    async def test_publish_non_npm_ignores_dist_tag(self, tmp_path: Path) -> None:
        """publish() non-npm mode should ignore dist_tag."""
        pkg = tmp_path / 'core'
        pkg.mkdir()
        backend = BazelBackend(workspace_root=tmp_path, publish_mode='java_export')
        result = await backend.publish(pkg, dist_tag='next', dry_run=True)
        assert 'DIST_TAG' not in ' '.join(result.command)


class TestBazelBackendLock:
    """Tests for BazelBackend.lock()."""

    @pytest.mark.asyncio
    async def test_lock_jvm_mode(self, tmp_path: Path) -> None:
        """lock() for JVM modes should run @maven//:pin."""
        backend = BazelBackend(workspace_root=tmp_path, publish_mode='java_export')
        result = await backend.lock(dry_run=True)
        assert '@maven//:pin' in result.command

    @pytest.mark.asyncio
    async def test_lock_jvm_check_only(self, tmp_path: Path) -> None:
        """lock(check_only=True) for JVM should use lockfile_mode=error."""
        backend = BazelBackend(workspace_root=tmp_path, publish_mode='java_export')
        result = await backend.lock(check_only=True, dry_run=True)
        assert '--lockfile_mode=error' in result.command

    @pytest.mark.asyncio
    async def test_lock_non_jvm_mode(self, tmp_path: Path) -> None:
        """lock() for non-JVM modes should run bazel mod tidy."""
        backend = BazelBackend(workspace_root=tmp_path, publish_mode='npm_package')
        result = await backend.lock(dry_run=True)
        assert 'mod' in result.command
        assert 'tidy' in result.command

    @pytest.mark.asyncio
    async def test_lock_non_jvm_check_only(self, tmp_path: Path) -> None:
        """lock(check_only=True) for non-JVM should use lockfile_mode=error."""
        backend = BazelBackend(workspace_root=tmp_path, publish_mode='py_wheel')
        result = await backend.lock(check_only=True, dry_run=True)
        assert '--lockfile_mode=error' in result.command


class TestBazelBackendVersionBump:
    """Tests for BazelBackend.version_bump()."""

    @pytest.mark.asyncio
    async def test_version_bump_returns_synthetic(self, tmp_path: Path) -> None:
        """version_bump() should return a synthetic result."""
        backend = BazelBackend(workspace_root=tmp_path)
        result = await backend.version_bump(tmp_path / 'core', '2.0.0')
        assert result.ok
        assert '2.0.0' in result.stdout

    @pytest.mark.asyncio
    async def test_version_bump_dry_run(self, tmp_path: Path) -> None:
        """version_bump(dry_run=True) should set dry_run flag."""
        backend = BazelBackend(workspace_root=tmp_path)
        result = await backend.version_bump(tmp_path / 'core', '2.0.0', dry_run=True)
        assert result.dry_run


class TestBazelBackendResolveCheck:
    """Tests for BazelBackend.resolve_check()."""

    @pytest.mark.asyncio
    async def test_resolve_check_jvm(self, tmp_path: Path) -> None:
        """resolve_check() for JVM should use @maven//:pin with artifact."""
        backend = BazelBackend(workspace_root=tmp_path, publish_mode='java_export')
        result = await backend.resolve_check('com.example:core', '1.0.0', dry_run=True)
        assert '@maven//:pin' in result.command
        assert '--artifact=com.example:core:1.0.0' in result.command

    @pytest.mark.asyncio
    async def test_resolve_check_non_jvm(self, tmp_path: Path) -> None:
        """resolve_check() for non-JVM should use bazel fetch."""
        backend = BazelBackend(workspace_root=tmp_path, publish_mode='npm_package')
        result = await backend.resolve_check('my-pkg', '1.0.0', dry_run=True)
        assert 'fetch' in result.command


class TestBazelBackendSmokeTest:
    """Tests for BazelBackend.smoke_test()."""

    @pytest.mark.asyncio
    async def test_smoke_test_simple_name(self, tmp_path: Path) -> None:
        """smoke_test() with simple name should derive //name:all target."""
        backend = BazelBackend(workspace_root=tmp_path)
        result = await backend.smoke_test('core', '1.0.0', dry_run=True)
        assert 'test' in result.command
        assert '//core:all' in result.command

    @pytest.mark.asyncio
    async def test_smoke_test_explicit_target(self, tmp_path: Path) -> None:
        """smoke_test() with explicit target should use it directly."""
        backend = BazelBackend(workspace_root=tmp_path)
        result = await backend.smoke_test('//core:tests', '1.0.0', dry_run=True)
        assert '//core:tests' in result.command

    @pytest.mark.asyncio
    async def test_smoke_test_colon_target(self, tmp_path: Path) -> None:
        """smoke_test() with colon in name should use it directly."""
        backend = BazelBackend(workspace_root=tmp_path)
        result = await backend.smoke_test('core:integration_tests', '1.0.0', dry_run=True)
        assert 'core:integration_tests' in result.command
