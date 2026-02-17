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

"""GitHub forge backend for releasekit.

The :class:`GitHubCLIBackend` implements the :class:`Forge` protocol
by delegating to the ``gh`` CLI tool.

All methods are async — blocking subprocess calls are dispatched to
``asyncio.to_thread()`` to avoid blocking the event loop.
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

log = get_logger('releasekit.backends.github')


class GitHubCLIBackend:
    """Default :class:`~releasekit.backends.forge.Forge` implementation using the ``gh`` CLI.

    All methods are async and delegate blocking subprocess calls to
    ``asyncio.to_thread()`` to avoid blocking the event loop.

    Args:
        repo: Repository in ``owner/name`` format (e.g., ``"firebase/genkit"``).
        cwd: Working directory for ``gh`` commands.
    """

    def __init__(self, repo: str, cwd: Path) -> None:
        """Initialize with repository slug and working directory."""
        self._repo = repo
        self._cwd = cwd

    def _gh(self, *args: str, dry_run: bool = False, check: bool = False) -> CommandResult:
        """Run a gh command synchronously (called via to_thread)."""
        return run_command(
            ['gh', *args, '--repo', self._repo],
            cwd=self._cwd,
            dry_run=dry_run,
            check=check,
        )

    async def is_available(self) -> bool:
        """Check if ``gh`` is installed and authenticated."""
        if shutil.which('gh') is None:
            log.warning('gh_not_found', hint='Install gh: https://cli.github.com/')
            return False

        result = await asyncio.to_thread(
            run_command,
            ['gh', 'auth', 'status'],
            cwd=self._cwd,
        )
        if not result.ok:
            log.warning('gh_not_authenticated', hint="Run 'gh auth login'")
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
        """Create a GitHub Release."""
        cmd_parts = ['release', 'create', tag]
        if title:
            cmd_parts.extend(['--title', title])
        if draft:
            cmd_parts.append('--draft')
        if prerelease:
            cmd_parts.append('--prerelease')
        if assets:
            for asset in assets:
                cmd_parts.append(str(asset))

        log.info('create_release', tag=tag, draft=draft)
        if body:
            # Use --notes-file to avoid shell argument size limits with large
            # release notes (e.g. 60+ package changelogs).
            notes_file = ''
            try:
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.md',
                    delete=False,
                    encoding='utf-8',
                ) as f:
                    notes_file = f.name
                    f.write(body)
                cmd_parts.extend(['--notes-file', notes_file])
                return await asyncio.to_thread(self._gh, *cmd_parts, dry_run=dry_run)
            finally:
                if notes_file:
                    os.unlink(notes_file)  # noqa: PTH108
        else:
            cmd_parts.append('--generate-notes')
            return await asyncio.to_thread(self._gh, *cmd_parts, dry_run=dry_run)

    async def delete_release(
        self,
        tag: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Delete a GitHub Release by tag."""
        log.info('delete_release', tag=tag)
        return await asyncio.to_thread(self._gh, 'release', 'delete', tag, '--yes', dry_run=dry_run)

    async def promote_release(
        self,
        tag: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Promote a draft release to published."""
        log.info('promote_release', tag=tag)
        return await asyncio.to_thread(
            self._gh,
            'release',
            'edit',
            tag,
            '--draft=false',
            dry_run=dry_run,
        )

    async def list_releases(
        self,
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List recent GitHub Releases."""
        result = await asyncio.to_thread(
            self._gh,
            'release',
            'list',
            '--limit',
            str(limit),
            '--json',
            'tagName,name,isDraft,isPrerelease',
        )
        if not result.ok:
            return []

        try:
            releases = json.loads(result.stdout)
        except json.JSONDecodeError:
            log.warning('release_list_parse_error', stdout=result.stdout[:200])
            return []

        return [
            {
                'tag': r.get('tagName', ''),
                'title': r.get('name', ''),
                'draft': r.get('isDraft', False),
                'prerelease': r.get('isPrerelease', False),
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
        """Create a GitHub Pull Request."""
        cmd_parts = ['pr', 'create', '--title', title, '--head', head, '--base', base]

        log.info('create_pr', title=title, head=head, base=base)
        if body:
            # Use --body-file to avoid shell argument size limits with large
            # PR bodies (e.g. 60+ package changelogs + embedded manifest).
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
                cmd_parts.extend(['--body-file', body_file])
                return await asyncio.to_thread(self._gh, *cmd_parts, dry_run=dry_run)
            finally:
                if body_file:
                    os.unlink(body_file)  # noqa: PTH108
        return await asyncio.to_thread(self._gh, *cmd_parts, dry_run=dry_run)

    async def pr_data(self, pr_number: int) -> dict[str, Any]:
        """Fetch PR data as a dict."""
        result = await asyncio.to_thread(
            self._gh,
            'pr',
            'view',
            str(pr_number),
            '--json',
            'title,body,author,labels,state,mergedAt,headRefName,mergeCommit',
        )
        if not result.ok:
            return {}

        try:
            return json.loads(result.stdout)
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
        """List PRs matching the given filters."""
        cmd_parts = [
            'pr',
            'list',
            '--state',
            state,
            '--limit',
            str(limit),
            '--json',
            'number,title,state,labels,headRefName,mergeCommit,url',
        ]
        if label:
            cmd_parts.extend(['--label', label])
        if head:
            cmd_parts.extend(['--head', head])

        result = await asyncio.to_thread(self._gh, *cmd_parts)
        if not result.ok:
            return []

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            log.warning('pr_list_parse_error', stdout=result.stdout[:200])
            return []

    async def add_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Add labels to a PR, creating any that don't exist.

        Uses ``gh label create --force`` which is a no-op for labels
        that already exist, then adds them to the PR.
        """
        # Ensure all labels exist before adding them to the PR.
        # gh pr edit --add-label fails if the label doesn't exist.
        await asyncio.gather(
            *(
                asyncio.to_thread(
                    self._gh,
                    'label',
                    'create',
                    label,
                    '--force',
                    dry_run=dry_run,
                )
                for label in labels
            )
        )

        cmd_parts = ['pr', 'edit', str(pr_number)]
        for label in labels:
            cmd_parts.extend(['--add-label', label])

        log.info('add_labels', pr=pr_number, labels=labels)
        return await asyncio.to_thread(self._gh, *cmd_parts, dry_run=dry_run)

    async def remove_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Remove labels from a PR."""
        cmd_parts = ['pr', 'edit', str(pr_number)]
        for label in labels:
            cmd_parts.extend(['--remove-label', label])

        log.info('remove_labels', pr=pr_number, labels=labels)
        return await asyncio.to_thread(self._gh, *cmd_parts, dry_run=dry_run)

    async def update_pr(
        self,
        pr_number: int,
        *,
        title: str = '',
        body: str = '',
        dry_run: bool = False,
    ) -> CommandResult:
        """Update a PR's title and/or body."""
        cmd_parts = ['pr', 'edit', str(pr_number)]
        if title:
            cmd_parts.extend(['--title', title])

        log.info('update_pr', pr=pr_number, has_title=bool(title), has_body=bool(body))
        if body:
            # Use --body-file to avoid shell argument size limits with large
            # PR bodies (e.g. 60+ package changelogs + embedded manifest).
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
                cmd_parts.extend(['--body-file', body_file])
                return await asyncio.to_thread(self._gh, *cmd_parts, dry_run=dry_run)
            finally:
                if body_file:
                    os.unlink(body_file)  # noqa: PTH108
        return await asyncio.to_thread(self._gh, *cmd_parts, dry_run=dry_run)

    async def merge_pr(
        self,
        pr_number: int,
        *,
        method: str = 'squash',
        commit_message: str = '',
        delete_branch: bool = True,
        dry_run: bool = False,
    ) -> CommandResult:
        """Merge a PR via ``gh pr merge``."""
        method_flag = f'--{method}'  # --squash, --merge, or --rebase
        cmd_parts = ['pr', 'merge', str(pr_number), method_flag, '--auto']
        if delete_branch:
            cmd_parts.append('--delete-branch')
        if commit_message:
            cmd_parts.extend(['--subject', commit_message])

        log.info('merge_pr', pr=pr_number, method=method)
        return await asyncio.to_thread(self._gh, *cmd_parts, dry_run=dry_run)


__all__ = [
    'GitHubCLIBackend',
]
