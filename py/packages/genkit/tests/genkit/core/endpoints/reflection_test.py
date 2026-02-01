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

"""Tests for the Reflection API v2 module.

This module contains unit tests for the WebSocket-based Reflection API v2
client which connects to a runtime manager server.

Test coverage includes:
- JSON-RPC message structures (request, response, error)
- Helper functions (is_reflection_v2_enabled, get_reflection_v2_url)
- Active actions map operations
- Action descriptor generation
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from genkit.core.reflection import (
    ActiveAction,
    ActiveActionsMap,
    JsonRpcError,
    JsonRpcRequest,
    JsonRpcResponse,
    ReflectionClientV2,
    get_reflection_v2_url,
    is_reflection_v2_enabled,
)


class TestJsonRpcRequest:
    """Tests for JsonRpcRequest class."""

    def test_notification_to_dict(self) -> None:
        """Test that a notification (no ID) serializes correctly."""
        request = JsonRpcRequest(method='notify', params={'data': 'test'})
        result = request.to_dict()

        assert result == {
            'jsonrpc': '2.0',
            'method': 'notify',
            'params': {'data': 'test'},
        }

    def test_request_with_id_to_dict(self) -> None:
        """Test that a request with ID serializes correctly."""
        request = JsonRpcRequest(method='call', params=['arg1'], id=42)
        result = request.to_dict()

        assert result == {
            'jsonrpc': '2.0',
            'method': 'call',
            'params': ['arg1'],
            'id': 42,
        }

    def test_request_minimal_to_dict(self) -> None:
        """Test that a minimal request (no params, no ID) serializes correctly."""
        request = JsonRpcRequest(method='ping')
        result = request.to_dict()

        assert result == {
            'jsonrpc': '2.0',
            'method': 'ping',
        }


class TestJsonRpcResponse:
    """Tests for JsonRpcResponse class."""

    def test_success_response_to_dict(self) -> None:
        """Test that a success response serializes correctly."""
        response = JsonRpcResponse(result={'status': 'ok'}, id=1)
        result = response.to_dict()

        assert result == {
            'jsonrpc': '2.0',
            'result': {'status': 'ok'},
            'id': 1,
        }

    def test_error_response_to_dict(self) -> None:
        """Test that an error response serializes correctly."""
        error = JsonRpcError(code=-32600, message='Invalid Request')
        response = JsonRpcResponse(error=error, id=2)
        result = response.to_dict()

        assert result == {
            'jsonrpc': '2.0',
            'error': {'code': -32600, 'message': 'Invalid Request'},
            'id': 2,
        }

    def test_error_with_data_to_dict(self) -> None:
        """Test that an error with additional data serializes correctly."""
        error = JsonRpcError(code=-32000, message='Custom Error', data={'detail': 'extra info'})
        response = JsonRpcResponse(error=error, id=3)
        result = response.to_dict()

        assert result == {
            'jsonrpc': '2.0',
            'error': {
                'code': -32000,
                'message': 'Custom Error',
                'data': {'detail': 'extra info'},
            },
            'id': 3,
        }


class TestJsonRpcError:
    """Tests for JsonRpcError class."""

    def test_basic_error_to_dict(self) -> None:
        """Test that a basic error serializes correctly."""
        error = JsonRpcError(code=-32601, message='Method not found')
        result = error.to_dict()

        assert result == {
            'code': -32601,
            'message': 'Method not found',
        }

    def test_error_with_data_to_dict(self) -> None:
        """Test that an error with data serializes correctly."""
        error = JsonRpcError(code=-32000, message='Server Error', data={'stack': 'trace'})
        result = error.to_dict()

        assert result == {
            'code': -32000,
            'message': 'Server Error',
            'data': {'stack': 'trace'},
        }


class TestActiveActionsMap:
    """Tests for ActiveActionsMap class."""

    @pytest.mark.asyncio
    async def test_set_and_get(self) -> None:
        """Test that actions can be set and retrieved."""
        actions_map = ActiveActionsMap()
        action = ActiveAction(
            cancel=lambda: None,
            start_time=1000.0,
            trace_id='trace-123',
        )

        await actions_map.set('trace-123', action)
        result = await actions_map.get('trace-123')

        assert result is not None
        assert result is action
        assert result.trace_id == 'trace-123'

    @pytest.mark.asyncio
    async def test_get_nonexistent(self) -> None:
        """Test that getting a nonexistent action returns None."""
        actions_map = ActiveActionsMap()
        result = await actions_map.get('nonexistent')
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self) -> None:
        """Test that actions can be deleted."""
        actions_map = ActiveActionsMap()
        action = ActiveAction(
            cancel=lambda: None,
            start_time=1000.0,
            trace_id='trace-456',
        )

        await actions_map.set('trace-456', action)
        await actions_map.delete('trace-456')
        result = await actions_map.get('trace-456')

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self) -> None:
        """Test that deleting a nonexistent action doesn't raise an error."""
        actions_map = ActiveActionsMap()
        # Should not raise
        await actions_map.delete('nonexistent')


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_is_reflection_v2_enabled_false(self) -> None:
        """Test that v2 is disabled when env var is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove the env var if it exists
            os.environ.pop('GENKIT_REFLECTION_V2_SERVER', None)
            result = is_reflection_v2_enabled()
            assert result is False

    def test_is_reflection_v2_enabled_true(self) -> None:
        """Test that v2 is enabled when env var is set."""
        with patch.dict(os.environ, {'GENKIT_REFLECTION_V2_SERVER': 'ws://localhost:4100'}):
            result = is_reflection_v2_enabled()
            assert result is True

    def test_get_reflection_v2_url_not_set(self) -> None:
        """Test that URL is None when env var is not set."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop('GENKIT_REFLECTION_V2_SERVER', None)
            result = get_reflection_v2_url()
            assert result is None

    def test_get_reflection_v2_url_set(self) -> None:
        """Test that URL is returned when env var is set."""
        with patch.dict(os.environ, {'GENKIT_REFLECTION_V2_SERVER': 'ws://localhost:4100'}):
            result = get_reflection_v2_url()
            assert result == 'ws://localhost:4100'


class TestReflectionClientV2:
    """Tests for ReflectionClientV2 class."""

    def test_runtime_id(self) -> None:
        """Test that runtime_id is based on process ID."""
        mock_registry = MagicMock()
        client = ReflectionClientV2(mock_registry, 'ws://localhost:4100')

        # runtime_id should be the process ID as a string
        assert client.runtime_id == str(os.getpid())

    def test_default_configured_envs(self) -> None:
        """Test that default configured_envs is ['dev']."""
        mock_registry = MagicMock()
        client = ReflectionClientV2(mock_registry, 'ws://localhost:4100')

        assert client._configured_envs == ['dev']

    def test_custom_configured_envs(self) -> None:
        """Test that custom configured_envs can be set."""
        mock_registry = MagicMock()
        client = ReflectionClientV2(mock_registry, 'ws://localhost:4100', configured_envs=['prod', 'staging'])

        assert client._configured_envs == ['prod', 'staging']

    @pytest.mark.asyncio
    async def test_stop(self) -> None:
        """Test that stop() sets running to False and closes WebSocket."""
        mock_registry = MagicMock()
        client = ReflectionClientV2(mock_registry, 'ws://localhost:4100')
        client._running = True
        client._ws = AsyncMock()

        await client.stop()

        assert client._running is False
        client._ws.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_list_actions(self) -> None:
        """Test that _handle_list_actions returns action descriptors."""
        from genkit.core.action import Action
        from genkit.core.action.types import ActionKind

        mock_registry = MagicMock()

        # Mock action
        mock_action = MagicMock(spec=Action)
        mock_action.name = 'test_action'
        mock_action.kind = ActionKind.TOOL
        mock_action.description = 'A test tool'
        mock_action.input_schema = {'type': 'object'}
        mock_action.output_schema = {'type': 'string'}
        mock_action.metadata = {'key': 'value'}

        # Mock registry methods
        mock_registry.get_actions_by_kind.return_value = {'test_action': mock_action}
        mock_registry.list_actions = AsyncMock(return_value=[])

        client = ReflectionClientV2(mock_registry, 'ws://localhost:4100')
        result = await client._handle_list_actions()

        # Should have the action keyed by /{kind}/{name}
        assert '/tool/test_action' in result
        assert result['/tool/test_action']['name'] == 'test_action'
        assert result['/tool/test_action']['type'] == 'tool'
        assert result['/tool/test_action']['description'] == 'A test tool'

    @pytest.mark.asyncio
    async def test_handle_list_values(self) -> None:
        """Test that _handle_list_values returns value list."""
        mock_registry = MagicMock()
        mock_registry.list_values.return_value = ['model1', 'model2']

        client = ReflectionClientV2(mock_registry, 'ws://localhost:4100')
        result = await client._handle_list_values({'type': 'defaultModel'})

        assert result == ['model1', 'model2']
        mock_registry.list_values.assert_called_once_with('defaultModel')

    @pytest.mark.asyncio
    async def test_handle_cancel_action_missing_trace_id(self) -> None:
        """Test that cancel action returns error when traceId is missing."""
        mock_registry = MagicMock()
        client = ReflectionClientV2(mock_registry, 'ws://localhost:4100')

        result, error = await client._handle_cancel_action({})

        assert result is None
        assert error is not None
        assert error.code == -32602
        assert 'traceId' in error.message

    @pytest.mark.asyncio
    async def test_handle_cancel_action_not_found(self) -> None:
        """Test that cancel action returns error when action not found."""
        mock_registry = MagicMock()
        client = ReflectionClientV2(mock_registry, 'ws://localhost:4100')

        result, error = await client._handle_cancel_action({'traceId': 'nonexistent'})

        assert result is None
        assert error is not None
        assert error.code == -32004  # JSON-RPC implementation-defined server error

    @pytest.mark.asyncio
    async def test_handle_cancel_action_success(self) -> None:
        """Test that cancel action works correctly."""
        mock_registry = MagicMock()
        client = ReflectionClientV2(mock_registry, 'ws://localhost:4100')

        # Add an active action
        cancel_called = []

        def cancel_fn() -> None:
            cancel_called.append(True)

        action = ActiveAction(
            cancel=cancel_fn,
            start_time=1000.0,
            trace_id='trace-to-cancel',
        )
        await client._active_actions.set('trace-to-cancel', action)

        result, error = await client._handle_cancel_action({'traceId': 'trace-to-cancel'})

        assert error is None
        assert result is not None
        assert 'message' in result
        assert cancel_called == [True]

        # Action should be removed from active actions
        remaining = await client._active_actions.get('trace-to-cancel')
        assert remaining is None
