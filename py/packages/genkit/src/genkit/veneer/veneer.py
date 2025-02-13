"""A layer that provides a flat library structure for a user.

Copyright 2025 Google LLC
SPDX-License-Identifier: Apache-2.0
"""

import atexit
import datetime
import json
import os
import threading
from collections.abc import Callable
from http.server import HTTPServer
from typing import Any

from genkit.ai.model import ModelFn
from genkit.ai.prompt import PromptFn
from genkit.core.action import Action
from genkit.core.reflection import make_reflection_server
from genkit.core.registry import Registry
from genkit.core.schemas import GenerateRequest, GenerateResponse, Message

Plugin = Callable[['Genkit'], None]


class Genkit:
    """An entrypoint for a user that encapsulate the SDK functionality."""

    MODEL = 'model'
    FLOW = 'flow'

    registry: Registry = Registry()

    def __init__(
        self,
        plugins: list[Plugin] | None = None,
        model: str | None = None,
    ) -> None:
        self.model = model
        if os.getenv('GENKIT_ENV') == 'dev':
            cwd = os.getcwd()
            runtimes_dir = os.path.join(cwd, '.genkit/runtimes')
            current_datetime = datetime.datetime.now()
            if not os.path.exists(runtimes_dir):
                os.makedirs(runtimes_dir)
            runtime_file_path = os.path.join(
                runtimes_dir, f'{current_datetime.isoformat()}.json'
            )
            with open(runtime_file_path, 'w', encoding='utf-8') as rf:
                rf.write(
                    json.dumps(
                        {
                            'id': f'{os.getpid()}',
                            'pid': os.getpid(),
                            'reflectionServerUrl': 'http://localhost:3100',
                            'timestamp': f'{current_datetime.isoformat()}',
                        }
                    )
                )

            def delete_runtime_file() -> None:
                os.remove(runtime_file_path)

            atexit.register(delete_runtime_file)

            self.thread = threading.Thread(target=self.start_server)
            self.thread.start()

        if plugins is not None:
            for plugin in plugins:
                plugin(self)

    def start_server(self) -> None:
        httpd = HTTPServer(
            ('127.0.0.1', 3100), make_reflection_server(self.registry)
        )
        httpd.serve_forever()

    def generate(
        self,
        model: str | None = None,
        prompt: str | None = None,
        messages: list[Message] | None = None,
        system: str | None = None,
        tools: list[str] | None = None,
    ) -> GenerateResponse:
        model = model if model is not None else self.model
        if model is None:
            raise Exception('No model configured.')

        model_action = self.registry.lookup_action(self.MODEL, model)

        return model_action.fn(GenerateRequest(messages=messages)).response

    def flow(self, name: str | None = None) -> Callable[[Callable], Callable]:
        def wrapper(func: Callable) -> Callable:
            flow_name = name if name is not None else func.__name__
            action = Action(
                name=flow_name,
                action_type=self.FLOW,
                fn=func,
                span_metadata={'genkit:metadata:flow:name': flow_name},
            )
            self.registry.register_action(
                action_type=self.FLOW, name=flow_name, action=action
            )

            def decorator(*args: Any, **kwargs: Any) -> GenerateResponse:
                return action.fn(*args, **kwargs).response

            return decorator

        return wrapper

    def define_model(
        self,
        name: str,
        fn: ModelFn,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        action = Action(
            name=name, action_type=self.MODEL, fn=fn, metadata=metadata
        )
        self.registry.register_action(self.MODEL, name, action)

    def define_prompt(
        self,
        name: str,
        fn: PromptFn,
        model: str | None = None,
    ) -> Callable[[Any | None], GenerateResponse]:
        def prompt(input_prompt: Any | None = None) -> GenerateResponse:
            req = fn(input_prompt)
            return self.generate(messages=req.messages, model=model)

        action = Action(self.MODEL, name, prompt)
        self.registry.register_action(self.MODEL, name, action)

        def wrapper(input_prompt: Any | None = None) -> GenerateResponse:
            return action.fn(input_prompt)

        return wrapper
