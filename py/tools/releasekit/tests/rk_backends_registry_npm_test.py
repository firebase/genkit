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

"""Tests for the npm registry backend.

Uses httpx mock transport to avoid real network calls.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import pytest
from releasekit.backends.registry.npm import NpmRegistry, _encode_package_name

# Pure function tests


class TestEncodePackageName:
    """Tests for Encode Package Name."""

    def test_unscoped(self) -> None:
        """Test unscoped."""
        assert _encode_package_name('genkit') == 'genkit'

    def test_scoped(self) -> None:
        """Test scoped."""
        assert _encode_package_name('@genkit-ai/core') == '@genkit-ai%2Fcore'

    def test_scoped_nested(self) -> None:
        """Test scoped nested."""
        assert _encode_package_name('@scope/pkg') == '@scope%2Fpkg'


# Helpers


def _mock_transport(responses: dict[str, tuple[int, str]]) -> Any:  # noqa: ANN401
    """Mock transport."""

    def handler(request: httpx.Request) -> httpx.Response:
        """Handler."""
        url = str(request.url)
        for suffix, (status, body) in responses.items():
            if suffix in url:
                return httpx.Response(status, text=body)
        return httpx.Response(404, text='Not found')

    return handler


def _make_client_cm(transport: Any, npm: NpmRegistry) -> Any:  # noqa: ANN401
    """Make client cm."""

    @asynccontextmanager
    async def _client_cm(**kw: Any) -> AsyncGenerator[httpx.AsyncClient]:  # noqa: ANN401
        """Client cm."""
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
            yield client

    return _client_cm


@pytest.fixture()
def npm() -> NpmRegistry:
    """Npm."""
    return NpmRegistry(base_url='https://registry.test', pool_size=1, timeout=5.0)


# Async method tests


class TestCheckPublished:
    """Tests for Check Published."""

    @pytest.mark.asyncio()
    async def test_exists(self, npm: NpmRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test exists."""
        transport = _mock_transport({'/genkit/1.0.0': (200, '{}')})
        monkeypatch.setattr('releasekit.backends.registry.npm.http_client', _make_client_cm(transport, npm))
        assert await npm.check_published('genkit', '1.0.0') is True

    @pytest.mark.asyncio()
    async def test_not_exists(self, npm: NpmRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test not exists."""
        transport = _mock_transport({})
        monkeypatch.setattr('releasekit.backends.registry.npm.http_client', _make_client_cm(transport, npm))
        assert await npm.check_published('genkit', '9.9.9') is False

    @pytest.mark.asyncio()
    async def test_scoped(self, npm: NpmRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test scoped."""
        transport = _mock_transport({'%2Fcore/1.0.0': (200, '{}')})
        monkeypatch.setattr('releasekit.backends.registry.npm.http_client', _make_client_cm(transport, npm))
        assert await npm.check_published('@genkit-ai/core', '1.0.0') is True


class TestProjectExists:
    """Tests for Project Exists."""

    @pytest.mark.asyncio()
    async def test_exists(self, npm: NpmRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test exists."""
        transport = _mock_transport({'/genkit': (200, '{}')})
        monkeypatch.setattr('releasekit.backends.registry.npm.http_client', _make_client_cm(transport, npm))
        assert await npm.project_exists('genkit') is True

    @pytest.mark.asyncio()
    async def test_not_exists(self, npm: NpmRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test not exists."""
        transport = _mock_transport({})
        monkeypatch.setattr('releasekit.backends.registry.npm.http_client', _make_client_cm(transport, npm))
        assert await npm.project_exists('nonexistent') is False


class TestLatestVersion:
    """Tests for Latest Version."""

    @pytest.mark.asyncio()
    async def test_success(self, npm: NpmRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test success."""
        body = json.dumps({'dist-tags': {'latest': '2.0.0'}})
        transport = _mock_transport({'/genkit': (200, body)})
        monkeypatch.setattr('releasekit.backends.registry.npm.http_client', _make_client_cm(transport, npm))
        assert await npm.latest_version('genkit') == '2.0.0'

    @pytest.mark.asyncio()
    async def test_not_found(self, npm: NpmRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test not found."""
        transport = _mock_transport({})
        monkeypatch.setattr('releasekit.backends.registry.npm.http_client', _make_client_cm(transport, npm))
        assert await npm.latest_version('nonexistent') is None

    @pytest.mark.asyncio()
    async def test_bad_json(self, npm: NpmRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test bad json."""
        transport = _mock_transport({'/genkit': (200, 'not json')})
        monkeypatch.setattr('releasekit.backends.registry.npm.http_client', _make_client_cm(transport, npm))
        assert await npm.latest_version('genkit') is None


class TestVerifyChecksum:
    """Tests for Verify Checksum."""

    @pytest.mark.asyncio()
    async def test_match(self, npm: NpmRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test match."""
        body = json.dumps({'dist': {'shasum': 'abc123'}})
        transport = _mock_transport({'/genkit/1.0.0': (200, body)})
        monkeypatch.setattr('releasekit.backends.registry.npm.http_client', _make_client_cm(transport, npm))
        result = await npm.verify_checksum('genkit', '1.0.0', {'genkit-1.0.0.tgz': 'abc123'})
        assert result.ok is True
        assert result.matched == ['genkit-1.0.0.tgz']

    @pytest.mark.asyncio()
    async def test_mismatch(self, npm: NpmRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test mismatch."""
        body = json.dumps({'dist': {'shasum': 'abc123'}})
        transport = _mock_transport({'/genkit/1.0.0': (200, body)})
        monkeypatch.setattr('releasekit.backends.registry.npm.http_client', _make_client_cm(transport, npm))
        result = await npm.verify_checksum('genkit', '1.0.0', {'genkit-1.0.0.tgz': 'wrong'})
        assert result.ok is False
        assert 'genkit-1.0.0.tgz' in result.mismatched

    @pytest.mark.asyncio()
    async def test_missing_file(self, npm: NpmRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test missing file."""
        body = json.dumps({'dist': {'shasum': 'abc123'}})
        transport = _mock_transport({'/genkit/1.0.0': (200, body)})
        monkeypatch.setattr('releasekit.backends.registry.npm.http_client', _make_client_cm(transport, npm))
        result = await npm.verify_checksum('genkit', '1.0.0', {'other.tgz': 'abc'})
        assert result.ok is False
        assert 'other.tgz' in result.missing

    @pytest.mark.asyncio()
    async def test_api_error(self, npm: NpmRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test api error."""
        transport = _mock_transport({})
        monkeypatch.setattr('releasekit.backends.registry.npm.http_client', _make_client_cm(transport, npm))
        result = await npm.verify_checksum('genkit', '1.0.0', {'f.tgz': 'abc'})
        assert result.ok is False

    @pytest.mark.asyncio()
    async def test_bad_json(self, npm: NpmRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test bad json."""
        transport = _mock_transport({'/genkit/1.0.0': (200, 'not json')})
        monkeypatch.setattr('releasekit.backends.registry.npm.http_client', _make_client_cm(transport, npm))
        result = await npm.verify_checksum('genkit', '1.0.0', {'f.tgz': 'abc'})
        assert result.ok is False


class TestPollAvailable:
    """Tests for Poll Available."""

    @pytest.mark.asyncio()
    async def test_immediately_available(self, npm: NpmRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test immediately available."""
        transport = _mock_transport({'/genkit/1.0.0': (200, '{}')})
        monkeypatch.setattr('releasekit.backends.registry.npm.http_client', _make_client_cm(transport, npm))
        result = await npm.poll_available('genkit', '1.0.0', timeout=10.0, interval=1.0)
        assert result is True

    @pytest.mark.asyncio()
    async def test_timeout(self, npm: NpmRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test timeout."""
        transport = _mock_transport({})
        monkeypatch.setattr('releasekit.backends.registry.npm.http_client', _make_client_cm(transport, npm))
        result = await npm.poll_available('genkit', '9.9.9', timeout=10.0, interval=1.0)
        assert result is False
