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

"""crates.io registry backend for releasekit.

The :class:`CratesIoRegistry` implements the
:class:`~releasekit.backends.registry.Registry` protocol using the
`crates.io API <https://crates.io/api/v1>`_.

API endpoints used::

    GET /api/v1/crates/{name}              → crate metadata + versions
    GET /api/v1/crates/{name}/{version}    → specific version info

All methods are async because they involve network I/O with potential
latency and rate limiting.
"""

from __future__ import annotations

import asyncio
import time

from releasekit.backends.registry._types import ChecksumResult
from releasekit.logging import get_logger
from releasekit.net import DEFAULT_POOL_SIZE, DEFAULT_TIMEOUT, http_client, request_with_retry

log = get_logger('releasekit.backends.registry.crates_io')


class CratesIoRegistry:
    """crates.io :class:`~releasekit.backends.registry.Registry` implementation.

    Queries the crates.io API to check crate publication status,
    poll for availability, and retrieve version metadata.

    Args:
        base_url: Base URL for the crates.io API. Defaults to
            ``crates.io``. Use :data:`TEST_BASE_URL` for a local
            Alexandrie or similar test registry.
        pool_size: HTTP connection pool size.
        timeout: HTTP request timeout in seconds.
    """

    #: Base URL for the production crates.io registry.
    DEFAULT_BASE_URL: str = 'https://crates.io'
    #: Base URL for a local Alexandrie test registry (common default).
    TEST_BASE_URL: str = 'http://localhost:3000'

    def __init__(
        self,
        *,
        base_url: str = 'https://crates.io',
        pool_size: int = DEFAULT_POOL_SIZE,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize with crates.io base URL, pool size, and timeout."""
        self._base_url = base_url.rstrip('/')
        self._pool_size = pool_size
        self._timeout = timeout

    async def check_published(self, package_name: str, version: str) -> bool:
        """Check if a specific crate version is published on crates.io.

        Args:
            package_name: Crate name (e.g. ``serde``).
            version: Version string (e.g. ``1.0.200``).
        """
        url = f'{self._base_url}/api/v1/crates/{package_name}/{version}'
        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            available = response.status_code == 200
            if available:
                log.info(
                    'crate_version_available',
                    crate=package_name,
                    version=version,
                )
            else:
                log.debug(
                    'crate_version_not_found',
                    crate=package_name,
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
        """Poll crates.io until a version appears or timeout is reached.

        After ``cargo publish``, there may be a short delay before the
        version is visible on the API.
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
                    crate=package_name,
                    version=version,
                    attempts=attempt,
                )
                return True

            remaining = deadline - time.monotonic()
            wait = min(interval, remaining)
            if wait > 0:
                log.debug(
                    'poll_waiting',
                    crate=package_name,
                    version=version,
                    attempt=attempt,
                    wait=wait,
                )
                await asyncio.sleep(wait)

        log.warning(
            'poll_timeout',
            crate=package_name,
            version=version,
            timeout=timeout,
            attempts=attempt,
        )
        return False

    async def project_exists(self, package_name: str) -> bool:
        """Check if a crate exists on crates.io (any version)."""
        url = f'{self._base_url}/api/v1/crates/{package_name}'
        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            return response.status_code == 200

    async def latest_version(self, package_name: str) -> str | None:
        """Query crates.io for the latest non-yanked version of a crate."""
        url = f'{self._base_url}/api/v1/crates/{package_name}'
        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            if response.status_code != 200:
                return None
            try:
                data = response.json()
                # The crate object has a max_stable_version field.
                version = data.get('crate', {}).get('max_stable_version')
                if version:
                    return str(version)
                # Fallback: newest_version includes pre-releases.
                version = data.get('crate', {}).get('newest_version')
                return str(version) if version else None
            except (ValueError, KeyError):
                log.warning('crates_io_parse_error', crate=package_name)
                return None

    async def verify_checksum(
        self,
        package_name: str,
        version: str,
        local_checksums: dict[str, str],
    ) -> ChecksumResult:
        """Checksum verification for crates.io.

        crates.io provides a ``cksum`` (SHA-256) for each published
        version in the version metadata. Per-file checksums are not
        available — returns missing for all local files.
        """
        log.info(
            'checksum_noop',
            crate=package_name,
            reason='crates.io provides per-crate checksums, not per-file.',
        )
        return ChecksumResult(missing=list(local_checksums.keys()))

    async def list_versions(self, package_name: str) -> list[str]:
        """Return all published versions from crates.io (newest first)."""
        url = f'{self._base_url}/api/v1/crates/{package_name}/versions'
        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            if response.status_code != 200:
                return []
            try:
                data = response.json()
                return [v['num'] for v in data.get('versions', []) if 'num' in v]
            except (ValueError, KeyError):
                log.warning('crates_io_list_versions_error', crate=package_name)
                return []

    async def yank_version(
        self,
        package_name: str,
        version: str,
        *,
        reason: str = '',
        dry_run: bool = False,
    ) -> bool:
        """Yank a crate version via ``cargo yank``."""
        cmd = ['cargo', 'yank', '--version', version, package_name]
        if dry_run:
            log.info('cargo_yank_dry_run', crate=package_name, version=version, cmd=cmd)
            return True
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                log.info('crate_yanked', crate=package_name, version=version)
                return True
            log.warning(
                'cargo_yank_failed',
                crate=package_name,
                version=version,
                stderr=stderr.decode(errors='replace'),
            )
            return False
        except FileNotFoundError:
            log.warning('cargo_not_found', hint='cargo CLI is required for yank')
            return False


__all__ = [
    'CratesIoRegistry',
]
