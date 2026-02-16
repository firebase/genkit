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

"""Conventional Commits parsing and semver bump computation.

Reads git log via the :class:`~releasekit.backends.vcs.VCS` backend,
parses `Conventional Commits <https://www.conventionalcommits.org/>`_
messages, scopes each commit to the package(s) it touches, and computes
the appropriate semver bump per package.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Conventional Commit │ A commit message like ``feat: add X`` or      │
    │                     │ ``fix!: break Y``. The prefix tells us        │
    │                     │ whether it's a feature, bugfix, or breaking   │
    │                     │ change.                                       │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ BumpType            │ One of: major, minor, patch, prerelease, or   │
    │                     │ none. Determined by the "strongest" commit    │
    │                     │ since the last tag.                           │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Package Scoping     │ Each commit is assigned to packages whose     │
    │                     │ files it touches (via ``vcs.diff_files``).    │
    │                     │ A commit only bumps packages it affects.      │
    └─────────────────────┴────────────────────────────────────────────────┘

    Conventional Commit → BumpType mapping::

        BREAKING CHANGE (or ``!``)  →  major
        feat:                       →  minor
        fix:, perf:                 →  patch
        docs:, chore:, ci:, etc.    →  none

Usage::

    from releasekit.versioning import compute_bumps, parse_conventional_commit

    # Parse a single commit message
    cc = parse_conventional_commit('feat(auth): add OAuth2 support')
    assert cc.type == 'feat'
    assert cc.scope == 'auth'
    assert cc.bump == BumpType.MINOR

    # Compute bumps for all packages
    bumps = compute_bumps(packages, vcs, tag_format='{name}-v{version}')
"""

from __future__ import annotations

import asyncio
import re
from collections import deque

from releasekit.backends.vcs import VCS
from releasekit.commit_parsing import (
    BumpType,
    CommitParser,
    ConventionalCommit,
    ConventionalCommitParser,
    ParsedCommit,
    max_bump as _max_bump,
    parse_conventional_commit,
)
from releasekit.config import PackageConfig
from releasekit.errors import E, ReleaseKitError
from releasekit.graph import DependencyGraph
from releasekit.logging import get_logger
from releasekit.tags import format_tag
from releasekit.versions import PackageVersion
from releasekit.workspace import Package

logger = get_logger(__name__)


# Module-level singleton for convenience.
_DEFAULT_PARSER = ConventionalCommitParser()


async def _last_tag(vcs: VCS, tag_format: str, name: str, version: str) -> str | None:
    """Find the most recent tag for a package, or None if no tag exists."""
    tag = format_tag(tag_format, name=name, version=version)
    if await vcs.tag_exists(tag):
        return tag
    return None


# PEP 440 pre-release suffix mapping.
_PEP440_SUFFIXES: dict[str, str] = {
    'alpha': 'a',
    'beta': 'b',
    'rc': 'rc',
    'dev': '.dev',
}

# Regex to strip PEP 440 pre-release suffixes from a base version.
_PEP440_STRIP_RE = re.compile(r'^(\d+\.\d+\.\d+)(?:\.dev|a|b|rc)\d+$')


def _parse_base_version(version: str) -> tuple[int, int, int]:
    """Extract (major, minor, patch) from a version string.

    Handles both semver (``1.2.3-rc.1``) and PEP 440 (``1.2.3rc1``) formats.

    Args:
        version: Version string.

    Returns:
        Tuple of (major, minor, patch).

    Raises:
        ReleaseKitError: If the version cannot be parsed.
    """
    # Strip semver pre-release/build metadata.
    base = version.split('-')[0].split('+')[0]
    # Strip PEP 440 pre-release suffixes.
    m = _PEP440_STRIP_RE.match(base)
    if m:
        base = m.group(1)
    parts = base.split('.')

    if len(parts) < 3:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Version {version!r} is not valid (expected X.Y.Z)',
            hint='Use a version string like "1.2.3" (MAJOR.MINOR.PATCH).',
        )

    try:
        return int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError as exc:
        raise ReleaseKitError(
            code=E.VERSION_INVALID,
            message=f'Version {version!r} contains non-numeric components',
            hint='Each component of the version (MAJOR.MINOR.PATCH) must be a non-negative integer.',
        ) from exc


def _apply_bump(
    version: str,
    bump: BumpType,
    prerelease: str = '',
    versioning_scheme: str = 'semver',
) -> str:
    """Apply a version bump to a version string.

    When ``prerelease`` is set, the bump is applied first to compute the
    new base version, then the prerelease suffix is appended.  For
    example, a MINOR bump on ``0.5.0`` with ``prerelease='rc'`` yields
    ``0.6.0rc1`` (PEP 440) or ``0.6.0-rc.1`` (semver), **not**
    ``0.5.1rc1``.

    Args:
        version: Current version (e.g. ``"0.5.0"``).
        bump: The bump type to apply.
        prerelease: Prerelease label (e.g. ``"rc"``).  When non-empty
            the result is a prerelease of the bumped version.
        versioning_scheme: ``"semver"`` or ``"pep440"``.

    Returns:
        The new version string.

    Raises:
        ReleaseKitError: If the version string is not valid.
    """
    major, minor, patch = _parse_base_version(version)

    # Compute the bumped base version.
    if bump == BumpType.MAJOR:
        major, minor, patch = major + 1, 0, 0
    elif bump == BumpType.MINOR:
        major, minor, patch = major, minor + 1, 0
    elif bump == BumpType.PATCH:
        major, minor, patch = major, minor, patch + 1
    elif bump == BumpType.NONE:
        return version

    base = f'{major}.{minor}.{patch}'

    # Append prerelease suffix if requested.
    if prerelease:
        label = prerelease
        if versioning_scheme == 'pep440':
            suffix = _PEP440_SUFFIXES.get(label, label)
            return f'{base}{suffix}1'
        # semver: 1.2.0-rc.1
        return f'{base}-{label}.1'

    return base


async def compute_bumps(
    packages: list[Package],
    vcs: VCS,
    *,
    tag_format: str = '{name}-v{version}',
    prerelease: str = '',
    force_unchanged: bool = False,
    graph: DependencyGraph | None = None,
    synchronize: bool = False,
    major_on_zero: bool = False,
    ignore_unknown_tags: bool = False,
    commit_parser: CommitParser | None = None,
    max_commits: int = 0,
    bootstrap_sha: str = '',
    versioning_scheme: str = 'semver',
    package_configs: dict[str, PackageConfig] | None = None,
) -> list[PackageVersion]:
    """Compute version bumps for all packages based on Conventional Commits.

    For each package:

    1. Find its last git tag (using ``tag_format``).
    2. Get commits since that tag *restricted to the package's directory*.
    3. Parse as Conventional Commits.
    4. Compute the max bump type.
    5. Apply the bump to produce a new version.

    After computing direct bumps, two propagation modes are supported:

    **Independent mode** (default, ``synchronize=False``):
        If a ``graph`` is provided, any package that was bumped triggers
        a PATCH bump in all its transitive dependents (via
        ``graph.reverse_edges``). This ensures lockfiles stay fresh.

    **Synchronized mode** (``synchronize=True``):
        All packages receive the *maximum* bump computed across the
        entire workspace. This keeps all versions in lockstep.

    Args:
        packages: The workspace packages to version.
        vcs: VCS backend for git operations.
        tag_format: Git tag format string with ``{name}``/``{version}``.
        prerelease: Prerelease label (e.g. ``"rc"``). If set, all bumps
            produce prerelease versions.
        force_unchanged: If ``True``, bump unchanged packages to patch.
        graph: Dependency graph for transitive propagation. If ``None``,
            no propagation is performed.
        synchronize: If ``True``, use lockstep mode (all packages share
            the max bump).
        major_on_zero: If ``False`` (default), breaking changes on
            ``0.x`` versions produce MINOR instead of MAJOR.
        ignore_unknown_tags: If ``True``, when a tag exists but
            ``git log {tag}..HEAD`` fails (e.g. corrupt or unreachable
            tag object), fall back to scanning all commits instead of
            raising an error.
        commit_parser: Optional custom commit parser. Defaults to
            :class:`ConventionalCommitParser`.
        max_commits: Maximum number of commits to scan per package.
            0 means no limit. Useful for large repos where scanning
            the entire history is expensive.
        bootstrap_sha: Git SHA to use as the starting point when no
            tag exists for a package. Useful for mid-stream adoption
            of releasekit on repos that already have versions but no
            releasekit tags. Only commits after this SHA are scanned.
            Empty string means scan the entire history.
        versioning_scheme: ``"semver"`` or ``"pep440"``. Controls
            the format of pre-release version strings. Used as the
            fallback when ``package_configs`` does not contain an
            entry for a given package.
        package_configs: Optional per-package config overrides keyed
            by package name. When present, each package's
            ``versioning_scheme`` is looked up from its config entry.
            Use :func:`releasekit.config.resolve_package_config` to
            build these from ``WorkspaceConfig``.

    Returns:
        A list of :class:`PackageVersion` records, one per package.
    """
    parser = commit_parser or _DEFAULT_PARSER

    # Phase 1: Compute direct bumps per package from commits (parallel).
    pkg_bumps: dict[str, BumpType] = {}
    pkg_reasons: dict[str, str] = {}

    async def _compute_pkg_bump(pkg: Package) -> tuple[str, BumpType, str]:
        """Compute the bump for a single package (runs concurrently)."""
        last_tag = await _last_tag(vcs, tag_format, pkg.name, pkg.version)
        # When no tag exists and bootstrap_sha is configured, use it
        # as the starting point instead of scanning the entire history.
        effective_since = last_tag if last_tag is not None else (bootstrap_sha or None)

        try:
            log_lines = await vcs.log(
                format='%H %s',
                since_tag=effective_since,
                paths=[str(pkg.path)],
                first_parent=True,
                no_merges=True,
                max_commits=max_commits,
            )
        except Exception:
            if ignore_unknown_tags and last_tag is not None:
                logger.warning(
                    'tag_unreachable_fallback',
                    package=pkg.name,
                    tag=last_tag,
                    hint='Falling back to full history scan (--ignore-unknown-tags)',
                )
                log_lines = await vcs.log(
                    format='%H %s',
                    since_tag=None,
                    paths=[str(pkg.path)],
                    first_parent=True,
                    no_merges=True,
                    max_commits=max_commits,
                )
            else:
                raise

        commits: list[ParsedCommit] = []
        for line in log_lines:
            parts = line.split(' ', maxsplit=1)
            if len(parts) < 2:
                continue
            sha, subject = parts
            cc = parser.parse(subject, sha=sha)
            if cc is not None:
                commits.append(cc)
            else:
                logger.warning(
                    'non_conventional_commit',
                    package=pkg.name,
                    sha=sha[:8],
                    subject=subject,
                )

        logger.debug(
            'commits_parsed_for_package',
            package=pkg.name,
            total=len(log_lines),
            conventional=len(commits),
        )

        # Count bumps per level; reverts decrement the reverted level.
        bump_counts: dict[BumpType, int] = {
            BumpType.MAJOR: 0,
            BumpType.MINOR: 0,
            BumpType.PATCH: 0,
        }
        reason_commit = ''
        for commit in commits:
            if commit.is_revert and commit.reverted_bump in bump_counts:
                bump_counts[commit.reverted_bump] -= 1
                logger.debug(
                    'revert_cancels_bump',
                    package=pkg.name,
                    reverted_bump=commit.reverted_bump.value,
                    message=commit.raw,
                )
            elif commit.bump in bump_counts:
                bump_counts[commit.bump] += 1
                if not reason_commit:
                    reason_commit = commit.raw

        # Effective bump is the highest level with a positive count.
        max_bump = BumpType.NONE
        for level in [BumpType.MAJOR, BumpType.MINOR, BumpType.PATCH]:
            if bump_counts[level] > 0:
                max_bump = level
                break

        if max_bump == BumpType.MAJOR and not major_on_zero:
            major_version = pkg.version.split('.')[0]
            if major_version == '0':
                max_bump = BumpType.MINOR
                logger.info(
                    'major_downgraded_on_zero',
                    package=pkg.name,
                    version=pkg.version,
                    hint='Set major_on_zero = true to allow 0.x → 1.0.0',
                )

        return pkg.name, max_bump, reason_commit

    bump_results = await asyncio.gather(*[_compute_pkg_bump(pkg) for pkg in packages])
    for name, bump, reason in bump_results:
        pkg_bumps[name] = bump
        pkg_reasons[name] = reason

    # Phase 2: Propagation.
    if synchronize:
        # Lockstep: all packages get the max bump across the workspace.
        global_max = BumpType.NONE
        global_reason = ''
        for name, bump in pkg_bumps.items():
            if _max_bump(global_max, bump) != global_max:
                global_max = _max_bump(global_max, bump)
                global_reason = pkg_reasons[name]

        if global_max != BumpType.NONE:
            for pkg in packages:
                pkg_bumps[pkg.name] = global_max
                if not pkg_reasons[pkg.name]:
                    pkg_reasons[pkg.name] = f'synchronized: {global_reason}'

            logger.info(
                'synchronized_bump',
                bump=global_max.value,
                reason=global_reason,
                count=len(packages),
            )
    elif graph is not None:
        # Independent: propagate PATCH to transitive dependents via BFS.
        queue = deque(name for name, bump in pkg_bumps.items() if bump != BumpType.NONE)
        while queue:
            name = queue.popleft()
            for dependent in graph.reverse_edges.get(name, []):
                if pkg_bumps.get(dependent) == BumpType.NONE:
                    pkg_bumps[dependent] = BumpType.PATCH
                    pkg_reasons[dependent] = f'dependency {name} bumped'
                    queue.append(dependent)
                    logger.info(
                        'transitive_bump',
                        package=dependent,
                        trigger=name,
                    )

    # Phase 3: Build results.
    results: list[PackageVersion] = []
    for pkg in packages:
        max_bump = pkg_bumps[pkg.name]
        reason_commit = pkg_reasons[pkg.name]

        # Skip unchanged packages (unless forced).
        skipped = max_bump == BumpType.NONE
        if skipped and force_unchanged:
            max_bump = BumpType.PATCH
            reason_commit = 'forced: --force-unchanged'
            skipped = False

        # Resolve per-package versioning scheme.
        pkg_scheme = versioning_scheme
        if package_configs and pkg.name in package_configs:
            pkg_cfg = package_configs[pkg.name]
            if pkg_cfg.versioning_scheme:
                pkg_scheme = pkg_cfg.versioning_scheme

        new_version = _apply_bump(pkg.version, max_bump, prerelease, pkg_scheme)
        tag = format_tag(tag_format, name=pkg.name, version=new_version)

        results.append(
            PackageVersion(
                name=pkg.name,
                old_version=pkg.version,
                new_version=new_version,
                bump=max_bump.value,
                reason=reason_commit if not skipped else 'unchanged',
                skipped=skipped,
                tag=tag,
            )
        )

        if skipped:
            logger.debug('package_skipped', package=pkg.name, version=pkg.version)
        else:
            logger.info(
                'package_bumped',
                package=pkg.name,
                old=pkg.version,
                new=new_version,
                bump=max_bump.value,
            )

    return results


__all__ = [
    'BumpType',
    'CommitParser',
    'ConventionalCommit',
    'ConventionalCommitParser',
    'ParsedCommit',
    'compute_bumps',
    'parse_conventional_commit',
]
