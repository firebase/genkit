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

"""Tests for releasekit.backends.vcs.mercurial module."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends.vcs.mercurial import MercurialCLIBackend
from releasekit.logging import configure_logging

configure_logging(quiet=True)


class TestMercurialCLIBackendInit:
    """Tests for MercurialCLIBackend initialization."""

    def test_stores_root(self, tmp_path: Path) -> None:
        """Test stores root."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        assert backend._root == tmp_path


class TestMercurialIsClean:
    """Tests for MercurialCLIBackend.is_clean()."""

    @pytest.mark.asyncio
    async def test_dry_run_returns_true(self, tmp_path: Path) -> None:
        """Test dry run returns true."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        result = await backend.is_clean(dry_run=True)
        assert result is True


class TestMercurialIsShallow:
    """Tests for MercurialCLIBackend.is_shallow()."""

    @pytest.mark.asyncio
    async def test_always_returns_false(self, tmp_path: Path) -> None:
        """Test always returns false."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        result = await backend.is_shallow()
        assert result is False


class TestMercurialDefaultBranch:
    """Tests for MercurialCLIBackend.default_branch()."""

    @pytest.mark.asyncio
    async def test_returns_default(self, tmp_path: Path) -> None:
        """Test returns default."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        result = await backend.default_branch()
        assert result == 'default'


class TestMercurialHgHelper:
    """Tests for MercurialCLIBackend._hg() helper."""

    def test_dry_run_returns_success(self, tmp_path: Path) -> None:
        """Test dry run returns success."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        result = backend._hg('status', dry_run=True)
        assert result.ok
        assert result.dry_run
        assert result.command == ['hg', 'status']

    def test_dry_run_with_multiple_args(self, tmp_path: Path) -> None:
        """Test dry run with multiple args."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        result = backend._hg('log', '-r', '.', '--template', '{node}', dry_run=True)
        assert result.ok
        assert result.command == ['hg', 'log', '-r', '.', '--template', '{node}']


class TestMercurialCommit:
    """Tests for MercurialCLIBackend.commit()."""

    @pytest.mark.asyncio
    async def test_commit_dry_run(self, tmp_path: Path) -> None:
        """Test commit dry run."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        result = await backend.commit('test message', dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_commit_with_paths_dry_run(self, tmp_path: Path) -> None:
        """Test commit with paths dry run."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        result = await backend.commit('test', paths=['src/foo.py'], dry_run=True)
        assert result.ok


class TestMercurialTag:
    """Tests for MercurialCLIBackend.tag()."""

    @pytest.mark.asyncio
    async def test_tag_dry_run(self, tmp_path: Path) -> None:
        """Test tag dry run."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        result = await backend.tag('v1.0.0', dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_tag_with_message_dry_run(self, tmp_path: Path) -> None:
        """Test tag with message dry run."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        result = await backend.tag('v1.0.0', message='Release 1.0.0', dry_run=True)
        assert result.ok


class TestMercurialDeleteTag:
    """Tests for MercurialCLIBackend.delete_tag()."""

    @pytest.mark.asyncio
    async def test_delete_tag_dry_run(self, tmp_path: Path) -> None:
        """Test delete tag dry run."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        result = await backend.delete_tag('v1.0.0', dry_run=True)
        assert result.ok
        assert result.dry_run


class TestMercurialPush:
    """Tests for MercurialCLIBackend.push()."""

    @pytest.mark.asyncio
    async def test_push_dry_run(self, tmp_path: Path) -> None:
        """Test push dry run."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        result = await backend.push(dry_run=True)
        assert result.ok
        assert result.dry_run

    @pytest.mark.asyncio
    async def test_push_maps_origin_to_default(self, tmp_path: Path) -> None:
        """Test push maps origin to default."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        result = await backend.push(remote='origin', dry_run=True)
        assert 'default' in result.command

    @pytest.mark.asyncio
    async def test_push_custom_remote(self, tmp_path: Path) -> None:
        """Test push custom remote."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        result = await backend.push(remote='upstream', dry_run=True)
        assert 'upstream' in result.command


class TestMercurialCheckoutBranch:
    """Tests for MercurialCLIBackend.checkout_branch()."""

    @pytest.mark.asyncio
    async def test_create_bookmark_dry_run(self, tmp_path: Path) -> None:
        """Test create bookmark dry run."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        result = await backend.checkout_branch('feature-x', create=True, dry_run=True)
        assert result.ok
        assert 'bookmark' in result.command
        assert 'feature-x' in result.command

    @pytest.mark.asyncio
    async def test_switch_bookmark_dry_run(self, tmp_path: Path) -> None:
        """Test switch bookmark dry run."""
        backend = MercurialCLIBackend(repo_root=tmp_path)
        result = await backend.checkout_branch('feature-x', create=False, dry_run=True)
        assert result.ok
        assert 'update' in result.command
        assert 'feature-x' in result.command
