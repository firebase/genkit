# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""Development API for inspecting and interacting with Genkit.

This module provides a reflection API server for inspection and interaction
during development. It exposes endpoints for health checks, action discovery,
and action execution.
"""

import json
from http.server import BaseHTTPRequestHandler

from genkit.core.constants import DEFAULT_GENKIT_VERSION
from genkit.core.headers import HTTPHeader
from genkit.core.registry import Registry
from pydantic import BaseModel


def make_reflection_server(
    registry: Registry, version=DEFAULT_GENKIT_VERSION, encoding='utf-8'
):
    """Create and return a ReflectionServer class with the given registry.

    Args:
        registry: The registry to use for the reflection server.
        version: The version string to use when setting the value of
            the X-GENKIT-VERSION HTTP header.
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
                self.send_response(200)

            elif self.path == '/api/actions':
                self.send_response(200)
                self.send_header(HTTPHeader.ContentType, 'application/json')
                self.end_headers()

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

            elif self.path == '/api/runAction':
                content_len = int(
                    self.headers.get(HTTPHeader.ContentLength) or 0
                )
                post_body = self.rfile.read(content_len)
                payload = json.loads(post_body.decode(encoding=encoding))
                action = registry.lookup_action_by_key(payload['key'])
                if '/flow/' in payload['key']:
                    input_action = action.input_type.validate_python(
                        payload['input']['start']['input']
                    )
                else:
                    input_action = action.input_type.validate_python(
                        payload['input']
                    )

                output = action.fn(input_action)

                self.send_response(200)
                self.send_header(HTTPHeader.X_GENKIT_VERSION, version)
                self.send_header(HTTPHeader.CONTENT_TYPE, 'application/json')
                self.end_headers()

                if isinstance(output.response, BaseModel):
                    self.wfile.write(
                        bytes(
                            '{"result":  '
                            + output.response.model_dump_json()
                            + ', "traceId": "'
                            + output.trace_id
                            + '"}',
                            encoding,
                        )
                    )
                else:
                    self.wfile.write(
                        bytes(
                            json.dumps({
                                'result': output.response,
                                'telemetry': {'traceId': output.trace_id},
                            }),
                            encoding,
                        )
                    )

    return ReflectionServer
