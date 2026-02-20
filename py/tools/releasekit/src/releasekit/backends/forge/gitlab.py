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

"""GitLab forge backend for releasekit.

Implements the :class:`~releasekit.backends.forge.Forge` protocol using
the ``glab`` CLI. This backend validates that the Forge protocol is
generic enough to support forges beyond GitHub.

Usage::

    from releasekit.backends.forge.gitlab import GitLabCLIBackend

    forge = GitLabCLIBackend(project='firebase/genkit', cwd=Path('.'))
    if await forge.is_available():
        await forge.create_release('v1.0.0', title='Release v1.0.0')
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from releasekit.backends._run import CommandResult, run_command
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.forge.gitlab')


class GitLabCLIBackend:
    """Forge implementation using the ``glab`` CLI.

    Demonstrates that the :class:`~releasekit.backends.forge.Forge`
    protocol works beyond GitHub. Maps Forge operations to GitLab
    equivalents.

    Terminology mapping:

    ============================  =========================
    Forge (generic)               GitLab
    ============================  =========================
    Release                       Release
    Pull Request (PR)             Merge Request (MR)
    label                         label
    draft                         (no draft releases)
    ============================  =========================

    Args:
        project: GitLab project path (e.g., ``"firebase/genkit"``).
        cwd: Working directory for ``glab`` commands.
    """

    def __init__(self, project: str, cwd: Path) -> None:
        """Initialize with project path and working directory."""
        self._project = project
        self._cwd = cwd

    def _glab(self, *args: str, dry_run: bool = False, check: bool = False) -> CommandResult:
        """Run a glab command synchronously (called via to_thread)."""
        return run_command(
            ['glab', *args, '--repo', self._project],
            cwd=self._cwd,
            dry_run=dry_run,
            check=check,
        )

    async def is_available(self) -> bool:
        """Check if ``glab`` is installed and authenticated."""
        if shutil.which('glab') is None:
            log.warning('glab_not_found', hint='Install glab: https://gitlab.com/gitlab-org/cli')
            return False

        result = await asyncio.to_thread(
            run_command,
            ['glab', 'auth', 'status'],
            cwd=self._cwd,
        )
        if not result.ok:
            log.warning('glab_not_authenticated', hint="Run 'glab auth login'")
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
        """Create a GitLab Release."""
        cmd_parts = ['release', 'create', tag]
        if title:
            cmd_parts.extend(['--name', title])
        if body:
            cmd_parts.extend(['--notes', body])

        # GitLab doesn't support draft releases natively.
        if draft:
            log.warning('gitlab_no_draft', hint='GitLab does not support draft releases')
        if prerelease:
            # glab release create does not have a --prerelease flag;
            # this is a protocol difference we document but don't fail on.
            log.info('gitlab_prerelease_ignored', tag=tag)
        if assets:
            for asset in assets:
                cmd_parts.extend(['--assets-links', f'{{"name":"{asset.name}","url":"file://{asset}"}}'])

        log.info('create_release', tag=tag, draft=draft)
        return await asyncio.to_thread(self._glab, *cmd_parts, dry_run=dry_run)

    async def delete_release(
        self,
        tag: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Delete a GitLab Release by tag."""
        log.info('delete_release', tag=tag)
        return await asyncio.to_thread(self._glab, 'release', 'delete', tag, '--yes', dry_run=dry_run)

    async def promote_release(
        self,
        tag: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Promote a release (no-op on GitLab, no draft concept)."""
        log.warning('gitlab_promote_noop', tag=tag, hint='GitLab has no draft releases')
        return CommandResult(
            command=['glab', 'release', 'edit', tag, '(no-op)'],
            return_code=0,
            stdout='',
            stderr='',
            dry_run=dry_run,
        )

    async def list_releases(
        self,
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List recent GitLab Releases."""
        result = await asyncio.to_thread(
            self._glab,
            'release',
            'list',
            '--per-page',
            str(limit),
        )
        if not result.ok:
            return []

        # glab outputs text, not JSON by default. Parse line-by-line.
        releases = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                releases.append({
                    'tag': line.strip(),
                    'title': line.strip(),
                    'draft': False,
                    'prerelease': False,
                })
        return releases

    async def create_pr(
        self,
        *,
        title: str,
        body: str = '',
        head: str,
        base: str = 'main',
        dry_run: bool = False,
    ) -> CommandResult:
        """Create a GitLab Merge Request."""
        cmd_parts = [
            'mr',
            'create',
            '--title',
            title,
            '--source-branch',
            head,
            '--target-branch',
            base,
            '--remove-source-branch',
        ]
        log.info('create_mr', title=title, head=head, base=base)
        if body:
            # Use a temp file to avoid shell argument size limits with large
            # MR descriptions (e.g. 60+ package changelogs + embedded manifest).
            body_file = ''
            try:
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.md',
                    delete=False,
                    encoding='utf-8',
                ) as f:
                    body_file = f.name
                    f.write(body)
                cmd_parts.extend(['--description', f'@{body_file}'])
                return await asyncio.to_thread(self._glab, *cmd_parts, dry_run=dry_run)
            finally:
                if body_file:
                    os.unlink(body_file)  # noqa: PTH108
        return await asyncio.to_thread(self._glab, *cmd_parts, dry_run=dry_run)

    async def pr_data(self, pr_number: int) -> dict[str, Any]:
        """Fetch MR data as a dict."""
        result = await asyncio.to_thread(
            self._glab,
            'mr',
            'view',
            str(pr_number),
            '--output',
            'json',
        )
        if not result.ok:
            return {}

        try:
            data = json.loads(result.stdout)
            # Normalize to Forge protocol keys.
            return {
                'title': data.get('title', ''),
                'body': data.get('description', ''),
                'author': data.get('author', {}).get('username', ''),
                'labels': data.get('labels', []),
                'state': data.get('state', ''),
                'mergedAt': data.get('merged_at', ''),
                'headRefName': data.get('source_branch', ''),
                'mergeCommit': {'oid': data.get('merge_commit_sha', '')},
            }
        except json.JSONDecodeError:
            log.warning('mr_data_parse_error', mr=pr_number)
            return {}

    async def list_prs(
        self,
        *,
        label: str = '',
        state: str = 'open',
        head: str = '',
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List MRs matching the given filters.

        ``glab mr list`` uses separate boolean flags for state filtering
        rather than a ``--state`` parameter:

        - (default): open MRs only
        - ``--closed``: closed MRs only
        - ``--merged``: merged MRs only
        - ``--all``: all MRs regardless of state
        """
        cmd_parts = [
            'mr',
            'list',
            '--per-page',
            str(limit),
            '--output',
            'json',
        ]

        # glab uses boolean flags, not --state.
        if state == 'closed':
            cmd_parts.append('--closed')
        elif state == 'merged':
            cmd_parts.append('--merged')
        elif state == 'all':
            cmd_parts.append('--all')
        # 'open' is the default — no flag needed.

        if label:
            cmd_parts.extend(['--label', label])
        if head:
            cmd_parts.extend(['--source-branch', head])

        result = await asyncio.to_thread(self._glab, *cmd_parts)
        if not result.ok:
            return []

        try:
            mrs = json.loads(result.stdout)
            return [
                {
                    'number': mr.get('iid', 0),
                    'title': mr.get('title', ''),
                    'state': mr.get('state', ''),
                    'url': mr.get('web_url', ''),
                    'labels': mr.get('labels', []),
                    'headRefName': mr.get('source_branch', ''),
                    'mergeCommit': {'oid': mr.get('merge_commit_sha', '')},
                }
                for mr in mrs
            ]
        except json.JSONDecodeError:
            log.warning('mr_list_parse_error', stdout=result.stdout[:200])
            return []

    async def add_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Add labels to an MR."""
        cmd_parts = ['mr', 'update', str(pr_number)]
        cmd_parts.extend(['--label', ','.join(labels)])

        log.info('add_labels', mr=pr_number, labels=labels)
        return await asyncio.to_thread(self._glab, *cmd_parts, dry_run=dry_run)

    async def remove_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Remove labels from an MR."""
        cmd_parts = ['mr', 'update', str(pr_number)]
        cmd_parts.extend(['--unlabel', ','.join(labels)])

        log.info('remove_labels', mr=pr_number, labels=labels)
        return await asyncio.to_thread(self._glab, *cmd_parts, dry_run=dry_run)

    async def update_pr(
        self,
        pr_number: int,
        *,
        title: str = '',
        body: str = '',
        dry_run: bool = False,
    ) -> CommandResult:
        """Update an MR's title and/or description."""
        cmd_parts = ['mr', 'update', str(pr_number)]
        if title:
            cmd_parts.extend(['--title', title])
        if body:
            cmd_parts.extend(['--description', body])

        log.info('update_mr', mr=pr_number, has_title=bool(title), has_body=bool(body))
        return await asyncio.to_thread(self._glab, *cmd_parts, dry_run=dry_run)

    async def merge_pr(
        self,
        pr_number: int,
        *,
        method: str = 'squash',
        commit_message: str = '',
        delete_branch: bool = True,
        dry_run: bool = False,
    ) -> CommandResult:
        """Merge an MR via ``glab mr merge``."""
        cmd_parts = ['mr', 'merge', str(pr_number), '--yes']
        if method == 'squash':
            cmd_parts.append('--squash')
        if delete_branch:
            cmd_parts.append('--remove-source-branch')
        if commit_message:
            cmd_parts.extend(['--message', commit_message])

        log.info('merge_mr', mr=pr_number, method=method)
        return await asyncio.to_thread(self._glab, *cmd_parts, dry_run=dry_run)


__all__ = [
    'GitLabCLIBackend',
]
