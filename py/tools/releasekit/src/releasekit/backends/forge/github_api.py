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

"""GitHub REST API forge backend for releasekit.

Implements the :class:`~releasekit.backends.forge.Forge` protocol using
the GitHub REST API v3 via ``httpx``. Preferred over
:class:`~releasekit.backends.forge.github.GitHubCLIBackend` in CI where:

- The ``gh`` CLI may not be installed (minimal containers, self-hosted runners).
- Direct ``GITHUB_TOKEN`` authentication is simpler than ``gh auth login``.
- API rate-limit headers are available for better backoff.

Authentication:

    Resolves a token in order of precedence:

    1. ``token`` constructor parameter.
    2. ``GITHUB_TOKEN`` env var (set automatically by GitHub Actions).
    3. ``GH_TOKEN`` env var (used by the ``gh`` CLI).

    If none are set, the backend raises ``ValueError`` at construction
    to fail fast rather than silently on the first API call.

Usage::

    from releasekit.backends.forge.github_api import GitHubAPIBackend

    forge = GitHubAPIBackend(owner='firebase', repo='genkit')
    if await forge.is_available():
        await forge.create_release('v1.0.0', title='Release v1.0.0')

.. seealso::

    `GitHub REST API <https://docs.github.com/en/rest>`_
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from releasekit.backends._run import CommandResult
from releasekit.logging import get_logger
from releasekit.net import DEFAULT_POOL_SIZE, DEFAULT_TIMEOUT, http_client, request_with_retry

log = get_logger('releasekit.backends.forge.github_api')

# GitHub REST API base URL.
_DEFAULT_BASE_URL = 'https://api.github.com'

# API version header for stable API behavior.
_API_VERSION = '2022-11-28'


class GitHubAPIBackend:
    """Forge implementation using the GitHub REST API.

    Uses ``httpx`` for async HTTP with connection pooling and automatic
    retry on transient errors (429, 5xx). No ``gh`` CLI dependency.

    In GitHub Actions, the ``GITHUB_TOKEN`` secret is automatically
    available and provides scoped access to the repository. For
    cross-repository operations (e.g., creating releases in a fork),
    use a Personal Access Token or GitHub App token.

    Args:
        owner: Repository owner (e.g., ``"firebase"``).
        repo: Repository name (e.g., ``"genkit"``).
        token: GitHub API token. Falls back to ``GITHUB_TOKEN`` or
            ``GH_TOKEN`` env vars.
        base_url: API base URL (override for GitHub Enterprise Server).
        pool_size: HTTP connection pool size.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        owner: str,
        repo: str,
        *,
        token: str = '',
        base_url: str = _DEFAULT_BASE_URL,
        pool_size: int = DEFAULT_POOL_SIZE,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize with owner, repo, and API token."""
        self._owner = owner
        self._repo = repo
        self._base_url = base_url.rstrip('/')
        self._repo_url = f'{self._base_url}/repos/{owner}/{repo}'
        self._pool_size = pool_size
        self._timeout = timeout

        # Resolve auth: explicit token > GITHUB_TOKEN > GH_TOKEN.
        resolved_token = token or os.environ.get('GITHUB_TOKEN', '') or os.environ.get('GH_TOKEN', '')
        if not resolved_token:
            msg = 'GitHub API token required: pass token= or set GITHUB_TOKEN or GH_TOKEN env var.'
            raise ValueError(msg)

        self._headers = {
            'Authorization': f'Bearer {resolved_token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': _API_VERSION,
        }

    def __repr__(self) -> str:
        """Return a safe repr that never exposes the API token."""
        return f'GitHubAPIBackend(owner={self._owner!r}, repo={self._repo!r})'

    def _dry_run_result(self, method: str, url: str) -> CommandResult:
        """Create a synthetic CommandResult for dry-run mode."""
        return CommandResult(
            command=[method, url],
            return_code=0,
            stdout='',
            stderr='',
            dry_run=True,
        )

    async def is_available(self) -> bool:
        """Check if the GitHub API is reachable and the token is valid."""
        async with http_client(
            pool_size=self._pool_size,
            timeout=self._timeout,
            headers=self._headers,
        ) as client:
            response = await request_with_retry(client, 'GET', self._repo_url)
            if response.status_code != 200:
                log.warning(
                    'github_api_not_available',
                    status=response.status_code,
                    hint='Check GITHUB_TOKEN permissions (repo scope required)',
                )
                return False
            return True

    async def create_release(
        self,
        tag: str,
        *,
        title: str | None = None,
        body: str = '',
        draft: bool = False,
        prerelease: bool = False,
        assets: list[Path] | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Create a GitHub Release via the REST API.

        Note: Asset upload is not yet implemented via the REST API.
        Use the ``gh`` CLI backend if you need asset uploads.
        """
        url = f'{self._repo_url}/releases'
        if dry_run:
            log.info('dry_run_create_release', tag=tag)
            return self._dry_run_result('POST', url)

        payload: dict[str, Any] = {
            'tag_name': tag,
            'name': title or tag,
            'body': body,
            'draft': draft,
            'prerelease': prerelease,
            'generate_release_notes': not body,
        }

        if assets:
            log.warning(
                'asset_upload_not_supported',
                count=len(assets),
                hint='Use GitHubCLIBackend for asset uploads, or upload manually.',
            )

        async with http_client(
            pool_size=self._pool_size,
            timeout=self._timeout,
            headers=self._headers,
        ) as client:
            response = await request_with_retry(client, 'POST', url, json=payload)

        log.info('create_release', tag=tag, status=response.status_code)
        return CommandResult(
            command=['POST', url],
            return_code=0 if response.is_success else response.status_code,
            stdout=response.text,
            stderr='' if response.is_success else response.text,
        )

    async def delete_release(
        self,
        tag: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Delete a release by finding it via tag, then deleting by release ID."""
        release_url = f'{self._repo_url}/releases/tags/{tag}'
        if dry_run:
            log.info('dry_run_delete_release', tag=tag)
            return self._dry_run_result('DELETE', release_url)

        async with http_client(
            pool_size=self._pool_size,
            timeout=self._timeout,
            headers=self._headers,
        ) as client:
            # Find release by tag.
            lookup = await request_with_retry(client, 'GET', release_url)
            if lookup.status_code != 200:
                log.warning('release_not_found', tag=tag, status=lookup.status_code)
                return CommandResult(
                    command=['GET', release_url],
                    return_code=lookup.status_code,
                    stdout='',
                    stderr=f'Release not found for tag {tag}',
                )

            release_data = lookup.json()
            release_id = release_data.get('id')
            delete_url = f'{self._repo_url}/releases/{release_id}'

            response = await request_with_retry(client, 'DELETE', delete_url)

        log.info('delete_release', tag=tag, status=response.status_code)
        return CommandResult(
            command=['DELETE', delete_url],
            return_code=0 if response.is_success else response.status_code,
            stdout='',
            stderr='' if response.is_success else response.text,
        )

    async def promote_release(
        self,
        tag: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Promote a draft release to published by setting draft=false."""
        release_url = f'{self._repo_url}/releases/tags/{tag}'
        if dry_run:
            log.info('dry_run_promote_release', tag=tag)
            return self._dry_run_result('PATCH', release_url)

        async with http_client(
            pool_size=self._pool_size,
            timeout=self._timeout,
            headers=self._headers,
        ) as client:
            lookup = await request_with_retry(client, 'GET', release_url)
            if lookup.status_code != 200:
                return CommandResult(
                    command=['GET', release_url],
                    return_code=lookup.status_code,
                    stdout='',
                    stderr=f'Release not found for tag {tag}',
                )

            release_data = lookup.json()
            release_id = release_data.get('id')
            edit_url = f'{self._repo_url}/releases/{release_id}'

            response = await request_with_retry(
                client,
                'PATCH',
                edit_url,
                json={'draft': False},
            )

        log.info('promote_release', tag=tag, status=response.status_code)
        return CommandResult(
            command=['PATCH', edit_url],
            return_code=0 if response.is_success else response.status_code,
            stdout=response.text,
            stderr='' if response.is_success else response.text,
        )

    async def list_releases(
        self,
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List recent releases via the REST API."""
        url = f'{self._repo_url}/releases?per_page={limit}'
        async with http_client(
            pool_size=self._pool_size,
            timeout=self._timeout,
            headers=self._headers,
        ) as client:
            response = await request_with_retry(client, 'GET', url)

        if response.status_code != 200:
            return []

        try:
            releases = response.json()
        except (ValueError, json.JSONDecodeError):
            log.warning('release_list_parse_error')
            return []

        return [
            {
                'tag': r.get('tag_name', ''),
                'title': r.get('name', ''),
                'draft': r.get('draft', False),
                'prerelease': r.get('prerelease', False),
            }
            for r in releases
        ]

    async def create_pr(
        self,
        *,
        title: str,
        body: str = '',
        head: str,
        base: str = 'main',
        dry_run: bool = False,
    ) -> CommandResult:
        """Create a Pull Request via the REST API."""
        url = f'{self._repo_url}/pulls'
        if dry_run:
            log.info('dry_run_create_pr', title=title, head=head, base=base)
            return self._dry_run_result('POST', url)

        payload: dict[str, Any] = {
            'title': title,
            'body': body,
            'head': head,
            'base': base,
        }

        async with http_client(
            pool_size=self._pool_size,
            timeout=self._timeout,
            headers=self._headers,
        ) as client:
            response = await request_with_retry(client, 'POST', url, json=payload)

        log.info('create_pr', title=title, status=response.status_code)
        # Extract html_url from response so stdout matches gh CLI behavior
        # (prepare.py expects stdout to be the PR URL).
        stdout = response.text
        if response.is_success:
            try:
                pr_data = response.json()
                stdout = pr_data.get('html_url', response.text)
            except (ValueError, json.JSONDecodeError):
                pass
        return CommandResult(
            command=['POST', url],
            return_code=0 if response.is_success else response.status_code,
            stdout=stdout,
            stderr='' if response.is_success else response.text,
        )

    async def pr_data(self, pr_number: int) -> dict[str, Any]:
        """Fetch PR data and normalize to Forge contract keys."""
        url = f'{self._repo_url}/pulls/{pr_number}'
        async with http_client(
            pool_size=self._pool_size,
            timeout=self._timeout,
            headers=self._headers,
        ) as client:
            response = await request_with_retry(client, 'GET', url)

        if response.status_code != 200:
            return {}

        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError):
            log.warning('pr_data_parse_error', pr=pr_number)
            return {}

        # Normalize GitHub REST API response to the Forge contract.
        return {
            'title': data.get('title', ''),
            'body': data.get('body', ''),
            'author': data.get('user', {}).get('login', ''),
            'labels': [lbl.get('name', '') for lbl in data.get('labels', [])],
            'state': data.get('state', ''),
            'mergedAt': data.get('merged_at', ''),
            'headRefName': data.get('head', {}).get('ref', ''),
            'mergeCommit': {
                'oid': data.get('merge_commit_sha', ''),
            },
        }

    async def list_prs(
        self,
        *,
        label: str = '',
        state: str = 'open',
        head: str = '',
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List PRs via the REST API with optional filters.

        Note: GitHub REST API ``GET /pulls`` supports ``state`` and ``head``
        filters natively. Label filtering is done client-side.
        """
        # Map Forge states to GitHub API states.
        state_map = {
            'open': 'open',
            'closed': 'closed',
            'merged': 'closed',  # GitHub merges are a subset of closed.
            'all': 'all',
        }
        api_state = state_map.get(state, state)

        url = f'{self._repo_url}/pulls?state={api_state}&per_page={limit}'
        if head:
            # GitHub expects head in "owner:branch" format.
            url += f'&head={self._owner}:{head}'

        async with http_client(
            pool_size=self._pool_size,
            timeout=self._timeout,
            headers=self._headers,
        ) as client:
            response = await request_with_retry(client, 'GET', url)

        if response.status_code != 200:
            return []

        try:
            prs_data = response.json()
        except (ValueError, json.JSONDecodeError):
            log.warning('pr_list_parse_error')
            return []

        results: list[dict[str, Any]] = []
        for pr in prs_data:
            pr_labels = [lbl.get('name', '') for lbl in pr.get('labels', [])]

            # Post-filter by label.
            if label and label not in pr_labels:
                continue

            # Post-filter merged state (GitHub REST API doesn't distinguish).
            if state == 'merged' and not pr.get('merged_at'):
                continue

            results.append({
                'number': pr.get('number', 0),
                'title': pr.get('title', ''),
                'state': pr.get('state', ''),
                'url': pr.get('html_url', ''),
                'labels': pr_labels,
                'headRefName': pr.get('head', {}).get('ref', ''),
                'mergeCommit': {
                    'oid': pr.get('merge_commit_sha', ''),
                },
            })

        return results

    async def add_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Add labels to a PR (or issue) via the REST API."""
        url = f'{self._repo_url}/issues/{pr_number}/labels'
        if dry_run:
            log.info('dry_run_add_labels', pr=pr_number, labels=labels)
            return self._dry_run_result('POST', url)

        async with http_client(
            pool_size=self._pool_size,
            timeout=self._timeout,
            headers=self._headers,
        ) as client:
            response = await request_with_retry(
                client,
                'POST',
                url,
                json={'labels': labels},
            )

        log.info('add_labels', pr=pr_number, labels=labels, status=response.status_code)
        return CommandResult(
            command=['POST', url],
            return_code=0 if response.is_success else response.status_code,
            stdout=response.text,
            stderr='' if response.is_success else response.text,
        )

    async def remove_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Remove labels from a PR (or issue) via the REST API.

        GitHub REST API requires one DELETE per label.
        """
        if dry_run:
            log.info('dry_run_remove_labels', pr=pr_number, labels=labels)
            url = f'{self._repo_url}/issues/{pr_number}/labels'
            return self._dry_run_result('DELETE', url)

        last_result: CommandResult | None = None
        async with http_client(
            pool_size=self._pool_size,
            timeout=self._timeout,
            headers=self._headers,
        ) as client:
            for label_name in labels:
                url = f'{self._repo_url}/issues/{pr_number}/labels/{label_name}'
                response = await request_with_retry(client, 'DELETE', url)
                last_result = CommandResult(
                    command=['DELETE', url],
                    return_code=0 if response.is_success else response.status_code,
                    stdout='',
                    stderr='' if response.is_success else response.text,
                )
                log.info(
                    'remove_label',
                    pr=pr_number,
                    label=label_name,
                    status=response.status_code,
                )

        if last_result is None:
            return self._dry_run_result('DELETE', f'{self._repo_url}/issues/{pr_number}/labels')
        return last_result

    async def update_pr(
        self,
        pr_number: int,
        *,
        title: str = '',
        body: str = '',
        dry_run: bool = False,
    ) -> CommandResult:
        """Update a PR's title and/or body via the REST API."""
        url = f'{self._repo_url}/pulls/{pr_number}'
        if dry_run:
            log.info('dry_run_update_pr', pr=pr_number)
            return self._dry_run_result('PATCH', url)

        payload: dict[str, Any] = {}
        if title:
            payload['title'] = title
        if body:
            payload['body'] = body

        async with http_client(
            pool_size=self._pool_size,
            timeout=self._timeout,
            headers=self._headers,
        ) as client:
            response = await request_with_retry(client, 'PATCH', url, json=payload)

        log.info('update_pr', pr=pr_number, status=response.status_code)
        return CommandResult(
            command=['PATCH', url],
            return_code=0 if response.is_success else response.status_code,
            stdout=response.text,
            stderr='' if response.is_success else response.text,
        )

    async def merge_pr(
        self,
        pr_number: int,
        *,
        method: str = 'squash',
        commit_message: str = '',
        delete_branch: bool = True,
        dry_run: bool = False,
    ) -> CommandResult:
        """Merge a PR via the REST API.

        Uses ``PUT /repos/{owner}/{repo}/pulls/{pr_number}/merge``.
        After merging, optionally deletes the head branch.
        """
        url = f'{self._repo_url}/pulls/{pr_number}/merge'
        if dry_run:
            log.info('dry_run_merge_pr', pr=pr_number, method=method)
            return self._dry_run_result('PUT', url)

        payload: dict[str, Any] = {
            'merge_method': method,
        }
        if commit_message:
            payload['commit_title'] = commit_message

        async with http_client(
            pool_size=self._pool_size,
            timeout=self._timeout,
            headers=self._headers,
        ) as client:
            response = await request_with_retry(client, 'PUT', url, json=payload)

            # Optionally delete the head branch after merge.
            if response.is_success and delete_branch:
                pr_info = await request_with_retry(client, 'GET', f'{self._repo_url}/pulls/{pr_number}')
                if pr_info.is_success:
                    head_ref = pr_info.json().get('head', {}).get('ref', '')
                    if head_ref:
                        del_url = f'{self._repo_url}/git/refs/heads/{head_ref}'
                        await request_with_retry(client, 'DELETE', del_url)
                        log.info('deleted_branch', ref=head_ref)

        log.info('merge_pr', pr=pr_number, method=method, status=response.status_code)
        return CommandResult(
            command=['PUT', url],
            return_code=0 if response.is_success else response.status_code,
            stdout=response.text,
            stderr='' if response.is_success else response.text,
        )


__all__ = [
    'GitHubAPIBackend',
]
