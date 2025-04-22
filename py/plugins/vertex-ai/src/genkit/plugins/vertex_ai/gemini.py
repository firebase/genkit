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

"""Gemini model integration for Vertex AI plugin.

This module provides classes and utilities for working with Google's
Gemini models through the Vertex AI platform. It includes version
definitions and a client class for making requests to Gemini models.
"""

import sys  # noqa

if sys.version_info < (3, 11):  # noqa
    from strenum import StrEnum  # noqa
else:  # noqa
    from enum import StrEnum  # noqa

from typing import Any

import structlog
import vertexai.generative_models as genai

from genkit.ai import ActionKind, ActionRunContext, GenkitRegistry
from genkit.types import (
    CustomPart,
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

logger = structlog.get_logger(__name__)


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
    GEMINI_2_5_FLASH_PREVIEW = 'gemini-2.5-flash-preview-04-17'


SUPPORTED_MODELS: dict[GeminiVersion | str, ModelInfo] = {
    GeminiVersion.GEMINI_1_5_PRO: ModelInfo(
        versions=[],
        label='Vertex AI - Gemini 1.5 Pro',
        supports=Supports(multiturn=True, media=True, tools=True, systemRole=True),
    ),
    GeminiVersion.GEMINI_1_5_FLASH: ModelInfo(
        versions=[],
        label='Vertex AI - Gemini 1.5 Flash',
        supports=Supports(multiturn=True, media=True, tools=True, systemRole=True),
    ),
    GeminiVersion.GEMINI_2_0_FLASH_001: ModelInfo(
        versions=[],
        label='Vertex AI - Gemini 2.0 Flash 001',
        supports=Supports(multiturn=True, media=True, tools=True, systemRole=True),
    ),
    GeminiVersion.GEMINI_2_0_FLASH_LITE_PREVIEW: ModelInfo(
        versions=[],
        label='Vertex AI - Gemini 2.0 Flash Lite Preview 02-05',
        supports=Supports(multiturn=True, media=True, tools=True, systemRole=True),
    ),
    GeminiVersion.GEMINI_2_0_PRO_EXP: ModelInfo(
        versions=[],
        label='Vertex AI - Gemini 2.0 Flash Pro Experimental 02-05',
        supports=Supports(multiturn=True, media=True, tools=True, systemRole=True),
    ),
    GeminiVersion.GEMINI_2_5_FLASH_PREVIEW: ModelInfo(
        versions=[],
        label='Vertex AI - Gemini 2.5 Flash Preview 04-17',
        supports=Supports(multiturn=True, media=True, tools=True, systemRole=True),
    ),
}


class Gemini:
    """Client for interacting with Gemini models via Vertex AI.

    This class provides methods for making requests to Gemini models,
    handling message formatting and response processing.
    """

    def __init__(self, version: str | GeminiVersion, registry: GenkitRegistry):
        """Initialize a Gemini client.

        Args:
            version: The version of the Gemini model to use, should be
                one of the values from GeminiVersion.
            registry: The registry to use for the Gemini client.
        """
        self._version = version
        self._registry = registry

    def is_multimode(self):
        """Check if the model supports multimode input.

        Returns:
            True if the model supports multimode input, False otherwise.
        """
        return SUPPORTED_MODELS[self._version].supports.media

    def build_messages(self, request: GenerateRequest) -> list[genai.Content]:
        """Builds a list of VertexAI content from a request.

        Args:
            request: a packed request for the model.

        Returns:
            A list of VertexAI GenAI Content for the request.
        """
        messages: list[genai.Content] = []
        for message in request.messages:
            parts: list[genai.Part] = []
            for part in message.content:
                if isinstance(part.root, TextPart):
                    parts.append(genai.Part.from_text(part.root.text))
                elif isinstance(part.root, MediaPart):
                    if not self.is_multimode():
                        logger.error(f'The model {self._version} does not support multimode input')
                        continue
                    parts.append(
                        genai.Part.from_uri(
                            mime_type=part.root.media.content_type,
                            uri=part.root.media.url,
                        )
                    )
                elif isinstance(part.root, ToolRequestPart | ToolResponsePart):
                    logger.warning('Tools are not supported yet')
                elif isinstance(part.root, CustomPart):
                    # TODO: handle CustomPart
                    logger.warning('The code part is not supported yet.')
                else:
                    logger.error('The type is not supported')
            messages.append(genai.Content(role=message.role.value, parts=parts))

        return messages

    @property
    def gemini_model(self) -> genai.GenerativeModel:
        """Get the Vertex AI GenerativeModel instance.

        Returns:
            A configured GenerativeModel instance for the specified version.
        """
        return genai.GenerativeModel(self._version)

    def _get_gemini_tools(self, request: GenerateRequest) -> list[genai.Tool]:
        """Generates VertexAI Gemini compatible tool definitions.

        Args:
            request: The generation request.

        Returns:
            List of Gemini tools.
        """
        tools = []
        for tool in request.tools:
            function = genai.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters=tool.input_schema,
                response=tool.output_schema,
            )
            tools.append(genai.Tool(function_declarations=[function]))

        return tools

    def _call_tool(self, call: genai.FunctionCall) -> genai.Content:
        """Calls tool's function from the registry.

        Args:
            call: FunctionCall from Gemini response

        Returns:
            Gemini message content to add to the message
        """
        tool_function = self._registry.registry.lookup_action(ActionKind.TOOL, call.name)
        args = tool_function.input_type.validate_python(call.args)
        tool_answer = tool_function.run(args)
        return genai.Content(
            parts=[
                genai.Part.from_function_response(
                    name=call.name,
                    response={
                        'content': tool_answer.response,
                    },
                )
            ]
        )

    def generate(self, request: GenerateRequest, ctx: ActionRunContext) -> GenerateResponse | None:
        """Handle a generation request using the Gemini model.

        Args:
            request: The generation request containing messages and parameters.
            ctx: additional context

        Returns:
            The model's response to the generation request.
        """
        messages = self.build_messages(request)
        tools = self._get_gemini_tools(request) if request.tools else None
        if request.tools:
            nn_tool_choice = self.gemini_model.generate_content(contents=messages, stream=ctx.is_streaming, tools=tools)
            for candidate in nn_tool_choice.candidates:
                messages.append(candidate.content)
                for call in candidate.function_calls:
                    messages.append(self._call_tool(call))

        response = self.gemini_model.generate_content(contents=messages, stream=ctx.is_streaming, tools=tools)

        text_response = ''
        if ctx.is_streaming:
            for chunk in response:
                # TODO: Support other types of output.
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
        """Get the model metadata.

        Returns:
            A dictionary containing the model metadata.
        """
        supports = SUPPORTED_MODELS[self._version].supports.model_dump()
        return {
            'model': {
                'supports': supports,
            }
        }
