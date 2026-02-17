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

"""Mercurial VCS backend for releasekit.

Implements the :class:`~releasekit.backends.vcs.VCS` protocol using
the ``hg`` CLI. This backend validates that the VCS protocol is
generic enough to support version control systems beyond Git.

Terminology mapping:

============================  =========================
VCS (generic)                 Mercurial
============================  =========================
commit SHA                    changeset hash (node)
tag                           tag (global, stored in .hgtags)
branch                        bookmark (named branches are different)
remote                        path (default = origin equivalent)
shallow clone                 (not applicable, always False)
============================  =========================

Usage::

    from releasekit.backends.vcs.mercurial import MercurialCLIBackend

    vcs = MercurialCLIBackend(repo_root=Path('.'))
    sha = await vcs.current_sha()
    log = await vcs.log(since_tag='v1.0.0', paths=['src/'])
"""

from __future__ import annotations

import asyncio
import fnmatch
from pathlib import Path

from releasekit.backends._run import CommandResult, run_command
from releasekit.logging import get_logger

log = get_logger('releasekit.backends.vcs.mercurial')


class MercurialCLIBackend:
    """VCS implementation using ``hg`` (Mercurial).

    Demonstrates that the :class:`~releasekit.backends.vcs.VCS` protocol
    works beyond Git. Maps VCS operations to Mercurial equivalents.

    Key differences from Git:

    - Tags are stored in ``.hgtags`` and are themselves changesets.
    - Shallow clones don't exist; ``is_shallow()`` always returns ``False``.
    - ``hg log`` uses revsets instead of ``ref..ref`` range syntax.
    - Branches are typically bookmarks (lightweight) rather than
      named branches (permanent).

    Args:
        repo_root: Path to the Mercurial repository root.
    """

    def __init__(self, repo_root: Path) -> None:
        """Initialize with the Mercurial repository root path."""
        self._root = repo_root

    def _hg(self, *args: str, dry_run: bool = False, check: bool = False) -> CommandResult:
        """Run an hg command synchronously (called via to_thread)."""
        return run_command(['hg', *args], cwd=self._root, dry_run=dry_run, check=check)

    async def is_clean(self, *, dry_run: bool = False) -> bool:
        """Return ``True`` if the working directory has no uncommitted changes."""
        if dry_run:
            return True
        result = await asyncio.to_thread(self._hg, 'status', '--quiet')
        return result.stdout.strip() == ''

    async def is_shallow(self) -> bool:
        """Return ``False`` — Mercurial does not support shallow clones."""
        return False

    async def default_branch(self) -> str:
        """Return the default branch name.

        In Mercurial, the default named branch is always ``"default"``.
        This is a fixed convention, unlike Git where the default branch
        name is configurable.
        """
        return 'default'

    async def current_sha(self) -> str:
        """Return the current working directory's changeset hash."""
        result = await asyncio.to_thread(
            self._hg,
            'log',
            '-r',
            '.',
            '--template',
            '{node}',
            check=True,
        )
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
        """Return hg log lines.

        Maps Git's ``--pretty=format:`` to Mercurial's ``--template``.
        The ``format`` parameter uses Git-style placeholders which are
        translated to Mercurial template syntax:

        - ``%H`` → ``{node}`` (full changeset hash)
        - ``%s`` → ``{desc|firstline}`` (first line of description)
        """
        # Translate Git format to Mercurial template.
        template = format.replace('%H', '{node}').replace('%s', '{desc|firstline}')
        template += '\\n'

        cmd_parts = ['log', '--template', template]
        if max_commits > 0:
            cmd_parts.extend(['--limit', str(max_commits)])
        if first_parent:
            cmd_parts.append('--follow-first')
        if no_merges:
            cmd_parts.append('--no-merges')

        if since_tag:
            # Mercurial revset: all changesets from tag to tip.
            cmd_parts.extend(['-r', f'tag("{since_tag}")::. and not tag("{since_tag}")'])
        else:
            cmd_parts.extend(['-r', '0:.'])

        if paths:
            cmd_parts.append('--')
            cmd_parts.extend(paths)

        result = await asyncio.to_thread(self._hg, *cmd_parts)
        if not result.stdout.strip():
            return []
        return [line for line in result.stdout.strip().split('\n') if line]

    async def diff_files(self, *, since_tag: str | None = None) -> list[str]:
        """Return list of files changed since a tag.

        Uses ``hg status --rev`` with two revisions to show cumulative
        changes across a range. Note that ``--change`` only accepts a
        single revision (showing changes in that one changeset), so it
        cannot be used for ranges.
        """
        if since_tag:
            # Show files changed between the tagged revision and the
            # working directory parent (`.`).
            result = await asyncio.to_thread(
                self._hg,
                'status',
                '--rev',
                f'tag("{since_tag}")',
                '--rev',
                '.',
                '--no-status',
            )
        else:
            result = await asyncio.to_thread(
                self._hg,
                'status',
                '--no-status',
            )

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
        """Create a commit, adding specified paths first."""
        if paths and not dry_run:
            await asyncio.to_thread(self._hg, 'add', *paths)
        elif not dry_run:
            await asyncio.to_thread(self._hg, 'add')

        log.info('commit', message=message[:80])
        return await asyncio.to_thread(self._hg, 'commit', '-m', message, dry_run=dry_run)

    async def tag(
        self,
        tag_name: str,
        *,
        message: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Create a tag.

        In Mercurial, tags are stored in ``.hgtags`` and create a new
        changeset. This is different from Git's lightweight/annotated
        tags, which are refs.
        """
        tag_message = message or tag_name
        log.info('tag', tag=tag_name)
        return await asyncio.to_thread(
            self._hg,
            'tag',
            '-m',
            tag_message,
            tag_name,
            dry_run=dry_run,
        )

    async def tag_exists(self, tag_name: str) -> bool:
        """Return ``True`` if the tag exists."""
        result = await asyncio.to_thread(self._hg, 'tags', '--quiet')
        return tag_name in result.stdout.split()

    async def delete_tag(
        self,
        tag_name: str,
        *,
        remote: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """Delete a tag.

        In Mercurial, removing a tag creates a new changeset that nullifies
        it. The ``remote`` flag triggers a push after removal.
        """
        result = await asyncio.to_thread(
            self._hg,
            'tag',
            '--remove',
            tag_name,
            dry_run=dry_run,
        )
        if remote and result.ok and not dry_run:
            await asyncio.to_thread(self._hg, 'push')
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
        """Push changesets to a remote path.

        Mercurial pushes all new changesets by default (tags are
        changesets, so they're included automatically).

        Note:
            ``set_upstream`` is accepted for protocol compatibility but
            ignored — Mercurial does not have Git-style upstream tracking
            branches.

            ``force`` is accepted for protocol compatibility but
            ignored — Mercurial push uses ``--force`` which has different
            semantics (allows pushing new heads).
        """
        # Mercurial uses "default" as the default remote, not "origin".
        hg_remote = 'default' if remote == 'origin' else remote
        cmd_parts = ['push', hg_remote]
        if force:
            cmd_parts.append('--force')

        log.info('push', remote=hg_remote, tags=tags, set_upstream=set_upstream, force=force)
        return await asyncio.to_thread(self._hg, *cmd_parts, dry_run=dry_run)

    async def tag_commit_sha(self, tag_name: str) -> str:
        """Return the commit SHA that a tag points to."""
        result = await asyncio.to_thread(
            self._hg,
            'log',
            '-r',
            f'tag({tag_name!r})',
            '--template',
            '{node}',
        )
        return result.stdout.strip() if result.ok else ''

    async def list_tags(self, *, pattern: str = '') -> list[str]:
        """Return all tags, optionally filtered by a glob pattern.

        Uses ``hg tags --quiet`` which lists tag names one per line.
        Filters out the special ``tip`` tag.
        """
        result = await asyncio.to_thread(self._hg, 'tags', '--quiet')
        if not result.ok or not result.stdout.strip():
            return []
        tags = [t for t in result.stdout.strip().splitlines() if t != 'tip']
        if pattern:
            tags = [t for t in tags if fnmatch.fnmatch(t, pattern)]
        return sorted(tags)

    async def current_branch(self) -> str:
        """Return the current bookmark name.

        In Mercurial, the active bookmark is the closest equivalent to
        Git's current branch. Returns an empty string if no bookmark
        is active.
        """
        result = await asyncio.to_thread(
            self._hg,
            'log',
            '-r',
            '.',
            '--template',
            '{activebookmark}',
        )
        return result.stdout.strip() if result.ok else ''

    async def checkout_branch(
        self,
        branch: str,
        *,
        create: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """Switch to a bookmark (Mercurial's lightweight branch equivalent).

        Uses ``hg bookmark`` for creation and ``hg update`` for switching.
        """
        if create:
            log.info('bookmark_create', bookmark=branch)
            return await asyncio.to_thread(
                self._hg,
                'bookmark',
                branch,
                dry_run=dry_run,
            )
        log.info('update_to', bookmark=branch)
        return await asyncio.to_thread(
            self._hg,
            'update',
            branch,
            dry_run=dry_run,
        )

    async def tags_on_branch(self, branch: str) -> list[str]:
        """Return tags reachable from a branch, in chronological order.

        Uses ``hg log`` with a revset to find all tagged changesets
        that are ancestors of the given bookmark/branch.
        """
        result = await asyncio.to_thread(
            self._hg,
            'log',
            '-r',
            f'ancestors({branch!r}) and tag()',
            '--template',
            '{tags}\\n',
        )
        if not result.ok or not result.stdout.strip():
            return []
        tags: list[str] = []
        for line in result.stdout.strip().splitlines():
            for t in line.split():
                if t and t != 'tip':
                    tags.append(t)
        return tags

    async def commit_exists(self, sha: str) -> bool:
        """Return ``True`` if the changeset exists in the repository."""
        result = await asyncio.to_thread(
            self._hg,
            'log',
            '-r',
            sha,
            '--template',
            '{node|short}',
        )
        return result.ok and bool(result.stdout.strip())

    async def cherry_pick(
        self,
        sha: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Graft (cherry-pick) a changeset onto the current working directory parent.

        Mercurial's ``hg graft`` is the equivalent of ``git cherry-pick``.
        """
        log.info('graft', changeset=sha)
        return await asyncio.to_thread(
            self._hg,
            'graft',
            '-r',
            sha,
            dry_run=dry_run,
        )

    async def cherry_pick_abort(self) -> CommandResult:
        """Abort an in-progress graft (cherry-pick) operation."""
        return await asyncio.to_thread(
            self._hg,
            'graft',
            '--abort',
        )

    async def tag_date(self, tag_name: str) -> str:
        """Return the ISO 8601 date of a tag.

        Queries the changeset that the tag points to and formats
        its date in ISO 8601.
        """
        result = await asyncio.to_thread(
            self._hg,
            'log',
            '-r',
            f'tag({tag_name!r})',
            '--template',
            '{date|isodate}',
        )
        return result.stdout.strip() if result.ok else ''


__all__ = [
    'MercurialCLIBackend',
]
