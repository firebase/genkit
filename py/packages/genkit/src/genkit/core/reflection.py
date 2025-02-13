# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""Exposes an API for inspecting and interacting with Genkit in development."""

import json
from http.server import BaseHTTPRequestHandler

from genkit.core.registry import Registry
from pydantic import BaseModel


def make_reflection_server(registry: Registry):
    """Returns a ReflectionServer class."""

    class ReflectionServer(BaseHTTPRequestHandler):
        """Exposes an API for local development."""

        ENCODING = 'utf-8'

        def do_GET(self) -> None:  # noqa: N802
            """Handles GET requests."""
            if self.path == '/api/__health':
                self.send_response(200)

            elif self.path == '/api/actions':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
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

                self.wfile.write(bytes(json.dumps(actions), self.ENCODING))

            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            """Handles POST requests."""
            if self.path == '/api/notify':
                self.send_response(200)
                self.end_headers()

            elif self.path == '/api/runAction':
                content_len = int(self.headers.get('Content-Length') or 0)
                post_body = self.rfile.read(content_len)
                payload = json.loads(post_body.decode(encoding=self.ENCODING))
                print(payload)
                action = registry.lookup_by_absolute_name(payload['key'])
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
                self.send_header('x-genkit-version', '0.9.1')
                self.send_header('Content-type', 'application/json')
                self.end_headers()

                if isinstance(output.response, BaseModel):
                    self.wfile.write(
                        bytes(
                            '{"result":  '
                            + output.response.model_dump_json()
                            + ', "traceId": "'
                            + output.trace_id
                            + '"}',
                            self.ENCODING,
                        )
                    )
                else:
                    self.wfile.write(
                        bytes(
                            json.dumps(
                                {
                                    'result': output.response,
                                    'telemetry': {'traceId': output.trace_id},
                                }
                            ),
                            self.ENCODING,
                        )
                    )

            else:
                self.send_response(404)
                self.end_headers()

    return ReflectionServer
