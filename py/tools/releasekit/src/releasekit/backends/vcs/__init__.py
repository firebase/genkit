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

"""VCS protocol for releasekit.

The :class:`VCS` protocol defines the interface for version control
operations (commit, tag, push, log). Implementations:

- :class:`~releasekit.backends.vcs.git.GitCLIBackend` — ``git`` CLI
- :class:`~releasekit.backends.vcs.mercurial.MercurialBackend` — ``hg`` CLI
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from releasekit.backends._run import CommandResult
from releasekit.backends.vcs.git import GitCLIBackend as GitCLIBackend

__all__ = [
    'GitCLIBackend',
    'VCS',
]


@runtime_checkable
class VCS(Protocol):
    """Protocol for version control operations.

    All methods are async to avoid blocking the event loop when
    shelling out to ``git`` or other VCS tools.
    """

    async def is_clean(self, *, dry_run: bool = False) -> bool:
        """Return ``True`` if the working tree is clean.

        Args:
            dry_run: Always return ``True`` without checking.
        """
        ...

    async def is_shallow(self) -> bool:
        """Return ``True`` if the repository is a shallow clone."""
        ...

    async def default_branch(self) -> str:
        """Return the name of the default (trunk) branch.

        Auto-detects the default branch from the VCS configuration.
        For Git, this queries ``refs/remotes/origin/HEAD``. For
        Mercurial, the default branch is typically ``"default"``.

        Returns:
            The branch name (e.g. ``"main"``, ``"master"``, ``"develop"``).
        """
        ...

    async def current_sha(self) -> str:
        """Return the current HEAD commit SHA."""
        ...

    async def log(
        self,
        *,
        since_tag: str | None = None,
        paths: list[str] | None = None,
        format: str = '%H %s',
        first_parent: bool = False,
        no_merges: bool = False,
        max_commits: int = 0,
    ) -> list[str]:
        """Return log entry lines.

        Args:
            since_tag: Only include commits after this tag.
            paths: Restrict to commits touching these paths.
            format: Log format string (git ``--pretty=format:``).
            first_parent: If True, follow only the first parent of
                merge commits. Prevents duplicate entries when merge
                commits repeat the squashed commit message.
            no_merges: If True, exclude merge commits entirely.
                Prevents accidental merge commits in trunk-based
                workflows from being parsed as conventional commits.
            max_commits: Maximum number of commits to return. 0 means
                no limit. Useful for large repos where scanning the
                entire history is expensive.
        """
        ...

    async def diff_files(self, *, since_tag: str | None = None) -> list[str]:
        """Return list of files changed since a tag.

        Args:
            since_tag: Tag to diff against. If ``None``, uses the
                most recent tag.
        """
        ...

    async def commit(
        self,
        message: str,
        *,
        paths: list[str] | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Create a commit, staging specified paths first.

        Args:
            message: Commit message.
            paths: Specific paths to stage. If ``None``, stages all.
            dry_run: Log the command without executing.
        """
        ...

    async def tag(
        self,
        tag_name: str,
        *,
        message: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Create an annotated tag.

        Args:
            tag_name: Tag name (e.g. ``"genkit-v0.5.0"``).
            message: Tag message. Defaults to the tag name.
            dry_run: Log the command without executing.
        """
        ...

    async def tag_exists(self, tag_name: str) -> bool:
        """Return ``True`` if the tag exists.

        Args:
            tag_name: Tag name to check.
        """
        ...

    async def delete_tag(
        self,
        tag_name: str,
        *,
        remote: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """Delete a tag locally and optionally on the remote.

        Args:
            tag_name: Tag to delete.
            remote: Also delete the remote tag.
            dry_run: Log the command without executing.
        """
        ...

    async def push(
        self,
        *,
        tags: bool = False,
        remote: str = 'origin',
        set_upstream: bool = True,
        dry_run: bool = False,
    ) -> CommandResult:
        """Push commits and/or tags.

        Args:
            tags: Also push tags.
            remote: Remote name.
            set_upstream: Set upstream tracking for new branches.
            dry_run: Log the command without executing.
        """
        ...

    async def list_tags(self, *, pattern: str = '') -> list[str]:
        """Return all tags, optionally filtered by a glob pattern.

        Args:
            pattern: Optional glob pattern to filter tags
                (e.g. ``"py/v*"``). Empty string means all tags.

        Returns:
            Sorted list of tag names.
        """
        ...

    async def tag_commit_sha(self, tag_name: str) -> str:
        """Return the commit SHA that a tag points to.

        For annotated tags, this dereferences to the underlying commit.
        For lightweight tags, this returns the tagged commit directly.

        Args:
            tag_name: Tag name to resolve.

        Returns:
            The full commit SHA, or an empty string if the tag does
            not exist.
        """
        ...

    async def current_branch(self) -> str:
        """Return the name of the currently checked-out branch.

        Returns:
            Branch name (e.g. ``"main"``), or an empty string if
            in detached HEAD state.
        """
        ...

    async def checkout_branch(
        self,
        branch: str,
        *,
        create: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """Switch to a branch, optionally creating it.

        Args:
            branch: Branch name.
            create: Create the branch if it doesn't exist.
            dry_run: Log the command without executing.
        """
        ...

    async def tags_on_branch(self, branch: str) -> list[str]:
        """Return tags reachable from a branch, in chronological order.

        Args:
            branch: Branch name to scan for tags.

        Returns:
            List of tag names, oldest first.
        """
        ...

    async def commit_exists(self, sha: str) -> bool:
        """Return ``True`` if the commit SHA exists in the repository.

        Args:
            sha: Full or abbreviated commit SHA.
        """
        ...

    async def cherry_pick(
        self,
        sha: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Cherry-pick a single commit onto the current branch.

        Args:
            sha: Commit SHA to cherry-pick.
            dry_run: Log the command without executing.
        """
        ...

    async def cherry_pick_abort(self) -> CommandResult:
        """Abort an in-progress cherry-pick operation."""
        ...

    async def tag_date(self, tag_name: str) -> str:
        """Return the ISO 8601 date of a tag.

        Args:
            tag_name: Tag name to query.

        Returns:
            ISO 8601 date string, or empty string if the tag
            does not exist.
        """
        ...
