# Copyright 2025 Google LLC
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

from releasekit.backends._run import run_command
from releasekit.backends.vcs import VCS, GitBackend
from releasekit.logging import configure_logging

configure_logging(quiet=True)


def _init_repo(path: Path) -> GitBackend:
    """Create a git repo with one commit and return a GitBackend."""
    run_command(['git', 'init'], cwd=path, check=True)
    run_command(['git', 'config', 'user.email', 'test@example.com'], cwd=path, check=True)
    run_command(['git', 'config', 'user.name', 'Test User'], cwd=path, check=True)
    (path / 'README.md').write_text('# Test\n')
    run_command(['git', 'add', '.'], cwd=path, check=True)
    run_command(['git', 'commit', '-m', 'Initial commit'], cwd=path, check=True)
    return GitBackend(repo_root=path)


class TestGitBackendProtocol:
    """Verify GitBackend implements the VCS protocol."""

    def test_implements_vcs(self, tmp_path: Path) -> None:
        """GitBackend should be a runtime-checkable VCS."""
        backend = GitBackend(repo_root=tmp_path)
        assert isinstance(backend, VCS)


class TestGitBackendIsClean:
    """Tests for GitBackend.is_clean()."""

    def test_clean_repo(self, tmp_path: Path) -> None:
        """Should return True for a clean repo."""
        backend = _init_repo(tmp_path)
        assert backend.is_clean()

    def test_dirty_repo(self, tmp_path: Path) -> None:
        """Should return False when there are uncommitted changes."""
        backend = _init_repo(tmp_path)
        (tmp_path / 'new_file.txt').write_text('dirty')
        assert not backend.is_clean()

    def test_dry_run_returns_true(self, tmp_path: Path) -> None:
        """dry_run should always return True."""
        backend = _init_repo(tmp_path)
        (tmp_path / 'dirty.txt').write_text('dirty')
        assert backend.is_clean(dry_run=True)


class TestGitBackendIsShallow:
    """Tests for GitBackend.is_shallow()."""

    def test_not_shallow(self, tmp_path: Path) -> None:
        """A regular repo should not be shallow."""
        backend = _init_repo(tmp_path)
        assert not backend.is_shallow()


class TestGitBackendCurrentSha:
    """Tests for GitBackend.current_sha()."""

    def test_returns_sha(self, tmp_path: Path) -> None:
        """Should return a 40-character hex SHA."""
        backend = _init_repo(tmp_path)
        sha = backend.current_sha()
        assert len(sha) == 40
        assert all(c in '0123456789abcdef' for c in sha)


class TestGitBackendLog:
    """Tests for GitBackend.log()."""

    def test_log_returns_lines(self, tmp_path: Path) -> None:
        """Should return log lines for the repo."""
        backend = _init_repo(tmp_path)
        lines = backend.log()
        assert len(lines) >= 1
        assert 'Initial commit' in lines[0]


class TestGitBackendCommit:
    """Tests for GitBackend.commit()."""

    def test_commit_creates_commit(self, tmp_path: Path) -> None:
        """Should create a new commit."""
        backend = _init_repo(tmp_path)
        (tmp_path / 'new.txt').write_text('content')
        result = backend.commit('test commit', paths=['new.txt'])
        assert result.ok

    def test_commit_dry_run(self, tmp_path: Path) -> None:
        """dry_run should not create a commit."""
        backend = _init_repo(tmp_path)
        (tmp_path / 'new.txt').write_text('content')
        result = backend.commit('test commit', dry_run=True)
        assert result.dry_run


class TestGitBackendTag:
    """Tests for GitBackend.tag()."""

    def test_create_tag(self, tmp_path: Path) -> None:
        """Should create an annotated tag."""
        backend = _init_repo(tmp_path)
        result = backend.tag('v1.0.0')
        assert result.ok
        assert backend.tag_exists('v1.0.0')

    def test_tag_exists_false(self, tmp_path: Path) -> None:
        """tag_exists should return False for non-existent tags."""
        backend = _init_repo(tmp_path)
        assert not backend.tag_exists('v999.0.0')

    def test_delete_tag(self, tmp_path: Path) -> None:
        """Should delete a tag."""
        backend = _init_repo(tmp_path)
        backend.tag('v1.0.0')
        assert backend.tag_exists('v1.0.0')
        result = backend.delete_tag('v1.0.0')
        assert result.ok
        assert not backend.tag_exists('v1.0.0')
