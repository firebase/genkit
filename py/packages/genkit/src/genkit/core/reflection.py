# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Exposes an API for inspecting and interacting with Genkit in development."""

import json
from collections.abc import Callable
from typing import Any

from genkit.core.headers import HttpHeader
from genkit.core.registry import Registry
from pydantic import BaseModel

GENKIT_VERSION = '0.9.1'


async def json_response(
    body: Any, status: int = 200, headers: dict[str, str] | None = None
) -> tuple:
    """Helper to create JSON responses."""
    response_headers = [(b'content-type', b'application/json')]
    if headers:
        response_headers.extend(
            [(k.encode(), v.encode()) for k, v in headers.items()]
        )

    return {
        'type': 'http.response.start',
        'status': status,
        'headers': response_headers,
    }, {
        'type': 'http.response.body',
        'body': json.dumps(body).encode(),
    }


async def empty_response(status: int = 200) -> tuple:
    """Helper to create empty responses."""
    return {
        'type': 'http.response.start',
        'status': status,
        'headers': [],
    }, {
        'type': 'http.response.body',
        'body': b'',
    }


async def read_json_body(receive: Callable) -> dict:
    """Helper to read JSON request body."""
    body = b''
    more_body = True

    while more_body:
        message = await receive()
        body += message.get('body', b'')
        more_body = message.get('more_body', False)

    return json.loads(body) if body else {}


def make_reflection_server(registry: Registry) -> Callable:
    """Returns an asynchronous application for reflection API."""

    async def app(scope: dict, receive: Callable, send: Callable) -> None:
        if scope['type'] != 'http':
            return

        path = scope['path']
        method = scope['method']

        if path == '/api/__health' and method == 'GET':
            # Health check endpoint
            start, body = await empty_response(200)
            await send(start)
            await send(body)
            return

        if path == '/api/actions' and method == 'GET':
            # List all available actions
            actions = {}
            for action_type in registry.actions:
                for name in registry.actions[action_type]:
                    action = registry.lookup_action(action_type, name)
                    key = f'/{action_type}/{name}'
                    actions[key] = {
                        'key': key,
                        'name': action.name,
                        'inputSchema': action.input_schema,
                        'outputSchema': action.output_schema,
                        'metadata': action.metadata,
                    }
            start, body = await json_response(actions)
            await send(start)
            await send(body)
            return

        if path == '/api/notify' and method == 'POST':
            # Handle notifications
            start, body = await empty_response(200)
            await send(start)
            await send(body)
            return

        if path == '/api/runAction' and method == 'POST':
            # Run an action
            payload = await read_json_body(receive)
            key = payload['key']
            action = registry.lookup_action_by_key(key)

            if '/flow/' in key:
                iput = payload['input']['start']['input']
                input_action = action.input_type.validate_python(iput)
            else:
                input_action = action.input_type.validate_python(
                    payload['input']
                )

            output = action.fn(input_action)

            if isinstance(output.response, BaseModel):
                result = output.response.model_dump(by_alias=True)
                response_data = {
                    'result': result,
                    'traceId': output.trace_id,
                }
            else:
                response_data = {
                    'result': output.response,
                    'telemetry': {'traceId': output.trace_id},
                }

            start, body = await json_response(
                response_data,
                headers={HttpHeader.X_GENKIT_VERSION: GENKIT_VERSION},
            )
            await send(start)
            await send(body)
            return

        # Not found
        start, body = await json_response({'error': 'Not Found'}, status=404)
        await send(start)
        await send(body)

    return app
