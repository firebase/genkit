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

from pydantic import BaseModel, TypeAdapter
import json
import inspect
from typing import Union, List, Dict, Optional, Callable, Any
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import os
import datetime
import atexit

from .types import GenerateRequest, GenerateResponse, Message
from .registry import Registry, Action
from .reflection import MakeReflectionServer
from .tracing import tracer
from .model import ModelFn
from .prompt import PromptFn

Plugin = Callable[['Genkit'], None]


class Genkit:
    registry: Registry = Registry()

    def __init__(self, plugins: Optional[List[Plugin]] = None, model: Optional[str] = None) -> None:
        self.model = model
        if "GENKIT_ENV" in os.environ and os.environ["GENKIT_ENV"] == "dev":
            cwd = os.getcwd()
            runtimesDir = os.path.join(cwd, ".genkit/runtimes")
            current_datetime = datetime.datetime.now()
            if not os.path.exists(runtimesDir):
                os.makedirs(runtimesDir)
            runtime_file_path = os.path.join(
                runtimesDir, f"{current_datetime.isoformat()}.json")
            rf = open(runtime_file_path, "w")
            rf.write(json.dumps({
                "id": f"{os.getpid()}",
                "pid": os.getpid(),
                "reflectionServerUrl": "http://localhost:3100",
                "timestamp": f"{current_datetime.isoformat()}"
            }))
            rf.close()

            def delete_runtime_file():
                os.remove(runtime_file_path)
            atexit.register(delete_runtime_file)

            threading.Thread(target=self.start_server).start()

        if plugins != None:
            for plugin in plugins:
                plugin(self)

    def start_server(self):
        httpd = HTTPServer(("127.0.0.1", 3100),
                           MakeReflectionServer(self.registry))
        httpd.serve_forever()

    def generate(self,
                 model: Optional[str] = None,
                 prompt: Optional[Union[str]] = None,
                 messages: Optional[List[Message]] = None,
                 system: Optional[Union[str]] = None,
                 tools: Optional[List[str]] = None,
                 ) -> GenerateResponse:
        model = model if model != None else self.model
        if model == None:
            raise Exception('no model configured')

        modelAction = self.registry.lookup_action('model', model)

        return modelAction.fn(GenerateRequest(messages=messages)).response

    def flow(self, name: Optional[str] = None):
        def wrapper(func):
            flowName = name if name != None else func.__name__
            action = Action(name=flowName, type='flow', fn=func, spanMetadata={
                            'genkit:metadata:flow:name': flowName})
            self.registry.register_action(type="flow", name=flowName, action=action)

            def decorator(*args, **kwargs):
                return action.fn(*args, **kwargs).response
            return decorator
        return wrapper

    def define_model(self, name: str, fn: ModelFn, metadata: Optional[Dict[str, Any]] = None):
        action = Action(name=name, type='model', fn=fn, metadata=metadata)
        self.registry.register_action('model', name, action)

    def define_prompt(self, name: str, fn: PromptFn, model: Optional[str] = None):
        def prompt(input: Optional[any] = None) -> GenerateResponse:
            req = fn(input)
            return self.generate(messages=req.messages, model=model)
        action = Action('model', name, prompt)
        self.registry.register_action('model', name, action)

        def wrapper(input: Optional[any] = None):
            return action.fn(input)
        return wrapper
