# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Gemini model integration for Vertex AI plugin.

This module provides classes and utilities for working with Google's
Gemini models through the Vertex AI platform. It includes version
definitions and a client class for making requests to Gemini models.
"""

from enum import StrEnum
from typing import Any

from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    Message,
    ModelInfo,
    Role,
    Supports,
    TextPart,
    ToolRequest1,
    ToolRequestPart,
)
from vertexai.generative_models import (
    Content,
    FunctionDeclaration,
    GenerativeModel,
    Part,
    Tool,
)


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

    def __init__(self, version: str):
        """Initialize a Gemini client.

        Args:
            version: The version of the Gemini model to use, should be
                one of the values from GeminiVersion.
        """
        self._version = version

    @property
    def gemini_model(self) -> GenerativeModel:
        """Get the Vertex AI GenerativeModel instance.

        Returns:
            A configured GenerativeModel instance for the specified version.
        """
        return GenerativeModel(self._version)

    def handle_request(self, request: GenerateRequest) -> GenerateResponse:
        """Handle a generation request using the Gemini model.

        Args:
            request: The generation request containing messages and parameters.

        Returns:
            The model's response to the generation request.
        """
        messages: list[Content] = []
        for m in request.messages:
            parts: list[Part] = []
            for p in m.content:
                if p.root.text is not None:
                    parts.append(Part.from_text(p.root.text))
                else:
                    raise Exception('unsupported part type')
            messages.append(Content(role=m.role.value, parts=parts))
        tools = [
            Tool(
                function_declarations=[
                    FunctionDeclaration(
                        name=tool_definition.name,
                        parameters=tool_definition.input_schema,
                        description=tool_definition.description,
                        response=tool_definition.output_schema,
                    )
                ]
            )
            for tool_definition in request.tools or []
        ]
        response = self.gemini_model.generate_content(
            contents=messages,
            tools=tools,
        )
        # If response containing text -
        # model was able to address request without tools
        try:
            content = [
                TextPart(
                    text=response.text,
                )
            ]
        except ValueError:
            content = []
            for candidate in response.candidates:
                # If model is able to address request by itself - return text
                # Otherwise will return a suggested tool
                try:
                    content.append(
                        TextPart(
                            text=candidate.text,
                        )
                    )
                except ValueError:
                    content.append(
                        ToolRequestPart(
                            tool_request=ToolRequest1(
                                name=candidate.function_calls[0].name,
                                input=candidate.function_calls[0].args,
                            )
                        )
                    )
        return GenerateResponse(
            message=Message(
                role=Role.MODEL,
                content=content,
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
