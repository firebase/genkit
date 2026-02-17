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

"""Tests for releasekit.backends.pm.maturin module."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends.pm import MaturinBackend, PackageManager
from releasekit.logging import configure_logging

configure_logging(quiet=True)


class TestMaturinBackendProtocol:
    """Verify MaturinBackend implements the PackageManager protocol."""

    def test_implements_protocol(self, tmp_path: Path) -> None:
        """MaturinBackend should be a runtime-checkable PackageManager."""
        backend = MaturinBackend(workspace_root=tmp_path)
        assert isinstance(backend, PackageManager)


class TestMaturinBackendDryRun:
    """Tests for MaturinBackend in dry-run mode.

    These tests verify the command construction without actually
    executing maturin/uv commands, which may not be available in CI.
    """

    @pytest.mark.asyncio
    async def test_build_dry_run(self, tmp_path: Path) -> None:
        """build() in dry-run should return a synthetic success."""
        backend = MaturinBackend(workspace_root=tmp_path)
        pkg_dir = tmp_path / 'python' / 'handlebarrz'
        result = await backend.build(pkg_dir, dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_build_uses_maturin(self, tmp_path: Path) -> None:
        """build() should use maturin build --release."""
        backend = MaturinBackend(workspace_root=tmp_path)
        result = await backend.build(tmp_path / 'pkg', dry_run=True)
        assert 'maturin' in result.command
        assert 'build' in result.command
        assert '--release' in result.command

    @pytest.mark.asyncio
    async def test_build_includes_sdist(self, tmp_path: Path) -> None:
        """build() should include --sdist for source distribution."""
        backend = MaturinBackend(workspace_root=tmp_path)
        result = await backend.build(tmp_path / 'pkg', dry_run=True)
        assert '--sdist' in result.command

    @pytest.mark.asyncio
    async def test_build_with_output_dir(self, tmp_path: Path) -> None:
        """build() should include --out when output_dir is specified."""
        backend = MaturinBackend(workspace_root=tmp_path)
        out = tmp_path / 'dist'
        result = await backend.build(tmp_path / 'pkg', output_dir=out, dry_run=True)
        assert '--out' in result.command
        assert str(out) in result.command

    @pytest.mark.asyncio
    async def test_build_no_sources_ignored(self, tmp_path: Path) -> None:
        """build() should not include --no-sources (maturin doesn't use it)."""
        backend = MaturinBackend(workspace_root=tmp_path)
        result = await backend.build(tmp_path / 'pkg', no_sources=True, dry_run=True)
        assert '--no-sources' not in result.command

    @pytest.mark.asyncio
    async def test_publish_dry_run(self, tmp_path: Path) -> None:
        """publish() in dry-run should include dist dir."""
        backend = MaturinBackend(workspace_root=tmp_path)
        dist = tmp_path / 'dist'
        result = await backend.publish(dist, dry_run=True)
        assert result.ok
        assert str(dist) in result.command

    @pytest.mark.asyncio
    async def test_publish_uses_uv(self, tmp_path: Path) -> None:
        """publish() should use uv publish (not maturin publish)."""
        backend = MaturinBackend(workspace_root=tmp_path)
        result = await backend.publish(tmp_path / 'dist', dry_run=True)
        assert 'uv' in result.command
        assert 'publish' in result.command

    @pytest.mark.asyncio
    async def test_publish_with_check_url(self, tmp_path: Path) -> None:
        """publish() should include --check-url when provided."""
        backend = MaturinBackend(workspace_root=tmp_path)
        result = await backend.publish(
            tmp_path / 'dist',
            check_url='https://pypi.org/simple/dotpromptz-handlebars/',
            dry_run=True,
        )
        assert '--check-url' in result.command

    @pytest.mark.asyncio
    async def test_publish_with_registry_url(self, tmp_path: Path) -> None:
        """publish() should include --publish-url when registry_url is set."""
        backend = MaturinBackend(workspace_root=tmp_path)
        result = await backend.publish(
            tmp_path / 'dist',
            registry_url='https://test.pypi.org/legacy/',
            dry_run=True,
        )
        assert '--publish-url' in result.command
        assert 'https://test.pypi.org/legacy/' in result.command

    @pytest.mark.asyncio
    async def test_lock_check_only(self, tmp_path: Path) -> None:
        """lock(check_only=True) should include --check."""
        backend = MaturinBackend(workspace_root=tmp_path)
        result = await backend.lock(check_only=True, dry_run=True)
        assert '--check' in result.command

    @pytest.mark.asyncio
    async def test_lock_upgrade_package(self, tmp_path: Path) -> None:
        """lock(upgrade_package=...) should include --upgrade-package."""
        backend = MaturinBackend(workspace_root=tmp_path)
        result = await backend.lock(upgrade_package='pyo3', dry_run=True)
        assert '--upgrade-package' in result.command
        assert 'pyo3' in result.command

    @pytest.mark.asyncio
    async def test_version_bump_dry_run(self, tmp_path: Path) -> None:
        """version_bump() should use uv version."""
        backend = MaturinBackend(workspace_root=tmp_path)
        result = await backend.version_bump(tmp_path / 'pkg', '0.2.0', dry_run=True)
        assert result.ok
        assert '0.2.0' in result.command

    @pytest.mark.asyncio
    async def test_resolve_check_dry_run(self, tmp_path: Path) -> None:
        """resolve_check() should use uv pip install --dry-run."""
        backend = MaturinBackend(workspace_root=tmp_path)
        result = await backend.resolve_check('dotpromptz-handlebars', '0.1.8', dry_run=True)
        assert '--dry-run' in result.command
        assert 'dotpromptz-handlebars==0.1.8' in result.command

    @pytest.mark.asyncio
    async def test_smoke_test_dry_run(self, tmp_path: Path) -> None:
        """smoke_test() should use uv run --with."""
        backend = MaturinBackend(workspace_root=tmp_path)
        result = await backend.smoke_test('dotpromptz-handlebars', '0.1.8', dry_run=True)
        assert '--with' in result.command
        assert 'dotpromptz-handlebars==0.1.8' in result.command
