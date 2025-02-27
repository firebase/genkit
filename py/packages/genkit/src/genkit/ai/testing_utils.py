#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Testing utils/helpers for genkit.ai"""

from genkit.core.action import Action, ActionRunContext
from genkit.core.codec import dump_json
from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    Message,
    Role,
    TextPart,
)
from genkit.veneer.veneer import Genkit


class ProgrammableModel:
    request_idx = 0
    responses: list[GenerateResponse] = []
    chunks: list[list[GenerateResponseChunk]] = None
    last_request: GenerateRequest = None

    def __init__(self):
        self.request_idx = 0
        self.responses = []
        self.chunks = None
        self.last_request = None

    def model_fn(self, request: GenerateRequest, ctx: ActionRunContext):
        self.last_request = request
        response = self.responses[self.request_idx]
        if self.chunks is not None:
            for chunk in self.chunks[self.request_idx]:
                ctx.send_chunk(chunk)
        self.request_idx += 1
        return response


def define_programmable_model(ai: Genkit, name: str = 'programmableModel'):
    """Defines a programmable model which can be configured to respond with
    specific responses and streaming chunks."""
    pm = ProgrammableModel()

    def model_fn(request: GenerateRequest, ctx: ActionRunContext):
        return pm.model_fn(request, ctx)

    action = ai.define_model(name=name, fn=model_fn)

    return (pm, action)


class EchoModel:
    last_request: GenerateRequest = None

    def __init__(self):
        def model_fn(request: GenerateRequest):
            self.last_request = request
            merged_txt = ''
            for m in request.messages:
                merged_txt += f' {m.role}: ' + ','.join(
                    dump_json(p.root.text) if p.root.text is not None else '""'
                    for p in m.content
                )
            echo_resp = f'[ECHO]{merged_txt}'
            if request.config:
                echo_resp += f' {dump_json(request.config)}'
            if request.tool_choice is not None:
                echo_resp += f' tool_choice={request.tool_choice}'
            if request.output and dump_json(request.output) != '{}':
                echo_resp += f' output={dump_json(request.output)}'
            return GenerateResponse(
                message=Message(
                    role=Role.MODEL, content=[TextPart(text=echo_resp)]
                )
            )

        self.model_fn = model_fn


def define_echo_model(ai: Genkit, name: str = 'echoModel'):
    """Defines a simple echo model that echos requests"""
    echo = EchoModel()

    action = ai.define_model(name=name, fn=echo.model_fn)

    return (echo, action)
