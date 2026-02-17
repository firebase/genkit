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

"""Tests for the npm registry and pnpm package manager backends."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends.pm.pnpm import PnpmBackend
from releasekit.backends.registry.npm import NpmRegistry, _encode_package_name


class TestEncodePackageName:
    """Tests for scoped package URL encoding."""

    def test_unscoped(self) -> None:
        """Unscoped names are returned as-is."""
        assert _encode_package_name('genkit') == 'genkit'

    def test_scoped(self) -> None:
        """Scoped names have / encoded as %2F."""
        assert _encode_package_name('@genkit-ai/core') == '@genkit-ai%2Fcore'

    def test_scoped_nested(self) -> None:
        """Scoped names with nested paths are encoded correctly."""
        assert _encode_package_name('@scope/pkg-name') == '@scope%2Fpkg-name'

    def test_at_preserved(self) -> None:
        """The @ prefix is preserved (not encoded)."""
        encoded = _encode_package_name('@scope/name')
        assert encoded.startswith('@')
        assert '%40' not in encoded


class TestNpmRegistryInit:
    """NpmRegistry initialization."""

    def test_default_base_url(self) -> None:
        """Default base URL is the public npm registry."""
        registry = NpmRegistry()
        assert registry._base_url == 'https://registry.npmjs.org'

    def test_custom_base_url(self) -> None:
        """Custom registry URL (e.g. Verdaccio, Artifactory)."""
        registry = NpmRegistry(base_url='https://npm.example.com/')
        assert registry._base_url == 'https://npm.example.com'

    def test_trailing_slash_stripped(self) -> None:
        """Trailing slashes are stripped from the base URL."""
        registry = NpmRegistry(base_url='https://registry.npmjs.org/')
        assert registry._base_url == 'https://registry.npmjs.org'


class TestPnpmBackendBuild:
    """PnpmBackend.build() dry-run behavior."""

    @pytest.mark.asyncio
    async def test_build_dry_run(self, tmp_path: Path) -> None:
        """Build dry-run returns success without executing."""
        backend = PnpmBackend(tmp_path)
        result = await backend.build(tmp_path / 'packages' / 'core', dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_build_command_uses_pnpm_pack(self, tmp_path: Path) -> None:
        """Build command starts with 'pnpm pack'."""
        backend = PnpmBackend(tmp_path)
        result = await backend.build(tmp_path / 'core', dry_run=True)
        assert result.command[:2] == ['pnpm', 'pack']

    @pytest.mark.asyncio
    async def test_build_with_output_dir(self, tmp_path: Path) -> None:
        """Build with output_dir adds --pack-destination."""
        backend = PnpmBackend(tmp_path)
        out = tmp_path / 'dist'
        result = await backend.build(tmp_path / 'core', output_dir=out, dry_run=True)
        assert '--pack-destination' in result.command
        assert str(out) in result.command


class TestPnpmBackendPublish:
    """PnpmBackend.publish() dry-run behavior."""

    @pytest.mark.asyncio
    async def test_publish_dry_run(self, tmp_path: Path) -> None:
        """Publish dry-run includes --dry-run flag."""
        backend = PnpmBackend(tmp_path)
        result = await backend.publish(tmp_path / 'core', dry_run=True)
        assert '--dry-run' in result.command

    @pytest.mark.asyncio
    async def test_publish_includes_no_git_checks(self, tmp_path: Path) -> None:
        """Publish always includes --no-git-checks."""
        backend = PnpmBackend(tmp_path)
        result = await backend.publish(tmp_path / 'core', dry_run=True)
        assert '--no-git-checks' in result.command

    @pytest.mark.asyncio
    async def test_publish_includes_access_public(self, tmp_path: Path) -> None:
        """Publish always includes --access public."""
        backend = PnpmBackend(tmp_path)
        result = await backend.publish(tmp_path / 'core', dry_run=True)
        assert '--access' in result.command
        assert 'public' in result.command

    @pytest.mark.asyncio
    async def test_publish_with_registry(self, tmp_path: Path) -> None:
        """Publish with custom registry adds --registry."""
        backend = PnpmBackend(tmp_path)
        result = await backend.publish(
            tmp_path / 'core',
            registry_url='https://npm.example.com',
            dry_run=True,
        )
        assert '--registry' in result.command
        assert 'https://npm.example.com' in result.command


class TestPnpmBackendLock:
    """PnpmBackend.lock() dry-run behavior."""

    @pytest.mark.asyncio
    async def test_lock_update(self, tmp_path: Path) -> None:
        """Lock update uses --lockfile-only."""
        backend = PnpmBackend(tmp_path)
        result = await backend.lock(dry_run=True)
        assert '--lockfile-only' in result.command

    @pytest.mark.asyncio
    async def test_lock_check_only(self, tmp_path: Path) -> None:
        """Lock check uses --frozen-lockfile."""
        backend = PnpmBackend(tmp_path)
        result = await backend.lock(check_only=True, dry_run=True)
        assert '--frozen-lockfile' in result.command

    @pytest.mark.asyncio
    async def test_lock_upgrade_package(self, tmp_path: Path) -> None:
        """Lock upgrade uses pnpm update <package>."""
        backend = PnpmBackend(tmp_path)
        result = await backend.lock(upgrade_package='express', dry_run=True)
        assert result.command[:2] == ['pnpm', 'update']
        assert 'express' in result.command


class TestPnpmBackendVersionBump:
    """PnpmBackend.version_bump() dry-run behavior."""

    @pytest.mark.asyncio
    async def test_version_bump_dry_run(self, tmp_path: Path) -> None:
        """Version bump uses npm version with --no-git-tag-version."""
        backend = PnpmBackend(tmp_path)
        result = await backend.version_bump(tmp_path / 'core', '2.0.0', dry_run=True)
        assert 'npm' in result.command
        assert 'version' in result.command
        assert '2.0.0' in result.command
        assert '--no-git-tag-version' in result.command


class TestPnpmBackendResolveCheck:
    """PnpmBackend.resolve_check() dry-run behavior."""

    @pytest.mark.asyncio
    async def test_resolve_check_dry_run(self, tmp_path: Path) -> None:
        """Resolve check uses pnpm view."""
        backend = PnpmBackend(tmp_path)
        result = await backend.resolve_check('genkit', '1.28.0', dry_run=True)
        assert 'pnpm' in result.command
        assert 'view' in result.command
        assert 'genkit@1.28.0' in result.command

    @pytest.mark.asyncio
    async def test_resolve_check_with_registry(self, tmp_path: Path) -> None:
        """Resolve check with custom registry adds --registry."""
        backend = PnpmBackend(tmp_path)
        result = await backend.resolve_check(
            'genkit',
            '1.0.0',
            registry_url='https://npm.example.com',
            dry_run=True,
        )
        assert '--registry' in result.command
