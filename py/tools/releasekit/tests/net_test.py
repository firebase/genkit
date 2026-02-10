# Copyright 2025 Google LLC
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

import pytest
from releasekit.logging import configure_logging
from releasekit.net import http_client, request_with_retry

configure_logging(quiet=True)


class TestHttpClient:
    """Tests for http_client() context manager."""

    @pytest.mark.asyncio
    async def test_basic_get(self) -> None:
        """Should be able to make a basic GET request."""
        async with http_client() as client:
            response = await client.get('https://pypi.org/pypi/pip/json')
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_custom_timeout(self) -> None:
        """Should accept a custom timeout."""
        async with http_client(timeout=10.0) as client:
            response = await client.get('https://pypi.org/pypi/pip/json')
            assert response.status_code == 200


class TestRequestWithRetry:
    """Tests for request_with_retry()."""

    @pytest.mark.asyncio
    async def test_successful_request(self) -> None:
        """Should return a response for a successful request."""
        async with http_client() as client:
            response = await request_with_retry(client, 'GET', 'https://pypi.org/pypi/pip/json')
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_404_not_retried(self) -> None:
        """404 should not be retried (not in RETRYABLE_STATUS_CODES)."""
        async with http_client() as client:
            response = await request_with_retry(
                client,
                'GET',
                'https://pypi.org/pypi/nonexistent-package-xyz123/json',
                max_retries=1,
            )
            assert response.status_code == 404
