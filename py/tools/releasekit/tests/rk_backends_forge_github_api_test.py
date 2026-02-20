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

"""Tests for the GitHub REST API forge backend.

Uses httpx mock transport to avoid real network calls.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
import pytest
from releasekit.backends.forge.github_api import GitHubAPIBackend

# Helpers


def _mock_transport(responses: dict[str, tuple[int, str]]) -> object:
    """Create a mock transport handler keyed by URL suffix."""

    def handler(request: httpx.Request) -> httpx.Response:
        """Handler."""
        url = str(request.url)
        for suffix, (status, body) in responses.items():
            if suffix in url:
                return httpx.Response(status, text=body)
        return httpx.Response(404, text='Not found')

    return handler


def _make_client_cm(transport: Any) -> Any:  # noqa: ANN401
    """Create a context manager that yields an httpx.AsyncClient with mock transport."""

    @asynccontextmanager
    async def _client_cm(**kw: Any) -> AsyncGenerator[httpx.AsyncClient]:  # noqa: ANN401
        """Client cm."""
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
            yield client

    return _client_cm


@pytest.fixture()
def gh() -> GitHubAPIBackend:
    """Create a GitHubAPIBackend fixture."""
    return GitHubAPIBackend(owner='firebase', repo='genkit', token='fake-token')


# Init / Auth


class TestInit:
    """Tests for Init."""

    def test_explicit_token(self) -> None:
        """Test explicit token."""
        api = GitHubAPIBackend(owner='o', repo='r', token='tok')
        assert 'Bearer tok' in api._headers['Authorization']

    def test_env_github_token(self) -> None:
        """Test env github token."""
        with patch.dict('os.environ', {'GITHUB_TOKEN': 'env-tok', 'GH_TOKEN': ''}):
            api = GitHubAPIBackend(owner='o', repo='r')
            assert 'Bearer env-tok' in api._headers['Authorization']

    def test_env_gh_token(self) -> None:
        """Test env gh token."""
        with patch.dict('os.environ', {'GITHUB_TOKEN': '', 'GH_TOKEN': 'gh-tok'}):
            api = GitHubAPIBackend(owner='o', repo='r')
            assert 'Bearer gh-tok' in api._headers['Authorization']

    def test_no_token_raises(self) -> None:
        """Test no token raises."""
        with patch.dict('os.environ', {'GITHUB_TOKEN': '', 'GH_TOKEN': ''}):
            with pytest.raises(ValueError, match='GitHub API token required'):
                GitHubAPIBackend(owner='o', repo='r')

    def test_custom_base_url(self) -> None:
        """Test custom base url."""
        api = GitHubAPIBackend(owner='o', repo='r', token='t', base_url='https://ghe.corp.com/api/v3/')
        assert api._base_url == 'https://ghe.corp.com/api/v3'
        assert 'ghe.corp.com' in api._repo_url


class TestDryRunResult:
    """Tests for Dry Run Result."""

    def test_creates_synthetic_result(self, gh: GitHubAPIBackend) -> None:
        """Test creates synthetic result."""
        result = gh._dry_run_result('POST', 'https://api.github.com/test')
        assert result.ok is True
        assert result.dry_run is True
        assert result.command == ['POST', 'https://api.github.com/test']


# is_available


class TestIsAvailable:
    """Tests for Is Available."""

    @pytest.mark.asyncio()
    async def test_available(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test available."""
        transport = _mock_transport({'/repos/firebase/genkit': (200, '{}')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        assert await gh.is_available() is True

    @pytest.mark.asyncio()
    async def test_not_available(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test not available."""
        transport = _mock_transport({'/repos/firebase/genkit': (401, 'Unauthorized')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        assert await gh.is_available() is False


# create_release


class TestCreateRelease:
    """Tests for Create Release."""

    @pytest.mark.asyncio()
    async def test_basic(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test basic."""
        transport = _mock_transport({'/releases': (201, '{"id": 1}')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        result = await gh.create_release('v1.0.0', title='Release', body='notes')
        assert result.ok is True

    @pytest.mark.asyncio()
    async def test_dry_run(self, gh: GitHubAPIBackend) -> None:
        """Test dry run."""
        result = await gh.create_release('v1.0.0', dry_run=True)
        assert result.ok is True
        assert result.dry_run is True

    @pytest.mark.asyncio()
    async def test_with_assets_logs_warning(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test with assets logs warning."""
        transport = _mock_transport({'/releases': (201, '{}')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        # Should not raise — just logs a warning about unsupported assets.
        result = await gh.create_release('v1.0.0', assets=[Path('/fake/assets/a.tar.gz')])
        assert result.ok is True

    @pytest.mark.asyncio()
    async def test_failure(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test failure."""
        transport = _mock_transport({'/releases': (422, 'Validation failed')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        result = await gh.create_release('v1.0.0')
        assert result.ok is False


# delete_release


class TestDeleteRelease:
    """Tests for Delete Release."""

    @pytest.mark.asyncio()
    async def test_success(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test success."""
        transport = _mock_transport({
            '/releases/tags/v1.0.0': (200, '{"id": 42}'),
            '/releases/42': (204, ''),
        })
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        result = await gh.delete_release('v1.0.0')
        assert result.ok is True

    @pytest.mark.asyncio()
    async def test_not_found(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test not found."""
        transport = _mock_transport({'/releases/tags/v1.0.0': (404, 'Not found')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        result = await gh.delete_release('v1.0.0')
        assert result.ok is False

    @pytest.mark.asyncio()
    async def test_dry_run(self, gh: GitHubAPIBackend) -> None:
        """Test dry run."""
        result = await gh.delete_release('v1.0.0', dry_run=True)
        assert result.ok is True
        assert result.dry_run is True


# promote_release


class TestPromoteRelease:
    """Tests for Promote Release."""

    @pytest.mark.asyncio()
    async def test_success(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test success."""
        transport = _mock_transport({
            '/releases/tags/v1.0.0': (200, '{"id": 42}'),
            '/releases/42': (200, '{"draft": false}'),
        })
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        result = await gh.promote_release('v1.0.0')
        assert result.ok is True

    @pytest.mark.asyncio()
    async def test_not_found(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test not found."""
        transport = _mock_transport({'/releases/tags/v1.0.0': (404, 'Not found')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        result = await gh.promote_release('v1.0.0')
        assert result.ok is False

    @pytest.mark.asyncio()
    async def test_dry_run(self, gh: GitHubAPIBackend) -> None:
        """Test dry run."""
        result = await gh.promote_release('v1.0.0', dry_run=True)
        assert result.ok is True
        assert result.dry_run is True


# list_releases


class TestListReleases:
    """Tests for List Releases."""

    @pytest.mark.asyncio()
    async def test_success(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test success."""
        data = [{'tag_name': 'v1.0.0', 'name': 'Release 1', 'draft': False, 'prerelease': False}]
        transport = _mock_transport({'/releases?': (200, json.dumps(data))})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        releases = await gh.list_releases()
        assert len(releases) == 1
        assert releases[0]['tag'] == 'v1.0.0'

    @pytest.mark.asyncio()
    async def test_failure(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test failure."""
        transport = _mock_transport({'/releases?': (403, 'Forbidden')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        assert await gh.list_releases() == []

    @pytest.mark.asyncio()
    async def test_bad_json(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test bad json."""
        transport = _mock_transport({'/releases?': (200, 'not json')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        assert await gh.list_releases() == []


# create_pr


class TestCreatePR:
    """Tests for Create PR."""

    @pytest.mark.asyncio()
    async def test_success(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test success."""
        transport = _mock_transport({'/pulls': (201, '{"number": 1}')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        result = await gh.create_pr(title='PR', head='feat/x', base='main', body='body')
        assert result.ok is True

    @pytest.mark.asyncio()
    async def test_dry_run(self, gh: GitHubAPIBackend) -> None:
        """Test dry run."""
        result = await gh.create_pr(title='PR', head='feat/x', dry_run=True)
        assert result.ok is True
        assert result.dry_run is True

    @pytest.mark.asyncio()
    async def test_failure(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test failure."""
        transport = _mock_transport({'/pulls': (422, 'Validation failed')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        result = await gh.create_pr(title='PR', head='feat/x')
        assert result.ok is False


# pr_data


class TestPRData:
    """Tests for PRData."""

    @pytest.mark.asyncio()
    async def test_success(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test success."""
        data = {
            'title': 'PR Title',
            'body': 'PR body',
            'user': {'login': 'octocat'},
            'labels': [{'name': 'bug'}],
            'state': 'open',
            'merged_at': None,
            'head': {'ref': 'feat/x'},
            'merge_commit_sha': 'abc123',
        }
        transport = _mock_transport({'/pulls/42': (200, json.dumps(data))})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        result = await gh.pr_data(42)
        assert result['title'] == 'PR Title'
        assert result['author'] == 'octocat'
        assert result['labels'] == ['bug']
        assert result['headRefName'] == 'feat/x'
        assert result['mergeCommit']['oid'] == 'abc123'

    @pytest.mark.asyncio()
    async def test_not_found(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test not found."""
        transport = _mock_transport({'/pulls/42': (404, 'Not found')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        assert await gh.pr_data(42) == {}

    @pytest.mark.asyncio()
    async def test_bad_json(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test bad json."""
        transport = _mock_transport({'/pulls/42': (200, 'not json')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        assert await gh.pr_data(42) == {}


# list_prs


class TestListPRs:
    """Tests for List PRs."""

    @pytest.mark.asyncio()
    async def test_basic(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test basic."""
        data = [
            {
                'number': 1,
                'title': 'PR1',
                'state': 'open',
                'labels': [{'name': 'bug'}],
                'head': {'ref': 'feat/x'},
                'merge_commit_sha': 'abc',
                'merged_at': None,
            }
        ]
        transport = _mock_transport({'/pulls?': (200, json.dumps(data))})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        prs = await gh.list_prs()
        assert len(prs) == 1
        assert prs[0]['number'] == 1

    @pytest.mark.asyncio()
    async def test_label_filter(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test label filter."""
        data = [
            {
                'number': 1,
                'title': 'PR1',
                'state': 'open',
                'labels': [{'name': 'autorelease'}],
                'head': {'ref': 'a'},
                'merge_commit_sha': '',
                'merged_at': None,
            },
            {
                'number': 2,
                'title': 'PR2',
                'state': 'open',
                'labels': [],
                'head': {'ref': 'b'},
                'merge_commit_sha': '',
                'merged_at': None,
            },
        ]
        transport = _mock_transport({'/pulls?': (200, json.dumps(data))})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        prs = await gh.list_prs(label='autorelease')
        assert len(prs) == 1
        assert prs[0]['number'] == 1

    @pytest.mark.asyncio()
    async def test_merged_filter(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test merged filter."""
        data = [
            {
                'number': 1,
                'title': 'PR1',
                'state': 'closed',
                'labels': [],
                'head': {'ref': 'a'},
                'merge_commit_sha': 'abc',
                'merged_at': '2026-01-01',
            },
            {
                'number': 2,
                'title': 'PR2',
                'state': 'closed',
                'labels': [],
                'head': {'ref': 'b'},
                'merge_commit_sha': '',
                'merged_at': None,
            },
        ]
        transport = _mock_transport({'/pulls?': (200, json.dumps(data))})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        prs = await gh.list_prs(state='merged')
        assert len(prs) == 1
        assert prs[0]['number'] == 1

    @pytest.mark.asyncio()
    async def test_head_filter(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test head filter."""
        transport = _mock_transport({'/pulls?': (200, '[]')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        await gh.list_prs(head='feat/x')
        # Just verify it doesn't crash; URL construction tested implicitly.

    @pytest.mark.asyncio()
    async def test_failure(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test failure."""
        transport = _mock_transport({'/pulls?': (403, 'Forbidden')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        assert await gh.list_prs() == []

    @pytest.mark.asyncio()
    async def test_bad_json(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test bad json."""
        transport = _mock_transport({'/pulls?': (200, 'not json')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        assert await gh.list_prs() == []


# add_labels


class TestAddLabels:
    """Tests for Add Labels."""

    @pytest.mark.asyncio()
    async def test_success(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test success."""
        transport = _mock_transport({'/issues/42/labels': (200, '[]')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        result = await gh.add_labels(42, ['bug', 'urgent'])
        assert result.ok is True

    @pytest.mark.asyncio()
    async def test_dry_run(self, gh: GitHubAPIBackend) -> None:
        """Test dry run."""
        result = await gh.add_labels(42, ['bug'], dry_run=True)
        assert result.ok is True
        assert result.dry_run is True


# remove_labels


class TestRemoveLabels:
    """Tests for Remove Labels."""

    @pytest.mark.asyncio()
    async def test_success(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test success."""
        transport = _mock_transport({'/labels/bug': (200, ''), '/labels/urgent': (200, '')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        result = await gh.remove_labels(42, ['bug', 'urgent'])
        assert result.ok is True

    @pytest.mark.asyncio()
    async def test_dry_run(self, gh: GitHubAPIBackend) -> None:
        """Test dry run."""
        result = await gh.remove_labels(42, ['bug'], dry_run=True)
        assert result.ok is True
        assert result.dry_run is True

    @pytest.mark.asyncio()
    async def test_empty_labels(self, gh: GitHubAPIBackend) -> None:
        """Test empty labels."""
        result = await gh.remove_labels(42, [])
        assert result.ok is True
        assert result.dry_run is True


# update_pr


class TestUpdatePR:
    """Tests for Update PR."""

    @pytest.mark.asyncio()
    async def test_success(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test success."""
        transport = _mock_transport({'/pulls/42': (200, '{}')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        result = await gh.update_pr(42, title='New', body='Body')
        assert result.ok is True

    @pytest.mark.asyncio()
    async def test_dry_run(self, gh: GitHubAPIBackend) -> None:
        """Test dry run."""
        result = await gh.update_pr(42, dry_run=True)
        assert result.ok is True
        assert result.dry_run is True


# merge_pr


class TestMergePR:
    """Tests for Merge PR."""

    @pytest.mark.asyncio()
    async def test_squash_with_branch_delete(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test squash with branch delete."""
        pr_data = {'head': {'ref': 'feat/x'}}
        transport = _mock_transport({
            '/pulls/42/merge': (200, '{"merged": true}'),
            '/pulls/42': (200, json.dumps(pr_data)),
            '/git/refs/heads/feat/x': (204, ''),
        })
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        result = await gh.merge_pr(42)
        assert result.ok is True

    @pytest.mark.asyncio()
    async def test_no_branch_delete(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test no branch delete."""
        transport = _mock_transport({'/pulls/42/merge': (200, '{"merged": true}')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        result = await gh.merge_pr(42, delete_branch=False)
        assert result.ok is True

    @pytest.mark.asyncio()
    async def test_with_commit_message(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test with commit message."""
        transport = _mock_transport({'/pulls/42/merge': (200, '{}')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        result = await gh.merge_pr(42, commit_message='chore: release', delete_branch=False)
        assert result.ok is True

    @pytest.mark.asyncio()
    async def test_dry_run(self, gh: GitHubAPIBackend) -> None:
        """Test dry run."""
        result = await gh.merge_pr(42, dry_run=True)
        assert result.ok is True
        assert result.dry_run is True

    @pytest.mark.asyncio()
    async def test_failure(self, gh: GitHubAPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test failure."""
        transport = _mock_transport({'/pulls/42/merge': (405, 'Not allowed')})
        monkeypatch.setattr('releasekit.backends.forge.github_api.http_client', _make_client_cm(transport))
        result = await gh.merge_pr(42, delete_branch=False)
        assert result.ok is False
