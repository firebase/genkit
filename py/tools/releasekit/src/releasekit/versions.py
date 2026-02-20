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

"""Version manifest for CI handoff and audit trail.

A :class:`ReleaseManifest` captures the complete versioning state of a
release run: which packages were bumped, what their old/new versions are,
which bump type was applied, and the git SHA at the time of computation.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ PackageVersion      │ One package's version record: old version,    │
    │                     │ new version, bump type, and reason.           │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ ReleaseManifest     │ A snapshot of all packages in a release run.  │
    │                     │ Can be saved as JSON for CI handoff or audit. │
    └─────────────────────┴────────────────────────────────────────────────┘

Usage::

    from releasekit.versions import PackageVersion, ReleaseManifest

    manifest = ReleaseManifest(
        git_sha='abc123',
        packages=[
            PackageVersion(
                name='genkit',
                old_version='0.4.0',
                new_version='0.5.0',
                bump='minor',
                reason='feat: add streaming support',
            ),
        ],
    )

    # Export for CI
    manifest.save(Path('release-manifest.json'))

    # Import in a later CI step
    loaded = ReleaseManifest.load(Path('release-manifest.json'))
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from releasekit.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class PackageVersion:
    """Version record for a single package.

    Attributes:
        name: Normalized package name (e.g. ``"genkit"``).
        old_version: Version before the bump (e.g. ``"0.4.0"``).
        new_version: Version after the bump (e.g. ``"0.5.0"``).
        bump: Bump type applied: ``"major"``, ``"minor"``, ``"patch"``,
            ``"prerelease"``, or ``"none"``.
        reason: Human-readable reason for the bump (e.g. the commit
            message that triggered it, or ``"unchanged"``).
        skipped: Whether this package was skipped (no changes since
            last tag). If ``True``, ``old_version == new_version``.
        tag: The git tag that will be created for this version
            (e.g. ``"genkit-v0.5.0"``).
    """

    name: str
    old_version: str
    new_version: str
    bump: str = 'none'
    reason: str = ''
    skipped: bool = False
    tag: str = ''


@dataclass(frozen=True)
class ReleaseManifest:
    """Snapshot of a release run's versioning state.

    Serialized as JSON for handoff between CI steps (e.g., a "version"
    job writes the manifest, a "publish" job reads it).

    Attributes:
        git_sha: The HEAD SHA at the time versions were computed.
        umbrella_tag: The umbrella tag for this release (e.g. ``"v0.5.0"``).
        packages: List of per-package version records.
        created_at: ISO 8601 timestamp when the manifest was created.
    """

    git_sha: str
    umbrella_tag: str = ''
    packages: list[PackageVersion] = field(default_factory=list)
    created_at: str = ''

    @property
    def bumped(self) -> list[PackageVersion]:
        """Return only packages that were actually bumped."""
        return [p for p in self.packages if not p.skipped]

    @property
    def skipped(self) -> list[PackageVersion]:
        """Return only packages that were skipped (unchanged)."""
        return [p for p in self.packages if p.skipped]

    def save(self, path: Path) -> None:
        """Write the manifest as JSON.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        data = asdict(self)
        try:
            path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        except OSError as exc:
            raise OSError(f'Failed to write manifest to {path}: {exc}') from exc
        logger.info('manifest_saved', path=str(path), packages=len(self.packages))

    @classmethod
    def load(cls, path: Path) -> ReleaseManifest:
        """Load a manifest from a JSON file.

        Args:
            path: Path to the manifest JSON file.

        Returns:
            A :class:`ReleaseManifest` instance.

        Raises:
            OSError: If the file cannot be read.
            ValueError: If the JSON is malformed or missing required fields.
        """
        try:
            text = path.read_text(encoding='utf-8')
        except OSError as exc:
            raise OSError(f'Failed to read manifest from {path}: {exc}') from exc

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f'Invalid JSON in manifest {path}: {exc}') from exc

        packages = [PackageVersion(**pkg) for pkg in data.get('packages', [])]
        try:
            git_sha = data['git_sha']
        except KeyError as exc:
            raise ValueError(f'Manifest {path} is missing required field: git_sha') from exc
        manifest = cls(
            git_sha=git_sha,
            umbrella_tag=data.get('umbrella_tag', ''),
            packages=packages,
            created_at=data.get('created_at', ''),
        )
        logger.info('manifest_loaded', path=str(path), packages=len(packages))
        return manifest


def resolve_umbrella_version(
    bumped: list[PackageVersion],
    core_package: str = '',
) -> str:
    """Pick the umbrella version from the core package, falling back to the first bumped.

    The umbrella tag should reflect the core package's version (e.g. ``genkit``),
    not whichever package happens to sort first in dependency order.

    Args:
        bumped: List of bumped :class:`PackageVersion` records.
        core_package: Name of the core package (from ``ws_config.core_package``).

    Returns:
        The version string to use for the umbrella tag, or ``'0.0.0'`` if
        *bumped* is empty.
    """
    if not bumped:
        return '0.0.0'
    if core_package:
        for pkg in bumped:
            if pkg.name == core_package:
                return pkg.new_version
    return bumped[0].new_version


__all__ = [
    'PackageVersion',
    'ReleaseManifest',
    'resolve_umbrella_version',
]
