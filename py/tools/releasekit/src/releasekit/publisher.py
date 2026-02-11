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
        packages=packages,
        levels=levels,
        versions=versions,
        config=PublishConfig(concurrency=5, dry_run=True),
    )
"""

from __future__ import annotations

import asyncio
import hashlib
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from releasekit.backends.forge import Forge
from releasekit.backends.pm import PackageManager
from releasekit.backends.registry import Registry
from releasekit.backends.vcs import VCS
from releasekit.errors import E, ReleaseKitError
from releasekit.logging import get_logger
from releasekit.pin import ephemeral_pin
from releasekit.state import PackageStatus, RunState
from releasekit.ui import NullProgressUI, PublishObserver, PublishStage
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
        force: Skip confirmation prompts.
        workspace_root: Workspace root directory.
    """

    concurrency: int = 5
    dry_run: bool = False
    check_url: str | None = None
    index_url: str | None = None
    smoke_test: bool = True
    poll_timeout: float = 300.0
    poll_interval: float = 5.0
    force: bool = False
    workspace_root: Path = field(default_factory=Path)


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
    semaphore: asyncio.Semaphore,
    observer: PublishObserver,
) -> None:
    """Publish a single package through the full pipeline.

    Acquires the semaphore for concurrency control. Updates state
    at each step for resume support. Notifies the observer at each
    pipeline stage for live UI feedback.

    Args:
        pkg: Package to publish.
        version: Version record for this package.
        version_map: All package versions for dependency pinning.
        pm: Package manager backend.
        registry: Registry backend for polling.
        config: Publish configuration.
        state: Run state (mutated in place).
        state_path: Path to persist state.
        semaphore: Concurrency limiter.
        observer: UI observer for progress callbacks.
    """
    name = pkg.name
    async with semaphore:
        try:
            # Step 1: Pin dependencies.
            observer.on_stage(name, PublishStage.PINNING)
            state.set_status(name, PackageStatus.BUILDING)
            state.save(state_path)

            with ephemeral_pin(pkg.pyproject_path, version_map):
                # Step 2: Build.
                observer.on_stage(name, PublishStage.BUILDING)
                with tempfile.TemporaryDirectory(prefix=f'releasekit-{name}-') as tmp:
                    dist_dir = Path(tmp)
                    pm.build(
                        pkg.path,
                        output_dir=dist_dir,
                        no_sources=True,
                        dry_run=config.dry_run,
                    )

                    # Step 3: Compute checksums.
                    checksums = _compute_dist_checksum(dist_dir)
                    if not config.dry_run and not checksums:
                        raise ReleaseKitError(
                            E.BUILD_FAILED,
                            f'No distribution files produced for {name}.',
                            hint=f"Check 'uv build' output for {pkg.path}.",
                        )

                    # Step 4: Publish.
                    observer.on_stage(name, PublishStage.PUBLISHING)
                    state.set_status(name, PackageStatus.PUBLISHING)
                    state.save(state_path)

                    pm.publish(
                        dist_dir,
                        check_url=config.check_url,
                        index_url=config.index_url,
                        dry_run=config.dry_run,
                    )

            # Step 5: Poll for availability.
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

            # Step 6: Smoke test.
            if config.smoke_test and not config.dry_run:
                observer.on_stage(name, PublishStage.VERIFYING)
                pm.smoke_test(name, version.new_version, dry_run=config.dry_run)

            # Success.
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
            ) from exc


async def publish_workspace(
    *,
    vcs: VCS,
    pm: PackageManager,
    forge: Forge | None,
    registry: Registry,
    packages: list[Package],
    levels: list[list[Package]],
    versions: list[PackageVersion],
    config: PublishConfig,
    state: RunState | None = None,
    observer: PublishObserver | None = None,
) -> PublishResult:
    """Publish all workspace packages in topological order.

    Processes packages level-by-level, with semaphore-controlled
    concurrency within each level. If any package in a level fails,
    subsequent levels are skipped (fail-fast).

    Args:
        vcs: Version control backend.
        pm: Package manager backend.
        forge: Code forge backend (optional).
        registry: Package registry backend.
        packages: All workspace packages.
        levels: Topological levels from :func:`~releasekit.graph.topo_sort`.
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

    # Build lookup maps.
    ver_map: dict[str, PackageVersion] = {v.name: v for v in versions}
    version_map = _build_version_map(versions)

    # Initialize or resume state.
    git_sha = vcs.current_sha()
    state_path = config.workspace_root / '.releasekit-state.json'

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

    # Mark skipped packages in the observer.
    for name, pkg_state in state.packages.items():
        if pkg_state.status == PackageStatus.SKIPPED:
            observer.on_stage(name, PublishStage.SKIPPED)

    result = PublishResult(state=state)
    semaphore = asyncio.Semaphore(config.concurrency)

    for level_idx, level in enumerate(levels):
        # Filter to packages that need publishing in this level.
        level_tasks: list[tuple[Package, PackageVersion]] = []
        for pkg in level:
            pkg_state = state.packages.get(pkg.name)
            if pkg_state is None:
                continue

            # Skip already-completed packages (resume support).
            if pkg_state.status in {
                PackageStatus.PUBLISHED,
                PackageStatus.SKIPPED,
            }:
                if pkg_state.status == PackageStatus.SKIPPED:
                    result.skipped.append(pkg.name)
                else:
                    result.published.append(pkg.name)
                continue

            v = ver_map.get(pkg.name)
            if v is None or v.skipped:
                result.skipped.append(pkg.name)
                continue

            level_tasks.append((pkg, v))

        if not level_tasks:
            logger.debug('level_empty', level=level_idx)
            continue

        logger.info(
            'level_start',
            level=level_idx,
            packages=[t[0].name for t in level_tasks],
            concurrency=config.concurrency,
        )
        observer.on_level_start(level_idx, [t[0].name for t in level_tasks])

        # Launch all packages in this level with semaphore concurrency.
        tasks = [
            asyncio.create_task(
                _publish_one(
                    pkg=pkg,
                    version=v,
                    version_map=version_map,
                    pm=pm,
                    registry=registry,
                    config=config,
                    state=state,
                    state_path=state_path,
                    semaphore=semaphore,
                    observer=observer,
                ),
                name=f'publish-{pkg.name}',
            )
            for pkg, v in level_tasks
        ]

        # Wait for all tasks, collecting results.
        done = await asyncio.gather(*tasks, return_exceptions=True)

        level_failed = False
        for (pkg, _v), outcome in zip(level_tasks, done, strict=False):
            if isinstance(outcome, BaseException):
                result.failed[pkg.name] = str(outcome)
                level_failed = True
                logger.error(
                    'package_failed',
                    package=pkg.name,
                    error=str(outcome),
                )
            else:
                result.published.append(pkg.name)

        # Fail-fast: stop if any package in this level failed.
        if level_failed:
            logger.error(
                'level_failed',
                level=level_idx,
                failed=list(result.failed.keys()),
            )
            break

        logger.info(
            'level_complete',
            level=level_idx,
            published=[t[0].name for t in level_tasks],
        )

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
