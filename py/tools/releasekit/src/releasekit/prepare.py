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

Orchestrates the "prepare" step of the releasekit model. On every
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
        bump_pyproject(pkg.manifest_path, new_version)
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
from pathlib import Path

from releasekit.backends.forge import Forge
from releasekit.backends.pm import PackageManager
from releasekit.backends.registry import Registry
from releasekit.backends.vcs import VCS
from releasekit.branch import resolve_default_branch
from releasekit.bump import BumpTarget, bump_file, bump_pyproject
from releasekit.changelog import generate_changelog, render_changelog, write_changelog
from releasekit.config import ReleaseConfig, WorkspaceConfig, build_package_configs
from releasekit.graph import build_graph, topo_sort
from releasekit.logging import get_logger
from releasekit.preflight import run_preflight
from releasekit.tags import format_tag
from releasekit.utils.date import utc_iso, utc_today
from releasekit.versioning import compute_bumps
from releasekit.versions import PackageVersion, ReleaseManifest, resolve_umbrella_version
from releasekit.workspace import Package, discover_packages

logger = get_logger(__name__)

_RELEASE_BRANCH_PREFIX = 'releasekit--release'
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


# GitHub's maximum PR body size.
_GITHUB_BODY_LIMIT: int = 65_536

# Safety margin so the manifest + boilerplate always fit.
_MANIFEST_RESERVE: int = 8_192


def _build_pr_body(
    changelogs: dict[str, str],
    manifest_json: str,
    umbrella_version: str,
) -> str:
    """Build the Release PR body with changelogs and embedded manifest.

    If the body would exceed GitHub's 65,536-character limit, changelogs
    are progressively dropped (largest first) and replaced with a
    truncation notice.  The embedded manifest is always preserved.
    """
    # Sort once, reuse for both table and detail blocks.
    sorted_changelogs = sorted(changelogs.items())

    # --- 1. Build a compact summary table. ---
    header_lines = [
        f'# Release v{umbrella_version}',
        '',
        f'This release includes **{len(changelogs)}** package(s).',
        '',
        '| Package | Version heading |',
        '|---------|----------------|',
    ]
    for pkg_name, changelog_md in sorted_changelogs:
        # Extract the first heading line (## x.y.z ...) as the summary.
        first_heading = ''
        for cl_line in changelog_md.splitlines():
            if cl_line.startswith('## '):
                first_heading = cl_line.lstrip('# ').strip()
                break
        header_lines.append(f'| `{pkg_name}` | {first_heading} |')
    header_lines.append('')

    # --- 2. Build collapsible changelog sections. ---
    detail_blocks: list[tuple[str, str]] = []
    for pkg_name, changelog_md in sorted_changelogs:
        block = f'<details><summary><b>{pkg_name}</b></summary>\n\n{changelog_md}\n</details>\n'
        detail_blocks.append((pkg_name, block))

    # --- 3. Assemble and check size, truncating if needed. ---
    header = '\n'.join(header_lines)
    manifest_block = _embed_manifest('', manifest_json)
    # Budget available for changelog details.
    budget = _GITHUB_BODY_LIMIT - len(header) - len(manifest_block) - _MANIFEST_RESERVE

    included: list[str] = []
    dropped: list[str] = []
    used = 0
    # Sort smallest-first so the largest changelogs are dropped first.
    for pkg_name, block in sorted(detail_blocks, key=lambda item: len(item[1])):
        if used + len(block) <= budget:
            included.append(block)
            used += len(block)
        else:
            dropped.append(pkg_name)

    parts = [header]
    if included:
        parts.append('## Changelogs\n')
        parts.extend(included)
    if dropped:
        parts.append(
            f'\n> **Note:** {len(dropped)} changelog(s) omitted to stay '
            f'within the PR body size limit. See individual CHANGELOG.md '
            f'files for full details.\n'
        )

    body = '\n'.join(parts)
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
    ws_config: WorkspaceConfig,
    dry_run: bool = False,
    force: bool = False,
    prerelease: str = '',
    bump_override: str = '',
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
        config: Global release configuration.
        ws_config: Per-workspace configuration.
        dry_run: If True, skip all side effects.
        force: If True, skip preflight and force bumps.
        prerelease: Prerelease label (e.g. ``"rc.1"``). If set, all bumps
            produce prerelease versions.
        bump_override: Override bump type (``"patch"``, ``"minor"``,
            ``"major"``). Empty string means auto-detect from commits.

    Returns:
        A :class:`PrepareResult` with bumped packages and PR URL.
    """
    result = PrepareResult()

    # 1. Discover packages and build dependency graph.
    packages = discover_packages(workspace_root, exclude_patterns=ws_config.exclude)
    graph = build_graph(packages)
    topo_sort(graph)  # Validate DAG (raises on cycles).

    # 2. Compute version bumps.
    # Pass the graph only when propagation is enabled and not in synchronized mode.
    propagate_graph = graph if (ws_config.propagate_bumps and not ws_config.synchronize) else None
    pkg_configs = build_package_configs(ws_config, [p.name for p in packages])
    versions = await compute_bumps(
        packages,
        vcs,
        tag_format=ws_config.tag_format,
        prerelease=prerelease,
        force_unchanged=bool(bump_override),
        graph=propagate_graph,
        synchronize=ws_config.synchronize,
        major_on_zero=ws_config.major_on_zero,
        max_commits=ws_config.max_commits,
        bootstrap_sha=ws_config.bootstrap_sha,
        versioning_scheme=ws_config.versioning_scheme,
        package_configs=pkg_configs,
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
            bump_pyproject(pkg.manifest_path, ver.new_version)
        logger.info('bumped', package=ver.name, old=ver.old_version, new=ver.new_version)

    # 4b. Bump extra files (e.g. __init__.py with __version__).
    if ws_config.extra_files and not dry_run:
        for entry in ws_config.extra_files:
            if ':' in entry:
                file_path_str, pattern = entry.split(':', 1)
            else:
                file_path_str = entry
                pattern = ''
            extra_path = workspace_root / file_path_str
            if extra_path.exists():
                target = BumpTarget(path=extra_path, pattern=pattern) if pattern else BumpTarget(path=extra_path)
                for ver in bumped:
                    try:
                        bump_file(target, ver.new_version)
                        logger.info('extra_file_bumped', path=file_path_str, version=ver.new_version)
                        break
                    except Exception as exc:  # noqa: BLE001
                        logger.debug('extra_file_skip', path=file_path_str, package=ver.name, error=str(exc))
                        continue

    # 5. Update lock file.
    if not dry_run:
        for ver in bumped:
            await pm.lock(upgrade_package=ver.name)

    # 6. Generate changelogs.
    today = utc_today()
    pkg_paths = _package_paths(packages)
    for ver in bumped:
        since_tag = format_tag(ws_config.tag_format, name=ver.name, version=ver.old_version, label=ws_config.label)
        # Fall back to bootstrap_sha (or None for full history) when the
        # per-package tag doesn't exist yet — e.g. on the very first release.
        if not await vcs.tag_exists(since_tag):
            since_tag = ws_config.bootstrap_sha or None
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

    # 6b. Write per-package CHANGELOG.md files.
    for ver in bumped:
        pkg = pkg_by_name.get(ver.name)
        if pkg is None:
            continue
        rendered = result.changelogs.get(ver.name, '')
        if rendered and not dry_run:
            changelog_path = pkg.path / 'CHANGELOG.md'
            write_changelog(changelog_path, rendered)

    # 7. Build and save manifest.
    git_sha = await vcs.current_sha()
    umbrella_version = resolve_umbrella_version(bumped, core_package=ws_config.core_package)
    umbrella_tag = format_tag(ws_config.umbrella_tag, version=umbrella_version, label=ws_config.label)
    manifest = ReleaseManifest(
        git_sha=git_sha,
        umbrella_tag=umbrella_tag,
        packages=versions,
        created_at=utc_iso(),
    )
    result.manifest = manifest

    release_branch = f'{_RELEASE_BRANCH_PREFIX}--{ws_config.label}' if ws_config.label else _RELEASE_BRANCH_PREFIX
    manifest_name = f'release-manifest--{ws_config.label}.json' if ws_config.label else 'release-manifest.json'
    manifest_path = workspace_root / manifest_name
    if not dry_run:
        manifest.save(manifest_path)

    # 8. Commit and push on release branch.
    commit_msg = config.pr_title_template.replace('{version}', umbrella_version)
    if not dry_run:
        await vcs.checkout_branch(release_branch, create=True)
        await vcs.commit(commit_msg, paths=['.'])
        # Force-push because the release branch is recreated from
        # scratch on each prepare run (checkout -B resets to HEAD).
        # If the remote already has the branch from a previous run,
        # a normal push fails with non-fast-forward.
        push_result = await vcs.push(force=True)
        if not push_result.ok:
            raise RuntimeError(f'Failed to push release branch {release_branch!r}: {push_result.stderr.strip()}')
    logger.info('release_branch_pushed', branch=release_branch, sha=git_sha)

    # 9. Create or update Release PR.
    if dry_run:
        manifest_json = json.dumps({'dry_run': True, 'bumped': len(bumped)}, indent=2)
    else:
        manifest_json = manifest_path.read_text(encoding='utf-8')

    pr_body = _build_pr_body(result.changelogs, manifest_json, umbrella_version)
    pr_title = config.pr_title_template.replace('{version}', umbrella_version)

    if forge is not None and await forge.is_available():
        # Check if a Release PR already exists for this branch.
        existing_prs = await forge.list_prs(head=release_branch, state='open', limit=1)
        if existing_prs:
            pr_number = existing_prs[0].get('number', 0)
            if not dry_run:
                await forge.update_pr(pr_number, title=pr_title, body=pr_body)
            result.pr_url = existing_prs[0].get('url', f'PR #{pr_number}')
            logger.info('release_pr_updated', pr=pr_number)
        else:
            if not dry_run:
                base = await resolve_default_branch(vcs, config.default_branch)
                pr_result = await forge.create_pr(
                    title=pr_title,
                    body=pr_body,
                    head=release_branch,
                    base=base,
                )
                if pr_result.ok:
                    result.pr_url = pr_result.stdout.strip()
                else:
                    raise RuntimeError(
                        f'Failed to create Release PR for branch {release_branch!r}: {pr_result.stderr[:500].strip()}'
                    )
            logger.info('release_pr_created', branch=release_branch)

        # Add "autorelease: pending" label to both new and existing PRs.
        if not dry_run:
            # For existing PRs, use the known number. For new PRs,
            # extract the number from the PR URL returned by create_pr.
            label_pr_number = 0
            if existing_prs:
                label_pr_number = existing_prs[0].get('number', 0)
            elif result.pr_url:
                # PR URL typically ends with the PR number.
                try:
                    label_pr_number = int(result.pr_url.rstrip('/').rsplit('/', 1)[-1])
                except (ValueError, IndexError):
                    logger.warning('cannot_parse_pr_number', url=result.pr_url)
            if label_pr_number:
                await forge.add_labels(label_pr_number, [_AUTORELEASE_PENDING])

            # 10. Auto-merge the Release PR if configured.
            if ws_config.auto_merge and label_pr_number:
                merge_result = await forge.merge_pr(
                    label_pr_number,
                    method='squash',
                    commit_message=commit_msg,
                    delete_branch=True,
                    dry_run=dry_run,
                )
                if merge_result.ok:
                    logger.info('release_pr_auto_merged', pr=label_pr_number)
                else:
                    logger.warning('release_pr_auto_merge_failed', pr=label_pr_number, stderr=merge_result.stderr)

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
