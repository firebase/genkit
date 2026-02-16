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

"""Registry protocol for releasekit.

The :class:`Registry` protocol defines the async interface for querying
package registries (PyPI, Test PyPI, npm, crates.io, etc.).
Implementations:

- :class:`~releasekit.backends.registry.pypi.PyPIBackend` — PyPI JSON API
- :class:`~releasekit.backends.registry.npm.NpmRegistry` — npm registry API
- :class:`~releasekit.backends.registry.goproxy.GoProxyCheck` — Go module proxy
- :class:`~releasekit.backends.registry.pubdev.PubDevRegistry` — pub.dev API
- :class:`~releasekit.backends.registry.maven_central.MavenCentralRegistry` — Maven Central Search API
- :class:`~releasekit.backends.registry.crates_io.CratesIoRegistry` — crates.io API

Operations are async because they involve network I/O with potential
latency and rate limiting.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from releasekit.backends.registry._types import ChecksumResult as ChecksumResult
from releasekit.backends.registry.crates_io import CratesIoRegistry as CratesIoRegistry
from releasekit.backends.registry.goproxy import GoProxyCheck as GoProxyCheck
from releasekit.backends.registry.maven_central import MavenCentralRegistry as MavenCentralRegistry
from releasekit.backends.registry.npm import NpmRegistry as NpmRegistry
from releasekit.backends.registry.pubdev import PubDevRegistry as PubDevRegistry
from releasekit.backends.registry.pypi import PyPIBackend as PyPIBackend

__all__ = [
    'ChecksumResult',
    'CratesIoRegistry',
    'GoProxyCheck',
    'MavenCentralRegistry',
    'NpmRegistry',
    'PubDevRegistry',
    'PyPIBackend',
    'Registry',
]


@runtime_checkable
class Registry(Protocol):
    """Protocol for package registry queries."""

    async def check_published(self, package_name: str, version: str) -> bool:
        """Return ``True`` if the exact version is already published.

        Args:
            package_name: Package name on the registry.
            version: Version string to check.
        """
        ...

    async def poll_available(
        self,
        package_name: str,
        version: str,
        *,
        timeout: float = 300.0,
        interval: float = 5.0,
    ) -> bool:
        """Poll until a version becomes available on the registry.

        Args:
            package_name: Package name on the registry.
            version: Version to wait for.
            timeout: Maximum seconds to wait.
            interval: Seconds between polls.

        Returns:
            ``True`` if the version became available, ``False`` on timeout.
        """
        ...

    async def project_exists(self, package_name: str) -> bool:
        """Return ``True`` if the project exists on the registry.

        Args:
            package_name: Package name to check.
        """
        ...

    async def latest_version(self, package_name: str) -> str | None:
        """Return the latest published version, or ``None`` if not published.

        Args:
            package_name: Package name to query.
        """
        ...

    async def verify_checksum(
        self,
        package_name: str,
        version: str,
        local_checksums: dict[str, str],
    ) -> ChecksumResult:
        """Verify local checksums against registry-published digests.

        Args:
            package_name: Package name on the registry.
            version: Version string to check.
            local_checksums: Mapping of filename to local SHA-256 hex digest.

        Returns:
            A :class:`ChecksumResult` with matches, mismatches, and
            files missing from the registry.
        """
        ...

    async def list_versions(self, package_name: str) -> list[str]:
        """Return all published versions of a package.

        Used by rollback to discover which versions are on the registry
        and verify the release graph before yanking.

        Args:
            package_name: Package name to query.

        Returns:
            A list of version strings in registry order (newest first
            when the registry supports it, otherwise unspecified order).
            Returns an empty list if the project does not exist.
        """
        ...

    async def yank_version(
        self,
        package_name: str,
        version: str,
        *,
        reason: str = '',
        dry_run: bool = False,
    ) -> bool:
        """Yank (hide) a version from the registry.

        Yanking marks a version as unsuitable for new installs but does
        **not** delete it. Existing lockfiles that pin the exact version
        continue to resolve. This is the safest registry-side rollback.

        Not all registries support yanking:

        - **PyPI**: Yank via ``/manage/project/.../release/.../yank/``
          (requires API token with ``yank`` scope).
        - **npm**: ``npm deprecate <pkg>@<version> "<reason>"``
          (deprecation, not true yank; ``npm unpublish`` is separate).
        - **crates.io**: ``cargo yank --version <version>``
        - **Maven Central**: Not supported (returns ``False``).
        - **pub.dev**: Not supported (returns ``False``).
        - **Go proxy**: Not supported (cached forever; returns ``False``).

        Args:
            package_name: Package name on the registry.
            version: Version string to yank.
            reason: Human-readable reason for the yank (shown to users
                who try to install the yanked version).
            dry_run: Log the action without executing.

        Returns:
            ``True`` if the version was yanked (or would be in dry-run),
            ``False`` if the registry does not support yanking.
        """
        ...
