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

"""VCS protocol and Git backend for releasekit.

The :class:`VCS` protocol defines the interface for version control
operations (commit, tag, push, log). The default implementation,
:class:`GitBackend`, delegates to ``git`` via :func:`run_command`.

All operations are synchronous because git is fast locally.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from releasekit.backends._run import CommandResult, run_command
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.vcs')


@runtime_checkable
class VCS(Protocol):
    """Protocol for version control operations."""

    def is_clean(self, *, dry_run: bool = False) -> bool:
        """Return ``True`` if the working tree has no uncommitted changes."""
        ...

    def is_shallow(self) -> bool:
        """Return ``True`` if the repository is a shallow clone."""
        ...

    def current_sha(self) -> str:
        """Return the current HEAD commit SHA."""
        ...

    def log(
        self,
        *,
        since_tag: str | None = None,
        paths: list[str] | None = None,
        format: str = '%H %s',
    ) -> list[str]:
        """Return git log lines.

        Args:
            since_tag: Only show commits after this tag.
            paths: Limit to changes in these paths.
            format: Git pretty-print format string.
        """
        ...

    def diff_files(self, *, since_tag: str | None = None) -> list[str]:
        """Return list of files changed since a tag.

        Args:
            since_tag: Compare against this tag. If ``None``, compare
                against the last tag.
        """
        ...

    def commit(
        self,
        message: str,
        *,
        paths: list[str] | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Create a commit.

        Args:
            message: Commit message.
            paths: Specific paths to add before committing. If ``None``,
                stages all changes.
            dry_run: Log the command without executing.
        """
        ...

    def tag(
        self,
        tag_name: str,
        *,
        message: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Create an annotated tag.

        Args:
            tag_name: Tag name (e.g., ``"py-v0.5.0"``).
            message: Tag annotation message. Defaults to the tag name.
            dry_run: Log the command without executing.
        """
        ...

    def tag_exists(self, tag_name: str) -> bool:
        """Return ``True`` if the tag exists locally or remotely."""
        ...

    def delete_tag(
        self,
        tag_name: str,
        *,
        remote: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """Delete a tag locally (and optionally on the remote).

        Args:
            tag_name: Tag name to delete.
            remote: Also delete from the remote.
            dry_run: Log the command without executing.
        """
        ...

    def push(
        self,
        *,
        tags: bool = False,
        remote: str = 'origin',
        dry_run: bool = False,
    ) -> CommandResult:
        """Push commits and/or tags to the remote.

        Args:
            tags: Also push tags.
            remote: Remote name.
            dry_run: Log the command without executing.
        """
        ...

    def checkout_branch(
        self,
        branch: str,
        *,
        create: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """Switch to a branch, optionally creating it.

        Args:
            branch: Branch name.
            create: If ``True``, create the branch first.
            dry_run: Log the command without executing.
        """
        ...


class GitBackend:
    """Default :class:`VCS` implementation using ``git``.

    Args:
        repo_root: Path to the git repository root.
    """

    def __init__(self, repo_root: Path) -> None:
        """Initialize with the git repository root path."""
        self._root = repo_root

    def _git(self, *args: str, dry_run: bool = False, check: bool = False) -> CommandResult:
        """Run a git command."""
        return run_command(['git', *args], cwd=self._root, dry_run=dry_run, check=check)

    def is_clean(self, *, dry_run: bool = False) -> bool:
        """Return ``True`` if the working tree is clean."""
        if dry_run:
            return True
        result = self._git('status', '--porcelain')
        return result.stdout.strip() == ''

    def is_shallow(self) -> bool:
        """Return ``True`` if the repository is a shallow clone."""
        result = self._git('rev-parse', '--is-shallow-repository')
        return result.stdout.strip() == 'true'

    def current_sha(self) -> str:
        """Return the current HEAD commit SHA."""
        result = self._git('rev-parse', 'HEAD', check=True)
        return result.stdout.strip()

    def log(
        self,
        *,
        since_tag: str | None = None,
        paths: list[str] | None = None,
        format: str = '%H %s',
    ) -> list[str]:
        """Return git log lines."""
        cmd_parts = ['log', f'--pretty=format:{format}']
        if since_tag:
            cmd_parts.append(f'{since_tag}..HEAD')
        if paths:
            cmd_parts.append('--')
            cmd_parts.extend(paths)
        result = self._git(*cmd_parts)
        if not result.stdout.strip():
            return []
        return result.stdout.strip().split('\n')

    def diff_files(self, *, since_tag: str | None = None) -> list[str]:
        """Return list of changed files since a tag."""
        if since_tag:
            result = self._git('diff', '--name-only', f'{since_tag}..HEAD')
        else:
            # Find the most recent tag and diff against it.
            tag_result = self._git('describe', '--tags', '--abbrev=0')
            if not tag_result.ok:
                return []
            last_tag = tag_result.stdout.strip()
            result = self._git('diff', '--name-only', f'{last_tag}..HEAD')

        if not result.stdout.strip():
            return []
        return result.stdout.strip().split('\n')

    def commit(
        self,
        message: str,
        *,
        paths: list[str] | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Create a commit, staging specified paths first."""
        if paths and not dry_run:
            self._git('add', *paths)
        else:
            self._git('add', '-A', dry_run=dry_run)

        log.info('commit', message=message[:80])
        return self._git('commit', '-m', message, dry_run=dry_run)

    def tag(
        self,
        tag_name: str,
        *,
        message: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Create an annotated tag."""
        tag_message = message or tag_name
        log.info('tag', tag=tag_name)
        return self._git('tag', '-a', tag_name, '-m', tag_message, dry_run=dry_run)

    def tag_exists(self, tag_name: str) -> bool:
        """Return ``True`` if the tag exists."""
        result = self._git('tag', '-l', tag_name)
        return result.stdout.strip() == tag_name

    def delete_tag(
        self,
        tag_name: str,
        *,
        remote: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """Delete a tag locally and optionally on the remote."""
        result = self._git('tag', '-d', tag_name, dry_run=dry_run)
        if remote and result.ok:
            self._git('push', 'origin', f':refs/tags/{tag_name}', dry_run=dry_run)
        return result

    def push(
        self,
        *,
        tags: bool = False,
        remote: str = 'origin',
        dry_run: bool = False,
    ) -> CommandResult:
        """Push commits and/or tags."""
        cmd_parts = ['push', remote]
        if tags:
            cmd_parts.append('--tags')
        log.info('push', remote=remote, tags=tags)
        return self._git(*cmd_parts, dry_run=dry_run)

    def checkout_branch(
        self,
        branch: str,
        *,
        create: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """Switch to a branch, optionally creating it."""
        if create:
            log.info('checkout_branch_create', branch=branch)
            return self._git('checkout', '-b', branch, dry_run=dry_run)
        log.info('checkout_branch', branch=branch)
        return self._git('checkout', branch, dry_run=dry_run)


__all__ = [
    'GitBackend',
    'VCS',
]
