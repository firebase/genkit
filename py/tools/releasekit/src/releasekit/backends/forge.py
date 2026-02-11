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

"""Forge protocol and GitHub backend for releasekit.

The :class:`Forge` protocol defines the async interface for code forge
operations (GitHub Releases, PRs). The default implementation,
:class:`GitHubBackend`, delegates to the ``gh`` CLI.

Key design decision (D-10): if ``gh`` is not installed, the backend
degrades gracefully -- core publish works without it.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from releasekit.backends._run import CommandResult, run_command
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.forge')


@runtime_checkable
class Forge(Protocol):
    """Protocol for code forge operations (GitHub, GitLab, etc.).

    Operations that touch the network are async-ready by convention,
    but the ``gh`` CLI implementation runs synchronously under the hood.
    """

    def is_available(self) -> bool:
        """Return ``True`` if the forge CLI tool is installed and authenticated."""
        ...

    def create_release(
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
        """Create a release on the forge.

        Args:
            tag: Git tag for the release.
            title: Release title. Defaults to the tag name.
            body: Release body (markdown).
            draft: Create as a draft release.
            prerelease: Mark as a prerelease.
            assets: File paths to attach as release assets.
            dry_run: Log the command without executing.
        """
        ...

    def delete_release(
        self,
        tag: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Delete a release by its tag.

        Args:
            tag: Tag of the release to delete.
            dry_run: Log the command without executing.
        """
        ...

    def promote_release(
        self,
        tag: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Promote a draft release to published.

        Args:
            tag: Tag of the draft release to promote.
            dry_run: Log the command without executing.
        """
        ...

    def list_releases(
        self,
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List recent releases.

        Args:
            limit: Maximum number of releases to return.

        Returns:
            List of release dicts with keys: tag, title, draft, prerelease.
        """
        ...

    def create_pr(
        self,
        *,
        title: str,
        body: str = '',
        head: str,
        base: str = 'main',
        dry_run: bool = False,
    ) -> CommandResult:
        """Create a pull request.

        Args:
            title: PR title.
            body: PR body (markdown).
            head: Source branch.
            base: Target branch.
            dry_run: Log the command without executing.
        """
        ...

    def pr_data(self, pr_number: int) -> dict[str, Any]:
        """Fetch data about a pull request.

        Args:
            pr_number: PR number.

        Returns:
            Dict with PR metadata (title, body, author, labels, etc.).
        """
        ...


class GitHubBackend:
    """Default :class:`Forge` implementation using the ``gh`` CLI.

    Args:
        repo: Repository in ``owner/name`` format (e.g., ``"firebase/genkit"``).
        cwd: Working directory for ``gh`` commands.
    """

    def __init__(self, repo: str, cwd: Path) -> None:
        """Initialize with repository slug and working directory."""
        self._repo = repo
        self._cwd = cwd

    def _gh(self, *args: str, dry_run: bool = False, check: bool = False) -> CommandResult:
        """Run a gh command."""
        return run_command(
            ['gh', *args, '--repo', self._repo],
            cwd=self._cwd,
            dry_run=dry_run,
            check=check,
        )

    def is_available(self) -> bool:
        """Check if ``gh`` is installed and authenticated."""
        if shutil.which('gh') is None:
            log.warning('gh_not_found', hint='Install gh: https://cli.github.com/')
            return False

        result = run_command(['gh', 'auth', 'status'], cwd=self._cwd)
        if not result.ok:
            log.warning('gh_not_authenticated', hint="Run 'gh auth login'")
            return False

        return True

    def create_release(
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
        if body:
            cmd_parts.extend(['--notes', body])
        else:
            cmd_parts.append('--generate-notes')
        if draft:
            cmd_parts.append('--draft')
        if prerelease:
            cmd_parts.append('--prerelease')
        if assets:
            for asset in assets:
                cmd_parts.append(str(asset))

        log.info('create_release', tag=tag, draft=draft)
        return self._gh(*cmd_parts, dry_run=dry_run)

    def delete_release(
        self,
        tag: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Delete a GitHub Release by tag."""
        log.info('delete_release', tag=tag)
        return self._gh('release', 'delete', tag, '--yes', dry_run=dry_run)

    def promote_release(
        self,
        tag: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Promote a draft release to published."""
        log.info('promote_release', tag=tag)
        return self._gh('release', 'edit', tag, '--draft=false', dry_run=dry_run)

    def list_releases(
        self,
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List recent GitHub Releases."""
        result = self._gh(
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

    def create_pr(
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
        if body:
            cmd_parts.extend(['--body', body])

        log.info('create_pr', title=title, head=head, base=base)
        return self._gh(*cmd_parts, dry_run=dry_run)

    def pr_data(self, pr_number: int) -> dict[str, Any]:
        """Fetch PR data as a dict."""
        result = self._gh(
            'pr',
            'view',
            str(pr_number),
            '--json',
            'title,body,author,labels,state,mergedAt',
        )
        if not result.ok:
            return {}

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            log.warning('pr_data_parse_error', pr=pr_number)
            return {}


__all__ = [
    'Forge',
    'GitHubBackend',
]
