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
from genkit.core.constants import DEFAULT_GENKIT_VERSION
from genkit.core.error import get_reflection_json
from genkit.core.registry import Registry
from genkit.web import asgi
from genkit.web.asgi import is_streaming_requested_from_scope
from genkit.web.manager.signals import terminate_all_servers
from genkit.web.requests import is_streaming_requested
from genkit.web.typing import (
    Application,
    HTTPScope,
    LifespanHandler,
    Receive,
    Scope,
    Send,
)

logger = structlog.get_logger(__name__)


def make_reflection_server(
    registry: Registry,
    loop: asyncio.AbstractEventLoop,
    encoding='utf-8',
    quiet=True,
):
    """Create and return a ReflectionServer class with the given registry.

    Args:
        registry: The registry to use for the reflection server.
        loop: The asyncio event loop to use for running async actions.
        encoding: The text encoding to use; default 'utf-8'.
        quiet: If True, suppress request logging.

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
                    f'{self.address_string()} - - '
                    f'[{self.log_date_time_string()}] '
                    f'{message.translate(self._control_char_table)}'
                )

        def do_GET(self) -> None:  # noqa: N802
            """Handle GET requests to the reflection API.

            Endpoints:
                - /api/__health: Returns 200 OK if the server is healthy
                - /api/actions: Returns JSON describing all registered actions

            For the /api/actions endpoint, returns a JSON object mapping action
            keys to their metadata, including input/output schemas.
            """
            if self.path == '/api/__health':
                self.send_response(200, 'OK')
                self.end_headers()

            elif self.path == '/api/actions':
                self.send_response(200)
                self.send_header('content-type', 'application/json')
                self.end_headers()
                actions = registry.list_serializable_actions()
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
                action = registry.lookup_action_by_key(payload['key'])
                context = payload['context'] if 'context' in payload else {}

                query = urllib.parse.urlparse(self.path).query
                query_params = urllib.parse.parse_qs(query)
                stream = query_params.get('stream', ['false'])[0] == 'true'
                if stream:

                    def send_chunk(chunk):
                        self.wfile.write(
                            bytes(
                                dump_json(chunk),
                                encoding,
                            )
                        )
                        self.wfile.write(bytes('\n', encoding))

                    self.send_response(200)
                    self.send_header('x-genkit-version', DEFAULT_GENKIT_VERSION)
                    # TODO: Since each event being sent down the wire is a JSON
                    # chunk, shouldn't this be set to text/event-stream?
                    self.send_header('content-type', 'application/json')
                    self.end_headers()

                    try:

                        async def run_fn():
                            return await action.arun_raw(
                                raw_input=payload['input'],
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
                            return await action.arun_raw(raw_input=payload['input'], context=context)

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


def create_reflection_starlette_asgi_app(
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
        return JSONResponse(
            content=registry.list_serializable_actions(),
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
        # Get the action.
        payload = await request.json()
        action = registry.lookup_action_by_key(payload['key'])
        if action is None:
            return JSONResponse(
                content={'error': f'Action not found: {payload["key"]}'},
                status_code=404,
            )

        # Run the action.
        context = payload.get('context', {})
        stream = is_streaming_requested(request)
        handler = run_streaming_action if stream else run_standard_action
        return await handler(action, payload, context, version)

    async def run_streaming_action(
        action: Action,
        payload: dict[str, Any],
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

        queue = asyncio.Queue[bytes | None]()

        # Synchronous callback to put chunks onto the queue
        def send_chunk_sync(chunk):
            try:
                # Wrap the intermediate chunk in a standard object structure
                chunk_obj = {'chunk': chunk}
                out = json.dumps(chunk_obj)
                # Add newline for intermediate chunks
                queue.put_nowait(f'{out}\\n'.encode(encoding))
            except Exception as e:
                # Log error putting chunk, but don't crash the callback
                logger.error('Error encoding/queueing stream chunk', error=e, chunk=chunk)

        async def run_action_and_get_result() -> tuple[Any | None, Exception | None]:
            """Run the action in the background and return result or exception."""
            output = None
            error = None
            try:
                output = await action.arun_raw(
                    raw_input=payload['input'],
                    on_chunk=send_chunk_sync,  # Pass the sync callback
                    context=context,
                )
            except Exception as e:
                error = e
            finally:
                # Signal the end of chunks from the action itself
                await queue.put(None)  # Use await put for the final signal
            return output, error

        async def stream_generator() -> AsyncGenerator[bytes, None]:
            """Yields chunks from the queue and the final result/error."""
            action_task = asyncio.create_task(run_action_and_get_result())
            final_output = None
            final_error = None

            while True:
                chunk = await queue.get()
                if chunk is None:  # Sentinel indicating action completion (intermediate chunks done)
                    queue.task_done()
                    break
                yield chunk
                queue.task_done()

            # Wait for the action task to fully complete and get its result/error
            final_output, final_error = await action_task

            if final_error:
                error_response = get_reflection_json(final_error).model_dump(by_alias=True)
                logger.error('Error streaming action', error=error_response)
                # Errors are newline-terminated
                yield f'{json.dumps(error_response)}\\n'.encode(encoding)
            elif final_output:
                # Send the final response WITH a trailing newline (matching Starlette?)
                final_response_obj = {
                    'result': dump_dict(final_output.response),
                    'telemetry': {'traceId': final_output.trace_id},
                }
                yield f'{json.dumps(final_response_obj)}\\n'.encode(encoding)
            # If no error and no output, yield nothing further

        return StreamingResponse(
            stream_generator(),
            # TODO: Should this be set to event-stream in the future?
            # media_type='text/event-stream',
            #
            # Apparently, the Genkit dev server uses
            # an older protocol that uses JSON chunks rather
            # than event streams.
            media_type='application/json',
            headers={'x-genkit-version': version},
        )

    async def run_standard_action(
        action: Action,
        payload: dict[str, Any],
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
            output = await action.arun_raw(raw_input=payload['input'], context=context)
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


class ReflectionApp:
    """ASGI application for the Genkit reflection API.

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
    """

    def __init__(
        self,
        registry: Registry,
        on_app_startup: LifespanHandler | None = None,
        on_app_shutdown: LifespanHandler | None = None,
        version: str = DEFAULT_GENKIT_VERSION,
        encoding: str = 'utf-8',
    ):
        """Initializes the ReflectionApp.

        Args:
            registry: The registry to use for the reflection server.
            on_app_startup: Optional callback for lifespan startup.
            on_app_shutdown: Optional callback for lifespan shutdown.
            version: The Genkit version string.
            encoding: The text encoding to use.
        """
        self._registry = registry
        self._on_app_startup = on_app_startup
        self._on_app_shutdown = on_app_shutdown
        self._version = version
        self._encoding = encoding

    async def send_genkit_json_response(self, send: Send, status: int, obj: dict[str, Any]) -> None:
        """Sends a JSON response with the Genkit version header."""
        return await asgi.send_response(
            send,
            status,
            [
                (b'content-type', b'application/json'),
                (b'x-genkit-version', self._version.encode(self._encoding)),
            ],
            json.dumps(obj).encode(self._encoding),
        )

    async def handle_health_check(self, scope: HTTPScope, receive: Receive, send: Send) -> None:
        """Handles the /api/__health endpoint."""
        return await self.send_genkit_json_response(
            send,
            200,
            {'status': 'OK'},
        )

    async def handle_list_actions(self, scope: HTTPScope, receive: Receive, send: Send) -> None:
        """Handles the /api/actions endpoint."""
        actions = self._registry.list_serializable_actions()
        return await self.send_genkit_json_response(
            send,
            200,
            actions,
        )

    async def handle_terminate(self, scope: HTTPScope, receive: Receive, send: Send) -> None:
        """Handles the /api/__quitquitquit endpoint."""
        await logger.ainfo('Shutting down servers...')
        terminate_all_servers()
        return await self.send_genkit_json_response(
            send,
            200,
            {'status': 'OK'},
        )

    async def handle_notify(self, scope: HTTPScope, receive: Receive, send: Send) -> None:
        """Handles the /api/notify endpoint."""
        await asgi.send_response(
            send,
            200,
            [
                (b'content-type', b'application/json'),
                (b'x-genkit-version', self._version.encode(self._encoding)),
            ],
            b'',
        )

    async def handle_run_action(self, scope: HTTPScope, receive: Receive, send: Send) -> None:
        """Handles the /api/runAction endpoint."""
        body = await asgi.read_body(receive)
        payload = json.loads(body.decode(self._encoding))
        action = self._registry.lookup_action_by_key(payload['key'])
        if action is None:
            return await self.send_genkit_json_response(
                send,
                404,
                {'error': f'Action not found: {payload["key"]}'},
            )

        context = payload.get('context', {})
        stream = is_streaming_requested_from_scope(scope)

        if stream:
            await self.handle_streaming_action(send, action, payload, context)
        else:
            await self.handle_standard_action(send, action, payload, context)

    async def handle_streaming_action(
        self, send: Send, action: Action, payload: dict[str, Any], context: dict[str, Any]
    ) -> None:
        """Handles the streaming response for /api/runAction using asyncio.Queue."""
        queue = asyncio.Queue[bytes | None]()

        # Synchronous callback to put chunks onto the queue
        def send_chunk_sync(chunk):
            try:
                # Wrap the intermediate chunk in a standard object structure
                chunk_obj = {'chunk': chunk}
                out = json.dumps(chunk_obj)
                # Add newline for intermediate chunks
                queue.put_nowait(f'{out}\\n'.encode(self._encoding))
            except Exception as e:
                # Log error putting chunk, but don't crash the callback
                logger.error('Error encoding/queueing stream chunk', error=e, chunk=chunk)

        async def run_action_and_get_result() -> tuple[Any | None, Exception | None]:
            """Run the action in the background and return result or exception."""
            output = None
            error = None
            try:
                output = await action.arun_raw(
                    raw_input=payload['input'],
                    on_chunk=send_chunk_sync,  # Pass the sync callback
                    context=context,
                )
            except Exception as e:
                error = e
            finally:
                # Signal the end of chunks from the action itself
                await queue.put(None)  # Use await put for the final signal
            return output, error

        async def stream_generator() -> AsyncGenerator[bytes, None]:
            """Yields chunks from the queue and the final result/error."""
            action_task = asyncio.create_task(run_action_and_get_result())
            final_output = None
            final_error = None

            while True:
                chunk = await queue.get()
                if chunk is None:  # Sentinel indicating action completion (intermediate chunks done)
                    queue.task_done()
                    break
                yield chunk
                queue.task_done()

            # Wait for the action task to fully complete and get its result/error
            final_output, final_error = await action_task

            if final_error:
                error_response = get_reflection_json(final_error).model_dump(by_alias=True)
                logger.error('Error streaming action', error=error_response)
                # Errors are newline-terminated
                yield f'{json.dumps(error_response)}\\n'.encode(self._encoding)
            elif final_output:
                # Send the final response WITH a trailing newline (matching Starlette?)
                final_response_obj = {
                    'result': dump_dict(final_output.response),
                    'telemetry': {'traceId': final_output.trace_id},
                }
                yield f'{json.dumps(final_response_obj)}\\n'.encode(self._encoding)
            # If no error and no output, yield nothing further

        # Now, send the response using the generator that reads from the queue
        await asgi.send_streaming_response(
            send,
            200,
            [
                (b'content-type', b'application/json'),
                (b'x-genkit-version', self._version.encode(self._encoding)),
            ],
            stream_generator(),
        )

    async def handle_standard_action(
        self, send: Send, action: Action, payload: dict[str, Any], context: dict[str, Any]
    ) -> None:
        """Handles the standard (non-streaming) response for /api/runAction."""
        try:
            output = await action.arun_raw(raw_input=payload['input'], context=context)
            response = {
                'result': dump_dict(output.response),
                'telemetry': {'traceId': output.trace_id},
            }
            return await self.send_genkit_json_response(
                send,
                200,
                response,
            )
        except Exception as e:
            error_response = get_reflection_json(e).model_dump(by_alias=True)
            logger.error('Error executing action', error=error_response)
            return await self.send_genkit_json_response(
                send,
                500,
                error_response,
            )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI application entry point."""
        if scope['type'] == 'lifespan':
            while True:
                message = await receive()
                if message['type'] == 'lifespan.startup':
                    if self._on_app_startup:
                        try:
                            await self._on_app_startup(scope, receive, send)  # Pass args if handler expects them
                            await send({'type': 'lifespan.startup.complete'})
                        except Exception as e:
                            await logger.aexception('Error during ASGI startup', exc_info=e)
                            await send({'type': 'lifespan.startup.failed', 'message': str(e)})
                            return  # Exit lifespan loop on startup failure
                    else:
                        await send({'type': 'lifespan.startup.complete'})
                elif message['type'] == 'lifespan.shutdown':
                    if self._on_app_shutdown:
                        try:
                            await self._on_app_shutdown(scope, receive, send)  # Pass args if handler expects them
                            await send({'type': 'lifespan.shutdown.complete'})
                        except Exception as e:
                            await logger.aexception('Error during ASGI shutdown', exc_info=e)
                            await send({'type': 'lifespan.shutdown.failed', 'message': str(e)})
                    else:
                        await send({'type': 'lifespan.shutdown.complete'})
                    return  # Exit lifespan loop after shutdown

        if scope['type'] != 'http':
            await logger.awarn('Received non-HTTP message', scope_type=scope['type'])
            # Optionally send a 400 Bad Request
            return

        path = scope['path']
        method = scope['method']

        handler = None
        match method, path:
            case 'GET', '/api/__health':
                handler = self.handle_health_check
            case 'GET', '/api/actions':
                handler = self.handle_list_actions
            case 'POST', '/api/__quitquitquit':
                handler = self.handle_terminate
            case 'POST', '/api/notify':
                handler = self.handle_notify
            case 'POST', '/api/runAction':
                handler = self.handle_run_action

        if handler:
            await handler(scope, receive, send)
        else:
            # Use send_genkit_json_response for consistency
            await self.send_genkit_json_response(send, 404, {'error': 'Not Found'})


def create_reflection_asgi_app(
    registry: Registry,
    on_app_startup: LifespanHandler | None = None,
    on_app_shutdown: LifespanHandler | None = None,
    version: str = DEFAULT_GENKIT_VERSION,
    encoding: str = 'utf-8',
) -> Application:
    """Creates a pure ASGI application instance for the Genkit reflection API.

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
        An instance of PureReflectionASGIApp conforming to the ASGI protocol.
    """
    return ReflectionApp(
        registry=registry,
        on_app_startup=on_app_startup,
        on_app_shutdown=on_app_shutdown,
        version=version,
        encoding=encoding,
    )
