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

"""Registry protocol and PyPI backend for releasekit.

The :class:`Registry` protocol defines the async interface for querying
package registries (PyPI, Test PyPI). The default implementation,
:class:`PyPIBackend`, uses the PyPI JSON API via :mod:`releasekit.net`.

Operations are async because they involve network I/O with potential
latency and rate limiting.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from releasekit.logging import get_logger
from releasekit.net import DEFAULT_POOL_SIZE, DEFAULT_TIMEOUT, http_client, request_with_retry

log = get_logger('releasekit.backends.registry')


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

        Downloads the SHA-256 digests from the registry API for the
        given version, then compares each local file's checksum against
        the registry's value.

        Args:
            package_name: Package name on the registry.
            version: Version string to check.
            local_checksums: Mapping of filename to local SHA-256 hex digest
                (from ``_compute_dist_checksum``).

        Returns:
            A :class:`ChecksumResult` with matches, mismatches, and
            files missing from the registry.
        """
        ...


@dataclass(frozen=True)
class ChecksumResult:
    """Result of checksum verification against a registry.

    Attributes:
        matched: Files where local and registry checksums agree.
        mismatched: Files where checksums differ.
            Maps filename to ``(local_sha, registry_sha)``.
        missing: Files not found on the registry.
    """

    matched: list[str] = field(default_factory=list)
    mismatched: dict[str, tuple[str, str]] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Return True if all checksums match and none are missing."""
        return not self.mismatched and not self.missing

    def summary(self) -> str:
        """Return a human-readable summary."""
        parts: list[str] = []
        if self.matched:
            parts.append(f'{len(self.matched)} matched')
        if self.mismatched:
            parts.append(f'{len(self.mismatched)} mismatched')
        if self.missing:
            parts.append(f'{len(self.missing)} missing')
        return ', '.join(parts) if parts else 'no files checked'


class PyPIBackend:
    """Default :class:`Registry` implementation using the PyPI JSON API.

    Args:
        base_url: Base URL for the PyPI JSON API. Defaults to public PyPI.
        pool_size: HTTP connection pool size.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        *,
        base_url: str = 'https://pypi.org',
        pool_size: int = DEFAULT_POOL_SIZE,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize with PyPI base URL, pool size, and timeout."""
        self._base_url = base_url.rstrip('/')
        self._pool_size = pool_size
        self._timeout = timeout

    async def check_published(self, package_name: str, version: str) -> bool:
        """Check if a specific version exists on PyPI."""
        url = f'{self._base_url}/pypi/{package_name}/{version}/json'
        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            return response.status_code == 200

    async def poll_available(
        self,
        package_name: str,
        version: str,
        *,
        timeout: float = 300.0,
        interval: float = 5.0,
    ) -> bool:
        """Poll PyPI until the version appears or timeout is reached."""
        # Clamp interval and timeout to reasonable bounds.
        interval = max(1.0, min(interval, 60.0))
        timeout = max(10.0, min(timeout, 3600.0))

        deadline = time.monotonic() + timeout
        attempt = 0

        while time.monotonic() < deadline:
            attempt += 1
            available = await self.check_published(package_name, version)
            if available:
                log.info(
                    'version_available',
                    package=package_name,
                    version=version,
                    attempts=attempt,
                )
                return True

            remaining = deadline - time.monotonic()
            wait = min(interval, remaining)
            if wait > 0:
                log.debug(
                    'poll_waiting',
                    package=package_name,
                    version=version,
                    attempt=attempt,
                    wait=wait,
                )
                await asyncio.sleep(wait)

        log.warning(
            'poll_timeout',
            package=package_name,
            version=version,
            timeout=timeout,
            attempts=attempt,
        )
        return False

    async def project_exists(self, package_name: str) -> bool:
        """Check if the project exists on PyPI (any version)."""
        url = f'{self._base_url}/pypi/{package_name}/json'
        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            return response.status_code == 200

    async def latest_version(self, package_name: str) -> str | None:
        """Query PyPI for the latest version of a package."""
        url = f'{self._base_url}/pypi/{package_name}/json'
        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            if response.status_code != 200:
                return None

            try:
                data = response.json()
                return data.get('info', {}).get('version')
            except (ValueError, KeyError):
                log.warning('pypi_parse_error', package=package_name)
                return None

    async def verify_checksum(
        self,
        package_name: str,
        version: str,
        local_checksums: dict[str, str],
    ) -> ChecksumResult:
        """Verify local checksums against PyPI-published SHA-256 digests.

        Uses the PyPI JSON API ``/pypi/{name}/{version}/json`` response,
        which includes ``urls[].digests.sha256`` for each distribution file.
        """
        url = f'{self._base_url}/pypi/{package_name}/{version}/json'
        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            if response.status_code != 200:
                log.warning(
                    'checksum_fetch_failed',
                    package=package_name,
                    version=version,
                    status=response.status_code,
                )
                return ChecksumResult(missing=list(local_checksums.keys()))

            try:
                data = response.json()
            except ValueError:
                log.warning('checksum_parse_failed', package=package_name)
                return ChecksumResult(missing=list(local_checksums.keys()))

        # Build filename→sha256 map from PyPI response.
        registry_checksums: dict[str, str] = {}
        for file_info in data.get('urls', []):
            filename = file_info.get('filename', '')
            sha256 = file_info.get('digests', {}).get('sha256', '')
            if filename and sha256:
                registry_checksums[filename] = sha256

        matched: list[str] = []
        mismatched: dict[str, tuple[str, str]] = {}
        missing: list[str] = []

        for filename, local_sha in local_checksums.items():
            registry_sha = registry_checksums.get(filename)
            if registry_sha is None:
                missing.append(filename)
                log.warning(
                    'checksum_file_missing',
                    package=package_name,
                    file=filename,
                )
            elif local_sha == registry_sha:
                matched.append(filename)
                log.debug(
                    'checksum_match',
                    package=package_name,
                    file=filename,
                    sha256=local_sha,
                )
            else:
                mismatched[filename] = (local_sha, registry_sha)
                log.error(
                    'checksum_mismatch',
                    package=package_name,
                    file=filename,
                    local_sha256=local_sha,
                    registry_sha256=registry_sha,
                )

        result = ChecksumResult(
            matched=matched,
            mismatched=mismatched,
            missing=missing,
        )
        log.info(
            'checksum_verification',
            package=package_name,
            version=version,
            summary=result.summary(),
            ok=result.ok,
        )
        return result


__all__ = [
    'ChecksumResult',
    'PyPIBackend',
    'Registry',
]
