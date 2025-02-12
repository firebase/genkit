# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""
Google Cloud Vertex AI Plugin for Genkit.
"""

from typing import Any

import vertexai
from genkit.core.plugin_abc import Plugin
from genkit.core.schemas import (
    GenerateRequest,
    GenerateResponse,
    Message,
    Role,
    TextPart,
)
from genkit.veneer.veneer import Genkit
from vertexai.generative_models import Content, GenerativeModel, Part


def package_name() -> str:
    return 'genkit.plugins.vertex_ai'


def gemini(name: str) -> str:
    return f'vertexai/{name}'


class VertexAI(Plugin):
    LOCATION = 'us-central1'
    VERTEX_AI_MODEL_NAME = gemini('gemini-1.5-flash')
    VERTEX_AI_GENERATIVE_MODEL_NAME = 'gemini-1.5-flash-002'

    def __init__(self, project_id: str | None = None):
        self.project_id = project_id
        vertexai.init(location=self.LOCATION, project=self.project_id)

    def attach_to_veneer(self, veneer: Genkit) -> None:
        self._add_model_to_veneer(veneer=veneer)

    def _add_model_to_veneer(self, veneer: Genkit, **kwargs) -> None:
        return super()._add_model_to_veneer(
            veneer=veneer,
            name=self.VERTEX_AI_MODEL_NAME,
            metadata=self.vertex_ai_model_metadata,
        )

    @property
    def vertex_ai_model_metadata(self) -> dict[str, dict[str, Any]]:
        return {
            'model': {
                'label': 'banana',
                'supports': {'multiturn': True},
            }
        }

    def _model_callback(self, request: GenerateRequest) -> GenerateResponse:
        return self._handle_gemini_request(request=request)

    def _handle_gemini_request(
        self, request: GenerateRequest
    ) -> GenerateResponse:
        gemini_msgs: list[Content] = []
        for m in request.messages:
            gemini_parts: list[Part] = []
            for p in m.content:
                if p.root.text is not None:
                    gemini_parts.append(Part.from_text(p.root.text))
                else:
                    raise Exception('unsupported part type')
            gemini_msgs.append(Content(role=m.role.value, parts=gemini_parts))
        response = self.vertex_ai_generative_model.generate_content(
            contents=gemini_msgs
        )
        return GenerateResponse(
            message=Message(
                role=Role.model,
                content=[TextPart(text=response.text)],
            )
        )

    @property
    def vertex_ai_generative_model(self) -> GenerativeModel:
        return GenerativeModel(self.VERTEX_AI_GENERATIVE_MODEL_NAME)


__all__ = ['package_name', 'VertexAI', 'gemini']
