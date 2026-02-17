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

"""npm registry backend for releasekit.

The :class:`NpmRegistry` implements the :class:`Registry` protocol
using the npm registry API (https://registry.npmjs.org).

API endpoints used:

- ``GET /{package}`` — Full package metadata ("packument").
  Returns ``dist-tags``, ``versions``, ``time``, etc.
  See: https://github.com/npm/registry/blob/main/docs/REGISTRY-API.md

- ``GET /{package}/{version}`` — Version-specific metadata.
  Returns ``dist.shasum`` (SHA-1) and ``dist.integrity`` (SHA-512).

Scoped packages (e.g. ``@genkit-ai/core``) must be URL-encoded
as ``@genkit-ai%2Fcore`` in the URL path.

All methods are async because they involve network I/O with potential
latency and rate limiting.
"""

from __future__ import annotations

import asyncio
import time
import urllib.parse

from releasekit.backends.registry._types import ChecksumResult
from releasekit.logging import get_logger
from releasekit.net import DEFAULT_POOL_SIZE, DEFAULT_TIMEOUT, http_client, request_with_retry

log = get_logger('releasekit.backends.npm')


def _encode_package_name(name: str) -> str:
    """URL-encode a package name for the registry API.

    Scoped packages like ``@genkit-ai/core`` must be encoded as
    ``@genkit-ai%2Fcore`` (the ``/`` becomes ``%2F``).

    Unscoped packages are returned as-is.
    """
    if name.startswith('@'):
        return urllib.parse.quote(name, safe='@')
    return name


class NpmRegistry:
    """Registry implementation for the npm registry.

    Implements the :class:`~releasekit.backends.registry.Registry`
    protocol using the npm registry JSON API.

    This backend handles **read-side** operations: checking whether
    a version is published, polling for availability, listing versions,
    and verifying checksums.

    When ``registry_url`` is set in ``releasekit.toml``, it overrides
    the base URL for both this backend (polling/verification) **and**
    the publish path (``pnpm publish --registry``).  This works with:

    - **Full mirrors** like `Verdaccio <https://verdaccio.org/>`_
    - **Managed registries** like `Google Cloud Artifact Registry
      <https://cloud.google.com/artifact-registry>`_ (private npm
      hosting with IAM-based access control)
    - **Security proxies** like Google's `Wombat Dressing Room
      <https://github.com/GoogleCloudPlatform/wombat-dressing-room>`_,
      which proxies both reads (``GET /<package>`` → npmjs.org) and
      writes (``PUT /<package>`` with auth/2FA enforcement → npmjs.org)

    See the configuration guide for a worked example.

    Args:
        base_url: Base URL for the npm registry API. Defaults to
            public npm. Use :data:`TEST_BASE_URL` for a local
            Verdaccio or similar test registry.
        pool_size: HTTP connection pool size.
        timeout: HTTP request timeout in seconds.
    """

    #: Base URL for the production npm registry.
    DEFAULT_BASE_URL: str = 'https://registry.npmjs.org'
    #: Base URL for a local Verdaccio test registry (common default).
    TEST_BASE_URL: str = 'http://localhost:4873'

    def __init__(
        self,
        *,
        base_url: str = 'https://registry.npmjs.org',
        pool_size: int = DEFAULT_POOL_SIZE,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize with the npm registry base URL."""
        self._base_url = base_url.rstrip('/')
        self._pool_size = pool_size
        self._timeout = timeout

    async def check_published(self, package_name: str, version: str) -> bool:
        """Check if a specific version exists on the npm registry.

        Uses ``GET /{package}/{version}`` — returns 200 if the version
        exists, 404 otherwise.
        """
        encoded = _encode_package_name(package_name)
        url = f'{self._base_url}/{encoded}/{version}'
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
        """Poll the npm registry until the version appears or timeout is reached.

        npm registry propagation is typically fast (< 30s) but can be
        delayed during high traffic.
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
        """Check if the package exists on npm (any version).

        Uses ``GET /{package}`` — returns 200 if the package exists.
        """
        encoded = _encode_package_name(package_name)
        url = f'{self._base_url}/{encoded}'
        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            return response.status_code == 200

    async def latest_version(self, package_name: str) -> str | None:
        """Query the npm registry for the latest version of a package.

        Reads ``dist-tags.latest`` from the full packument response.
        """
        encoded = _encode_package_name(package_name)
        url = f'{self._base_url}/{encoded}'
        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            if response.status_code != 200:
                return None

            try:
                data = response.json()
                dist_tags = data.get('dist-tags', {})
                return dist_tags.get('latest')
            except (ValueError, KeyError):
                log.warning('npm_parse_error', package=package_name)
                return None

    async def verify_checksum(
        self,
        package_name: str,
        version: str,
        local_checksums: dict[str, str],
    ) -> ChecksumResult:
        """Verify local checksums against npm-published digests.

        The npm registry provides ``dist.shasum`` (SHA-1) and
        ``dist.integrity`` (subresource integrity, usually SHA-512)
        for each version. Since the Registry protocol uses SHA-256
        checksums and npm only provides SHA-1 and SHA-512, this
        implementation logs a warning and marks all files as missing
        if SHA-256 digests are expected.

        For local npm tarballs, the ``shasum`` (SHA-1) is typically
        used. Pass SHA-1 hex digests in ``local_checksums`` to verify
        against the registry's ``dist.shasum``.
        """
        encoded = _encode_package_name(package_name)
        url = f'{self._base_url}/{encoded}/{version}'
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

        # npm provides dist.shasum (SHA-1) per version.
        registry_shasum: str = data.get('dist', {}).get('shasum', '')
        tarball_filename = f'{package_name}-{version}.tgz'

        matched: list[str] = []
        mismatched: dict[str, tuple[str, str]] = {}
        missing: list[str] = []

        for filename, local_sha in local_checksums.items():
            if filename == tarball_filename and registry_shasum:
                if local_sha == registry_shasum:
                    matched.append(filename)
                    log.debug(
                        'checksum_match',
                        package=package_name,
                        file=filename,
                        shasum=local_sha,
                    )
                else:
                    mismatched[filename] = (local_sha, registry_shasum)
                    log.error(
                        'checksum_mismatch',
                        package=package_name,
                        file=filename,
                        local_shasum=local_sha,
                        registry_shasum=registry_shasum,
                    )
            else:
                missing.append(filename)
                log.warning(
                    'checksum_file_missing',
                    package=package_name,
                    file=filename,
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

    async def list_versions(self, package_name: str) -> list[str]:
        """Return all published versions from npm (newest first)."""
        scoped = _encode_package_name(package_name)
        url = f'{self._base_url}/{scoped}'
        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            if response.status_code != 200:
                return []
            try:
                data = response.json()
                versions = list(data.get('versions', {}).keys())
                versions.reverse()
                return versions
            except (ValueError, KeyError):
                log.warning('npm_list_versions_error', package=package_name)
                return []

    async def yank_version(
        self,
        package_name: str,
        version: str,
        *,
        reason: str = '',
        dry_run: bool = False,
    ) -> bool:
        """Deprecate a version on npm (npm's equivalent of yank).

        Uses ``npm deprecate <pkg>@<version> "<reason>"``. This marks
        the version with a deprecation warning but does not remove it.
        For actual removal, use ``npm unpublish`` (only within 72h).
        """
        msg = reason or 'This version has been rolled back.'
        cmd = ['npm', 'deprecate', f'{package_name}@{version}', msg]
        if dry_run:
            log.info('npm_yank_dry_run', package=package_name, version=version, cmd=cmd)
            return True
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                log.info('npm_version_deprecated', package=package_name, version=version)
                return True
            log.warning(
                'npm_deprecate_failed',
                package=package_name,
                version=version,
                stderr=stderr.decode(errors='replace'),
            )
            return False
        except FileNotFoundError:
            log.warning('npm_not_found', hint='npm CLI is required for yank')
            return False


__all__ = [
    'NpmRegistry',
]
