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

"""Tests for the Bitbucket REST API forge backend."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from releasekit.backends._run import CommandResult
from releasekit.backends.forge.bitbucket import BitbucketAPIBackend


def _ok(stdout: str = '', **kw: Any) -> CommandResult:  # noqa: ANN401
    """Ok."""
    return CommandResult(command=['GET', 'url'], return_code=0, stdout=stdout, **kw)


def _fail(code: int = 404, stderr: str = '', **kw: Any) -> CommandResult:  # noqa: ANN401
    """Fail."""
    return CommandResult(command=['GET', 'url'], return_code=code, stderr=stderr, **kw)


@pytest.fixture()
def bb() -> BitbucketAPIBackend:
    """Bb."""
    return BitbucketAPIBackend(workspace='myteam', repo_slug='genkit', token='fake-token')


class TestInit:
    """TestInit."""

    def test_token_auth(self) -> None:
        """Test token auth."""
        bb = BitbucketAPIBackend(workspace='w', repo_slug='r', token='tok')
        assert 'Bearer tok' in bb._headers.get('Authorization', '')

    def test_app_password_auth(self) -> None:
        """Test app password auth."""
        bb = BitbucketAPIBackend(workspace='w', repo_slug='r', username='u', app_password='p')
        assert bb._auth is not None

    def test_env_token(self) -> None:
        """Test env token."""
        with patch.dict('os.environ', {'BITBUCKET_TOKEN': 'env-tok'}):
            bb = BitbucketAPIBackend(workspace='w', repo_slug='r')
            assert 'Bearer env-tok' in bb._headers.get('Authorization', '')

    def test_env_app_password(self) -> None:
        """Test env app password."""
        with patch.dict('os.environ', {'BITBUCKET_USERNAME': 'u', 'BITBUCKET_APP_PASSWORD': 'p'}, clear=False):
            # Clear BITBUCKET_TOKEN to force app password path.
            env = {'BITBUCKET_USERNAME': 'u', 'BITBUCKET_APP_PASSWORD': 'p', 'BITBUCKET_TOKEN': ''}
            with patch.dict('os.environ', env):
                bb = BitbucketAPIBackend(workspace='w', repo_slug='r')
                assert bb._auth is not None

    def test_no_auth_raises(self) -> None:
        """Test no auth raises."""
        with patch.dict('os.environ', {'BITBUCKET_TOKEN': '', 'BITBUCKET_USERNAME': '', 'BITBUCKET_APP_PASSWORD': ''}):
            with pytest.raises(ValueError, match='Bitbucket auth required'):
                BitbucketAPIBackend(workspace='w', repo_slug='r')


class TestIsAvailable:
    """TestIsAvailable."""

    @pytest.mark.asyncio()
    async def test_available(self, bb: BitbucketAPIBackend) -> None:
        """Test available."""
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_ok()):
            assert await bb.is_available() is True

    @pytest.mark.asyncio()
    async def test_not_available(self, bb: BitbucketAPIBackend) -> None:
        """Test not available."""
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_fail()):
            assert await bb.is_available() is False


class TestCreateRelease:
    """TestCreateRelease."""

    @pytest.mark.asyncio()
    async def test_basic(self, bb: BitbucketAPIBackend) -> None:
        """Test basic."""
        # Mock _resolve_default_branch_head to avoid nested _request calls.
        with (
            patch.object(bb, '_resolve_default_branch_head', new_callable=AsyncMock, return_value='abc123'),
            patch.object(bb, '_request', new_callable=AsyncMock, return_value=_ok()) as m,
        ):
            await bb.create_release('v1.0.0', body='notes')
            m.assert_called_once()
            call_args = m.call_args
            assert call_args[0][0] == 'POST'
            assert 'refs/tags' in call_args[0][1]

    @pytest.mark.asyncio()
    async def test_dry_run(self, bb: BitbucketAPIBackend) -> None:
        """Test dry run."""
        with (
            patch.object(bb, '_resolve_default_branch_head', new_callable=AsyncMock, return_value='abc'),
            patch.object(bb, '_request', new_callable=AsyncMock, return_value=_ok()) as m,
        ):
            await bb.create_release('v1.0.0', dry_run=True)
            assert m.call_args[1].get('dry_run') is True


class TestDeleteRelease:
    """TestDeleteRelease."""

    @pytest.mark.asyncio()
    async def test_delete(self, bb: BitbucketAPIBackend) -> None:
        """Test delete."""
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_ok()) as m:
            await bb.delete_release('v1.0.0')
            assert m.call_args[0][0] == 'DELETE'
            assert 'refs/tags/v1.0.0' in m.call_args[0][1]


class TestPromoteRelease:
    """TestPromoteRelease."""

    @pytest.mark.asyncio()
    async def test_noop(self, bb: BitbucketAPIBackend) -> None:
        """Test noop."""
        result = await bb.promote_release('v1.0.0')
        assert result.ok
        assert result.dry_run is True


class TestListReleases:
    """TestListReleases."""

    @pytest.mark.asyncio()
    async def test_success(self, bb: BitbucketAPIBackend) -> None:
        """Test success."""
        data = {'values': [{'name': 'v1.0.0'}, {'name': 'v0.9.0'}]}
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_ok(stdout=json.dumps(data))):
            releases = await bb.list_releases()
            assert len(releases) == 2
            assert releases[0]['tag'] == 'v1.0.0'

    @pytest.mark.asyncio()
    async def test_failure(self, bb: BitbucketAPIBackend) -> None:
        """Test failure."""
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_fail()):
            assert await bb.list_releases() == []

    @pytest.mark.asyncio()
    async def test_bad_json(self, bb: BitbucketAPIBackend) -> None:
        """Test bad json."""
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_ok(stdout='not json')):
            assert await bb.list_releases() == []


class TestCreatePR:
    """TestCreatePR."""

    @pytest.mark.asyncio()
    async def test_basic(self, bb: BitbucketAPIBackend) -> None:
        """Test basic."""
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_ok()) as m:
            await bb.create_pr(title='PR', head='feat/x', base='main', body='body')
            assert m.call_args[0][0] == 'POST'
            assert 'pullrequests' in m.call_args[0][1]


class TestPRData:
    """TestPRData."""

    @pytest.mark.asyncio()
    async def test_success(self, bb: BitbucketAPIBackend) -> None:
        """Test success."""
        data = {
            'title': 'PR',
            'description': 'desc',
            'author': {'display_name': 'User'},
            'state': 'OPEN',
            'updated_on': '2026-01-01',
            'source': {'branch': {'name': 'feat/x'}},
            'merge_commit': {'hash': 'abc'},
        }
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_ok(stdout=json.dumps(data))):
            result = await bb.pr_data(42)
            assert result['title'] == 'PR'
            assert result['author'] == 'User'
            assert result['headRefName'] == 'feat/x'

    @pytest.mark.asyncio()
    async def test_failure(self, bb: BitbucketAPIBackend) -> None:
        """Test failure."""
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_fail()):
            assert await bb.pr_data(42) == {}

    @pytest.mark.asyncio()
    async def test_bad_json(self, bb: BitbucketAPIBackend) -> None:
        """Test bad json."""
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_ok(stdout='not json')):
            assert await bb.pr_data(42) == {}


class TestListPRs:
    """TestListPRs."""

    @pytest.mark.asyncio()
    async def test_basic(self, bb: BitbucketAPIBackend) -> None:
        """Test basic."""
        data = {
            'values': [
                {
                    'id': 1,
                    'title': 'PR1',
                    'state': 'OPEN',
                    'source': {'branch': {'name': 'feat/x'}},
                    'merge_commit': {'hash': 'abc'},
                },
            ]
        }
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_ok(stdout=json.dumps(data))):
            prs = await bb.list_prs()
            assert len(prs) == 1
            assert prs[0]['number'] == 1

    @pytest.mark.asyncio()
    async def test_head_filter(self, bb: BitbucketAPIBackend) -> None:
        """Test head filter."""
        data = {
            'values': [
                {
                    'id': 1,
                    'title': 'PR1',
                    'state': 'OPEN',
                    'source': {'branch': {'name': 'feat/x'}},
                    'merge_commit': {},
                },
                {
                    'id': 2,
                    'title': 'PR2',
                    'state': 'OPEN',
                    'source': {'branch': {'name': 'feat/y'}},
                    'merge_commit': {},
                },
            ]
        }
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_ok(stdout=json.dumps(data))):
            prs = await bb.list_prs(head='feat/x')
            assert len(prs) == 1

    @pytest.mark.asyncio()
    async def test_label_filter(self, bb: BitbucketAPIBackend) -> None:
        """Test label filter."""
        data = {
            'values': [
                {
                    'id': 1,
                    'title': '[autorelease] PR1',
                    'state': 'OPEN',
                    'source': {'branch': {'name': 'feat/x'}},
                    'merge_commit': {},
                },
                {
                    'id': 2,
                    'title': 'PR2',
                    'state': 'OPEN',
                    'source': {'branch': {'name': 'feat/y'}},
                    'merge_commit': {},
                },
            ]
        }
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_ok(stdout=json.dumps(data))):
            prs = await bb.list_prs(label='autorelease')
            assert len(prs) == 1

    @pytest.mark.asyncio()
    async def test_failure(self, bb: BitbucketAPIBackend) -> None:
        """Test failure."""
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_fail()):
            assert await bb.list_prs() == []

    @pytest.mark.asyncio()
    async def test_bad_json(self, bb: BitbucketAPIBackend) -> None:
        """Test bad json."""
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_ok(stdout='not json')):
            assert await bb.list_prs() == []


class TestLabels:
    """TestLabels."""

    @pytest.mark.asyncio()
    async def test_add_noop(self, bb: BitbucketAPIBackend) -> None:
        """Test add noop."""
        result = await bb.add_labels(42, ['bug'])
        assert result.ok
        assert result.dry_run is True

    @pytest.mark.asyncio()
    async def test_remove_noop(self, bb: BitbucketAPIBackend) -> None:
        """Test remove noop."""
        result = await bb.remove_labels(42, ['bug'])
        assert result.ok
        assert result.dry_run is True


class TestUpdatePR:
    """TestUpdatePR."""

    @pytest.mark.asyncio()
    async def test_update(self, bb: BitbucketAPIBackend) -> None:
        """Test update."""
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_ok()) as m:
            await bb.update_pr(42, title='New', body='Body')
            assert m.call_args[0][0] == 'PUT'


class TestMergePR:
    """TestMergePR."""

    @pytest.mark.asyncio()
    async def test_squash(self, bb: BitbucketAPIBackend) -> None:
        """Test squash."""
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_ok()) as m:
            await bb.merge_pr(42)
            payload = m.call_args[1].get('json_data', {})
            assert payload['merge_strategy'] == 'squash'
            assert payload['close_source_branch'] is True

    @pytest.mark.asyncio()
    async def test_merge_method(self, bb: BitbucketAPIBackend) -> None:
        """Test merge method."""
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_ok()) as m:
            await bb.merge_pr(42, method='merge')
            payload = m.call_args[1].get('json_data', {})
            assert payload['merge_strategy'] == 'merge_commit'

    @pytest.mark.asyncio()
    async def test_rebase_method(self, bb: BitbucketAPIBackend) -> None:
        """Test rebase method."""
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_ok()) as m:
            await bb.merge_pr(42, method='rebase')
            payload = m.call_args[1].get('json_data', {})
            assert payload['merge_strategy'] == 'fast_forward'


class TestResolveDefaultBranchHead:
    """TestResolveDefaultBranchHead."""

    @pytest.mark.asyncio()
    async def test_success(self, bb: BitbucketAPIBackend) -> None:
        """Test success."""
        repo_data = json.dumps({'mainbranch': {'name': 'main'}})
        branch_data = json.dumps({'target': {'hash': 'abc123def'}})

        call_count = 0

        async def mock_request(method: str, url: str, **kw: object) -> object:
            """Mock request."""
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _ok(stdout=repo_data)
            return _ok(stdout=branch_data)

        with patch.object(bb, '_request', side_effect=mock_request):
            result = await bb._resolve_default_branch_head()
            assert result == 'abc123def'

    @pytest.mark.asyncio()
    async def test_fallback(self, bb: BitbucketAPIBackend) -> None:
        """Test fallback."""
        with patch.object(bb, '_request', new_callable=AsyncMock, return_value=_fail()):
            result = await bb._resolve_default_branch_head()
            assert result == 'main'
