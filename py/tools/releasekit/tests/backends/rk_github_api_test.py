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

Validates that :class:`GitHubAPIBackend` satisfies the :class:`Forge`
protocol, handles authentication, dry-run mode, and API responses
correctly.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from releasekit.backends.forge import Forge, GitHubAPIBackend
from releasekit.logging import configure_logging

configure_logging(quiet=True)


def _mock_response(
    status_code: int = 200,
    json_data: Any = None,  # noqa: ANN401 — test helper
    text: str = '',
) -> httpx.Response:
    """Create a mock httpx.Response."""
    if json_data is not None:
        content = json.dumps(json_data).encode()
        headers = {'content-type': 'application/json'}
    else:
        content = text.encode()
        headers = {'content-type': 'text/plain'}

    return httpx.Response(
        status_code=status_code,
        content=content,
        headers=headers,
        request=httpx.Request('GET', 'https://api.github.com/test'),
    )


@pytest.fixture
def backend() -> GitHubAPIBackend:
    """Create a backend with a test token."""
    return GitHubAPIBackend(
        owner='firebase',
        repo='genkit',
        token='ghp_test_token_for_unit_tests',
    )


class TestProtocolConformance:
    """Verify GitHubAPIBackend satisfies the Forge protocol."""

    def test_is_forge(self, backend: GitHubAPIBackend) -> None:
        """Test is forge."""
        if not isinstance(backend, Forge):
            pytest.fail(f'{type(backend).__name__} does not satisfy the Forge protocol')


class TestAuth:
    """Verify authentication resolution."""

    def test_explicit_token(self) -> None:
        """Test explicit token."""
        be = GitHubAPIBackend(owner='o', repo='r', token='tok')
        if be._headers.get('Authorization') != 'Bearer tok':
            pytest.fail('Explicit token not used')

    def test_github_token_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test github token env."""
        monkeypatch.setenv('GITHUB_TOKEN', 'env_tok')
        be = GitHubAPIBackend(owner='o', repo='r')
        if be._headers.get('Authorization') != 'Bearer env_tok':
            pytest.fail('GITHUB_TOKEN env var not used')

    def test_gh_token_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test gh token env."""
        monkeypatch.delenv('GITHUB_TOKEN', raising=False)
        monkeypatch.setenv('GH_TOKEN', 'gh_tok')
        be = GitHubAPIBackend(owner='o', repo='r')
        if be._headers.get('Authorization') != 'Bearer gh_tok':
            pytest.fail('GH_TOKEN env var not used')

    def test_no_token_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test no token raises."""
        monkeypatch.delenv('GITHUB_TOKEN', raising=False)
        monkeypatch.delenv('GH_TOKEN', raising=False)
        with pytest.raises(ValueError, match='GitHub API token required'):
            GitHubAPIBackend(owner='o', repo='r')

    def test_explicit_token_takes_precedence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test explicit token takes precedence."""
        monkeypatch.setenv('GITHUB_TOKEN', 'env_tok')
        be = GitHubAPIBackend(owner='o', repo='r', token='explicit')
        if be._headers.get('Authorization') != 'Bearer explicit':
            pytest.fail('Explicit token should take precedence over env vars')


class TestDryRun:
    """Dry-run mode should return synthetic results without HTTP calls."""

    @pytest.mark.asyncio
    async def test_create_release_dry_run(self, backend: GitHubAPIBackend) -> None:
        """Test create release dry run."""
        result = await backend.create_release('v1.0.0', dry_run=True)
        if not result.ok:
            pytest.fail('Dry-run create_release should return ok=True')
        if not result.dry_run:
            pytest.fail('Dry-run result should have dry_run=True')

    @pytest.mark.asyncio
    async def test_delete_release_dry_run(self, backend: GitHubAPIBackend) -> None:
        """Test delete release dry run."""
        result = await backend.delete_release('v1.0.0', dry_run=True)
        if not result.ok:
            pytest.fail('Dry-run delete_release should return ok=True')

    @pytest.mark.asyncio
    async def test_promote_release_dry_run(self, backend: GitHubAPIBackend) -> None:
        """Test promote release dry run."""
        result = await backend.promote_release('v1.0.0', dry_run=True)
        if not result.ok:
            pytest.fail('Dry-run promote_release should return ok=True')

    @pytest.mark.asyncio
    async def test_create_pr_dry_run(self, backend: GitHubAPIBackend) -> None:
        """Test create pr dry run."""
        result = await backend.create_pr(
            title='Release PR',
            head='release/v1.0.0',
            dry_run=True,
        )
        if not result.ok:
            pytest.fail('Dry-run create_pr should return ok=True')

    @pytest.mark.asyncio
    async def test_add_labels_dry_run(self, backend: GitHubAPIBackend) -> None:
        """Test add labels dry run."""
        result = await backend.add_labels(1, ['autorelease: pending'], dry_run=True)
        if not result.ok:
            pytest.fail('Dry-run add_labels should return ok=True')

    @pytest.mark.asyncio
    async def test_remove_labels_dry_run(self, backend: GitHubAPIBackend) -> None:
        """Test remove labels dry run."""
        result = await backend.remove_labels(1, ['autorelease: pending'], dry_run=True)
        if not result.ok:
            pytest.fail('Dry-run remove_labels should return ok=True')

    @pytest.mark.asyncio
    async def test_update_pr_dry_run(self, backend: GitHubAPIBackend) -> None:
        """Test update pr dry run."""
        result = await backend.update_pr(1, title='Updated', dry_run=True)
        if not result.ok:
            pytest.fail('Dry-run update_pr should return ok=True')


class TestAPIInteractions:
    """Test API interactions with mocked HTTP responses."""

    @pytest.mark.asyncio
    async def test_is_available_success(self, backend: GitHubAPIBackend) -> None:
        """Test is available success."""
        mock_resp = _mock_response(200, json_data={'full_name': 'firebase/genkit'})
        with patch('releasekit.backends.forge.github_api.request_with_retry', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_resp
            result = await backend.is_available()
        if not result:
            pytest.fail('is_available should return True for 200 response')

    @pytest.mark.asyncio
    async def test_is_available_failure(self, backend: GitHubAPIBackend) -> None:
        """Test is available failure."""
        mock_resp = _mock_response(401, text='Unauthorized')
        with patch('releasekit.backends.forge.github_api.request_with_retry', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_resp
            result = await backend.is_available()
        if result:
            pytest.fail('is_available should return False for 401 response')

    @pytest.mark.asyncio
    async def test_create_release_success(self, backend: GitHubAPIBackend) -> None:
        """Test create release success."""
        mock_resp = _mock_response(201, json_data={'id': 1, 'tag_name': 'v1.0.0'})
        with patch('releasekit.backends.forge.github_api.request_with_retry', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_resp
            result = await backend.create_release('v1.0.0', title='Release 1.0')
        if not result.ok:
            pytest.fail('create_release should succeed with 201')

    @pytest.mark.asyncio
    async def test_list_releases(self, backend: GitHubAPIBackend) -> None:
        """Test list releases."""
        mock_resp = _mock_response(
            200,
            json_data=[
                {'tag_name': 'v1.0.0', 'name': 'Release 1.0', 'draft': False, 'prerelease': False},
                {'tag_name': 'v0.9.0', 'name': 'Release 0.9', 'draft': True, 'prerelease': True},
            ],
        )
        with patch('releasekit.backends.forge.github_api.request_with_retry', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_resp
            releases = await backend.list_releases(limit=5)

        if len(releases) != 2:
            pytest.fail(f'Expected 2 releases, got {len(releases)}')
        if releases[0]['tag'] != 'v1.0.0':
            pytest.fail(f"Expected tag 'v1.0.0', got '{releases[0]['tag']}'")
        if releases[1]['draft'] is not True:
            pytest.fail('Second release should be a draft')

    @pytest.mark.asyncio
    async def test_pr_data(self, backend: GitHubAPIBackend) -> None:
        """Test pr data."""
        mock_resp = _mock_response(
            200,
            json_data={
                'title': 'fix: bug',
                'body': 'Fixes #123',
                'user': {'login': 'octocat'},
                'labels': [{'name': 'bug'}],
                'state': 'open',
                'merged_at': None,
                'head': {'ref': 'fix-bug'},
                'merge_commit_sha': 'abc123',
            },
        )
        with patch('releasekit.backends.forge.github_api.request_with_retry', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_resp
            data = await backend.pr_data(42)

        if data.get('title') != 'fix: bug':
            pytest.fail(f"Expected title 'fix: bug', got '{data.get('title')}'")
        if data.get('author') != 'octocat':
            pytest.fail(f"Expected author 'octocat', got '{data.get('author')}'")
        if data.get('labels') != ['bug']:
            pytest.fail(f"Expected labels ['bug'], got {data.get('labels')}")
        if data.get('headRefName') != 'fix-bug':
            pytest.fail(f"Expected headRefName 'fix-bug', got '{data.get('headRefName')}'")

    @pytest.mark.asyncio
    async def test_list_prs_with_label_filter(self, backend: GitHubAPIBackend) -> None:
        """Test list prs with label filter."""
        mock_resp = _mock_response(
            200,
            json_data=[
                {
                    'number': 1,
                    'title': 'Release PR',
                    'state': 'open',
                    'labels': [{'name': 'autorelease: pending'}],
                    'head': {'ref': 'release/v1.0'},
                    'merge_commit_sha': '',
                },
                {
                    'number': 2,
                    'title': 'Other PR',
                    'state': 'open',
                    'labels': [{'name': 'bug'}],
                    'head': {'ref': 'fix-bug'},
                    'merge_commit_sha': '',
                },
            ],
        )
        with patch('releasekit.backends.forge.github_api.request_with_retry', new_callable=AsyncMock) as mock_req:
            mock_req.return_value = mock_resp
            prs = await backend.list_prs(label='autorelease: pending')

        if len(prs) != 1:
            pytest.fail(f'Expected 1 PR after label filter, got {len(prs)}')
        if prs[0]['number'] != 1:
            pytest.fail(f'Expected PR #1, got #{prs[0]["number"]}')


class TestGitHubEnterprise:
    """Verify custom base_url for GitHub Enterprise Server."""

    def test_custom_base_url(self) -> None:
        """Test custom base url."""
        be = GitHubAPIBackend(
            owner='corp',
            repo='app',
            token='tok',
            base_url='https://github.example.com/api/v3',
        )
        expected = 'https://github.example.com/api/v3/repos/corp/app'
        if be._repo_url != expected:
            pytest.fail(f'Expected {expected}, got {be._repo_url}')

    def test_trailing_slash_stripped(self) -> None:
        """Test trailing slash stripped."""
        be = GitHubAPIBackend(
            owner='corp',
            repo='app',
            token='tok',
            base_url='https://github.example.com/api/v3/',
        )
        expected = 'https://github.example.com/api/v3/repos/corp/app'
        if be._repo_url != expected:
            pytest.fail(f'Expected {expected}, got {be._repo_url}')
