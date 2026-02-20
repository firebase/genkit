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

"""Tests for releasekit.net module."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from releasekit.net import (
    DEFAULT_POOL_SIZE,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    RETRYABLE_STATUS_CODES,
    http_client,
    request_with_retry,
)


class TestConstants:
    """Tests for module-level constants."""

    def test_default_pool_size(self) -> None:
        """Default pool size is 10."""
        if DEFAULT_POOL_SIZE != 10:
            raise AssertionError(f'Expected 10, got {DEFAULT_POOL_SIZE}')

    def test_default_timeout(self) -> None:
        """Default timeout is 30 seconds."""
        if DEFAULT_TIMEOUT != 30.0:
            raise AssertionError(f'Expected 30.0, got {DEFAULT_TIMEOUT}')

    def test_max_retries(self) -> None:
        """Max retries default is 3."""
        if MAX_RETRIES != 3:
            raise AssertionError(f'Expected 3, got {MAX_RETRIES}')

    def test_retryable_status_codes(self) -> None:
        """Retryable codes include 429 and 5xx server errors."""
        expected = {429, 500, 502, 503, 504}
        if RETRYABLE_STATUS_CODES != expected:
            raise AssertionError(f'Expected {expected}, got {RETRYABLE_STATUS_CODES}')


class TestHttpClient:
    """Tests for http_client async context manager."""

    def test_creates_client(self) -> None:
        """Creates a properly configured httpx.AsyncClient."""

        async def _test() -> None:
            """Test."""
            async with http_client() as client:
                if not isinstance(client, httpx.AsyncClient):
                    raise AssertionError(f'Expected AsyncClient, got {type(client)}')

        asyncio.run(_test())

    def test_custom_pool_size(self) -> None:
        """Respects custom pool size without error."""

        async def _test() -> None:
            """Test."""
            async with http_client(pool_size=20) as client:
                if not isinstance(client, httpx.AsyncClient):
                    raise AssertionError(f'Expected AsyncClient, got {type(client)}')

        asyncio.run(_test())

    def test_custom_timeout(self) -> None:
        """Respects custom timeout."""

        async def _test() -> None:
            """Test."""
            async with http_client(timeout=60.0) as client:
                if client.timeout.connect != 60.0:
                    raise AssertionError(f'Expected 60.0, got {client.timeout.connect}')

        asyncio.run(_test())

    def test_custom_headers(self) -> None:
        """Respects custom headers."""

        async def _test() -> None:
            """Test."""
            async with http_client(headers={'X-Test': 'hello'}) as client:
                if client.headers.get('X-Test') != 'hello':
                    raise AssertionError('Custom header not set')

        asyncio.run(_test())

    def test_base_url(self) -> None:
        """Respects base_url."""

        async def _test() -> None:
            """Test."""
            async with http_client(base_url='https://example.com') as client:
                if str(client.base_url) != 'https://example.com':
                    raise AssertionError(f'Unexpected base_url: {client.base_url}')

        asyncio.run(_test())


class TestRequestWithRetry:
    """Tests for request_with_retry."""

    def test_success_no_retry(self) -> None:
        """Successful request returns immediately."""

        async def _test() -> None:
            """Test."""
            transport = httpx.MockTransport(
                lambda request: httpx.Response(200, json={'ok': True}),
            )
            async with httpx.AsyncClient(transport=transport) as client:
                response = await request_with_retry(
                    client,
                    'GET',
                    'https://example.com/api',
                    max_retries=0,
                )
                if response.status_code != 200:
                    raise AssertionError(f'Expected 200, got {response.status_code}')

        asyncio.run(_test())

    def test_non_retryable_error(self) -> None:
        """Non-retryable status code (404) returns immediately."""

        async def _test() -> None:
            """Test."""
            transport = httpx.MockTransport(
                lambda request: httpx.Response(404, text='not found'),
            )
            async with httpx.AsyncClient(transport=transport) as client:
                response = await request_with_retry(
                    client,
                    'GET',
                    'https://example.com/missing',
                    max_retries=2,
                )
                if response.status_code != 404:
                    raise AssertionError(f'Expected 404, got {response.status_code}')

        asyncio.run(_test())

    def test_retryable_status_exhausted(self) -> None:
        """Retryable status code exhausts retries then raises."""

        async def _test() -> None:
            """Test."""
            transport = httpx.MockTransport(
                lambda request: httpx.Response(503, text='unavailable'),
            )
            async with httpx.AsyncClient(transport=transport) as client:
                with pytest.raises(httpx.HTTPStatusError):
                    await request_with_retry(
                        client,
                        'GET',
                        'https://example.com/fail',
                        max_retries=1,
                        backoff_base=0.01,
                    )

        asyncio.run(_test())

    def test_retryable_then_success(self) -> None:
        """Retries on 503 then succeeds."""
        call_count = 0

        async def _test() -> None:
            """Test."""
            nonlocal call_count

            def handler(request: httpx.Request) -> httpx.Response:
                """Handler."""
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    return httpx.Response(503, text='try again')
                return httpx.Response(200, json={'ok': True})

            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport) as client:
                response = await request_with_retry(
                    client,
                    'GET',
                    'https://example.com/retry',
                    max_retries=3,
                    backoff_base=0.01,
                )
                if response.status_code != 200:
                    raise AssertionError(f'Expected 200, got {response.status_code}')

        asyncio.run(_test())
        if call_count != 2:
            raise AssertionError(f'Expected 2 calls, got {call_count}')

    def test_connection_error_retries(self) -> None:
        """Connection errors trigger retries."""
        call_count = 0

        async def _test() -> None:
            """Test."""
            nonlocal call_count

            def handler(request: httpx.Request) -> httpx.Response:
                """Handler."""
                nonlocal call_count
                call_count += 1
                if call_count < 2:
                    raise httpx.ConnectError('connection refused')
                return httpx.Response(200, json={'ok': True})

            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport) as client:
                response = await request_with_retry(
                    client,
                    'GET',
                    'https://example.com/retry',
                    max_retries=3,
                    backoff_base=0.01,
                )
                if response.status_code != 200:
                    raise AssertionError(f'Expected 200, got {response.status_code}')

        asyncio.run(_test())

    def test_connection_error_exhausted(self) -> None:
        """Connection errors exhaust retries then raise."""

        async def _test() -> None:
            """Test."""

            def handler(request: httpx.Request) -> httpx.Response:
                """Handler."""
                raise httpx.ConnectError('connection refused')

            transport = httpx.MockTransport(handler)
            async with httpx.AsyncClient(transport=transport) as client:
                with pytest.raises(httpx.ConnectError):
                    await request_with_retry(
                        client,
                        'GET',
                        'https://example.com/fail',
                        max_retries=1,
                        backoff_base=0.01,
                    )

        asyncio.run(_test())
