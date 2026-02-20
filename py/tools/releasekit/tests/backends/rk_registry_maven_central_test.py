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

"""Tests for releasekit.backends.registry.maven_central module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from releasekit.backends.registry import MavenCentralRegistry, Registry
from releasekit.logging import configure_logging

configure_logging(quiet=True)


def _mock_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.text = ''
    return resp


class TestMavenCentralRegistryProtocol:
    """Verify MavenCentralRegistry implements the Registry protocol."""

    def test_implements_protocol(self) -> None:
        """Test implements protocol."""
        registry = MavenCentralRegistry()
        assert isinstance(registry, Registry)

    def test_default_base_url(self) -> None:
        """Test default base url."""
        registry = MavenCentralRegistry()
        assert registry._base_url == 'https://search.maven.org'

    def test_custom_base_url(self) -> None:
        """Test custom base url."""
        registry = MavenCentralRegistry(base_url='http://localhost:8081/')
        assert registry._base_url == 'http://localhost:8081'

    def test_class_constants(self) -> None:
        """Test class constants."""
        assert MavenCentralRegistry.DEFAULT_BASE_URL == 'https://search.maven.org'
        assert MavenCentralRegistry.TEST_BASE_URL == 'http://localhost:8081'


class TestParseCoordinates:
    """Tests for MavenCentralRegistry._parse_coordinates()."""

    def test_parses_group_and_artifact(self) -> None:
        """Test parses group and artifact."""
        group, artifact = MavenCentralRegistry._parse_coordinates('com.google.genkit:genkit-core')
        assert group == 'com.google.genkit'
        assert artifact == 'genkit-core'

    def test_no_colon_treats_as_artifact(self) -> None:
        """Test no colon treats as artifact."""
        group, artifact = MavenCentralRegistry._parse_coordinates('genkit-core')
        assert group == ''
        assert artifact == 'genkit-core'

    def test_multiple_colons_splits_on_first(self) -> None:
        """Test multiple colons splits on first."""
        group, artifact = MavenCentralRegistry._parse_coordinates('com.google:genkit:core')
        assert group == 'com.google'
        assert artifact == 'genkit:core'


class TestMavenCentralCheckPublished:
    """Tests for MavenCentralRegistry.check_published()."""

    @pytest.mark.asyncio
    async def test_returns_true_when_found(self) -> None:
        """Test returns true when found."""
        registry = MavenCentralRegistry()
        mock_resp = _mock_response(200, {'response': {'numFound': 1}})
        with (
            patch('releasekit.backends.registry.maven_central.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.maven_central.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.check_published('com.google.genkit:genkit-core', '0.5.0')
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self) -> None:
        """Test returns false when not found."""
        registry = MavenCentralRegistry()
        mock_resp = _mock_response(200, {'response': {'numFound': 0}})
        with (
            patch('releasekit.backends.registry.maven_central.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.maven_central.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.check_published('com.google.genkit:genkit-core', '99.0.0')
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_http_error(self) -> None:
        """Test returns false on http error."""
        registry = MavenCentralRegistry()
        mock_resp = _mock_response(500)
        with (
            patch('releasekit.backends.registry.maven_central.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.maven_central.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.check_published('com.google.genkit:genkit-core', '0.5.0')
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_parse_error(self) -> None:
        """Test returns false on parse error."""
        registry = MavenCentralRegistry()
        mock_resp = _mock_response(200)
        mock_resp.json.side_effect = ValueError('bad json')
        with (
            patch('releasekit.backends.registry.maven_central.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.maven_central.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.check_published('com.google.genkit:genkit-core', '0.5.0')
        assert result is False


class TestMavenCentralPollAvailable:
    """Tests for MavenCentralRegistry.poll_available()."""

    @pytest.mark.asyncio
    async def test_returns_true_immediately(self) -> None:
        """Test returns true immediately."""
        registry = MavenCentralRegistry()
        mock_resp = _mock_response(200, {'response': {'numFound': 1}})
        with (
            patch('releasekit.backends.registry.maven_central.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.maven_central.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.poll_available(
                'com.google.genkit:genkit-core',
                '0.5.0',
                timeout=30.0,
                interval=5.0,
            )
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_timeout(self) -> None:
        """Test returns false on timeout."""
        registry = MavenCentralRegistry()
        mock_resp = _mock_response(200, {'response': {'numFound': 0}})
        with (
            patch('releasekit.backends.registry.maven_central.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.maven_central.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.poll_available(
                'com.google.genkit:genkit-core',
                '99.0.0',
                timeout=30.0,
                interval=5.0,
            )
        assert result is False

    @pytest.mark.asyncio
    async def test_clamps_interval_and_timeout(self) -> None:
        """Interval clamped to [5, 120], timeout to [30, 7200]."""
        registry = MavenCentralRegistry()
        mock_resp = _mock_response(200, {'response': {'numFound': 1}})
        with (
            patch('releasekit.backends.registry.maven_central.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.maven_central.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.poll_available(
                'com.google.genkit:genkit-core',
                '0.5.0',
                timeout=1.0,
                interval=0.001,
            )
        assert result is True


class TestMavenCentralProjectExists:
    """Tests for MavenCentralRegistry.project_exists()."""

    @pytest.mark.asyncio
    async def test_returns_true_when_found(self) -> None:
        """Test returns true when found."""
        registry = MavenCentralRegistry()
        mock_resp = _mock_response(200, {'response': {'numFound': 5}})
        with (
            patch('releasekit.backends.registry.maven_central.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.maven_central.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.project_exists('com.google.genkit:genkit-core')
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self) -> None:
        """Test returns false when not found."""
        registry = MavenCentralRegistry()
        mock_resp = _mock_response(200, {'response': {'numFound': 0}})
        with (
            patch('releasekit.backends.registry.maven_central.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.maven_central.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.project_exists('com.nonexistent:lib')
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_http_error(self) -> None:
        """Test returns false on http error."""
        registry = MavenCentralRegistry()
        mock_resp = _mock_response(500)
        with (
            patch('releasekit.backends.registry.maven_central.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.maven_central.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.project_exists('com.google.genkit:genkit-core')
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_parse_error(self) -> None:
        """Test returns false on parse error."""
        registry = MavenCentralRegistry()
        mock_resp = _mock_response(200)
        mock_resp.json.side_effect = ValueError('bad json')
        with (
            patch('releasekit.backends.registry.maven_central.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.maven_central.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.project_exists('com.google.genkit:genkit-core')
        assert result is False


class TestMavenCentralLatestVersion:
    """Tests for MavenCentralRegistry.latest_version()."""

    @pytest.mark.asyncio
    async def test_returns_version_on_success(self) -> None:
        """Test returns version on success."""
        registry = MavenCentralRegistry()
        mock_resp = _mock_response(200, {'response': {'docs': [{'v': '0.5.0'}]}})
        with (
            patch('releasekit.backends.registry.maven_central.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.maven_central.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.latest_version('com.google.genkit:genkit-core')
        assert result == '0.5.0'

    @pytest.mark.asyncio
    async def test_returns_none_when_no_docs(self) -> None:
        """Test returns none when no docs."""
        registry = MavenCentralRegistry()
        mock_resp = _mock_response(200, {'response': {'docs': []}})
        with (
            patch('releasekit.backends.registry.maven_central.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.maven_central.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.latest_version('com.google.genkit:genkit-core')
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_404(self) -> None:
        """Test returns none on 404."""
        registry = MavenCentralRegistry()
        mock_resp = _mock_response(404)
        with (
            patch('releasekit.backends.registry.maven_central.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.maven_central.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.latest_version('com.nonexistent:lib')
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_parse_error(self) -> None:
        """Test returns none on parse error."""
        registry = MavenCentralRegistry()
        mock_resp = _mock_response(200)
        mock_resp.json.side_effect = ValueError('bad json')
        with (
            patch('releasekit.backends.registry.maven_central.http_client') as mock_client,
            patch(
                'releasekit.backends.registry.maven_central.request_with_retry',
                new_callable=AsyncMock,
                return_value=mock_resp,
            ),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await registry.latest_version('com.google.genkit:genkit-core')
        assert result is None


class TestMavenCentralVerifyChecksum:
    """Tests for MavenCentralRegistry.verify_checksum()."""

    @pytest.mark.asyncio
    async def test_returns_all_missing(self) -> None:
        """Test returns all missing."""
        registry = MavenCentralRegistry()
        checksums = {'genkit-core-0.5.0.jar': 'abc123'}
        result = await registry.verify_checksum(
            'com.google.genkit:genkit-core',
            '0.5.0',
            checksums,
        )
        assert not result.ok
        assert result.missing == ['genkit-core-0.5.0.jar']
        assert not result.matched
        assert not result.mismatched
