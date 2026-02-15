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

"""Tests for releasekit.backends.pm.go module."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends.pm import GoBackend, PackageManager
from releasekit.logging import configure_logging

configure_logging(quiet=True)


class TestGoBackendProtocol:
    """Verify GoBackend implements the PackageManager protocol."""

    def test_implements_protocol(self, tmp_path: Path) -> None:
        """Test implements protocol."""
        backend = GoBackend(workspace_root=tmp_path)
        assert isinstance(backend, PackageManager)

    def test_init_stores_root(self, tmp_path: Path) -> None:
        """Test init stores root."""
        backend = GoBackend(workspace_root=tmp_path)
        assert backend._root == tmp_path


class TestGoBackendBuild:
    """Tests for GoBackend.build()."""

    @pytest.mark.asyncio
    async def test_build_dry_run(self, tmp_path: Path) -> None:
        """Test build dry run."""
        backend = GoBackend(workspace_root=tmp_path)
        result = await backend.build(tmp_path / 'pkg', dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_build_uses_go_build(self, tmp_path: Path) -> None:
        """Test build uses go build."""
        backend = GoBackend(workspace_root=tmp_path)
        result = await backend.build(tmp_path / 'pkg', dry_run=True)
        assert result.command == ['go', 'build', './...']

    @pytest.mark.asyncio
    async def test_build_with_output_dir(self, tmp_path: Path) -> None:
        """output_dir sets GOBIN env var (not a command flag)."""
        backend = GoBackend(workspace_root=tmp_path)
        out = tmp_path / 'bin'
        result = await backend.build(tmp_path / 'pkg', output_dir=out, dry_run=True)
        assert result.ok
        # GOBIN is set via env, not as a command arg


class TestGoBackendPublish:
    """Tests for GoBackend.publish()."""

    @pytest.mark.asyncio
    async def test_publish_is_noop(self, tmp_path: Path) -> None:
        """Test publish is noop."""
        backend = GoBackend(workspace_root=tmp_path)
        result = await backend.publish(tmp_path / 'pkg', dry_run=True)
        assert result.ok
        assert result.return_code == 0
        assert 'VCS tags' in result.stdout

    @pytest.mark.asyncio
    async def test_publish_noop_dry_run_flag(self, tmp_path: Path) -> None:
        """Test publish noop dry run flag."""
        backend = GoBackend(workspace_root=tmp_path)
        result = await backend.publish(tmp_path / 'pkg', dry_run=True)
        assert result.dry_run is True

    @pytest.mark.asyncio
    async def test_publish_noop_not_dry_run(self, tmp_path: Path) -> None:
        """Test publish noop not dry run."""
        backend = GoBackend(workspace_root=tmp_path)
        result = await backend.publish(tmp_path / 'pkg', dry_run=False)
        assert result.ok
        assert result.dry_run is False
        assert 'VCS tags' in result.stdout


class TestGoBackendLock:
    """Tests for GoBackend.lock()."""

    @pytest.mark.asyncio
    async def test_lock_default(self, tmp_path: Path) -> None:
        """Test lock default."""
        backend = GoBackend(workspace_root=tmp_path)
        result = await backend.lock(dry_run=True)
        assert result.ok
        assert result.command == ['go', 'mod', 'tidy']

    @pytest.mark.asyncio
    async def test_lock_check_only(self, tmp_path: Path) -> None:
        """Test lock check only."""
        backend = GoBackend(workspace_root=tmp_path)
        result = await backend.lock(check_only=True, dry_run=True)
        assert 'mod' in result.command
        assert 'tidy' in result.command

    @pytest.mark.asyncio
    async def test_lock_upgrade_package(self, tmp_path: Path) -> None:
        """Test lock upgrade package."""
        backend = GoBackend(workspace_root=tmp_path)
        result = await backend.lock(upgrade_package='golang.org/x/net', dry_run=True)
        assert 'get' in result.command
        assert '-u' in result.command
        assert 'golang.org/x/net' in result.command

    @pytest.mark.asyncio
    async def test_lock_custom_cwd(self, tmp_path: Path) -> None:
        """Test lock custom cwd."""
        backend = GoBackend(workspace_root=tmp_path)
        custom = tmp_path / 'submod'
        result = await backend.lock(cwd=custom, dry_run=True)
        assert result.ok


class TestGoBackendVersionBump:
    """Tests for GoBackend.version_bump()."""

    @pytest.mark.asyncio
    async def test_version_bump_is_noop(self, tmp_path: Path) -> None:
        """Test version bump is noop."""
        backend = GoBackend(workspace_root=tmp_path)
        result = await backend.version_bump(tmp_path / 'pkg', '1.2.0', dry_run=True)
        assert result.ok
        assert result.return_code == 0
        assert '1.2.0' in result.stdout
        assert 'VCS tag' in result.stdout

    @pytest.mark.asyncio
    async def test_version_bump_dry_run_flag(self, tmp_path: Path) -> None:
        """Test version bump dry run flag."""
        backend = GoBackend(workspace_root=tmp_path)
        result = await backend.version_bump(tmp_path / 'pkg', '1.0.0', dry_run=True)
        assert result.dry_run is True


class TestGoBackendResolveCheck:
    """Tests for GoBackend.resolve_check()."""

    @pytest.mark.asyncio
    async def test_resolve_check_dry_run(self, tmp_path: Path) -> None:
        """Test resolve check dry run."""
        backend = GoBackend(workspace_root=tmp_path)
        result = await backend.resolve_check(
            'github.com/firebase/genkit/go/genkit',
            '0.5.0',
            dry_run=True,
        )
        assert result.ok
        assert 'list' in result.command
        assert '-m' in result.command
        assert 'github.com/firebase/genkit/go/genkit@v0.5.0' in result.command

    @pytest.mark.asyncio
    async def test_resolve_check_version_prefix(self, tmp_path: Path) -> None:
        """resolve_check should prepend 'v' to the version."""
        backend = GoBackend(workspace_root=tmp_path)
        result = await backend.resolve_check('example.com/mod', '1.0.0', dry_run=True)
        assert 'example.com/mod@v1.0.0' in result.command


class TestGoBackendSmokeTest:
    """Tests for GoBackend.smoke_test()."""

    @pytest.mark.asyncio
    async def test_smoke_test_dry_run(self, tmp_path: Path) -> None:
        """Test smoke test dry run."""
        backend = GoBackend(workspace_root=tmp_path)
        result = await backend.smoke_test(
            'github.com/firebase/genkit/go/genkit',
            '0.5.0',
            dry_run=True,
        )
        assert result.ok
        assert 'get' in result.command
        assert 'github.com/firebase/genkit/go/genkit@v0.5.0' in result.command
