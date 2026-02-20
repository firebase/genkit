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

"""Tests for the Git VCS backend.

Mocks run_command to avoid real git calls.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from releasekit.backends._run import CommandResult
from releasekit.backends.vcs.git import GitCLIBackend


def _ok(stdout: str = '', **kw: Any) -> CommandResult:  # noqa: ANN401
    """Ok."""
    return CommandResult(command=['git'], return_code=0, stdout=stdout, **kw)


def _fail(stderr: str = '', **kw: Any) -> CommandResult:  # noqa: ANN401
    """Fail."""
    return CommandResult(command=['git'], return_code=1, stderr=stderr, **kw)


@pytest.fixture()
def git() -> GitCLIBackend:
    """Git."""
    return GitCLIBackend(repo_root=Path('/fake/repo'))


class TestIsClean:
    """Tests for Is Clean."""

    @pytest.mark.asyncio()
    async def test_clean(self, git: GitCLIBackend) -> None:
        """Test clean."""
        with patch.object(git, '_git', return_value=_ok(stdout='')) as m:
            assert await git.is_clean() is True
            m.assert_called_once_with('status', '--porcelain')

    @pytest.mark.asyncio()
    async def test_dirty(self, git: GitCLIBackend) -> None:
        """Test dirty."""
        with patch.object(git, '_git', return_value=_ok(stdout=' M foo.py\n')):
            assert await git.is_clean() is False

    @pytest.mark.asyncio()
    async def test_dry_run(self, git: GitCLIBackend) -> None:
        """Test dry run."""
        assert await git.is_clean(dry_run=True) is True


class TestIsShallow:
    """Tests for Is Shallow."""

    @pytest.mark.asyncio()
    async def test_shallow(self, git: GitCLIBackend) -> None:
        """Test shallow."""
        with patch.object(git, '_git', return_value=_ok(stdout='true\n')):
            assert await git.is_shallow() is True

    @pytest.mark.asyncio()
    async def test_not_shallow(self, git: GitCLIBackend) -> None:
        """Test not shallow."""
        with patch.object(git, '_git', return_value=_ok(stdout='false\n')):
            assert await git.is_shallow() is False


class TestDefaultBranch:
    """Tests for Default Branch."""

    @pytest.mark.asyncio()
    async def test_symbolic_ref(self, git: GitCLIBackend) -> None:
        """Test symbolic ref."""
        with patch.object(git, '_git', return_value=_ok(stdout='origin/main\n')):
            assert await git.default_branch() == 'main'

    @pytest.mark.asyncio()
    async def test_symbolic_ref_no_prefix(self, git: GitCLIBackend) -> None:
        """Test symbolic ref no prefix."""
        with patch.object(git, '_git', return_value=_ok(stdout='develop\n')):
            assert await git.default_branch() == 'develop'

    @pytest.mark.asyncio()
    async def test_probe_master(self, git: GitCLIBackend) -> None:
        """Test probe master."""

        def side_effect(*args: object, **kw: object) -> object:
            """Side effect."""
            if 'symbolic-ref' in args:
                return _fail()
            if 'refs/heads/main' in args:
                return _fail()
            if 'refs/heads/master' in args:
                return _ok()
            return _fail()

        with patch.object(git, '_git', side_effect=side_effect):
            assert await git.default_branch() == 'master'

    @pytest.mark.asyncio()
    async def test_fallback_main(self, git: GitCLIBackend) -> None:
        """Test fallback main."""
        with patch.object(git, '_git', return_value=_fail()):
            assert await git.default_branch() == 'main'


class TestCurrentSha:
    """Tests for Current Sha."""

    @pytest.mark.asyncio()
    async def test_returns_sha(self, git: GitCLIBackend) -> None:
        """Test returns sha."""
        with patch.object(git, '_git', return_value=_ok(stdout='abc123def\n')):
            assert await git.current_sha() == 'abc123def'


class TestLog:
    """Tests for Log."""

    @pytest.mark.asyncio()
    async def test_basic(self, git: GitCLIBackend) -> None:
        """Test basic."""
        with patch.object(git, '_git', return_value=_ok(stdout='abc feat: x\ndef fix: y\n')) as m:
            lines = await git.log()
            assert lines == ['abc feat: x', 'def fix: y']
            args = m.call_args[0]
            assert 'log' in args
            assert '--pretty=format:%H %s' in args

    @pytest.mark.asyncio()
    async def test_since_tag(self, git: GitCLIBackend) -> None:
        """Test since tag."""
        with patch.object(git, '_git', return_value=_ok(stdout='abc feat: x\n')) as m:
            await git.log(since_tag='v1.0.0')
            args = m.call_args[0]
            assert 'v1.0.0..HEAD' in args

    @pytest.mark.asyncio()
    async def test_paths(self, git: GitCLIBackend) -> None:
        """Test paths."""
        with patch.object(git, '_git', return_value=_ok(stdout='abc feat: x\n')) as m:
            await git.log(paths=['src/'])
            args = m.call_args[0]
            assert '--' in args
            assert 'src/' in args

    @pytest.mark.asyncio()
    async def test_first_parent_no_merges(self, git: GitCLIBackend) -> None:
        """Test first parent no merges."""
        with patch.object(git, '_git', return_value=_ok(stdout='abc feat: x\n')) as m:
            await git.log(first_parent=True, no_merges=True)
            args = m.call_args[0]
            assert '--first-parent' in args
            assert '--no-merges' in args

    @pytest.mark.asyncio()
    async def test_empty(self, git: GitCLIBackend) -> None:
        """Test empty."""
        with patch.object(git, '_git', return_value=_ok(stdout='')):
            assert await git.log() == []

    @pytest.mark.asyncio()
    async def test_changelog_format_no_literal_null_bytes(self, git: GitCLIBackend) -> None:
        r"""Regression: changelog format %x00 must not put literal null bytes in argv.

        A literal \\x00 in the --pretty=format: argument causes
        ``ValueError: embedded null byte`` in subprocess.Popen on Linux
        because execve(2) rejects null bytes in command arguments.
        Git interprets ``%x00`` in the format and outputs actual null
        bytes, so the command arg itself stays clean.
        """
        changelog_fmt = '%H%x00%an%x00%s'
        with patch.object(git, '_git', return_value=_ok(stdout='')) as m:
            await git.log(format=changelog_fmt)
            args = m.call_args[0]
            pretty_arg = [a for a in args if a.startswith('--pretty=format:')]
            assert len(pretty_arg) == 1
            # The argument string must not contain a literal null byte.
            assert '\x00' not in pretty_arg[0], f'Literal null byte found in git arg: {pretty_arg[0]!r}'
            # It should contain the %x00 escape for git to interpret.
            assert '%x00' in pretty_arg[0]

    @pytest.mark.asyncio()
    async def test_max_commits(self, git: GitCLIBackend) -> None:
        """max_commits passes -n flag."""
        with patch.object(git, '_git', return_value=_ok(stdout='abc feat: x\n')) as m:
            await git.log(max_commits=50)
            args = m.call_args[0]
            assert '-n50' in args


class TestDiffFiles:
    """Tests for Diff Files."""

    @pytest.mark.asyncio()
    async def test_since_tag(self, git: GitCLIBackend) -> None:
        """Test since tag."""
        with patch.object(git, '_git', return_value=_ok(stdout='a.py\nb.py\n')):
            files = await git.diff_files(since_tag='v1.0.0')
            assert files == ['a.py', 'b.py']

    @pytest.mark.asyncio()
    async def test_no_tag_with_describe(self, git: GitCLIBackend) -> None:
        """Test no tag with describe."""
        call_count = 0

        def side_effect(*args: object, **kw: object) -> object:
            """Side effect."""
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _ok(stdout='v0.9.0\n')
            return _ok(stdout='c.py\n')

        with patch.object(git, '_git', side_effect=side_effect):
            files = await git.diff_files()
            assert files == ['c.py']

    @pytest.mark.asyncio()
    async def test_no_tag_no_describe(self, git: GitCLIBackend) -> None:
        """Test no tag no describe."""
        with patch.object(git, '_git', return_value=_fail()):
            assert await git.diff_files() == []

    @pytest.mark.asyncio()
    async def test_empty(self, git: GitCLIBackend) -> None:
        """Test empty."""
        with patch.object(git, '_git', return_value=_ok(stdout='')):
            assert await git.diff_files(since_tag='v1.0.0') == []


class TestCommit:
    """Tests for Commit."""

    @pytest.mark.asyncio()
    async def test_with_paths(self, git: GitCLIBackend) -> None:
        """Test with paths."""
        with patch.object(git, '_git', return_value=_ok()) as m:
            await git.commit('feat: x', paths=['a.py'])
            calls = [c[0] for c in m.call_args_list]
            assert ('add', 'a.py') == calls[0]

    @pytest.mark.asyncio()
    async def test_without_paths(self, git: GitCLIBackend) -> None:
        """Test without paths."""
        with patch.object(git, '_git', return_value=_ok()) as m:
            await git.commit('feat: x')
            calls = [c[0] for c in m.call_args_list]
            assert calls[0][0] == 'add'
            assert '-A' in calls[0]

    @pytest.mark.asyncio()
    async def test_no_verify_flag(self, git: GitCLIBackend) -> None:
        """Regression: commit must pass --no-verify to skip pre-commit hooks."""
        with patch.object(git, '_git', return_value=_ok()) as m:
            await git.commit('chore(release): v1.0.0')
            commit_call = m.call_args_list[-1][0]
            assert '--no-verify' in commit_call

    @pytest.mark.asyncio()
    async def test_dry_run(self, git: GitCLIBackend) -> None:
        """Test dry run."""
        with patch.object(git, '_git', return_value=_ok()) as m:
            await git.commit('feat: x', dry_run=True)
            for call in m.call_args_list:
                assert call[1].get('dry_run') is True


class TestTag:
    """Tests for Tag."""

    @pytest.mark.asyncio()
    async def test_create(self, git: GitCLIBackend) -> None:
        """Test create."""
        with patch.object(git, '_git', return_value=_ok()) as m:
            await git.tag('v1.0.0', message='Release v1.0.0')
            args = m.call_args[0]
            assert 'tag' in args
            assert '-a' in args
            assert 'v1.0.0' in args
            assert 'Release v1.0.0' in args

    @pytest.mark.asyncio()
    async def test_default_message(self, git: GitCLIBackend) -> None:
        """Test default message."""
        with patch.object(git, '_git', return_value=_ok()) as m:
            await git.tag('v1.0.0')
            args = m.call_args[0]
            # Message defaults to tag name.
            assert args[-1] == 'v1.0.0'


class TestTagExists:
    """Tests for Tag Exists."""

    @pytest.mark.asyncio()
    async def test_exists(self, git: GitCLIBackend) -> None:
        """Test exists."""
        with patch.object(git, '_git', return_value=_ok(stdout='v1.0.0\n')):
            assert await git.tag_exists('v1.0.0') is True

    @pytest.mark.asyncio()
    async def test_not_exists(self, git: GitCLIBackend) -> None:
        """Test not exists."""
        with patch.object(git, '_git', return_value=_ok(stdout='')):
            assert await git.tag_exists('v1.0.0') is False


class TestDeleteTag:
    """Tests for Delete Tag."""

    @pytest.mark.asyncio()
    async def test_local_only(self, git: GitCLIBackend) -> None:
        """Test local only."""
        with patch.object(git, '_git', return_value=_ok()) as m:
            await git.delete_tag('v1.0.0')
            assert m.call_count == 1

    @pytest.mark.asyncio()
    async def test_with_remote(self, git: GitCLIBackend) -> None:
        """Test with remote."""
        with patch.object(git, '_git', return_value=_ok()) as m:
            await git.delete_tag('v1.0.0', remote=True)
            assert m.call_count == 2
            remote_call = m.call_args_list[1][0]
            assert 'push' in remote_call
            assert ':refs/tags/v1.0.0' in remote_call


class TestPush:
    """Tests for Push."""

    @pytest.mark.asyncio()
    async def test_basic(self, git: GitCLIBackend) -> None:
        """Test basic."""
        with patch.object(git, '_git', return_value=_ok()) as m:
            await git.push()
            args = m.call_args[0]
            assert 'push' in args
            assert '--no-verify' in args
            assert 'origin' in args

    @pytest.mark.asyncio()
    async def test_with_tags(self, git: GitCLIBackend) -> None:
        """Test with tags."""
        with patch.object(git, '_git', return_value=_ok()) as m:
            await git.push(tags=True)
            assert '--tags' in m.call_args[0]

    @pytest.mark.asyncio()
    async def test_custom_remote(self, git: GitCLIBackend) -> None:
        """Test custom remote."""
        with patch.object(git, '_git', return_value=_ok()) as m:
            await git.push(remote='upstream')
            assert 'upstream' in m.call_args[0]


class TestCheckoutBranch:
    """Tests for Checkout Branch."""

    @pytest.mark.asyncio()
    async def test_switch(self, git: GitCLIBackend) -> None:
        """Test switch."""
        with patch.object(git, '_git', return_value=_ok()) as m:
            await git.checkout_branch('develop')
            args = m.call_args[0]
            assert 'checkout' in args
            assert 'develop' in args
            assert '-b' not in args

    @pytest.mark.asyncio()
    async def test_create(self, git: GitCLIBackend) -> None:
        """Test create."""
        with patch.object(git, '_git', return_value=_ok()) as m:
            await git.checkout_branch('release/1.0', create=True)
            args = m.call_args[0]
            assert '-B' in args
            assert 'release/1.0' in args
