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

"""Async publish orchestrator for uv workspace packages.

Publishes packages in topological order with semaphore-controlled
concurrency within each level. Each package goes through:

    pin → build → publish → poll → verify → restore

All backends are injected via dependency injection.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Level-by-level      │ Publish packages in layers. Layer 0 first     │
    │                     │ (no deps), then layer 1 (depends on L0), etc. │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Semaphore           │ A sliding window of N concurrent publishes.   │
    │                     │ As one finishes, the next starts immediately. │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Ephemeral pin       │ Temporarily rewrite deps to exact versions    │
    │                     │ for building, then restore the original file. │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Fail-fast           │ If any package in a level fails, cancel the   │
    │                     │ remaining packages and stop the release.      │
    └─────────────────────┴────────────────────────────────────────────────┘

Pipeline per package::

    ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
    │ pin deps │──▶│  build   │──▶│ publish  │──▶│  poll    │
    │ (toml)   │   │ (uv)     │   │ (uv)     │   │ (PyPI)   │
    └──────────┘   └──────────┘   └──────────┘   └──────────┘
                                                       │
                   ┌──────────┐   ┌──────────┐         │
                   │ restore  │◀──│  verify  │◀────────┘
                   │ (toml)   │   │ (smoke)  │
                   └──────────┘   └──────────┘

Usage::

    from releasekit.publisher import PublishConfig, publish_workspace

    result = await publish_workspace(
        vcs=git_backend,
        pm=uv_backend,
        forge=github_backend,
        registry=pypi_backend,
        graph=dep_graph,
        packages=packages,
        levels=levels,
        versions=versions,
        config=PublishConfig(concurrency=5, dry_run=True),
    )
"""

from __future__ import annotations

import hashlib
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from releasekit.backends.forge import Forge
from releasekit.backends.pm import PackageManager
from releasekit.backends.registry import ChecksumResult, Registry
from releasekit.backends.vcs import VCS
from releasekit.errors import E, ReleaseKitError
from releasekit.graph import DependencyGraph, topo_sort
from releasekit.logging import get_logger
from releasekit.observer import PublishObserver, PublishStage
from releasekit.pin import ephemeral_pin
from releasekit.scheduler import Scheduler
from releasekit.state import PackageStatus, RunState
from releasekit.ui import NullProgressUI
from releasekit.versions import PackageVersion
from releasekit.workspace import Package

logger = get_logger(__name__)


@dataclass(frozen=True)
class PublishConfig:
    """Configuration for a publish run.

    Attributes:
        concurrency: Max packages publishing simultaneously per level.
        dry_run: Preview mode — log commands but don't execute.
        check_url: URL to check for existing files (``uv publish --check-url``).
        index_url: Custom index URL (e.g., Test PyPI).
        smoke_test: Whether to run smoke tests after publishing.
        poll_timeout: Seconds to wait for PyPI indexing.
        poll_interval: Seconds between poll attempts.
        max_retries: Retry failed publishes with exponential backoff (0=off).
        retry_base_delay: Base delay in seconds for retry backoff.
        task_timeout: Timeout per publish attempt in seconds (600=10 min).
        force: Skip confirmation prompts.
        workspace_root: Workspace root directory.
        workspace_label: Workspace label for scoping state files.
        dist_tag: npm dist-tag (e.g. ``latest``, ``next``).
            Maps to ``pnpm publish --tag``. Ignored by Python backends.
        publish_branch: Allow publishing from a non-default branch.
            Maps to ``pnpm publish --publish-branch``. Ignored by
            Python backends.
        provenance: Generate npm provenance attestation.
            Maps to ``pnpm publish --provenance``. Ignored by
            Python backends.
    """

    concurrency: int = 5
    dry_run: bool = False
    check_url: str | None = None
    index_url: str | None = None
    smoke_test: bool = True
    verify_checksums: bool = True
    poll_timeout: float = 300.0
    poll_interval: float = 5.0
    max_retries: int = 0
    retry_base_delay: float = 1.0
    task_timeout: float = 600.0
    force: bool = False
    workspace_root: Path = field(default_factory=Path)
    workspace_label: str = ''
    dist_tag: str = ''
    publish_branch: str = ''
    provenance: bool = False


@dataclass
class PublishResult:
    """Result of a complete publish run.

    Attributes:
        published: Names of successfully published packages.
        skipped: Names of skipped packages.
        failed: Mapping of failed package names to error messages.
        state: Final run state for persistence/resume.
    """

    published: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    state: RunState | None = None

    @property
    def ok(self) -> bool:
        """Return True if no packages failed."""
        return len(self.failed) == 0

    def summary(self) -> str:
        """Return a human-readable summary."""
        parts = []
        if self.published:
            parts.append(f'{len(self.published)} published')
        if self.skipped:
            parts.append(f'{len(self.skipped)} skipped')
        if self.failed:
            parts.append(f'{len(self.failed)} failed')
        return ', '.join(parts) if parts else 'no packages processed'


def _compute_dist_checksum(dist_dir: Path) -> dict[str, str]:
    """Compute SHA-256 checksums for all distribution files.

    Args:
        dist_dir: Directory containing .tar.gz and .whl files.

    Returns:
        Mapping of filename to SHA-256 hex digest.
    """
    checksums: dict[str, str] = {}
    for path in sorted(dist_dir.iterdir()):
        if path.suffix in {'.gz', '.whl'}:
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            checksums[path.name] = sha
            logger.debug('dist_checksum', file=path.name, sha256=sha)
    return checksums


def _build_version_map(versions: list[PackageVersion]) -> dict[str, str]:
    """Build a name→version map from version records.

    Only includes packages that were actually bumped (not skipped).
    """
    return {v.name: v.new_version for v in versions if not v.skipped}


async def _publish_one(
    *,
    pkg: Package,
    version: PackageVersion,
    version_map: dict[str, str],
    pm: PackageManager,
    registry: Registry,
    config: PublishConfig,
    state: RunState,
    state_path: Path,
    observer: PublishObserver,
) -> None:
    """Publish a single package through the full pipeline.

    Updates state at each step for resume support. Notifies the
    observer at each pipeline stage for live UI feedback.

    Concurrency is controlled by the :class:`~releasekit.scheduler.Scheduler`,
    not by this function. The scheduler calls this via a closure that
    captures all context.

    Args:
        pkg: Package to publish.
        version: Version record for this package.
        version_map: All package versions for dependency pinning.
        pm: Package manager backend.
        registry: Registry backend for polling.
        config: Publish configuration.
        state: Run state (mutated in place).
        state_path: Path to persist state.
        observer: UI observer for progress callbacks.
    """
    name = pkg.name
    try:
        observer.on_stage(name, PublishStage.PINNING)
        state.set_status(name, PackageStatus.BUILDING)
        state.save(state_path)

        with ephemeral_pin(pkg.manifest_path, version_map):
            observer.on_stage(name, PublishStage.BUILDING)
            with tempfile.TemporaryDirectory(prefix=f'releasekit-{name}-') as tmp:
                dist_dir = Path(tmp)
                await pm.build(
                    pkg.path,
                    output_dir=dist_dir,
                    no_sources=True,
                    dry_run=config.dry_run,
                )

                checksums = _compute_dist_checksum(dist_dir)
                if not config.dry_run and not checksums:
                    raise ReleaseKitError(
                        E.BUILD_FAILED,
                        f'No distribution files produced for {name}.',
                        hint=f"Check 'uv build' output for {pkg.path}.",
                    )

                observer.on_stage(name, PublishStage.PUBLISHING)
                state.set_status(name, PackageStatus.PUBLISHING)
                state.save(state_path)

                await pm.publish(
                    dist_dir,
                    check_url=config.check_url,
                    index_url=config.index_url,
                    dist_tag=config.dist_tag or None,
                    publish_branch=config.publish_branch or None,
                    provenance=config.provenance,
                    dry_run=config.dry_run,
                )

        observer.on_stage(name, PublishStage.POLLING)
        state.set_status(name, PackageStatus.VERIFYING)
        state.save(state_path)

        if not config.dry_run:
            available = await registry.poll_available(
                name,
                version.new_version,
                timeout=config.poll_timeout,
                interval=config.poll_interval,
            )
            if not available:
                raise ReleaseKitError(
                    E.PUBLISH_TIMEOUT,
                    f'{name}=={version.new_version} not available on registry after {config.poll_timeout}s.',
                    hint='The package may still be indexing. Check the registry manually.',
                )

        if config.verify_checksums and not config.dry_run and checksums:
            checksum_result: ChecksumResult = await registry.verify_checksum(
                name,
                version.new_version,
                checksums,
            )
            if not checksum_result.ok:
                mismatched_files = ', '.join(checksum_result.mismatched.keys())
                missing_files = ', '.join(checksum_result.missing)
                detail_parts: list[str] = []
                if mismatched_files:
                    detail_parts.append(f'mismatched: {mismatched_files}')
                if missing_files:
                    detail_parts.append(f'missing: {missing_files}')
                raise ReleaseKitError(
                    E.PUBLISH_CHECKSUM_MISMATCH,
                    f'Checksum verification failed for {name}: {"; ".join(detail_parts)}',
                    hint=(
                        'The published artifact does not match the locally-built '
                        'artifact. This could indicate a supply chain attack or '
                        'a registry processing error. Investigate immediately.'
                    ),
                )

        if config.smoke_test and not config.dry_run:
            observer.on_stage(name, PublishStage.VERIFYING)
            await pm.smoke_test(name, version.new_version, dry_run=config.dry_run)

        observer.on_stage(name, PublishStage.PUBLISHED)
        state.set_status(name, PackageStatus.PUBLISHED)
        state.save(state_path)

        logger.info(
            'package_published',
            package=name,
            version=version.new_version,
            checksums=checksums,
        )

    except ReleaseKitError:
        observer.on_error(name, f'ReleaseKitError in {name}')
        state.set_status(name, PackageStatus.FAILED, error=str(name))
        state.save(state_path)
        raise

    except Exception as exc:
        observer.on_error(name, str(exc))
        state.set_status(name, PackageStatus.FAILED, error=str(exc))
        state.save(state_path)
        raise ReleaseKitError(
            E.PUBLISH_FAILED,
            f'Unexpected error publishing {name}: {exc}',
            hint='Check the build output and registry status. Re-run with --resume to retry.',
        ) from exc


async def publish_workspace(
    *,
    vcs: VCS,
    pm: PackageManager,
    forge: Forge | None,
    registry: Registry,
    graph: DependencyGraph,
    packages: list[Package],
    levels: list[list[Package]] | None = None,
    versions: list[PackageVersion],
    config: PublishConfig,
    state: RunState | None = None,
    observer: PublishObserver | None = None,
) -> PublishResult:
    """Publish all workspace packages using dependency-triggered scheduling.

    Uses a :class:`~releasekit.scheduler.Scheduler` to dispatch packages
    as soon as all their dependencies complete, rather than waiting for
    an entire topological level to finish. This provides faster publishing
    when packages within a level have different dependency sets.

    Args:
        vcs: Version control backend.
        pm: Package manager backend.
        forge: Code forge backend (optional).
        registry: Package registry backend.
        graph: Workspace dependency graph.
        packages: All workspace packages.
        levels: Topological levels (computed from ``graph`` if not provided).
            Used only for state initialization and observer display.
        versions: Computed version bumps from
            :func:`~releasekit.versioning.compute_bumps`.
        config: Publish configuration.
        state: Existing run state for resume (``None`` to start fresh).
        observer: UI observer for progress callbacks (``None`` for no UI).

    Returns:
        A :class:`PublishResult` summarizing the outcome.
    """
    # Default to no-op observer if none provided.
    if observer is None:
        observer = NullProgressUI()

    # Compute levels from graph if not provided.
    if levels is None:
        levels = topo_sort(graph)

    # Build lookup maps.
    ver_map: dict[str, PackageVersion] = {v.name: v for v in versions}
    version_map = _build_version_map(versions)
    pkg_map: dict[str, Package] = {p.name: p for p in packages}

    # Initialize or resume state.
    git_sha = await vcs.current_sha()
    state_name = (
        f'.releasekit-state--{config.workspace_label}.json' if config.workspace_label else '.releasekit-state.json'
    )
    state_path = config.workspace_root / state_name

    if state is None:
        state = RunState(git_sha=git_sha)
        for level_idx, level in enumerate(levels):
            for pkg in level:
                v = ver_map.get(pkg.name)
                if v is None or v.skipped:
                    state.init_package(
                        pkg.name,
                        version=v.new_version if v else '',
                        level=level_idx,
                        status=PackageStatus.SKIPPED,
                    )
                else:
                    state.init_package(
                        pkg.name,
                        version=v.new_version,
                        level=level_idx,
                    )
    else:
        state.validate_sha(git_sha)

    state.save(state_path)

    # Initialize observer with all packages.
    observer_packages: list[tuple[str, int, str]] = []
    for level_idx, level in enumerate(levels):
        for pkg in level:
            v = ver_map.get(pkg.name)
            version_str = v.new_version if v else ''
            observer_packages.append((pkg.name, level_idx, version_str))
    observer.init_packages(observer_packages)

    # Determine which packages are publishable (not skipped/already done).
    publishable: set[str] = set()
    for name, pkg_state in state.packages.items():
        if pkg_state.status == PackageStatus.SKIPPED:
            observer.on_stage(name, PublishStage.SKIPPED)
        elif pkg_state.status == PackageStatus.PUBLISHED:
            pass  # Already done (resume).
        elif name in ver_map and not ver_map[name].skipped:
            publishable.add(name)

    result = PublishResult(state=state)

    # Pre-populate result with already-completed packages (resume support).
    for name, pkg_state in state.packages.items():
        if pkg_state.status == PackageStatus.PUBLISHED:
            result.published.append(name)
        elif pkg_state.status == PackageStatus.SKIPPED:
            result.skipped.append(name)

    if not publishable:
        logger.info('publish_nothing_to_do', reason='all packages skipped or already done')
        state.save(state_path)
        observer.on_complete()
        return result

    # Build the scheduler from the graph.
    scheduler = Scheduler.from_graph(
        graph=graph,
        publishable=publishable,
        concurrency=config.concurrency,
        max_retries=config.max_retries,
        retry_base_delay=config.retry_base_delay,
        task_timeout=config.task_timeout,
        observer=observer,
    )

    # Create the publish callback — closes over all context.
    async def _do_publish(name: str) -> None:
        """Publish a single package (scheduler callback)."""
        pkg = pkg_map[name]
        v = ver_map[name]
        await _publish_one(
            pkg=pkg,
            version=v,
            version_map=version_map,
            pm=pm,
            registry=registry,
            config=config,
            state=state,
            state_path=state_path,
            observer=observer,
        )

    # Run the scheduler.
    sched_result = await scheduler.run(_do_publish)

    # Merge scheduler results into publish result.
    result.published.extend(sched_result.published)
    result.failed.update(sched_result.failed)

    # Save final state.
    state.save(state_path)
    observer.on_complete()

    logger.info(
        'publish_complete',
        summary=result.summary(),
        published=len(result.published),
        skipped=len(result.skipped),
        failed=len(result.failed),
    )
    return result


__all__ = [
    'PublishConfig',
    'PublishResult',
    'publish_workspace',
]
