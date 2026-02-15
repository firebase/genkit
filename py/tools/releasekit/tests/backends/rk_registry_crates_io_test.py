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

"""Tests for releasekit.backends.registry.crates_io module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from releasekit.backends.registry import CratesIoRegistry, Registry
from releasekit.logging import configure_logging

configure_logging(quiet=True)


def _mock_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = ''
    return resp


class TestCratesIoRegistryProtocol:
    """Verify CratesIoRegistry implements the Registry protocol."""

    def test_implements_protocol(self) -> None:
        """Test implements protocol."""
        registry = CratesIoRegistry()
        assert isinstance(registry, Registry)

    def test_default_base_url(self) -> None:
        """Test default base url."""
        registry = CratesIoRegistry()
        assert registry._base_url == 'https://crates.io'

    def test_custom_base_url(self) -> None:
        """Test custom base url."""
        registry = CratesIoRegistry(base_url='http://localhost:3000/')
        assert registry._base_url == 'http://localhost:3000'

    def test_class_constants(self) -> None:
        """Test class constants."""
        assert CratesIoRegistry.DEFAULT_BASE_URL == 'https://crates.io'
        assert CratesIoRegistry.TEST_BASE_URL == 'http://localhost:3000'


class TestCratesIoCheckPublished:
    """Tests for CratesIoRegistry.check_published()."""

    @pytest.mark.asyncio
    async def test_returns_true_on_200(self) -> None:
        """Test returns true on 200."""
        registry = CratesIoRegistry()
        mock_resp = _mock_response(200)
        with (
            patch('releasekit.backends.registry.crates_io.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.crates_io.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.check_published('serde', '1.0.200')
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_404(self) -> None:
        """Test returns false on 404."""
        registry = CratesIoRegistry()
        mock_resp = _mock_response(404)
        with (
            patch('releasekit.backends.registry.crates_io.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.crates_io.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.check_published('nonexistent-crate', '0.0.1')
        assert result is False


class TestCratesIoPollAvailable:
    """Tests for CratesIoRegistry.poll_available()."""

    @pytest.mark.asyncio
    async def test_returns_true_immediately(self) -> None:
        """Test returns true immediately."""
        registry = CratesIoRegistry()
        mock_resp = _mock_response(200)
        with (
            patch('releasekit.backends.registry.crates_io.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.crates_io.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.poll_available('serde', '1.0.200', timeout=10.0, interval=1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self) -> None:
        """Test returns false on timeout."""
        registry = CratesIoRegistry()
        mock_resp = _mock_response(404)
        with (
            patch('releasekit.backends.registry.crates_io.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.crates_io.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.poll_available('nonexistent', '99.0.0', timeout=10.0, interval=1.0)
        assert result is False

    @pytest.mark.asyncio
    async def test_clamps_interval(self) -> None:
        """Test clamps interval."""
        registry = CratesIoRegistry()
        mock_resp = _mock_response(200)
        with (
            patch('releasekit.backends.registry.crates_io.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.crates_io.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.poll_available('serde', '1.0.200', timeout=10.0, interval=0.001)
        assert result is True


class TestCratesIoProjectExists:
    """Tests for CratesIoRegistry.project_exists()."""

    @pytest.mark.asyncio
    async def test_returns_true_on_200(self) -> None:
        """Test returns true on 200."""
        registry = CratesIoRegistry()
        mock_resp = _mock_response(200)
        with (
            patch('releasekit.backends.registry.crates_io.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.crates_io.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.project_exists('serde')
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_404(self) -> None:
        """Test returns false on 404."""
        registry = CratesIoRegistry()
        mock_resp = _mock_response(404)
        with (
            patch('releasekit.backends.registry.crates_io.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.crates_io.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.project_exists('nonexistent-crate')
        assert result is False


class TestCratesIoLatestVersion:
    """Tests for CratesIoRegistry.latest_version()."""

    @pytest.mark.asyncio
    async def test_returns_max_stable_version(self) -> None:
        """Test returns max stable version."""
        registry = CratesIoRegistry()
        mock_resp = _mock_response(
            200,
            {
                'crate': {'max_stable_version': '1.0.200', 'newest_version': '1.1.0-beta.1'},
            },
        )
        with (
            patch('releasekit.backends.registry.crates_io.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.crates_io.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.latest_version('serde')
        assert result == '1.0.200'

    @pytest.mark.asyncio
    async def test_falls_back_to_newest_version(self) -> None:
        """Test falls back to newest version."""
        registry = CratesIoRegistry()
        mock_resp = _mock_response(
            200,
            {
                'crate': {'max_stable_version': None, 'newest_version': '0.1.0-alpha.1'},
            },
        )
        with (
            patch('releasekit.backends.registry.crates_io.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.crates_io.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.latest_version('new-crate')
        assert result == '0.1.0-alpha.1'

    @pytest.mark.asyncio
    async def test_returns_none_when_both_missing(self) -> None:
        """Test returns none when both missing."""
        registry = CratesIoRegistry()
        mock_resp = _mock_response(200, {'crate': {}})
        with (
            patch('releasekit.backends.registry.crates_io.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.crates_io.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.latest_version('empty-crate')
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_404(self) -> None:
        """Test returns none on 404."""
        registry = CratesIoRegistry()
        mock_resp = _mock_response(404)
        with (
            patch('releasekit.backends.registry.crates_io.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.crates_io.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.latest_version('nonexistent')
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_parse_error(self) -> None:
        """Test returns none on parse error."""
        registry = CratesIoRegistry()
        mock_resp = _mock_response(200)
        mock_resp.json.side_effect = ValueError('bad json')
        with (
            patch('releasekit.backends.registry.crates_io.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.crates_io.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.latest_version('serde')
        assert result is None


class TestCratesIoVerifyChecksum:
    """Tests for CratesIoRegistry.verify_checksum()."""

    @pytest.mark.asyncio
    async def test_returns_all_missing(self) -> None:
        """Test returns all missing."""
        registry = CratesIoRegistry()
        checksums = {'serde-1.0.200.crate': 'abc123'}
        result = await registry.verify_checksum('serde', '1.0.200', checksums)
        assert not result.ok
        assert result.missing == ['serde-1.0.200.crate']
        assert not result.matched
        assert not result.mismatched
