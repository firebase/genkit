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

    async def default_branch(self) -> str:
        """Auto-detect the default branch name.

        Tries, in order:

        1. ``git symbolic-ref refs/remotes/origin/HEAD`` — set by
           ``git clone`` or ``git remote set-head origin --auto``.
        2. Check if common branch names (``main``, ``master``, ``trunk``,
           ``develop``) exist as local refs.
        3. Fall back to ``"main"``.
        """
        # Method 1: symbolic-ref (most reliable after clone).
        result = await asyncio.to_thread(
            self._git,
            'symbolic-ref',
            '--short',
            'refs/remotes/origin/HEAD',
        )
        if result.ok and result.stdout.strip():
            ref = result.stdout.strip()
            # Strip "origin/" prefix if present.
            if ref.startswith('origin/'):
                ref = ref[len('origin/') :]
            return ref

        # Method 2: probe common branch names.
        for candidate in ('main', 'master', 'trunk', 'develop'):
            probe = await asyncio.to_thread(
                self._git,
                'rev-parse',
                '--verify',
                '--quiet',
                f'refs/heads/{candidate}',
            )
            if probe.ok:
                return candidate

        # Method 3: fall back.
        log.warning(
            'default_branch_fallback',
            hint='Could not detect default branch; falling back to "main". '
            'Set default_branch in releasekit.toml or run '
            '"git remote set-head origin --auto".',
        )
        return 'main'

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
        no_merges: bool = False,
        max_commits: int = 0,
    ) -> list[str]:
        """Return git log lines."""
        cmd_parts = ['log', f'--pretty=format:{format}']
        if max_commits > 0:
            cmd_parts.append(f'-n{max_commits}')
        if first_parent:
            cmd_parts.append('--first-parent')
        if no_merges:
            cmd_parts.append('--no-merges')
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
        if paths:
            await asyncio.to_thread(self._git, 'add', *paths, dry_run=dry_run)
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
            remote_result = await asyncio.to_thread(
                self._git,
                'push',
                'origin',
                f':refs/tags/{tag_name}',
                dry_run=dry_run,
            )
            if not remote_result.ok:
                return remote_result
        return result

    async def push(
        self,
        *,
        tags: bool = False,
        remote: str = 'origin',
        set_upstream: bool = True,
        force: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """Push commits and/or tags."""
        cmd_parts = ['push']
        if force:
            cmd_parts.append('--force-with-lease')
        # --set-upstream is only meaningful for branch pushes, not tag-only pushes.
        branch_refspec: str = ''
        if set_upstream and not tags:
            cmd_parts.append('--set-upstream')
            # --set-upstream requires an explicit refspec (branch name).
            branch_refspec = await self.current_branch()
        cmd_parts.append(remote)
        if branch_refspec:
            cmd_parts.append(branch_refspec)
        if tags:
            cmd_parts.append('--tags')
        log.info('push', remote=remote, tags=tags, set_upstream=set_upstream, force=force)
        return await asyncio.to_thread(self._git, *cmd_parts, dry_run=dry_run)

    async def tag_commit_sha(self, tag_name: str) -> str:
        """Return the commit SHA that a tag points to."""
        result = await asyncio.to_thread(self._git, 'rev-list', '-1', tag_name)
        return result.stdout.strip() if result.ok else ''

    async def list_tags(self, *, pattern: str = '') -> list[str]:
        """Return all tags, optionally filtered by a glob pattern."""
        cmd_parts = ['tag', '--list', '--sort=version:refname']
        if pattern:
            cmd_parts.append(pattern)
        result = await asyncio.to_thread(self._git, *cmd_parts)
        if not result.ok or not result.stdout.strip():
            return []
        return result.stdout.strip().splitlines()

    async def current_branch(self) -> str:
        """Return the name of the currently checked-out branch."""
        result = await asyncio.to_thread(self._git, 'branch', '--show-current')
        return result.stdout.strip() if result.ok else ''

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
            return await asyncio.to_thread(self._git, 'checkout', '-B', branch, dry_run=dry_run)
        log.info('checkout_branch', branch=branch)
        return await asyncio.to_thread(self._git, 'checkout', branch, dry_run=dry_run)

    async def tags_on_branch(self, branch: str) -> list[str]:
        """Return tags reachable from a branch, in chronological order."""
        result = await asyncio.to_thread(
            self._git,
            'tag',
            '--merged',
            branch,
            '--sort=creatordate',
        )
        if not result.ok or not result.stdout.strip():
            return []
        return result.stdout.strip().splitlines()

    async def commit_exists(self, sha: str) -> bool:
        """Return ``True`` if the commit SHA exists in the repository."""
        result = await asyncio.to_thread(self._git, 'cat-file', '-t', sha)
        return result.ok and result.stdout.strip() == 'commit'

    async def cherry_pick(
        self,
        sha: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Cherry-pick a single commit onto the current branch."""
        log.info('cherry_pick', sha=sha[:8])
        return await asyncio.to_thread(self._git, 'cherry-pick', sha, dry_run=dry_run)

    async def cherry_pick_abort(self) -> CommandResult:
        """Abort an in-progress cherry-pick operation."""
        return await asyncio.to_thread(self._git, 'cherry-pick', '--abort')

    async def tag_date(self, tag_name: str) -> str:
        """Return the ISO 8601 date of a tag."""
        result = await asyncio.to_thread(
            self._git,
            'log',
            '-1',
            '--format=%aI',
            tag_name,
        )
        return result.stdout.strip() if result.ok else ''


__all__ = [
    'GitCLIBackend',
]
