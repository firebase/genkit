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

"""Bitbucket forge backend for releasekit.

Implements the :class:`~releasekit.backends.forge.Forge` protocol using
the Bitbucket REST API v2.0 via ``httpx``. This is the third Forge
backend and the first to use a REST API instead of a CLI tool,
validating that the protocol is transport-agnostic.

Authentication:

    Bitbucket supports three authentication methods. The backend
    resolves them in order of precedence:

    1. **Workspace/repo access token** (``token`` parameter or
       ``BITBUCKET_TOKEN`` env var) — scoped Bearer token, no user
       identity required. Best for CI.
    2. **App password** (``username`` + ``app_password`` parameters, or
       ``BITBUCKET_USERNAME`` + ``BITBUCKET_APP_PASSWORD`` env vars) —
       HTTP Basic auth tied to a user account.
    3. If neither is provided, the backend raises ``ValueError`` at
       construction time rather than failing silently at runtime.

Terminology mapping:

    ============================  =========================
    Forge (generic)               Bitbucket
    ============================  =========================
    Release                       (no native releases; uses tags + downloads)
    Pull Request (PR)             Pull Request (PR)
    label                         (no labels; simulated via PR title prefix)
    draft                         (no draft releases)
    prerelease                    (no prerelease concept)
    ============================  =========================

Usage::

    from releasekit.backends.forge.bitbucket import BitbucketAPIBackend

    forge = BitbucketAPIBackend(
        workspace='myteam',
        repo_slug='genkit',
        token='ATBBxyz...',
    )
    await forge.create_release('v1.0.0', title='Release v1.0.0')

.. seealso::

    `Bitbucket REST API v2.0 <https://developer.atlassian.com/cloud/bitbucket/rest/intro/>`_
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from releasekit.backends._run import CommandResult
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.forge.bitbucket')

# Bitbucket API base URL.
_DEFAULT_BASE_URL = 'https://api.bitbucket.org/2.0'


class BitbucketAPIBackend:
    """Forge implementation using the Bitbucket REST API v2.0.

    The third Forge backend — validates that the protocol works with
    direct HTTP calls, not just CLI wrappers.

    Key differences from GitHub/GitLab:

    - **No native releases**: Bitbucket has tags and downloads, but no
      "Release" object. ``create_release`` creates an annotated tag.
    - **No labels on PRs**: Bitbucket PRs don't support labels. The
      ``add_labels`` / ``remove_labels`` methods are no-ops that log
      a warning. Workflows needing label-like state should use PR
      title prefixes (e.g. ``[autorelease: pending]``) or custom
      PR properties.
    - **No draft releases**: ``draft`` and ``prerelease`` flags are
      silently ignored.

    Args:
        workspace: Bitbucket workspace slug (e.g., ``"myteam"``).
        repo_slug: Repository slug (e.g., ``"genkit"``).
        token: Workspace or repository access token (Bearer auth).
            Falls back to ``BITBUCKET_TOKEN`` env var.
        username: Bitbucket username for app password auth.
            Falls back to ``BITBUCKET_USERNAME`` env var.
        app_password: Bitbucket app password.
            Falls back to ``BITBUCKET_APP_PASSWORD`` env var.
        base_url: API base URL (override for Bitbucket Server / Data Center).
    """

    def __init__(
        self,
        workspace: str,
        repo_slug: str,
        *,
        token: str = '',
        username: str = '',
        app_password: str = '',
        base_url: str = _DEFAULT_BASE_URL,
    ) -> None:
        """Initialize with workspace, repo, and credentials."""
        self._workspace = workspace
        self._repo_slug = repo_slug
        self._base_url = base_url.rstrip('/')
        self._repo_url = f'{self._base_url}/repositories/{workspace}/{repo_slug}'

        # Resolve auth: token > app password > env vars.
        resolved_token = token or os.environ.get('BITBUCKET_TOKEN', '')
        resolved_user = username or os.environ.get('BITBUCKET_USERNAME', '')
        resolved_pass = app_password or os.environ.get('BITBUCKET_APP_PASSWORD', '')

        if resolved_token:
            self._auth: httpx.Auth | None = None
            self._headers = {
                'Authorization': f'Bearer {resolved_token}',
                'Content-Type': 'application/json',
            }
        elif resolved_user and resolved_pass:
            self._auth = httpx.BasicAuth(resolved_user, resolved_pass)
            self._headers = {'Content-Type': 'application/json'}
        else:
            msg = (
                'Bitbucket auth required: set token= or '
                '(username= + app_password=), or set BITBUCKET_TOKEN '
                'or (BITBUCKET_USERNAME + BITBUCKET_APP_PASSWORD) env vars.'
            )
            raise ValueError(msg)

        self._client: httpx.AsyncClient | None = None

    def __repr__(self) -> str:
        """Return a safe repr that never exposes credentials."""
        return f'BitbucketAPIBackend(workspace={self._workspace!r}, repo_slug={self._repo_slug!r})'

    def _dry_run_result(self, method: str, url: str) -> CommandResult:
        """Create a synthetic CommandResult for dry-run mode."""
        return CommandResult(
            command=[method, url],
            return_code=0,
            stdout='',
            stderr='',
            dry_run=True,
        )

    def _get_client(self) -> httpx.AsyncClient:
        """Return a lazily-created httpx client for connection pooling.

        The client is NOT created in ``__init__`` because ``httpx.AsyncClient``
        is bound to the event loop it is first used on. Creating it at init
        time causes "bound to a different event loop" errors when the instance
        is later used from a different loop (e.g. in tests).
        """
        if self._client is None:
            self._client = httpx.AsyncClient(auth=self._auth, headers=self._headers)
        return self._client

    async def _request(
        self,
        method: str,
        url: str,
        *,
        json_data: dict[str, Any] | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Make an authenticated HTTP request to the Bitbucket API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            url: Full URL to request.
            json_data: JSON body for POST/PUT requests.
            dry_run: Return synthetic success without making the request.
        """
        if dry_run:
            log.info('dry_run_request', method=method, url=url)
            return self._dry_run_result(method, url)

        client = self._get_client()
        response = await client.request(method, url, json=json_data)

        return CommandResult(
            command=[method, url],
            return_code=0 if response.is_success else response.status_code,
            stdout=response.text,
            stderr='' if response.is_success else response.text,
        )

    async def is_available(self) -> bool:
        """Check if the Bitbucket API is reachable and authenticated."""
        result = await self._request('GET', f'{self._repo_url}')
        if not result.ok:
            log.warning(
                'bitbucket_not_available',
                status=result.return_code,
                hint='Check BITBUCKET_TOKEN or BITBUCKET_USERNAME + BITBUCKET_APP_PASSWORD',
            )
        return result.ok

    async def create_release(
        self,
        tag: str,
        *,
        title: str | None = None,
        body: str = '',
        draft: bool = False,
        prerelease: bool = False,
        assets: list[Any] | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Create a tag (Bitbucket has no Release object).

        Resolves the default branch HEAD commit hash first, since the
        Bitbucket API requires an actual hash in ``target.hash`` —
        the string ``"HEAD"`` is not recognized.

        The ``title``, ``draft``, and ``prerelease`` parameters are
        accepted for protocol compatibility but have no effect.
        """
        if draft:
            log.warning('bitbucket_no_drafts', hint='Bitbucket has no draft releases')
        if prerelease:
            log.info('bitbucket_prerelease_ignored', tag=tag)

        # Resolve the default branch HEAD hash — Bitbucket API requires
        # an actual commit hash, not "HEAD".
        target_hash = await self._resolve_default_branch_head()

        url = f'{self._repo_url}/refs/tags'
        payload: dict[str, Any] = {
            'name': tag,
            'target': {'hash': target_hash},
        }
        if body:
            payload['message'] = body

        log.info('create_release', tag=tag, target=target_hash[:12])
        return await self._request('POST', url, json_data=payload, dry_run=dry_run)

    async def _resolve_default_branch_head(self) -> str:
        """Resolve the commit hash of the default branch HEAD.

        Fetches the repository metadata to find the default branch name,
        then fetches that branch's latest commit hash. Falls back to
        ``"main"`` if the default branch cannot be determined.
        """
        # Step 1: Get the default branch name from repository metadata.
        repo_result = await self._request('GET', self._repo_url)
        default_branch = 'main'
        if repo_result.ok:
            try:
                repo_data = json.loads(repo_result.stdout)
                default_branch = repo_data.get('mainbranch', {}).get('name', 'main')
            except json.JSONDecodeError:
                pass

        # Step 2: Get the latest commit hash of that branch.
        branch_url = f'{self._repo_url}/refs/branches/{default_branch}'
        branch_result = await self._request('GET', branch_url)
        if branch_result.ok:
            try:
                branch_data = json.loads(branch_result.stdout)
                commit_hash = branch_data.get('target', {}).get('hash', '')
                if commit_hash:
                    return commit_hash
            except json.JSONDecodeError:
                pass

        log.warning(
            'default_branch_head_fallback',
            branch=default_branch,
            hint='Could not resolve HEAD hash; tag creation may fail',
        )
        return default_branch

    async def delete_release(
        self,
        tag: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Delete a tag."""
        url = f'{self._repo_url}/refs/tags/{tag}'
        log.info('delete_release', tag=tag)
        return await self._request('DELETE', url, dry_run=dry_run)

    async def promote_release(
        self,
        tag: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Promote a release (no-op — Bitbucket has no draft concept)."""
        log.warning('bitbucket_promote_noop', tag=tag, hint='Bitbucket has no draft releases')
        return self._dry_run_result('PUT', f'{self._repo_url}/refs/tags/{tag}')

    async def list_releases(
        self,
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List recent tags (Bitbucket's closest equivalent to releases)."""
        url = f'{self._repo_url}/refs/tags?pagelen={limit}&sort=-name'
        result = await self._request('GET', url)
        if not result.ok:
            return []

        try:
            data = json.loads(result.stdout)
            return [
                {
                    'tag': tag.get('name', ''),
                    'title': tag.get('name', ''),
                    'draft': False,
                    'prerelease': False,
                }
                for tag in data.get('values', [])
            ]
        except json.JSONDecodeError:
            log.warning('tag_list_parse_error')
            return []

    async def create_pr(
        self,
        *,
        title: str,
        body: str = '',
        head: str,
        base: str = 'main',
        dry_run: bool = False,
    ) -> CommandResult:
        """Create a Bitbucket Pull Request."""
        url = f'{self._repo_url}/pullrequests'
        payload: dict[str, Any] = {
            'title': title,
            'source': {'branch': {'name': head}},
            'destination': {'branch': {'name': base}},
            'close_source_branch': True,
        }
        if body:
            payload['description'] = body

        log.info('create_pr', title=title, head=head, base=base)
        return await self._request('POST', url, json_data=payload, dry_run=dry_run)

    async def pr_data(self, pr_number: int) -> dict[str, Any]:
        """Fetch PR data and normalize to Forge contract keys."""
        url = f'{self._repo_url}/pullrequests/{pr_number}'
        result = await self._request('GET', url)
        if not result.ok:
            return {}

        try:
            data = json.loads(result.stdout)
            return {
                'title': data.get('title', ''),
                'body': data.get('description', ''),
                'author': data.get('author', {}).get('display_name', ''),
                'labels': [],  # Bitbucket PRs don't have labels.
                'state': data.get('state', '').lower(),
                'mergedAt': data.get('updated_on', ''),
                'headRefName': data.get('source', {}).get('branch', {}).get('name', ''),
                'mergeCommit': {
                    'oid': data.get('merge_commit', {}).get('hash', ''),
                },
            }
        except json.JSONDecodeError:
            log.warning('pr_data_parse_error', pr=pr_number)
            return {}

    async def list_prs(
        self,
        *,
        label: str = '',
        state: str = 'open',
        head: str = '',
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List PRs matching the given filters.

        Bitbucket doesn't support label filtering natively. If ``label``
        is provided, results are post-filtered by title prefix match.
        """
        # Map Forge states to Bitbucket states.
        state_map = {
            'open': 'OPEN',
            'closed': 'DECLINED',
            'merged': 'MERGED',
            'all': '',
        }
        bb_state = state_map.get(state, state.upper())

        url = f'{self._repo_url}/pullrequests?pagelen={limit}'
        if bb_state:
            url += f'&state={bb_state}'

        result = await self._request('GET', url)
        if not result.ok:
            return []

        try:
            data = json.loads(result.stdout)
            prs = []
            for pr in data.get('values', []):
                pr_title = pr.get('title', '')
                source_branch = pr.get('source', {}).get('branch', {}).get('name', '')

                # Post-filter by head branch if specified.
                if head and source_branch != head:
                    continue

                # Post-filter by label (simulated via title prefix).
                if label and f'[{label}]' not in pr_title:
                    continue

                prs.append({
                    'number': pr.get('id', 0),
                    'title': pr_title,
                    'state': pr.get('state', '').lower(),
                    'url': pr.get('links', {}).get('html', {}).get('href', ''),
                    'labels': [],  # Bitbucket PRs don't have labels.
                    'headRefName': source_branch,
                    'mergeCommit': {
                        'oid': pr.get('merge_commit', {}).get('hash', ''),
                    },
                })
            return prs
        except json.JSONDecodeError:
            log.warning('pr_list_parse_error')
            return []

    async def add_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Add labels to a PR (no-op — Bitbucket PRs have no labels).

        Logs a warning. Workflows needing label-based state on Bitbucket
        should use PR title prefixes (e.g. ``[autorelease: pending]``)
        via ``update_pr(title=...)`` instead.
        """
        log.warning(
            'bitbucket_no_labels',
            pr=pr_number,
            labels=labels,
            hint='Use update_pr(title=...) with title prefixes instead',
        )
        url = f'{self._repo_url}/pullrequests/{pr_number}'
        return self._dry_run_result('PUT', url)

    async def remove_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Remove labels from a PR (no-op — Bitbucket PRs have no labels)."""
        log.warning(
            'bitbucket_no_labels',
            pr=pr_number,
            labels=labels,
            hint='Use update_pr(title=...) with title prefixes instead',
        )
        url = f'{self._repo_url}/pullrequests/{pr_number}'
        return self._dry_run_result('PUT', url)

    async def update_pr(
        self,
        pr_number: int,
        *,
        title: str = '',
        body: str = '',
        dry_run: bool = False,
    ) -> CommandResult:
        """Update a PR's title and/or description."""
        url = f'{self._repo_url}/pullrequests/{pr_number}'
        payload: dict[str, Any] = {}
        if title:
            payload['title'] = title
        if body:
            payload['description'] = body

        log.info('update_pr', pr=pr_number, has_title=bool(title), has_body=bool(body))
        return await self._request('PUT', url, json_data=payload, dry_run=dry_run)

    async def merge_pr(
        self,
        pr_number: int,
        *,
        method: str = 'squash',
        commit_message: str = '',
        delete_branch: bool = True,
        dry_run: bool = False,
    ) -> CommandResult:
        """Merge a PR via the Bitbucket REST API.

        Uses ``POST /pullrequests/{id}/merge``.  Bitbucket uses
        ``merge_strategy`` with values ``"squash"``, ``"merge_commit"``,
        or ``"fast_forward"``.
        """
        url = f'{self._repo_url}/pullrequests/{pr_number}/merge'

        # Map Forge method names to Bitbucket strategy names.
        strategy_map = {
            'squash': 'squash',
            'merge': 'merge_commit',
            'rebase': 'fast_forward',
        }
        strategy = strategy_map.get(method, 'squash')

        payload: dict[str, Any] = {
            'merge_strategy': strategy,
            'close_source_branch': delete_branch,
        }
        if commit_message:
            payload['message'] = commit_message

        log.info('merge_pr', pr=pr_number, strategy=strategy)
        return await self._request('POST', url, json_data=payload, dry_run=dry_run)


__all__ = [
    'BitbucketAPIBackend',
]
