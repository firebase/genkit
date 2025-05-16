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

"""Flows API module for GenKit.

This module implements the Flows API server functionality for GenKit, providing
endpoints to execute both streaming and standard flows. The Flows API allows
clients to invoke registered flows over HTTP, with support for:

1. **Standard request/response flows**: Synchronous execution with a single
   response.

2. **Streaming flows**: Asynchronous execution that streams partial results to
   clients.

The module provides:

- An ASGI application factory (create_flows_asgi_app) that creates a Starlette
  application with appropriate routes.
- Request handlers for both streaming and standard flows.
- Proper error handling and response formatting.
- Context providers for request-specific execution contexts.
- Endpoints for health checks and flow execution, supporting both streaming and
  non-streaming responses.

## Example usage:

    ```python
    from genkit.core.flows import create_flows_asgi_app
    from genkit.core.registry import Registry

    # Create a registry with your flows
    registry = Registry()
    registry.register(my_flow, name='my_flow')

    # Create the ASGI app
    app = create_flows_asgi_app(registry)

    # Run with any ASGI server
    import uvicorn

    uvicorn.run(app, host='localhost', port=3400)
    ```

For a higher-level server implementation, see the FlowsServer class in
genkit.core.flow_server.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, Callable
from typing import Any

import structlog
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from genkit.codec import dump_dict
from genkit.core.action import Action
from genkit.core.constants import DEFAULT_GENKIT_VERSION
from genkit.core.error import get_callable_json
from genkit.core.registry import Registry
from genkit.web.requests import (
    is_streaming_requested,
)
from genkit.web.typing import (
    Application,
    LifespanHandler,
)

logger = structlog.get_logger(__name__)


# TODO: This is a work in progress and may change. Do not use.
def create_flows_asgi_app(
    registry: Registry,
    context_providers: list[Callable[..., Any]] | None = None,
    on_app_startup: LifespanHandler | None = None,
    on_app_shutdown: LifespanHandler | None = None,
    version: str = DEFAULT_GENKIT_VERSION,
) -> Application:
    """Create an ASGI application for flows.

    Args:
        registry: The registry to use for the flows server.
        context_providers: Optional list of context providers to process
            requests. Each provider is a callable that takes a context and
            request data and returns an enriched context.
        on_app_startup: Optional callback to execute when the app's
            lifespan starts. Must be an async function.
        on_app_shutdown: Optional callback to execute when the app's
            lifespan ends. Must be an async function.
        version: The version of the Genkit server to use.

    Returns:
        An ASGI application.
    """
    routes = []
    logger = structlog.get_logger(__name__)

    async def health_check(request: Request) -> JSONResponse:
        """Handle health check requests.

        Args:
            request: The Starlette request object.

        Returns:
            A JSON response with status code 200.
        """
        return JSONResponse(content={'status': 'OK'})

    async def handle_run_flows(
        request: Request,
    ) -> JSONResponse | EventSourceResponse:
        """Handle flow execution.

        Flow:
        1. Extracts flow name from the path
        2. Reads and validates the request payload
        3. Looks up the requested flow action
        4. Executes the flow with the provided input
        5. Returns the flow result as JSON

        Args:
            request: The Starlette request object.

        Returns:
            A JSON or EventSourceResponse with the flow result, or an error
            response.
        """
        flow_name = request.path_params.get('flow_name')
        if not flow_name:
            return JSONResponse(
                content={'error': 'Flow name not provided'},
                status_code=400,
            )

        try:
            # Look up the flow action.
            action = registry.lookup_action_by_key(flow_name)
            if action is None:
                await logger.aerror(
                    'Flow not found',
                    error=f'Flow not found: {flow_name}',
                )
                return JSONResponse(
                    content={'error': f'Flow not found: {flow_name}'},
                    status_code=404,
                )

            # Parse request body.
            try:
                input_data = {}
                if await request.body():
                    payload = await request.json()
                    input_data = payload.get('data', {})
            except json.JSONDecodeError as e:
                await logger.eerror(
                    'Invalid JSON',
                    error=f'Invalid JSON: {str(e)}',
                )
                return JSONResponse(
                    content={'error': f'Invalid JSON: {str(e)}'},
                    status_code=400,
                )

            # Set up context.
            ctx = {}
            if context_providers:
                headers = {k.lower(): v for k, v in request.headers.items()}
                request_data = {
                    'method': request.method,
                    'headers': headers,
                    'input': input_data,
                }

                for provider in context_providers:
                    try:
                        provider_ctx = await provider(request.app.state.context, request_data)
                        ctx.update(provider_ctx)
                    except Exception as e:
                        await logger.aerror(
                            'context provider error',
                            error=str(e),
                        )
                        return JSONResponse(
                            content={'error': f'Unauthorized: {str(e)}'},
                            status_code=401,
                        )

            # Run the flow.
            stream = is_streaming_requested(request)
            handler = handle_streaming_flow if stream else handle_standard_flow
            return await handler(action, input_data, ctx, version)
        except Exception as e:
            await logger.aerror('error executing flow', error=str(e))
            error_response = {'error': str(e)}
            return JSONResponse(
                content=error_response,
                status_code=500,
            )

    async def handle_streaming_flow(
        action: Action,
        input_data: dict,
        context: dict,
        version: str,
    ) -> EventSourceResponse:
        """Handle streaming flow execution.

        Args:
            action: The flow action to execute.
            input_data: Input data for the flow.
            context: Execution context.
            version: The Genkit version header value.

        Returns:
            An EventSourceResponse with the flow result or error.
        """

        async def stream_generator() -> AsyncGenerator[dict, None]:
            """Generate stream of data dictionaries for the SSE response."""
            chunks = []

            async def chunk_callback(chunk):
                chunks.append(chunk)
                yield {
                    'event': 'message',
                    'data': json.dumps({'message': chunk}),
                }

            try:
                output = await action.arun_raw(
                    raw_input=input_data,
                    on_chunk=chunk_callback,
                    context=context,
                )

                # Send final result.
                result = dump_dict(output.response)
                yield {
                    'event': 'result',
                    'data': json.dumps({'result': result}),
                }

            except Exception as e:
                error_msg = str(e)
                await logger.aerror('error in stream', error=error_msg)
                yield {
                    'event': 'error',
                    'data': json.dumps({
                        'error': {
                            'status': 'INTERNAL',
                            'message': 'stream flow error',
                            'details': error_msg,
                        }
                    }),
                }

        return EventSourceResponse(
            stream_generator(),
            headers={
                'x-genkit-version': version,
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
            },
        )

    async def handle_standard_flow(
        action: Action,
        input_data: Any,
        context: dict[str, Any],
        version: str,
    ) -> JSONResponse:
        """Handle standard (non-streaming) flow execution.

        Args:
            action: The flow action to execute.
            input_data: Input data for the flow.
            context: Execution context.
            version: The Genkit version header value.

        Returns:
            A JSONResponse with the flow result or error.
        """
        try:
            output = await action.arun_raw(raw_input=input_data, context=context)

            result = dump_dict(output.response)
            response = {'result': result}

            return JSONResponse(
                content=response,
                status_code=200,
                headers={'x-genkit-version': version},
            )
        except Exception as e:
            error_response = get_callable_json(e).model_dump(by_alias=True)
            await logger.aerror('error executing flow', error=error_response)
            return JSONResponse(
                content={'error': error_response},
                status_code=500,
            )

    routes = [
        Route('/__health', health_check, methods=['GET']),
        Route('/{flow_name:path}', handle_run_flows, methods=['POST']),
    ]

    app = Starlette(
        routes=routes,
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

    app.state.context = {}

    return app
