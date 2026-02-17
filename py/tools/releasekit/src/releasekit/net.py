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

"""HTTP utilities for releasekit.

Provides a managed :class:`httpx.AsyncClient` with:

- Connection pooling (configurable pool size).
- Automatic retry with exponential backoff for transient errors.
- Structured logging of all requests.

Used by :mod:`releasekit.backends.registry` for PyPI API calls.

Usage::

    from releasekit.net import http_client

    async with http_client() as client:
        response = await client.get('https://pypi.org/pypi/genkit/json')
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Final

import httpx

from releasekit.logging import get_logger

log = get_logger('releasekit.net')

# Default connection pool limits.
DEFAULT_POOL_SIZE: Final[int] = 10
DEFAULT_TIMEOUT: Final[float] = 30.0

# Retry configuration for transient errors.
MAX_RETRIES: Final[int] = 3
RETRY_BACKOFF_BASE: Final[float] = 1.0
RETRY_JITTER_MAX: Final[float] = 0.5

# HTTP status codes that trigger a retry.
RETRYABLE_STATUS_CODES: Final[frozenset[int]] = frozenset({429, 500, 502, 503, 504})


@asynccontextmanager
async def http_client(
    *,
    pool_size: int = DEFAULT_POOL_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
    base_url: str = '',
    headers: dict[str, str] | None = None,
) -> AsyncGenerator[httpx.AsyncClient]:
    """Create a managed async HTTP client with connection pooling.

    Args:
        pool_size: Maximum number of connections in the pool.
        timeout: Request timeout in seconds.
        base_url: Optional base URL for all requests.
        headers: Optional default headers.

    Yields:
        An :class:`httpx.AsyncClient` instance.
    """
    limits = httpx.Limits(
        max_connections=pool_size,
        max_keepalive_connections=pool_size,
    )
    async with httpx.AsyncClient(
        limits=limits,
        timeout=httpx.Timeout(timeout),
        base_url=base_url,
        headers=headers or {},
        follow_redirects=True,
    ) as client:
        yield client


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_retries: int = MAX_RETRIES,
    backoff_base: float = RETRY_BACKOFF_BASE,
    **kwargs: object,
) -> httpx.Response:
    """Make an HTTP request with automatic retry for transient errors.

    Retries on 429 (rate limit), 5xx (server errors), and connection
    errors. Uses exponential backoff between retries.

    Args:
        client: The httpx async client to use.
        method: HTTP method (GET, POST, etc.).
        url: Request URL.
        max_retries: Maximum number of retry attempts.
        backoff_base: Base delay in seconds for exponential backoff.
        **kwargs: Additional keyword arguments passed to ``client.request()``.

    Returns:
        The :class:`httpx.Response`.

    Raises:
        httpx.HTTPStatusError: If all retries are exhausted and the last
            response has a non-retryable error status.
        httpx.ConnectError: If all retries are exhausted due to connection
            failures.
    """
    last_exception: Exception | None = None
    response: httpx.Response | None = None

    for attempt in range(max_retries + 1):
        try:
            response = await client.request(method, url, **kwargs)  # type: ignore[arg-type]

            if response.status_code not in RETRYABLE_STATUS_CODES:
                return response

            # Retryable status code -- backoff with jitter and retry.
            delay = backoff_base * (2**attempt) + random.uniform(0, RETRY_JITTER_MAX)
            log.warning(
                'http_retry',
                url=url,
                status=response.status_code,
                attempt=attempt + 1,
                delay=round(delay, 3),
            )
            await asyncio.sleep(delay)

        except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
            last_exception = exc
            delay = backoff_base * (2**attempt) + random.uniform(0, RETRY_JITTER_MAX)
            log.warning(
                'http_retry_error',
                url=url,
                error=str(exc),
                attempt=attempt + 1,
                delay=round(delay, 3),
            )
            if attempt < max_retries:
                await asyncio.sleep(delay)

    # All retries exhausted.
    if last_exception:
        raise last_exception

    # This path means we got a retryable status code on the last attempt.
    if response is not None:
        response.raise_for_status()
        return response

    # Should never reach here -- max_retries >= 0 guarantees at least one attempt.
    msg = 'request_with_retry: no attempts were made'
    raise RuntimeError(msg)


__all__ = [
    'DEFAULT_POOL_SIZE',
    'DEFAULT_TIMEOUT',
    'MAX_RETRIES',
    'RETRYABLE_STATUS_CODES',
    'RETRY_BACKOFF_BASE',
    'RETRY_JITTER_MAX',
    'http_client',
    'request_with_retry',
]
