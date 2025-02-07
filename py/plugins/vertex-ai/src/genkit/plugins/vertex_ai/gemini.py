# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Processes Gemini request."""
import logging

from vertexai.generative_models import Content, GenerativeModel, Part

from genkit.ai.model import ModelReference
from genkit.core.schemas import (
    GenerateRequest,
    GenerateResponse,
    Message,
    ModelInfo,
    Role,
    Supports,
    TextPart,
)

LOG = logging.getLogger(__name__)


# Deprecated on 2/15/2025
SUPPORTED_V1_MODELS = {
  'gemini-1.0-pro': ModelReference(
        name='vertexai/gemini-1.0-pro',
        info=ModelInfo(
    versions=['gemini-1.0-pro-001', 'gemini-1.0-pro-002'],
    label='Vertex AI - Gemini Pro',
    supports=Supports(
        multiturn=True,
        media=False,
        tools=True,
        systemRole=True
    )
))
}

SUPPORTED_V15_MODELS = {
    'gemini-1.5-pro': ModelReference(
        name='vertexai/gemini-1.5-pro',
        info=ModelInfo(
        versions=['gemini-1.5-pro-001', 'gemini-1.5-pro-002'],
        label='Vertex AI - Gemini 1.5 Pro',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True
        )
    )),
    'gemini-1.5-flash': ModelReference(
        name='vertexai/gemini-1.5-flash',
        info=ModelInfo(
        versions=['gemini-1.5-flash-001', 'gemini-1.5-flash-002'],
        label='Vertex AI - Gemini 1.5 Flash',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True
        )
    )),
    'gemini-2.0-flash-001': ModelReference(
        name='vertexai/gemini-2.0-flash-001',
        info=ModelInfo(
        versions=[],
        label='Vertex AI - Gemini 2.0 Flash 001',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True
        )
    )),
    'gemini-2.0-flash-lite-preview-02-05': ModelReference(
        name='vertexai/gemini-2.0-flash-lite-preview-02-05',
        info=ModelInfo(
        versions=[],
        label='Vertex AI - Gemini 2.0 Flash Lite Preview 02-05',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True
        )
    )),
    'gemini-2.0-pro-exp-02-05': ModelReference(
        name='vertexai/gemini-2.0-pro-exp-02-05',
        info=ModelInfo(
        versions=[],
        label='Vertex AI - Gemini 2.0 Flash Pro Experimental 02-05',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True
        )
    )),
}

SUPPORTED_MODELS = SUPPORTED_V1_MODELS | SUPPORTED_V15_MODELS


def nearest_gemini_model(model_name):
    model = SUPPORTED_MODELS.get(model_name)
    if model:
        return model
    return ModelReference(
        name=f'vertexai/{model_name}',
        info=ModelInfo(
        versions=[],
        label='Vertex AI - Gemini',
        supports=Supports(
            multiturn=True,
            media=True,
            tools=True,
            systemRole=True
            )
        )
    )


def execute_gemini_request(request: GenerateRequest) -> GenerateResponse:
    messages: list[Content] = []
    for msg in request.messages:
        parts: list[Part] = []
        for part in msg.content:
            if hasattr(part, "text") and part.text:
                parts.append(Part.from_text(part.text))
            else:
                LOG.error("Unsupported message type.")
        messages.append(Content(role=msg.role.value, parts=parts))
    model = GenerativeModel('gemini-1.5-flash-001')
    response = model.generate_content(contents=messages)
    return GenerateResponse(
        message=Message(
            role=Role.model, content=[TextPart(text=response.text)]
        )
    )
