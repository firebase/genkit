# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Gemini model integration for Vertex AI plugin.

This module provides classes and utilities for working with Google's
Gemini models through the Vertex AI platform. It includes version
definitions and a client class for making requests to Gemini models.
"""

import logging
from enum import StrEnum
from typing import Any

import vertexai.generative_models as genai
from genkit.core.action import ActionRunContext
from genkit.veneer.registry import GenkitRegistry
from genkit.core.typing import (
    CustomPart,
    ToolDefinition,
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    MediaPart,
    Message,
    ModelInfo,
    Role,
    Supports,
    TextPart,
    ToolRequestPart,
    ToolResponsePart,
)
from genkit.core.action import ActionKind

LOG = logging.getLogger(__name__)


class GeminiVersion(StrEnum):
    """Available versions of the Gemini model.

    This enum defines the available versions of the Gemini model that
    can be used through Vertex AI.
    """

    GEMINI_1_5_PRO = 'gemini-1.5-pro'
    GEMINI_1_5_FLASH = 'gemini-1.5-flash'
    GEMINI_2_0_FLASH_001 = 'gemini-2.0-flash-001'
    GEMINI_2_0_FLASH_LITE_PREVIEW = 'gemini-2.0-flash-lite-preview-02-05'
    GEMINI_2_0_PRO_EXP = 'gemini-2.0-pro-exp-02-05'


SUPPORTED_MODELS = {
    GeminiVersion.GEMINI_1_5_PRO: ModelInfo(
        versions=[],
        label='Vertex AI - Gemini 1.5 Pro',
        supports=Supports(
            multiturn=True, media=True, tools=True, systemRole=True
        ),
    ),
    GeminiVersion.GEMINI_1_5_FLASH: ModelInfo(
        versions=[],
        label='Vertex AI - Gemini 1.5 Flash',
        supports=Supports(
            multiturn=True, media=True, tools=True, systemRole=True
        ),
    ),
    GeminiVersion.GEMINI_2_0_FLASH_001: ModelInfo(
        versions=[],
        label='Vertex AI - Gemini 2.0 Flash 001',
        supports=Supports(
            multiturn=True, media=True, tools=True, systemRole=True
        ),
    ),
    GeminiVersion.GEMINI_2_0_FLASH_LITE_PREVIEW: ModelInfo(
        versions=[],
        label='Vertex AI - Gemini 2.0 Flash Lite Preview 02-05',
        supports=Supports(
            multiturn=True, media=True, tools=True, systemRole=True
        ),
    ),
    GeminiVersion.GEMINI_2_0_PRO_EXP: ModelInfo(
        versions=[],
        label='Vertex AI - Gemini 2.0 Flash Pro Experimental 02-05',
        supports=Supports(
            multiturn=True, media=True, tools=True, systemRole=True
        ),
    ),
}


class Gemini:
    """Client for interacting with Gemini models via Vertex AI.

    This class provides methods for making requests to Gemini models,
    handling message formatting and response processing.
    """

    def __init__(self, version: str | GeminiVersion, ai: GenkitRegistry):
        """Initialize a Gemini client.

        Args:
            version: The version of the Gemini model to use, should be
                one of the values from GeminiVersion.
        """
        self._version = version
        self._ai = ai

    def is_multimode(self):
        return SUPPORTED_MODELS[self._version].supports.media

    def build_messages(self, request: GenerateRequest) -> list[genai.Content]:
        """Builds a list of VertexAI content from a request.

        Args:
            - request: a packed request for the model

        Returns:
            - a list of VertexAI GenAI Content for the request
        """
        messages: list[genai.Content] = []
        for message in request.messages:
            parts: list[genai.Part] = []
            for part in message.content:
                if isinstance(part.root, TextPart):
                    parts.append(genai.Part.from_text(part.root.text))
                elif isinstance(part.root, MediaPart):
                    if not self.is_multimode():
                        LOG.error(
                            f'The model {self._version} does not'
                            f' support multimode input'
                        )
                        continue
                    parts.append(
                        genai.Part.from_uri(
                            mime_type=part.root.media.content_type,
                            uri=part.root.media.url,
                        )
                    )
                elif isinstance(part.root, ToolRequestPart | ToolResponsePart):
                    LOG.warning('Tools are not supported yet')
                elif isinstance(part.root, CustomPart):
                    # TODO: handle CustomPart
                    LOG.warning('The code part is not supported yet.')
                else:
                    LOG.error('The type is not supported')
            messages.append(genai.Content(role=message.role.value, parts=parts))

        return messages

    @property
    def gemini_model(self) -> genai.GenerativeModel:
        """Get the Vertex AI GenerativeModel instance.

        Returns:
            A configured GenerativeModel instance for the specified version.
        """
        return genai.GenerativeModel(self._version)

    def _to_gemini_tool(self, tool: ToolDefinition) -> genai.Tool:
        func = genai.FunctionDeclaration(name=tool.name,
                                         description=tool.description,
                                         parameters=tool.input_schema)

        return genai.Tool(function_declarations=[func])


    def generate(
        self, request: GenerateRequest, ctx: ActionRunContext
    ) -> GenerateResponse | None:
        """Handle a generation request using the Gemini model.

        Args:
            request: The generation request containing messages and parameters.
            ctx: additional context

        Returns:
            The model's response to the generation request.
        """

        messages = self.build_messages(request)

        tools = []
        tool_names = []
        if request.tools:
            for tool in request.tools:

                tool_names.append(tool.name)
                gemini_tool = self._to_gemini_tool(tool)
                tools.append(gemini_tool)

            response = self.gemini_model.generate_content(
                contents=messages, stream=ctx.is_streaming, tools=tools
            )
            function_calls = response.candidates[0].function_calls

            for call in function_calls:
                action = self._ai.registry.lookup_action(ActionKind.TOOL, call.name)
                tool_response = action.run(**call.args)
                print(tool_response)


        response = self.gemini_model.generate_content(
            contents=messages, stream=ctx.is_streaming, tools=tools
        )

        text_response = ''
        if ctx.is_streaming:
            for chunk in response:
                # TODO: Support other types of output
                ctx.send_chunk(
                    GenerateResponseChunk(
                        role=Role.MODEL,
                        content=[TextPart(text=chunk.text)],
                    )
                )

        else:
            text_response = response.text

        return GenerateResponse(
            message=Message(
                role=Role.MODEL,
                content=[TextPart(text=text_response)],
            )
        )

    @property
    def model_metadata(self) -> dict[str, dict[str, Any]]:
        supports = SUPPORTED_MODELS[self._version].supports.model_dump()
        return {
            'model': {
                'supports': supports,
            }
        }
