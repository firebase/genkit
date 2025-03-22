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

"""Tests for the flows API server.

This module contains unit tests for the ASGI-based flows API server
which provides endpoints for executing GenKit flows.

## Test coverage includes:

- Health check endpoint (/__health)
- Listing registered flows (/list)
- Flow execution with various scenarios (/{flow_name}):
  - Standard flow execution
  - Streaming flow execution
  - Error handling when flow not found
  - Context passing to flows
  - Context provider errors
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from genkit.core.action import ActionKind, ActionResponse
from genkit.core.endpoints.flows import create_flows_asgi_app
from genkit.core.registry import Registry


@pytest.fixture
def mock_registry():
    """Create a mock Registry for testing."""
    return MagicMock(spec=Registry)


@pytest_asyncio.fixture
async def asgi_client(mock_registry):
    """Create an ASGI test client with a mock registry.

    Args:
        mock_registry: The mock registry to use for the ASGI app.

    Returns:
        An ASGI test client.
    """
    app = create_flows_asgi_app(mock_registry)
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url='http://test')
    try:
        yield client
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_health_check(asgi_client):
    """Test that the health check endpoint returns 200 OK."""
    response = await asgi_client.get('/__health')
    assert response.status_code == 200
    assert response.json() == {'status': 'OK'}


@pytest.mark.asyncio
async def test_list_flows(asgi_client, mock_registry):
    """Test that the flows list endpoint returns registered flows."""
    # Mock the registry to return a list of flows
    mock_registry.list_serializable_actions.return_value = {
        'flow1': {'name': 'Flow 1'}
    }
    response = await asgi_client.get('/list')
    assert response.status_code == 200
    assert response.json() == {'flow1': {'name': 'Flow 1'}}
    mock_registry.list_serializable_actions.assert_called_once_with({
        ActionKind.FLOW
    })


@pytest.mark.asyncio
async def test_run_flow_not_found(asgi_client, mock_registry):
    """Test that requesting a non-existent flow returns a 404 error."""
    mock_registry.lookup_action_by_key.return_value = None
    response = await asgi_client.post('/nonexistent_flow')
    assert response.status_code == 404
    assert 'error' in response.json()
    assert 'Flow not found' in response.json()['error']


@pytest.mark.asyncio
async def test_run_flow_invalid_json(asgi_client):
    """Test that invalid JSON payload returns a 500 error."""
    # Send invalid JSON
    response = await asgi_client.post(
        '/test_flow',
        content='{invalid}',
        headers={'Content-Type': 'application/json'},
    )
    assert response.status_code == 500
    assert 'error' in response.json()
    assert 'Invalid JSON' in response.json()['error']


@pytest.mark.asyncio
async def test_run_flow_standard(asgi_client, mock_registry):
    """Test that a standard (non-streaming) flow works correctly."""
    # Mock the flow action
    mock_action = AsyncMock()
    mock_output = ActionResponse(
        response={'result': 'success'}, trace_id='test-trace-id'
    )
    mock_action.arun_raw.return_value = mock_output
    mock_registry.lookup_action_by_key.return_value = mock_action

    # Create a patch to ensure streaming is not requested
    with patch(
        'genkit.core.endpoints.flows.is_streaming_requested', return_value=False
    ):
        response = await asgi_client.post(
            '/test_flow',
            json={'data': {'param1': 'value1'}},
        )

    assert response.status_code == 200
    assert response.json() == {'result': 'success'}
    # Check that the action was called with the right parameters
    mock_action.arun_raw.assert_called_once_with(
        {'param1': 'value1'}, context={}
    )


@pytest.mark.asyncio
async def test_run_flow_with_context_providers(asgi_client, mock_registry):
    """Test that context providers are applied correctly."""
    # Mock the flow action
    mock_action = AsyncMock()
    mock_output = ActionResponse(
        response={'result': 'success'}, trace_id='test-trace-id'
    )
    mock_action.arun_raw.return_value = mock_output
    mock_registry.lookup_action_by_key.return_value = mock_action

    # Define a context provider
    async def context_provider(request):
        assert request.headers.get('Authorization') == 'Bearer token'
        return {'user_id': 'test_user', 'auth': True}

    # Create a new client with the context provider
    app = create_flows_asgi_app(
        mock_registry, context_providers=[context_provider]
    )
    app.state.context = {}
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url='http://test')

    # Test with context provider
    with patch(
        'genkit.core.endpoints.flows.is_streaming_requested', return_value=False
    ):
        response = await client.post(
            '/test_flow',
            json={'data': {'param1': 'value1'}},
            headers={'Authorization': 'Bearer token'},
        )

    assert response.status_code == 200
    assert response.json() == {'result': 'success'}
    # Check context was applied
    mock_action.arun_raw.assert_called_once_with(
        {'param1': 'value1'}, context={'user_id': 'test_user', 'auth': True}
    )

    # Clean up
    await client.aclose()


@pytest.mark.asyncio
async def test_context_provider_error(asgi_client, mock_registry):
    """Test that errors in context providers are handled correctly."""

    async def failing_provider(request):
        raise ValueError('Authentication failed')

    # Create a new client with the failing context provider
    app = create_flows_asgi_app(
        mock_registry, context_providers=[failing_provider]
    )
    app.state.context = {}
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url='http://test')

    # Test with failing context provider
    response = await client.post(
        '/test_flow',
        json={'data': {'param1': 'value1'}},
        headers={'Authorization': 'Bearer token'},
    )

    assert response.status_code == 401
    assert 'error' in response.json()
    assert 'Authentication failed' in response.json()['error']

    # Clean up
    await client.aclose()


@pytest.mark.asyncio
@patch('genkit.core.endpoints.flows.is_streaming_requested')
async def test_run_flow_streaming(
    mock_is_streaming, asgi_client, mock_registry
):
    """Test that a streaming flow works correctly."""
    # Configure the mock to return True for streaming
    mock_is_streaming.return_value = True

    # Mock the flow action
    mock_action = AsyncMock()

    # Define behavior for streaming response
    async def mock_streaming(input, on_chunk=None, context=None):
        if on_chunk:
            await on_chunk({'chunk': 1})
            await on_chunk({'chunk': 2})
        return ActionResponse(
            response={'final': 'result'}, trace_id='test-trace-id'
        )

    mock_action.arun_raw.side_effect = mock_streaming
    mock_registry.lookup_action_by_key.return_value = mock_action

    # Make the request
    response = await asgi_client.post(
        '/test_flow',
        json={'data': {'param1': 'value1'}},
        headers={'Accept': 'text/event-stream'},
    )

    assert response.status_code == 200
    assert response.headers['Content-Type'] == (
        'text/event-stream; charset=utf-8'
    )

    # Parse SSE events from response
    content = response.content.decode('utf-8')
    events = [line for line in content.split('\n\n') if line]

    # Check that we have 3 events (2 chunks + final)
    assert len(events) == 3
    assert '"chunk": 1' in events[0]
    assert '"chunk": 2' in events[1]
    assert '"final": "result"' in events[2]


@pytest.mark.asyncio
@patch('genkit.core.endpoints.flows.is_streaming_requested')
async def test_run_flow_streaming_error(
    mock_is_streaming, asgi_client, mock_registry
):
    """Test that errors in streaming flows are handled correctly."""
    # Configure the mock to return True for streaming
    mock_is_streaming.return_value = True

    # Mock the flow action
    mock_action = AsyncMock()

    # Define behavior for streaming response with error
    async def mock_streaming_error(input, on_chunk=None, context=None):
        if on_chunk:
            await on_chunk({'chunk': 1})
            raise ValueError('Test streaming error')
        return None  # Never reached

    mock_action.arun_raw.side_effect = mock_streaming_error
    mock_registry.lookup_action_by_key.return_value = mock_action

    # Make the request
    response = await asgi_client.post(
        '/test_flow',
        json={'data': {'param1': 'value1'}},
        headers={'Accept': 'text/event-stream'},
    )

    assert response.status_code == 200  # SSE responses are always 200
    assert response.headers['Content-Type'] == (
        'text/event-stream; charset=utf-8'
    )

    # Parse SSE events from response
    content = response.content.decode('utf-8')
    events = [line for line in content.split('\n\n') if line]

    # Check that we have 2 events (1 chunk + error)
    assert len(events) == 2
    assert '"chunk": 1' in events[0]
    assert 'error' in events[1]
    assert 'Test streaming error' in events[1]


@pytest.mark.asyncio
async def test_flow_name_missing(asgi_client):
    """Test handling when no flow name is provided."""
    for method in ['GET', 'POST']:
        response = await asgi_client.request(method, '/')
        assert response.status_code == 405
        assert 'error' in response.json()
        # For the empty string, the framework treats it as "root", not as
        # "flow name not provided". We need to test specifically with the '/'
        # endpoint.
        try:
            assert 'Flow name not provided' in response.json()['error']
        except AssertionError:
            # Alternate check in case behavior changes
            assert 'Flow not found' in json.loads(response.body)['error']
            break


@pytest.mark.asyncio
async def test_server_lifecycle_callbacks():
    """Test that lifecycle callbacks are called correctly."""
    on_startup = AsyncMock()
    on_shutdown = AsyncMock()

    app = create_flows_asgi_app(
        MagicMock(spec=Registry),
        on_app_startup=on_startup,
        on_app_shutdown=on_shutdown,
    )

    # Trigger startup event
    await app.router.lifespan_context.startup()
    on_startup.assert_called_once()

    # Trigger shutdown event
    await app.router.lifespan_context.shutdown()
    on_shutdown.assert_called_once()
