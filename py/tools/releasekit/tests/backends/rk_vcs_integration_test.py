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

"""Integration tests for GitCLIBackend against real git repos.

These tests create real git repositories (with a bare repo as "remote")
and exercise every command that GitCLIBackend constructs, verifying
argument order, flag correctness, and error propagation.

The tests do NOT touch the network — the "remote" is a local bare repo.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from releasekit.backends._run import run_command
from releasekit.backends.vcs.git import GitCLIBackend
from releasekit.logging import configure_logging

configure_logging(quiet=True)

pytestmark = pytest.mark.skipif(
    shutil.which('git') is None,
    reason='git not found on PATH. Install git: https://git-scm.com/',
)


def _init_repo_with_remote(tmp_path: Path) -> tuple[GitCLIBackend, Path, Path]:
    """Create a git repo with a bare remote and one commit.

    Returns (backend, work_dir, bare_dir).
    """
    bare = tmp_path / 'remote.git'
    bare.mkdir()
    run_command(['git', 'init', '--bare', '-b', 'main'], cwd=bare, check=True)

    work = tmp_path / 'work'
    work.mkdir()
    run_command(['git', 'init', '-b', 'main'], cwd=work, check=True)
    run_command(['git', 'config', 'user.email', 'test@example.com'], cwd=work, check=True)
    run_command(['git', 'config', 'user.name', 'Test User'], cwd=work, check=True)
    run_command(['git', 'remote', 'add', 'origin', str(bare)], cwd=work, check=True)

    (work / 'README.md').write_text('# Test\n')
    run_command(['git', 'add', '.'], cwd=work, check=True)
    run_command(['git', 'commit', '-m', 'Initial commit'], cwd=work, check=True)

    # Push main so the remote has a branch.
    run_command(['git', 'push', '-u', 'origin', 'main'], cwd=work, check=True)

    return GitCLIBackend(repo_root=work), work, bare


class TestPushBranchSetUpstream:
    """Test git push --set-upstream for new branches."""

    @pytest.mark.asyncio
    async def test_push_new_branch_set_upstream(self, tmp_path: Path) -> None:
        """push() on a new branch should use --set-upstream origin <branch>."""
        backend, work, _ = _init_repo_with_remote(tmp_path)

        # Create and switch to a new branch.
        await backend.checkout_branch('release/v1.0', create=True)
        (work / 'release.txt').write_text('release notes')
        await backend.commit('release commit', paths=['release.txt'])

        # Push with set_upstream=True (default).
        result = await backend.push()
        assert result.ok, f'push failed: {result.stderr}'

        # Verify the branch exists on the remote.
        ls = run_command(
            ['git', 'ls-remote', '--heads', 'origin', 'release/v1.0'],
            cwd=work,
        )
        assert 'release/v1.0' in ls.stdout

    @pytest.mark.asyncio
    async def test_push_set_upstream_false(self, tmp_path: Path) -> None:
        """push(set_upstream=False) should push without --set-upstream."""
        backend, work, _ = _init_repo_with_remote(tmp_path)

        # We're on main which already has upstream.
        (work / 'change.txt').write_text('change')
        await backend.commit('another commit', paths=['change.txt'])

        result = await backend.push(set_upstream=False)
        assert result.ok, f'push failed: {result.stderr}'


class TestPushTags:
    """Test git push --tags."""

    @pytest.mark.asyncio
    async def test_push_tags(self, tmp_path: Path) -> None:
        """push(tags=True) should push tags to the remote."""
        backend, work, _ = _init_repo_with_remote(tmp_path)

        await backend.tag('v1.0.0', message='Release v1.0.0')
        result = await backend.push(tags=True)
        assert result.ok, f'tag push failed: {result.stderr}'

        # Verify the tag exists on the remote.
        ls = run_command(
            ['git', 'ls-remote', '--tags', 'origin', 'v1.0.0'],
            cwd=work,
        )
        assert 'v1.0.0' in ls.stdout

    @pytest.mark.asyncio
    async def test_push_tags_does_not_use_set_upstream(self, tmp_path: Path) -> None:
        """push(tags=True) should NOT include --set-upstream."""
        backend, _work, _ = _init_repo_with_remote(tmp_path)

        await backend.tag('v2.0.0', message='Release v2.0.0')
        # This should succeed — --set-upstream is skipped for tag pushes.
        result = await backend.push(tags=True, set_upstream=True)
        assert result.ok, f'tag push failed: {result.stderr}'


class TestBranchOperations:
    """Test checkout_branch and current_branch."""

    @pytest.mark.asyncio
    async def test_checkout_create_branch(self, tmp_path: Path) -> None:
        """checkout_branch(create=True) should create and switch to a new branch."""
        backend, _, _ = _init_repo_with_remote(tmp_path)

        result = await backend.checkout_branch('feat/new', create=True)
        assert result.ok

        branch = await backend.current_branch()
        assert branch == 'feat/new'

    @pytest.mark.asyncio
    async def test_checkout_existing_branch(self, tmp_path: Path) -> None:
        """checkout_branch() should switch to an existing branch."""
        backend, _, _ = _init_repo_with_remote(tmp_path)

        await backend.checkout_branch('feat/x', create=True)
        await backend.checkout_branch('main')
        branch = await backend.current_branch()
        assert branch == 'main'

    @pytest.mark.asyncio
    async def test_current_branch_on_main(self, tmp_path: Path) -> None:
        """current_branch() should return 'main' on the default branch."""
        backend, _, _ = _init_repo_with_remote(tmp_path)
        branch = await backend.current_branch()
        assert branch == 'main'


class TestTagOperations:
    """Test tag, tag_exists, delete_tag, list_tags."""

    @pytest.mark.asyncio
    async def test_create_and_list_tags(self, tmp_path: Path) -> None:
        """tag() + list_tags() should create and list tags."""
        backend, _, _ = _init_repo_with_remote(tmp_path)

        await backend.tag('v1.0.0')
        await backend.tag('v1.1.0')
        await backend.tag('v2.0.0')

        tags = await backend.list_tags()
        assert 'v1.0.0' in tags
        assert 'v1.1.0' in tags
        assert 'v2.0.0' in tags

    @pytest.mark.asyncio
    async def test_list_tags_with_pattern(self, tmp_path: Path) -> None:
        """list_tags(pattern=...) should filter tags."""
        backend, _, _ = _init_repo_with_remote(tmp_path)

        await backend.tag('v1.0.0')
        await backend.tag('v2.0.0')
        await backend.tag('pkg-v1.0.0')

        tags = await backend.list_tags(pattern='v*')
        assert 'v1.0.0' in tags
        assert 'v2.0.0' in tags
        assert 'pkg-v1.0.0' not in tags

    @pytest.mark.asyncio
    async def test_delete_tag_local(self, tmp_path: Path) -> None:
        """delete_tag() should remove a local tag."""
        backend, _, _ = _init_repo_with_remote(tmp_path)

        await backend.tag('v1.0.0')
        assert await backend.tag_exists('v1.0.0')

        result = await backend.delete_tag('v1.0.0')
        assert result.ok
        assert not await backend.tag_exists('v1.0.0')

    @pytest.mark.asyncio
    async def test_delete_tag_remote(self, tmp_path: Path) -> None:
        """delete_tag(remote=True) should remove from both local and remote."""
        backend, work, _ = _init_repo_with_remote(tmp_path)

        await backend.tag('v1.0.0')
        await backend.push(tags=True)

        # Verify tag is on remote.
        ls = run_command(['git', 'ls-remote', '--tags', 'origin', 'v1.0.0'], cwd=work)
        assert 'v1.0.0' in ls.stdout

        # Delete locally and remotely.
        result = await backend.delete_tag('v1.0.0', remote=True)
        assert result.ok

        # Verify tag is gone from remote.
        ls = run_command(['git', 'ls-remote', '--tags', 'origin', 'v1.0.0'], cwd=work)
        assert 'v1.0.0' not in ls.stdout


class TestLogAndDiff:
    """Test log() and diff_files() with since_tag."""

    @pytest.mark.asyncio
    async def test_log_since_tag(self, tmp_path: Path) -> None:
        """log(since_tag=...) should only return commits after the tag."""
        backend, work, _ = _init_repo_with_remote(tmp_path)

        await backend.tag('v1.0.0')

        (work / 'file1.txt').write_text('one')
        await backend.commit('feat: add file1', paths=['file1.txt'])
        (work / 'file2.txt').write_text('two')
        await backend.commit('feat: add file2', paths=['file2.txt'])

        lines = await backend.log(since_tag='v1.0.0')
        assert len(lines) == 2
        assert any('file1' in line for line in lines)
        assert any('file2' in line for line in lines)

    @pytest.mark.asyncio
    async def test_log_with_paths(self, tmp_path: Path) -> None:
        """log(paths=...) should filter to commits touching those paths."""
        backend, work, _ = _init_repo_with_remote(tmp_path)

        (work / 'a.txt').write_text('a')
        await backend.commit('add a', paths=['a.txt'])
        (work / 'b.txt').write_text('b')
        await backend.commit('add b', paths=['b.txt'])

        lines = await backend.log(paths=['a.txt'])
        assert len(lines) == 1
        assert 'add a' in lines[0]

    @pytest.mark.asyncio
    async def test_log_max_commits(self, tmp_path: Path) -> None:
        """log(max_commits=N) should limit output."""
        backend, work, _ = _init_repo_with_remote(tmp_path)

        for i in range(5):
            (work / f'f{i}.txt').write_text(str(i))
            await backend.commit(f'commit {i}', paths=[f'f{i}.txt'])

        lines = await backend.log(max_commits=2)
        assert len(lines) == 2

    @pytest.mark.asyncio
    async def test_diff_files_since_tag(self, tmp_path: Path) -> None:
        """diff_files(since_tag=...) should return changed files."""
        backend, work, _ = _init_repo_with_remote(tmp_path)

        await backend.tag('v1.0.0')

        (work / 'new.txt').write_text('new')
        await backend.commit('add new', paths=['new.txt'])

        files = await backend.diff_files(since_tag='v1.0.0')
        assert 'new.txt' in files


class TestCommitEdgeCases:
    """Test commit() with various path/dry_run combinations."""

    @pytest.mark.asyncio
    async def test_commit_with_paths(self, tmp_path: Path) -> None:
        """commit(paths=[...]) should only stage specified files."""
        backend, work, _ = _init_repo_with_remote(tmp_path)

        (work / 'staged.txt').write_text('staged')
        (work / 'unstaged.txt').write_text('unstaged')

        result = await backend.commit('partial commit', paths=['staged.txt'])
        assert result.ok

        # unstaged.txt should still be untracked.
        assert not await backend.is_clean()

    @pytest.mark.asyncio
    async def test_commit_without_paths_stages_all(self, tmp_path: Path) -> None:
        """commit(paths=None) should stage everything via git add -A."""
        backend, work, _ = _init_repo_with_remote(tmp_path)

        (work / 'a.txt').write_text('a')
        (work / 'b.txt').write_text('b')

        result = await backend.commit('stage all')
        assert result.ok
        assert await backend.is_clean()

    @pytest.mark.asyncio
    async def test_commit_dry_run_does_not_stage(self, tmp_path: Path) -> None:
        """commit(dry_run=True) should not stage or commit anything."""
        backend, work, _ = _init_repo_with_remote(tmp_path)

        (work / 'dirty.txt').write_text('dirty')

        result = await backend.commit('dry run commit', dry_run=True)
        assert result.dry_run

        # File should still be untracked.
        assert not await backend.is_clean()


class TestRepoMetadata:
    """Test is_shallow() and default_branch()."""

    @pytest.mark.asyncio
    async def test_not_shallow(self, tmp_path: Path) -> None:
        """A locally-created repo should not be shallow."""
        backend, _, _ = _init_repo_with_remote(tmp_path)
        assert not await backend.is_shallow()

    @pytest.mark.asyncio
    async def test_default_branch(self, tmp_path: Path) -> None:
        """default_branch() should detect 'main'."""
        backend, _, _ = _init_repo_with_remote(tmp_path)
        branch = await backend.default_branch()
        assert branch == 'main'
