# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""Development API for inspecting and interacting with Genkit.

This module provides a reflection API server for inspection and interaction
during development. It exposes endpoints for health checks, action discovery,
and action execution.
"""

from __future__ import annotations

import asyncio
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler
from typing import Any

import structlog

from genkit.codec import dump_dict, dump_json
from genkit.core.action import Action
from genkit.core.constants import DEFAULT_GENKIT_VERSION
from genkit.core.error import get_callable_json
from genkit.core.registry import Registry
from genkit.web import (
    create_asgi_app,
    extract_query_params,
    is_query_flag_enabled,
)
from genkit.web.enums import ContentType, HTTPHeader
from genkit.web.handlers import handle_health_check
from genkit.web.requests import read_json_body
from genkit.web.responses import json_chunk_response
from genkit.web.typing import (
    Application,
    HTTPScope,
    LifespanHandler,
    QueryParams,
    Receive,
    Route,
    Routes,
    Send,
)

logger = structlog.get_logger(__name__)


def is_streaming_requested(query_params: QueryParams) -> bool:
    """Check if streaming is requested in the query parameters.

    Args:
        query_params: Dictionary containing parsed query parameters.

    Returns:
        True if streaming is requested, False otherwise.
    """
    return is_query_flag_enabled(query_params, 'stream')


def make_reflection_server(registry: Registry, encoding='utf-8'):
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
                self.send_header(HTTPHeader.CONTENT_TYPE, 'application/json')
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
                content_len = int(
                    self.headers.get(HTTPHeader.CONTENT_LENGTH) or 0
                )
                post_body = self.rfile.read(content_len)
                payload = json.loads(post_body.decode(encoding=encoding))
                action = registry.lookup_action_by_key(payload['key'])
                context = payload['context'] if 'context' in payload else {}

                query = urllib.parse.urlparse(self.path).query
                query_params = urllib.parse.parse_qs(query)
                if is_streaming_requested(query_params):

                    def send_chunk(chunk):
                        self.wfile.write(
                            bytes(
                                dump_json(chunk),
                                encoding,
                            )
                        )
                        self.wfile.write(bytes('\n', encoding))

                    self.send_response(200)
                    self.send_header(
                        HTTPHeader.X_GENKIT_VERSION, DEFAULT_GENKIT_VERSION
                    )
                    self.send_header(
                        HTTPHeader.CONTENT_TYPE, 'application/json'
                    )
                    self.end_headers()

                    try:
                        output = asyncio.run(
                            action.arun_raw(
                                raw_input=payload['input'],
                                on_chunk=send_chunk,
                                context=context,
                            )
                        )
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
                        error_response = get_callable_json(e).model_dump(
                            by_alias=True
                        )
                        logger.error(
                            'Error streaming action', error=error_response
                        )

                        # Since we're streaming, we must do special error
                        # handling here -- the headers are already sent.
                        self.wfile.write(
                            bytes(
                                json.dumps({'error': error_response}), encoding
                            )
                        )
                else:
                    try:
                        output = asyncio.run(
                            action.arun_raw(
                                raw_input=payload['input'], context=context
                            )
                        )

                        self.send_response(200)
                        self.send_header(
                            HTTPHeader.X_GENKIT_VERSION, DEFAULT_GENKIT_VERSION
                        )
                        self.send_header(
                            HTTPHeader.CONTENT_TYPE, 'application/json'
                        )
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
                        # Since we're streaming, we must do special error
                        # handling here -- the headers are already sent.
                        error_response = get_callable_json(e).model_dump(
                            by_alias=True
                        )
                        logger.error(
                            'Error streaming action', error=error_response
                        )

                        self.send_response(500)
                        self.send_header(
                            HTTPHeader.X_GENKIT_VERSION, DEFAULT_GENKIT_VERSION
                        )
                        self.send_header(
                            HTTPHeader.CONTENT_TYPE, 'application/json'
                        )
                        self.end_headers()
                        self.wfile.write(
                            bytes(json.dumps(error_response), encoding)
                        )

    return ReflectionServer


def create_reflection_asgi_app(
    registry: Registry,
    on_app_startup: LifespanHandler | None = None,
    on_app_shutdown: LifespanHandler | None = None,
    version=DEFAULT_GENKIT_VERSION,
    encoding='utf-8',
) -> Application:
    """Create and return an ASGI application for the Genkit reflection API.

    Key endpoints:

        | Method | Path           | Handler               |
        |--------|----------------|-----------------------|
        | GET    | /api/runAction | handle_run_action     |
        | POST   | /api/actions   | handle_list_actions   |
        | GET    | /api/__health  | handle_health_check   |
        | POST   | /api/notify    | handle_notify         |

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
    # TODO: Add middleware support and implement a logging middleware.
    # NOTE: We don't take on a dependency on third-party libraries such as
    # starlette, fastapi, or litestar for this server, to keep the dependencies
    # minimal for the end-user.

    async def handle_list_actions(
        scope: HTTPScope, receive: Receive, send: Send
    ) -> None:
        """Handle the GET request for listing available actions.

        Args:
            scope: ASGI HTTP scope.
            receive: ASGI receive function.
            send: ASGI send function.
            query_params: Parsed query parameters.
        """
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                (b'content-type', b'application/json'),
            ],
        })

        actions = registry.list_serializable_actions()
        body = json.dumps(actions).encode(encoding)
        await send({
            'type': 'http.response.body',
            'body': body,
        })

    async def handle_notify(
        scope: HTTPScope, receive: Receive, send: Send
    ) -> None:
        """Handle the POST notification endpoint.

        Args:
            scope: ASGI HTTP scope.
            receive: ASGI receive function.
            send: ASGI send function.
        """
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [],
        })
        await send({
            'type': 'http.response.body',
            'body': b'',
        })

    async def handle_run_action(
        scope: HTTPScope, receive: Receive, send: Send
    ) -> None:
        """Handle the runAction endpoint for executing registered actions.

        Flow:

        1. Reads and validates the request payload
        2. Looks up the requested action
        3. Executes the action with the provided input
        4. Returns the action result as JSON with trace ID

        The response format varies based on whether the action returns a
        Pydantic model or a plain value.

        Args:
            scope: ASGI HTTP scope.
            receive: ASGI receive function.
            send: ASGI send function.
        """
        payload = await read_json_body(receive, encoding)
        action = registry.lookup_action_by_key(payload['key'])

        if action is None:
            await send({
                'type': 'http.response.start',
                'status': 404,
                'headers': [
                    (
                        HTTPHeader.CONTENT_TYPE,
                        ContentType.APPLICATION_JSON,
                    ),
                ],
            })
            error_message = {'error': f'Action not found: {payload["key"]}'}
            await send({
                'type': 'http.response.body',
                'body': json.dumps(error_message).encode(encoding),
            })
            return

        context = payload.get('context', {})
        headers = [
            (b'content-type', b'application/json'),
            (HTTPHeader.X_GENKIT_VERSION.encode(), version.encode()),
        ]
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': headers,
        })

        if is_streaming_requested(extract_query_params(scope, encoding)):
            await handle_streaming_action(
                scope, receive, send, action, payload, context
            )
        else:
            await handle_standard_action(
                scope, receive, send, action, payload, context
            )

    async def handle_streaming_action(
        scope: HTTPScope,
        receive: Receive,
        send: Send,
        action: Action,
        payload: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        """Handle streaming action execution.

        Args:
            scope: ASGI HTTP scope.
            receive: ASGI receive function.
            send: ASGI send function.
            action: The action to execute.
            payload: Request payload with input data.
            context: Execution context.

        Raises:
            Exception: Any exception raised by the action execution is caught,
                logged, and an error response is sent to the client. The error
                response is a JSON object with an 'error' field containing
                details about the exception.  The response is sent in the body
                and no more body is sent after that.
        """

        async def send_chunk(chunk):
            await send(json_chunk_response(chunk, encoding))

        try:
            output = await action.arun_raw(
                raw_input=payload['input'],
                on_chunk=send_chunk,
                context=context,
            )
            final_response = {
                'result': dump_dict(output.response),
                'telemetry': {'traceId': output.trace_id},
            }
            await send({
                'type': 'http.response.body',
                'body': json.dumps(final_response).encode(encoding),
                'more_body': False,
            })
        except Exception as e:
            error_response = get_callable_json(e).model_dump(by_alias=True)
            await logger.aerror('Error streaming action', error=error_response)
            await send({
                'type': 'http.response.body',
                'body': json.dumps({'error': error_response}).encode(encoding),
                'more_body': False,
            })

    async def handle_standard_action(
        scope: HTTPScope,
        receive: Receive,
        send: Send,
        action: Action,
        payload: dict[str, Any],
        context: dict[str, Any],
    ) -> None:
        """Handle standard (non-streaming) action execution.

        Args:
            scope: ASGI HTTP scope.
            receive: ASGI receive function.
            send: ASGI send function.
            action: The action to execute.
            payload: Request payload with input data.
            context: Execution context.

        Raises:
            Exception: Any exception raised by the action execution is caught,
                logged, and a 500 Internal Server Error response is sent to the
                client. The error response is a JSON object containing details
                about the exception, and is sent in the response body.
        """
        try:
            output = await action.arun_raw(
                raw_input=payload['input'], context=context
            )
            response = {
                'result': dump_dict(output.response),
                'telemetry': {'traceId': output.trace_id},
            }
            await send({
                'type': 'http.response.body',
                'body': json.dumps(response).encode(encoding),
                'more_body': False,
            })
        except Exception as e:
            error_response = get_callable_json(e).model_dump(by_alias=True)
            await logger.aerror('Error executing action', error=error_response)
            await send({
                'type': 'http.response.start',
                'status': 500,
                'headers': [
                    (b'content-type', b'application/json'),
                    (HTTPHeader.X_GENKIT_VERSION.encode(), version.encode()),
                ],
            })
            await send({
                'type': 'http.response.body',
                'body': json.dumps(error_response).encode(encoding),
            })

    routes: Routes = [
        Route('GET', '/api/__health', handle_health_check),
        Route('GET', '/api/actions', handle_list_actions),
        Route('POST', '/api/runAction', handle_run_action),
        Route('POST', '/api/notify', handle_notify),
    ]

    return create_asgi_app(routes, on_app_startup, on_app_shutdown)
