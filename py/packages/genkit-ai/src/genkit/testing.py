#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Testing utils/helpers for genkit.blocks."""

from genkit.ai import Genkit
from genkit.codec import dump_json
from genkit.core.action import ActionRunContext
from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    Message,
    Role,
    TextPart,
)


class ProgrammableModel:
    """A configurable model implementation for testing.

    This class allows test cases to define custom responses that the model
    should return, making it useful for testing expected behavior in various
    scenarios.

    Attributes:
        request_idx: Index tracking which request is being processed.
        responses: List of predefined responses to return.
        chunks: Optional list of chunks to stream for each request.
        last_request: The most recent request received.
    """

    def __init__(self):
        """Initialize a new ProgrammableModel instance."""
        self.request_idx = 0
        self.responses: list[GenerateResponse] = []
        self.chunks: list[list[GenerateResponseChunk]] = None
        self.last_request: GenerateRequest = None

    def model_fn(self, request: GenerateRequest, ctx: ActionRunContext):
        """Process a generation request and return a programmed response.

        This function returns pre-configured responses and streams
        pre-configured chunks based on the current request index.

        Args:
            request: The generation request to process.
            ctx: The action run context for streaming chunks.

        Returns:
            The pre-configured response for the current request.
        """
        self.last_request = request
        response = self.responses[self.request_idx]
        if self.chunks:
            for chunk in self.chunks[self.request_idx]:
                ctx.send_chunk(chunk)
        self.request_idx += 1
        return response


def define_programmable_model(ai: Genkit, name: str = 'programmableModel'):
    """Defines a configurable programmable model."""
    pm = ProgrammableModel()

    def model_fn(request: GenerateRequest, ctx: ActionRunContext):
        return pm.model_fn(request, ctx)

    action = ai.define_model(name=name, fn=model_fn)

    return (pm, action)


class EchoModel:
    """A simple model implementation that echoes back the input.

    This model is useful for testing as it returns a readable representation
    of the input it received.

    Attributes:
        last_request: The most recent request received.
    """

    def __init__(self):
        """Initialize a new EchoModel instance."""
        self.last_request: GenerateRequest = None

    def model_fn(self, request: GenerateRequest):
        """Process a generation request and echo it back in the response.

        Args:
            request: The generation request to process.

        Returns:
            A response containing an echo of the input request details.
        """
        self.last_request = request
        merged_txt = ''
        for m in request.messages:
            merged_txt += f' {m.role}: ' + ','.join(
                dump_json(p.root.text) if p.root.text is not None else '""' for p in m.content
            )
        echo_resp = f'[ECHO]{merged_txt}'
        if request.config:
            echo_resp += f' {dump_json(request.config)}'
        if request.tools:
            echo_resp += f' tools={",".join(t.name for t in request.tools)}'
        if request.tool_choice is not None:
            echo_resp += f' tool_choice={request.tool_choice}'
        if request.output and dump_json(request.output) != '{}':
            echo_resp += f' output={dump_json(request.output)}'
        return GenerateResponse(message=Message(role=Role.MODEL, content=[TextPart(text=echo_resp)]))


def define_echo_model(ai: Genkit, name: str = 'echoModel'):
    """Defines a simple echo model that echos requests."""
    echo = EchoModel()

    def model_fn(request: GenerateRequest):
        return echo.model_fn(request)

    action = ai.define_model(name=name, fn=model_fn)

    return (echo, action)
