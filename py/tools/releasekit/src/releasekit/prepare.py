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

"""Release preparation: version bumps, changelog, and Release PR.

Orchestrates the "prepare" step of the release-please model. On every
push to the default branch, this module:

1. Runs preflight checks (clean tree, lock file, forge auth, etc.).
2. Computes version bumps from Conventional Commits.
3. Propagates PATCH bumps to reverse-dependents (if ``synchronize=False``)
   or applies lockstep bumps (if ``synchronize=True``).
4. Rewrites ``pyproject.toml`` versions via :func:`bump.bump_pyproject`.
5. Updates ``uv.lock`` for each bumped package.
6. Generates per-package changelogs.
7. Commits all changes on a release branch and pushes.
8. Opens (or updates) a Release PR with the manifest embedded in the body.

This module is forge-agnostic. It works with any backend that satisfies
the :class:`~releasekit.backends.forge.Forge` protocol. Forges that
don't support labels (e.g. Bitbucket) will simply skip the label-based
state management with a logged warning — the core flow still works.

Key Concepts (ELI5)::

    ┌─────────────────────────┬─────────────────────────────────────────────┐
    │ Concept                 │ ELI5 Explanation                            │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Release PR              │ A pull request that contains all version    │
    │                         │ bumps and changelogs for a release. When    │
    │                         │ merged, it triggers the "tag" step.         │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Embedded manifest       │ JSON block in the PR body that lists all    │
    │                         │ packages, old/new versions, and bump types. │
    │                         │ Parsed by the "tag" step to know what to    │
    │                         │ tag and release.                            │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ PrepareResult           │ Outcome of the prepare run: which packages  │
    │                         │ were bumped, the PR URL, and any errors.    │
    └─────────────────────────┴─────────────────────────────────────────────┘

Prepare flow::

    push to main
         │
         ▼
    preflight checks (clean tree, lock, forge, cycles)
         │
         ▼
    compute_bumps(packages, vcs, tag_format, graph, synchronize)
         │
         ▼
    for each bumped package:
        bump_pyproject(pkg.pyproject_path, new_version)
        pm.lock(upgrade_package=pkg.name)
        generate_changelog(vcs, version, since_tag, paths)
         │
         ▼
    vcs.commit("chore: release ...")
    vcs.push()
         │
         ▼
    forge.create_pr() or forge.update_pr()
    forge.add_labels("autorelease: pending")
         │
         ▼
    PrepareResult(bumped=..., pr_url=..., manifest=...)

Usage::

    from releasekit.prepare import prepare_release

    result = await prepare_release(
        vcs=git_backend,
        pm=uv_backend,
        forge=github_backend,
        registry=pypi_backend,
        workspace_root=Path('.'),
        config=config,
        dry_run=False,
    )
    if result.ok:
        print(f'Release PR: {result.pr_url}')
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from releasekit.backends.forge import Forge
from releasekit.backends.pm import PackageManager
from releasekit.backends.registry import Registry
from releasekit.backends.vcs import VCS
from releasekit.bump import bump_pyproject
from releasekit.changelog import generate_changelog, render_changelog
from releasekit.config import ReleaseConfig
from releasekit.graph import build_graph, topo_sort
from releasekit.logging import get_logger
from releasekit.preflight import run_preflight
from releasekit.tags import format_tag
from releasekit.versioning import compute_bumps
from releasekit.versions import PackageVersion, ReleaseManifest
from releasekit.workspace import Package, discover_packages

logger = get_logger(__name__)

_RELEASE_BRANCH = 'release-please--packages--default'
_AUTORELEASE_PENDING = 'autorelease: pending'
_MANIFEST_START = '<!-- releasekit:manifest:start -->'
_MANIFEST_END = '<!-- releasekit:manifest:end -->'


@dataclass
class PrepareResult:
    """Outcome of a prepare run.

    Attributes:
        bumped: Packages that received a version bump.
        skipped: Packages with no changes.
        manifest: The release manifest (for serialization).
        pr_url: URL of the created or updated Release PR.
        changelogs: Rendered markdown changelog per package name.
        errors: Error messages keyed by step name.
    """

    bumped: list[PackageVersion] = field(default_factory=list)
    skipped: list[PackageVersion] = field(default_factory=list)
    manifest: ReleaseManifest | None = None
    pr_url: str = ''
    changelogs: dict[str, str] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """Return True if no errors occurred."""
        return not self.errors


def _embed_manifest(body: str, manifest_json: str) -> str:
    """Embed a JSON manifest in the PR body between marker comments.

    If markers already exist, replace the block. Otherwise append it.
    """
    block = f'{_MANIFEST_START}\n```json\n{manifest_json}\n```\n{_MANIFEST_END}'
    if _MANIFEST_START in body:
        pattern = re.escape(_MANIFEST_START) + r'.*?' + re.escape(_MANIFEST_END)
        return re.sub(pattern, block, body, flags=re.DOTALL)
    return body + '\n\n' + block


def _build_pr_body(
    changelogs: dict[str, str],
    manifest_json: str,
    umbrella_version: str,
) -> str:
    """Build the Release PR body with changelogs and embedded manifest."""
    lines = [f'# Release v{umbrella_version}', '']
    for _pkg_name, changelog_md in sorted(changelogs.items()):
        lines.append(changelog_md)
        lines.append('')
    body = '\n'.join(lines)
    return _embed_manifest(body, manifest_json)


def _package_paths(packages: list[Package]) -> dict[str, str]:
    """Build a name → relative path mapping for changelogs."""
    return {pkg.name: str(pkg.path) for pkg in packages}


async def prepare_release(
    *,
    vcs: VCS,
    pm: PackageManager,
    forge: Forge | None,
    registry: Registry,
    workspace_root: Path,
    config: ReleaseConfig,
    dry_run: bool = False,
    force: bool = False,
) -> PrepareResult:
    """Run the prepare step: bump versions, generate changelogs, open Release PR.

    This function is forge-agnostic. When ``forge`` is ``None`` or
    unavailable, it still performs all local operations (bump, changelog,
    commit) but skips PR creation.

    Args:
        vcs: Version control backend.
        pm: Package manager backend (uv).
        forge: Code forge backend (GitHub/GitLab/Bitbucket). None to skip PR.
        registry: Package registry backend (PyPI).
        workspace_root: Workspace root directory.
        config: Release configuration.
        dry_run: If True, skip all side effects.
        force: If True, skip preflight and force bumps.

    Returns:
        A :class:`PrepareResult` with bumped packages and PR URL.
    """
    result = PrepareResult()

    # 1. Discover packages and build dependency graph.
    packages = discover_packages(workspace_root, exclude_patterns=config.exclude)
    graph = build_graph(packages)
    topo_sort(graph)  # Validate DAG (raises on cycles).

    # 2. Compute version bumps.
    versions = await compute_bumps(
        packages,
        vcs,
        tag_format=config.tag_format,
        graph=graph if not config.synchronize else None,
        synchronize=config.synchronize,
    )

    bumped = [v for v in versions if not v.skipped]
    skipped = [v for v in versions if v.skipped]
    result.bumped = bumped
    result.skipped = skipped

    if not bumped:
        logger.info('prepare_nothing_to_release', message='No packages have changes.')
        return result

    # 3. Preflight checks.
    if not force:
        preflight = await run_preflight(
            vcs=vcs,
            pm=pm,
            forge=forge,
            registry=registry,
            packages=packages,
            graph=graph,
            versions=versions,
            workspace_root=workspace_root,
            dry_run=dry_run,
        )
        if not preflight.ok:
            for name, error in preflight.errors.items():
                result.errors[f'preflight:{name}'] = error
            return result

    # 4. Bump pyproject.toml for each bumped package.
    pkg_by_name = {pkg.name: pkg for pkg in packages}
    for ver in bumped:
        pkg = pkg_by_name.get(ver.name)
        if pkg is None:
            result.errors[f'bump:{ver.name}'] = f'Package {ver.name!r} not found in workspace'
            continue
        if not dry_run:
            bump_pyproject(pkg.pyproject_path, ver.new_version)
        logger.info('bumped', package=ver.name, old=ver.old_version, new=ver.new_version)

    # 5. Update lock file.
    if not dry_run:
        for ver in bumped:
            await pm.lock(upgrade_package=ver.name)

    # 6. Generate changelogs.
    today = datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')
    pkg_paths = _package_paths(packages)
    for ver in bumped:
        since_tag = format_tag(config.tag_format, name=ver.name, version=ver.old_version)
        changelog = await generate_changelog(
            vcs=vcs,
            version=ver.new_version,
            since_tag=since_tag,
            paths=[pkg_paths[ver.name]] if ver.name in pkg_paths else None,
            date=today,
        )
        rendered = render_changelog(changelog)
        result.changelogs[ver.name] = rendered
        logger.info('changelog_generated', package=ver.name, sections=len(changelog.sections))

    # 7. Build and save manifest.
    git_sha = await vcs.current_sha()
    umbrella_version = bumped[0].new_version if bumped else '0.0.0'
    umbrella_tag = format_tag(config.umbrella_tag, version=umbrella_version)
    manifest = ReleaseManifest(
        git_sha=git_sha,
        umbrella_tag=umbrella_tag,
        packages=versions,
        created_at=datetime.now(tz=timezone.utc).isoformat(),
    )
    result.manifest = manifest

    manifest_path = workspace_root / 'release-manifest.json'
    if not dry_run:
        manifest.save(manifest_path)

    # 8. Commit and push on release branch.
    commit_msg = f'chore: release v{umbrella_version}'
    if not dry_run:
        await vcs.checkout_branch(_RELEASE_BRANCH, create=True)
        await vcs.commit(commit_msg, paths=['.'])
        await vcs.push()
    logger.info('release_branch_pushed', branch=_RELEASE_BRANCH, sha=git_sha)

    # 9. Create or update Release PR.
    if dry_run:
        manifest_json = json.dumps({'dry_run': True, 'bumped': len(bumped)}, indent=2)
    else:
        manifest_json = manifest_path.read_text(encoding='utf-8')

    pr_body = _build_pr_body(result.changelogs, manifest_json, umbrella_version)
    pr_title = f'chore: release v{umbrella_version}'

    if forge is not None and await forge.is_available():
        # Check if a Release PR already exists for this branch.
        existing_prs = await forge.list_prs(head=_RELEASE_BRANCH, state='open', limit=1)
        if existing_prs:
            pr_number = existing_prs[0].get('number', 0)
            if not dry_run:
                await forge.update_pr(pr_number, title=pr_title, body=pr_body)
            result.pr_url = existing_prs[0].get('url', f'PR #{pr_number}')
            logger.info('release_pr_updated', pr=pr_number)
        else:
            if not dry_run:
                pr_result = await forge.create_pr(
                    title=pr_title,
                    body=pr_body,
                    head=_RELEASE_BRANCH,
                    base='main',
                )
                result.pr_url = pr_result.stdout.strip() if pr_result.ok else ''
            logger.info('release_pr_created', branch=_RELEASE_BRANCH)

        # Add "autorelease: pending" label (no-op on forges without labels).
        if not dry_run and existing_prs:
            pr_number = existing_prs[0].get('number', 0)
            if pr_number:
                await forge.add_labels(pr_number, [_AUTORELEASE_PENDING])

    logger.info(
        'prepare_complete',
        bumped=len(bumped),
        skipped=len(skipped),
        pr_url=result.pr_url,
    )
    return result


__all__ = [
    'PrepareResult',
    'prepare_release',
]
