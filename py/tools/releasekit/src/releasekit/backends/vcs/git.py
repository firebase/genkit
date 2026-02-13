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

"""Git VCS backend for releasekit.

The :class:`GitCLIBackend` implements the :class:`VCS` protocol by
delegating to ``git`` via :func:`run_command`.

All methods are async — blocking subprocess calls are dispatched to
``asyncio.to_thread()`` to avoid blocking the event loop.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from releasekit.backends._run import CommandResult, run_command
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.git')


class GitCLIBackend:
    """Default :class:`~releasekit.backends.vcs.VCS` implementation using ``git``.

    All methods are async and delegate blocking subprocess calls to
    ``asyncio.to_thread()`` to avoid blocking the event loop.

    Args:
        repo_root: Path to the git repository root.
    """

    def __init__(self, repo_root: Path) -> None:
        """Initialize with the git repository root path."""
        self._root = repo_root

    def _git(self, *args: str, dry_run: bool = False, check: bool = False) -> CommandResult:
        """Run a git command synchronously (called via to_thread)."""
        return run_command(['git', *args], cwd=self._root, dry_run=dry_run, check=check)

    async def is_clean(self, *, dry_run: bool = False) -> bool:
        """Return ``True`` if the working tree is clean."""
        if dry_run:
            return True
        result = await asyncio.to_thread(self._git, 'status', '--porcelain')
        return result.stdout.strip() == ''

    async def is_shallow(self) -> bool:
        """Return ``True`` if the repository is a shallow clone."""
        result = await asyncio.to_thread(self._git, 'rev-parse', '--is-shallow-repository')
        return result.stdout.strip() == 'true'

    async def current_sha(self) -> str:
        """Return the current HEAD commit SHA."""
        result = await asyncio.to_thread(self._git, 'rev-parse', 'HEAD', check=True)
        return result.stdout.strip()

    async def log(
        self,
        *,
        since_tag: str | None = None,
        paths: list[str] | None = None,
        format: str = '%H %s',
        first_parent: bool = False,
    ) -> list[str]:
        """Return git log lines."""
        cmd_parts = ['log', f'--pretty=format:{format}']
        if first_parent:
            cmd_parts.append('--first-parent')
        if since_tag:
            cmd_parts.append(f'{since_tag}..HEAD')
        if paths:
            cmd_parts.append('--')
            cmd_parts.extend(paths)
        result = await asyncio.to_thread(self._git, *cmd_parts)
        if not result.stdout.strip():
            return []
        return result.stdout.strip().split('\n')

    async def diff_files(self, *, since_tag: str | None = None) -> list[str]:
        """Return list of changed files since a tag."""
        if since_tag:
            result = await asyncio.to_thread(self._git, 'diff', '--name-only', f'{since_tag}..HEAD')
        else:
            tag_result = await asyncio.to_thread(self._git, 'describe', '--tags', '--abbrev=0')
            if not tag_result.ok:
                return []
            last_tag = tag_result.stdout.strip()
            result = await asyncio.to_thread(self._git, 'diff', '--name-only', f'{last_tag}..HEAD')

        if not result.stdout.strip():
            return []
        return result.stdout.strip().split('\n')

    async def commit(
        self,
        message: str,
        *,
        paths: list[str] | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Create a commit, staging specified paths first."""
        if paths and not dry_run:
            await asyncio.to_thread(self._git, 'add', *paths)
        else:
            await asyncio.to_thread(self._git, 'add', '-A', dry_run=dry_run)

        log.info('commit', message=message[:80])
        return await asyncio.to_thread(self._git, 'commit', '-m', message, dry_run=dry_run)

    async def tag(
        self,
        tag_name: str,
        *,
        message: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Create an annotated tag."""
        tag_message = message or tag_name
        log.info('tag', tag=tag_name)
        return await asyncio.to_thread(
            self._git,
            'tag',
            '-a',
            tag_name,
            '-m',
            tag_message,
            dry_run=dry_run,
        )

    async def tag_exists(self, tag_name: str) -> bool:
        """Return ``True`` if the tag exists."""
        result = await asyncio.to_thread(self._git, 'tag', '-l', tag_name)
        return result.stdout.strip() == tag_name

    async def delete_tag(
        self,
        tag_name: str,
        *,
        remote: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """Delete a tag locally and optionally on the remote."""
        result = await asyncio.to_thread(self._git, 'tag', '-d', tag_name, dry_run=dry_run)
        if remote and result.ok:
            await asyncio.to_thread(
                self._git,
                'push',
                'origin',
                f':refs/tags/{tag_name}',
                dry_run=dry_run,
            )
        return result

    async def push(
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
        return await asyncio.to_thread(self._git, *cmd_parts, dry_run=dry_run)

    async def checkout_branch(
        self,
        branch: str,
        *,
        create: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """Switch to a branch, optionally creating it."""
        if create:
            log.info('checkout_branch_create', branch=branch)
            return await asyncio.to_thread(self._git, 'checkout', '-b', branch, dry_run=dry_run)
        log.info('checkout_branch', branch=branch)
        return await asyncio.to_thread(self._git, 'checkout', branch, dry_run=dry_run)


__all__ = [
    'GitCLIBackend',
]
