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

    releasekit publish    Publish all changed packages to their registry
    releasekit plan       Preview the execution plan (no publish)
    releasekit changelog  Generate per-package CHANGELOG.md files
    releasekit discover   List all workspace packages
    releasekit graph      Show the dependency graph
    releasekit version    Show computed version bumps
    releasekit explain    Explain an error code
    releasekit doctor    Diagnose release state consistency
    releasekit sign      Sign artifacts with Sigstore (keyless)
    releasekit verify    Verify Sigstore bundles

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
import dataclasses
import fnmatch
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console
from rich_argparse import RichHelpFormatter

from releasekit import __version__
from releasekit.announce import send_announcements
from releasekit.backends._run import CommandResult
from releasekit.backends.forge import Forge, GitHubAPIBackend, GitHubCLIBackend
from releasekit.backends.forge.bitbucket import BitbucketAPIBackend
from releasekit.backends.forge.gitlab import GitLabCLIBackend
from releasekit.backends.pm import (
    BazelBackend,
    CargoBackend,
    DartBackend,
    GoBackend,
    MaturinBackend,
    MavenBackend,
    PackageManager,
    PnpmBackend,
    UvBackend,
)
from releasekit.backends.registry import (
    CratesIoRegistry,
    GoProxyCheck,
    MavenCentralRegistry,
    NpmRegistry,
    PubDevRegistry,
    PyPIBackend,
    Registry,
)
from releasekit.backends.validation.runner import (
    detect_artifacts,
    validate_artifacts,
)
from releasekit.backends.vcs import GitCLIBackend
from releasekit.changelog import Changelog, generate_changelog, render_changelog, write_changelog
from releasekit.checks import (
    PythonCheckBackend,
    fix_missing_license,
    fix_missing_readme,
    fix_stale_artifacts,
    run_checks,
)
from releasekit.commit_parsing._types import BumpType
from releasekit.compliance import (
    ComplianceControl,
    ComplianceStatus,
    compliance_to_json,
    evaluate_compliance,
    print_compliance_table,
)
from releasekit.config import (
    ReleaseConfig,
    WorkspaceConfig,
    build_package_configs,
    build_skip_map,
    load_config,
    resolve_group_refs,
)
from releasekit.detection import (
    DetectedEcosystem,
    Ecosystem,
    detect_ecosystems,
    find_monorepo_root,
)
from releasekit.doctor import Severity, run_doctor
from releasekit.errors import E, ReleaseKitError, explain, render_error
from releasekit.formatters import FORMATTERS, format_graph
from releasekit.graph import build_graph, topo_sort
from releasekit.groups import filter_by_group
from releasekit.init import (
    print_scaffold_preview,
    print_tag_scan_report,
    scaffold_config,
    scaffold_multi_config,
    scan_and_bootstrap,
)
from releasekit.lock import release_lock
from releasekit.logging import get_logger
from releasekit.migrate import MIGRATION_SOURCES, migrate_from_source
from releasekit.osv import OSVSeverity, check_osv_vulnerabilities
from releasekit.plan import build_plan
from releasekit.preflight import PreflightResult, SourceContext, read_source_snippet, run_preflight
from releasekit.prepare import prepare_release
from releasekit.prerelease import is_prerelease as _is_pre, promote_to_stable
from releasekit.provenance import is_ci, should_sign_provenance, verify_provenance
from releasekit.publisher import PublishConfig, publish_workspace
from releasekit.release import tag_release
from releasekit.scorecard import run_scorecard_checks
from releasekit.security_insights import (
    SecurityInsightsConfig,
    generate_security_insights,
)
from releasekit.should_release import ReleaseDecision, should_release
from releasekit.signing import sign_artifacts, verify_artifact
from releasekit.snapshot import (
    SnapshotConfig,
    apply_snapshot_versions,
    compute_snapshot_version,
    resolve_snapshot_identifier,
)
from releasekit.state import STATE_FILENAME, RunState
from releasekit.tags import format_tag, parse_tag
from releasekit.ui import create_progress_ui
from releasekit.utils.date import utc_today
from releasekit.versioning import compute_bumps
from releasekit.versions import ReleaseManifest
from releasekit.workspace import Package, discover_packages

logger = get_logger(__name__)


def _auto_slsa_provenance() -> bool:
    """Auto-enable SLSA provenance when running in CI.

    Returns ``True`` when the ``CI`` environment variable is set,
    enabling SLSA Build L1 (provenance exists) by default for all
    CI pipelines.
    """
    return is_ci()


def _auto_sign_provenance() -> bool:
    """Auto-enable signed provenance when CI has OIDC credentials.

    Returns ``True`` when running in CI **and** an OIDC credential
    is available, enabling SLSA Build L2 (signed provenance) by
    default for properly configured CI pipelines.
    """
    return should_sign_provenance()


def _find_workspace_root() -> Path:
    """Find the workspace root by walking up from CWD.

    Walks up from CWD looking for ``releasekit.toml``.  Falls back to
    ``pyproject.toml`` with ``[tool.uv.workspace]`` for legacy
    uv-only setups.

    Returns:
        Absolute path to the workspace root.

    Raises:
        ReleaseKitError: If no workspace root is found.
    """
    cwd = Path.cwd().resolve()
    # Primary: look for releasekit.toml (polyglot config).
    for parent in [cwd, *cwd.parents]:
        if (parent / 'releasekit.toml').is_file():
            return parent
    # Fallback: legacy uv-only workspace.
    for parent in [cwd, *cwd.parents]:
        pyproject = parent / 'pyproject.toml'
        if pyproject.exists():
            text = pyproject.read_text(encoding='utf-8')
            if '[tool.uv.workspace]' in text:
                return parent
    raise ReleaseKitError(
        E.WORKSPACE_NOT_FOUND,
        'Could not find releasekit.toml or a pyproject.toml with [tool.uv.workspace].',
        hint='Run "releasekit init" or place releasekit.toml at the repo root.',
    )


def _effective_workspace_root(config_root: Path, ws_config: WorkspaceConfig) -> Path:
    """Resolve the effective workspace root from the config root and workspace config.

    The ``root`` field in ``[workspace.<label>]`` is relative to the
    directory containing ``releasekit.toml``.  For example, if the config
    lives at ``/repo/releasekit.toml`` and ``root = "py"``, the effective
    workspace root is ``/repo/py``.

    Returns:
        Absolute path to the ecosystem-specific workspace root.
    """
    return (config_root / ws_config.root).resolve()


def _get_ecosystem_filter(args: argparse.Namespace) -> Ecosystem | None:
    """Extract ``--ecosystem`` filter from parsed args.

    Returns:
        The ecosystem enum value, or ``None`` if not specified.
    """
    eco_str = getattr(args, 'ecosystem', None)
    if eco_str is None:
        return None
    for member in Ecosystem:
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

    _NOOP = CommandResult(command=[], return_code=0, stdout='', stderr='')

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
    config_root: Path,
    config: ReleaseConfig,
    *,
    ws_root: Path | None = None,
    ws_config: WorkspaceConfig | None = None,
    forge_backend: str = 'cli',
) -> tuple[GitCLIBackend, PackageManager, Forge, Registry]:
    """Create real backend instances for production use.

    The forge backend is determined by ``config.forge`` (github, gitlab,
    bitbucket, none) and the ``forge_backend`` transport hint (cli vs api).
    Repository coordinates come from ``config.repo_owner`` and
    ``config.repo_name``.

    The package manager and registry backends are selected based on
    ``ws_config.tool``:

    - ``"uv"`` → :class:`UvBackend` + :class:`PyPIBackend`
    - ``"pnpm"`` → :class:`PnpmBackend` + :class:`NpmRegistry`
    - ``"go"`` → :class:`GoBackend` + :class:`GoProxyCheck`
    - ``"pub"`` → :class:`DartBackend` + :class:`PubDevRegistry`
    - ``"gradle"`` / ``"maven"`` → :class:`MavenBackend` + :class:`MavenCentralRegistry`
    - ``"bazel"`` → :class:`BazelBackend` + :class:`MavenCentralRegistry`
    - ``"cargo"`` → :class:`CargoBackend` + :class:`CratesIoRegistry`
    - ``"maturin"`` → :class:`MaturinBackend` + :class:`PyPIBackend`

    When ``ws_config.registry_url`` is set, it overrides the default
    base URL for the registry backend (e.g. for Test PyPI, a local
    Verdaccio, or a staging crates.io).

    For npm workspaces, ``registry_url`` flows to both the
    ``NpmRegistry`` backend (polling/verification) **and** the publish
    path (``pnpm publish --registry``).  This works with full mirrors
    like Verdaccio and with Google's `Wombat Dressing Room
    <https://github.com/GoogleCloudPlatform/wombat-dressing-room>`_
    (which proxies both reads and writes).

    Args:
        config_root: Directory containing ``releasekit.toml`` (repo root).
        config: Release configuration.
        ws_root: Ecosystem-specific workspace root (e.g. ``repo/py``).
            Defaults to *config_root* if not provided.
        ws_config: Per-workspace config (used to select PM/registry).
        forge_backend: Transport hint: ``"cli"`` for CLI-based backends,
            ``"api"`` for REST API-based backends (where available).

    Returns:
        Tuple of (VCS, PackageManager, Forge, Registry) backends.
    """
    effective_root = ws_root or config_root
    vcs = GitCLIBackend(config_root)

    tool = ws_config.tool if ws_config else 'uv'
    registry_url = ws_config.registry_url if ws_config else ''
    pool = config.http_pool_size

    pm: PackageManager
    registry: Registry
    registry_kw: dict[str, object] = {'pool_size': pool}
    if registry_url:
        registry_kw['base_url'] = registry_url

    if tool == 'pnpm':
        pm = PnpmBackend(effective_root)
        registry = NpmRegistry(**registry_kw)  # type: ignore[arg-type]
    elif tool == 'go':
        pm = GoBackend(effective_root)
        registry = GoProxyCheck(**registry_kw)  # type: ignore[arg-type]
    elif tool == 'pub':
        pm = DartBackend(effective_root)
        registry = PubDevRegistry(**registry_kw)  # type: ignore[arg-type]
    elif tool in ('gradle', 'maven'):
        pm = MavenBackend(effective_root)
        registry = MavenCentralRegistry(**registry_kw)  # type: ignore[arg-type]
    elif tool == 'bazel':
        pm = BazelBackend(effective_root)
        registry = MavenCentralRegistry(**registry_kw)  # type: ignore[arg-type]
    elif tool == 'cargo':
        pm = CargoBackend(effective_root)
        registry = CratesIoRegistry(**registry_kw)  # type: ignore[arg-type]
    elif tool == 'maturin':
        pm = MaturinBackend(effective_root)
        registry = PyPIBackend(**registry_kw)  # type: ignore[arg-type]
    else:
        pm = UvBackend(effective_root)
        registry = PyPIBackend(**registry_kw)  # type: ignore[arg-type]

    owner = config.repo_owner
    repo = config.repo_name
    repo_slug = f'{owner}/{repo}' if owner and repo else ''

    forge: Forge
    forge_type = config.forge

    if forge_type == 'none':
        forge = _NullForge()
    elif forge_type == 'gitlab':
        forge = GitLabCLIBackend(project=repo_slug, cwd=config_root)
    elif forge_type == 'bitbucket':
        forge = BitbucketAPIBackend(workspace=owner, repo_slug=repo)
    elif forge_backend == 'api':
        forge = GitHubAPIBackend(owner=owner, repo=repo)
    else:
        forge = GitHubCLIBackend(repo=repo_slug, cwd=config_root)

    return vcs, pm, forge, registry


def _resolve_ws_config(
    config: ReleaseConfig,
    label: str | None = None,
) -> WorkspaceConfig:
    """Pick the workspace config for the current CLI context.

    When ``label`` is given (via ``--workspace``), returns that specific
    workspace config.  Otherwise returns the first (and typically only)
    workspace, or a default ``WorkspaceConfig()`` if none are configured.

    Raises:
        ReleaseKitError: If the requested workspace label does not exist.
    """
    if label and label in config.workspaces:
        return config.workspaces[label]
    if label:
        available = ', '.join(config.workspaces) or '(none)'
        raise ReleaseKitError(
            E.WORKSPACE_NOT_FOUND,
            f'Workspace {label!r} not found. Available: {available}',
            hint='Check the [workspace.<label>] sections in releasekit.toml.',
        )
    if config.workspaces:
        return next(iter(config.workspaces.values()))
    return WorkspaceConfig()


def _maybe_filter_group(
    packages: list[Package],
    ws_config: WorkspaceConfig,
    group: str | None,
) -> list[Package]:
    """Optionally filter packages by release group.

    If ``group`` is None, returns all packages unchanged.
    Otherwise, filters to only packages matching the named group.
    """
    if group is None:
        return packages

    return filter_by_group(packages, groups=ws_config.groups, group=group)


def _match_exclude_patterns(name: str, patterns: list[str]) -> bool:
    """Return True if *name* matches any of the glob *patterns*."""
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)


async def _cmd_publish(args: argparse.Namespace) -> int:
    """Handle the ``publish`` subcommand."""
    config_root = _find_workspace_root()
    config = load_config(config_root)
    ws_config = _resolve_ws_config(config, getattr(args, 'workspace', None))

    # CLI --registry-url overrides the config-file registry_url.
    cli_registry_url = getattr(args, 'registry_url', None)
    if cli_registry_url:
        ws_config = dataclasses.replace(ws_config, registry_url=cli_registry_url)

    ws_root = _effective_workspace_root(config_root, ws_config)
    forge_backend = getattr(args, 'forge_backend', 'cli')
    vcs, pm, forge, registry = _create_backends(
        config_root,
        config,
        ws_root=ws_root,
        ws_config=ws_config,
        forge_backend=forge_backend,
    )

    # Discover and analyze — all packages participate in checks + version bumps.
    all_packages = discover_packages(
        ws_root,
        exclude_patterns=ws_config.exclude,
        ecosystem=ws_config.ecosystem or 'python',
    )
    group = getattr(args, 'group', None)
    packages = _maybe_filter_group(all_packages, ws_config, group)
    graph = build_graph(packages)
    levels = topo_sort(graph)
    propagate_graph = graph if (ws_config.propagate_bumps and not ws_config.synchronize) else None
    pkg_configs = build_package_configs(ws_config, [p.name for p in packages])
    versions = await compute_bumps(
        packages,
        vcs,
        tag_format=ws_config.tag_format,
        prerelease='',
        force_unchanged=args.force_unchanged,
        ignore_unknown_tags=getattr(args, 'ignore_unknown_tags', False),
        graph=propagate_graph,
        synchronize=ws_config.synchronize,
        major_on_zero=ws_config.major_on_zero,
        max_commits=ws_config.max_commits,
        bootstrap_sha=ws_config.bootstrap_sha,
        versioning_scheme=ws_config.versioning_scheme,
        package_configs=pkg_configs,
    )

    # Filter out exclude_bump packages — they are discovered + checked but not bumped.
    resolved_exclude_bump = resolve_group_refs(ws_config.exclude_bump, ws_config.groups)
    if resolved_exclude_bump:
        bump_excluded = {p.name for p in packages if _match_exclude_patterns(p.name, resolved_exclude_bump)}
        if bump_excluded:
            logger.info('exclude_bump', count=len(bump_excluded), names=sorted(bump_excluded))
        packages = [p for p in packages if p.name not in bump_excluded]
        versions = [v for v in versions if v.name not in bump_excluded]
        graph = build_graph(packages)
        levels = topo_sort(graph)

    # Filter out exclude_publish packages — they get version bumps but not published.
    resolved_exclude_publish = resolve_group_refs(ws_config.exclude_publish, ws_config.groups)
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
    plan = build_plan(versions, levels, exclude_names=ws_config.exclude, git_sha=await vcs.current_sha())

    if not args.force and not args.dry_run:
        print(plan.format_table())  # noqa: T201 - CLI output
        print()  # noqa: T201 - CLI output
        if sys.stdin.isatty():
            answer = await asyncio.to_thread(input, f'Publish {len(bumped)} package(s)? [y/N] ')
            if answer.lower() not in {'y', 'yes'}:
                logger.info('publish_cancelled')
                return 1

    # Preflight.
    with release_lock(ws_root):
        # Merge skip_checks from config and CLI --skip-check flags.
        cli_skip = getattr(args, 'skip_check', []) or []
        merged_skip = list({*ws_config.skip_checks, *cli_skip})

        preflight = await run_preflight(
            vcs=vcs,
            pm=pm,
            forge=forge,
            registry=registry,
            packages=packages,
            graph=graph,
            versions=versions,
            workspace_root=ws_root,
            dry_run=args.dry_run,
            skip_version_check=args.force,
            ecosystem=ws_config.ecosystem,
            osv_severity_threshold=ws_config.osv_severity_threshold,
            skip_checks=merged_skip or None,
        )
        if not preflight.ok:
            for name, error in preflight.errors.items():
                logger.error('preflight_blocked', check=name, error=error)
            return 1

        # Publish.
        # Compute SLSA provenance and signing flags with safe defaults.
        no_slsa = getattr(args, 'no_slsa_provenance', False)
        want_slsa = not no_slsa and (
            getattr(args, 'slsa_provenance', False)
            or getattr(args, 'sign_provenance', False)
            or ws_config.slsa_provenance
            or ws_config.sign_provenance
            or _auto_slsa_provenance()
        )
        want_sign = not no_slsa and (
            getattr(args, 'sign_provenance', False) or ws_config.sign_provenance or _auto_sign_provenance()
        )

        # Emit security warnings for downgraded configurations.
        if no_slsa and is_ci():
            logger.warning(
                'security_downgrade',
                message='--no-slsa-provenance used in CI: provenance generation disabled.',
                hint=(
                    'SLSA provenance is a critical supply chain security control. '
                    'Remove --no-slsa-provenance unless you have a specific reason.'
                ),
            )
        if want_slsa and not want_sign and is_ci():
            logger.warning(
                'security_downgrade',
                message='SLSA provenance will be generated but NOT signed (OIDC unavailable).',
                hint=('Unsigned provenance only achieves SLSA Build L1. Configure OIDC trusted publishing for L2+.'),
            )

        no_pep740 = getattr(args, 'no_pep740', False)
        want_pep740 = not no_pep740 and ws_config.pep740_attestations and ws_config.ecosystem == 'python'

        pub_config = PublishConfig(
            concurrency=args.concurrency,
            dry_run=args.dry_run,
            check_url=args.check_url,
            registry_url=ws_config.registry_url or None,
            smoke_test=ws_config.smoke_test,
            max_retries=args.max_retries,
            retry_base_delay=args.retry_base_delay,
            task_timeout=args.task_timeout,
            force=args.force,
            workspace_root=ws_root,
            workspace_label=ws_config.label,
            dist_tag=getattr(args, 'dist_tag', '') or ws_config.dist_tag,
            publish_branch=ws_config.publish_branch,
            provenance=ws_config.provenance,
            slsa_provenance=want_slsa,
            sign_provenance=want_sign,
            pep740_attestations=want_pep740,
            config_source=str(ws_root / 'releasekit.toml'),
            ecosystem=ws_config.ecosystem,
        )

        # Resume support: load state from previous interrupted run.
        resume = getattr(args, 'resume', False)
        fresh = getattr(args, 'fresh', False)
        state_name = f'.releasekit-state--{ws_config.label}.json' if ws_config.label else STATE_FILENAME
        state_path = ws_root / state_name
        run_state: RunState | None = None

        if resume and state_path.exists():
            run_state = RunState.load(state_path)
            logger.info(
                'resume_from_state',
                path=str(state_path),
                pending=len(run_state.pending_packages()),
                published=len(run_state.published_packages()),
            )
        elif fresh and state_path.exists():
            state_path.unlink()
            logger.info('fresh_start', deleted=str(state_path))

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
                state=run_state,
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
    manifest_name = f'release-manifest--{ws_config.label}.json' if ws_config.label else 'release-manifest.json'
    manifest_path = ws_root / manifest_name
    manifest.save(manifest_path)
    logger.info('manifest_saved', path=str(manifest_path))

    return 0


async def _cmd_plan(args: argparse.Namespace) -> int:
    """Handle the ``plan`` subcommand."""
    config_root = _find_workspace_root()
    config = load_config(config_root)
    ws_config = _resolve_ws_config(config, getattr(args, 'workspace', None))
    ws_root = _effective_workspace_root(config_root, ws_config)
    vcs, _pm, _forge, registry = _create_backends(config_root, config, ws_root=ws_root, ws_config=ws_config)

    all_packages = discover_packages(
        ws_root,
        exclude_patterns=ws_config.exclude,
        ecosystem=ws_config.ecosystem or 'python',
    )
    group = getattr(args, 'group', None)
    packages = _maybe_filter_group(all_packages, ws_config, group)
    graph = build_graph(packages)
    levels = topo_sort(graph)
    propagate_graph = graph if (ws_config.propagate_bumps and not ws_config.synchronize) else None
    pkg_configs = build_package_configs(ws_config, [p.name for p in packages])
    versions = await compute_bumps(
        packages,
        vcs,
        tag_format=ws_config.tag_format,
        force_unchanged=args.force_unchanged,
        ignore_unknown_tags=getattr(args, 'ignore_unknown_tags', False),
        graph=propagate_graph,
        synchronize=ws_config.synchronize,
        major_on_zero=ws_config.major_on_zero,
        max_commits=ws_config.max_commits,
        bootstrap_sha=ws_config.bootstrap_sha,
        versioning_scheme=ws_config.versioning_scheme,
        package_configs=pkg_configs,
    )

    # Check which versions are already published (concurrently).
    async def _check_pub(v_name: str, v_version: str) -> str | None:
        if await registry.check_published(v_name, v_version):
            return v_name
        return None

    pub_checks = [_check_pub(v.name, v.new_version) for v in versions if not v.skipped]
    pub_results = await asyncio.gather(*pub_checks)
    already_published: set[str] = {name for name in pub_results if name is not None}

    plan = build_plan(
        versions,
        levels,
        exclude_names=ws_config.exclude,
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


async def _cmd_discover(args: argparse.Namespace) -> int:
    """Handle the ``discover`` subcommand.

    Discovers packages across all detected ecosystems (or a
    specific one if ``--ecosystem`` is provided).  Falls back
    to the legacy uv-only path when a specific ecosystem's
    Workspace backend is not yet implemented.
    """
    monorepo_root, ecosystems = _resolve_ecosystems(args)
    config = load_config(monorepo_root)
    ws_config = _resolve_ws_config(config, getattr(args, 'workspace', None))
    group = getattr(args, 'group', None)
    fmt = getattr(args, 'format', 'table')

    eco_filter = _get_ecosystem_filter(args)

    if not ecosystems:
        if eco_filter is not None:
            # User explicitly requested an ecosystem that wasn't detected.
            # Do NOT fall back to Python — that would be misleading.
            logger.error(
                'No %s ecosystem detected. Nothing to discover.',
                eco_filter.value,
            )
            return 1

        # No --ecosystem flag: fall back to legacy uv-only discovery.
        config_root = _find_workspace_root()
        ws_root = _effective_workspace_root(config_root, ws_config)
        all_packages = discover_packages(
            ws_root,
            exclude_patterns=ws_config.exclude,
            ecosystem=ws_config.ecosystem or 'python',
        )
        packages = _maybe_filter_group(all_packages, ws_config, group)
        _print_packages(packages, fmt, ecosystem_label=None)
        return 0

    # Discover all ecosystems concurrently.
    valid_ecos = []
    for eco in ecosystems:
        if eco.workspace is None:
            logger.warning(
                'ecosystem_no_backend',
                ecosystem=eco.ecosystem.value,
                root=str(eco.root),
                hint=f'{eco.ecosystem.value} workspace backend not yet implemented.',
            )
        else:
            valid_ecos.append(eco)

    async def _discover_eco(eco: DetectedEcosystem) -> tuple[DetectedEcosystem, list[Package]] | None:
        try:
            if eco.workspace is None:
                return None
            eco_packages = await eco.workspace.discover(exclude_patterns=ws_config.exclude)
            legacy = [
                Package(
                    name=p.name,
                    version=p.version,
                    path=p.path,
                    manifest_path=p.manifest_path,
                    internal_deps=list(p.internal_deps),
                    external_deps=list(p.external_deps),
                    all_deps=list(p.all_deps),
                    is_publishable=p.is_publishable,
                )
                for p in eco_packages
            ]
            return (eco, legacy)
        except ReleaseKitError as exc:
            logger.warning(
                'ecosystem_discover_failed',
                ecosystem=eco.ecosystem.value,
                root=str(eco.root),
                error=str(exc),
            )
            return None

    results = await asyncio.gather(*(_discover_eco(e) for e in valid_ecos))

    all_data: list[dict[str, object]] = []
    for result in results:
        if result is None:
            continue
        eco, legacy = result
        filtered = _maybe_filter_group(legacy, ws_config, group)
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
        fmt: Output format — any key from :data:`FORMATTERS` or ``"json"``.
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
    elif fmt in FORMATTERS:
        if ecosystem_label:
            print(f'\n  ── {ecosystem_label} ({len(packages)} packages) ──')  # noqa: T201 - CLI output
        graph = build_graph(packages)
        output = format_graph(graph, packages, fmt=fmt)
        print(output, end='')  # noqa: T201 - CLI output
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
    config_root = _find_workspace_root()
    config = load_config(config_root)
    ws_config = _resolve_ws_config(config, getattr(args, 'workspace', None))
    ws_root = _effective_workspace_root(config_root, ws_config)
    packages = discover_packages(
        ws_root,
        exclude_patterns=ws_config.exclude,
        ecosystem=ws_config.ecosystem or 'python',
    )
    graph = build_graph(packages)

    fmt = getattr(args, 'format', 'levels')
    output = format_graph(graph, packages, fmt=fmt)
    print(output, end='')  # noqa: T201 - CLI output

    return 0


def _check_one_workspace(
    config_root: Path,
    config: ReleaseConfig,
    ws_config: WorkspaceConfig,
    *,
    fix: bool = False,
) -> tuple[str, PreflightResult]:
    """Run checks for a single workspace and return ``(label, result)``.

    This is the core logic extracted from ``_cmd_check`` so that
    multiple workspaces can be checked concurrently.
    """
    label = ws_config.label or ws_config.ecosystem or 'default'
    ws_root = _effective_workspace_root(config_root, ws_config)
    packages = discover_packages(
        ws_root,
        exclude_patterns=ws_config.exclude,
        ecosystem=ws_config.ecosystem or 'python',
    )
    graph = build_graph(packages)

    resolved_exclude_publish = resolve_group_refs(ws_config.exclude_publish, ws_config.groups)

    # --fix: auto-fix issues before running checks.
    if fix:
        all_changes: list[str] = []

        # Universal fixers (ecosystem-agnostic).
        all_changes.extend(fix_missing_readme(packages))
        all_changes.extend(fix_missing_license(packages))
        all_changes.extend(fix_stale_artifacts(packages))

        # Language-specific fixers (via backend).
        backend = PythonCheckBackend(
            core_package=ws_config.core_package,
            plugin_prefix=ws_config.plugin_prefix,
            namespace_dirs=ws_config.namespace_dirs,
            library_dirs=ws_config.library_dirs,
            plugin_dirs=ws_config.plugin_dirs,
        )
        all_changes.extend(
            backend.run_fixes(
                packages,
                exclude_publish=resolved_exclude_publish,
                repo_owner=config.repo_owner,
                repo_name=config.repo_name,
                namespace_dirs=ws_config.namespace_dirs,
                library_dirs=ws_config.library_dirs,
                plugin_dirs=ws_config.plugin_dirs,
            )
        )

        if all_changes:
            for change in all_changes:
                print(f'  🔧 [{label}] {change}')  # noqa: T201 - CLI output
            print()  # noqa: T201 - CLI output
            # Re-discover packages so checks see the updated state.
            packages = discover_packages(
                ws_root,
                exclude_patterns=ws_config.exclude,
                ecosystem=ws_config.ecosystem or 'python',
            )
            graph = build_graph(packages)

    skip = build_skip_map(ws_config, [p.name for p in packages])

    result = run_checks(
        packages,
        graph,
        exclude_publish=resolved_exclude_publish,
        groups=ws_config.groups,
        workspace_root=ws_root,
        core_package=ws_config.core_package,
        plugin_prefix=ws_config.plugin_prefix,
        namespace_dirs=ws_config.namespace_dirs,
        library_dirs=ws_config.library_dirs,
        plugin_dirs=ws_config.plugin_dirs,
        skip_map=skip or None,
    )
    return label, result


def _print_source_context(loc: str | SourceContext) -> None:
    """Print a single location annotation with optional source snippet.

    For plain strings, prints ``--> path``.  For :class:`SourceContext`
    with a line number, prints the surrounding source lines with the
    offending line highlighted::

        --> plugins/foo/pyproject.toml:5
         |
       3 |  version = "1.0.0"
       4 |  description = "A test"
       5 |  requires-python = ">=3.10"
         |  ^^^^^^^^^^^^^^^^ missing here
       6 |
         |
    """
    if isinstance(loc, SourceContext) and loc.line > 0:
        print(f'     --> {loc}')  # noqa: T201 - CLI output
        snippet = read_source_snippet(loc.path, loc.line)
        if snippet:
            gutter_width = len(str(snippet[-1][0]))
            print(f'     {" " * gutter_width} |')  # noqa: T201 - CLI output
            for lineno, text in snippet:
                marker = '>' if lineno == loc.line else ' '
                print(f'     {lineno:>{gutter_width}} |{marker} {text}')  # noqa: T201 - CLI output
            if loc.label:
                # Underline the key on the offending line.
                offending_text = next((t for n, t in snippet if n == loc.line), '')
                if loc.key and loc.key in offending_text:
                    col = offending_text.index(loc.key)
                    underline = ' ' * col + '^' * len(loc.key) + ' ' + loc.label
                else:
                    underline = loc.label
                print(f'     {" " * gutter_width} |  {underline}')  # noqa: T201 - CLI output
            print(f'     {" " * gutter_width} |')  # noqa: T201 - CLI output
    else:
        print(f'     --> {loc}')  # noqa: T201 - CLI output


def _print_check_result(label: str, result: PreflightResult, *, show_label: bool = False) -> None:
    """Print the check results for one workspace.

    Output follows Rust-style diagnostic formatting with source context::

        ✅ check_name
        ⚠️  warning[check_name]: message
           --> path/to/file.toml:5
            |
          3 |  version = "1.0.0"
          4 |  description = "A test"
          5 |> requires-python = ">=3.10"
            |  ^^^^^^^^^^^^^^^^ missing here
          6 |
            |
           = hint: actionable suggestion
        ❌ error[check_name]: message
           --> path/to/file.toml
           = hint: actionable suggestion
    """
    prefix = f'[{label}] ' if show_label else ''
    if result.passed:
        for name in result.passed:
            print(f'  ✅ {prefix}{name}')  # noqa: T201 - CLI output
    if result.warnings:
        for name in result.warnings:
            msg = result.warning_messages.get(name, '')
            print(f'  ⚠️  {prefix}warning[{name}]: {msg}')  # noqa: T201 - CLI output
            for loc in result.context.get(name, []):
                _print_source_context(loc)
            hint = result.hints.get(name, '')
            if hint:
                print(f'     = hint: {hint}')  # noqa: T201 - CLI output
    if result.failed:
        for name in result.failed:
            msg = result.errors.get(name, '')
            print(f'  ❌ {prefix}error[{name}]: {msg}')  # noqa: T201 - CLI output
            for loc in result.context.get(name, []):
                _print_source_context(loc)
            hint = result.hints.get(name, '')
            if hint:
                print(f'     = hint: {hint}')  # noqa: T201 - CLI output

    print()  # noqa: T201 - CLI output
    print(f'  {prefix}{result.summary()}')  # noqa: T201 - CLI output


async def _cmd_check(args: argparse.Namespace) -> int:
    """Handle the ``check`` subcommand.

    When ``--workspace`` is specified, checks that single workspace.
    Otherwise, checks **all** configured workspaces in parallel using
    :func:`asyncio.gather` with :func:`asyncio.to_thread`.
    """
    config_root = _find_workspace_root()
    config = load_config(config_root)
    fix = getattr(args, 'fix', False)
    explicit_ws = getattr(args, 'workspace', None)

    all_ok = True

    # Resolve which workspaces to check.
    if explicit_ws or len(config.workspaces) <= 1:
        ws_config = _resolve_ws_config(config, explicit_ws)
        ws_configs = [ws_config]
        label, result = await asyncio.to_thread(
            _check_one_workspace,
            config_root,
            config,
            ws_config,
            fix=fix,
        )
        _print_check_result(label, result)
        if not result.ok:
            all_ok = False
    else:
        # Multiple workspaces: run in parallel via asyncio.
        ws_configs = list(config.workspaces.values())
        tasks = [asyncio.to_thread(_check_one_workspace, config_root, config, wsc, fix=fix) for wsc in ws_configs]
        results: list[tuple[str, PreflightResult]] = list(await asyncio.gather(*tasks))

        # Sort by label for deterministic output.
        results.sort(key=lambda r: r[0])

        for label, result in results:
            print(f'\n--- workspace: {label} ---')  # noqa: T201 - CLI output
            _print_check_result(label, result, show_label=False)
            if not result.ok:
                all_ok = False

    # OpenSSF Scorecard checks (--scorecard flag).
    if getattr(args, 'scorecard', False):
        # Walk up to the repo root (where .git lives).
        repo_root = config_root
        while repo_root != repo_root.parent:
            if (repo_root / '.git').exists():
                break
            repo_root = repo_root.parent

        sc_results = run_scorecard_checks(repo_root=repo_root)
        sc_total = len(sc_results)
        sc_passed = sum(1 for r in sc_results if r.passed)

        print('\n--- OpenSSF Scorecard ---')  # noqa: T201 - CLI output
        for r in sc_results:
            if r.passed:
                print(f'  \u2705 {r.check}')  # noqa: T201 - CLI output
            else:
                icon = '\u274c' if r.severity == 'failure' else '\u26a0\ufe0f'
                print(f'  {icon} {r.check}: {r.message}')  # noqa: T201 - CLI output
                if r.hint:
                    print(f'     = hint: {r.hint}')  # noqa: T201 - CLI output
        print(f'\n  Scorecard: {sc_passed}/{sc_total}')  # noqa: T201 - CLI output
        if sc_passed < sc_total:
            all_ok = False

    # OSV vulnerability scanning (--osv flag).
    if getattr(args, 'osv', False):
        severity_str = getattr(args, 'osv_severity', 'HIGH').upper()
        try:
            threshold = OSVSeverity[severity_str]
        except KeyError:
            logger.error('invalid_osv_severity', value=severity_str)
            return 1

        # Collect PURLs from all resolved workspaces.
        all_purls: list[str] = []
        for ws_cfg in ws_configs:
            ws_root = _effective_workspace_root(config_root, ws_cfg)
            ws_packages = discover_packages(
                ws_root,
                exclude_patterns=ws_cfg.exclude,
                ecosystem=ws_cfg.ecosystem or 'python',
            )
            for pkg in ws_packages:
                purl = f'pkg:pypi/{pkg.name}@{pkg.version}'
                if purl not in all_purls:
                    all_purls.append(purl)

        print('\n--- OSV Vulnerability Scan ---')  # noqa: T201 - CLI output
        vulns = await check_osv_vulnerabilities(all_purls, severity_threshold=threshold)
        if vulns:
            for v in vulns:
                icon = '\U0001f534' if v.severity.value >= OSVSeverity.CRITICAL.value else '\U0001f7e0'
                print(f'  {icon} {v.severity.name}: {v.id} in {v.purl}')  # noqa: T201 - CLI output
                if v.summary:
                    print(f'     {v.summary}')  # noqa: T201 - CLI output
                if v.details_url:
                    print(f'     {v.details_url}')  # noqa: T201 - CLI output
            all_ok = False
        else:
            print(f'  \u2705 No vulnerabilities at or above {severity_str}.')  # noqa: T201 - CLI output

    return 0 if all_ok else 1


async def _cmd_version(args: argparse.Namespace) -> int:
    """Handle the ``version`` subcommand."""
    config_root = _find_workspace_root()
    config = load_config(config_root)
    ws_config = _resolve_ws_config(config, getattr(args, 'workspace', None))
    ws_root = _effective_workspace_root(config_root, ws_config)
    vcs, _pm, _forge, _registry = _create_backends(config_root, config, ws_root=ws_root, ws_config=ws_config)

    packages = discover_packages(
        ws_root,
        exclude_patterns=ws_config.exclude,
        ecosystem=ws_config.ecosystem or 'python',
    )

    # Filter out exclude_bump packages before computing bumps.
    resolved_exclude_bump = resolve_group_refs(ws_config.exclude_bump, ws_config.groups)
    if resolved_exclude_bump:
        bump_excluded = {p.name for p in packages if _match_exclude_patterns(p.name, resolved_exclude_bump)}
        if bump_excluded:
            logger.info('exclude_bump', count=len(bump_excluded), names=sorted(bump_excluded))
        packages = [p for p in packages if p.name not in bump_excluded]

    graph = build_graph(packages)
    propagate_graph = graph if (ws_config.propagate_bumps and not ws_config.synchronize) else None
    pkg_configs = build_package_configs(ws_config, [p.name for p in packages])
    versions = await compute_bumps(
        packages,
        vcs,
        tag_format=ws_config.tag_format,
        force_unchanged=args.force_unchanged,
        ignore_unknown_tags=getattr(args, 'ignore_unknown_tags', False),
        graph=propagate_graph,
        synchronize=ws_config.synchronize,
        major_on_zero=ws_config.major_on_zero,
        max_commits=ws_config.max_commits,
        bootstrap_sha=ws_config.bootstrap_sha,
        versioning_scheme=ws_config.versioning_scheme,
        package_configs=pkg_configs,
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
    config_root = _find_workspace_root()
    config = load_config(config_root)
    ws_config = _resolve_ws_config(config, getattr(args, 'workspace', None))
    ws_root = _effective_workspace_root(config_root, ws_config)
    vcs, _pm, _forge, _registry = _create_backends(config_root, config, ws_root=ws_root, ws_config=ws_config)

    all_packages = discover_packages(
        ws_root,
        exclude_patterns=ws_config.exclude,
        ecosystem=ws_config.ecosystem or 'python',
    )
    group = getattr(args, 'group', None)
    packages = _maybe_filter_group(all_packages, ws_config, group)

    dry_run = getattr(args, 'dry_run', False)
    today = utc_today()

    # Generate changelogs concurrently (git log is read-only).
    async def _gen_one(pkg: Package) -> tuple[Package, Changelog | None]:
        tag = format_tag(ws_config.tag_format, name=pkg.name, version=pkg.version, label=ws_config.label)
        tag_exists = await vcs.tag_exists(tag)
        since_tag = tag if tag_exists else None
        changelog = await generate_changelog(
            vcs=vcs,
            version=pkg.version,
            since_tag=since_tag,
            paths=[str(pkg.path)],
            date=today,
        )
        return (pkg, changelog if changelog.sections else None)

    gen_results = await asyncio.gather(*(_gen_one(pkg) for pkg in packages))

    written = 0
    skipped = 0
    for pkg, changelog in gen_results:
        if changelog is None:
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


async def _cmd_init(args: argparse.Namespace) -> int:
    """Handle the ``init`` subcommand.

    Detects all ecosystems in the monorepo and scaffolds a
    ``releasekit.toml`` at the monorepo root.  If ``--ecosystem``
    is specified, only that ecosystem is included in the generated
    config.  After scaffolding, scans existing git tags and writes
    ``bootstrap_sha`` for mid-stream adoption.
    """
    monorepo_root, ecosystems = _resolve_ecosystems(args)
    dry_run = getattr(args, 'dry_run', False)
    force = getattr(args, 'force', False)

    if ecosystems:
        eco_summary = ', '.join(f'{e.ecosystem.value} ({e.root.relative_to(monorepo_root)})' for e in ecosystems)
        logger.info('init_detected_ecosystems', ecosystems=eco_summary)

    # Multi-ecosystem path: generate one [workspace.<label>] per ecosystem.
    if len(ecosystems) > 1 or (ecosystems and ecosystems[0].root != monorepo_root):
        eco_tuples = [
            (e.ecosystem.value, e.ecosystem.value if e.ecosystem.value != 'python' else 'py', e.root)
            for e in ecosystems
        ]
        toml_fragment = scaffold_multi_config(
            monorepo_root,
            eco_tuples,
            dry_run=dry_run,
            force=force,
        )
    else:
        # Single-ecosystem at monorepo root: use original scaffold_config.
        workspace_root = ecosystems[0].root if ecosystems else monorepo_root
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

    # Generate SECURITY-INSIGHTS.yml if requested.
    if getattr(args, 'security_insights', False):
        si_path = monorepo_root / 'SECURITY-INSIGHTS.yml'
        si_config = SecurityInsightsConfig(
            project_name=monorepo_root.name,
            repo_url=f'https://github.com/{monorepo_root.name}',
        )
        si_result = generate_security_insights(
            si_config,
            output_path=si_path,
            dry_run=dry_run,
        )
        if si_result.generated:
            print(f'  \u2705 SECURITY-INSIGHTS.yml written to {si_path}')  # noqa: T201
        elif si_result.reason and 'dry-run' in si_result.reason:
            print('  \U0001f50d Would generate SECURITY-INSIGHTS.yml')  # noqa: T201
        else:
            print(f'  \u274c SECURITY-INSIGHTS.yml: {si_result.reason}')  # noqa: T201

    # Scan existing git tags and write bootstrap_sha.
    config_path = monorepo_root / 'releasekit.toml'
    if config_path.exists():
        config = load_config(monorepo_root)
        vcs = GitCLIBackend(monorepo_root)
        report = await scan_and_bootstrap(
            config_path,
            config,
            vcs,
            dry_run=dry_run,
        )
        print_tag_scan_report(report)

    return 0


async def _cmd_rollback(args: argparse.Namespace) -> int:
    """Handle the ``rollback`` subcommand.

    Deletes git tags (local + remote) and platform releases. With
    ``--all-tags``, discovers and deletes every tag pointing to the
    same commit as the given tag (i.e. all per-package tags from the
    same release). With ``--yank``, also yanks the released versions
    from the package registry (where supported).
    """
    config_root = _find_workspace_root()
    config = load_config(config_root)
    ws_label = next(iter(config.workspaces), None)
    ws_config = config.workspaces.get(ws_label) if ws_label else None
    vcs, _pm, forge, registry = _create_backends(
        config_root,
        config,
        ws_config=ws_config,
    )
    dry_run = getattr(args, 'dry_run', False)
    all_tags = getattr(args, 'all_tags', False)
    yank = getattr(args, 'yank', False)
    yank_reason = getattr(args, 'yank_reason', '')
    tag = args.tag

    tags_to_delete: list[str] = []

    if all_tags and await vcs.tag_exists(tag):
        # Find the commit the given tag points to, then find all
        # tags pointing to that same commit.
        try:
            commit_sha = await vcs.tag_commit_sha(tag)
            if commit_sha:
                all_repo_tags = await vcs.list_tags()
                sibling_tags = []
                for t in all_repo_tags:
                    if await vcs.tag_commit_sha(t) == commit_sha:
                        sibling_tags.append(t)
                tags_to_delete = sibling_tags
                logger.info(
                    'Found %d tags at commit %s: %s',
                    len(sibling_tags),
                    commit_sha[:12],
                    ', '.join(sibling_tags),
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning('Could not discover sibling tags: %s', exc)

    # Fallback: just the single tag the user specified.
    if not tags_to_delete:
        tags_to_delete = [tag]

    deleted: list[str] = []
    for t in tags_to_delete:
        if await vcs.tag_exists(t):
            logger.info('Deleting tag %s', t)
            await vcs.delete_tag(t, remote=True, dry_run=dry_run)
            deleted.append(t)
        else:
            logger.info('Tag %s does not exist locally', t)

    if forge is not None and await forge.is_available():

        async def _delete_release(t: str) -> None:
            logger.info('Deleting platform release for %s', t)
            try:
                await forge.delete_release(t, dry_run=dry_run)
            except Exception as exc:  # noqa: BLE001
                logger.warning('Release deletion failed for %s: %s', t, exc)

        await asyncio.gather(*(_delete_release(t) for t in deleted))
    else:
        logger.info('Forge not available, skipping release deletion')

    yanked: list[str] = []
    yank_failed: list[str] = []
    if yank:

        async def _yank_one(pkg_name: str, pkg_version: str) -> tuple[str, bool]:
            logger.info('Yanking %s@%s from registry', pkg_name, pkg_version)
            ok = await registry.yank_version(
                pkg_name,
                pkg_version,
                reason=yank_reason,
                dry_run=dry_run,
            )
            return (f'{pkg_name}@{pkg_version}', ok)

        yank_tasks = []
        for t in deleted:
            parsed = parse_tag(
                t,
                tag_format=ws_config.tag_format if ws_config else '{name}-v{version}',
            )
            if parsed is None:
                logger.warning('Cannot parse tag %s for yank', t)
                continue
            yank_tasks.append(_yank_one(parsed[0], parsed[1]))

        yank_results = await asyncio.gather(*yank_tasks)
        for label, ok in yank_results:
            if ok:
                yanked.append(label)
            else:
                yank_failed.append(label)

    for t in deleted:
        print(f'  \U0001f5d1\ufe0f  Deleted tag: {t}')  # noqa: T201 - CLI output
    for y in yanked:
        print(f'  \U0001f6ab  Yanked: {y}')  # noqa: T201 - CLI output
    for y in yank_failed:
        print(f'  \u26a0\ufe0f  Yank unsupported: {y}')  # noqa: T201 - CLI output

    if not deleted:
        print(f'  \u2139\ufe0f  Tag {tag} not found')  # noqa: T201 - CLI output

    announce_cfg = config.announcements
    if deleted and announce_cfg and announce_cfg.enabled:
        pkg_names = []
        version = ''
        for t in deleted:
            parsed = parse_tag(
                t,
                tag_format=ws_config.tag_format if ws_config else '{name}-v{version}',
            )
            if parsed:
                pkg_names.append(parsed[0])
                if not version:
                    version = parsed[1]

        result = await send_announcements(
            announce_cfg,
            version=version,
            packages=pkg_names,
            event='rollback',
            dry_run=dry_run,
        )
        if result.sent:
            print(f'  \U0001f4e2  Announced rollback to {result.sent} channel(s)')  # noqa: T201 - CLI output
        for err in result.errors:
            print(f'  \u26a0\ufe0f  Announcement failed: {err}')  # noqa: T201 - CLI output

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
    config_root = _find_workspace_root()
    config = load_config(config_root)
    ws_config = _resolve_ws_config(config, getattr(args, 'workspace', None))
    ws_root = _effective_workspace_root(config_root, ws_config)
    vcs, pm, forge, registry = _create_backends(config_root, config, ws_root=ws_root, ws_config=ws_config)

    try:
        result = await prepare_release(
            vcs=vcs,
            pm=pm,
            forge=forge,
            registry=registry,
            workspace_root=ws_root,
            config=config,
            ws_config=ws_config,
            dry_run=args.dry_run,
            force=args.force,
        )
    except RuntimeError as exc:
        logger.error('prepare_error', step='prepare_release', error=str(exc))
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.error('prepare_error', step='prepare_release', error=str(exc), exc_type=type(exc).__name__)
        return 1

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
    config_root = _find_workspace_root()
    config = load_config(config_root)
    ws_config = _resolve_ws_config(config, getattr(args, 'workspace', None))
    vcs, _pm, forge, _registry = _create_backends(config_root, config, ws_config=ws_config)

    manifest_path = Path(args.manifest) if args.manifest else None

    result = await tag_release(
        vcs=vcs,
        forge=forge,
        config=config,
        ws_config=ws_config,
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


async def _cmd_doctor(args: argparse.Namespace) -> int:
    """Handle the ``doctor`` subcommand."""
    config_root = _find_workspace_root()
    config = load_config(config_root)
    ws_config = _resolve_ws_config(config, getattr(args, 'workspace', None))
    ws_root = _effective_workspace_root(config_root, ws_config)
    forge_backend = getattr(args, 'forge_backend', 'cli')
    vcs, _pm, forge, _registry = _create_backends(
        config_root,
        config,
        ws_root=ws_root,
        ws_config=ws_config,
        forge_backend=forge_backend,
    )

    packages = discover_packages(
        ws_root,
        exclude_patterns=ws_config.exclude,
        ecosystem=ws_config.ecosystem or 'python',
    )

    report = await run_doctor(
        packages=packages,
        vcs=vcs,
        forge=forge,
        config=config,
        ws_config=ws_config,
    )

    # Render report.
    severity_icons = {Severity.PASS: '\u2705', Severity.WARN: '\u26a0\ufe0f ', Severity.FAIL: '\u274c'}
    for diag in report.results:
        icon = severity_icons.get(diag.severity, '?')
        print(f'{icon} {diag.name}: {diag.message}')  # noqa: T201
        if diag.hint:
            print(f'   \u2192 {diag.hint}')  # noqa: T201

    passed = len(report.passed)
    warns = len(report.warnings)
    fails = len(report.failures)
    print()  # noqa: T201
    print(f'{passed} passed, {warns} warnings, {fails} failures')  # noqa: T201

    return 0 if report.ok else 1


def _cmd_migrate(args: argparse.Namespace) -> int:
    """Handle the ``migrate`` subcommand.

    Migrates from an alternative release tool (e.g. release-please)
    by reading its config files and generating ``releasekit.toml``.
    """
    source_name = getattr(args, 'from_tool', None)
    dry_run = getattr(args, 'dry_run', False)
    force = getattr(args, 'force', False)

    if not source_name:
        print('  \u274c --from is required. Supported sources:')  # noqa: T201
        for name in sorted(MIGRATION_SOURCES):
            print(f'     \u2022 {name}')  # noqa: T201
        return 1

    source = MIGRATION_SOURCES.get(source_name)
    if source is None:
        print(f'  \u274c Unknown source: {source_name!r}')  # noqa: T201
        print('  Supported sources:')  # noqa: T201
        for name in sorted(MIGRATION_SOURCES):
            print(f'     \u2022 {name}')  # noqa: T201
        return 1

    root = find_monorepo_root()
    report = migrate_from_source(root, source, dry_run=dry_run, force=force)

    if not report.detected:
        print(f'  \u2139\ufe0f  No {source.name} configuration found in {root}')  # noqa: T201
        return 1

    if report.toml_content:
        print_scaffold_preview(report.toml_content)

    if report.written:
        print(f"  \u2705 Migrated from {source.name}. Run 'releasekit init' to scan tags.")  # noqa: T201
    elif dry_run:
        print('  (dry-run: no files modified)')  # noqa: T201
    elif not report.written and report.toml_content:
        print('  \u2139\ufe0f  releasekit.toml already exists (use --force to overwrite)')  # noqa: T201

    return 0


def _cmd_sign(args: argparse.Namespace) -> int:
    """Handle the ``sign`` subcommand.

    Signs release artifacts using Sigstore keyless signing.
    """
    dry_run = getattr(args, 'dry_run', False)
    output_dir = getattr(args, 'output_dir', None)
    identity_token = getattr(args, 'identity_token', '') or ''

    artifact_paths: list[Path] = []
    raw_paths: list[str] = getattr(args, 'artifacts', [])
    for raw in raw_paths:
        p = Path(raw)
        if p.is_dir():
            artifact_paths.extend(sorted(p.glob('*.tar.gz')))
            artifact_paths.extend(sorted(p.glob('*.whl')))
        elif p.exists():
            artifact_paths.append(p)
        else:
            print(f'  ❌ Not found: {p}')  # noqa: T201
            return 1

    if not artifact_paths:
        print('  ❌ No artifacts to sign. Pass file paths or a directory.')  # noqa: T201
        return 1

    out = Path(output_dir) if output_dir else None
    results = sign_artifacts(
        artifact_paths,
        output_dir=out,
        identity_token=identity_token,
        dry_run=dry_run,
    )

    failures = 0
    for r in results:
        if r.signed:
            print(f'  ✅ Signed: {r.artifact_path.name} → {r.bundle_path.name}')  # noqa: T201
        elif r.reason and 'dry-run' in r.reason:
            print(f'  🔍 Would sign: {r.artifact_path.name}')  # noqa: T201
        else:
            print(f'  ❌ {r.artifact_path.name}: {r.reason}')  # noqa: T201
            failures += 1

    return 1 if failures else 0


def _cmd_verify(args: argparse.Namespace) -> int:
    """Handle the ``verify`` subcommand.

    Verifies Sigstore bundles and/or SLSA provenance for release artifacts.
    """
    identity = getattr(args, 'cert_identity', '') or ''
    issuer = getattr(args, 'cert_oidc_issuer', '') or ''
    provenance_file = getattr(args, 'provenance', None)

    artifact_paths: list[Path] = []
    raw_paths: list[str] = getattr(args, 'artifacts', [])
    for raw in raw_paths:
        p = Path(raw)
        if p.is_dir():
            artifact_paths.extend(sorted(p.glob('*.tar.gz')))
            artifact_paths.extend(sorted(p.glob('*.whl')))
        elif p.exists():
            artifact_paths.append(p)
        else:
            print(f'  ❌ Not found: {p}')  # noqa: T201
            return 1

    if not artifact_paths:
        print('  ❌ No artifacts to verify. Pass file paths or a directory.')  # noqa: T201
        return 1

    failures = 0

    # Verify SLSA provenance if --provenance is provided.
    if provenance_file:
        prov_path = Path(provenance_file)
        for artifact_path in artifact_paths:
            ok, reason = verify_provenance(artifact_path, prov_path)
            if ok:
                print(f'  ✅ Provenance: {artifact_path.name}')  # noqa: T201
            else:
                print(f'  ❌ Provenance: {artifact_path.name}: {reason}')  # noqa: T201
                failures += 1

    # Verify Sigstore bundles.
    for artifact_path in artifact_paths:
        bundle_path = artifact_path.parent / f'{artifact_path.name}.sigstore.json'
        if not bundle_path.exists():
            if not provenance_file:
                print(f'  ❌ Bundle not found: {bundle_path.name}')  # noqa: T201
                failures += 1
            continue

        result = verify_artifact(
            artifact_path,
            bundle_path,
            identity=identity,
            issuer=issuer,
        )
        if result.verified:
            print(f'  ✅ Sigstore: {artifact_path.name}')  # noqa: T201
        else:
            print(f'  ❌ Sigstore: {artifact_path.name}: {result.reason}')  # noqa: T201
            failures += 1

    return 1 if failures else 0


def _cmd_compliance(args: argparse.Namespace) -> int:
    """Handle the ``compliance`` subcommand.

    Prints an OSPS Baseline compliance report for the repository.
    """
    config_root = _find_workspace_root()
    fmt = getattr(args, 'format', 'table')

    _status_icons = {
        ComplianceStatus.MET: '\u2705',
        ComplianceStatus.PARTIAL: '\u26a0\ufe0f',
        ComplianceStatus.GAP: '\u274c',
    }

    def _show_progress(c: ComplianceControl, current: int, total: int) -> None:
        icon = _status_icons.get(c.status, '?')
        sys.stderr.write(f'\r  [{current}/{total}] {icon} {c.id:<14} {c.control}')
        sys.stderr.write('\033[K')  # clear to end of line
        sys.stderr.flush()

    on_progress = _show_progress if fmt != 'json' and sys.stderr.isatty() else None
    controls = evaluate_compliance(config_root, on_progress=on_progress)

    if on_progress is not None:
        sys.stderr.write('\r\033[K')  # clear the progress line
        sys.stderr.flush()

    if fmt == 'json':
        print(compliance_to_json(controls))  # noqa: T201
    else:
        print_compliance_table(controls, console=Console())

    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    """Handle the ``validate`` subcommand.

    Runs all available validators against generated release artifacts.
    Auto-detects provenance, attestation, SBOM, and SECURITY-INSIGHTS
    files in the workspace root.
    """
    config_root = _find_workspace_root()
    fmt = getattr(args, 'format', 'table')

    # Resolve explicit paths from CLI args.
    raw_paths: list[str] = getattr(args, 'artifacts', []) or []
    artifact_paths: list[Path] = []
    for raw in raw_paths:
        p = Path(raw)
        if p.is_dir():
            artifact_paths.extend(sorted(p.iterdir()))
        elif p.exists():
            artifact_paths.append(p)
        else:
            print(f'  \u274c Not found: {p}')  # noqa: T201
            return 1

    if not artifact_paths:
        artifact_paths = detect_artifacts(config_root)

    if not artifact_paths:
        print('  \u2139\ufe0f  No artifacts found to validate.')  # noqa: T201
        return 0

    report = validate_artifacts(artifact_paths)

    if fmt == 'json':
        print(report.to_json())  # noqa: T201
    else:
        print(report.format_table())  # noqa: T201

    return 1 if report.failures else 0


async def _cmd_should_release(args: argparse.Namespace) -> int:
    """Handle the ``should-release`` subcommand.

    Checks whether a release should happen based on each workspace's
    schedule config, releasable commits, and cooldown.

    When ``--workspace`` is specified, checks only that workspace.
    Otherwise, checks **every** workspace independently and exits 0
    if **any** workspace should release.

    Designed for CI cron integration::

        releasekit should-release || exit 0
        releasekit publish --if-needed
    """
    config_root = _find_workspace_root()
    config = load_config(config_root)

    # Determine which workspaces to check.
    ws_label = getattr(args, 'workspace', None)
    if ws_label:
        ws_configs = [_resolve_ws_config(config, ws_label)]
    elif config.workspaces:
        ws_configs = list(config.workspaces.values())
    else:
        ws_configs = [_resolve_ws_config(config, None)]

    async def _check_workspace(wsc: WorkspaceConfig | None) -> tuple[str, ReleaseDecision]:
        label = wsc.label if wsc else 'default'
        ws_root = _effective_workspace_root(config_root, wsc) if wsc else config_root
        vcs, _pm, _forge, _registry = _create_backends(
            config_root,
            config,
            ws_root=ws_root,
            ws_config=wsc,
        )

        packages = discover_packages(
            ws_root,
            exclude_patterns=wsc.exclude if wsc else None,
            ecosystem=wsc.ecosystem if wsc else 'python',
        )

        pkg_configs = build_package_configs(wsc, [p.name for p in packages]) if wsc else None
        bump_results = await compute_bumps(
            packages,
            vcs,
            tag_format=wsc.tag_format if wsc else '{name}-v{version}',
            major_on_zero=wsc.major_on_zero if wsc else False,
            max_commits=wsc.max_commits if wsc else 0,
            versioning_scheme=wsc.versioning_scheme if wsc else 'semver',
            package_configs=pkg_configs,
        )

        # Determine max bump level for this workspace.
        has_releasable = False
        max_bump_level = ''
        bump_order = {'major': 3, 'minor': 2, 'patch': 1}
        for br in bump_results:
            if br.bump != BumpType.NONE:
                has_releasable = True
                level: str = br.bump.value  # type: ignore[union-attr]  # ty narrows Enum incorrectly
                if bump_order.get(level, 0) > bump_order.get(max_bump_level, 0):
                    max_bump_level = level

        # Workspace-specific schedule (falls back to root).
        schedule = wsc.schedule if wsc else config.schedule

        # Get last release time from VCS tags.
        last_release_time = None
        if has_releasable and packages:
            tag_format = wsc.tag_format if wsc else '{name}-v{version}'
            sample_tag = tag_format.format(name=packages[0].name, version=packages[0].version)
            try:
                tag_date_result = await vcs.tag_date(sample_tag)
                if tag_date_result:
                    last_release_time = datetime.fromisoformat(tag_date_result).replace(
                        tzinfo=timezone.utc,
                    )
            except Exception:  # noqa: BLE001
                logger.debug('no_previous_release_tag', tag=sample_tag)

        decision = should_release(
            schedule,
            has_releasable_commits=has_releasable,
            max_bump_level=max_bump_level,
            last_release_time=last_release_time,
        )
        return (label, decision)

    decisions = list(await asyncio.gather(*(_check_workspace(wsc) for wsc in ws_configs)))

    # Output results.
    any_should = any(d.should for _, d in decisions)

    if getattr(args, 'json_output', False):
        results = [{'workspace': label, 'should': d.should, 'reason': d.reason} for label, d in decisions]
        print(json.dumps(results if len(results) > 1 else results[0]))  # noqa: T201
    else:
        for label, decision in decisions:
            status = '✅ YES' if decision.should else '⏭️  NO'
            prefix = f'[{label}] ' if len(decisions) > 1 else ''
            print(f'{prefix}{status}: {decision.reason}')  # noqa: T201

    return 0 if any_should else 1


async def _cmd_promote(args: argparse.Namespace) -> int:
    """Handle the ``promote`` subcommand.

    Promotes a pre-release version to stable by stripping the
    pre-release suffix and creating a new stable release.
    """
    config_root = _find_workspace_root()
    config = load_config(config_root)
    ws_config = _resolve_ws_config(config, getattr(args, 'workspace', None))
    ws_root = _effective_workspace_root(config_root, ws_config)
    vcs, _pm, _forge, _registry = _create_backends(config_root, config, ws_root=ws_root, ws_config=ws_config)

    packages = discover_packages(
        ws_root,
        exclude_patterns=ws_config.exclude,
        ecosystem=ws_config.ecosystem or 'python',
    )

    scheme = ws_config.versioning_scheme or 'semver'
    promoted = 0

    for pkg in packages:
        if not _is_pre(pkg.version):
            continue

        stable = promote_to_stable(pkg.version, scheme=scheme)
        print(f'  📦 {pkg.name}: {pkg.version} → {stable}')  # noqa: T201 - CLI output
        promoted += 1

    if not promoted:
        print('  ℹ️  No pre-release packages to promote.')  # noqa: T201 - CLI output

    print(f'\n  {promoted} package(s) promoted')  # noqa: T201 - CLI output
    return 0


async def _cmd_snapshot(args: argparse.Namespace) -> int:
    """Handle the ``snapshot`` subcommand.

    Computes snapshot versions for all packages using the current
    git SHA or a timestamp.
    """
    config_root = _find_workspace_root()
    config = load_config(config_root)
    ws_config = _resolve_ws_config(config, getattr(args, 'workspace', None))
    ws_root = _effective_workspace_root(config_root, ws_config)
    vcs, _pm, _forge, _registry = _create_backends(config_root, config, ws_root=ws_root, ws_config=ws_config)

    packages = discover_packages(
        ws_root,
        exclude_patterns=ws_config.exclude,
        ecosystem=ws_config.ecosystem or 'python',
    )

    graph = build_graph(packages)
    propagate_graph = graph if (ws_config.propagate_bumps and not ws_config.synchronize) else None
    pkg_configs = build_package_configs(ws_config, [p.name for p in packages])
    versions = await compute_bumps(
        packages,
        vcs,
        tag_format=ws_config.tag_format,
        graph=propagate_graph,
        synchronize=ws_config.synchronize,
        major_on_zero=ws_config.major_on_zero,
        max_commits=ws_config.max_commits,
        bootstrap_sha=ws_config.bootstrap_sha,
        versioning_scheme=ws_config.versioning_scheme,
        package_configs=pkg_configs,
    )

    snapshot_cfg = SnapshotConfig(
        identifier=getattr(args, 'identifier', ''),
        pr_number=getattr(args, 'pr', ''),
        timestamp=getattr(args, 'timestamp', False),
    )
    snapshot_cfg = await resolve_snapshot_identifier(vcs, snapshot_cfg)

    scheme = ws_config.versioning_scheme or 'semver'
    snapshot_version = compute_snapshot_version(snapshot_cfg, scheme=scheme)
    snapshot_versions = apply_snapshot_versions(versions, snapshot_version)

    fmt = getattr(args, 'format', 'table')
    if fmt == 'json':
        data = [
            {
                'name': v.name,
                'old_version': v.old_version,
                'new_version': v.new_version,
                'bump': v.bump,
                'skipped': v.skipped,
            }
            for v in snapshot_versions
        ]
        print(json.dumps(data, indent=2))  # noqa: T201 - CLI output
    else:
        print(f'  Snapshot version: {snapshot_version}')  # noqa: T201 - CLI output
        print()  # noqa: T201 - CLI output
        for v in snapshot_versions:
            if v.skipped:
                print(f'  ⏭️  {v.name}: skipped')  # noqa: T201 - CLI output
            else:
                print(f'  📦 {v.name}: {v.old_version} → {v.new_version}')  # noqa: T201 - CLI output

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured :class:`argparse.ArgumentParser`.
    """
    RichHelpFormatter.styles['argparse.groups'] = 'bold yellow'
    parser = argparse.ArgumentParser(
        prog='releasekit',
        description='Release orchestration for polyglot monorepos.',
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}',
    )
    parser.add_argument(
        '--workspace',
        '-w',
        metavar='LABEL',
        default=None,
        help='Workspace label from releasekit.toml (e.g. py, js). Defaults to the first workspace.',
    )
    parser.add_argument(
        '--no-ai',
        action='store_true',
        default=False,
        help='Disable all AI features for this run.',
    )
    parser.add_argument(
        '--model',
        metavar='PROVIDER/MODEL',
        default=None,
        help='Override the AI model (e.g. ollama/gemma3:4b, google-genai/gemini-3.0-flash-preview).',
    )
    parser.add_argument(
        '--codename-theme',
        metavar='THEME',
        default=None,
        help=(
            'Theme for AI-generated release codenames '
            '(e.g. mountains, animals, space, mythology, gems, '
            'weather, cities, or any custom theme).'
        ),
    )

    subparsers = parser.add_subparsers(dest='command')

    publish_parser = subparsers.add_parser(
        'publish',
        help='Publish all changed packages to their registry.',
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
        '--ignore-unknown-tags',
        action='store_true',
        help='Fall back to full history if a tag is unreachable.',
    )
    publish_parser.add_argument(
        '--concurrency',
        type=int,
        default=5,
        help='Max packages publishing simultaneously per level (default: 5).',
    )
    publish_parser.add_argument(
        '--check-url',
        help='URL to check for already-published versions.',
    )
    publish_parser.add_argument(
        '--registry-url',
        '--index-url',
        dest='registry_url',
        help='Custom registry URL for both publishing and polling/verification '
        '(e.g. Test PyPI, local Verdaccio, Wombat Dressing Room). '
        'Overrides registry_url in releasekit.toml.',
    )
    publish_parser.add_argument(
        '--dist-tag',
        dest='dist_tag',
        default='',
        help='npm dist-tag for pnpm publish --tag (e.g. latest, next).',
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
    publish_parser.add_argument(
        '--sign',
        action='store_true',
        help='Sign published artifacts with Sigstore after publishing.',
    )
    publish_parser.add_argument(
        '--slsa-provenance',
        action='store_true',
        help='Generate SLSA Provenance v1 in-toto statement for published artifacts (auto-enabled in CI).',
    )
    publish_parser.add_argument(
        '--no-slsa-provenance',
        action='store_true',
        help='Disable SLSA provenance generation (overrides auto-detection and config).',
    )
    publish_parser.add_argument(
        '--sign-provenance',
        action='store_true',
        help='Sign the SLSA provenance file with Sigstore (implies --slsa-provenance).',
    )
    publish_parser.add_argument(
        '--no-pep740',
        action='store_true',
        help='Disable PEP 740 attestation generation for Python packages.',
    )
    publish_parser.add_argument(
        '--skip-check',
        action='append',
        metavar='NAME',
        help=(
            'Skip a preflight check by name (repeatable). '
            'E.g. --skip-check compliance --skip-check security_insights. '
            'Also configurable via skip_checks in releasekit.toml.'
        ),
    )
    publish_parser.add_argument(
        '--if-needed',
        action='store_true',
        help='Exit 0 if no releasable changes (for continuous deploy mode).',
    )
    publish_parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume an interrupted publish run from the saved state file.',
    )
    publish_parser.add_argument(
        '--fresh',
        action='store_true',
        help='Delete any saved state file and start a fresh publish run.',
    )

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
        '--ignore-unknown-tags',
        action='store_true',
        help='Fall back to full history if a tag is unreachable.',
    )
    plan_parser.add_argument(
        '--group',
        '-g',
        metavar='NAME',
        help='Only show packages in this release group.',
    )

    discover_parser = subparsers.add_parser(
        'discover',
        help='List all workspace packages (across all detected ecosystems).',
    )
    discover_parser.add_argument(
        '--format',
        choices=sorted({*FORMATTERS, 'json'}),
        default='table',
        help='Output format (default: table). Supports all graph formats plus json.',
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
        choices=[e.value for e in Ecosystem],
        metavar='ECO',
        help='Only discover packages in this ecosystem.',
    )

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
    check_parser.add_argument(
        '--skip-check',
        action='append',
        metavar='NAME',
        help=('Skip a check by name (repeatable). Also configurable via skip_checks in releasekit.toml.'),
    )
    check_parser.add_argument(
        '--scorecard',
        action='store_true',
        help='Run OpenSSF Scorecard-aligned security checks (SECURITY.md, CI, pinned deps, permissions).',
    )
    check_parser.add_argument(
        '--osv',
        action='store_true',
        help='Scan workspace dependencies for known vulnerabilities via OSV.dev.',
    )
    check_parser.add_argument(
        '--osv-severity',
        default='HIGH',
        metavar='LEVEL',
        help='Minimum OSV severity to report: LOW, MEDIUM, HIGH, CRITICAL (default: HIGH).',
    )

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
        '--ignore-unknown-tags',
        action='store_true',
        help='Fall back to full history if a tag is unreachable.',
    )
    version_parser.add_argument(
        '--group',
        '-g',
        metavar='NAME',
        help='Only show versions for packages in this release group.',
    )

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

    explain_parser = subparsers.add_parser(
        'explain',
        help='Explain an error code.',
    )
    explain_parser.add_argument(
        'code',
        help='Error code to explain (e.g., RK-PREFLIGHT-DIRTY-WORKTREE).',
    )

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
        choices=[e.value for e in Ecosystem],
        metavar='ECO',
        help='Only init for this ecosystem.',
    )
    init_parser.add_argument(
        '--security-insights',
        action='store_true',
        help='Also generate SECURITY-INSIGHTS.yml (OpenSSF Security Insights v2).',
    )

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
    rollback_parser.add_argument(
        '--all-tags',
        action='store_true',
        help=(
            'Delete ALL per-package tags that point to the same commit as the given tag, not just the one specified.'
        ),
    )
    rollback_parser.add_argument(
        '--yank',
        action='store_true',
        help=(
            'Also yank (hide) the released versions from the package '
            'registry. Not all registries support this. '
            'Default: only delete tags and platform releases.'
        ),
    )
    rollback_parser.add_argument(
        '--yank-reason',
        default='',
        help='Human-readable reason for the yank (shown to users).',
    )

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

    completion_parser = subparsers.add_parser(
        'completion',
        help='Generate shell completion script.',
    )
    completion_parser.add_argument(
        'shell',
        choices=['bash', 'zsh', 'fish'],
        help='Shell to generate completions for.',
    )

    doctor_parser = subparsers.add_parser(
        'doctor',
        help='Diagnose release state: config, tags, VCS, forge connectivity.',
    )
    doctor_parser.add_argument(
        '--forge-backend',
        choices=['cli', 'api'],
        default='cli',
        help="Forge transport: 'cli' (forge CLI tool) or 'api' (REST API).",
    )

    migrate_parser = subparsers.add_parser(
        'migrate',
        help='Migrate from an alternative release tool (e.g. release-please).',
    )
    migrate_parser.add_argument(
        '--from',
        dest='from_tool',
        choices=sorted(MIGRATION_SOURCES),
        help='Source tool to migrate from.',
    )
    migrate_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be written without modifying files.',
    )
    migrate_parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing releasekit.toml.',
    )

    sign_parser = subparsers.add_parser(
        'sign',
        help='Sign release artifacts with Sigstore (keyless).',
    )
    sign_parser.add_argument(
        'artifacts',
        nargs='+',
        help='Artifact files or directories to sign (e.g. dist/).',
    )
    sign_parser.add_argument(
        '--output-dir',
        help='Directory for .sigstore.json bundles (default: same as artifact).',
    )
    sign_parser.add_argument(
        '--identity-token',
        help='Explicit OIDC identity token (default: ambient detection).',
    )
    sign_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be signed without signing.',
    )

    verify_parser = subparsers.add_parser(
        'verify',
        help='Verify Sigstore bundles for release artifacts.',
    )
    verify_parser.add_argument(
        'artifacts',
        nargs='+',
        help='Artifact files or directories to verify.',
    )
    verify_parser.add_argument(
        '--cert-identity',
        help='Expected certificate identity (email or URI).',
    )
    verify_parser.add_argument(
        '--cert-oidc-issuer',
        help='Expected OIDC issuer URL.',
    )
    verify_parser.add_argument(
        '--provenance',
        metavar='FILE',
        help='Verify artifacts against a SLSA provenance file (.intoto.jsonl).',
    )

    should_release_parser = subparsers.add_parser(
        'should-release',
        help='Check if a release should happen (for CI cron integration).',
    )
    should_release_parser.add_argument(
        '--json',
        action='store_true',
        dest='json_output',
        help='Output decision as JSON.',
    )

    subparsers.add_parser(
        'promote',
        help='Promote pre-release packages to stable versions.',
    )

    snapshot_parser = subparsers.add_parser(
        'snapshot',
        help='Compute snapshot versions for CI testing / PR previews.',
    )
    snapshot_parser.add_argument(
        '--identifier',
        default='',
        help='Snapshot identifier (default: git SHA).',
    )
    snapshot_parser.add_argument(
        '--pr',
        default='',
        help='PR number to include in the snapshot version.',
    )
    snapshot_parser.add_argument(
        '--timestamp',
        action='store_true',
        help='Use a timestamp instead of git SHA.',
    )
    snapshot_parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        help='Output format (default: table).',
    )

    compliance_parser = subparsers.add_parser(
        'compliance',
        help='Print OSPS Baseline compliance report for the repository.',
    )
    compliance_parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        help='Output format (default: table).',
    )

    validate_parser = subparsers.add_parser(
        'validate',
        help='Run validators against generated release artifacts.',
    )
    validate_parser.add_argument(
        'artifacts',
        nargs='*',
        help='Artifact files or directories to validate (default: auto-detect).',
    )
    validate_parser.add_argument(
        '--format',
        choices=['table', 'json'],
        default='table',
        help='Output format (default: table).',
    )

    # Add --prerelease to publish, plan, version.
    for p in (publish_parser, plan_parser, version_parser):
        p.add_argument(
            '--prerelease',
            default='',
            metavar='LABEL',
            help='Pre-release label (alpha, beta, rc, dev).',
        )

    # Add --base-branch and --since-tag to publish, plan, version.
    for p in (publish_parser, plan_parser, version_parser):
        p.add_argument(
            '--base-branch',
            default='',
            help='Override the base branch for version computation (hotfix/maintenance).',
        )
        p.add_argument(
            '--since-tag',
            default='',
            help='Override the starting tag for commit scanning.',
        )

    # Add --template to changelog.
    changelog_parser.add_argument(
        '--template',
        default='',
        help='Path to a Jinja2 template for changelog rendering.',
    )
    changelog_parser.add_argument(
        '--incremental',
        action='store_true',
        help='Append to the end of CHANGELOG.md instead of prepending.',
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
            return asyncio.run(_cmd_discover(args))
        if command == 'graph':
            return _cmd_graph(args)
        if command == 'check':
            return asyncio.run(_cmd_check(args))
        if command == 'version':
            return asyncio.run(_cmd_version(args))
        if command == 'changelog':
            return asyncio.run(_cmd_changelog(args))
        if command == 'explain':
            return _cmd_explain(args)
        if command == 'init':
            return asyncio.run(_cmd_init(args))
        if command == 'rollback':
            return asyncio.run(_cmd_rollback(args))
        if command == 'prepare':
            return asyncio.run(_cmd_prepare(args))
        if command == 'release':
            return asyncio.run(_cmd_release(args))
        if command == 'completion':
            return _cmd_completion(args)
        if command == 'doctor':
            return asyncio.run(_cmd_doctor(args))
        if command == 'migrate':
            return _cmd_migrate(args)
        if command == 'sign':
            return _cmd_sign(args)
        if command == 'verify':
            return _cmd_verify(args)
        if command == 'should-release':
            return asyncio.run(_cmd_should_release(args))
        if command == 'promote':
            return asyncio.run(_cmd_promote(args))
        if command == 'snapshot':
            return asyncio.run(_cmd_snapshot(args))
        if command == 'compliance':
            return _cmd_compliance(args)
        if command == 'validate':
            return _cmd_validate(args)

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
