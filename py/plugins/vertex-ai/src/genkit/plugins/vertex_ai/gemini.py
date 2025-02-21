# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from enum import StrEnum

from genkit.core.schema_types import (
    GenerateRequest,
    GenerateResponse,
    Message,
    ModelInfo,
    Role,
    Supports,
    TextPart,
)
from vertexai.generative_models import Content, GenerativeModel, Part


class GeminiVersion(StrEnum):
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
    def __init__(self, version):
        self.version = version

    @property
    def gemini_model(self) -> GenerativeModel:
        return GenerativeModel(self.version)

    def handle_request(self, request: GenerateRequest) -> GenerateResponse:
        messages: list[Content] = []
        for m in request.messages:
            parts: list[Part] = []
            for p in m.content:
                if p.root.text is not None:
                    parts.append(Part.from_text(p.root.text))
                else:
                    raise Exception('unsupported part type')
            messages.append(Content(role=m.role.value, parts=parts))
        response = self.gemini_model.generate_content(contents=messages)
        return GenerateResponse(
            message=Message(
                role=Role.model,
                content=[TextPart(text=response.text)],
            )
        )
