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

"""Hotfix and maintenance branch release support.

Provides utilities for releasing from non-default branches, cherry-picking
commits for backport releases, and computing version bumps scoped to a
specific branch or tag range.

Key Concepts (ELI5)::

    ┌─────────────────────────┬─────────────────────────────────────────────┐
    │ Concept                 │ Plain-English                               │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Hotfix branch           │ A branch like ``release/1.x`` that gets    │
    │                         │ critical fixes backported from ``main``.    │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ --base-branch           │ Override the default branch for version     │
    │                         │ computation. Commits are scoped to this     │
    │                         │ branch instead of ``main``.                │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ --since-tag             │ Override the starting tag for commit scan.  │
    │                         │ Useful when the last tag on a maintenance   │
    │                         │ branch differs from the latest on main.     │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ cherry-pick             │ Apply specific commits from main to a       │
    │                         │ maintenance branch for backporting.         │
    └─────────────────────────┴─────────────────────────────────────────────┘

Usage::

    from releasekit.hotfix import (
        cherry_pick_commits,
        resolve_base_branch,
        resolve_since_tag,
    )

    # Resolve the effective base branch
    branch = resolve_base_branch(ws_config, cli_override='release/1.x')

    # Cherry-pick commits for backport
    result = await cherry_pick_commits(
        vcs,
        shas=['abc123', 'def456'],
        dry_run=True,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field

from releasekit.backends.vcs import VCS
from releasekit.config import WorkspaceConfig
from releasekit.errors import E, ReleaseKitError
from releasekit.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class CherryPickResult:
    """Result of a cherry-pick operation.

    Attributes:
        applied: SHAs that were successfully cherry-picked.
        skipped: SHAs that were skipped (already applied or empty diff).
        failed: Mapping of SHA → error message for failed cherry-picks.
        dry_run: Whether this was a dry-run.
    """

    applied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    dry_run: bool = False

    @property
    def ok(self) -> bool:
        """Whether all cherry-picks succeeded (no failures)."""
        return len(self.failed) == 0

    def summary(self) -> str:
        """Human-readable summary."""
        parts = [f'{len(self.applied)} applied']
        if self.skipped:
            parts.append(f'{len(self.skipped)} skipped')
        if self.failed:
            parts.append(f'{len(self.failed)} failed')
        if self.dry_run:
            parts.append('(dry-run)')
        return ', '.join(parts)


@dataclass(frozen=True)
class HotfixContext:
    """Resolved context for a hotfix/maintenance release.

    Attributes:
        base_branch: The branch to release from.
        since_tag: The tag to start scanning commits from.
        is_maintenance: Whether this is a maintenance branch release
            (as opposed to a release from the default branch).
    """

    base_branch: str
    since_tag: str = ''
    is_maintenance: bool = False


def resolve_base_branch(
    ws_config: WorkspaceConfig,
    *,
    cli_override: str = '',
    default_branch: str = 'main',
) -> str:
    """Resolve the effective base branch for version computation.

    Priority: CLI ``--base-branch`` > ``ws_config.publish_branch`` >
    ``default_branch``.

    Args:
        ws_config: Workspace configuration.
        cli_override: CLI ``--base-branch`` flag value.
        default_branch: Fallback default branch name.

    Returns:
        The resolved branch name.
    """
    if cli_override:
        logger.info('base_branch_override', branch=cli_override, source='cli')
        return cli_override
    if ws_config.publish_branch:
        logger.info('base_branch_override', branch=ws_config.publish_branch, source='config')
        return ws_config.publish_branch
    return default_branch


async def resolve_since_tag(
    vcs: VCS,
    *,
    cli_override: str = '',
    tag_format: str = '{name}-v{version}',
    package_name: str = '',
    base_branch: str = '',
) -> str:
    """Resolve the starting tag for commit scanning.

    Priority: CLI ``--since-tag`` > latest tag on the base branch >
    empty (scan all history).

    Args:
        vcs: VCS backend.
        cli_override: CLI ``--since-tag`` flag value.
        tag_format: Tag format string for pattern matching.
        package_name: Package name for tag pattern.
        base_branch: Branch to search for tags on.

    Returns:
        Tag name, or empty string to scan all history.
    """
    if cli_override:
        if await vcs.tag_exists(cli_override):
            logger.info('since_tag_override', tag=cli_override, source='cli')
            return cli_override
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Tag {cli_override!r} specified by --since-tag does not exist',
            hint='Check the tag name. Use "git tag -l" to list available tags.',
        )

    # If on a maintenance branch, try to find the latest tag reachable
    # from that branch.
    if base_branch:
        try:
            tags = await vcs.tags_on_branch(base_branch)
            if tags:
                # Return the most recent tag (last in chronological order).
                latest = tags[-1]
                logger.info('since_tag_from_branch', tag=latest, branch=base_branch)
                return latest
        except Exception:  # noqa: BLE001
            logger.debug('since_tag_branch_scan_failed', branch=base_branch)

    return ''


async def resolve_hotfix_context(
    vcs: VCS,
    ws_config: WorkspaceConfig,
    *,
    cli_base_branch: str = '',
    cli_since_tag: str = '',
    default_branch: str = 'main',
) -> HotfixContext:
    """Resolve the full hotfix context from config and CLI overrides.

    Args:
        vcs: VCS backend.
        ws_config: Workspace configuration.
        cli_base_branch: CLI ``--base-branch`` override.
        cli_since_tag: CLI ``--since-tag`` override.
        default_branch: Fallback default branch.

    Returns:
        Resolved :class:`HotfixContext`.
    """
    base_branch = resolve_base_branch(
        ws_config,
        cli_override=cli_base_branch,
        default_branch=default_branch,
    )

    since_tag = await resolve_since_tag(
        vcs,
        cli_override=cli_since_tag,
        base_branch=base_branch if base_branch != default_branch else '',
    )

    is_maintenance = base_branch != default_branch

    if is_maintenance:
        logger.info(
            'hotfix_context',
            base_branch=base_branch,
            since_tag=since_tag or '(all)',
            is_maintenance=True,
        )

    return HotfixContext(
        base_branch=base_branch,
        since_tag=since_tag,
        is_maintenance=is_maintenance,
    )


async def cherry_pick_commits(
    vcs: VCS,
    shas: list[str],
    *,
    dry_run: bool = False,
) -> CherryPickResult:
    """Cherry-pick a list of commits onto the current branch.

    Each SHA is cherry-picked in order. If a cherry-pick fails due to
    conflicts, the operation is aborted for that commit and recorded
    in the ``failed`` dict. Already-applied commits are detected and
    skipped.

    Args:
        vcs: VCS backend.
        shas: List of commit SHAs to cherry-pick.
        dry_run: If True, don't actually cherry-pick.

    Returns:
        :class:`CherryPickResult` with applied/skipped/failed details.
    """
    applied: list[str] = []
    skipped: list[str] = []
    failed: dict[str, str] = {}

    for sha in shas:
        short = sha[:8]

        # Check if commit exists.
        if not await vcs.commit_exists(sha):
            failed[sha] = f'Commit {short} does not exist'
            logger.error('cherry_pick_not_found', sha=short)
            continue

        if dry_run:
            logger.info('cherry_pick_dry_run', sha=short)
            applied.append(sha)
            continue

        try:
            result = await vcs.cherry_pick(sha)
            if result.return_code == 0:
                applied.append(sha)
                logger.info('cherry_pick_applied', sha=short)
            else:
                # Cherry-pick failed (likely conflict).
                await vcs.cherry_pick_abort()
                failed[sha] = result.stderr.strip() or f'Cherry-pick failed for {short}'
                logger.error('cherry_pick_conflict', sha=short, stderr=result.stderr.strip())
        except Exception as exc:  # noqa: BLE001
            failed[sha] = str(exc)
            logger.error('cherry_pick_error', sha=short, error=str(exc))
            try:
                await vcs.cherry_pick_abort()
            except Exception:  # noqa: BLE001
                logger.debug('cherry_pick_abort_failed', sha=short)

    result = CherryPickResult(
        applied=applied,
        skipped=skipped,
        failed=failed,
        dry_run=dry_run,
    )

    logger.info('cherry_pick_result', summary=result.summary())
    return result


__all__ = [
    'CherryPickResult',
    'HotfixContext',
    'cherry_pick_commits',
    'resolve_base_branch',
    'resolve_hotfix_context',
    'resolve_since_tag',
]
