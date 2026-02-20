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

"""Tests for releasekit.backends.vcs module."""

from __future__ import annotations

from pathlib import Path

import pytest
from releasekit.backends._run import run_command
from releasekit.backends.vcs import VCS, GitCLIBackend
from releasekit.logging import configure_logging

configure_logging(quiet=True)


def _init_repo(path: Path) -> GitCLIBackend:
    """Create a git repo with one commit and return a GitCLIBackend."""
    run_command(['git', 'init'], cwd=path, check=True)
    run_command(['git', 'config', 'user.email', 'test@example.com'], cwd=path, check=True)
    run_command(['git', 'config', 'user.name', 'Test User'], cwd=path, check=True)
    (path / 'README.md').write_text('# Test\n')
    run_command(['git', 'add', '.'], cwd=path, check=True)
    run_command(['git', 'commit', '-m', 'Initial commit'], cwd=path, check=True)
    return GitCLIBackend(repo_root=path)


class TestGitCLIBackendProtocol:
    """Verify GitCLIBackend implements the VCS protocol."""

    def test_implements_vcs(self, tmp_path: Path) -> None:
        """GitCLIBackend should be a runtime-checkable VCS."""
        backend = GitCLIBackend(repo_root=tmp_path)
        assert isinstance(backend, VCS)


class TestGitCLIBackendIsClean:
    """Tests for GitCLIBackend.is_clean()."""

    @pytest.mark.asyncio
    async def test_clean_repo(self, tmp_path: Path) -> None:
        """Should return True for a clean repo."""
        backend = _init_repo(tmp_path)
        assert await backend.is_clean()

    @pytest.mark.asyncio
    async def test_dirty_repo(self, tmp_path: Path) -> None:
        """Should return False when there are uncommitted changes."""
        backend = _init_repo(tmp_path)
        (tmp_path / 'new_file.txt').write_text('dirty')
        assert not await backend.is_clean()

    @pytest.mark.asyncio
    async def test_dry_run_returns_true(self, tmp_path: Path) -> None:
        """dry_run should always return True."""
        backend = _init_repo(tmp_path)
        (tmp_path / 'dirty.txt').write_text('dirty')
        assert await backend.is_clean(dry_run=True)


class TestGitCLIBackendIsShallow:
    """Tests for GitCLIBackend.is_shallow()."""

    @pytest.mark.asyncio
    async def test_not_shallow(self, tmp_path: Path) -> None:
        """A regular repo should not be shallow."""
        backend = _init_repo(tmp_path)
        assert not await backend.is_shallow()


class TestGitCLIBackendCurrentSha:
    """Tests for GitCLIBackend.current_sha()."""

    @pytest.mark.asyncio
    async def test_returns_sha(self, tmp_path: Path) -> None:
        """Should return a 40-character hex SHA."""
        backend = _init_repo(tmp_path)
        sha = await backend.current_sha()
        assert len(sha) == 40
        assert all(c in '0123456789abcdef' for c in sha)


class TestGitCLIBackendLog:
    """Tests for GitCLIBackend.log()."""

    @pytest.mark.asyncio
    async def test_log_returns_lines(self, tmp_path: Path) -> None:
        """Should return log lines for the repo."""
        backend = _init_repo(tmp_path)
        lines = await backend.log()
        assert len(lines) >= 1
        assert 'Initial commit' in lines[0]


class TestGitCLIBackendCommit:
    """Tests for GitCLIBackend.commit()."""

    @pytest.mark.asyncio
    async def test_commit_creates_commit(self, tmp_path: Path) -> None:
        """Should create a new commit."""
        backend = _init_repo(tmp_path)
        (tmp_path / 'new.txt').write_text('content')
        result = await backend.commit('test commit', paths=['new.txt'])
        assert result.ok

    @pytest.mark.asyncio
    async def test_commit_dry_run(self, tmp_path: Path) -> None:
        """dry_run should not create a commit."""
        backend = _init_repo(tmp_path)
        (tmp_path / 'new.txt').write_text('content')
        result = await backend.commit('test commit', dry_run=True)
        assert result.dry_run


class TestGitCLIBackendTag:
    """Tests for GitCLIBackend.tag()."""

    @pytest.mark.asyncio
    async def test_create_tag(self, tmp_path: Path) -> None:
        """Should create an annotated tag."""
        backend = _init_repo(tmp_path)
        result = await backend.tag('v1.0.0')
        assert result.ok
        assert await backend.tag_exists('v1.0.0')

    @pytest.mark.asyncio
    async def test_tag_exists_false(self, tmp_path: Path) -> None:
        """tag_exists should return False for non-existent tags."""
        backend = _init_repo(tmp_path)
        assert not await backend.tag_exists('v999.0.0')

    @pytest.mark.asyncio
    async def test_delete_tag(self, tmp_path: Path) -> None:
        """Should delete a tag."""
        backend = _init_repo(tmp_path)
        await backend.tag('v1.0.0')
        assert await backend.tag_exists('v1.0.0')
        result = await backend.delete_tag('v1.0.0')
        assert result.ok
        assert not await backend.tag_exists('v1.0.0')
