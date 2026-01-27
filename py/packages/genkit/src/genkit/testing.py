#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Testing utilities for Genkit applications.

This module provides mock models and utilities for testing Genkit applications
without making actual API calls to AI providers.

Key Components:
    - EchoModel: Echoes input back for verification
    - ProgrammableModel: Returns configurable responses
    - StaticResponseModel: Always returns the same response

Example:
    ```python
    from genkit.ai import Genkit
    from genkit.testing import define_echo_model, define_programmable_model

    ai = Genkit()

    # Echo model - useful for verifying request formatting
    echo, echo_action = define_echo_model(ai)
    response = await ai.generate(model='echoModel', prompt='Hello')
    # response contains: "[ECHO] user: "Hello""

    # Programmable model - useful for testing specific scenarios
    pm, pm_action = define_programmable_model(ai)
    pm.responses = [GenerateResponse(message=Message(...))]
    response = await ai.generate(model='programmableModel', prompt='test')
    assert pm.last_request is not None
    ```

Cross-Language Parity:
    - JavaScript: js/genkit/tests/helpers.ts, js/ai/tests/helpers.ts
    - Go: go/ai/testutil_test.go

See Also:
    - https://firebase.google.com/docs/genkit for Genkit documentation
"""

from copy import deepcopy
from typing import Any

from genkit.ai import Genkit
from genkit.codec import dump_json
from genkit.core.action import Action, ActionRunContext
from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    Message,
    Part,
    Role,
    TextPart,
)


class ProgrammableModel:
    """A configurable model implementation for testing.

    This class allows test cases to define custom responses that the model
    should return, making it useful for testing expected behavior in various
    scenarios.

    Attributes:
        request_count: Total number of requests received.
        responses: List of predefined responses to return.
        chunks: Optional list of chunks to stream for each request.
        last_request: The most recent request received (deep copy).

    Example:
        ```python
        ai = Genkit()
        pm, action = define_programmable_model(ai)

        # Set up responses
        pm.responses = [
            GenerateResponse(message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='Response 1'))])),
            GenerateResponse(message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='Response 2'))])),
        ]

        # First call returns "Response 1"
        result1 = await ai.generate(model='programmableModel', prompt='test')

        # Second call returns "Response 2"
        result2 = await ai.generate(model='programmableModel', prompt='test')

        # Inspect last request
        assert pm.last_request.messages[0].content[0].root.text == 'test'
        ```
    """

    def __init__(self) -> None:
        """Initialize a new ProgrammableModel instance."""
        self._request_idx = 0
        self.request_count = 0
        self.responses: list[GenerateResponse] = []
        self.chunks: list[list[GenerateResponseChunk]] | None = None
        self.last_request: GenerateRequest | None = None

    def reset(self) -> None:
        """Reset the model state for reuse in tests."""
        self._request_idx = 0
        self.request_count = 0
        self.responses = []
        self.chunks = None
        self.last_request = None

    def model_fn(self, request: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        """Process a generation request and return a programmed response.

        This function returns pre-configured responses and streams
        pre-configured chunks based on the current request index.

        Args:
            request: The generation request to process.
            ctx: The action run context for streaming chunks.

        Returns:
            The pre-configured response for the current request.

        Raises:
            IndexError: If more requests are made than responses configured.
        """
        # Store deep copy of request for inspection (matches JS behavior)
        self.last_request = deepcopy(request)
        self.request_count += 1

        response = self.responses[self._request_idx]
        if self.chunks and self._request_idx < len(self.chunks):
            for chunk in self.chunks[self._request_idx]:
                ctx.send_chunk(chunk)
        self._request_idx += 1
        return response


def define_programmable_model(
    ai: Genkit,
    name: str = 'programmableModel',
) -> tuple[ProgrammableModel, Action]:
    """Define a configurable programmable model for testing.

    Creates a model that returns pre-configured responses, useful for
    testing specific scenarios like multi-turn conversations, tool calls,
    or error conditions.

    Args:
        ai: The Genkit instance to register the model with.
        name: The name for the model. Defaults to 'programmableModel'.

    Returns:
        A tuple of (ProgrammableModel instance, registered Action).

    Example:
        ```python
        ai = Genkit()
        pm, action = define_programmable_model(ai)

        # Configure response with tool call
        pm.responses = [
            GenerateResponse(
                message=Message(
                    role=Role.MODEL,
                    content=[
                        Part(
                            root=ToolRequestPart(
                                tool_request=ToolRequest(
                                    name='myTool',
                                    input={'arg': 'value'},
                                ),
                            )
                        )
                    ],
                )
            )
        ]
        ```
    """
    pm = ProgrammableModel()

    def model_fn(request: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        return pm.model_fn(request, ctx)

    action = ai.define_model(name=name, fn=model_fn)

    return (pm, action)


class EchoModel:
    """A model implementation that echoes back the input with metadata.

    This model is useful for testing as it returns a readable representation
    of the input it received, including config, tools, and output schema.

    The echo format is:
        [ECHO] role: "content", role: "content" config tool_choice output

    Attributes:
        last_request: The most recent request received.
        stream_countdown: If True, streams "3", "2", "1" chunks before response.

    Example:
        ```python
        ai = Genkit()
        echo, action = define_echo_model(ai, stream_countdown=True)

        response = await ai.generate(model='echoModel', prompt='Hello world', config={'temperature': 0.5})
        # Response text: '[ECHO] user: "Hello world" {"temperature":0.5}'
        # With streaming: sends chunks "3", "2", "1" before final response
        ```
    """

    def __init__(self, stream_countdown: bool = False) -> None:
        """Initialize a new EchoModel instance.

        Args:
            stream_countdown: If True, stream "3", "2", "1" chunks before response.
        """
        self.last_request: GenerateRequest | None = None
        self.stream_countdown = stream_countdown

    def model_fn(self, request: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        """Process a generation request and echo it back in the response.

        Args:
            request: The generation request to process.
            ctx: The action run context for streaming.

        Returns:
            A response containing an echo of the input request details.
        """
        self.last_request = request

        # Build echo string from messages
        merged_txt = ''
        for m in request.messages:
            merged_txt += f' {m.role}: ' + ','.join(
                dump_json(p.root.text) if p.root.text is not None else '""' for p in m.content
            )
        echo_resp = f'[ECHO]{merged_txt}'

        # Add config, tools, and output info
        if request.config:
            echo_resp += f' {dump_json(request.config)}'
        if request.tools:
            echo_resp += f' tools={",".join(t.name for t in request.tools)}'
        if request.tool_choice is not None:
            echo_resp += f' tool_choice={request.tool_choice}'
        if request.output and dump_json(request.output) != '{}':
            echo_resp += f' output={dump_json(request.output)}'

        # Stream countdown chunks if enabled (matches JS behavior)
        if self.stream_countdown:
            for i, countdown in enumerate(['3', '2', '1']):
                ctx.send_chunk(
                    chunk=GenerateResponseChunk(role=Role.MODEL, index=i, content=[Part(root=TextPart(text=countdown))])
                )

        # NOTE: Part is a RootModel requiring root=TextPart(...) syntax.
        return GenerateResponse(message=Message(role=Role.MODEL, content=[Part(root=TextPart(text=echo_resp))]))


def define_echo_model(
    ai: Genkit,
    name: str = 'echoModel',
    stream_countdown: bool = False,
) -> tuple[EchoModel, Action]:
    """Define an echo model that returns input back as output.

    Creates a model that echoes the request back in a readable format,
    useful for testing request formatting and middleware behavior.

    Args:
        ai: The Genkit instance to register the model with.
        name: The name for the model. Defaults to 'echoModel'.
        stream_countdown: If True, stream "3", "2", "1" before final response.

    Returns:
        A tuple of (EchoModel instance, registered Action).

    Example:
        ```python
        ai = Genkit()
        echo, action = define_echo_model(ai, stream_countdown=True)

        # Test that middleware properly formats requests
        response = await ai.generate(model='echoModel', prompt='test')
        assert '[ECHO]' in response.text
        ```
    """
    echo = EchoModel(stream_countdown=stream_countdown)

    def model_fn(request: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        return echo.model_fn(request, ctx)

    action = ai.define_model(name=name, fn=model_fn)

    return (echo, action)


class StaticResponseModel:
    """A model that always returns the same static response.

    Useful for simple test cases where a fixed response is needed.

    Attributes:
        response_message: The message to always return.
        last_request: The most recent request received.
        request_count: Total number of requests received.
    """

    def __init__(self, message: dict[str, Any]) -> None:
        """Initialize with a static message to return.

        Args:
            message: The message data to always return.
        """
        self.response_message = message
        self.last_request: GenerateRequest | None = None
        self.request_count = 0

    def model_fn(self, request: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        """Return the static response.

        Args:
            request: The generation request (stored but not used).
            ctx: The action run context (unused).

        Returns:
            GenerateResponse with the static message.
        """
        self.last_request = request
        self.request_count += 1
        return GenerateResponse(message=Message.model_validate(self.response_message))


def define_static_response_model(
    ai: Genkit,
    message: dict[str, Any],
    name: str = 'staticModel',
) -> tuple[StaticResponseModel, Action]:
    """Define a model that always returns the same response.

    Args:
        ai: The Genkit instance to register the model with.
        message: The message data to always return.
        name: The name for the model. Defaults to 'staticModel'.

    Returns:
        A tuple of (StaticResponseModel instance, registered Action).

    Example:
        ```python
        ai = Genkit()
        static, action = define_static_response_model(
            ai,
            message={'role': 'model', 'content': [{'text': 'Hello!'}]},
        )

        # Always returns "Hello!"
        response = await ai.generate(model='staticModel', prompt='anything')
        assert response.text == 'Hello!'
        ```
    """
    static = StaticResponseModel(message)

    def model_fn(request: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse:
        return static.model_fn(request, ctx)

    action = ai.define_model(name=name, fn=model_fn)

    return (static, action)


# Export all public symbols
__all__ = [
    'EchoModel',
    'ProgrammableModel',
    'StaticResponseModel',
    'define_echo_model',
    'define_programmable_model',
    'define_static_response_model',
]
