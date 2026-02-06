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

"""Reflection API v2 client using WebSocket and JSON-RPC 2.0.

This module implements a WebSocket-based client that connects to a Genkit
runtime manager server. Unlike v1 which starts an HTTP server, v2 acts as
a client connecting to a centralized manager.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                               │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Reflection API v1   │ Genkit starts a server, tools connect to it.  │
    │                     │ Like opening a shop and waiting for customers. │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ Reflection API v2   │ Genkit connects to a manager as a client.     │
    │                     │ Like calling the headquarters to report in.    │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ JSON-RPC 2.0        │ A simple protocol for remote procedure calls. │
    │                     │ Like a structured phone conversation.          │
    ├─────────────────────┼────────────────────────────────────────────────┤
    │ WebSocket           │ A persistent two-way connection.              │
    │                     │ Like keeping a phone line open.                │
    └─────────────────────┴────────────────────────────────────────────────┘

Architecture Comparison::

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                      Reflection API V1 (HTTP Server)                    │
    └─────────────────────────────────────────────────────────────────────────┘

    Genkit Runtime starts an HTTP server; CLI/DevUI connect to it:

        ┌─────────────────────┐          ┌─────────────────────┐
        │    Genkit CLI       │          │      Dev UI         │
        │    (Client)         │          │     (Client)        │
        └──────────┬──────────┘          └──────────┬──────────┘
                   │                                │
                   │       HTTP Requests            │
                   │    (GET /api/actions, etc)     │
                   │                                │
                   ▼                                ▼
        ┌───────────────────────────────────────────────────────┐
        │                  Genkit Runtime                       │
        │               ┌────────────────────┐                  │
        │               │   HTTP Server      │                  │
        │               │   (port 3100)      │                  │
        │               └────────────────────┘                  │
        │               ┌────────────────────┐                  │
        │               │     Registry       │                  │
        │               │  (Actions, Flows)  │                  │
        │               └────────────────────┘                  │
        └───────────────────────────────────────────────────────┘

        Discovery: Runtime writes file to ~/.genkit/{runtimeId}.runtime.json
        Connection: CLI reads file, finds port, connects via HTTP

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                      Reflection API V2 (WebSocket)                      │
    └─────────────────────────────────────────────────────────────────────────┘

    CLI acts as WebSocket server; Genkit Runtimes connect as clients:

        ┌───────────────────────────────────────────────────────┐
        │                 Runtime Manager                       │
        │               (CLI WebSocket Server)                  │
        │               ┌────────────────────┐                  │
        │               │  WebSocket Server  │                  │
        │               │   (port 4100)      │                  │
        │               └────────────────────┘                  │
        │               ┌────────────────────┐                  │
        │               │     Dev UI         │                  │
        │               └────────────────────┘                  │
        └───────────────────────────────────────────────────────┘
                        ▲           ▲           ▲
                        │           │           │
           WebSocket    │           │           │   WebSocket
           Connect      │           │           │   Connect
                        │           │           │
        ┌───────────────┴───┐ ┌─────┴─────┐ ┌───┴───────────────┐
        │   Genkit Runtime  │ │  Runtime  │ │   Genkit Runtime  │
        │   (Python app)    │ │  (JS app) │ │   (Go app)        │
        └───────────────────┘ └───────────┘ └───────────────────┘

        Discovery: Runtime reads GENKIT_REFLECTION_V2_SERVER env var
        Connection: Runtime connects outbound to Manager via WebSocket

Data Flow (V2)::

    Genkit Runtime                    Runtime Manager Server
         │                                    │
         │  ──── WebSocket Connect ────►      │
         │                                    │
         │  ──── register (JSON-RPC) ────►    │
         │                                    │
         │  ◄──── configure notification ──   │
         │                                    │
         │  ◄──── listActions request ────    │
         │  ──── response with actions ────►  │
         │                                    │
         │  ◄──── runAction request ────      │
         │  ──── runActionState notif ────►   │  (sends traceId early)
         │  ──── streamChunk notification ──► │  (if streaming)
         │  ──── response with result ────►   │
         │                                    │
         │  ◄──── cancelAction request ────   │
         │  ──── response (cancelled) ────►   │
         │                                    │

Protocol Methods (V2)::

    ┌──────────────────┬─────────────────┬─────────┬─────────────────────────┐
    │ Method           │ Direction       │ Type    │ Description             │
    ├──────────────────┼─────────────────┼─────────┼─────────────────────────┤
    │ register         │ Runtime→Manager │ Notif   │ Register runtime info   │
    │ configure        │ Manager→Runtime │ Notif   │ Push config (telemetry) │
    │ listActions      │ Manager→Runtime │ Request │ List available actions  │
    │ listValues       │ Manager→Runtime │ Request │ List values by type     │
    │ runAction        │ Manager→Runtime │ Request │ Execute an action       │
    │ runActionState   │ Runtime→Manager │ Notif   │ Send traceId early      │
    │ streamChunk      │ Runtime→Manager │ Notif   │ Stream output chunk     │
    │ cancelAction     │ Manager→Runtime │ Request │ Cancel running action   │
    └──────────────────┴─────────────────┴─────────┴─────────────────────────┘

Environment Variables:
    GENKIT_REFLECTION_V2_SERVER: WebSocket URL to connect to (e.g., ws://localhost:4100)
    GENKIT_TELEMETRY_SERVER: Optional telemetry server URL

Example:
    >>> import asyncio
    >>> from genkit.core.reflection import ReflectionClientV2
    >>> async def main():
    ...     client = ReflectionClientV2(registry, 'ws://localhost:4100')
    ...     await client.run()

See Also:
    - RFC: https://github.com/firebase/genkit/pull/4211
    - V1 HTTP server implementation: genkit.core.reflection_v1
"""

from __future__ import annotations

import asyncio
import json
import os
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import websockets

from genkit.codec import dump_dict
from genkit.core.action.types import ActionKind
from genkit.core.constants import (
    DEFAULT_GENKIT_VERSION,
    GENKIT_REFLECTION_API_SPEC_VERSION,
)
from genkit.core.error import get_reflection_json
from genkit.core.logging import get_logger

if TYPE_CHECKING:
    from genkit.core.action import Action
    from genkit.core.registry import Registry

logger = get_logger(__name__)

# Environment variable for v2 server URL
GENKIT_REFLECTION_V2_SERVER_ENV = 'GENKIT_REFLECTION_V2_SERVER'


@dataclass
class JsonRpcRequest:
    """JSON-RPC 2.0 request or notification."""

    jsonrpc: str = '2.0'
    method: str = ''
    params: dict[str, Any] | list[Any] | None = None
    id: int | str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {'jsonrpc': self.jsonrpc, 'method': self.method}
        if self.params is not None:
            result['params'] = self.params
        if self.id is not None:
            result['id'] = self.id
        return result


@dataclass
class JsonRpcError:
    """JSON-RPC 2.0 error object."""

    code: int
    message: str
    data: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {'code': self.code, 'message': self.message}
        if self.data is not None:
            result['data'] = self.data
        return result


@dataclass
class JsonRpcResponse:
    """JSON-RPC 2.0 response."""

    jsonrpc: str = '2.0'
    result: Any = None
    error: JsonRpcError | None = None
    id: int | str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        response: dict[str, Any] = {'jsonrpc': self.jsonrpc, 'id': self.id}
        if self.error is not None:
            response['error'] = self.error.to_dict()
        else:
            response['result'] = self.result
        return response


@dataclass
class ActiveAction:
    """Represents an in-flight action that can be cancelled."""

    cancel: Callable[[], None]
    start_time: float
    trace_id: str
    task: asyncio.Task[Any] | None = None


@dataclass
class ActiveActionsMap:
    """Thread-safe map of active actions."""

    _actions: dict[str, ActiveAction] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def set(self, trace_id: str, action: ActiveAction) -> None:
        """Add an active action."""
        async with self._lock:
            self._actions[trace_id] = action

    async def get(self, trace_id: str) -> ActiveAction | None:
        """Get an active action by trace ID."""
        async with self._lock:
            return self._actions.get(trace_id)

    async def delete(self, trace_id: str) -> None:
        """Remove an active action."""
        async with self._lock:
            self._actions.pop(trace_id, None)


class ReflectionClientV2:
    """Reflection API v2 client using WebSocket and JSON-RPC 2.0.

    This client connects to a Genkit runtime manager server and handles
    requests for listing actions, running actions, and other reflection
    operations.

    Attributes:
        registry: The Genkit registry containing actions and values.
        url: The WebSocket URL to connect to.
        active_actions: Map of currently running actions for cancellation.
    """

    def __init__(
        self,
        registry: Registry,
        url: str,
        *,
        version: str = DEFAULT_GENKIT_VERSION,
        configured_envs: list[str] | None = None,
    ) -> None:
        """Initialize the Reflection v2 client.

        Args:
            registry: The Genkit registry.
            url: WebSocket URL to connect to.
            version: Genkit version string.
            configured_envs: List of configured environments.
        """
        self._registry = registry
        self._url = url
        self._version = version
        self._configured_envs = configured_envs or ['dev']
        self._ws: Any = None  # WebSocket connection
        self._active_actions = ActiveActionsMap()
        self._running = False
        self._reconnect_delay = 1.0  # seconds
        self._max_reconnect_delay = 60.0  # maximum delay for exponential backoff

    @property
    def runtime_id(self) -> str:
        """Generate a unique runtime ID based on process ID."""
        return str(os.getpid())

    async def run(self) -> None:
        """Run the reflection client with automatic reconnection.

        This method will continuously try to connect to the server and
        handle messages. If the connection drops, it will attempt to
        reconnect after a delay.
        """
        self._running = True
        logger.info(f'Connecting to Reflection v2 server: {self._url}')

        while self._running:
            try:
                async with websockets.connect(self._url) as ws:
                    self._ws = ws
                    self._reconnect_delay = 1.0  # Reset delay on successful connection
                    logger.info('Connected to Reflection v2 server')

                    # Register immediately upon connection
                    await self._register()

                    # Handle messages
                    async for message in ws:
                        if isinstance(message, bytes):
                            message = message.decode('utf-8')
                        asyncio.create_task(self._handle_message(message))

            except asyncio.CancelledError:
                logger.debug('Reflection v2 client cancelled')
                break
            except Exception as e:
                delay = self._reconnect_delay
                logger.debug(f'Failed to connect to Reflection v2 server, retrying in {delay:.1f}s: {e}')
                self._ws = None
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)

        self._running = False
        logger.info('Disconnected from Reflection v2 server')

    async def stop(self) -> None:
        """Stop the reflection client."""
        self._running = False
        if self._ws:
            await self._ws.close()

    async def _register(self) -> None:
        """Send registration message to the server."""
        request = JsonRpcRequest(
            method='register',
            params={
                'id': self.runtime_id,
                'name': self.runtime_id,
                'pid': os.getpid(),
                'genkitVersion': f'python/{self._version}',
                'reflectionApiSpecVersion': GENKIT_REFLECTION_API_SPEC_VERSION,
                'envs': self._configured_envs,
            },
        )
        await self._send(request.to_dict())

    async def _send(self, message: dict[str, Any]) -> None:
        """Send a message to the server."""
        if self._ws is None:
            raise RuntimeError('WebSocket not connected')

        data = json.dumps(message)
        logger.debug(f'Sending v2 message: {data}')
        await self._ws.send(data)

    async def _handle_message(self, data: str) -> None:
        """Handle an incoming message from the server."""
        logger.debug(f'Received v2 message: {data}')

        try:
            msg = json.loads(data)
        except json.JSONDecodeError as e:
            logger.error(f'Failed to parse JSON-RPC message: {e}')
            return

        method = msg.get('method', '')
        msg_id = msg.get('id')

        if method:
            if msg_id is not None:
                # Request (has ID, expects response)
                await self._handle_request(msg)
            else:
                # Notification (no ID, no response expected)
                await self._handle_notification(msg)
        elif msg_id is not None:
            # Response to a request we sent
            logger.debug(f'Received response for id={msg_id}')

    async def _handle_request(self, msg: dict[str, Any]) -> None:
        """Handle an incoming JSON-RPC request."""
        method = msg.get('method', '')
        params = msg.get('params', {})
        msg_id = msg.get('id')

        result: Any = None
        error: JsonRpcError | None = None

        try:
            if method == 'listActions':
                result = await self._handle_list_actions()
            elif method == 'listValues':
                result = await self._handle_list_values(params)
            elif method == 'runAction':
                # runAction handles its own response
                await self._handle_run_action(msg)
                return
            elif method == 'cancelAction':
                result, error = await self._handle_cancel_action(params)
            else:
                error = JsonRpcError(
                    code=-32601,
                    message=f'Method not found: {method}',
                )
        except Exception as e:
            logger.exception(f'Error handling request {method}')
            error = JsonRpcError(
                code=-32000,
                message=str(e),
                data={'stack': traceback.format_exc()},
            )

        # Send response
        response = JsonRpcResponse(
            id=msg_id,
            result=result,
            error=error,
        )
        await self._send(response.to_dict())

    async def _handle_notification(self, msg: dict[str, Any]) -> None:
        """Handle an incoming JSON-RPC notification."""
        method = msg.get('method', '')
        params = msg.get('params', {})

        if method == 'configure':
            await self._handle_configure(params)
        else:
            logger.debug(f'Unknown notification: {method}')

    async def _handle_list_actions(self) -> dict[str, dict[str, Any]]:
        """Handle listActions request.

        Returns:
            Dictionary of action descriptors keyed by action key.
        """
        actions: dict[str, dict[str, Any]] = {}

        # Get registered actions (using resolve to trigger lazy loading)
        for kind in ActionKind.__members__.values():
            for name, action in (await self._registry.resolve_actions_by_kind(kind)).items():
                key = f'/{kind.value}/{name}'
                actions[key] = self._action_to_desc(action, key)

        # Get plugin-advertised actions
        metas = await self._registry.list_actions()
        for meta in metas or []:
            try:
                key = f'/{meta.kind.value}/{meta.name}'
                if key not in actions:
                    actions[key] = {
                        'key': key,
                        'name': meta.name,
                        'type': meta.kind.value,
                        'description': getattr(meta, 'description', None),
                        'inputSchema': getattr(meta, 'input_json_schema', None),
                        'outputSchema': getattr(meta, 'output_json_schema', None),
                        'metadata': getattr(meta, 'metadata', None),
                    }
            except Exception as e:
                logger.warning(f'Skipping invalid plugin action metadata: {e}')

        return actions

    def _action_to_desc(self, action: Action, key: str) -> dict[str, Any]:
        """Convert an Action to an action descriptor dictionary."""
        return {
            'key': key,
            'name': action.name,
            'type': action.kind.value,
            'description': action.description,
            'inputSchema': action.input_schema,
            'outputSchema': action.output_schema,
            'metadata': action.metadata,
        }

    async def _handle_list_values(self, params: dict[str, Any]) -> list[str]:
        """Handle listValues request.

        Args:
            params: Request parameters containing 'type'.

        Returns:
            List of value names.

        Raises:
            ValueError: If type parameter is missing or unsupported.
        """
        value_type = params.get('type')

        if not value_type:
            raise ValueError("The 'type' parameter is required for listValues.")

        if value_type != 'defaultModel':
            raise ValueError(f"Value type '{value_type}' is not supported. Only 'defaultModel' is currently supported.")

        return self._registry.list_values(value_type)

    async def _handle_run_action(self, msg: dict[str, Any]) -> None:
        """Handle runAction request with streaming support.

        This method handles its own response sending since it needs to
        send intermediate notifications for streaming and telemetry.

        Args:
            msg: The JSON-RPC request message.
        """
        msg_id = msg.get('id')
        params = msg.get('params', {})

        key = params.get('key', '')
        action_input = params.get('input')
        context = params.get('context', {})
        stream = params.get('stream', False)

        # Look up action
        action = await self._registry.resolve_action_by_key(key)
        if action is None:
            await self._send_error(msg_id, -32602, f'Action not found: {key}')
            return

        # Get the current task to allow for cancellation
        current_task = asyncio.current_task()

        # Track trace ID for telemetry
        run_trace_id: str | None = None
        sent_trace_ids: set[str] = set()

        async def on_trace_start(tid: str) -> None:
            nonlocal run_trace_id
            if tid in sent_trace_ids:
                return
            sent_trace_ids.add(tid)
            run_trace_id = tid

            # Register active action with task cancellation
            # Wrap cancel() in lambda to discard bool return value (expected: () -> None)
            def cancel_fn() -> None:
                if current_task:
                    _ = current_task.cancel()

            await self._active_actions.set(
                tid,
                ActiveAction(
                    cancel=cancel_fn,
                    start_time=asyncio.get_event_loop().time(),
                    trace_id=tid,
                    task=current_task,
                ),
            )

            # Send runActionState notification
            notification = JsonRpcRequest(
                method='runActionState',
                params={
                    'requestId': msg_id,
                    'state': {'traceId': tid},
                },
            )
            await self._send(notification.to_dict())

        # Streaming callback
        async def send_chunk(chunk: Any) -> None:  # noqa: ANN401
            if stream:
                notification = JsonRpcRequest(
                    method='streamChunk',
                    params={
                        'requestId': msg_id,
                        'chunk': dump_dict(chunk),
                    },
                )
                await self._send(notification.to_dict())

        # Set up synchronous wrapper for on_trace_start
        # (action.arun_raw expects sync callback currently)
        def sync_on_trace_start(tid: str) -> None:
            asyncio.create_task(on_trace_start(tid))

        # Synchronous chunk callback wrapper
        def sync_send_chunk(chunk: Any) -> None:  # noqa: ANN401
            asyncio.create_task(send_chunk(chunk))

        try:
            output = await action.arun_raw(
                raw_input=action_input,
                on_chunk=sync_send_chunk if stream else None,
                context=context,
                on_trace_start=sync_on_trace_start,
            )

            # Clean up active action
            if run_trace_id:
                await self._active_actions.delete(run_trace_id)

            # Send success response
            await self._send_response(
                msg_id,
                {
                    'result': dump_dict(output.response),
                    'telemetry': {'traceId': output.trace_id},
                },
            )

        except asyncio.CancelledError:
            logger.info(f'Action {key} with traceId {run_trace_id} was cancelled.')
            if run_trace_id:
                await self._active_actions.delete(run_trace_id)
            await self._send_error(
                msg_id,
                -32000,
                'Action was cancelled by request.',
                data={'traceId': run_trace_id} if run_trace_id else None,
            )

        except Exception as e:
            logger.exception(f'Error running action {key}')

            # Clean up active action
            if run_trace_id:
                await self._active_actions.delete(run_trace_id)

            # Send error response
            error_data = get_reflection_json(e).model_dump(by_alias=True)
            if run_trace_id:
                error_data.setdefault('details', {})['traceId'] = run_trace_id

            await self._send_error(
                msg_id,
                -32000,
                str(e),
                data=error_data,
            )

    async def _handle_cancel_action(self, params: dict[str, Any]) -> tuple[dict[str, str] | None, JsonRpcError | None]:
        """Handle cancelAction request.

        Args:
            params: Request parameters containing 'traceId'.

        Returns:
            Tuple of (result, error).
        """
        trace_id = params.get('traceId', '')

        if not trace_id:
            return None, JsonRpcError(code=-32602, message='traceId is required')

        action = await self._active_actions.get(trace_id)
        if action is None:
            return None, JsonRpcError(
                code=-32004,  # JSON-RPC implementation-defined server error
                message='Action not found or already completed',
            )

        # Cancel the action
        action.cancel()
        await self._active_actions.delete(trace_id)

        return {'message': 'Action cancelled'}, None

    async def _handle_configure(self, params: dict[str, Any]) -> None:
        """Handle configure notification.

        Args:
            params: Configuration parameters.
        """
        telemetry_url = params.get('telemetryServerUrl', '')

        if not os.environ.get('GENKIT_TELEMETRY_SERVER') and telemetry_url:
            # TODO(#4401): Implement telemetry server URL configuration
            logger.debug(f'Telemetry server URL configured: {telemetry_url}')

    async def _send_response(self, msg_id: int | str | None, result: object) -> None:
        """Send a success response."""
        response = JsonRpcResponse(id=msg_id, result=result)
        await self._send(response.to_dict())

    async def _send_error(
        self,
        msg_id: int | str | None,
        code: int,
        message: str,
        data: object = None,
    ) -> None:
        """Send an error response."""
        response = JsonRpcResponse(
            id=msg_id,
            error=JsonRpcError(code=code, message=message, data=data),
        )
        await self._send(response.to_dict())


def is_reflection_v2_enabled() -> bool:
    """Check if Reflection API v2 is enabled.

    Returns:
        True if GENKIT_REFLECTION_V2_SERVER is set, False otherwise.
    """
    return bool(os.environ.get(GENKIT_REFLECTION_V2_SERVER_ENV))


def get_reflection_v2_url() -> str | None:
    """Get the Reflection API v2 server URL.

    Returns:
        The WebSocket URL if set, None otherwise.
    """
    return os.environ.get(GENKIT_REFLECTION_V2_SERVER_ENV)
