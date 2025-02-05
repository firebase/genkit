# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


import atexit
import datetime
import json
import os
import threading

from http.server import HTTPServer
from typing import Union, List, Dict, Optional, Callable, Any

from genkit.ai.model import ModelFn
from genkit.ai.prompt import PromptFn
from genkit.core.reflection import MakeReflectionServer
from genkit.core.registry import Registry
from genkit.core.action import Action
from genkit.core.types import GenerateRequest, GenerateResponse, Message

Plugin = Callable[['Genkit'], None]


class Genkit:
    registry: Registry = Registry()

    def __init__(
        self,
        plugins: Optional[List[Plugin]] = None,
        model: Optional[str] = None,
    ) -> None:
        self.model = model
        if 'GENKIT_ENV' in os.environ and os.environ['GENKIT_ENV'] == 'dev':
            cwd = os.getcwd()
            runtimesDir = os.path.join(cwd, '.genkit/runtimes')
            current_datetime = datetime.datetime.now()
            if not os.path.exists(runtimesDir):
                os.makedirs(runtimesDir)
            runtime_file_path = os.path.join(
                runtimesDir, f'{current_datetime.isoformat()}.json'
            )
            rf = open(runtime_file_path, 'w')
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
            rf.close()

            def delete_runtime_file() -> None:
                os.remove(runtime_file_path)

            atexit.register(delete_runtime_file)

            threading.Thread(target=self.start_server).start()

        if plugins is not None:
            for plugin in plugins:
                plugin(self)

    def start_server(self) -> None:
        httpd = HTTPServer(
            ('127.0.0.1', 3100), MakeReflectionServer(self.registry)
        )
        httpd.serve_forever()

    def generate(
        self,
        model: Optional[str] = None,
        prompt: Optional[Union[str]] = None,
        messages: Optional[List[Message]] = None,
        system: Optional[Union[str]] = None,
        tools: Optional[List[str]] = None,
    ) -> GenerateResponse:
        model = model if model is not None else self.model
        if model is None:
            raise Exception('no model configured')

        modelAction = self.registry.lookup_action('model', model)

        return modelAction.fn(GenerateRequest(messages=messages)).response

    def flow(
        self, name: Optional[str] = None
    ) -> Callable[[Callable], Callable]:
        def wrapper(func: Callable) -> Callable:
            flowName = name if name is not None else func.__name__
            action = Action(
                name=flowName,
                type='flow',
                fn=func,
                spanMetadata={'genkit:metadata:flow:name': flowName},
            )
            self.registry.register_action(
                type='flow', name=flowName, action=action
            )

            def decorator(*args: Any, **kwargs: Any) -> GenerateResponse:
                return action.fn(*args, **kwargs).response

            return decorator

        return wrapper

    def define_model(
        self,
        name: str,
        fn: ModelFn,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        action = Action(name=name, type='model', fn=fn, metadata=metadata)
        self.registry.register_action('model', name, action)

    def define_prompt(
        self,
        name: str,
        fn: PromptFn,
        model: Optional[str] = None,
    ) -> Callable[[Optional[Any]], GenerateResponse]:
        def prompt(input: Optional[Any] = None) -> GenerateResponse:
            req = fn(input)
            return self.generate(messages=req.messages, model=model)

        action = Action('model', name, prompt)
        self.registry.register_action('model', name, action)

        def wrapper(input: Optional[Any] = None) -> GenerateResponse:
            return action.fn(input)

        return wrapper


__all__ = [
    'Genkit',
    'Plugin',
]
