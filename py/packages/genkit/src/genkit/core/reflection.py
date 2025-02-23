# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""Development API for inspecting and interacting with Genkit.

This module provides a reflection API server for inspection and interaction
during development. It exposes endpoints for health checks, action discovery,
and action execution.
"""

import json
import asyncio
import urllib.parse
from http.server import BaseHTTPRequestHandler
from genkit.core.constants import DEFAULT_GENKIT_VERSION
from genkit.core.headers import HTTPHeader
from genkit.core.registry import Registry
from typing import Any
from .utils import dump_json


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
                self.send_header(HTTPHeader.CONTENT_TYPE, 'application/json')
                self.end_headers()

                actions = {}
                for action_type in registry.actions:
                    for name in registry.actions[action_type]:
                        action = registry.lookup_action(action_type, name)
                        key = f'/{action_type.value}/{name}'
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

            elif self.path.startswith('/api/runAction'):
                content_len = int(
                    self.headers.get(HTTPHeader.CONTENT_LENGTH) or 0
                )
                post_body = self.rfile.read(content_len)
                payload = json.loads(post_body.decode(encoding=encoding))
                action = registry.lookup_action_by_key(payload['key'])
                context = payload['context'] if 'context' in payload else {}

                query = urllib.parse.urlparse(self.path).query
                query = urllib.parse.parse_qs(query)
                if 'stream' in query != None and query['stream'][0] == 'true':
                    def send_chunk(chunk):
                        self.wfile.write(
                            bytes(
                                dump_json(chunk),
                                encoding,
                            )
                        )
                        self.wfile.write(bytes("\n", encoding))

                    self.send_response(200)
                    self.send_header(HTTPHeader.X_GENKIT_VERSION, '0.0.1')
                    self.send_header(HTTPHeader.CONTENT_TYPE,
                                     'application/json')
                    self.end_headers()

                    output = asyncio.run(action.arun_raw(
                        raw_input=payload['input'], on_chunk=send_chunk, context=context))
                    self.wfile.write(
                        bytes(
                            json.dumps(
                                {
                                    'result': dump_json(output.response),
                                    'telemetry': {'traceId': output.trace_id},
                                }
                            ),
                            encoding,
                        )
                    )
                else:
                    output = asyncio.run(action.arun_raw(
                        raw_input=payload['input'], context=context))

                    self.send_response(200)
                    self.send_header(HTTPHeader.X_GENKIT_VERSION, '0.0.1')
                    self.send_header(HTTPHeader.CONTENT_TYPE,
                                     'application/json')
                    self.end_headers()

                    self.wfile.write(
                        bytes(
                            json.dumps(
                                {
                                    'result': dump_json(output.response),
                                    'telemetry': {'traceId': output.trace_id},
                                }
                            ),
                            encoding,
                        )
                    )

    return ReflectionServer
