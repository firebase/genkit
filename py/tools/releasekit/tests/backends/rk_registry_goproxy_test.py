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

"""Tests for releasekit.backends.registry.goproxy module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from releasekit.backends.registry import GoProxyCheck, Registry
from releasekit.logging import configure_logging

configure_logging(quiet=True)


def _mock_response(status_code: int = 200, json_data: dict | None = None, text: str = '') -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp


class TestGoProxyCheckProtocol:
    """Verify GoProxyCheck implements the Registry protocol."""

    def test_implements_protocol(self) -> None:
        """Test implements protocol."""
        registry = GoProxyCheck()
        assert isinstance(registry, Registry)

    def test_default_base_url(self) -> None:
        """Test default base url."""
        registry = GoProxyCheck()
        assert registry._base_url == 'https://proxy.golang.org'

    def test_custom_base_url(self) -> None:
        """Test custom base url."""
        registry = GoProxyCheck(base_url='http://localhost:3000/')
        assert registry._base_url == 'http://localhost:3000'

    def test_class_constants(self) -> None:
        """Test class constants."""
        assert GoProxyCheck.DEFAULT_BASE_URL == 'https://proxy.golang.org'
        assert GoProxyCheck.TEST_BASE_URL == 'http://localhost:3000'


class TestGoProxyCheckPublished:
    """Tests for GoProxyCheck.check_published()."""

    @pytest.mark.asyncio
    async def test_returns_true_on_200(self) -> None:
        """Test returns true on 200."""
        registry = GoProxyCheck()
        mock_resp = _mock_response(200)
        with (
            patch('releasekit.backends.registry.goproxy.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.goproxy.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.check_published('github.com/firebase/genkit/go/genkit', '0.5.0')
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_404(self) -> None:
        """Test returns false on 404."""
        registry = GoProxyCheck()
        mock_resp = _mock_response(404)
        with (
            patch('releasekit.backends.registry.goproxy.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.goproxy.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.check_published('github.com/nonexistent/mod', '0.0.1')
        assert result is False


class TestGoProxyPollAvailable:
    """Tests for GoProxyCheck.poll_available()."""

    @pytest.mark.asyncio
    async def test_returns_true_immediately(self) -> None:
        """Test returns true immediately."""
        registry = GoProxyCheck()
        mock_resp = _mock_response(200)
        with (
            patch('releasekit.backends.registry.goproxy.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.goproxy.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.poll_available(
                'github.com/firebase/genkit/go/genkit',
                '0.5.0',
                timeout=10.0,
                interval=1.0,
            )
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self) -> None:
        """Test returns false on timeout."""
        registry = GoProxyCheck()
        mock_resp = _mock_response(404)
        with (
            patch('releasekit.backends.registry.goproxy.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.goproxy.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.poll_available(
                'github.com/nonexistent/mod',
                '99.0.0',
                timeout=10.0,
                interval=1.0,
            )
        assert result is False

    @pytest.mark.asyncio
    async def test_clamps_interval(self) -> None:
        """Test clamps interval."""
        registry = GoProxyCheck()
        mock_resp = _mock_response(200)
        with (
            patch('releasekit.backends.registry.goproxy.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.goproxy.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.poll_available(
                'github.com/firebase/genkit/go/genkit',
                '0.5.0',
                timeout=10.0,
                interval=0.001,
            )
        assert result is True


class TestGoProxyProjectExists:
    """Tests for GoProxyCheck.project_exists()."""

    @pytest.mark.asyncio
    async def test_returns_true_when_versions_listed(self) -> None:
        """Test returns true when versions listed."""
        registry = GoProxyCheck()
        mock_resp = _mock_response(200, text='v0.4.0\nv0.5.0\n')
        with (
            patch('releasekit.backends.registry.goproxy.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.goproxy.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.project_exists('github.com/firebase/genkit/go/genkit')
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_empty_list(self) -> None:
        """Test returns false when empty list."""
        registry = GoProxyCheck()
        mock_resp = _mock_response(200, text='')
        with (
            patch('releasekit.backends.registry.goproxy.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.goproxy.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.project_exists('github.com/nonexistent/mod')
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_404(self) -> None:
        """Test returns false on 404."""
        registry = GoProxyCheck()
        mock_resp = _mock_response(404)
        with (
            patch('releasekit.backends.registry.goproxy.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.goproxy.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.project_exists('github.com/nonexistent/mod')
        assert result is False


class TestGoProxyLatestVersion:
    """Tests for GoProxyCheck.latest_version()."""

    @pytest.mark.asyncio
    async def test_returns_version_on_success(self) -> None:
        """Test returns version on success."""
        registry = GoProxyCheck()
        mock_resp = _mock_response(200, json_data={'Version': 'v0.5.0'})
        with (
            patch('releasekit.backends.registry.goproxy.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.goproxy.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.latest_version('github.com/firebase/genkit/go/genkit')
        assert result == '0.5.0'

    @pytest.mark.asyncio
    async def test_strips_v_prefix(self) -> None:
        """Test strips v prefix."""
        registry = GoProxyCheck()
        mock_resp = _mock_response(200, json_data={'Version': 'v1.2.3'})
        with (
            patch('releasekit.backends.registry.goproxy.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.goproxy.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.latest_version('example.com/mod')
        assert result == '1.2.3'

    @pytest.mark.asyncio
    async def test_returns_none_on_404(self) -> None:
        """Test returns none on 404."""
        registry = GoProxyCheck()
        mock_resp = _mock_response(404)
        with (
            patch('releasekit.backends.registry.goproxy.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.goproxy.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.latest_version('github.com/nonexistent/mod')
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_empty_version(self) -> None:
        """Test returns none on empty version."""
        registry = GoProxyCheck()
        mock_resp = _mock_response(200, json_data={'Version': ''})
        with (
            patch('releasekit.backends.registry.goproxy.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.goproxy.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.latest_version('example.com/mod')
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_parse_error(self) -> None:
        """Test returns none on parse error."""
        registry = GoProxyCheck()
        mock_resp = _mock_response(200)
        mock_resp.json.side_effect = ValueError('bad json')
        with (
            patch('releasekit.backends.registry.goproxy.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.goproxy.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.latest_version('example.com/mod')
        assert result is None


class TestGoProxyVerifyChecksum:
    """Tests for GoProxyCheck.verify_checksum()."""

    @pytest.mark.asyncio
    async def test_returns_all_missing(self) -> None:
        """Test returns all missing."""
        registry = GoProxyCheck()
        checksums = {'go.sum': 'abc123', 'go.mod': 'def456'}
        result = await registry.verify_checksum(
            'github.com/firebase/genkit/go/genkit',
            '0.5.0',
            checksums,
        )
        assert not result.ok
        assert set(result.missing) == {'go.sum', 'go.mod'}
        assert not result.matched
        assert not result.mismatched
