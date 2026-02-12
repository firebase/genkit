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

"""Forge protocol for releasekit.

The :class:`Forge` protocol defines the async interface for code forge
operations (GitHub Releases, PRs, labels). Implementations:

- :class:`~releasekit.backends.forge.github.GitHubCLIBackend` — ``gh`` CLI
- :class:`~releasekit.backends.forge.github_api.GitHubAPIBackend` — GitHub REST API
- :class:`~releasekit.backends.forge.gitlab.GitLabCLIBackend` — ``glab`` CLI
- :class:`~releasekit.backends.forge.bitbucket.BitbucketAPIBackend` — Bitbucket API

Key design decision (D-10): if the forge CLI is not installed, the
backend degrades gracefully — core publish works without it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from releasekit.backends._run import CommandResult
from releasekit.backends.forge.github import GitHubCLIBackend as GitHubCLIBackend
from releasekit.backends.forge.github_api import GitHubAPIBackend as GitHubAPIBackend

__all__ = [
    'Forge',
    'GitHubAPIBackend',
    'GitHubCLIBackend',
]


@runtime_checkable
class Forge(Protocol):
    """Protocol for code forge operations (GitHub, GitLab, etc.).

    All methods are async to avoid blocking the event loop when
    shelling out to ``gh`` or other forge CLI tools.
    """

    async def is_available(self) -> bool:
        """Return ``True`` if the forge CLI tool is installed and authenticated."""
        ...

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
        """Create a release on the forge.

        Args:
            tag: Git tag for the release.
            title: Release title. Defaults to the tag name.
            body: Release body (markdown).
            draft: Create as a draft release.
            prerelease: Mark as a pre-release.
            assets: Files to attach to the release.
            dry_run: Log the command without executing.
        """
        ...

    async def delete_release(
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

    async def promote_release(
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

    async def list_releases(
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

    async def create_pr(
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

    async def pr_data(self, pr_number: int) -> dict[str, Any]:
        """Fetch data about a pull request.

        Args:
            pr_number: PR number.

        Returns:
            Dict with PR metadata (title, body, author, labels, etc.).
        """
        ...

    async def list_prs(
        self,
        *,
        label: str = '',
        state: str = 'open',
        head: str = '',
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List pull requests matching the given filters.

        Args:
            label: Filter by label name (e.g. ``"autorelease: pending"``).
            state: PR state filter: ``"open"``, ``"closed"``, ``"merged"``,
                or ``"all"``.
            head: Filter by head branch name.
            limit: Maximum number of PRs to return.

        Returns:
            List of PR dicts with keys: number, title, state, labels,
            headRefName, mergeCommit.
        """
        ...

    async def add_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Add labels to a pull request.

        Args:
            pr_number: PR number.
            labels: Label names to add.
            dry_run: Log the command without executing.
        """
        ...

    async def remove_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Remove labels from a pull request.

        Args:
            pr_number: PR number.
            labels: Label names to remove.
            dry_run: Log the command without executing.
        """
        ...

    async def update_pr(
        self,
        pr_number: int,
        *,
        title: str = '',
        body: str = '',
        dry_run: bool = False,
    ) -> CommandResult:
        """Update an existing pull request's title and/or body.

        Args:
            pr_number: PR number to update.
            title: New title (empty string = no change).
            body: New body (empty string = no change).
            dry_run: Log the command without executing.
        """
        ...

    async def merge_pr(
        self,
        pr_number: int,
        *,
        method: str = 'squash',
        commit_message: str = '',
        delete_branch: bool = True,
        dry_run: bool = False,
    ) -> CommandResult:
        """Merge a pull request.

        Used by the automated release workflow to merge Release PRs
        without human intervention.

        Args:
            pr_number: PR number to merge.
            method: Merge method — ``"squash"``, ``"merge"``, or
                ``"rebase"``.
            commit_message: Custom merge commit message. Empty string
                uses the forge default.
            delete_branch: Delete the head branch after merging.
            dry_run: Log the command without executing.
        """
        ...
