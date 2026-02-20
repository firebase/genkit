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

"""Maven Central registry backend for releasekit.

The :class:`MavenCentralRegistry` implements the
:class:`~releasekit.backends.registry.Registry` protocol using the
Maven Central Search API (``https://search.maven.org``).

Maven artifact coordinates use the format ``groupId:artifactId``.
The ``package_name`` parameter should be in this format.

All methods are async because they involve network I/O.
"""

from __future__ import annotations

import asyncio
import time

from releasekit.backends.registry._types import ChecksumResult
from releasekit.logging import get_logger
from releasekit.net import DEFAULT_POOL_SIZE, DEFAULT_TIMEOUT, http_client, request_with_retry

log = get_logger('releasekit.backends.registry.maven_central')


class MavenCentralRegistry:
    """Maven Central :class:`~releasekit.backends.registry.Registry` implementation.

    This backend polls for artifact availability using the Maven Central
    Solr Search API (``search.maven.org``).  It works out of the box
    when publishing to Maven Central (via Sonatype OSSRH or the Central
    Portal).

    When ``registry_url`` is set in ``releasekit.toml``, the publish
    path (``MavenBackend``) is redirected to the custom repository
    (e.g. `Google Cloud Artifact Registry
    <https://cloud.google.com/artifact-registry>`_), but this polling
    backend still queries ``search.maven.org``.  For private
    registries that don't index on Maven Central, polling will not
    detect the artifact — verify publication via ``gcloud artifacts
    versions list`` or similar.

    Args:
        base_url: Base URL for the Maven Central Search API. Defaults
            to ``search.maven.org``. Use :data:`TEST_BASE_URL` for a
            local Nexus or Reposilite staging instance.
        pool_size: HTTP connection pool size.
        timeout: HTTP request timeout in seconds.
    """

    #: Base URL for the production Maven Central Search API.
    DEFAULT_BASE_URL: str = 'https://search.maven.org'
    #: Base URL for a local Nexus/Reposilite test registry (common default).
    TEST_BASE_URL: str = 'http://localhost:8081'

    def __init__(
        self,
        *,
        base_url: str = 'https://search.maven.org',
        pool_size: int = DEFAULT_POOL_SIZE,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize with Maven Central base URL, pool size, and timeout."""
        self._base_url = base_url.rstrip('/')
        self._pool_size = pool_size
        self._timeout = timeout

    @staticmethod
    def _parse_coordinates(package_name: str) -> tuple[str, str]:
        """Parse ``groupId:artifactId`` into a tuple.

        Args:
            package_name: Maven coordinates (e.g. ``com.google.genkit:genkit-core``).

        Returns:
            Tuple of (groupId, artifactId).
        """
        parts = package_name.split(':', 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        # If no colon, treat the whole string as artifactId.
        return '', parts[0]

    async def check_published(self, package_name: str, version: str) -> bool:
        """Check if a specific version exists on Maven Central.

        Args:
            package_name: Maven coordinates ``groupId:artifactId``.
            version: Version string to check.
        """
        group_id, artifact_id = self._parse_coordinates(package_name)
        query = f'g:"{group_id}" AND a:"{artifact_id}" AND v:"{version}"'
        url = f'{self._base_url}/solrsearch/select?q={query}&rows=1&wt=json'

        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            if response.status_code != 200:
                return False
            try:
                data = response.json()
                num_found = data.get('response', {}).get('numFound', 0)
                return num_found > 0
            except (ValueError, KeyError):
                return False

    async def poll_available(
        self,
        package_name: str,
        version: str,
        *,
        timeout: float = 600.0,
        interval: float = 30.0,
    ) -> bool:
        """Poll Maven Central until the version appears or timeout is reached.

        Maven Central indexing can take 10-30 minutes after deployment,
        so the default timeout and interval are longer than PyPI/npm.
        """
        interval = max(5.0, min(interval, 120.0))
        timeout = max(30.0, min(timeout, 7200.0))

        deadline = time.monotonic() + timeout
        attempt = 0

        while time.monotonic() < deadline:
            attempt += 1
            available = await self.check_published(package_name, version)
            if available:
                log.info(
                    'version_available',
                    artifact=package_name,
                    version=version,
                    attempts=attempt,
                )
                return True

            remaining = deadline - time.monotonic()
            wait = min(interval, remaining)
            if wait > 0:
                log.debug(
                    'poll_waiting',
                    artifact=package_name,
                    version=version,
                    attempt=attempt,
                    wait=wait,
                )
                await asyncio.sleep(wait)

        log.warning(
            'poll_timeout',
            artifact=package_name,
            version=version,
            timeout=timeout,
            attempts=attempt,
        )
        return False

    async def project_exists(self, package_name: str) -> bool:
        """Check if the artifact exists on Maven Central (any version)."""
        group_id, artifact_id = self._parse_coordinates(package_name)
        query = f'g:"{group_id}" AND a:"{artifact_id}"'
        url = f'{self._base_url}/solrsearch/select?q={query}&rows=1&wt=json'

        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            if response.status_code != 200:
                return False
            try:
                data = response.json()
                return data.get('response', {}).get('numFound', 0) > 0
            except (ValueError, KeyError):
                return False

    async def latest_version(self, package_name: str) -> str | None:
        """Query Maven Central for the latest version of an artifact."""
        group_id, artifact_id = self._parse_coordinates(package_name)
        query = f'g:"{group_id}" AND a:"{artifact_id}"'
        url = f'{self._base_url}/solrsearch/select?q={query}&rows=1&wt=json&core=gav'

        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            if response.status_code != 200:
                return None
            try:
                data = response.json()
                docs = data.get('response', {}).get('docs', [])
                if docs:
                    return docs[0].get('v')
                return None
            except (ValueError, KeyError):
                log.warning('maven_central_parse_error', artifact=package_name)
                return None

    async def verify_checksum(
        self,
        package_name: str,
        version: str,
        local_checksums: dict[str, str],
    ) -> ChecksumResult:
        """Verify checksums against Maven Central.

        Maven Central provides SHA-1 checksums for artifacts. For now,
        this returns all files as missing since the search API doesn't
        expose per-file SHA-256 checksums directly.
        """
        log.info(
            'checksum_noop',
            artifact=package_name,
            reason='Maven Central checksum verification requires direct repo access.',
        )
        return ChecksumResult(missing=list(local_checksums.keys()))

    async def list_versions(self, package_name: str) -> list[str]:
        """Return all published versions from Maven Central (newest first)."""
        group_id, artifact_id = self._parse_coordinates(package_name)
        query = f'g:"{group_id}" AND a:"{artifact_id}"'
        url = f'{self._base_url}/solrsearch/select?q={query}&rows=200&wt=json&core=gav'

        async with http_client(pool_size=self._pool_size, timeout=self._timeout) as client:
            response = await request_with_retry(client, 'GET', url)
            if response.status_code != 200:
                return []
            try:
                data = response.json()
                docs = data.get('response', {}).get('docs', [])
                return [d['v'] for d in docs if 'v' in d]
            except (ValueError, KeyError):
                log.warning('maven_central_list_versions_error', artifact=package_name)
                return []

    async def yank_version(
        self,
        package_name: str,
        version: str,
        *,
        reason: str = '',
        dry_run: bool = False,
    ) -> bool:
        """Maven Central does not support yanking or unpublishing.

        Once an artifact is published to Maven Central, it is
        immutable and cannot be removed. The only recourse is to
        publish a new version.
        """
        log.warning(
            'maven_central_yank_unsupported',
            artifact=package_name,
            version=version,
            hint='Maven Central does not support yanking. Publish a new version instead.',
        )
        return False


__all__ = [
    'MavenCentralRegistry',
]
