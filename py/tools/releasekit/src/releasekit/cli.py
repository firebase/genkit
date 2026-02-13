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

"""CLI entry point for releasekit.

Constructs backend instances and injects them into the pipeline modules.
Provides subcommands for the full release workflow.

Subcommands::

    releasekit publish    Publish all changed packages to PyPI
    releasekit plan       Preview the execution plan (no publish)
    releasekit changelog  Generate per-package CHANGELOG.md files
    releasekit discover   List all workspace packages
    releasekit graph      Show the dependency graph
    releasekit version    Show computed version bumps
    releasekit explain    Explain an error code

Usage::

    # Preview what would be published:
    uvx releasekit plan

    # Publish all changed packages:
    uvx releasekit publish --dry-run
    uvx releasekit publish --force

    # Show workspace packages:
    uvx releasekit discover

    # Explain an error:
    uvx releasekit explain RK-PREFLIGHT-DIRTY-WORKTREE
"""

from __future__ import annotations

import argparse
import asyncio
import fnmatch
import json
import sys
from pathlib import Path

from rich_argparse import RichHelpFormatter

from releasekit import __version__
from releasekit.backends._run import CommandResult
from releasekit.backends.forge import Forge, GitHubAPIBackend, GitHubCLIBackend
from releasekit.backends.forge.bitbucket import BitbucketAPIBackend
from releasekit.backends.forge.gitlab import GitLabCLIBackend
from releasekit.backends.pm import UvBackend
from releasekit.backends.registry import PyPIBackend
from releasekit.backends.vcs import GitCLIBackend
from releasekit.checks import (
    PythonCheckBackend,
    fix_missing_license,
    fix_missing_readme,
    fix_stale_artifacts,
    run_checks,
)
from releasekit.config import ReleaseConfig, load_config, resolve_group_refs
from releasekit.detection import (
    DetectedEcosystem,
    Ecosystem,
    detect_ecosystems,
    find_monorepo_root,
)
from releasekit.errors import E, ReleaseKitError, explain, render_error
from releasekit.formatters import FORMATTERS, format_graph
from releasekit.graph import build_graph, topo_sort
from releasekit.groups import filter_by_group
from releasekit.init import print_scaffold_preview, scaffold_config
from releasekit.lock import release_lock
from releasekit.logging import get_logger
from releasekit.plan import build_plan
from releasekit.preflight import run_preflight
from releasekit.prepare import prepare_release
from releasekit.publisher import PublishConfig, publish_workspace
from releasekit.release import tag_release
from releasekit.ui import create_progress_ui
from releasekit.versioning import compute_bumps
from releasekit.versions import ReleaseManifest
from releasekit.workspace import Package, discover_packages

logger = get_logger(__name__)


def _find_workspace_root() -> Path:
    """Find the workspace root by walking up from CWD.

    Backward-compatible helper for commands that still use the legacy
    ``discover_packages()`` function (which is uv-only). Walks up
    from CWD looking for ``pyproject.toml`` with ``[tool.uv.workspace]``.

    For multi-ecosystem discovery, use :func:`_resolve_ecosystems` instead.

    Returns:
        Absolute path to the workspace root.

    Raises:
        ReleaseKitError: If no workspace root is found.
    """
    cwd = Path.cwd().resolve()
    for parent in [cwd, *cwd.parents]:
        pyproject = parent / 'pyproject.toml'
        if pyproject.exists():
            text = pyproject.read_text(encoding='utf-8')
            if '[tool.uv.workspace]' in text:
                return parent
    raise ReleaseKitError(
        E.WORKSPACE_NOT_FOUND,
        'Could not find a pyproject.toml with [tool.uv.workspace].',
        hint='Run this command from within a uv workspace.',
    )


def _get_ecosystem_filter(args: argparse.Namespace) -> Ecosystem | None:
    """Extract ``--ecosystem`` filter from parsed args.

    Returns:
        The ecosystem enum value, or ``None`` if not specified.
    """
    eco_str = getattr(args, 'ecosystem', None)
    if eco_str is None:
        return None
    for member in list(Ecosystem):
        if member.value == eco_str:
            return member
    return None


def _resolve_ecosystems(
    args: argparse.Namespace,
) -> tuple[Path, list[DetectedEcosystem]]:
    """Detect the monorepo root and all ecosystems.

    Combines :func:`find_monorepo_root` and :func:`detect_ecosystems`
    with optional ``--ecosystem`` filtering.

    Returns:
        Tuple of (monorepo_root, detected_ecosystems).
    """
    monorepo_root = find_monorepo_root()
    eco_filter = _get_ecosystem_filter(args)
    ecosystems = detect_ecosystems(monorepo_root, ecosystem_filter=eco_filter)
    return monorepo_root, ecosystems


class _NullForge:
    """No-op forge backend for ``forge = "none"`` configuration.

    All methods return empty/successful results so the pipeline can
    run without a code forge (e.g. for local-only or registry-only
    workflows).
    """

    _NOOP = CommandResult(command=[], returncode=0, stdout='', stderr='')

    async def is_available(self) -> bool:
        return False

    async def create_release(
        self,
        tag: str,
        *,
        title: str | None = None,
        body: str = '',
        draft: bool = False,
        prerelease: bool = False,
        assets: list[Path] | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        return self._NOOP

    async def delete_release(self, tag: str, *, dry_run: bool = False) -> CommandResult:
        return self._NOOP

    async def promote_release(self, tag: str, *, dry_run: bool = False) -> CommandResult:
        return self._NOOP

    async def list_releases(self, *, limit: int = 10) -> list[dict[str, object]]:
        return []

    async def create_pr(
        self,
        *,
        title: str,
        body: str = '',
        head: str,
        base: str = 'main',
        dry_run: bool = False,
    ) -> CommandResult:
        return self._NOOP

    async def pr_data(self, pr_number: int) -> dict[str, object]:
        return {}

    async def list_prs(
        self,
        *,
        label: str = '',
        state: str = 'open',
        head: str = '',
        limit: int = 10,
    ) -> list[dict[str, object]]:
        return []

    async def add_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        return self._NOOP

    async def remove_labels(
        self,
        pr_number: int,
        labels: list[str],
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        return self._NOOP

    async def update_pr(
        self,
        pr_number: int,
        *,
        title: str = '',
        body: str = '',
        dry_run: bool = False,
    ) -> CommandResult:
        return self._NOOP

    async def merge_pr(
        self,
        pr_number: int,
        *,
        method: str = 'squash',
        commit_message: str = '',
        delete_branch: bool = True,
        dry_run: bool = False,
    ) -> CommandResult:
        return self._NOOP


def _create_backends(
    workspace_root: Path,
    config: ReleaseConfig,
    *,
    forge_backend: str = 'cli',
) -> tuple[GitCLIBackend, UvBackend, Forge, PyPIBackend]:
    """Create real backend instances for production use.

    The forge backend is determined by ``config.forge`` (github, gitlab,
    bitbucket, none) and the ``forge_backend`` transport hint (cli vs api).
    Repository coordinates come from ``config.repo_owner`` and
    ``config.repo_name``.

    Args:
        workspace_root: Workspace root directory.
        config: Release configuration.
        forge_backend: Transport hint: ``"cli"`` for CLI-based backends,
            ``"api"`` for REST API-based backends (where available).

    Returns:
        Tuple of (VCS, PackageManager, Forge, Registry) backends.
    """
    vcs = GitCLIBackend(workspace_root)
    pm = UvBackend(workspace_root)

    owner = config.repo_owner
    repo = config.repo_name
    repo_slug = f'{owner}/{repo}' if owner and repo else ''

    forge: Forge
    forge_type = config.forge

    if forge_type == 'none':
        forge = _NullForge()
    elif forge_type == 'gitlab':
        forge = GitLabCLIBackend(project=repo_slug, cwd=workspace_root)
    elif forge_type == 'bitbucket':
        forge = BitbucketAPIBackend(workspace=owner, repo_slug=repo)
    elif forge_backend == 'api':
        forge = GitHubAPIBackend(owner=owner, repo=repo)
    else:
        forge = GitHubCLIBackend(repo=repo_slug, cwd=workspace_root)

    registry = PyPIBackend(pool_size=config.http_pool_size)
    return vcs, pm, forge, registry


def _maybe_filter_group(
    packages: list[Package],
    config: ReleaseConfig,
    group: str | None,
) -> list[Package]:
    """Optionally filter packages by release group.

    If ``group`` is None, returns all packages unchanged.
    Otherwise, filters to only packages matching the named group.
    """
    if group is None:
        return packages

    return filter_by_group(packages, groups=config.groups, group=group)


def _match_exclude_patterns(name: str, patterns: list[str]) -> bool:
    """Return True if *name* matches any of the glob *patterns*."""
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)


# ── Subcommand handlers ──────────────────────────────────────────────


async def _cmd_publish(args: argparse.Namespace) -> int:
    """Handle the ``publish`` subcommand."""
    workspace_root = _find_workspace_root()
    config = load_config(workspace_root)
    forge_backend = getattr(args, 'forge_backend', 'cli')
    vcs, pm, forge, registry = _create_backends(
        workspace_root,
        config,
        forge_backend=forge_backend,
    )

    # Discover and analyze — all packages participate in checks + version bumps.
    all_packages = discover_packages(workspace_root, exclude_patterns=config.exclude)
    group = getattr(args, 'group', None)
    packages = _maybe_filter_group(all_packages, config, group)
    graph = build_graph(packages)
    levels = topo_sort(graph)
    versions = await compute_bumps(
        packages,
        vcs,
        tag_format=config.tag_format,
        prerelease='',
        force_unchanged=args.force_unchanged,
    )

    # Filter out exclude_bump packages — they are discovered + checked but not bumped.
    resolved_exclude_bump = resolve_group_refs(config.exclude_bump, config.groups)
    if resolved_exclude_bump:
        bump_excluded = {p.name for p in packages if _match_exclude_patterns(p.name, resolved_exclude_bump)}
        if bump_excluded:
            logger.info('exclude_bump', count=len(bump_excluded), names=sorted(bump_excluded))
        packages = [p for p in packages if p.name not in bump_excluded]
        versions = [v for v in versions if v.name not in bump_excluded]
        graph = build_graph(packages)
        levels = topo_sort(graph)

    # Filter out exclude_publish packages — they get version bumps but not published.
    resolved_exclude_publish = resolve_group_refs(config.exclude_publish, config.groups)
    if resolved_exclude_publish:
        pub_excluded = {p.name for p in packages if _match_exclude_patterns(p.name, resolved_exclude_publish)}
        if pub_excluded:
            logger.info('exclude_publish', count=len(pub_excluded), names=sorted(pub_excluded))
        packages = [p for p in packages if p.name not in pub_excluded]
        versions = [v for v in versions if v.name not in pub_excluded]
        graph = build_graph(packages)
        levels = topo_sort(graph)

    # Check for any actual bumps.
    bumped = [v for v in versions if not v.skipped]
    if not bumped:
        logger.info('nothing_to_publish', message='No packages have changes to publish.')
        return 0

    # Build execution plan for preview.
    plan = build_plan(versions, levels, exclude_names=config.exclude, git_sha=await vcs.current_sha())

    if not args.force and not args.dry_run:
        print(plan.format_table())  # noqa: T201 - CLI output
        print()  # noqa: T201 - CLI output
        if sys.stdin.isatty():
            answer = await asyncio.to_thread(input, f'Publish {len(bumped)} package(s)? [y/N] ')
            if answer.lower() not in {'y', 'yes'}:
                logger.info('publish_cancelled')
                return 1

    # Preflight.
    with release_lock(workspace_root):
        preflight = await run_preflight(
            vcs=vcs,
            pm=pm,
            forge=forge,
            registry=registry,
            packages=packages,
            graph=graph,
            versions=versions,
            workspace_root=workspace_root,
            dry_run=args.dry_run,
            skip_version_check=args.force,
        )
        if not preflight.ok:
            for name, error in preflight.errors.items():
                logger.error('preflight_blocked', check=name, error=error)
            return 1

        # Publish.
        pub_config = PublishConfig(
            concurrency=args.concurrency,
            dry_run=args.dry_run,
            check_url=args.check_url,
            index_url=args.index_url,
            smoke_test=config.smoke_test,
            max_retries=args.max_retries,
            retry_base_delay=args.retry_base_delay,
            task_timeout=args.task_timeout,
            force=args.force,
            workspace_root=workspace_root,
        )

        # Create progress UI (Rich table for TTY, log lines for CI).
        progress_ui = create_progress_ui(
            total_packages=len(packages),
            total_levels=len(levels),
            concurrency=args.concurrency,
        )

        with progress_ui:
            result = await publish_workspace(
                vcs=vcs,
                pm=pm,
                forge=forge,
                registry=registry,
                graph=graph,
                packages=packages,
                levels=levels,
                versions=versions,
                config=pub_config,
                observer=progress_ui,
            )

    logger.info('publish_result', summary=result.summary())

    if not result.ok:
        for name, error in result.failed.items():
            logger.error('publish_failed', package=name, error=error)
        return 1

    # Save manifest.
    manifest = ReleaseManifest(
        git_sha=await vcs.current_sha(),
        packages=versions,
    )
    manifest_path = workspace_root / 'release-manifest.json'
    manifest.save(manifest_path)
    logger.info('manifest_saved', path=str(manifest_path))

    return 0


async def _cmd_plan(args: argparse.Namespace) -> int:
    """Handle the ``plan`` subcommand."""
    workspace_root = _find_workspace_root()
    config = load_config(workspace_root)
    vcs, _pm, _forge, registry = _create_backends(workspace_root, config)

    all_packages = discover_packages(workspace_root, exclude_patterns=config.exclude)
    group = getattr(args, 'group', None)
    packages = _maybe_filter_group(all_packages, config, group)
    graph = build_graph(packages)
    levels = topo_sort(graph)
    versions = await compute_bumps(
        packages,
        vcs,
        tag_format=config.tag_format,
        force_unchanged=args.force_unchanged,
    )

    # Check which versions are already published.
    already_published: set[str] = set()
    for v in versions:
        if not v.skipped and await registry.check_published(v.name, v.new_version):
            already_published.add(v.name)

    plan = build_plan(
        versions,
        levels,
        exclude_names=config.exclude,
        already_published=already_published,
        git_sha=await vcs.current_sha(),
    )

    fmt = getattr(args, 'format', 'table')
    if fmt == 'json':
        print(plan.format_json())  # noqa: T201 - CLI output
    elif fmt == 'csv':
        print(plan.format_csv())  # noqa: T201 - CLI output
    elif fmt == 'ascii':
        print(plan.format_ascii_flow())  # noqa: T201 - CLI output
    elif fmt == 'full':
        print(plan.format_ascii_flow())  # noqa: T201 - CLI output
        print()  # noqa: T201 - CLI output
        print(plan.format_table())  # noqa: T201 - CLI output
    else:
        print(plan.format_table())  # noqa: T201 - CLI output

    return 0


def _cmd_discover(args: argparse.Namespace) -> int:
    """Handle the ``discover`` subcommand.

    Discovers packages across all detected ecosystems (or a
    specific one if ``--ecosystem`` is provided).  Falls back
    to the legacy uv-only path when a specific ecosystem's
    Workspace backend is not yet implemented.
    """
    monorepo_root, ecosystems = _resolve_ecosystems(args)
    config = load_config(monorepo_root)
    group = getattr(args, 'group', None)
    fmt = getattr(args, 'format', 'table')

    if not ecosystems:
        # Fall back to legacy uv-only discovery.
        workspace_root = _find_workspace_root()
        all_packages = discover_packages(workspace_root, exclude_patterns=config.exclude)
        packages = _maybe_filter_group(all_packages, config, group)
        _print_packages(packages, fmt, ecosystem_label=None)
        return 0

    all_data: list[dict[str, object]] = []
    for eco in ecosystems:
        if eco.workspace is None:
            logger.warning(
                'ecosystem_no_backend',
                ecosystem=eco.ecosystem.value,
                root=str(eco.root),
                hint=f'{eco.ecosystem.value} workspace backend not yet implemented.',
            )
            continue

        try:
            eco_packages = asyncio.run(eco.workspace.discover(exclude_patterns=config.exclude))
        except ReleaseKitError as exc:
            # Don't let one ecosystem's error block discovery of others.
            logger.warning(
                'ecosystem_discover_failed',
                ecosystem=eco.ecosystem.value,
                root=str(eco.root),
                error=str(exc),
            )
            continue

        # Convert WsPackage → legacy Package for group filtering compatibility.
        legacy = [
            Package(
                name=p.name,
                version=p.version,
                path=p.path,
                pyproject_path=p.manifest_path,
                internal_deps=list(p.internal_deps),
                external_deps=list(p.external_deps),
                all_deps=list(p.all_deps),
                is_publishable=p.is_publishable,
            )
            for p in eco_packages
        ]
        filtered = _maybe_filter_group(legacy, config, group)
        _print_packages(filtered, fmt, ecosystem_label=eco.ecosystem.value, data_acc=all_data)

    if fmt == 'json' and all_data:
        print(json.dumps(all_data, indent=2))  # noqa: T201 - CLI output

    return 0


def _print_packages(
    packages: list[Package],
    fmt: str,
    *,
    ecosystem_label: str | None = None,
    data_acc: list[dict[str, object]] | None = None,
) -> None:
    """Print packages in the requested format.

    Args:
        packages: Packages to display.
        fmt: Output format (``"table"`` or ``"json"``).
        ecosystem_label: If set, used to annotate output.
        data_acc: If fmt is json, append dicts here instead of printing.
    """
    if fmt == 'json':
        for p in packages:
            entry: dict[str, object] = {
                'name': p.name,
                'version': p.version,
                'path': str(p.path),
                'internal_deps': p.internal_deps,
                'publishable': p.is_publishable,
            }
            if ecosystem_label:
                entry['ecosystem'] = ecosystem_label
            if data_acc is not None:
                data_acc.append(entry)
    else:
        if ecosystem_label:
            print(f'\n  ── {ecosystem_label} ({len(packages)} packages) ──')  # noqa: T201 - CLI output
        for pkg in packages:
            deps = ', '.join(pkg.internal_deps) if pkg.internal_deps else '(none)'
            pub = '' if pkg.is_publishable else ' [private]'
            print(f'  {pkg.name} {pkg.version} ({pkg.path}){pub}')  # noqa: T201 - CLI output
            print(f'    deps: {deps}')  # noqa: T201 - CLI output


def _cmd_graph(args: argparse.Namespace) -> int:
    """Handle the ``graph`` subcommand."""
    workspace_root = _find_workspace_root()
    config = load_config(workspace_root)
    packages = discover_packages(workspace_root, exclude_patterns=config.exclude)
    graph = build_graph(packages)

    fmt = getattr(args, 'format', 'levels')
    output = format_graph(graph, packages, fmt=fmt)
    print(output, end='')  # noqa: T201 - CLI output

    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    """Handle the ``check`` subcommand."""
    workspace_root = _find_workspace_root()
    config = load_config(workspace_root)
    packages = discover_packages(workspace_root, exclude_patterns=config.exclude)
    graph = build_graph(packages)

    resolved_exclude_publish = resolve_group_refs(config.exclude_publish, config.groups)

    # --fix: auto-fix issues before running checks.
    if getattr(args, 'fix', False):
        all_changes: list[str] = []

        # Universal fixers (ecosystem-agnostic).
        all_changes.extend(fix_missing_readme(packages))
        all_changes.extend(fix_missing_license(packages))
        all_changes.extend(fix_stale_artifacts(packages))

        # Language-specific fixers (via backend).
        backend = PythonCheckBackend(
            core_package=config.core_package,
            plugin_prefix=config.plugin_prefix,
            namespace_dirs=config.namespace_dirs,
            library_dirs=config.library_dirs,
            plugin_dirs=config.plugin_dirs,
        )
        all_changes.extend(
            backend.run_fixes(
                packages,
                exclude_publish=resolved_exclude_publish,
                repo_owner=config.repo_owner,
                repo_name=config.repo_name,
                namespace_dirs=config.namespace_dirs,
                library_dirs=config.library_dirs,
                plugin_dirs=config.plugin_dirs,
            )
        )

        if all_changes:
            for change in all_changes:
                print(f'  🔧 {change}')  # noqa: T201 - CLI output
            print()  # noqa: T201 - CLI output
            # Re-discover packages so checks see the updated state.
            packages = discover_packages(workspace_root, exclude_patterns=config.exclude)
            graph = build_graph(packages)

    result = run_checks(
        packages,
        graph,
        exclude_publish=resolved_exclude_publish,
        groups=config.groups,
        workspace_root=workspace_root,
        core_package=config.core_package,
        plugin_prefix=config.plugin_prefix,
        namespace_dirs=config.namespace_dirs,
        library_dirs=config.library_dirs,
        plugin_dirs=config.plugin_dirs,
    )

    # Print detailed results.
    if result.passed:
        for name in result.passed:
            print(f'  ✅ {name}')  # noqa: T201 - CLI output
    if result.warnings:
        for name in result.warnings:
            msg = result.warning_messages.get(name, '')
            print(f'  ⚠️  {name}: {msg}')  # noqa: T201 - CLI output
            hint = result.hints.get(name, '')
            if hint:
                print(f'     = hint: {hint}')  # noqa: T201 - CLI output
    if result.failed:
        for name in result.failed:
            msg = result.errors.get(name, '')
            print(f'  ❌ {name}: {msg}')  # noqa: T201 - CLI output
            hint = result.hints.get(name, '')
            if hint:
                print(f'     = hint: {hint}')  # noqa: T201 - CLI output

    print()  # noqa: T201 - CLI output
    print(f'  {result.summary()}')  # noqa: T201 - CLI output

    return 0 if result.ok else 1


async def _cmd_version(args: argparse.Namespace) -> int:
    """Handle the ``version`` subcommand."""
    workspace_root = _find_workspace_root()
    config = load_config(workspace_root)
    vcs, _pm, _forge, _registry = _create_backends(workspace_root, config)

    packages = discover_packages(workspace_root, exclude_patterns=config.exclude)

    # Filter out exclude_bump packages before computing bumps.
    resolved_exclude_bump = resolve_group_refs(config.exclude_bump, config.groups)
    if resolved_exclude_bump:
        bump_excluded = {p.name for p in packages if _match_exclude_patterns(p.name, resolved_exclude_bump)}
        if bump_excluded:
            logger.info('exclude_bump', count=len(bump_excluded), names=sorted(bump_excluded))
        packages = [p for p in packages if p.name not in bump_excluded]

    versions = await compute_bumps(
        packages,
        vcs,
        tag_format=config.tag_format,
        force_unchanged=args.force_unchanged,
    )

    fmt = getattr(args, 'format', 'table')
    if fmt == 'json':
        data = [
            {
                'name': v.name,
                'old_version': v.old_version,
                'new_version': v.new_version,
                'bump': v.bump,
                'reason': v.reason,
                'skipped': v.skipped,
                'tag': v.tag,
            }
            for v in versions
        ]
        print(json.dumps(data, indent=2))  # noqa: T201 - CLI output
    else:
        for v in versions:
            emoji = '⏭️' if v.skipped else '📦'
            print(f'  {emoji} {v.name}: {v.old_version} → {v.new_version} ({v.bump})')  # noqa: T201 - CLI output
            if v.reason:
                print(f'     {v.reason}')  # noqa: T201 - CLI output

    return 0


async def _cmd_changelog(args: argparse.Namespace) -> int:
    """Handle the ``changelog`` subcommand.

    Generates per-package changelogs from Conventional Commits and
    writes them to ``CHANGELOG.md`` in each package directory.
    """
    from datetime import datetime, timezone

    from releasekit.changelog import generate_changelog, render_changelog, write_changelog
    from releasekit.tags import format_tag

    workspace_root = _find_workspace_root()
    config = load_config(workspace_root)
    vcs, _pm, _forge, _registry = _create_backends(workspace_root, config)

    all_packages = discover_packages(workspace_root, exclude_patterns=config.exclude)
    group = getattr(args, 'group', None)
    packages = _maybe_filter_group(all_packages, config, group)

    dry_run = getattr(args, 'dry_run', False)
    today = datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')

    written = 0
    skipped = 0

    for pkg in packages:
        # Find the last tag for this package to scope the log.
        tag = format_tag(config.tag_format, name=pkg.name, version=pkg.version)
        tag_exists = await vcs.tag_exists(tag)
        since_tag = tag if tag_exists else None

        changelog = await generate_changelog(
            vcs=vcs,
            version=pkg.version,
            since_tag=since_tag,
            paths=[str(pkg.path)],
            date=today,
        )

        if not changelog.sections:
            skipped += 1
            continue

        rendered = render_changelog(changelog)
        changelog_path = pkg.path / 'CHANGELOG.md'

        if write_changelog(changelog_path, rendered, dry_run=dry_run):
            written += 1
            print(f'  📝 {pkg.name}: {changelog_path}')  # noqa: T201 - CLI output
        else:
            skipped += 1
            print(f'  ⏭️  {pkg.name}: already up to date')  # noqa: T201 - CLI output

    print()  # noqa: T201 - CLI output
    print(f'  {written} written, {skipped} skipped')  # noqa: T201 - CLI output
    return 0


def _cmd_explain(args: argparse.Namespace) -> int:
    """Handle the ``explain`` subcommand."""
    result = explain(args.code)
    if result is None:
        print(f'Unknown error code: {args.code}')  # noqa: T201 - CLI output
        return 1
    print(result)  # noqa: T201 - CLI output
    return 0


def _cmd_init(args: argparse.Namespace) -> int:
    """Handle the ``init`` subcommand.

    Detects all ecosystems in the monorepo and scaffolds a
    ``releasekit.toml`` at the monorepo root.  If ``--ecosystem``
    is specified, only that ecosystem is included in the generated
    config.
    """
    monorepo_root, ecosystems = _resolve_ecosystems(args)
    dry_run = getattr(args, 'dry_run', False)
    force = getattr(args, 'force', False)

    if ecosystems:
        eco_summary = ', '.join(f'{e.ecosystem.value} ({e.root.relative_to(monorepo_root)})' for e in ecosystems)
        logger.info('init_detected_ecosystems', ecosystems=eco_summary)

    # Use the first uv workspace root for backward compatibility
    # with the single-ecosystem scaffold_config.
    uv_ecosystems = [e for e in ecosystems if e.ecosystem == Ecosystem.PYTHON]
    workspace_root = uv_ecosystems[0].root if uv_ecosystems else monorepo_root

    toml_fragment = scaffold_config(
        workspace_root,
        dry_run=dry_run,
        force=force,
    )

    if toml_fragment:
        print_scaffold_preview(toml_fragment)
        if not dry_run:
            print('  ✅ Configuration written')  # noqa: T201 - CLI output
    elif not dry_run:
        print('  ℹ️  releasekit.toml already exists (use --force to overwrite)')  # noqa: T201 - CLI output

    return 0


async def _cmd_rollback(args: argparse.Namespace) -> int:
    """Handle the ``rollback`` subcommand."""
    workspace_root = _find_workspace_root()
    config = load_config(workspace_root)
    vcs, _pm, forge, _registry = _create_backends(workspace_root, config)
    dry_run = getattr(args, 'dry_run', False)
    tag = args.tag

    deleted: list[str] = []

    # Delete the git tag (local + remote).
    if await vcs.tag_exists(tag):
        logger.info('Deleting tag %s', tag)
        await vcs.delete_tag(tag, remote=True, dry_run=dry_run)
        deleted.append(tag)
    else:
        logger.info('Tag %s does not exist locally', tag)

    # Delete the platform release if forge is available.
    if forge is not None and await forge.is_available():
        logger.info('Deleting platform release for %s', tag)
        try:
            await forge.delete_release(tag, dry_run=dry_run)
        except Exception as exc:
            logger.warning('Release deletion failed: %s', exc)
    else:
        logger.info('Forge not available, skipping release deletion')

    for t in deleted:
        print(f'  \U0001f5d1\ufe0f  Deleted tag: {t}')  # noqa: T201 - CLI output

    if not deleted:
        print(f'  \u2139\ufe0f  Tag {tag} not found')  # noqa: T201 - CLI output

    return 0


def _cmd_completion(args: argparse.Namespace) -> int:
    """Generate shell completion script.

    Outputs a completion script for the requested shell to stdout.
    Users install it by sourcing or placing in the appropriate directory.
    """
    shell = args.shell
    prog = 'releasekit'

    subcommands = [
        'changelog',
        'check',
        'completion',
        'discover',
        'explain',
        'graph',
        'init',
        'plan',
        'publish',
        'rollback',
        'version',
    ]
    formats = ['ascii', 'csv', 'd2', 'dot', 'json', 'levels', 'mermaid', 'table']

    if shell == 'bash':
        subcmd_words = ' '.join(subcommands)
        fmt_words = ' '.join(formats)
        graph_opts = '--format --rdeps --deps --packages --groups --exclude'
        pub_opts = (
            '--dry-run --force --force-unchanged --concurrency'
            ' --no-tag --no-push --no-release --version-only --max-retries'
        )
        script = f'''\
# Bash completion for {prog}
# Add to ~/.bashrc: eval "$({prog} completion bash)"
_{prog}_completions() {{
    local cur prev commands
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    commands="{subcmd_words}"

    if [[ $COMP_CWORD -eq 1 ]]; then
        COMPREPLY=($(compgen -W "$commands" -- "$cur"))
        return
    fi

    case "$prev" in
        graph)
            COMPREPLY=($(compgen -W "{graph_opts}" -- "$cur"))
            ;;
        --format)
            COMPREPLY=($(compgen -W "{fmt_words}" -- "$cur"))
            ;;
        completion)
            COMPREPLY=($(compgen -W "bash zsh fish" -- "$cur"))
            ;;
        publish)
            COMPREPLY=($(compgen -W "{pub_opts}" -- "$cur"))
            ;;
        *)
            COMPREPLY=($(compgen -W "--help --verbose --quiet" -- "$cur"))
            ;;
    esac
}}
complete -F _{prog}_completions {prog}
'''
    elif shell == 'zsh':
        subcmd_lines = '\n            '.join(f"'{cmd}:{cmd} subcommand'" for cmd in subcommands)
        script = f"""\
#compdef {prog}
# Zsh completion for {prog}
# Add to ~/.zshrc: eval "$({prog} completion zsh)"

_{prog}() {{
    local -a commands
    commands=(
            {subcmd_lines}
    )

    _arguments -C \\
        '1:command:->command' \\
        '*::arg:->args'

    case $state in
        command)
            _describe 'command' commands
            ;;
        args)
            case $words[1] in
                graph)
                    _arguments \\
                        '--format[Output format]:format:({' '.join(formats)})' \\
                        '--rdeps[Show reverse dependencies]' \\
                        '--deps[Show forward dependencies]' \\
                        '--packages[Filter packages]' \\
                        '--groups[Filter groups]' \\
                        '--exclude[Exclude packages]'
                    ;;
                completion)
                    _arguments '1:shell:(bash zsh fish)'
                    ;;
                publish)
                    _arguments \\
                        '--dry-run[Preview mode]' \\
                        '--force[Skip confirmation]' \\
                        '--force-unchanged[Include unchanged]' \\
                        '--concurrency[Max parallel]:n:' \\
                        '--no-tag[Skip tagging]' \\
                        '--no-push[Skip pushing]' \\
                        '--no-release[Skip releases]' \\
                        '--version-only[Version only]' \\
                        '--max-retries[Retry count]:n:'
                    ;;
            esac
            ;;
    esac
}}

_{prog} "$@"
"""
    elif shell == 'fish':
        subcmd_completions = '\n'.join(
            f"complete -c {prog} -n '__fish_use_subcommand' -a '{cmd}' -d '{cmd} subcommand'" for cmd in subcommands
        )
        format_completions = '\n'.join(
            f"complete -c {prog} -n '__fish_seen_subcommand_from graph' -l format -a '{fmt}'" for fmt in formats
        )
        script = f"""\
# Fish completion for {prog}
# Add to ~/.config/fish/completions/{prog}.fish

{subcmd_completions}

# graph --format
{format_completions}

# completion shell
complete -c {prog} -n '__fish_seen_subcommand_from completion' -a 'bash zsh fish'

# publish flags
complete -c {prog} -n '__fish_seen_subcommand_from publish' -l dry-run -d 'Preview mode'
complete -c {prog} -n '__fish_seen_subcommand_from publish' -l force -s y -d 'Skip confirmation'
complete -c {prog} -n '__fish_seen_subcommand_from publish' -l no-tag -d 'Skip tagging'
complete -c {prog} -n '__fish_seen_subcommand_from publish' -l no-push -d 'Skip pushing'
complete -c {prog} -n '__fish_seen_subcommand_from publish' -l no-release -d 'Skip releases'
complete -c {prog} -n '__fish_seen_subcommand_from publish' -l version-only -d 'Version only'
"""
    else:
        print(f'Unknown shell: {shell}', file=sys.stderr)  # noqa: T201 - CLI output
        return 1

    print(script)  # noqa: T201 - CLI output
    return 0


async def _cmd_prepare(args: argparse.Namespace) -> int:
    """Handle the ``prepare`` subcommand."""
    workspace_root = _find_workspace_root()
    config = load_config(workspace_root)
    vcs, pm, forge, registry = _create_backends(workspace_root, config)

    result = await prepare_release(
        vcs=vcs,
        pm=pm,
        forge=forge,
        registry=registry,
        workspace_root=workspace_root,
        config=config,
        dry_run=args.dry_run,
        force=args.force,
    )

    if not result.ok:
        for step, error in result.errors.items():
            logger.error('prepare_error', step=step, error=error)
        return 1

    if not result.bumped:
        logger.info('prepare_no_changes', message='No packages have changes to release.')
        return 0

    logger.info(
        'prepare_success',
        bumped=len(result.bumped),
        pr_url=result.pr_url,
    )
    if result.pr_url:
        print(f'Release PR: {result.pr_url}')  # noqa: T201 - CLI output
    return 0


async def _cmd_release(args: argparse.Namespace) -> int:
    """Handle the ``release`` subcommand."""
    workspace_root = _find_workspace_root()
    config = load_config(workspace_root)
    vcs, _pm, forge, _registry = _create_backends(workspace_root, config)

    manifest_path = Path(args.manifest) if args.manifest else None

    result = await tag_release(
        vcs=vcs,
        forge=forge,
        config=config,
        manifest_path=manifest_path,
        dry_run=args.dry_run,
    )

    if not result.ok:
        for step, error in result.errors.items():
            logger.error('release_error', step=step, error=error)
        return 1

    logger.info(
        'release_success',
        tags=len(result.tags_created),
        release_url=result.release_url,
    )
    return 0


# ── Argument parser ──────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured :class:`argparse.ArgumentParser`.
    """
    RichHelpFormatter.styles['argparse.groups'] = 'bold yellow'
    parser = argparse.ArgumentParser(
        prog='releasekit',
        description='Release orchestration for polyglot monorepos (uv, pnpm, Go).',
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}',
    )

    subparsers = parser.add_subparsers(dest='command')

    # ── publish ──
    publish_parser = subparsers.add_parser(
        'publish',
        help='Publish all changed packages to PyPI.',
    )
    publish_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview mode: log commands without executing.',
    )
    publish_parser.add_argument(
        '--force',
        '-y',
        action='store_true',
        help='Skip confirmation prompt.',
    )
    publish_parser.add_argument(
        '--force-unchanged',
        action='store_true',
        help='Include packages with no changes.',
    )
    publish_parser.add_argument(
        '--concurrency',
        type=int,
        default=5,
        help='Max packages publishing simultaneously per level (default: 5).',
    )
    publish_parser.add_argument(
        '--check-url',
        help='URL to check for existing files (uv publish --check-url).',
    )
    publish_parser.add_argument(
        '--index-url',
        help='Custom index URL (e.g., Test PyPI).',
    )
    publish_parser.add_argument(
        '--max-retries',
        type=int,
        default=0,
        help='Retry failed publishes up to N times with exponential backoff (default: 0).',
    )
    publish_parser.add_argument(
        '--retry-base-delay',
        type=float,
        default=1.0,
        help='Base delay in seconds for retry backoff (default: 1.0).',
    )
    publish_parser.add_argument(
        '--task-timeout',
        type=float,
        default=600.0,
        help='Timeout in seconds per publish attempt (default: 600).',
    )
    publish_parser.add_argument(
        '--no-tag',
        action='store_true',
        help='Skip git tag creation.',
    )
    publish_parser.add_argument(
        '--no-push',
        action='store_true',
        help='Skip pushing tags and commits to remote.',
    )
    publish_parser.add_argument(
        '--no-release',
        action='store_true',
        help='Skip creating platform releases.',
    )
    publish_parser.add_argument(
        '--version-only',
        action='store_true',
        help='Compute and apply version bumps, then stop (no build/publish).',
    )
    publish_parser.add_argument(
        '--group',
        '-g',
        metavar='NAME',
        help='Only publish packages in this release group.',
    )
    publish_parser.add_argument(
        '--forge-backend',
        choices=['cli', 'api'],
        default='cli',
        help="Forge transport: 'cli' (forge CLI tool) or 'api' (REST API).",
    )

    # ── plan ──
    plan_parser = subparsers.add_parser(
        'plan',
        help='Preview the execution plan without publishing.',
    )
    plan_parser.add_argument(
        '--format',
        choices=['table', 'json', 'csv', 'ascii', 'full'],
        default='table',
        help='Output format (default: table).',
    )
    plan_parser.add_argument(
        '--force-unchanged',
        action='store_true',
        help='Include packages with no changes.',
    )
    plan_parser.add_argument(
        '--group',
        '-g',
        metavar='NAME',
        help='Only show packages in this release group.',
    )

    # ── discover ──
    discover_parser = subparsers.add_parser(
        'discover',
        help='List all workspace packages (across all detected ecosystems).',
    )
    discover_parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        help='Output format (default: table).',
    )
    discover_parser.add_argument(
        '--group',
        '-g',
        metavar='NAME',
        help='Only show packages in this release group.',
    )
    discover_parser.add_argument(
        '--ecosystem',
        '-e',
        choices=[e.value for e in list(Ecosystem)],
        metavar='ECO',
        help='Only discover packages in this ecosystem (python, js, go).',
    )

    # ── graph ──
    graph_parser = subparsers.add_parser(
        'graph',
        help='Show the dependency graph.',
    )
    graph_parser.add_argument(
        '--format',
        choices=sorted(FORMATTERS),
        default='levels',
        help='Output format (default: levels).',
    )
    graph_parser.add_argument(
        '--deps',
        metavar='PKG',
        help='Show only forward dependencies of PKG.',
    )
    graph_parser.add_argument(
        '--rdeps',
        metavar='PKG',
        help='Show only reverse dependencies of PKG.',
    )

    # ── check ──
    check_parser = subparsers.add_parser(
        'check',
        help='Run workspace health checks (cycles, deps, files, metadata).',
    )
    check_parser.add_argument(
        '--fix',
        action='store_true',
        default=False,
        help='Auto-fix issues that can be fixed (e.g. Private :: Do Not Upload classifiers).',
    )

    # ── version ──
    version_parser = subparsers.add_parser(
        'version',
        help='Show computed version bumps.',
    )
    version_parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        help='Output format (default: table).',
    )
    version_parser.add_argument(
        '--force-unchanged',
        action='store_true',
        help='Include packages with no changes.',
    )
    version_parser.add_argument(
        '--group',
        '-g',
        metavar='NAME',
        help='Only show versions for packages in this release group.',
    )

    # ── changelog ──
    changelog_parser = subparsers.add_parser(
        'changelog',
        help='Generate per-package CHANGELOG.md files from Conventional Commits.',
    )
    changelog_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview mode: show what would be written without modifying files.',
    )
    changelog_parser.add_argument(
        '--group',
        '-g',
        metavar='NAME',
        help='Only generate changelogs for packages in this release group.',
    )

    # ── explain ──
    explain_parser = subparsers.add_parser(
        'explain',
        help='Explain an error code.',
    )
    explain_parser.add_argument(
        'code',
        help='Error code to explain (e.g., RK-PREFLIGHT-DIRTY-WORKTREE).',
    )

    # ── init ──
    init_parser = subparsers.add_parser(
        'init',
        help='Scaffold releasekit.toml config for the workspace.',
    )
    init_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview generated config without writing files.',
    )
    init_parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing releasekit.toml.',
    )
    init_parser.add_argument(
        '--ecosystem',
        '-e',
        choices=[e.value for e in list(Ecosystem)],
        metavar='ECO',
        help='Only init for this ecosystem (python, js, go).',
    )

    # ── rollback ──
    rollback_parser = subparsers.add_parser(
        'rollback',
        help='Delete a tag and its platform release.',
    )
    rollback_parser.add_argument(
        'tag',
        help='Git tag to delete (e.g., genkit-v0.5.0).',
    )
    rollback_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview mode: log commands without executing.',
    )

    # ── prepare ──
    prepare_parser = subparsers.add_parser(
        'prepare',
        help='Prepare a release: bump versions, generate changelogs, open Release PR.',
    )
    prepare_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview mode: log commands without executing.',
    )
    prepare_parser.add_argument(
        '--force',
        action='store_true',
        help='Skip preflight checks.',
    )
    prepare_parser.add_argument(
        '--group',
        '-g',
        metavar='NAME',
        help='Only prepare packages in this release group.',
    )
    prepare_parser.add_argument(
        '--forge-backend',
        choices=['cli', 'api'],
        default='cli',
        help="Forge transport: 'cli' (forge CLI tool) or 'api' (REST API).",
    )

    # ── release ──
    release_parser = subparsers.add_parser(
        'release',
        help='Tag a merged Release PR and create platform Release.',
    )
    release_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview mode: log commands without executing.',
    )
    release_parser.add_argument(
        '--manifest',
        default='',
        help='Path to a manifest JSON file (skips PR lookup).',
    )

    # ── completion ──
    completion_parser = subparsers.add_parser(
        'completion',
        help='Generate shell completion script.',
    )
    completion_parser.add_argument(
        'shell',
        choices=['bash', 'zsh', 'fish'],
        help='Shell to generate completions for.',
    )

    return parser


def main() -> int:
    """CLI entry point.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    parser = build_parser()
    args = parser.parse_args()

    try:
        command = args.command
        if command == 'publish':
            return asyncio.run(_cmd_publish(args))
        if command == 'plan':
            return asyncio.run(_cmd_plan(args))
        if command == 'discover':
            return _cmd_discover(args)
        if command == 'graph':
            return _cmd_graph(args)
        if command == 'check':
            return _cmd_check(args)
        if command == 'version':
            return asyncio.run(_cmd_version(args))
        if command == 'changelog':
            return asyncio.run(_cmd_changelog(args))
        if command == 'explain':
            return _cmd_explain(args)
        if command == 'init':
            return _cmd_init(args)
        if command == 'rollback':
            return asyncio.run(_cmd_rollback(args))
        if command == 'prepare':
            return asyncio.run(_cmd_prepare(args))
        if command == 'release':
            return asyncio.run(_cmd_release(args))
        if command == 'completion':
            return _cmd_completion(args)

        parser.print_help()  # noqa: T201 - CLI output
        print(  # noqa: T201 - CLI output
            f'\n{parser.prog}: error: please provide a command',
            file=sys.stderr,
        )
        return 2

    except ReleaseKitError as exc:
        render_error(exc)
        return 1
    except KeyboardInterrupt:
        logger.info('interrupted')
        return 130


def _main() -> None:
    """Wrapper for pyproject.toml [project.scripts] entry point."""
    sys.exit(main())


__all__ = [
    'build_parser',
    'main',
]
