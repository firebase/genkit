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

"""Tests for the reflection API server.

This module contains unit tests for the ASGI-based reflection API server
which provides endpoints for inspecting and interacting with Genkit during
development.

Test coverage includes:
- Health check endpoint (/api/__health)
- Listing registered actions (/api/actions)
- Notification endpoint (/api/notify)
- Action execution with various scenarios (/api/runAction):
  - Standard action execution
  - Streaming action execution
  - Error handling when action not found
  - Context passing to actions

The tests use an ASGI client with mocked Registry to isolate and verify
each endpoint's behavior.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest  # type: ignore
import pytest_asyncio  # type: ignore
from httpx import ASGITransport, AsyncClient  # type: ignore

from genkit.core.reflection import create_reflection_asgi_app  # type: ignore
from genkit.core.registry import Registry  # type: ignore


@pytest.fixture
def mock_registry():
    """Create a mock Registry for testing."""
    return MagicMock(spec=Registry)


@pytest_asyncio.fixture
async def asgi_client(mock_registry):
    """Create an ASGI test client with a mock registry.

    Args:
        mock_registry: A mock Registry object.

    Returns:
        An AsyncClient configured to make requests to the test ASGI app.
    """
    app = create_reflection_asgi_app(mock_registry)
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url='http://test')
    try:
        yield client
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_health_check(asgi_client):
    """Test that the health check endpoint returns 200 OK."""
    response = await asgi_client.get('/api/__health')
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_actions(asgi_client, mock_registry):
    """Test that the actions list endpoint returns registered actions."""
    mock_registry.list_serializable_actions.return_value = {'action1': {'name': 'Action 1'}}
    response = await asgi_client.get('/api/actions')
    assert response.status_code == 200
    assert response.json() == {'action1': {'name': 'Action 1'}}


@pytest.mark.asyncio
async def test_notify_endpoint(asgi_client):
    """Test that the notify endpoint returns 200 OK."""
    response = await asgi_client.post('/api/notify')
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_run_action_not_found(asgi_client, mock_registry):
    """Test that requesting a non-existent action returns a 404 error."""
    mock_registry.lookup_action_by_key.return_value = None
    response = await asgi_client.post(
        '/api/runAction',
        json={'key': 'non_existent_action', 'input': {'data': 'test'}},
    )
    assert response.status_code == 404
    assert 'error' in response.json()


@pytest.mark.asyncio
async def test_run_action_standard(asgi_client, mock_registry):
    """Test that a standard (non-streaming) action works correctly."""
    mock_action = AsyncMock()
    mock_output = MagicMock()
    mock_output.response = {'result': 'success'}
    mock_output.trace_id = 'test_trace_id'
    mock_action.arun_raw.return_value = mock_output

    mock_registry.lookup_action_by_key.return_value = mock_action

    response = await asgi_client.post('/api/runAction', json={'key': 'test_action', 'input': {'data': 'test'}})

    assert response.status_code == 200
    response_data = response.json()
    assert 'result' in response_data
    assert 'telemetry' in response_data
    assert response_data['telemetry']['traceId'] == 'test_trace_id'
    mock_action.arun_raw.assert_called_once_with(raw_input={'data': 'test'}, context={})


@pytest.mark.asyncio
async def test_run_action_with_context(asgi_client, mock_registry):
    """Test that an action with context works correctly."""
    mock_action = AsyncMock()
    mock_output = MagicMock()
    mock_output.response = {'result': 'success'}
    mock_output.trace_id = 'test_trace_id'
    mock_action.arun_raw.return_value = mock_output

    mock_registry.lookup_action_by_key.return_value = mock_action

    response = await asgi_client.post(
        '/api/runAction',
        json={
            'key': 'test_action',
            'input': {'data': 'test'},
            'context': {'user': 'test_user'},
        },
    )

    assert response.status_code == 200
    mock_action.arun_raw.assert_called_once_with(raw_input={'data': 'test'}, context={'user': 'test_user'})


@pytest.mark.asyncio
@patch('genkit.core.reflection.is_streaming_requested')
async def test_run_action_streaming(mock_is_streaming, asgi_client, mock_registry):
    """Test that streaming actions work correctly."""
    mock_is_streaming.return_value = True
    mock_action = AsyncMock()

    async def mock_streaming(raw_input, on_chunk=None, context=None):
        if on_chunk:
            await on_chunk({'chunk': 1})
            await on_chunk({'chunk': 2})
        mock_output = MagicMock()
        mock_output.response = {'final': 'result'}
        mock_output.trace_id = 'stream_trace_id'
        return mock_output

    mock_action.arun_raw.side_effect = mock_streaming
    mock_registry.lookup_action_by_key.return_value = mock_action

    response = await asgi_client.post(
        '/api/runAction?stream=true',
        json={'key': 'test_action', 'input': {'data': 'test'}},
    )

    assert response.status_code == 200
    assert mock_is_streaming.called
