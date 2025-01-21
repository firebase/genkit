# Copyright 2022 Google Inc.
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

import json
from typing import Union, List, Dict, Optional, Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from pydantic import BaseModel

from .registry import Registry


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
                payload = json.loads(post_body.decode(encoding="utf-8"))
                print(payload)
                action = registry.lookup_by_absolute_name(payload['key'])
                if "/flow/" in payload['key']:
                    input = action.inputType.validate_python(
                        payload['input']['start']['input'])
                else:
                    input = action.inputType.validate_python(payload['input'])

                output = action.fn(input)

                self.send_response(200)
                self.send_header('x-genkit-version', '0.9.1')
                self.send_header('Content-type', 'application/json')
                self.end_headers()

                if isinstance(output.response, BaseModel):
                    self.wfile.write(
                        bytes("{\"result\":  " + output.response.model_dump_json() + ", \"traceId\": \"" + output.traceId + "\"}", 'utf-8'))
                else:
                    self.wfile.write(
                        bytes(json.dumps({"result": output.response, "telemetry": {"traceId": output.traceId}}), 'utf-8'))

            else:
                self.send_response(404)
                self.end_headers()

    return ReflectionServer
