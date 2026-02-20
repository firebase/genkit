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

"""Tests for the GitLab CLI forge backend."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from releasekit.backends._run import CommandResult
from releasekit.backends.forge.gitlab import GitLabCLIBackend


def _ok(stdout: str = '', **kw: Any) -> CommandResult:  # noqa: ANN401
    """Ok."""
    return CommandResult(command=['glab'], return_code=0, stdout=stdout, **kw)


def _fail(stderr: str = '', **kw: Any) -> CommandResult:  # noqa: ANN401
    """Fail."""
    return CommandResult(command=['glab'], return_code=1, stderr=stderr, **kw)


@pytest.fixture()
def gl() -> GitLabCLIBackend:
    """Gl."""
    return GitLabCLIBackend(project='firebase/genkit', cwd=Path('/fake'))


class TestIsAvailable:
    """Tests for Is Available."""

    @pytest.mark.asyncio()
    async def test_available(self, gl: GitLabCLIBackend) -> None:
        """Test available."""
        with (
            patch('shutil.which', return_value='/usr/bin/glab'),
            patch('releasekit.backends.forge.gitlab.run_command', return_value=_ok()),
        ):
            assert await gl.is_available() is True

    @pytest.mark.asyncio()
    async def test_not_installed(self, gl: GitLabCLIBackend) -> None:
        """Test not installed."""
        with patch('shutil.which', return_value=None):
            assert await gl.is_available() is False

    @pytest.mark.asyncio()
    async def test_not_authenticated(self, gl: GitLabCLIBackend) -> None:
        """Test not authenticated."""
        with (
            patch('shutil.which', return_value='/usr/bin/glab'),
            patch('releasekit.backends.forge.gitlab.run_command', return_value=_fail()),
        ):
            assert await gl.is_available() is False


class TestCreateRelease:
    """Tests for Create Release."""

    @pytest.mark.asyncio()
    async def test_basic(self, gl: GitLabCLIBackend) -> None:
        """Test basic."""
        with patch.object(gl, '_glab', return_value=_ok()) as m:
            await gl.create_release('v1.0.0', title='Release', body='notes')
            args = m.call_args[0]
            assert 'release' in args
            assert 'create' in args
            assert '--name' in args
            assert '--notes' in args

    @pytest.mark.asyncio()
    async def test_draft_warning(self, gl: GitLabCLIBackend) -> None:
        """Test draft warning."""
        with patch.object(gl, '_glab', return_value=_ok()):
            # Should not raise — just logs a warning.
            await gl.create_release('v1.0.0', draft=True)

    @pytest.mark.asyncio()
    async def test_assets(self, gl: GitLabCLIBackend) -> None:
        """Test assets."""
        with patch.object(gl, '_glab', return_value=_ok()) as m:
            await gl.create_release('v1.0.0', assets=[Path('/fake/assets/a.tar.gz')])
            args = m.call_args[0]
            assert any('--assets-links' in a for a in args)


class TestDeleteRelease:
    """Tests for Delete Release."""

    @pytest.mark.asyncio()
    async def test_delete(self, gl: GitLabCLIBackend) -> None:
        """Test delete."""
        with patch.object(gl, '_glab', return_value=_ok()) as m:
            await gl.delete_release('v1.0.0')
            args = m.call_args[0]
            assert 'release' in args
            assert 'delete' in args
            assert '--yes' in args


class TestPromoteRelease:
    """Tests for Promote Release."""

    @pytest.mark.asyncio()
    async def test_noop(self, gl: GitLabCLIBackend) -> None:
        """Test noop."""
        result = await gl.promote_release('v1.0.0')
        assert result.ok


class TestListReleases:
    """Tests for List Releases."""

    @pytest.mark.asyncio()
    async def test_success(self, gl: GitLabCLIBackend) -> None:
        """Test success."""
        with patch.object(gl, '_glab', return_value=_ok(stdout='v1.0.0\nv0.9.0\n')):
            releases = await gl.list_releases()
            assert len(releases) == 2
            assert releases[0]['tag'] == 'v1.0.0'

    @pytest.mark.asyncio()
    async def test_failure(self, gl: GitLabCLIBackend) -> None:
        """Test failure."""
        with patch.object(gl, '_glab', return_value=_fail()):
            assert await gl.list_releases() == []

    @pytest.mark.asyncio()
    async def test_empty(self, gl: GitLabCLIBackend) -> None:
        """Test empty."""
        with patch.object(gl, '_glab', return_value=_ok(stdout='')):
            assert await gl.list_releases() == []


class TestCreatePR:
    """Tests for Create PR."""

    @pytest.mark.asyncio()
    async def test_basic(self, gl: GitLabCLIBackend) -> None:
        """Test basic."""
        with patch.object(gl, '_glab', return_value=_ok()) as m:
            await gl.create_pr(title='MR title', head='feat/x', base='main', body='body')
            args = m.call_args[0]
            assert 'mr' in args
            assert 'create' in args
            assert '--source-branch' in args
            assert '--description' in args


class TestPRData:
    """Tests for PRData."""

    @pytest.mark.asyncio()
    async def test_success(self, gl: GitLabCLIBackend) -> None:
        """Test success."""
        data = {
            'title': 'MR',
            'description': 'desc',
            'author': {'username': 'user'},
            'labels': ['bug'],
            'state': 'merged',
            'merged_at': '2026-01-01',
            'source_branch': 'feat/x',
            'merge_commit_sha': 'abc',
        }
        with patch.object(gl, '_glab', return_value=_ok(stdout=json.dumps(data))):
            result = await gl.pr_data(42)
            assert result['title'] == 'MR'
            assert result['body'] == 'desc'
            assert result['author'] == 'user'
            assert result['headRefName'] == 'feat/x'

    @pytest.mark.asyncio()
    async def test_failure(self, gl: GitLabCLIBackend) -> None:
        """Test failure."""
        with patch.object(gl, '_glab', return_value=_fail()):
            assert await gl.pr_data(42) == {}

    @pytest.mark.asyncio()
    async def test_bad_json(self, gl: GitLabCLIBackend) -> None:
        """Test bad json."""
        with patch.object(gl, '_glab', return_value=_ok(stdout='not json')):
            assert await gl.pr_data(42) == {}


class TestListPRs:
    """Tests for List PRs."""

    @pytest.mark.asyncio()
    async def test_with_filters(self, gl: GitLabCLIBackend) -> None:
        """Test with filters."""
        mrs = [
            {
                'iid': 1,
                'title': 'MR',
                'state': 'merged',
                'labels': [],
                'source_branch': 'feat/x',
                'merge_commit_sha': 'abc',
            }
        ]
        with patch.object(gl, '_glab', return_value=_ok(stdout=json.dumps(mrs))) as m:
            await gl.list_prs(label='bug', state='merged', head='feat/x')
            args = m.call_args[0]
            assert '--merged' in args
            assert '--label' in args
            assert '--source-branch' in args

    @pytest.mark.asyncio()
    async def test_closed_state(self, gl: GitLabCLIBackend) -> None:
        """Test closed state."""
        with patch.object(gl, '_glab', return_value=_ok(stdout='[]')) as m:
            await gl.list_prs(state='closed')
            assert '--closed' in m.call_args[0]

    @pytest.mark.asyncio()
    async def test_all_state(self, gl: GitLabCLIBackend) -> None:
        """Test all state."""
        with patch.object(gl, '_glab', return_value=_ok(stdout='[]')) as m:
            await gl.list_prs(state='all')
            assert '--all' in m.call_args[0]

    @pytest.mark.asyncio()
    async def test_failure(self, gl: GitLabCLIBackend) -> None:
        """Test failure."""
        with patch.object(gl, '_glab', return_value=_fail()):
            assert await gl.list_prs() == []

    @pytest.mark.asyncio()
    async def test_bad_json(self, gl: GitLabCLIBackend) -> None:
        """Test bad json."""
        with patch.object(gl, '_glab', return_value=_ok(stdout='not json')):
            assert await gl.list_prs() == []


class TestLabels:
    """Tests for Labels."""

    @pytest.mark.asyncio()
    async def test_add(self, gl: GitLabCLIBackend) -> None:
        """Test add."""
        with patch.object(gl, '_glab', return_value=_ok()) as m:
            await gl.add_labels(42, ['bug', 'urgent'])
            args = m.call_args[0]
            assert '--label' in args
            assert 'bug,urgent' in args

    @pytest.mark.asyncio()
    async def test_remove(self, gl: GitLabCLIBackend) -> None:
        """Test remove."""
        with patch.object(gl, '_glab', return_value=_ok()) as m:
            await gl.remove_labels(42, ['bug'])
            args = m.call_args[0]
            assert '--unlabel' in args


class TestUpdatePR:
    """Tests for Update PR."""

    @pytest.mark.asyncio()
    async def test_update(self, gl: GitLabCLIBackend) -> None:
        """Test update."""
        with patch.object(gl, '_glab', return_value=_ok()) as m:
            await gl.update_pr(42, title='New', body='Body')
            args = m.call_args[0]
            assert '--title' in args
            assert '--description' in args


class TestMergePR:
    """Tests for Merge PR."""

    @pytest.mark.asyncio()
    async def test_squash(self, gl: GitLabCLIBackend) -> None:
        """Test squash."""
        with patch.object(gl, '_glab', return_value=_ok()) as m:
            await gl.merge_pr(42)
            args = m.call_args[0]
            assert '--squash' in args
            assert '--remove-source-branch' in args
            assert '--yes' in args

    @pytest.mark.asyncio()
    async def test_merge_no_delete(self, gl: GitLabCLIBackend) -> None:
        """Test merge no delete."""
        with patch.object(gl, '_glab', return_value=_ok()) as m:
            await gl.merge_pr(42, method='merge', delete_branch=False)
            args = m.call_args[0]
            assert '--squash' not in args
            assert '--remove-source-branch' not in args

    @pytest.mark.asyncio()
    async def test_commit_message(self, gl: GitLabCLIBackend) -> None:
        """Test commit message."""
        with patch.object(gl, '_glab', return_value=_ok()) as m:
            await gl.merge_pr(42, commit_message='chore: release')
            args = m.call_args[0]
            assert '--message' in args
