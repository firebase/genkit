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

"""Go module proxy registry backend for releasekit.

The :class:`GoProxyCheck` implements the
:class:`~releasekit.backends.registry.Registry` protocol as a read-only
check against the Go module proxy (``proxy.golang.org``).

Go modules are not uploaded to a registry — they are fetched from VCS
by the proxy on first request. This backend verifies that a tagged
version is available on the proxy by querying its HTTP API::

    GET https://proxy.golang.org/{module}/@v/{version}.info

A 200 response means the version is cached and available.
"""

from __future__ import annotations

import asyncio
import time

from releasekit.backends.registry._types import ChecksumResult
from releasekit.logging import get_logger
from releasekit.net import DEFAULT_POOL_SIZE, DEFAULT_TIMEOUT, http_client, request_with_retry

log = get_logger('releasekit.backends.registry.goproxy')


class GoProxyCheck:
    """Read-only :class:`~releasekit.backends.registry.Registry` for Go modules.

    Queries the Go module proxy to verify that a tagged version is
    available for download.

    Args:
        base_url: Base URL for the Go module proxy. Defaults to
            ``proxy.golang.org``. Use :data:`TEST_BASE_URL` for the
            Go sum test database or a local Athens proxy.
        pool_size: HTTP connection pool size.
        timeout: HTTP request timeout in seconds.
    """

    #: Base URL for the production Go module proxy.
    DEFAULT_BASE_URL: str = 'https://proxy.golang.org'
    #: Base URL for a local Athens proxy (common test setup).
    TEST_BASE_URL: str = 'http://localhost:3000'

    def __init__(
        self,
        *,
        base_url: str = 'https://proxy.golang.org',
        pool_size: int = DEFAULT_POOL_SIZE,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize with proxy base URL, pool size, and timeout."""
        self._base_url = base_url.rstrip('/')
        self._pool_size = pool_size
        self._timeout = timeout

    async def check_published(self, package_name: str, version: str) -> bool:
        """Check if a Go module version is available on the proxy.

        Args:
            package_name: Full Go module path (e.g.
                ``github.com/firebase/genkit/go/genkit``).
            version: Version string without ``v`` prefix (e.g. ``0.5.0``).
        """
        url = f'{self._base_url}/{package_name}/@v/v{version}.info'
        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            available = response.status_code == 200
            if available:
                log.info(
                    'module_available',
                    module=package_name,
                    version=version,
                )
            else:
                log.debug(
                    'module_not_found',
                    module=package_name,
                    version=version,
                    status=response.status_code,
                )
            return available

    async def poll_available(
        self,
        package_name: str,
        version: str,
        *,
        timeout: float = 300.0,
        interval: float = 10.0,
    ) -> bool:
        """Poll the Go proxy until a version appears or timeout is reached.

        The Go proxy may take a few minutes to cache a newly tagged
        version from VCS. This method polls until it appears.
        """
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
                    module=package_name,
                    version=version,
                    attempts=attempt,
                )
                return True

            remaining = deadline - time.monotonic()
            wait = min(interval, remaining)
            if wait > 0:
                log.debug(
                    'poll_waiting',
                    module=package_name,
                    version=version,
                    attempt=attempt,
                    wait=wait,
                )
                await asyncio.sleep(wait)

        log.warning(
            'poll_timeout',
            module=package_name,
            version=version,
            timeout=timeout,
            attempts=attempt,
        )
        return False

    async def project_exists(self, package_name: str) -> bool:
        """Check if a Go module exists on the proxy (any version).

        Queries the ``/@v/list`` endpoint which returns known versions.
        """
        url = f'{self._base_url}/{package_name}/@v/list'
        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            if response.status_code != 200:
                return False
            # The list endpoint returns one version per line.
            return bool(response.text.strip())

    async def latest_version(self, package_name: str) -> str | None:
        """Query the Go proxy for the latest version of a module.

        Uses the ``/@latest`` endpoint.
        """
        url = f'{self._base_url}/{package_name}/@latest'
        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            if response.status_code != 200:
                return None
            try:
                data = response.json()
                version = data.get('Version', '')
                # Strip leading 'v' prefix.
                return version.lstrip('v') if version else None
            except (ValueError, KeyError):
                log.warning('goproxy_parse_error', module=package_name)
                return None

    async def verify_checksum(
        self,
        package_name: str,
        version: str,
        local_checksums: dict[str, str],
    ) -> ChecksumResult:
        """Checksum verification is not applicable for Go modules.

        Go modules use ``go.sum`` for integrity verification, which is
        handled by the ``go`` toolchain itself. Returns a result with
        all files marked as missing (not checked).
        """
        log.info(
            'checksum_noop',
            module=package_name,
            reason='Go modules use go.sum for integrity, not registry checksums.',
        )
        return ChecksumResult(missing=list(local_checksums.keys()))

    async def list_versions(self, package_name: str) -> list[str]:
        """Return all known versions from the Go module proxy.

        Uses the ``/@v/list`` endpoint which returns one version per line.
        """
        url = f'{self._base_url}/{package_name}/@v/list'
        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            if response.status_code != 200:
                return []
            lines = response.text.strip().splitlines()
            # Strip leading 'v' prefix from each version.
            return [v.lstrip('v') for v in reversed(lines) if v.strip()]

    async def yank_version(
        self,
        package_name: str,
        version: str,
        *,
        reason: str = '',
        dry_run: bool = False,
    ) -> bool:
        """Go modules cannot be yanked from the module proxy.

        Once a version is cached by ``proxy.golang.org``, it is
        available forever. The only recourse is to retract the version
        in ``go.mod`` (Go 1.16+) and publish a new version.
        """
        log.warning(
            'goproxy_yank_unsupported',
            module=package_name,
            version=version,
            hint=('Go modules cannot be yanked. Add a retract directive to go.mod and publish a new version instead.'),
        )
        return False


__all__ = [
    'GoProxyCheck',
]
