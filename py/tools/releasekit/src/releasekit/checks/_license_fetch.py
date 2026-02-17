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

"""Async fetcher for canonical LICENSE file text from source URLs.

When a package has a known SPDX license identifier but no LICENSE file
on disk, this module fetches the canonical license text from the SPDX
license list (hosted on GitHub) and optionally from the package's
source repository.

Data Flow::

    ┌──────────────┐     ┌───────────────────────┐     ┌──────────────┐
    │ SPDX ID      │────→│ SPDX license list URL │────→│ LICENSE text  │
    │ e.g. MIT     │     │ (GitHub raw content)  │     │ (canonical)  │
    └──────────────┘     └───────────────────────┘     └──────────────┘

    ┌──────────────┐     ┌───────────────────────┐     ┌──────────────┐
    │ PyPI project │────→│ project_urls →        │────→│ LICENSE text  │
    │ metadata     │     │ GitHub raw LICENSE    │     │ (repo copy)  │
    └──────────────┘     └───────────────────────┘     └──────────────┘

Sources (tried in order):

1. **SPDX license list** — ``https://raw.githubusercontent.com/spdx/
   license-list-data/main/text/{spdx_id}.txt``. Canonical text for
   every SPDX-registered license.
2. **GitHub repo** — If the package's PyPI/npm metadata includes a
   ``Homepage`` or ``Source`` URL pointing to GitHub, fetch
   ``raw.githubusercontent.com/{owner}/{repo}/{branch}/LICENSE``.

Usage::

    from releasekit.checks._license_fetch import (
        fetch_license_texts,
        fetch_spdx_license_text,
    )

    # Single SPDX ID:
    text = await fetch_spdx_license_text('MIT')

    # Batch for multiple packages:
    results = await fetch_license_texts([
        LicenseFetchRequest(package='requests', spdx_id='Apache-2.0'),
        LicenseFetchRequest(package='click', spdx_id='BSD-3-Clause'),
    ])
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Final

from releasekit.logging import get_logger
from releasekit.net import (
    DEFAULT_POOL_SIZE,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    http_client,
    request_with_retry,
)

log = get_logger('releasekit.checks.license_fetch')

# ── Constants ────────────────────────────────────────────────────────

#: Base URL for SPDX license list raw text files.
SPDX_LICENSE_TEXT_BASE: Final[str] = 'https://raw.githubusercontent.com/spdx/license-list-data/main/text'

#: Default maximum concurrent fetch requests.
DEFAULT_CONCURRENCY: Final[int] = 8

#: Pattern to extract GitHub owner/repo from a URL.
_GITHUB_REPO_RE: Final[re.Pattern[str]] = re.compile(
    r'https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)',
)


# ── Data types ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class LicenseFetchRequest:
    """A request to fetch LICENSE text for a package.

    Attributes:
        package: Package name.
        spdx_id: Known SPDX license identifier.
        source_url: Optional source repository URL (e.g. GitHub).
            If provided, the fetcher tries to get the actual LICENSE
            file from the repo before falling back to SPDX canonical.
    """

    package: str
    spdx_id: str
    source_url: str = ''


@dataclass(frozen=True)
class LicenseFetchResult:
    """Result of fetching a LICENSE file.

    Attributes:
        package: Package name.
        spdx_id: The SPDX ID that was requested.
        text: The fetched license text. Empty if fetch failed.
        source: Where the text was fetched from (e.g.
            ``"spdx-license-list"``, ``"github:owner/repo"``).
        ok: Whether the fetch succeeded.
    """

    package: str
    spdx_id: str
    text: str = ''
    source: str = ''
    ok: bool = False


# ── SPDX license text fetcher ───────────────────────────────────────


async def fetch_spdx_license_text(
    spdx_id: str,
    *,
    base_url: str = SPDX_LICENSE_TEXT_BASE,
    max_retries: int = MAX_RETRIES,
    pool_size: int = DEFAULT_POOL_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Fetch canonical license text from the SPDX license list.

    Args:
        spdx_id: SPDX license identifier (e.g. ``"MIT"``,
            ``"Apache-2.0"``).
        base_url: Base URL for the SPDX license text files.
        max_retries: Maximum retry attempts.
        pool_size: Connection pool size.
        timeout: Request timeout in seconds.

    Returns:
        The license text as a string, or empty string on failure.
    """
    url = f'{base_url}/{spdx_id}.txt'
    async with http_client(pool_size=pool_size, timeout=timeout) as client:
        try:
            resp = await request_with_retry(
                client,
                'GET',
                url,
                max_retries=max_retries,
            )
            if resp.status_code == 200:
                return resp.text
        except Exception:  # noqa: BLE001
            log.debug('spdx_fetch_failed', spdx_id=spdx_id, url=url)
    return ''


# ── GitHub LICENSE fetcher ───────────────────────────────────────────


async def _fetch_github_license(
    source_url: str,
    *,
    max_retries: int = MAX_RETRIES,
    pool_size: int = DEFAULT_POOL_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Fetch LICENSE file from a GitHub repository.

    Tries common branch names (``main``, ``master``) and common
    license file names (``LICENSE``, ``LICENSE.md``, ``LICENSE.txt``).

    Args:
        source_url: GitHub repository URL.
        max_retries: Maximum retry attempts.
        pool_size: Connection pool size.
        timeout: Request timeout in seconds.

    Returns:
        The license text, or empty string on failure.
    """
    match = _GITHUB_REPO_RE.match(source_url)
    if not match:
        return ''

    owner = match.group('owner')
    repo = match.group('repo')

    branches = ('main', 'master')
    filenames = ('LICENSE', 'LICENSE.md', 'LICENSE.txt', 'LICENCE', 'COPYING')

    async with http_client(pool_size=pool_size, timeout=timeout) as client:
        for branch in branches:
            for filename in filenames:
                url = f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filename}'
                try:
                    resp = await request_with_retry(
                        client,
                        'GET',
                        url,
                        max_retries=max_retries,
                    )
                    if resp.status_code == 200:
                        text = resp.text
                        # Sanity check: must be non-trivial text.
                        if len(text.strip()) > 50:
                            return text
                except Exception:  # noqa: BLE001, S112
                    continue
    return ''


# ── PyPI source URL resolver ────────────────────────────────────────


async def _resolve_pypi_source_url(
    package: str,
    *,
    max_retries: int = MAX_RETRIES,
    pool_size: int = DEFAULT_POOL_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    """Look up the source repository URL for a PyPI package.

    Checks ``project_urls`` in the PyPI JSON API for common keys
    like ``Source``, ``Repository``, ``Homepage``, ``GitHub``.

    Args:
        package: PyPI package name.
        max_retries: Maximum number of HTTP retries.
        pool_size: Connection pool size.
        timeout: HTTP request timeout in seconds.

    Returns:
        A GitHub URL string, or empty string if not found.
    """
    url = f'https://pypi.org/pypi/{package}/json'
    async with http_client(pool_size=pool_size, timeout=timeout) as client:
        try:
            resp = await request_with_retry(
                client,
                'GET',
                url,
                max_retries=max_retries,
            )
            if resp.status_code != 200:
                return ''
            data = resp.json()
        except Exception:  # noqa: BLE001
            return ''

    info = data.get('info', {})
    project_urls: dict[str, str] = info.get('project_urls', {}) or {}

    # Try common keys in priority order.
    for key in ('Source', 'Source Code', 'Repository', 'GitHub', 'Homepage', 'Home'):
        candidate = project_urls.get(key, '')
        if candidate and _GITHUB_REPO_RE.match(candidate):
            return candidate

    # Fallback: check the top-level home_page field.
    home_page = info.get('home_page', '')
    if home_page and _GITHUB_REPO_RE.match(home_page):
        return home_page

    return ''


# ── Batch fetcher ────────────────────────────────────────────────────


async def fetch_license_texts(
    requests: list[LicenseFetchRequest],
    *,
    concurrency: int = DEFAULT_CONCURRENCY,
    max_retries: int = MAX_RETRIES,
    try_github: bool = True,
    try_pypi_source: bool = True,
) -> dict[str, LicenseFetchResult]:
    """Fetch LICENSE texts for multiple packages concurrently.

    For each request, tries (in order):

    1. GitHub repo LICENSE (if ``source_url`` provided or resolved
       from PyPI).
    2. SPDX canonical license text.

    The GitHub source is preferred because it may contain
    copyright-holder-specific text (e.g. "Copyright 2024 Google LLC").

    Args:
        requests: List of fetch requests.
        concurrency: Maximum concurrent HTTP requests.
        max_retries: Maximum retry attempts per request.
        try_github: Whether to try fetching from GitHub repos.
        try_pypi_source: Whether to resolve source URLs from PyPI
            when ``source_url`` is not provided.

    Returns:
        Mapping from package name to :class:`LicenseFetchResult`.
    """
    sem = asyncio.Semaphore(concurrency)
    results: dict[str, LicenseFetchResult] = {}

    async def _do_one(req: LicenseFetchRequest) -> None:
        async with sem:
            # Strategy 1: Try GitHub repo LICENSE.
            if try_github:
                source_url = req.source_url
                if not source_url and try_pypi_source:
                    source_url = await _resolve_pypi_source_url(
                        req.package,
                        max_retries=max_retries,
                    )

                if source_url:
                    text = await _fetch_github_license(
                        source_url,
                        max_retries=max_retries,
                    )
                    if text:
                        match = _GITHUB_REPO_RE.match(source_url)
                        source_label = f'github:{match.group("owner")}/{match.group("repo")}' if match else 'github'
                        results[req.package] = LicenseFetchResult(
                            package=req.package,
                            spdx_id=req.spdx_id,
                            text=text,
                            source=source_label,
                            ok=True,
                        )
                        log.info(
                            'license_fetched',
                            package=req.package,
                            source=source_label,
                        )
                        return

            # Strategy 2: SPDX canonical text.
            text = await fetch_spdx_license_text(
                req.spdx_id,
                max_retries=max_retries,
            )
            if text:
                results[req.package] = LicenseFetchResult(
                    package=req.package,
                    spdx_id=req.spdx_id,
                    text=text,
                    source='spdx-license-list',
                    ok=True,
                )
                log.info(
                    'license_fetched',
                    package=req.package,
                    source='spdx-license-list',
                )
                return

            # All strategies failed.
            results[req.package] = LicenseFetchResult(
                package=req.package,
                spdx_id=req.spdx_id,
            )
            log.warning(
                'license_fetch_failed',
                package=req.package,
                spdx_id=req.spdx_id,
            )

    await asyncio.gather(*[_do_one(req) for req in requests])
    return results


__all__ = [
    'DEFAULT_CONCURRENCY',
    'LicenseFetchRequest',
    'LicenseFetchResult',
    'SPDX_LICENSE_TEXT_BASE',
    'fetch_license_texts',
    'fetch_spdx_license_text',
]
