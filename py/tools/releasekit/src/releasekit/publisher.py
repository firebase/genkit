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

from releasekit.attestations import sign_distributions
from releasekit.backends.forge import Forge
from releasekit.backends.pm import PackageManager
from releasekit.backends.registry import ChecksumResult, Registry
from releasekit.backends.validation.attestation import (
    PEP740AttestationValidator,
)
from releasekit.backends.validation.schema import (
    ProvenanceSchemaValidator,
)
from releasekit.backends.vcs import VCS
from releasekit.errors import E, ReleaseKitError
from releasekit.graph import DependencyGraph, topo_sort
from releasekit.logging import get_logger
from releasekit.observer import PublishObserver, PublishStage
from releasekit.pin import ephemeral_pin
from releasekit.provenance import (
    BuildContext,
    generate_workspace_provenance,
)
from releasekit.sbom import SBOMFormat, write_sbom
from releasekit.scheduler import Scheduler
from releasekit.signing import sign_artifact
from releasekit.state import PackageStatus, RunState
from releasekit.ui import NullProgressUI
from releasekit.utils.date import utc_iso
from releasekit.versions import PackageVersion, ReleaseManifest
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
        slsa_provenance: Generate SLSA Provenance v1 in-toto statement
            for all published artifacts. The provenance file is written
            to ``<workspace_root>/provenance.intoto.jsonl``.
        pep740_attestations: Generate PEP 740 digital attestations for
            each distribution file using ``pypi-attestations``. Requires
            ambient OIDC credentials (Trusted Publisher). Only applies
            to Python ecosystem publishes.
        config_source: Path to the build configuration file (relative
            to the repo root), recorded in the provenance predicate.
        ecosystem: Package ecosystem identifier (e.g. ``python``,
            ``js``) recorded in the provenance predicate.
    """

    concurrency: int = 5
    dry_run: bool = False
    check_url: str | None = None
    index_url: str | None = None
    smoke_test: bool = True
    verify_checksums: bool = True
    poll_timeout: float = 300.0
    poll_interval: float = 5.0
    max_retries: int = 3
    retry_base_delay: float = 1.0
    task_timeout: float = 600.0
    force: bool = False
    workspace_root: Path = field(default_factory=Path)
    workspace_label: str = ''
    dist_tag: str = ''
    publish_branch: str = ''
    provenance: bool = True
    slsa_provenance: bool = True
    sign_provenance: bool = True
    pep740_attestations: bool = True
    sbom: bool = True
    sbom_formats: list[str] = field(default_factory=lambda: ['cyclonedx', 'spdx'])
    config_source: str = ''
    ecosystem: str = ''


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
    artifact_checksums: dict[str, dict[str, str]] = field(default_factory=dict)
    provenance_path: Path | None = None

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


def _validate_provenance(prov_path: Path) -> None:
    """Run schema validation on a generated provenance file.

    Args:
        prov_path: Path to the provenance ``.intoto.jsonl`` file.
    """
    try:
        vr = ProvenanceSchemaValidator().validate(prov_path)
        if vr.ok:
            logger.info('slsa_provenance_validated', path=str(prov_path))
        else:
            logger.warning(
                'slsa_provenance_validation_failed',
                path=str(prov_path),
                message=vr.message,
                hint='Provenance was written but failed schema validation.',
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            'slsa_provenance_validation_error',
            error=str(exc),
            hint='Could not validate provenance (validator unavailable).',
        )


def _sign_provenance(prov_path: Path) -> None:
    """Sign a provenance file with Sigstore for SLSA L2.

    Args:
        prov_path: Path to the provenance file to sign.
    """
    try:
        sign_result = sign_artifact(prov_path)
        if sign_result.signed:
            logger.info(
                'slsa_provenance_signed',
                path=str(prov_path),
                bundle=str(sign_result.bundle_path),
            )
        else:
            logger.warning(
                'slsa_provenance_sign_failed',
                reason=sign_result.reason,
                hint='Provenance was generated but could not be signed.',
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            'slsa_provenance_sign_error',
            error=str(exc),
            hint='Provenance was generated but signing raised an error.',
        )


def _generate_and_sign_provenance(
    config: PublishConfig,
    result: PublishResult,
    build_start_time: str,
) -> None:
    """Generate SLSA provenance, validate it, and optionally sign it.

    Args:
        config: Publish configuration.
        result: Publish result (provenance_path is set on success).
        build_start_time: ISO 8601 timestamp of build start.
    """
    try:
        build_ctx = BuildContext.from_env()
        prov_stmt = generate_workspace_provenance(
            artifact_checksums=result.artifact_checksums,
            context=build_ctx,
            config_source=config.config_source,
            build_start_time=build_start_time,
            build_finish_time=utc_iso(),
            ecosystem=config.ecosystem,
        )
        prov_name = (
            f'provenance-{config.workspace_label}.intoto.jsonl' if config.workspace_label else 'provenance.intoto.jsonl'
        )
        prov_path = config.workspace_root / prov_name
        prov_stmt.write(prov_path)
        result.provenance_path = prov_path
        logger.info('slsa_provenance_written', path=str(prov_path))

        _validate_provenance(prov_path)

        if config.sign_provenance:
            _sign_provenance(prov_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            'slsa_provenance_failed',
            error=str(exc),
            hint='Provenance generation failed but publish succeeded.',
        )


def _validate_attestation(attestation_path: Path, dist_path: Path) -> None:
    """Run structural validation on a generated PEP 740 attestation.

    Args:
        attestation_path: Path to the ``.publish.attestation`` file.
        dist_path: Path to the distribution file (for logging).
    """
    try:
        vr = PEP740AttestationValidator().validate(attestation_path)
        if vr.ok:
            logger.info('pep740_attestation_validated', dist=str(dist_path))
        else:
            logger.warning(
                'pep740_attestation_validation_failed',
                dist=str(dist_path),
                message=vr.message,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning('pep740_attestation_validation_error', error=str(exc))


def _generate_pep740_attestations(
    config: PublishConfig,
    result: PublishResult,
) -> None:
    """Generate and validate PEP 740 attestations for published distributions.

    Args:
        config: Publish configuration.
        result: Publish result with artifact checksums.
    """
    try:
        for name, checksums in result.artifact_checksums.items():
            dist_paths = [config.workspace_root / 'dist' / fname for fname in checksums]
            existing = [p for p in dist_paths if p.exists()]
            if not existing:
                continue
            attest_results = sign_distributions(existing, dry_run=config.dry_run)
            for ar in attest_results:
                if ar.signed:
                    logger.info(
                        'pep740_attestation_created',
                        package=name,
                        dist=str(ar.dist_path),
                        attestation=str(ar.attestation_path),
                    )
                    _validate_attestation(ar.attestation_path, ar.dist_path)
                elif ar.reason:
                    logger.warning(
                        'pep740_attestation_skipped',
                        package=name,
                        dist=str(ar.dist_path),
                        reason=ar.reason,
                    )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            'pep740_attestation_failed',
            error=str(exc),
            hint='PEP 740 attestation generation failed but publish succeeded.',
        )


def _generate_sboms(
    config: PublishConfig,
    versions: list[PackageVersion],
    git_sha: str,
) -> list[Path]:
    """Generate SBOM files in all configured formats.

    Args:
        config: Publish configuration.
        versions: Version records for the published packages.
        git_sha: The HEAD SHA at the time versions were computed.

    Returns:
        List of paths to the written SBOM files.
    """
    sbom_paths: list[Path] = []
    try:
        manifest = ReleaseManifest(
            git_sha=git_sha,
            packages=versions,
            created_at=utc_iso(),
        )
        output_dir = config.workspace_root
        for fmt_name in config.sbom_formats:
            try:
                fmt = SBOMFormat(fmt_name)
            except ValueError:
                logger.warning(
                    'sbom_format_unknown',
                    format=fmt_name,
                    hint=f'Allowed values: {", ".join(f.value for f in SBOMFormat)}.',
                )
                continue
            path = write_sbom(
                manifest,
                output_dir,
                fmt=fmt,
                ecosystem=config.ecosystem,
            )
            sbom_paths.append(path)
            logger.info('sbom_generated_ok', path=str(path), format=fmt_name)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            'sbom_generation_failed',
            error=str(exc),
            hint='SBOM generation failed but publish succeeded.',
        )
    return sbom_paths


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
    result: PublishResult,
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
        result: Publish result to accumulate checksums into.
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

        # Store checksums for SLSA provenance generation.
        if checksums:
            result.artifact_checksums[name] = dict(checksums)

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
    if observer is None:
        observer = NullProgressUI()

    if levels is None:
        levels = topo_sort(graph)

    ver_map: dict[str, PackageVersion] = {v.name: v for v in versions}
    version_map = _build_version_map(versions)
    pkg_map: dict[str, Package] = {p.name: p for p in packages}

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

    observer_packages: list[tuple[str, int, str]] = []
    for level_idx, level in enumerate(levels):
        for pkg in level:
            v = ver_map.get(pkg.name)
            version_str = v.new_version if v else ''
            observer_packages.append((pkg.name, level_idx, version_str))
    observer.init_packages(observer_packages)

    publishable: set[str] = set()
    for name, pkg_state in state.packages.items():
        if pkg_state.status == PackageStatus.SKIPPED:
            observer.on_stage(name, PublishStage.SKIPPED)
        elif pkg_state.status == PackageStatus.PUBLISHED:
            pass  # Already done (resume).
        elif name in ver_map and not ver_map[name].skipped:
            publishable.add(name)

    result = PublishResult(state=state)

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

    scheduler = Scheduler.from_graph(
        graph=graph,
        publishable=publishable,
        concurrency=config.concurrency,
        max_retries=config.max_retries,
        retry_base_delay=config.retry_base_delay,
        task_timeout=config.task_timeout,
        observer=observer,
    )

    build_start_time = utc_iso()

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
            result=result,
        )

    sched_result = await scheduler.run(_do_publish)

    result.published.extend(sched_result.published)
    result.failed.update(sched_result.failed)

    if config.slsa_provenance and result.published and not config.dry_run:
        _generate_and_sign_provenance(config, result, build_start_time)

    if config.sbom and result.published and not config.dry_run:
        _generate_sboms(config, versions, git_sha)

    if config.pep740_attestations and config.ecosystem == 'python' and result.published:
        _generate_pep740_attestations(config, result)

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
