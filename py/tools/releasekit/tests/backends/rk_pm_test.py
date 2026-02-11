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

"""Tests for releasekit.backends.pm module."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends.pm import PackageManager, UvBackend
from releasekit.logging import configure_logging

configure_logging(quiet=True)


class TestUvBackendProtocol:
    """Verify UvBackend implements the PackageManager protocol."""

    def test_implements_protocol(self, tmp_path: Path) -> None:
        """UvBackend should be a runtime-checkable PackageManager."""
        backend = UvBackend(workspace_root=tmp_path)
        assert isinstance(backend, PackageManager)


class TestUvBackendDryRun:
    """Tests for UvBackend in dry-run mode.

    These tests verify the command construction without actually
    executing uv commands, which may not be available in CI.
    """

    @pytest.mark.asyncio
    async def test_build_dry_run(self, tmp_path: Path) -> None:
        """build() in dry-run should return a synthetic success."""
        backend = UvBackend(workspace_root=tmp_path)
        result = await backend.build(tmp_path / 'packages/genkit', dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_build_includes_no_sources(self, tmp_path: Path) -> None:
        """build() should include --no-sources by default."""
        backend = UvBackend(workspace_root=tmp_path)
        result = await backend.build(tmp_path / 'pkg', dry_run=True)
        assert '--no-sources' in result.command

    @pytest.mark.asyncio
    async def test_build_without_no_sources(self, tmp_path: Path) -> None:
        """build() should omit --no-sources when disabled."""
        backend = UvBackend(workspace_root=tmp_path)
        result = await backend.build(tmp_path / 'pkg', no_sources=False, dry_run=True)
        assert '--no-sources' not in result.command

    @pytest.mark.asyncio
    async def test_publish_dry_run(self, tmp_path: Path) -> None:
        """publish() in dry-run should include dist dir."""
        backend = UvBackend(workspace_root=tmp_path)
        dist = tmp_path / 'dist'
        result = await backend.publish(dist, dry_run=True)
        assert result.ok
        assert str(dist) in result.command

    @pytest.mark.asyncio
    async def test_publish_with_check_url(self, tmp_path: Path) -> None:
        """publish() should include --check-url when provided."""
        backend = UvBackend(workspace_root=tmp_path)
        result = await backend.publish(
            tmp_path / 'dist',
            check_url='https://pypi.org/simple/genkit/',
            dry_run=True,
        )
        assert '--check-url' in result.command

    @pytest.mark.asyncio
    async def test_lock_check_only(self, tmp_path: Path) -> None:
        """lock(check_only=True) should include --check."""
        backend = UvBackend(workspace_root=tmp_path)
        result = await backend.lock(check_only=True, dry_run=True)
        assert '--check' in result.command

    @pytest.mark.asyncio
    async def test_lock_upgrade_package(self, tmp_path: Path) -> None:
        """lock(upgrade_package=...) should include --upgrade-package."""
        backend = UvBackend(workspace_root=tmp_path)
        result = await backend.lock(upgrade_package='genkit', dry_run=True)
        assert '--upgrade-package' in result.command
        assert 'genkit' in result.command

    @pytest.mark.asyncio
    async def test_version_bump_dry_run(self, tmp_path: Path) -> None:
        """version_bump() should use uv version."""
        backend = UvBackend(workspace_root=tmp_path)
        result = await backend.version_bump(tmp_path / 'pkg', '1.0.0', dry_run=True)
        assert result.ok
        assert '1.0.0' in result.command

    @pytest.mark.asyncio
    async def test_resolve_check_dry_run(self, tmp_path: Path) -> None:
        """resolve_check() should use uv pip install --dry-run."""
        backend = UvBackend(workspace_root=tmp_path)
        result = await backend.resolve_check('genkit', '0.5.0', dry_run=True)
        assert '--dry-run' in result.command
        assert 'genkit==0.5.0' in result.command

    @pytest.mark.asyncio
    async def test_smoke_test_dry_run(self, tmp_path: Path) -> None:
        """smoke_test() should use uv run --with."""
        backend = UvBackend(workspace_root=tmp_path)
        result = await backend.smoke_test('genkit', '0.5.0', dry_run=True)
        assert '--with' in result.command
        assert 'genkit==0.5.0' in result.command
