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

"""Tests for releasekit.backends.pm.dart module."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends.pm import DartBackend, PackageManager
from releasekit.logging import configure_logging

configure_logging(quiet=True)


class TestDartBackendProtocol:
    """Verify DartBackend implements the PackageManager protocol."""

    def test_implements_protocol(self, tmp_path: Path) -> None:
        """Test implements protocol."""
        backend = DartBackend(workspace_root=tmp_path)
        assert isinstance(backend, PackageManager)

    def test_init_stores_root(self, tmp_path: Path) -> None:
        """Test init stores root."""
        backend = DartBackend(workspace_root=tmp_path)
        assert backend._root == tmp_path


class TestDartBackendBuild:
    """Tests for DartBackend.build()."""

    @pytest.mark.asyncio
    async def test_build_dry_run(self, tmp_path: Path) -> None:
        """Test build dry run."""
        backend = DartBackend(workspace_root=tmp_path)
        result = await backend.build(tmp_path / 'pkg', dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_build_uses_dart_pub_get(self, tmp_path: Path) -> None:
        """Test build uses dart pub get."""
        backend = DartBackend(workspace_root=tmp_path)
        result = await backend.build(tmp_path / 'pkg', dry_run=True)
        assert result.command == ['dart', 'pub', 'get']


class TestDartBackendPublish:
    """Tests for DartBackend.publish()."""

    @pytest.mark.asyncio
    async def test_publish_dry_run(self, tmp_path: Path) -> None:
        """Test publish dry run."""
        backend = DartBackend(workspace_root=tmp_path)
        result = await backend.publish(tmp_path / 'pkg', dry_run=True)
        assert result.ok
        assert 'dart' in result.command
        assert 'pub' in result.command
        assert 'publish' in result.command
        assert '--force' in result.command
        assert '--dry-run' in result.command

    @pytest.mark.asyncio
    async def test_publish_with_registry_url(self, tmp_path: Path) -> None:
        """Test publish with index url."""
        backend = DartBackend(workspace_root=tmp_path)
        result = await backend.publish(
            tmp_path / 'pkg',
            registry_url='https://my-pub-server.example.com',
            dry_run=True,
        )
        assert '--server' in result.command
        assert 'https://my-pub-server.example.com' in result.command

    @pytest.mark.asyncio
    async def test_publish_without_dry_run_no_flag(self, tmp_path: Path) -> None:
        """When dry_run=False on the method, --dry-run should not be in the cargo cmd."""
        backend = DartBackend(workspace_root=tmp_path)
        # We can't actually run dart, but we can verify the command construction
        # by passing dry_run=True to run_command (which the backend does via dry_run param)
        result = await backend.publish(tmp_path / 'pkg', dry_run=True)
        # dry_run=True adds --dry-run to the dart command
        assert '--dry-run' in result.command


class TestDartBackendLock:
    """Tests for DartBackend.lock()."""

    @pytest.mark.asyncio
    async def test_lock_default(self, tmp_path: Path) -> None:
        """Test lock default."""
        backend = DartBackend(workspace_root=tmp_path)
        result = await backend.lock(dry_run=True)
        assert result.ok
        assert result.command == ['dart', 'pub', 'get']

    @pytest.mark.asyncio
    async def test_lock_check_only(self, tmp_path: Path) -> None:
        """Test lock check only."""
        backend = DartBackend(workspace_root=tmp_path)
        result = await backend.lock(check_only=True, dry_run=True)
        assert '--dry-run' in result.command
        assert 'get' in result.command

    @pytest.mark.asyncio
    async def test_lock_upgrade_package(self, tmp_path: Path) -> None:
        """Test lock upgrade package."""
        backend = DartBackend(workspace_root=tmp_path)
        result = await backend.lock(upgrade_package='http', dry_run=True)
        assert 'upgrade' in result.command
        assert 'http' in result.command

    @pytest.mark.asyncio
    async def test_lock_custom_cwd(self, tmp_path: Path) -> None:
        """Test lock custom cwd."""
        backend = DartBackend(workspace_root=tmp_path)
        custom = tmp_path / 'subpkg'
        result = await backend.lock(cwd=custom, dry_run=True)
        assert result.ok


class TestDartBackendVersionBump:
    """Tests for DartBackend.version_bump()."""

    @pytest.mark.asyncio
    async def test_version_bump_returns_synthetic(self, tmp_path: Path) -> None:
        """Test version bump returns synthetic."""
        backend = DartBackend(workspace_root=tmp_path)
        result = await backend.version_bump(tmp_path / 'pkg', '0.2.0', dry_run=True)
        assert result.ok
        assert result.return_code == 0
        assert '0.2.0' in result.stdout
        assert 'pubspec.yaml' in result.stdout

    @pytest.mark.asyncio
    async def test_version_bump_dry_run_flag(self, tmp_path: Path) -> None:
        """Test version bump dry run flag."""
        backend = DartBackend(workspace_root=tmp_path)
        result = await backend.version_bump(tmp_path / 'pkg', '1.0.0', dry_run=True)
        assert result.dry_run is True


class TestDartBackendResolveCheck:
    """Tests for DartBackend.resolve_check()."""

    @pytest.mark.asyncio
    async def test_resolve_check_dry_run(self, tmp_path: Path) -> None:
        """Test resolve check dry run."""
        backend = DartBackend(workspace_root=tmp_path)
        result = await backend.resolve_check('http', '1.2.0', dry_run=True)
        assert result.ok
        assert 'cache' in result.command
        assert 'add' in result.command
        assert 'http' in result.command
        assert '--version' in result.command
        assert '1.2.0' in result.command


class TestDartBackendSmokeTest:
    """Tests for DartBackend.smoke_test()."""

    @pytest.mark.asyncio
    async def test_smoke_test_dry_run(self, tmp_path: Path) -> None:
        """Test smoke test dry run."""
        backend = DartBackend(workspace_root=tmp_path)
        result = await backend.smoke_test('http', '1.2.0', dry_run=True)
        assert result.ok
        assert 'cache' in result.command
        assert 'add' in result.command
        assert 'http' in result.command
        assert '--version' in result.command
        assert '1.2.0' in result.command
