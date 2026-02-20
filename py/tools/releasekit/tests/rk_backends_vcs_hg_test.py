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

"""Tests for the Mercurial VCS backend.

Mocks run_command to avoid real hg calls.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from releasekit.backends._run import CommandResult
from releasekit.backends.vcs.mercurial import MercurialCLIBackend


def _ok(stdout: str = '', **kw: Any) -> CommandResult:  # noqa: ANN401
    """Ok."""
    return CommandResult(command=['hg'], return_code=0, stdout=stdout, **kw)


def _fail(stderr: str = '', **kw: Any) -> CommandResult:  # noqa: ANN401
    """Fail."""
    return CommandResult(command=['hg'], return_code=1, stderr=stderr, **kw)


@pytest.fixture()
def hg() -> MercurialCLIBackend:
    """Hg."""
    return MercurialCLIBackend(repo_root=Path('/fake/repo'))


class TestIsClean:
    """Tests for Is Clean."""

    @pytest.mark.asyncio()
    async def test_clean(self, hg: MercurialCLIBackend) -> None:
        """Test clean."""
        with patch.object(hg, '_hg', return_value=_ok(stdout='')):
            assert await hg.is_clean() is True

    @pytest.mark.asyncio()
    async def test_dirty(self, hg: MercurialCLIBackend) -> None:
        """Test dirty."""
        with patch.object(hg, '_hg', return_value=_ok(stdout='M foo.py\n')):
            assert await hg.is_clean() is False

    @pytest.mark.asyncio()
    async def test_dry_run(self, hg: MercurialCLIBackend) -> None:
        """Test dry run."""
        assert await hg.is_clean(dry_run=True) is True


class TestIsShallow:
    """Tests for Is Shallow."""

    @pytest.mark.asyncio()
    async def test_always_false(self, hg: MercurialCLIBackend) -> None:
        """Test always false."""
        assert await hg.is_shallow() is False


class TestDefaultBranch:
    """Tests for Default Branch."""

    @pytest.mark.asyncio()
    async def test_always_default(self, hg: MercurialCLIBackend) -> None:
        """Test always default."""
        assert await hg.default_branch() == 'default'


class TestCurrentSha:
    """Tests for Current Sha."""

    @pytest.mark.asyncio()
    async def test_returns_hash(self, hg: MercurialCLIBackend) -> None:
        """Test returns hash."""
        with patch.object(hg, '_hg', return_value=_ok(stdout='abc123def456\n')):
            assert await hg.current_sha() == 'abc123def456'


class TestLog:
    """Tests for Log."""

    @pytest.mark.asyncio()
    async def test_basic(self, hg: MercurialCLIBackend) -> None:
        """Test basic."""
        with patch.object(hg, '_hg', return_value=_ok(stdout='abc feat: x\ndef fix: y\n')) as m:
            lines = await hg.log()
            assert lines == ['abc feat: x', 'def fix: y']
            args = m.call_args[0]
            assert 'log' in args

    @pytest.mark.asyncio()
    async def test_since_tag(self, hg: MercurialCLIBackend) -> None:
        """Test since tag."""
        with patch.object(hg, '_hg', return_value=_ok(stdout='abc feat: x\n')) as m:
            await hg.log(since_tag='v1.0.0')
            args = m.call_args[0]
            assert any('tag("v1.0.0")' in a for a in args)

    @pytest.mark.asyncio()
    async def test_paths(self, hg: MercurialCLIBackend) -> None:
        """Test paths."""
        with patch.object(hg, '_hg', return_value=_ok(stdout='abc feat: x\n')) as m:
            await hg.log(paths=['src/'])
            args = m.call_args[0]
            assert '--' in args
            assert 'src/' in args

    @pytest.mark.asyncio()
    async def test_first_parent_no_merges(self, hg: MercurialCLIBackend) -> None:
        """Test first parent no merges."""
        with patch.object(hg, '_hg', return_value=_ok(stdout='abc feat: x\n')) as m:
            await hg.log(first_parent=True, no_merges=True)
            args = m.call_args[0]
            assert '--follow-first' in args
            assert '--no-merges' in args

    @pytest.mark.asyncio()
    async def test_empty(self, hg: MercurialCLIBackend) -> None:
        """Test empty."""
        with patch.object(hg, '_hg', return_value=_ok(stdout='')):
            assert await hg.log() == []

    @pytest.mark.asyncio()
    async def test_format_translation(self, hg: MercurialCLIBackend) -> None:
        """Test format translation."""
        with patch.object(hg, '_hg', return_value=_ok(stdout='abc feat\n')) as m:
            await hg.log(format='%H %s')
            args = m.call_args[0]
            template_idx = list(args).index('--template') + 1
            template = args[template_idx]
            assert '{node}' in template
            assert '{desc|firstline}' in template


class TestDiffFiles:
    """Tests for Diff Files."""

    @pytest.mark.asyncio()
    async def test_since_tag(self, hg: MercurialCLIBackend) -> None:
        """Test since tag."""
        with patch.object(hg, '_hg', return_value=_ok(stdout='a.py\nb.py\n')):
            files = await hg.diff_files(since_tag='v1.0.0')
            assert files == ['a.py', 'b.py']

    @pytest.mark.asyncio()
    async def test_no_tag(self, hg: MercurialCLIBackend) -> None:
        """Test no tag."""
        with patch.object(hg, '_hg', return_value=_ok(stdout='c.py\n')):
            files = await hg.diff_files()
            assert files == ['c.py']

    @pytest.mark.asyncio()
    async def test_empty(self, hg: MercurialCLIBackend) -> None:
        """Test empty."""
        with patch.object(hg, '_hg', return_value=_ok(stdout='')):
            assert await hg.diff_files(since_tag='v1.0.0') == []


class TestCommit:
    """Tests for Commit."""

    @pytest.mark.asyncio()
    async def test_with_paths(self, hg: MercurialCLIBackend) -> None:
        """Test with paths."""
        with patch.object(hg, '_hg', return_value=_ok()) as m:
            await hg.commit('feat: x', paths=['a.py'])
            calls = [c[0] for c in m.call_args_list]
            assert ('add', 'a.py') == calls[0]

    @pytest.mark.asyncio()
    async def test_without_paths(self, hg: MercurialCLIBackend) -> None:
        """Test without paths."""
        with patch.object(hg, '_hg', return_value=_ok()) as m:
            await hg.commit('feat: x')
            calls = [c[0] for c in m.call_args_list]
            assert calls[0] == ('add',)

    @pytest.mark.asyncio()
    async def test_dry_run(self, hg: MercurialCLIBackend) -> None:
        """Test dry run."""
        with patch.object(hg, '_hg', return_value=_ok()) as m:
            await hg.commit('feat: x', dry_run=True)
            # dry_run skips add, only commits
            for call in m.call_args_list:
                assert call[1].get('dry_run') is True


class TestTag:
    """Tests for Tag."""

    @pytest.mark.asyncio()
    async def test_create(self, hg: MercurialCLIBackend) -> None:
        """Test create."""
        with patch.object(hg, '_hg', return_value=_ok()) as m:
            await hg.tag('v1.0.0', message='Release v1.0.0')
            args = m.call_args[0]
            assert 'tag' in args
            assert 'v1.0.0' in args

    @pytest.mark.asyncio()
    async def test_default_message(self, hg: MercurialCLIBackend) -> None:
        """Test default message."""
        with patch.object(hg, '_hg', return_value=_ok()) as m:
            await hg.tag('v1.0.0')
            args = m.call_args[0]
            assert 'v1.0.0' in args


class TestTagExists:
    """Tests for Tag Exists."""

    @pytest.mark.asyncio()
    async def test_exists(self, hg: MercurialCLIBackend) -> None:
        """Test exists."""
        with patch.object(hg, '_hg', return_value=_ok(stdout='tip\nv1.0.0\n')):
            assert await hg.tag_exists('v1.0.0') is True

    @pytest.mark.asyncio()
    async def test_not_exists(self, hg: MercurialCLIBackend) -> None:
        """Test not exists."""
        with patch.object(hg, '_hg', return_value=_ok(stdout='tip\n')):
            assert await hg.tag_exists('v1.0.0') is False


class TestDeleteTag:
    """Tests for Delete Tag."""

    @pytest.mark.asyncio()
    async def test_local_only(self, hg: MercurialCLIBackend) -> None:
        """Test local only."""
        with patch.object(hg, '_hg', return_value=_ok()) as m:
            await hg.delete_tag('v1.0.0')
            assert m.call_count == 1

    @pytest.mark.asyncio()
    async def test_with_remote(self, hg: MercurialCLIBackend) -> None:
        """Test with remote."""
        with patch.object(hg, '_hg', return_value=_ok()) as m:
            await hg.delete_tag('v1.0.0', remote=True)
            assert m.call_count == 2
            assert 'push' in m.call_args_list[1][0]


class TestPush:
    """Tests for Push."""

    @pytest.mark.asyncio()
    async def test_default_remote(self, hg: MercurialCLIBackend) -> None:
        """Test default remote."""
        with patch.object(hg, '_hg', return_value=_ok()) as m:
            await hg.push()
            args = m.call_args[0]
            assert 'push' in args
            assert 'default' in args

    @pytest.mark.asyncio()
    async def test_custom_remote(self, hg: MercurialCLIBackend) -> None:
        """Test custom remote."""
        with patch.object(hg, '_hg', return_value=_ok()) as m:
            await hg.push(remote='upstream')
            assert 'upstream' in m.call_args[0]


class TestCheckoutBranch:
    """Tests for Checkout Branch."""

    @pytest.mark.asyncio()
    async def test_switch(self, hg: MercurialCLIBackend) -> None:
        """Test switch."""
        with patch.object(hg, '_hg', return_value=_ok()) as m:
            await hg.checkout_branch('stable')
            args = m.call_args[0]
            assert 'update' in args
            assert 'stable' in args

    @pytest.mark.asyncio()
    async def test_create(self, hg: MercurialCLIBackend) -> None:
        """Test create."""
        with patch.object(hg, '_hg', return_value=_ok()) as m:
            await hg.checkout_branch('release/1.0', create=True)
            args = m.call_args[0]
            assert 'bookmark' in args
            assert 'release/1.0' in args
