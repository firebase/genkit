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

"""Package manager protocol for releasekit.

The :class:`PackageManager` protocol defines the async interface for
building, publishing, and testing packages. Implementations:

- :class:`~releasekit.backends.pm.uv.UvBackend` — ``uv`` CLI
- :class:`~releasekit.backends.pm.pnpm.PnpmBackend` — ``pnpm`` CLI
- :class:`~releasekit.backends.pm.go.GoBackend` — ``go`` CLI
- :class:`~releasekit.backends.pm.dart.DartBackend` — ``dart pub`` CLI
- :class:`~releasekit.backends.pm.maven.MavenBackend` — ``mvn`` / ``gradle`` CLI
- :class:`~releasekit.backends.pm.cargo.CargoBackend` — ``cargo`` CLI
- :class:`~releasekit.backends.pm.maturin.MaturinBackend` — ``maturin`` + ``uv`` CLI
- :class:`~releasekit.backends.pm.bazel.BazelBackend` — ``bazel`` CLI

Design notes:

- ``resolve_check()`` uses ``uv pip install --dry-run`` (D-9) for
  consistency with the uv toolchain.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from releasekit.backends._run import CommandResult
from releasekit.backends.pm.bazel import BazelBackend as BazelBackend
from releasekit.backends.pm.cargo import CargoBackend as CargoBackend
from releasekit.backends.pm.dart import DartBackend as DartBackend
from releasekit.backends.pm.go import GoBackend as GoBackend
from releasekit.backends.pm.maturin import MaturinBackend as MaturinBackend
from releasekit.backends.pm.maven import MavenBackend as MavenBackend
from releasekit.backends.pm.pnpm import PnpmBackend as PnpmBackend
from releasekit.backends.pm.uv import UvBackend as UvBackend

__all__ = [
    'BazelBackend',
    'CargoBackend',
    'DartBackend',
    'GoBackend',
    'MaturinBackend',
    'MavenBackend',
    'PackageManager',
    'PnpmBackend',
    'UvBackend',
]


@runtime_checkable
class PackageManager(Protocol):
    """Protocol for package build and publish operations.

    All methods are async to avoid blocking the event loop when
    shelling out to ``uv`` or other package managers.
    """

    async def build(
        self,
        package_dir: Path,
        *,
        output_dir: Path | None = None,
        no_sources: bool = True,
        dry_run: bool = False,
    ) -> CommandResult:
        """Build a distribution (sdist + wheel) for a package.

        Args:
            package_dir: Path to the package directory containing pyproject.toml.
            output_dir: Directory to place built distributions.
            no_sources: Disable workspace sources during build to test
                standalone installability.
            dry_run: Log the command without executing.
        """
        ...

    async def publish(
        self,
        dist_dir: Path,
        *,
        check_url: str | None = None,
        registry_url: str | None = None,
        dist_tag: str | None = None,
        publish_branch: str | None = None,
        provenance: bool = False,
        dry_run: bool = False,
    ) -> CommandResult:
        """Publish distributions to a package index.

        Args:
            dist_dir: Directory containing .tar.gz and .whl files.
            check_url: URL to check for existing versions (D-7).
            registry_url: Custom index URL (e.g., Test PyPI).
            dist_tag: npm dist-tag (e.g. ``latest``, ``next``).
                Maps to ``pnpm publish --tag``. Ignored by Python backends.
            publish_branch: Allow publishing from a non-default branch.
                Maps to ``pnpm publish --publish-branch``. Ignored by
                Python backends.
            provenance: Generate npm provenance attestation.
                Maps to ``pnpm publish --provenance``. Ignored by
                Python backends.
            dry_run: Log the command without executing.
        """
        ...

    async def lock(
        self,
        *,
        check_only: bool = False,
        upgrade_package: str | None = None,
        cwd: Path | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Update or verify the lock file.

        Args:
            check_only: Only verify the lock file is up-to-date (exit 1 if not).
            upgrade_package: Upgrade a specific package in the lock file (D-2).
            cwd: Working directory for the lock command.
            dry_run: Log the command without executing.
        """
        ...

    async def version_bump(
        self,
        package_dir: Path,
        new_version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Bump the version of a package.

        Args:
            package_dir: Path to the package directory.
            new_version: New version string (PEP 440).
            dry_run: Log the command without executing.
        """
        ...

    async def resolve_check(
        self,
        package_name: str,
        version: str,
        *,
        registry_url: str | None = None,
        dry_run: bool = False,
    ) -> CommandResult:
        """Verify a published package can be resolved by pip (D-9).

        Args:
            package_name: Name of the package on PyPI.
            version: Expected version.
            registry_url: Custom index URL.
            dry_run: Log the command without executing.
        """
        ...

    async def smoke_test(
        self,
        package_name: str,
        version: str,
        *,
        dry_run: bool = False,
    ) -> CommandResult:
        """Smoke-test a published package by importing it.

        Args:
            package_name: Package name to test.
            version: Version to install.
            dry_run: Log the command without executing.
        """
        ...
