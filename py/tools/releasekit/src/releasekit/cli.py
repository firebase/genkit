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
import json
import sys
from pathlib import Path

from releasekit import __version__
from releasekit.backends.forge import GitHubBackend
from releasekit.backends.pm import UvBackend
from releasekit.backends.registry import PyPIBackend
from releasekit.backends.vcs import GitBackend
from releasekit.checks import run_checks
from releasekit.config import ReleaseConfig, load_config
from releasekit.errors import E, ReleaseKitError, explain
from releasekit.graph import build_graph, topo_sort
from releasekit.lock import release_lock
from releasekit.logging import get_logger
from releasekit.plan import build_plan
from releasekit.preflight import run_preflight
from releasekit.publisher import PublishConfig, publish_workspace
from releasekit.ui import create_progress_ui
from releasekit.versioning import compute_bumps
from releasekit.versions import ReleaseManifest
from releasekit.workspace import discover_packages

logger = get_logger(__name__)


def _find_workspace_root() -> Path:
    """Find the workspace root by walking up from CWD.

    Looks for a ``pyproject.toml`` containing ``[tool.uv.workspace]``.

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


def _create_backends(
    workspace_root: Path,
    config: ReleaseConfig,
) -> tuple[GitBackend, UvBackend, GitHubBackend, PyPIBackend]:
    """Create real backend instances for production use.

    Args:
        workspace_root: Workspace root directory.
        config: Release configuration.

    Returns:
        Tuple of (VCS, PackageManager, Forge, Registry) backends.
    """
    vcs = GitBackend(workspace_root)
    pm = UvBackend(workspace_root)
    forge = GitHubBackend(
        repo='firebase/genkit',  # NOTE: Could be auto-detected from git remote.
        cwd=workspace_root,
    )
    registry = PyPIBackend(pool_size=config.http_pool_size)
    return vcs, pm, forge, registry


# ── Subcommand handlers ──────────────────────────────────────────────


async def _cmd_publish(args: argparse.Namespace) -> int:
    """Handle the ``publish`` subcommand."""
    workspace_root = _find_workspace_root()
    config = load_config(workspace_root / 'pyproject.toml')
    vcs, pm, forge, registry = _create_backends(workspace_root, config)

    # Discover and analyze.
    packages = discover_packages(workspace_root, exclude_patterns=config.exclude)
    graph = build_graph(packages)
    levels = topo_sort(graph)
    versions = compute_bumps(
        packages,
        vcs,
        tag_format=config.tag_format,
        prerelease='',
        force_unchanged=args.force_unchanged,
    )

    # Check for any actual bumps.
    bumped = [v for v in versions if not v.skipped]
    if not bumped:
        logger.info('nothing_to_publish', message='No packages have changes to publish.')
        return 0

    # Build execution plan for preview.
    plan = build_plan(versions, levels, exclude_names=config.exclude, git_sha=vcs.current_sha())

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
        git_sha=vcs.current_sha(),
        packages=versions,
    )
    manifest_path = workspace_root / 'release-manifest.json'
    manifest.save(manifest_path)
    logger.info('manifest_saved', path=str(manifest_path))

    return 0


async def _cmd_plan(args: argparse.Namespace) -> int:
    """Handle the ``plan`` subcommand."""
    workspace_root = _find_workspace_root()
    config = load_config(workspace_root / 'pyproject.toml')
    vcs, pm, forge, registry = _create_backends(workspace_root, config)

    packages = discover_packages(workspace_root, exclude_patterns=config.exclude)
    graph = build_graph(packages)
    levels = topo_sort(graph)
    versions = compute_bumps(
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
        git_sha=vcs.current_sha(),
    )

    fmt = getattr(args, 'format', 'table')
    if fmt == 'json':
        print(plan.format_json())  # noqa: T201 - CLI output
    elif fmt == 'csv':
        print(plan.format_csv())  # noqa: T201 - CLI output
    else:
        print(plan.format_table())  # noqa: T201 - CLI output

    return 0


def _cmd_discover(args: argparse.Namespace) -> int:
    """Handle the ``discover`` subcommand."""
    workspace_root = _find_workspace_root()
    config = load_config(workspace_root / 'pyproject.toml')
    packages = discover_packages(workspace_root, exclude_patterns=config.exclude)

    fmt = getattr(args, 'format', 'table')
    if fmt == 'json':
        data = [
            {
                'name': p.name,
                'version': p.version,
                'path': str(p.path),
                'internal_deps': p.internal_deps,
                'publishable': p.is_publishable,
            }
            for p in packages
        ]
        print(json.dumps(data, indent=2))  # noqa: T201 - CLI output
    else:
        for pkg in packages:
            deps = ', '.join(pkg.internal_deps) if pkg.internal_deps else '(none)'
            pub = '' if pkg.is_publishable else ' [private]'
            print(f'  {pkg.name} {pkg.version} ({pkg.path}){pub}')  # noqa: T201 - CLI output
            print(f'    deps: {deps}')  # noqa: T201 - CLI output

    return 0


def _cmd_graph(args: argparse.Namespace) -> int:
    """Handle the ``graph`` subcommand."""
    workspace_root = _find_workspace_root()
    config = load_config(workspace_root / 'pyproject.toml')
    packages = discover_packages(workspace_root, exclude_patterns=config.exclude)
    graph = build_graph(packages)

    fmt = getattr(args, 'format', 'table')
    if fmt == 'json':
        data = {
            'packages': graph.names,
            'edges': graph.edges,
            'reverse_edges': graph.reverse_edges,
        }
        print(json.dumps(data, indent=2))  # noqa: T201 - CLI output
    else:
        levels = topo_sort(graph)
        for level_idx, level in enumerate(levels):
            names = ', '.join(p.name for p in level)
            print(f'  Level {level_idx}: {names}')  # noqa: T201 - CLI output

    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    """Handle the ``check`` subcommand."""
    workspace_root = _find_workspace_root()
    config = load_config(workspace_root / 'pyproject.toml')
    packages = discover_packages(workspace_root, exclude_patterns=config.exclude)
    graph = build_graph(packages)

    result = run_checks(packages, graph)

    # Print detailed results.
    if result.passed:
        for name in result.passed:
            print(f'  ✅ {name}')  # noqa: T201 - CLI output
    if result.warnings:
        for name in result.warnings:
            msg = result.warning_messages.get(name, '')
            print(f'  ⚠️  {name}: {msg}')  # noqa: T201 - CLI output
    if result.failed:
        for name in result.failed:
            msg = result.errors.get(name, '')
            print(f'  ❌ {name}: {msg}')  # noqa: T201 - CLI output

    print()  # noqa: T201 - CLI output
    print(f'  {result.summary()}')  # noqa: T201 - CLI output

    return 0 if result.ok else 1


def _cmd_version(args: argparse.Namespace) -> int:
    """Handle the ``version`` subcommand."""
    workspace_root = _find_workspace_root()
    config = load_config(workspace_root / 'pyproject.toml')
    vcs, pm, forge, registry = _create_backends(workspace_root, config)

    packages = discover_packages(workspace_root, exclude_patterns=config.exclude)
    versions = compute_bumps(
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


def _cmd_explain(args: argparse.Namespace) -> int:
    """Handle the ``explain`` subcommand."""
    result = explain(args.code)
    if result is None:
        print(f'Unknown error code: {args.code}')  # noqa: T201 - CLI output
        return 1
    print(result)  # noqa: T201 - CLI output
    return 0


# ── Argument parser ──────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured :class:`argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog='releasekit',
        description='Release orchestration for uv workspaces.',
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}',
    )

    subparsers = parser.add_subparsers(dest='command', required=True)

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

    # ── plan ──
    plan_parser = subparsers.add_parser(
        'plan',
        help='Preview the execution plan without publishing.',
    )
    plan_parser.add_argument(
        '--format',
        choices=['table', 'json', 'csv'],
        default='table',
        help='Output format (default: table).',
    )
    plan_parser.add_argument(
        '--force-unchanged',
        action='store_true',
        help='Include packages with no changes.',
    )

    # ── discover ──
    discover_parser = subparsers.add_parser(
        'discover',
        help='List all workspace packages.',
    )
    discover_parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        help='Output format (default: table).',
    )

    # ── graph ──
    graph_parser = subparsers.add_parser(
        'graph',
        help='Show the dependency graph.',
    )
    graph_parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        help='Output format (default: table).',
    )

    # ── check ──
    subparsers.add_parser(
        'check',
        help='Run workspace health checks (cycles, deps, files, metadata).',
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

    # ── explain ──
    explain_parser = subparsers.add_parser(
        'explain',
        help='Explain an error code.',
    )
    explain_parser.add_argument(
        'code',
        help='Error code to explain (e.g., RK-PREFLIGHT-DIRTY-WORKTREE).',
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
            return _cmd_version(args)
        if command == 'explain':
            return _cmd_explain(args)

        parser.print_help()  # noqa: T201 - CLI output
        return 1

    except ReleaseKitError as exc:
        logger.error('releasekit_error', code=exc.code.value, message=str(exc))
        if exc.hint:
            logger.info('hint', hint=exc.hint)
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
