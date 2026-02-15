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

"""Tests for releasekit.backends.registry.pubdev module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from releasekit.backends.registry import PubDevRegistry, Registry
from releasekit.logging import configure_logging

configure_logging(quiet=True)


def _mock_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = ''
    return resp


class TestPubDevRegistryProtocol:
    """Verify PubDevRegistry implements the Registry protocol."""

    def test_implements_protocol(self) -> None:
        """Test implements protocol."""
        registry = PubDevRegistry()
        assert isinstance(registry, Registry)

    def test_default_base_url(self) -> None:
        """Test default base url."""
        registry = PubDevRegistry()
        assert registry._base_url == 'https://pub.dev'

    def test_custom_base_url(self) -> None:
        """Test custom base url."""
        registry = PubDevRegistry(base_url='http://localhost:8080/')
        assert registry._base_url == 'http://localhost:8080'

    def test_class_constants(self) -> None:
        """Test class constants."""
        assert PubDevRegistry.DEFAULT_BASE_URL == 'https://pub.dev'
        assert PubDevRegistry.TEST_BASE_URL == 'http://localhost:8080'


class TestPubDevCheckPublished:
    """Tests for PubDevRegistry.check_published()."""

    @pytest.mark.asyncio
    async def test_returns_true_on_200(self) -> None:
        """Test returns true on 200."""
        registry = PubDevRegistry()
        mock_resp = _mock_response(200)
        with (
            patch('releasekit.backends.registry.pubdev.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.pubdev.request_with_retry', new_callable=AsyncMock, return_value=mock_resp
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.check_published('http', '1.2.0')
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_404(self) -> None:
        """Test returns false on 404."""
        registry = PubDevRegistry()
        mock_resp = _mock_response(404)
        with (
            patch('releasekit.backends.registry.pubdev.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.pubdev.request_with_retry', new_callable=AsyncMock, return_value=mock_resp
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.check_published('nonexistent', '0.0.1')
        assert result is False


class TestPubDevPollAvailable:
    """Tests for PubDevRegistry.poll_available()."""

    @pytest.mark.asyncio
    async def test_returns_true_immediately_when_available(self) -> None:
        """Test returns true immediately when available."""
        registry = PubDevRegistry()
        mock_resp = _mock_response(200)
        with (
            patch('releasekit.backends.registry.pubdev.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.pubdev.request_with_retry', new_callable=AsyncMock, return_value=mock_resp
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.poll_available('http', '1.2.0', timeout=10.0, interval=1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self) -> None:
        """Test returns false on timeout."""
        registry = PubDevRegistry()
        mock_resp = _mock_response(404)
        with (
            patch('releasekit.backends.registry.pubdev.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.pubdev.request_with_retry', new_callable=AsyncMock, return_value=mock_resp
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.poll_available('http', '99.0.0', timeout=10.0, interval=1.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_clamps_interval(self) -> None:
        """Interval should be clamped to [1, 60]."""
        registry = PubDevRegistry()
        mock_resp = _mock_response(200)
        with (
            patch('releasekit.backends.registry.pubdev.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.pubdev.request_with_retry', new_callable=AsyncMock, return_value=mock_resp
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.poll_available('http', '1.0.0', timeout=10.0, interval=0.001)
        assert result is True


class TestPubDevProjectExists:
    """Tests for PubDevRegistry.project_exists()."""

    @pytest.mark.asyncio
    async def test_returns_true_on_200(self) -> None:
        """Test returns true on 200."""
        registry = PubDevRegistry()
        mock_resp = _mock_response(200)
        with (
            patch('releasekit.backends.registry.pubdev.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.pubdev.request_with_retry', new_callable=AsyncMock, return_value=mock_resp
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.project_exists('http')
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_404(self) -> None:
        """Test returns false on 404."""
        registry = PubDevRegistry()
        mock_resp = _mock_response(404)
        with (
            patch('releasekit.backends.registry.pubdev.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.pubdev.request_with_retry', new_callable=AsyncMock, return_value=mock_resp
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.project_exists('nonexistent')
        assert result is False


class TestPubDevLatestVersion:
    """Tests for PubDevRegistry.latest_version()."""

    @pytest.mark.asyncio
    async def test_returns_version_on_success(self) -> None:
        """Test returns version on success."""
        registry = PubDevRegistry()
        mock_resp = _mock_response(200, {'latest': {'version': '1.2.0'}})
        with (
            patch('releasekit.backends.registry.pubdev.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.pubdev.request_with_retry', new_callable=AsyncMock, return_value=mock_resp
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.latest_version('http')
        assert result == '1.2.0'

    @pytest.mark.asyncio
    async def test_returns_none_on_404(self) -> None:
        """Test returns none on 404."""
        registry = PubDevRegistry()
        mock_resp = _mock_response(404)
        with (
            patch('releasekit.backends.registry.pubdev.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.pubdev.request_with_retry', new_callable=AsyncMock, return_value=mock_resp
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.latest_version('nonexistent')
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_parse_error(self) -> None:
        """Test returns none on parse error."""
        registry = PubDevRegistry()
        mock_resp = _mock_response(200)
        mock_resp.json.side_effect = ValueError('bad json')
        with (
            patch('releasekit.backends.registry.pubdev.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.pubdev.request_with_retry', new_callable=AsyncMock, return_value=mock_resp
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.latest_version('http')
        assert result is None


class TestPubDevVerifyChecksum:
    """Tests for PubDevRegistry.verify_checksum()."""

    @pytest.mark.asyncio
    async def test_returns_all_missing(self) -> None:
        """Test returns all missing."""
        registry = PubDevRegistry()
        checksums = {'file1.tar.gz': 'abc123', 'file2.tar.gz': 'def456'}
        result = await registry.verify_checksum('http', '1.0.0', checksums)
        assert not result.ok
        assert set(result.missing) == {'file1.tar.gz', 'file2.tar.gz'}
        assert not result.matched
        assert not result.mismatched
