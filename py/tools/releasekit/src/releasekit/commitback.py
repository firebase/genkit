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

"""Post-release commit-back: bump to next dev version and create a PR.

After a release is published, the workspace versions need to be bumped
to the next development version (e.g., ``0.5.0`` → ``0.5.1.dev0``).
This module automates that process:

1. Create a branch from the release commit.
2. Bump all released packages to their next dev version.
3. Commit the changes.
4. Push the branch.
5. Create a PR via the Forge backend.

Key Concepts (ELI5)::

    ┌─────────────────────────┬─────────────────────────────────────────────┐
    │ Concept                 │ Plain-English                               │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Commit-back             │ After shipping v0.5.0, bump pyproject.toml  │
    │                         │ to 0.5.1.dev0 so the main branch always    │
    │                         │ has a dev version. Like turning the page.   │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Dev version             │ A version suffix (.dev0) that signals       │
    │                         │ "this is unreleased work in progress."      │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Commit-back PR          │ A pull request that bumps versions. Created │
    │                         │ automatically so developers don't forget.   │
    └─────────────────────────┴─────────────────────────────────────────────┘

Commit-back flow::

    Release published (v0.5.0)
         │
         ▼
    Create branch: chore/post-release-0.5.0
         │
         ▼
    For each bumped package:
        bump pyproject.toml → 0.5.1.dev0
         │
         ▼
    git commit + push
         │
         ▼
    forge.create_pr(branch → main)

Usage::

    from releasekit.commitback import create_commitback_pr

    result = create_commitback_pr(
        manifest=manifest,
        vcs=git_backend,
        forge=github_backend,
        package_paths={'genkit': Path('packages/genkit')},
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from releasekit.backends.forge import Forge
from releasekit.backends.vcs import VCS
from releasekit.bump import bump_pyproject
from releasekit.logging import get_logger
from releasekit.versions import ReleaseManifest

logger = get_logger(__name__)


@dataclass
class CommitbackResult:
    """Result of a commit-back operation.

    Attributes:
        branch: Name of the branch created.
        bumped: List of package names that were bumped.
        pr_created: Whether a PR was created.
        errors: List of error messages.
    """

    branch: str = ''
    bumped: list[str] = field(default_factory=list)
    pr_created: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True if no errors occurred."""
        return len(self.errors) == 0


def _next_dev_version(version: str) -> str:
    """Compute the next dev version from a release version.

    Bumps the patch component and appends ``.dev0``.

    Examples:
        ``"0.5.0"`` → ``"0.5.1.dev0"``
        ``"1.2.3"`` → ``"1.2.4.dev0"``
        ``"0.5.0rc1"`` → ``"0.5.0.dev0"`` (strip prerelease)

    Args:
        version: The release version string.

    Returns:
        The next dev version string.
    """
    base = version.split('-')[0].split('rc')[0].split('a')[0].split('b')[0]
    parts = base.split('.')

    if len(parts) < 3:
        parts.extend(['0'] * (3 - len(parts)))

    major, minor, patch = parts[0], parts[1], parts[2]
    next_patch = int(patch) + 1
    return f'{major}.{minor}.{next_patch}.dev0'


async def create_commitback_pr(
    *,
    manifest: ReleaseManifest,
    vcs: VCS,
    forge: Forge | None = None,
    package_paths: dict[str, Path] | None = None,
    branch_prefix: str = 'chore/post-release',
    base_branch: str = 'main',
    dry_run: bool = False,
) -> CommitbackResult:
    """Create a commit-back PR to bump versions to next dev.

    Args:
        manifest: Release manifest with bumped packages.
        vcs: VCS backend for git operations.
        forge: Forge backend for PR creation (optional).
        package_paths: Mapping of package name to directory path
            containing ``pyproject.toml``.
        branch_prefix: Prefix for the branch name.
        base_branch: Target branch for the PR.
        dry_run: If True, don't actually create branches or PRs.

    Returns:
        A :class:`CommitbackResult` with the outcome.
    """
    result = CommitbackResult()
    paths = package_paths or {}

    bumped_packages = manifest.bumped
    if not bumped_packages:
        logger.info('commitback_no_packages')
        return result

    umbrella_version = manifest.umbrella_tag.lstrip('v') if manifest.umbrella_tag else 'unknown'
    branch_name = f'{branch_prefix}-{umbrella_version}'
    result.branch = branch_name

    try:
        await vcs.checkout_branch(branch_name, create=True, dry_run=dry_run)
        logger.info('commitback_branch_created', branch=branch_name)
    except Exception as exc:
        result.errors.append(f'Failed to create branch: {exc}')
        logger.error('commitback_branch_error', error=str(exc))
        return result

    for pkg in bumped_packages:
        dev_version = _next_dev_version(pkg.new_version)
        pkg_dir = paths.get(pkg.name)
        if pkg_dir is None:
            logger.warning('commitback_skip_no_path', package=pkg.name)
            continue

        pyproject_path = pkg_dir / 'pyproject.toml'
        if not pyproject_path.exists():
            logger.warning('commitback_skip_no_pyproject', package=pkg.name)
            continue

        try:
            bump_pyproject(pyproject_path, dev_version)
            result.bumped.append(pkg.name)
            logger.info(
                'commitback_bumped',
                package=pkg.name,
                old=pkg.new_version,
                new=dev_version,
            )
        except Exception as exc:
            result.errors.append(f'{pkg.name}: {exc}')
            logger.error(
                'commitback_bump_error',
                package=pkg.name,
                error=str(exc),
            )

    if not result.bumped:
        logger.warning('commitback_nothing_bumped')
        return result

    commit_msg = f'chore: bump to next dev version after {umbrella_version}'
    await vcs.commit(commit_msg, dry_run=dry_run)
    try:
        push_result = await vcs.push(remote='origin', dry_run=dry_run)
        if not push_result.ok:
            result.errors.append(f'Failed to push commit-back branch {branch_name!r}: {push_result.stderr.strip()}')
            logger.error('commitback_push_failed', branch=branch_name, stderr=push_result.stderr.strip())
            return result
    except Exception as exc:
        result.errors.append(f'Failed to push commit-back branch {branch_name!r}: {exc}')
        logger.error('commitback_push_error', branch=branch_name, error=str(exc))
        return result
    logger.info('commitback_pushed', branch=branch_name)

    if forge is not None and hasattr(forge, 'is_available') and await forge.is_available():
        try:
            pr_result = await forge.create_pr(
                head=branch_name,
                base=base_branch,
                title=f'chore: post-release version bump ({umbrella_version})',
                body=(
                    f'Automated commit-back after release {umbrella_version}.\n\n'
                    f'Bumps {len(result.bumped)} package(s) to next dev version.'
                ),
                dry_run=dry_run,
            )
            result.pr_created = pr_result.ok
            logger.info('commitback_pr_created', ok=pr_result.ok)
        except Exception as exc:
            result.errors.append(f'PR creation failed: {exc}')
            logger.error('commitback_pr_error', error=str(exc))
    elif forge is not None:
        logger.info('commitback_forge_unavailable')

    logger.info(
        'commitback_complete',
        branch=branch_name,
        bumped=len(result.bumped),
        ok=result.ok,
    )

    return result


__all__ = [
    'CommitbackResult',
    'create_commitback_pr',
]
