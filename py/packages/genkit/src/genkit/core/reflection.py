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

"""Development API for inspecting and interacting with Genkit.

This module provides a reflection API server for inspection and interaction
during development. It exposes endpoints for health checks, action discovery,
and action execution.

## Caveats

The reflection API server predates the flows server implementation and differs
in the protocol it uses to interface with the Dev UI. The streaming protocol
uses unadorned JSON per streamed chunk. This may change in the future to use
Server-Sent Events (SSE).

## Key endpoints

    | Method | Path                | Handler               |
    |--------|---------------------|-----------------------|
    | GET    | /api/__health       | Health check          |
    | GET    | /api/actions        | List actions          |
    | POST   | /api/__quitquitquit | Trigger shutdown      |
    | POST   | /api/notify         | Handle notification   |
    | POST   | /api/runAction      | Run action (streaming)|
"""

from __future__ import annotations

import asyncio
import json
import urllib.parse
from collections.abc import AsyncGenerator
from http.server import BaseHTTPRequestHandler
from typing import Any

import structlog
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

from genkit.aio.loop import run_async
from genkit.codec import dump_dict, dump_json
from genkit.core.action import Action
from genkit.core.action.types import ActionKind
from genkit.core.constants import DEFAULT_GENKIT_VERSION
from genkit.core.error import get_reflection_json
from genkit.core.registry import Registry
from genkit.web.manager.signals import terminate_all_servers
from genkit.web.requests import (
    is_streaming_requested,
)
from genkit.web.typing import (
    Application,
    LifespanHandler,
)

logger = structlog.get_logger(__name__)


def _list_registered_actions(registry: Registry) -> dict[str, Action]:
    """Return all locally registered actions keyed as `/<kind>/<name>`."""
    registered: dict[str, Action] = {}
    for kind in ActionKind:
        for name, action in registry.get_actions_by_kind(kind).items():
            registered[f'/{kind.value}/{name}'] = action
    return registered


def _build_actions_payload(
    *,
    registered_actions: dict[str, Action],
    plugin_metas: list[Any],
) -> dict[str, dict[str, Any]]:
    """Build payload for GET /api/actions."""
    actions: dict[str, dict[str, Any]] = {}

    # 1) Registered actions (flows/tools/etc).
    for key, action in registered_actions.items():
        actions[key] = {
            'key': key,
            'name': action.name,
            'type': action.kind.value,
            'description': action.description,
            'inputSchema': action.input_schema,
            'outputSchema': action.output_schema,
            'metadata': action.metadata,
        }

    # 2) Plugin-advertised actions (may not be registered yet).
    for meta in plugin_metas or []:
        try:
            key = f'/{meta.kind.value}/{meta.name}'
        except Exception as exc:
            # Defensive: skip unexpected plugin metadata objects.
            logger.warning('Skipping invalid plugin action metadata', error=str(exc))
            continue

        advertised = {
            'key': key,
            'name': meta.name,
            'type': meta.kind.value,
            'description': getattr(meta, 'description', None),
            'inputSchema': getattr(meta, 'input_json_schema', None),
            'outputSchema': getattr(meta, 'output_json_schema', None),
            'metadata': getattr(meta, 'metadata', None),
        }

        if key not in actions:
            actions[key] = advertised
            continue

        # Merge into the existing (registered) action entry; prefer registered data.
        existing = actions[key]

        if not existing.get('description') and advertised.get('description'):
            existing['description'] = advertised['description']

        if not existing.get('inputSchema') and advertised.get('inputSchema'):
            existing['inputSchema'] = advertised['inputSchema']

        if not existing.get('outputSchema') and advertised.get('outputSchema'):
            existing['outputSchema'] = advertised['outputSchema']

        existing_meta = existing.get('metadata') or {}
        advertised_meta = advertised.get('metadata') or {}
        if isinstance(existing_meta, dict) and isinstance(advertised_meta, dict):
            # Prefer registered action metadata on key conflicts.
            existing['metadata'] = {**advertised_meta, **existing_meta}

    return actions


def make_reflection_server(
    registry: Registry,
    loop: asyncio.AbstractEventLoop,
    id: str,
    encoding='utf-8',
    quiet=True,
):
    """Create and return a ReflectionServer class with the given registry.

    Args:
        registry: The registry to use for the reflection server.
        encoding: The text encoding to use; default 'utf-8'.

    Returns:
        A ReflectionServer class configured with the given registry.
    """

    class ReflectionServer(BaseHTTPRequestHandler):
        """HTTP request handler for the Genkit reflection API.

        This handler provides endpoints for inspecting and interacting with
        registered Genkit actions during development.
        """

        def log_message(self, format, *args):
            if not quiet:
                message = format % args
                logger.debug(
                    f'{self.address_string()} - - [{self.log_date_time_string()}] {message.translate(self._control_char_table)}'
                )

        def do_GET(self) -> None:  # noqa: N802
            """Handle GET requests to the reflection API.

            Endpoints:
                - /api/__health: Returns 200 OK if the server is healthy
                - /api/actions: Returns JSON describing all registered actions

            For the /api/actions endpoint, returns a JSON object mapping action
            keys to their metadata, including input/output schemas.
            """
            parsed_url = urllib.parse.urlparse(self.path)
            if parsed_url.path == '/api/__health':
                query_params = urllib.parse.parse_qs(parsed_url.query)
                expected_id = query_params.get('id', [None])[0]
                if expected_id is not None and expected_id != id:
                    self.send_response(500)
                    self.end_headers()
                    return

                self.send_response(200, 'OK')
                self.end_headers()

            elif parsed_url.path == '/api/actions':

                async def get_actions():
                    registered = _list_registered_actions(registry)
                    metas = await registry.list_actions()
                    return _build_actions_payload(registered_actions=registered, plugin_metas=metas)

                actions = run_async(loop, get_actions)
                self.send_response(200)
                self.send_header('content-type', 'application/json')
                self.end_headers()
                self.wfile.write(bytes(json.dumps(actions), encoding))
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            """Handle POST requests to the reflection API.

            Flow:
                1. Reads and validates the request payload
                2. Looks up the requested action
                3. Executes the action with the provided input
                4. Returns the action result as JSON with trace ID

            The response format varies based on whether the action returns a
            Pydantic model or a plain value.
            """
            if self.path == '/api/notify':
                self.send_response(200)
                self.end_headers()

            elif self.path.startswith('/api/runAction'):
                content_len = int(self.headers.get('content-length') or 0)
                post_body = self.rfile.read(content_len)
                payload = json.loads(post_body.decode(encoding=encoding))

                # Use async resolve_action_by_key
                async def get_action():
                    return await registry.resolve_action_by_key(payload['key'])

                action = run_async(loop, get_action)
                payload.get('input')
                context = payload['context'] if 'context' in payload else {}

                query = urllib.parse.urlparse(self.path).query
                query_params = urllib.parse.parse_qs(query)
                stream = query_params.get('stream', ['false'])[0] == 'true'
                if stream:

                    def send_chunk(chunk):
                        chunk_json = dump_json(chunk)
                        self.wfile.write(
                            bytes(
                                chunk_json,
                                encoding,
                            )
                        )
                        self.wfile.write(bytes('\n', encoding))
                        self.wfile.flush()  # Flush immediately for streaming

                    self.send_response(200)
                    self.send_header('x-genkit-version', DEFAULT_GENKIT_VERSION)
                    # TODO: Since each event being sent down the wire is a JSON
                    # chunk, shouldn't this be set to text/event-stream?
                    self.send_header('content-type', 'application/json')
                    self.end_headers()

                    try:

                        async def run_fn():
                            return await action.arun_raw(
                                raw_input=payload.get('input'),
                                on_chunk=send_chunk,
                                context=context,
                            )

                        output = run_async(loop, run_fn)

                        self.wfile.write(
                            bytes(
                                json.dumps({
                                    'result': dump_dict(output.response),
                                    'telemetry': {'traceId': output.trace_id},
                                }),
                                encoding,
                            )
                        )
                    except Exception as e:
                        # Since we're streaming, the headers have already been
                        # sent as a 200 OK, but we must indicate an error
                        # regardless.
                        error_response = get_reflection_json(e).model_dump(by_alias=True)
                        logger.error('Error streaming action', error=error_response)
                        if 'message' in error_response:
                            logger.error(error_response['message'])
                        if 'details' in error_response and 'stack' in error_response['details']:
                            logger.error(error_response['details']['stack'])
                        self.wfile.write(bytes(json.dumps({'error': error_response}), encoding))
                else:
                    try:

                        async def run_fn():
                            return await action.arun_raw(raw_input=payload.get('input'), context=context)

                        output = run_async(loop, run_fn)

                        self.send_response(200)
                        self.send_header('x-genkit-version', DEFAULT_GENKIT_VERSION)
                        self.send_header('content-type', 'application/json')
                        self.end_headers()

                        self.wfile.write(
                            bytes(
                                json.dumps({
                                    'result': dump_dict(output.response),
                                    'telemetry': {'traceId': output.trace_id},
                                }),
                                encoding,
                            )
                        )
                    except Exception as e:
                        # We aren't streaming here so send a JSON-encoded 500
                        # internal server error response.
                        error_response = get_reflection_json(e).model_dump(by_alias=True)
                        logger.error(f'Error running action {action.name}')
                        if 'message' in error_response:
                            logger.error(error_response['message'])
                        if 'details' in error_response and 'stack' in error_response['details']:
                            logger.error(error_response['details']['stack'])

                        self.send_response(500)
                        self.send_header('x-genkit-version', DEFAULT_GENKIT_VERSION)
                        self.send_header('content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(bytes(json.dumps(error_response), encoding))

    return ReflectionServer


def create_reflection_asgi_app(
    registry: Registry,
    on_app_startup: LifespanHandler | None = None,
    on_app_shutdown: LifespanHandler | None = None,
    version: str = DEFAULT_GENKIT_VERSION,
    encoding: str = 'utf-8',
) -> Application:
    """Create and return a ASGI application for the Genkit reflection API.

    Caveats:

        The reflection API server predates the flows server implementation and
        differs in the protocol it uses to interface with the Dev UI. The
        streaming protocol uses unadorned JSON per streamed chunk. This may
        change in the future to use Server-Sent Events (SSE).

    Key endpoints:

        | Method | Path                | Handler               |
        |--------|---------------------|-----------------------|
        | GET    | /api/__health       | Health check          |
        | GET    | /api/actions        | List actions          |
        | POST   | /api/__quitquitquit | Trigger shutdown      |
        | POST   | /api/notify         | Handle notification   |
        | POST   | /api/runAction      | Run action (streaming)|

    Args:
        registry: The registry to use for the reflection server.
        on_app_startup: Optional callback to execute when the app's
            lifespan starts. Must be an async function.
        on_app_shutdown: Optional callback to execute when the app's
            lifespan ends. Must be an async function.
        version: The version string to use when setting the value of
            the X-GENKIT-VERSION HTTP header.
        encoding: The text encoding to use; default 'utf-8'.

    Returns:
        An ASGI application configured with the given registry.
    """

    async def handle_health_check(request: Request) -> JSONResponse:
        """Handle health check requests.

        Args:
            request: The Starlette request object.

        Returns:
            A JSON response with status code 200.
        """
        return JSONResponse(content={'status': 'OK'})

    async def handle_terminate(request: Request) -> JSONResponse:
        """Handle the quit endpoint.

        Args:
            request: The Starlette request object.

        Returns:
            An empty JSON response with status code 200.
        """
        await logger.ainfo('Shutting down servers...')
        terminate_all_servers()
        return JSONResponse(content={'status': 'OK'})

    async def handle_list_actions(request: Request) -> JSONResponse:
        """Handle the request for listing available actions.

        Args:
            request: The Starlette request object.

        Returns:
            A JSON response containing all serializable actions.
        """
        registered = _list_registered_actions(registry)
        metas = await registry.list_actions()
        actions = _build_actions_payload(registered_actions=registered, plugin_metas=metas)

        return JSONResponse(
            content=actions,
            status_code=200,
            headers={'x-genkit-version': version},
        )

    async def handle_notify(request: Request) -> JSONResponse:
        """Handle the notification endpoint.

        Args:
            request: The Starlette request object.

        Returns:
            An empty JSON response with status code 200.
        """
        return JSONResponse(
            content={},
            status_code=200,
            headers={'x-genkit-version': version},
        )

    async def handle_run_action(
        request: Request,
    ) -> JSONResponse | StreamingResponse:
        """Handle the runAction endpoint for executing registered actions.

        Flow:
        1. Reads and validates the request payload
        2. Looks up the requested action
        3. Executes the action with the provided input
        4. Returns the action result as JSON with trace ID

        Args:
            request: The Starlette request object.

        Returns:
            A JSON or StreamingResponse with the action result, or an error
            response.
        """
        # Get the action using async resolve.
        payload = await request.json()
        action = await registry.resolve_action_by_key(payload['key'])
        if action is None:
            return JSONResponse(
                content={'error': f'Action not found: {payload["key"]}'},
                status_code=404,
            )

        # Run the action.
        context = payload.get('context', {})
        action_input = payload.get('input')
        stream = is_streaming_requested(request)
        handler = run_streaming_action if stream else run_standard_action
        return await handler(action, payload, action_input, context, version)

    async def run_streaming_action(
        action: Action,
        payload: dict[str, Any],
        action_input: Any,
        context: dict[str, Any],
        version: str,
    ) -> StreamingResponse | JSONResponse:
        """Handle streaming action execution for Starlette.

        Args:
            action: The action to execute.
            payload: Request payload with input data.
            context: Execution context.
            version: The Genkit version header value.

        Returns:
            A StreamingResponse with JSON chunks containing result or error
            events.
        """
        # Use a queue to pass chunks from the callback to the generator
        chunk_queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def run_action_task():
            """Run the action and put chunks on the queue."""
            try:

                def send_chunk(chunk):
                    """Callback that puts chunks on the queue."""
                    out = dump_json(chunk)
                    chunk_queue.put_nowait(f'{out}\n')

                output = await action.arun_raw(
                    raw_input=payload.get('input'),
                    on_chunk=send_chunk,
                    context=context,
                )
                final_response = {
                    'result': dump_dict(output.response),
                    'telemetry': {'traceId': output.trace_id},
                }
                chunk_queue.put_nowait(json.dumps(final_response))

            except Exception as e:
                error_response = get_reflection_json(e).model_dump(by_alias=True)
                logger.error(
                    'Error streaming action',
                    error=error_response,
                )
                # Error response also should not have trailing newline (final message)
                chunk_queue.put_nowait(json.dumps(error_response))

            finally:
                # Signal end of stream
                chunk_queue.put_nowait(None)

        async def stream_generator() -> AsyncGenerator[str, None]:
            """Yield chunks from the queue as they arrive."""
            # Start the action task
            task = asyncio.create_task(run_action_task())

            try:
                while True:
                    chunk = await chunk_queue.get()
                    if chunk is None:
                        break
                    yield chunk
            finally:
                # Ensure task is cleaned up
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

        return StreamingResponse(
            stream_generator(),
            # Reflection server uses text/plain for streaming (not SSE format)
            # to match Go implementation
            media_type='text/plain',
            headers={
                'x-genkit-version': version,
                'Transfer-Encoding': 'chunked',
            },
        )

    async def run_standard_action(
        action: Action,
        payload: dict[str, Any],
        action_input: Any,
        context: dict[str, Any],
        version: str,
    ) -> JSONResponse:
        """Handle standard (non-streaming) action execution for Starlette.

        Args:
            action: The action to execute.
            payload: Request payload with input data.
            context: Execution context.
            version: The Genkit version header value.

        Returns:
            A JSONResponse with the action result or error.
        """
        try:
            output = await action.arun_raw(raw_input=payload.get('input'), context=context)
            response = {
                'result': dump_dict(output.response),
                'telemetry': {'traceId': output.trace_id},
            }
            return JSONResponse(
                content=response,
                status_code=200,
                headers={'x-genkit-version': version},
            )
        except Exception as e:
            error_response = get_reflection_json(e).model_dump(by_alias=True)
            logger.error('Error executing action', error=error_response)
            return JSONResponse(
                content=error_response,
                status_code=500,
            )

    return Starlette(
        routes=[
            Route('/api/__health', handle_health_check, methods=['GET']),
            Route('/api/__quitquitquit', handle_terminate, methods=['POST']),
            Route('/api/actions', handle_list_actions, methods=['GET']),
            Route('/api/notify', handle_notify, methods=['POST']),
            Route('/api/runAction', handle_run_action, methods=['POST']),
        ],
        middleware=[
            Middleware(
                CORSMiddleware,
                allow_origins=['*'],
                allow_methods=['*'],
                allow_headers=['*'],
            )
        ],
        on_startup=[on_app_startup] if on_app_startup else [],
        on_shutdown=[on_app_shutdown] if on_app_shutdown else [],
    )
