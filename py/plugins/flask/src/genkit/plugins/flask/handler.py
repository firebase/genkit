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

"""Genkit Flask plugin."""

import asyncio
from collections.abc import Callable

from flask import Response, request
from genkit.ai import Genkit
from genkit.ai.registry import FlowWrapper
from genkit.aio.loop import create_loop, iter_over_async
from genkit.codec import dump_dict, dump_json
from genkit.core.context import ContextProvider, RequestData
from genkit.core.error import GenkitError, get_callable_json


class _FlaskRequestData(RequestData):
    def __init__(self):
        self.method = request.method

        self.headers = {}
        for key, value in request.headers:
            self.headers[key.lower()] = value

        input_data = request.get_json()
        if 'data' not in input_data:
            return Response(status=400, response='flow request must be wrapped in {"data": data} object')

        self.input = input_data.get('data')


def genkit_flask_handler(ai: Genkit, context_provider: ContextProvider | None = None) -> Callable:
    """A decorator for serving Genkit flows via a flask sever.

    ```python
    from genkit.plugins.flask import genkit_flask_handler

    app = Flask(__name__)


    @app.post('/chat')
    @genkit_flask_handler(ai)
    @ai.flow()
    async def say_hi(name: str, ctx):
        return await ai.generate(
            on_chunk=ctx.send_chunk,
            prompt=f'tell a medium sized joke about {name}',
        )
    ```

    """
    loop = ai.loop if ai.loop else create_loop()

    def decorator(flow: Callable) -> Callable:
        if not isinstance(flow, FlowWrapper):
            raise GenkitError(status='INVALID_ARGUMENT', message='must apply @genkit_flask_handler on a @flow')

        async def handler():
            input_data = request.get_json()
            if 'data' not in input_data:
                return Response(status=400, response='flow request must be wrapped in {"data": data} object')

            request_data = _FlaskRequestData()
            context = None
            if context_provider:
                context = context_provider(request_data)
                if asyncio.iscoroutine(context):
                    context = await context

            stream = request_data.headers.get('accept') == 'text/event-stream' or request.args.get('stream') == 'true'
            if stream:

                async def async_gen():
                    try:
                        stream, response = flow._action.stream(input_data.get('data'), context=context)
                        async for chunk in stream:
                            yield f'data: {dump_json({"message": dump_dict(chunk)})}\n\n'

                        yield f'data: {dump_json({"result": dump_dict(await response)})}\n\n'
                    except Exception as e:
                        ex = e
                        if isinstance(ex, GenkitError):
                            ex = ex.cause
                        yield f'error: {dump_json({"error": dump_dict(get_callable_json(ex))})}'

                iter = iter_over_async(async_gen(), loop)
                return iter
            else:
                try:
                    response = await flow._action.arun_raw(input_data.get('data'), context=context)
                    return {'result': dump_dict(response.response)}
                except Exception as e:
                    ex = e
                    if isinstance(ex, GenkitError):
                        ex = ex.cause
                    return Response(status=500, response=dump_json(get_callable_json(ex)))

        return handler

    return decorator
