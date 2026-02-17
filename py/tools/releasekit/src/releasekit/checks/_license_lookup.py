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

"""Async license lookup from package registries with disk-backed caching.

When a dependency's license cannot be determined from its local manifest
(e.g. ``package.json``, ``Cargo.toml``, ``pyproject.toml``), this module
queries the upstream package registry to retrieve the license.

Features:

- **Per-ecosystem lookup** — npm, PyPI, crates.io, Maven Central, pub.dev,
  Go proxy each have a dedicated fetcher that knows how to extract the
  license field from the registry's JSON API response.
- **Disk-backed cache** — results are persisted to a JSON file so
  subsequent runs skip the network entirely for already-resolved packages.
  Cache entries include a TTL (default 7 days).
- **Batch async** — all lookups for a workspace run concurrently via
  :func:`asyncio.gather` with a configurable concurrency semaphore.
- **Retry with jitter** — uses :func:`releasekit.net.request_with_retry`
  which has exponential backoff + jitter built in.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable, Coroutine
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final
from xml.etree import ElementTree  # noqa: S405

from releasekit._types import DetectedLicense
from releasekit.logging import get_logger
from releasekit.net import (
    DEFAULT_POOL_SIZE,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    http_client,
    request_with_retry,
)

log = get_logger('releasekit.checks.license_lookup')

# ── Constants ────────────────────────────────────────────────────────

#: Default cache TTL in seconds (7 days).
CACHE_TTL: Final[int] = 7 * 24 * 3600

#: Default maximum concurrent registry requests.
DEFAULT_CONCURRENCY: Final[int] = 8

# ── Cache entry ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class CacheEntry:
    """A single cached license lookup result.

    Attributes:
        license_id: The SPDX license expression or raw string.
            Empty string if the registry had no license info.
        source: Where the license was found (e.g. ``"npm registry"``).
        timestamp: Unix timestamp when the entry was created.
    """

    license_id: str
    source: str
    timestamp: float


class LicenseLookupCache:
    """Disk-backed JSON cache for registry license lookups.

    The cache file is a JSON object mapping
    ``"{ecosystem}:{package}:{version}"`` → :class:`CacheEntry`.

    Args:
        path: Path to the cache JSON file.
        ttl: Time-to-live in seconds for cache entries.
    """

    def __init__(self, path: Path, *, ttl: int = CACHE_TTL) -> None:
        self._path = path
        self._ttl = ttl
        self._data: dict[str, dict[str, object]] = {}
        self._load()

    def _load(self) -> None:
        if self._path.is_file():
            try:
                self._data = json.loads(self._path.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, OSError):
                log.warning('cache_load_failed', path=str(self._path))
                self._data = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, indent=2, sort_keys=True),
            encoding='utf-8',
        )

    @staticmethod
    def _key(ecosystem: str, package: str, version: str) -> str:
        return f'{ecosystem}:{package}:{version}'

    def get(
        self,
        ecosystem: str,
        package: str,
        version: str,
    ) -> CacheEntry | None:
        """Return a cached entry if it exists and is not expired."""
        key = self._key(ecosystem, package, version)
        raw = self._data.get(key)
        if raw is None:
            return None
        entry = CacheEntry(
            license_id=str(raw.get('license_id', '')),
            source=str(raw.get('source', '')),
            timestamp=float(str(raw.get('timestamp', 0))),
        )
        if time.time() - entry.timestamp > self._ttl:
            return None
        return entry

    def put(
        self,
        ecosystem: str,
        package: str,
        version: str,
        entry: CacheEntry,
    ) -> None:
        """Store a cache entry and persist to disk."""
        key = self._key(ecosystem, package, version)
        self._data[key] = asdict(entry)
        self._save()


# ── Per-ecosystem registry fetchers ─────────────────────────────────


async def _lookup_npm(
    package: str,
    version: str,
    *,
    base_url: str = 'https://registry.npmjs.org',
    max_retries: int = MAX_RETRIES,
    pool_size: int = DEFAULT_POOL_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
) -> DetectedLicense:
    """Fetch license from the npm registry for a specific version."""
    import urllib.parse

    encoded = urllib.parse.quote(package, safe='@') if package.startswith('@') else package
    url = f'{base_url}/{encoded}/{version}'
    async with http_client(pool_size=pool_size, timeout=timeout) as client:
        resp = await request_with_retry(client, 'GET', url, max_retries=max_retries)
        if resp.status_code != 200:
            return DetectedLicense(value='', source='', package_name=package)
        try:
            data = resp.json()
        except ValueError:
            return DetectedLicense(value='', source='', package_name=package)

    lic = data.get('license', '')
    if isinstance(lic, dict):
        lic = lic.get('type', '')
    if isinstance(lic, list) and lic:
        lic = lic[0].get('type', '') if isinstance(lic[0], dict) else str(lic[0])
    return DetectedLicense(
        value=str(lic),
        source='npm registry',
        package_name=package,
    )


_IGNORED_VALUES: frozenset[str] = frozenset({'unknown', 'none', '', 'other'})


def extract_license_from_pypi_json(
    info: dict[str, object],
    package: str,
) -> DetectedLicense:
    """Extract license from a PyPI JSON API ``info`` dict.

    This is the shared extraction logic used by both the async
    :func:`_lookup_pypi` fetcher and the synchronous
    :func:`~releasekit.checks._universal._resolve_external_licenses`
    helper.

    The extraction tries three strategies in order:

    1. ``license_expression`` (PEP 639) — always a short SPDX expression.
    2. ``license`` (legacy) — only if ≤120 chars (avoids full LICENSE text).
    3. ``classifiers`` — first ``License :: OSI Approved ::`` entry, then
       any ``License ::`` entry.

    Args:
        info: The ``info`` dict from the PyPI JSON response.
        package: Package name (for the returned :class:`DetectedLicense`).

    Returns:
        A :class:`DetectedLicense` with the extracted license, or an
        empty-value result if no license could be determined.
    """
    # PEP 639 license_expression (preferred, always a short SPDX
    # expression when present).
    lic_expr = info.get('license_expression') or ''
    if isinstance(lic_expr, str) and lic_expr.strip().lower() not in _IGNORED_VALUES:
        return DetectedLicense(
            value=lic_expr.strip(),
            source='PyPI registry (license_expression)',
            package_name=package,
        )

    # Legacy license field — but only if it looks like a short
    # identifier, not the full license text.  Some packages (e.g.
    # json5, jsonata-python) stuff the entire LICENSE file into
    # this field.  A real SPDX expression is never >120 chars.
    max_license_len = 120
    lic = info.get('license') or ''
    if isinstance(lic, str) and len(lic.strip()) <= max_license_len and lic.strip().lower() not in _IGNORED_VALUES:
        return DetectedLicense(
            value=lic.strip(),
            source='PyPI registry',
            package_name=package,
        )

    # Fallback: first License :: OSI Approved :: classifier.
    classifiers = info.get('classifiers', [])
    if isinstance(classifiers, list):
        for c in classifiers:
            if isinstance(c, str) and c.startswith('License :: OSI Approved ::'):
                return DetectedLicense(
                    value=c.rsplit(' :: ', 1)[-1],
                    source='PyPI registry (classifier)',
                    package_name=package,
                )
        # Broader fallback: any License:: classifier.
        for c in classifiers:
            if isinstance(c, str) and c.startswith('License ::'):
                return DetectedLicense(
                    value=c.rsplit(' :: ', 1)[-1],
                    source='PyPI registry (classifier)',
                    package_name=package,
                )
    return DetectedLicense(value='', source='', package_name=package)


async def _lookup_pypi(
    package: str,
    version: str,
    *,
    base_url: str = 'https://pypi.org',
    max_retries: int = MAX_RETRIES,
    pool_size: int = DEFAULT_POOL_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
) -> DetectedLicense:
    """Fetch license from PyPI for a specific version."""
    url = f'{base_url}/pypi/{package}/{version}/json'
    async with http_client(pool_size=pool_size, timeout=timeout) as client:
        resp = await request_with_retry(client, 'GET', url, max_retries=max_retries)
        if resp.status_code != 200:
            return DetectedLicense(value='', source='', package_name=package)
        try:
            data = resp.json()
        except ValueError:
            return DetectedLicense(value='', source='', package_name=package)

    return extract_license_from_pypi_json(data.get('info', {}), package)


async def _lookup_crates_io(
    package: str,
    version: str,
    *,
    base_url: str = 'https://crates.io',
    max_retries: int = MAX_RETRIES,
    pool_size: int = DEFAULT_POOL_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
) -> DetectedLicense:
    """Fetch license from crates.io for a specific version."""
    url = f'{base_url}/api/v1/crates/{package}/{version}'
    async with http_client(pool_size=pool_size, timeout=timeout) as client:
        resp = await request_with_retry(client, 'GET', url, max_retries=max_retries)
        if resp.status_code != 200:
            return DetectedLicense(value='', source='', package_name=package)
        try:
            data = resp.json()
        except ValueError:
            return DetectedLicense(value='', source='', package_name=package)

    lic = data.get('version', {}).get('license', '')
    return DetectedLicense(
        value=str(lic),
        source='crates.io registry',
        package_name=package,
    )


async def _lookup_maven_central(
    package: str,
    version: str,
    *,
    base_url: str = 'https://repo1.maven.org/maven2',
    max_retries: int = MAX_RETRIES,
    pool_size: int = DEFAULT_POOL_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
) -> DetectedLicense:
    """Fetch license from Maven Central POM for a specific version."""
    parts = package.split(':', 1)
    if len(parts) != 2:
        return DetectedLicense(value='', source='', package_name=package)
    group_id, artifact_id = parts
    group_path = group_id.replace('.', '/')
    url = f'{base_url}/{group_path}/{artifact_id}/{version}/{artifact_id}-{version}.pom'
    async with http_client(pool_size=pool_size, timeout=timeout) as client:
        resp = await request_with_retry(client, 'GET', url, max_retries=max_retries)
        if resp.status_code != 200:
            return DetectedLicense(value='', source='', package_name=package)
        pom_text = resp.text

    try:
        root = ElementTree.fromstring(pom_text)  # noqa: S314
    except ElementTree.ParseError:
        return DetectedLicense(value='', source='', package_name=package)

    # Handle Maven namespace.
    ns = ''
    if root.tag.startswith('{'):
        ns = root.tag.split('}')[0] + '}'

    licenses_el = root.find(f'{ns}licenses')
    if licenses_el is not None:
        first = licenses_el.find(f'{ns}license')
        if first is not None:
            name_el = first.find(f'{ns}name')
            if name_el is not None and name_el.text:
                return DetectedLicense(
                    value=name_el.text.strip(),
                    source='Maven Central POM',
                    package_name=package,
                )
    return DetectedLicense(value='', source='', package_name=package)


async def _lookup_pubdev(
    package: str,
    version: str,
    *,
    base_url: str = 'https://pub.dev',
    max_retries: int = MAX_RETRIES,
    pool_size: int = DEFAULT_POOL_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
) -> DetectedLicense:
    """Fetch license from pub.dev for a specific version.

    pub.dev doesn't expose license in its JSON API directly, but the
    package page has a license field. We use the API score endpoint.
    """
    url = f'{base_url}/api/packages/{package}/score'
    async with http_client(pool_size=pool_size, timeout=timeout) as client:
        resp = await request_with_retry(client, 'GET', url, max_retries=max_retries)
        if resp.status_code != 200:
            return DetectedLicense(value='', source='', package_name=package)
        try:
            data = resp.json()
        except ValueError:
            return DetectedLicense(value='', source='', package_name=package)

    # The score API includes tags like "license:mit".
    tags = data.get('tags', [])
    for tag in tags:
        if isinstance(tag, str) and tag.startswith('license:'):
            lic = tag.split(':', 1)[1]
            return DetectedLicense(
                value=lic,
                source='pub.dev registry',
                package_name=package,
            )
    return DetectedLicense(value='', source='', package_name=package)


async def _lookup_goproxy(
    package: str,
    version: str,
    *,
    base_url: str = 'https://pkg.go.dev',
    max_retries: int = MAX_RETRIES,
    pool_size: int = DEFAULT_POOL_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
) -> DetectedLicense:
    """Fetch license from pkg.go.dev for a Go module.

    The Go module proxy doesn't serve license info, but pkg.go.dev
    has a JSON API that includes license metadata.
    """
    url = f'{base_url}/{package}@v{version}?tab=licenses&m=json'
    async with http_client(pool_size=pool_size, timeout=timeout) as client:
        resp = await request_with_retry(client, 'GET', url, max_retries=max_retries)
        if resp.status_code != 200:
            return DetectedLicense(value='', source='', package_name=package)
        try:
            data = resp.json()
        except ValueError:
            return DetectedLicense(value='', source='', package_name=package)

    # pkg.go.dev returns license types in the response.
    licenses = data.get('Licenses', [])
    if licenses:
        types = [lic.get('Type', '') for lic in licenses if lic.get('Type')]
        if types:
            return DetectedLicense(
                value=' AND '.join(types),
                source='pkg.go.dev',
                package_name=package,
            )
    return DetectedLicense(value='', source='', package_name=package)


# ── Ecosystem → fetcher dispatch ─────────────────────────────────────

# Type alias for async fetcher functions.
_Fetcher = Callable[..., Coroutine[Any, Any, DetectedLicense]]

_ECOSYSTEM_FETCHERS: dict[str, _Fetcher] = {
    'pnpm': _lookup_npm,
    'npm': _lookup_npm,
    'node': _lookup_npm,
    'python': _lookup_pypi,
    'uv': _lookup_pypi,
    'pip': _lookup_pypi,
    'cargo': _lookup_crates_io,
    'rust': _lookup_crates_io,
    'maven': _lookup_maven_central,
    'java': _lookup_maven_central,
    'gradle': _lookup_maven_central,
    'dart': _lookup_pubdev,
    'flutter': _lookup_pubdev,
    'go': _lookup_goproxy,
}


# ── Batch lookup ─────────────────────────────────────────────────────


@dataclass
class LookupRequest:
    """A single license lookup request.

    Attributes:
        package: Package name (e.g. ``express``, ``serde``).
        version: Version string (e.g. ``4.18.2``).
        ecosystem: Ecosystem key (e.g. ``pnpm``, ``cargo``).
    """

    package: str
    version: str
    ecosystem: str


async def lookup_licenses(
    requests: list[LookupRequest],
    *,
    cache: LicenseLookupCache | None = None,
    concurrency: int = DEFAULT_CONCURRENCY,
    max_retries: int = MAX_RETRIES,
) -> dict[str, DetectedLicense]:
    """Look up licenses for multiple packages concurrently.

    Args:
        requests: List of lookup requests.
        cache: Optional disk-backed cache. If provided, cached results
            are returned without hitting the network.
        concurrency: Maximum number of concurrent registry requests.
        max_retries: Maximum retry attempts per request (uses
            exponential backoff + jitter from :mod:`releasekit.net`).

    Returns:
        Mapping from ``"{package}@{version}"`` to :class:`DetectedLicense`.
    """
    sem = asyncio.Semaphore(concurrency)
    results: dict[str, DetectedLicense] = {}

    async def _do_one(req: LookupRequest) -> None:
        key = f'{req.package}@{req.version}'

        # Check cache first.
        if cache is not None:
            cached = cache.get(req.ecosystem, req.package, req.version)
            if cached is not None:
                results[key] = DetectedLicense(
                    value=cached.license_id,
                    source=cached.source,
                    package_name=req.package,
                )
                log.debug('cache_hit', package=req.package, version=req.version)
                return

        fetcher = _ECOSYSTEM_FETCHERS.get(req.ecosystem)
        if fetcher is None:
            log.debug('no_fetcher', ecosystem=req.ecosystem, package=req.package)
            results[key] = DetectedLicense(value='', source='', package_name=req.package)
            return

        async with sem:
            try:
                result = await fetcher(
                    req.package,
                    req.version,
                    max_retries=max_retries,
                )
            except Exception:  # noqa: BLE001
                log.warning(
                    'lookup_failed',
                    package=req.package,
                    version=req.version,
                    ecosystem=req.ecosystem,
                )
                result = DetectedLicense(value='', source='', package_name=req.package)

        results[key] = result

        # Populate cache.
        if cache is not None:
            cache.put(
                req.ecosystem,
                req.package,
                req.version,
                CacheEntry(
                    license_id=result.value,
                    source=result.source,
                    timestamp=time.time(),
                ),
            )

    await asyncio.gather(*[_do_one(req) for req in requests])
    return results


__all__ = [
    'CACHE_TTL',
    'CacheEntry',
    'DEFAULT_CONCURRENCY',
    'LicenseLookupCache',
    'LookupRequest',
    'extract_license_from_pypi_json',
    'lookup_licenses',
]
