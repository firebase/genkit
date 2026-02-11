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


__all__ = [
    'PyPIBackend',
    'Registry',
]
