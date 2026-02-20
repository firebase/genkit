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

"""Tests for releasekit.backends.pm.cargo module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from releasekit.backends._run import CommandResult
from releasekit.backends.pm import CargoBackend, PackageManager
from releasekit.backends.pm.cargo import _read_crate_name
from releasekit.logging import configure_logging

configure_logging(quiet=True)


class TestCargoBackendProtocol:
    """Verify CargoBackend implements the PackageManager protocol."""

    def test_implements_protocol(self, tmp_path: Path) -> None:
        """Test implements protocol."""
        backend = CargoBackend(workspace_root=tmp_path)
        assert isinstance(backend, PackageManager)

    def test_init_stores_root(self, tmp_path: Path) -> None:
        """Test init stores root."""
        backend = CargoBackend(workspace_root=tmp_path)
        assert backend._root == tmp_path


class TestCargoBackendBuild:
    """Tests for CargoBackend.build()."""

    @pytest.mark.asyncio
    async def test_build_dry_run(self, tmp_path: Path) -> None:
        """Test build dry run."""
        backend = CargoBackend(workspace_root=tmp_path)
        result = await backend.build(tmp_path / 'my-crate', dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_build_uses_cargo(self, tmp_path: Path) -> None:
        """Test build uses cargo."""
        backend = CargoBackend(workspace_root=tmp_path)
        result = await backend.build(tmp_path / 'my-crate', dry_run=True)
        assert 'cargo' in result.command
        assert 'build' in result.command
        assert '--release' in result.command

    @pytest.mark.asyncio
    async def test_build_with_output_dir(self, tmp_path: Path) -> None:
        """Test build with output dir."""
        backend = CargoBackend(workspace_root=tmp_path)
        out = tmp_path / 'target'
        result = await backend.build(tmp_path / 'crate', output_dir=out, dry_run=True)
        assert '--target-dir' in result.command
        assert str(out) in result.command

    @pytest.mark.asyncio
    async def test_build_with_crate_name_in_subdir(self, tmp_path: Path) -> None:
        """build() should use -p flag when package_dir differs from workspace root."""
        crate_dir = tmp_path / 'subcrate'
        crate_dir.mkdir()
        cargo_toml = crate_dir / 'Cargo.toml'
        cargo_toml.write_text('[package]\nname = "my-subcrate"\nversion = "0.1.0"\n')

        backend = CargoBackend(workspace_root=tmp_path)
        result = await backend.build(crate_dir, dry_run=True)
        assert '-p' in result.command
        assert 'my-subcrate' in result.command

    @pytest.mark.asyncio
    async def test_build_same_dir_no_p_flag(self, tmp_path: Path) -> None:
        """build() should NOT use -p flag when package_dir is workspace root."""
        cargo_toml = tmp_path / 'Cargo.toml'
        cargo_toml.write_text('[package]\nname = "root-crate"\nversion = "0.1.0"\n')

        backend = CargoBackend(workspace_root=tmp_path)
        result = await backend.build(tmp_path, dry_run=True)
        assert '-p' not in result.command


def _fake_run_command(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    dry_run: bool = False,
    **kwargs: object,
) -> CommandResult:
    """Fake run_command that captures the command without executing."""
    return CommandResult(
        command=cmd,
        return_code=0,
        stdout='',
        stderr='',
        duration=0.0,
        dry_run=dry_run,
    )


class TestCargoBackendPublish:
    """Tests for CargoBackend.publish().

    Note: publish() passes dry_run=False to run_command and uses cargo's
    own --dry-run flag. We mock run_command to avoid actually invoking cargo.
    """

    @pytest.mark.asyncio
    async def test_publish_dry_run(self, tmp_path: Path) -> None:
        """Test publish dry run."""
        backend = CargoBackend(workspace_root=tmp_path)
        with patch('releasekit.backends.pm.cargo.run_command', side_effect=_fake_run_command):
            result = await backend.publish(tmp_path / 'crate', dry_run=True)
        assert result.ok
        assert 'cargo' in result.command
        assert 'publish' in result.command
        assert '--no-verify' in result.command
        assert '--dry-run' in result.command

    @pytest.mark.asyncio
    async def test_publish_not_dry_run_no_flag(self, tmp_path: Path) -> None:
        """publish(dry_run=False) should not include --dry-run flag."""
        backend = CargoBackend(workspace_root=tmp_path)
        with patch('releasekit.backends.pm.cargo.run_command', side_effect=_fake_run_command):
            result = await backend.publish(tmp_path / 'crate', dry_run=False)
        assert '--dry-run' not in result.command

    @pytest.mark.asyncio
    async def test_publish_with_registry_url(self, tmp_path: Path) -> None:
        """Test publish with index url."""
        backend = CargoBackend(workspace_root=tmp_path)
        with patch('releasekit.backends.pm.cargo.run_command', side_effect=_fake_run_command):
            result = await backend.publish(
                tmp_path / 'crate',
                registry_url='https://my-registry.example.com',
                dry_run=True,
            )
        assert '--index' in result.command
        assert 'https://my-registry.example.com' in result.command

    @pytest.mark.asyncio
    async def test_publish_with_crate_name(self, tmp_path: Path) -> None:
        """Test publish with crate name."""
        crate_dir = tmp_path / 'subcrate'
        crate_dir.mkdir()
        (crate_dir / 'Cargo.toml').write_text('[package]\nname = "foo"\nversion = "1.0.0"\n')

        backend = CargoBackend(workspace_root=tmp_path)
        with patch('releasekit.backends.pm.cargo.run_command', side_effect=_fake_run_command):
            result = await backend.publish(crate_dir, dry_run=True)
        assert '-p' in result.command
        assert 'foo' in result.command


class TestCargoBackendLock:
    """Tests for CargoBackend.lock()."""

    @pytest.mark.asyncio
    async def test_lock_default(self, tmp_path: Path) -> None:
        """Test lock default."""
        backend = CargoBackend(workspace_root=tmp_path)
        result = await backend.lock(dry_run=True)
        assert result.ok
        assert 'cargo' in result.command
        assert 'update' in result.command

    @pytest.mark.asyncio
    async def test_lock_check_only(self, tmp_path: Path) -> None:
        """Test lock check only."""
        backend = CargoBackend(workspace_root=tmp_path)
        result = await backend.lock(check_only=True, dry_run=True)
        assert 'check' in result.command
        assert '--locked' in result.command

    @pytest.mark.asyncio
    async def test_lock_upgrade_package(self, tmp_path: Path) -> None:
        """Test lock upgrade package."""
        backend = CargoBackend(workspace_root=tmp_path)
        result = await backend.lock(upgrade_package='serde', dry_run=True)
        assert 'update' in result.command
        assert '-p' in result.command
        assert 'serde' in result.command

    @pytest.mark.asyncio
    async def test_lock_custom_cwd(self, tmp_path: Path) -> None:
        """Test lock custom cwd."""
        backend = CargoBackend(workspace_root=tmp_path)
        custom = tmp_path / 'subdir'
        result = await backend.lock(cwd=custom, dry_run=True)
        assert result.ok


class TestCargoBackendVersionBump:
    """Tests for CargoBackend.version_bump()."""

    @pytest.mark.asyncio
    async def test_version_bump_dry_run(self, tmp_path: Path) -> None:
        """Test version bump dry run."""
        crate_dir = tmp_path / 'crate'
        crate_dir.mkdir()
        (crate_dir / 'Cargo.toml').write_text('[package]\nname = "mycrate"\nversion = "0.1.0"\n')

        backend = CargoBackend(workspace_root=tmp_path)
        result = await backend.version_bump(crate_dir, '0.2.0', dry_run=True)
        assert result.ok
        assert 'set-version' in result.command
        assert '--package' in result.command
        assert 'mycrate' in result.command
        assert '0.2.0' in result.command

    @pytest.mark.asyncio
    async def test_version_bump_no_cargo_toml(self, tmp_path: Path) -> None:
        """Falls back to directory name when Cargo.toml is missing."""
        crate_dir = tmp_path / 'fallback-crate'
        crate_dir.mkdir()

        backend = CargoBackend(workspace_root=tmp_path)
        result = await backend.version_bump(crate_dir, '1.0.0', dry_run=True)
        assert 'fallback-crate' in result.command


class TestCargoBackendResolveCheck:
    """Tests for CargoBackend.resolve_check()."""

    @pytest.mark.asyncio
    async def test_resolve_check_dry_run(self, tmp_path: Path) -> None:
        """Test resolve check dry run."""
        backend = CargoBackend(workspace_root=tmp_path)
        result = await backend.resolve_check('serde', '1.0.200', dry_run=True)
        assert result.ok
        assert 'search' in result.command
        assert 'serde' in result.command
        assert '--limit' in result.command
        assert '1' in result.command

    @pytest.mark.asyncio
    async def test_resolve_check_with_index(self, tmp_path: Path) -> None:
        """Test resolve check with index."""
        backend = CargoBackend(workspace_root=tmp_path)
        result = await backend.resolve_check(
            'serde',
            '1.0.200',
            registry_url='https://my-index.example.com',
            dry_run=True,
        )
        assert '--index' in result.command
        assert 'https://my-index.example.com' in result.command


class TestCargoBackendSmokeTest:
    """Tests for CargoBackend.smoke_test()."""

    @pytest.mark.asyncio
    async def test_smoke_test_dry_run(self, tmp_path: Path) -> None:
        """Test smoke test dry run."""
        backend = CargoBackend(workspace_root=tmp_path)
        result = await backend.smoke_test('serde', '1.0.200', dry_run=True)
        assert result.ok
        assert 'test' in result.command
        assert '-p' in result.command
        assert 'serde' in result.command
        assert '--release' in result.command


class TestReadCrateName:
    """Tests for the _read_crate_name helper."""

    def test_reads_name_from_cargo_toml(self, tmp_path: Path) -> None:
        """Test reads name from cargo toml."""
        cargo_toml = tmp_path / 'Cargo.toml'
        cargo_toml.write_text('[package]\nname = "my-crate"\nversion = "0.1.0"\n')
        assert _read_crate_name(tmp_path) == 'my-crate'

    def test_reads_name_with_single_quotes(self, tmp_path: Path) -> None:
        """Test reads name with single quotes."""
        cargo_toml = tmp_path / 'Cargo.toml'
        cargo_toml.write_text("[package]\nname = 'single-quoted'\nversion = '0.1.0'\n")
        assert _read_crate_name(tmp_path) == 'single-quoted'

    def test_returns_none_when_no_cargo_toml(self, tmp_path: Path) -> None:
        """Test returns none when no cargo toml."""
        assert _read_crate_name(tmp_path) is None

    def test_returns_none_when_no_package_section(self, tmp_path: Path) -> None:
        """Test returns none when no package section."""
        cargo_toml = tmp_path / 'Cargo.toml'
        cargo_toml.write_text('[workspace]\nmembers = ["crate-a"]\n')
        assert _read_crate_name(tmp_path) is None

    def test_stops_at_next_section(self, tmp_path: Path) -> None:
        """Test stops at next section."""
        cargo_toml = tmp_path / 'Cargo.toml'
        cargo_toml.write_text(
            '[package]\nname = "before-section"\nversion = "0.1.0"\n\n[dependencies]\nserde = "1.0"\n'
        )
        assert _read_crate_name(tmp_path) == 'before-section'

    def test_handles_empty_cargo_toml(self, tmp_path: Path) -> None:
        """Test handles empty cargo toml."""
        cargo_toml = tmp_path / 'Cargo.toml'
        cargo_toml.write_text('')
        assert _read_crate_name(tmp_path) is None
