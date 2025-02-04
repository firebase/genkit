# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


import json

from http.server import BaseHTTPRequestHandler
from pydantic import BaseModel

from genkit.core.registry import Registry


def MakeReflectionServer(registry: Registry):
    class ReflectionServer(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/api/__health':
                self.send_response(200)

            elif self.path == '/api/actions':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()

                actions = {}
                for type in registry.actions:
                    for name in registry.actions[type]:
                        action = registry.lookup_action(type, name)
                        key = f'/{type}/{name}'
                        actions[key] = {
                            'key': key,
                            'name': action.name,
                            'inputSchema': action.inputSchema,
                            'outputSchema': action.outputSchema,
                            'metadata': action.metadata,
                        }

                self.wfile.write(bytes(json.dumps(actions), 'utf-8'))

            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            if self.path == '/api/notify':
                self.send_response(200)
                self.end_headers()

            elif self.path == '/api/runAction':
                content_len = int(self.headers.get('Content-Length'))
                post_body = self.rfile.read(content_len)
                payload = json.loads(post_body.decode(encoding='utf-8'))
                print(payload)
                action = registry.lookup_by_absolute_name(payload['key'])
                if '/flow/' in payload['key']:
                    input = action.inputType.validate_python(
                        payload['input']['start']['input']
                    )
                else:
                    input = action.inputType.validate_python(payload['input'])

                output = action.fn(input)

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
                            + output.traceId
                            + '"}',
                            'utf-8',
                        )
                    )
                else:
                    self.wfile.write(
                        bytes(
                            json.dumps(
                                {
                                    'result': output.response,
                                    'telemetry': {'traceId': output.traceId},
                                }
                            ),
                            'utf-8',
                        )
                    )

            else:
                self.send_response(404)
                self.end_headers()

    return ReflectionServer
