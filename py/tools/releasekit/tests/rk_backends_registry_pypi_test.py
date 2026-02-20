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

"""Tests for the PyPI registry backend.

Uses httpx mock transport to avoid real network calls.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import pytest
from releasekit.backends.registry.pypi import PyPIBackend


def _mock_transport(responses: dict[str, tuple[int, str]]) -> Any:  # noqa: ANN401
    """Create a mock transport that returns canned responses by URL suffix."""

    def handler(request: httpx.Request) -> httpx.Response:
        """Handler."""
        url = str(request.url)
        for suffix, (status, body) in responses.items():
            if url.endswith(suffix):
                return httpx.Response(status, text=body)
        return httpx.Response(404, text='Not found')

    return handler


@pytest.fixture()
def pypi() -> PyPIBackend:
    """Pypi."""
    return PyPIBackend(base_url='https://pypi.test', pool_size=1, timeout=5.0)


class TestCheckPublished:
    """Tests for Check Published."""

    @pytest.mark.asyncio()
    async def test_exists(self, pypi: PyPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test exists."""
        transport = _mock_transport({'/pypi/genkit/1.0.0/json': (200, '{}')})
        monkeypatch.setattr('releasekit.backends.registry.pypi.http_client', _make_client_cm(transport, pypi))
        assert await pypi.check_published('genkit', '1.0.0') is True

    @pytest.mark.asyncio()
    async def test_not_exists(self, pypi: PyPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test not exists."""
        transport = _mock_transport({})
        monkeypatch.setattr('releasekit.backends.registry.pypi.http_client', _make_client_cm(transport, pypi))
        assert await pypi.check_published('genkit', '9.9.9') is False


class TestProjectExists:
    """Tests for Project Exists."""

    @pytest.mark.asyncio()
    async def test_exists(self, pypi: PyPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test exists."""
        transport = _mock_transport({'/pypi/genkit/json': (200, '{}')})
        monkeypatch.setattr('releasekit.backends.registry.pypi.http_client', _make_client_cm(transport, pypi))
        assert await pypi.project_exists('genkit') is True

    @pytest.mark.asyncio()
    async def test_not_exists(self, pypi: PyPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test not exists."""
        transport = _mock_transport({})
        monkeypatch.setattr('releasekit.backends.registry.pypi.http_client', _make_client_cm(transport, pypi))
        assert await pypi.project_exists('nonexistent') is False


class TestLatestVersion:
    """Tests for Latest Version."""

    @pytest.mark.asyncio()
    async def test_success(self, pypi: PyPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test success."""
        body = json.dumps({'info': {'version': '1.2.3'}})
        transport = _mock_transport({'/pypi/genkit/json': (200, body)})
        monkeypatch.setattr('releasekit.backends.registry.pypi.http_client', _make_client_cm(transport, pypi))
        assert await pypi.latest_version('genkit') == '1.2.3'

    @pytest.mark.asyncio()
    async def test_not_found(self, pypi: PyPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test not found."""
        transport = _mock_transport({})
        monkeypatch.setattr('releasekit.backends.registry.pypi.http_client', _make_client_cm(transport, pypi))
        assert await pypi.latest_version('nonexistent') is None

    @pytest.mark.asyncio()
    async def test_bad_json(self, pypi: PyPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test bad json."""
        transport = _mock_transport({'/pypi/genkit/json': (200, 'not json')})
        monkeypatch.setattr('releasekit.backends.registry.pypi.http_client', _make_client_cm(transport, pypi))
        assert await pypi.latest_version('genkit') is None


class TestVerifyChecksum:
    """Tests for Verify Checksum."""

    @pytest.mark.asyncio()
    async def test_match(self, pypi: PyPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test match."""
        body = json.dumps({
            'urls': [
                {'filename': 'genkit-1.0.0.tar.gz', 'digests': {'sha256': 'abc123'}},
            ],
        })
        transport = _mock_transport({'/pypi/genkit/1.0.0/json': (200, body)})
        monkeypatch.setattr('releasekit.backends.registry.pypi.http_client', _make_client_cm(transport, pypi))
        result = await pypi.verify_checksum('genkit', '1.0.0', {'genkit-1.0.0.tar.gz': 'abc123'})
        assert result.ok is True
        assert result.matched == ['genkit-1.0.0.tar.gz']

    @pytest.mark.asyncio()
    async def test_mismatch(self, pypi: PyPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test mismatch."""
        body = json.dumps({
            'urls': [
                {'filename': 'genkit-1.0.0.tar.gz', 'digests': {'sha256': 'abc123'}},
            ],
        })
        transport = _mock_transport({'/pypi/genkit/1.0.0/json': (200, body)})
        monkeypatch.setattr('releasekit.backends.registry.pypi.http_client', _make_client_cm(transport, pypi))
        result = await pypi.verify_checksum('genkit', '1.0.0', {'genkit-1.0.0.tar.gz': 'wrong'})
        assert result.ok is False
        assert 'genkit-1.0.0.tar.gz' in result.mismatched

    @pytest.mark.asyncio()
    async def test_missing_file(self, pypi: PyPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test missing file."""
        body = json.dumps({'urls': []})
        transport = _mock_transport({'/pypi/genkit/1.0.0/json': (200, body)})
        monkeypatch.setattr('releasekit.backends.registry.pypi.http_client', _make_client_cm(transport, pypi))
        result = await pypi.verify_checksum('genkit', '1.0.0', {'genkit-1.0.0.tar.gz': 'abc'})
        assert result.ok is False
        assert 'genkit-1.0.0.tar.gz' in result.missing

    @pytest.mark.asyncio()
    async def test_api_error(self, pypi: PyPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test api error."""
        transport = _mock_transport({})
        monkeypatch.setattr('releasekit.backends.registry.pypi.http_client', _make_client_cm(transport, pypi))
        result = await pypi.verify_checksum('genkit', '1.0.0', {'f.tar.gz': 'abc'})
        assert result.ok is False
        assert 'f.tar.gz' in result.missing

    @pytest.mark.asyncio()
    async def test_bad_json(self, pypi: PyPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test bad json."""
        transport = _mock_transport({'/pypi/genkit/1.0.0/json': (200, 'not json')})
        monkeypatch.setattr('releasekit.backends.registry.pypi.http_client', _make_client_cm(transport, pypi))
        result = await pypi.verify_checksum('genkit', '1.0.0', {'f.tar.gz': 'abc'})
        assert result.ok is False


class TestPollAvailable:
    """Tests for Poll Available."""

    @pytest.mark.asyncio()
    async def test_immediately_available(self, pypi: PyPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test immediately available."""
        transport = _mock_transport({'/pypi/genkit/1.0.0/json': (200, '{}')})
        monkeypatch.setattr('releasekit.backends.registry.pypi.http_client', _make_client_cm(transport, pypi))
        result = await pypi.poll_available('genkit', '1.0.0', timeout=10.0, interval=1.0)
        assert result is True

    @pytest.mark.asyncio()
    async def test_timeout(self, pypi: PyPIBackend, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test timeout."""
        transport = _mock_transport({})
        monkeypatch.setattr('releasekit.backends.registry.pypi.http_client', _make_client_cm(transport, pypi))
        # Use minimum timeout to make test fast.
        result = await pypi.poll_available('genkit', '9.9.9', timeout=10.0, interval=1.0)
        assert result is False


# Helpers


def _make_client_cm(transport: Any, pypi: PyPIBackend) -> Any:  # noqa: ANN401
    """Create a context manager that yields an httpx.AsyncClient with mock transport."""

    @asynccontextmanager
    async def _client_cm(**kw: Any) -> AsyncGenerator[httpx.AsyncClient]:  # noqa: ANN401
        """Client cm."""
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
            yield client

    return _client_cm
