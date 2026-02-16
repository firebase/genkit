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

"""pub.dev registry backend for releasekit.

The :class:`PubDevRegistry` implements the
:class:`~releasekit.backends.registry.Registry` protocol using the
pub.dev API (``https://pub.dev/api/packages/<name>``).

All methods are async because they involve network I/O.
"""

from __future__ import annotations

import asyncio
import time

from releasekit.backends.registry._types import ChecksumResult
from releasekit.logging import get_logger
from releasekit.net import DEFAULT_POOL_SIZE, DEFAULT_TIMEOUT, http_client, request_with_retry

log = get_logger('releasekit.backends.registry.pubdev')


class PubDevRegistry:
    """pub.dev :class:`~releasekit.backends.registry.Registry` implementation.

    Args:
        base_url: Base URL for the pub.dev API. Defaults to public
            pub.dev. Use :data:`TEST_BASE_URL` for a local
            ``dart_pub_server`` or similar test registry.
        pool_size: HTTP connection pool size.
        timeout: HTTP request timeout in seconds.
    """

    #: Base URL for the production pub.dev registry.
    DEFAULT_BASE_URL: str = 'https://pub.dev'
    #: Base URL for a local dart_pub_server test registry (common default).
    TEST_BASE_URL: str = 'http://localhost:8080'

    def __init__(
        self,
        *,
        base_url: str = 'https://pub.dev',
        pool_size: int = DEFAULT_POOL_SIZE,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize with pub.dev base URL, pool size, and timeout."""
        self._base_url = base_url.rstrip('/')
        self._pool_size = pool_size
        self._timeout = timeout

    async def check_published(self, package_name: str, version: str) -> bool:
        """Check if a specific version exists on pub.dev."""
        url = f'{self._base_url}/api/packages/{package_name}/versions/{version}'
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
        """Poll pub.dev until the version appears or timeout is reached."""
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
        """Check if the package exists on pub.dev (any version)."""
        url = f'{self._base_url}/api/packages/{package_name}'
        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            return response.status_code == 200

    async def latest_version(self, package_name: str) -> str | None:
        """Query pub.dev for the latest version of a package."""
        url = f'{self._base_url}/api/packages/{package_name}'
        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            if response.status_code != 200:
                return None
            try:
                data = response.json()
                return data.get('latest', {}).get('version')
            except (ValueError, KeyError):
                log.warning('pubdev_parse_error', package=package_name)
                return None

    async def verify_checksum(
        self,
        package_name: str,
        version: str,
        local_checksums: dict[str, str],
    ) -> ChecksumResult:
        """Checksum verification against pub.dev.

        pub.dev provides SHA-256 checksums in the archive URL response.
        For now, this returns all files as missing (not checked) since
        pub.dev's API doesn't expose per-file checksums in the same way
        as PyPI.
        """
        log.info(
            'checksum_noop',
            package=package_name,
            reason='pub.dev does not expose per-file checksums via API.',
        )
        return ChecksumResult(missing=list(local_checksums.keys()))

    async def list_versions(self, package_name: str) -> list[str]:
        """Return all published versions from pub.dev (newest first)."""
        url = f'{self._base_url}/api/packages/{package_name}'
        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            if response.status_code != 200:
                return []
            try:
                data = response.json()
                versions = [v['version'] for v in data.get('versions', []) if 'version' in v]
                versions.reverse()
                return versions
            except (ValueError, KeyError):
                log.warning('pubdev_list_versions_error', package=package_name)
                return []

    async def yank_version(
        self,
        package_name: str,
        version: str,
        *,
        reason: str = '',
        dry_run: bool = False,
    ) -> bool:
        """pub.dev does not support yanking or unpublishing.

        Once a package version is published to pub.dev, it cannot be
        removed. The only option is to publish a newer version or
        mark the package as discontinued via the web UI.
        """
        log.warning(
            'pubdev_yank_unsupported',
            package=package_name,
            version=version,
            hint='pub.dev does not support yanking. Publish a new version instead.',
        )
        return False


__all__ = [
    'PubDevRegistry',
]
