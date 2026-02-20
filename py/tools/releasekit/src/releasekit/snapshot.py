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

"""Snapshot release version generation.

Generates ephemeral snapshot versions for CI testing and PR previews.
Snapshot versions are never published to production registries — they
use a special ``0.0.0-dev.<identifier>`` format that sorts below all
real versions.

Key Concepts (ELI5)::

    ┌─────────────────────────┬─────────────────────────────────────────────┐
    │ Concept                 │ Plain-English                               │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Snapshot version        │ A throwaway version like                    │
    │                         │ ``0.0.0-dev.abc1234`` used for testing.     │
    │                         │ Never published to production.              │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ --snapshot              │ CLI flag that replaces computed versions    │
    │                         │ with snapshot versions.                     │
    ├─────────────────────────┼─────────────────────────────────────────────┤
    │ Snapshot identifier     │ Usually the short git SHA, but can also be  │
    │                         │ a timestamp or PR number.                   │
    └─────────────────────────┴─────────────────────────────────────────────┘

Version format::

    Scheme   │ Format
    ─────────┼──────────────────────────────────────
    semver   │ 0.0.0-dev.abc1234
    semver   │ 0.0.0-dev.20260215T1200
    semver   │ 0.0.0-dev.pr-42.abc1234
    pep440   │ 0.0.0.dev20260215

Usage::

    from releasekit.snapshot import compute_snapshot_version, SnapshotConfig

    cfg = SnapshotConfig(prefix='dev', identifier='abc1234')
    v = compute_snapshot_version(cfg, scheme='semver')
    assert v == '0.0.0-dev.abc1234'
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from releasekit.backends.vcs import VCS
from releasekit.logging import get_logger
from releasekit.versions import PackageVersion

logger = get_logger(__name__)


@dataclass(frozen=True)
class SnapshotConfig:
    """Configuration for snapshot version generation.

    Attributes:
        prefix: Version prefix label (default ``"dev"``).
        identifier: Unique identifier for this snapshot. If empty,
            will be auto-populated from git SHA or timestamp.
        pr_number: Optional PR number to include in the version.
        timestamp: Whether to use a timestamp instead of git SHA.
        base_version: Override the base version (default ``"0.0.0"``).
    """

    prefix: str = 'dev'
    identifier: str = ''
    pr_number: str = ''
    timestamp: bool = False
    base_version: str = '0.0.0'


def compute_snapshot_version(
    config: SnapshotConfig,
    *,
    scheme: str = 'semver',
) -> str:
    """Compute a snapshot version string.

    Args:
        config: Snapshot configuration.
        scheme: ``"semver"`` or ``"pep440"``.

    Returns:
        Snapshot version string.
    """
    base = config.base_version
    identifier = config.identifier

    if not identifier:
        if config.timestamp:
            identifier = datetime.now(tz=timezone.utc).strftime('%Y%m%dT%H%M')
        else:
            identifier = 'snapshot'

    if scheme == 'pep440':
        # PEP 440: 0.0.0.dev20260215 (numeric only for dev segment).
        # Use timestamp format for PEP 440 since it requires numeric.
        if config.timestamp or not identifier.isdigit():
            ts = datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M')
            return f'{base}.dev{ts}'
        return f'{base}.dev{identifier}'

    # semver: 0.0.0-dev.abc1234 or 0.0.0-dev.pr-42.abc1234
    parts = [config.prefix]
    if config.pr_number:
        parts.append(f'pr-{config.pr_number}')
    parts.append(identifier)

    suffix = '.'.join(parts)
    return f'{base}-{suffix}'


async def resolve_snapshot_identifier(
    vcs: VCS,
    config: SnapshotConfig,
) -> SnapshotConfig:
    """Resolve the snapshot identifier from git if not already set.

    If ``config.identifier`` is empty, populates it from the current
    git SHA (short form).

    Args:
        vcs: VCS backend.
        config: Snapshot configuration (possibly with empty identifier).

    Returns:
        Updated :class:`SnapshotConfig` with resolved identifier.
    """
    if config.identifier:
        return config

    if config.timestamp:
        ts = datetime.now(tz=timezone.utc).strftime('%Y%m%dT%H%M')
        return SnapshotConfig(
            prefix=config.prefix,
            identifier=ts,
            pr_number=config.pr_number,
            timestamp=config.timestamp,
            base_version=config.base_version,
        )

    sha = await vcs.current_sha()
    short_sha = sha[:7] if sha else 'unknown'

    logger.info('snapshot_identifier_resolved', sha=short_sha)

    return SnapshotConfig(
        prefix=config.prefix,
        identifier=short_sha,
        pr_number=config.pr_number,
        timestamp=config.timestamp,
        base_version=config.base_version,
    )


def apply_snapshot_versions(
    versions: list[PackageVersion],
    snapshot_version: str,
) -> list[PackageVersion]:
    """Replace all computed versions with the snapshot version.

    Packages that were skipped (no changes) remain skipped.

    Args:
        versions: Computed version bumps.
        snapshot_version: The snapshot version to apply.

    Returns:
        New list of :class:`PackageVersion` with snapshot versions.
    """
    result: list[PackageVersion] = []
    for v in versions:
        if v.skipped:
            result.append(v)
            continue

        result.append(
            PackageVersion(
                name=v.name,
                old_version=v.old_version,
                new_version=snapshot_version,
                bump='snapshot',
                reason=f'snapshot: {snapshot_version}',
                skipped=False,
                tag='',  # Snapshots don't get tags.
            )
        )

    logger.info(
        'snapshot_versions_applied',
        version=snapshot_version,
        count=len([v for v in result if not v.skipped]),
    )
    return result


__all__ = [
    'SnapshotConfig',
    'apply_snapshot_versions',
    'compute_snapshot_version',
    'resolve_snapshot_identifier',
]
