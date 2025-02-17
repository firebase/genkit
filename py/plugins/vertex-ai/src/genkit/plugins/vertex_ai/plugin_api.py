# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Google Cloud Vertex AI Plugin for Genkit."""

import logging
import os
from typing import Any

import vertexai
from genkit.core.plugin_abc import Plugin
from genkit.core.schema_types import GenerateRequest, GenerateResponse
from genkit.plugins.vertex_ai import constants as const
from genkit.plugins.vertex_ai.gemini import Gemini, GeminiVersion
from genkit.veneer.veneer import Genkit

LOG = logging.getLogger(__name__)


def vertexai_name(name: str) -> str:
    return f'vertexai/{name}'


class VertexAI(Plugin):
    # This is 'gemini-1.5-pro' - the latest stable model
    VERTEX_AI_GENERATIVE_MODEL_NAME: str = GeminiVersion.GEMINI_1_5_FLASH.value

    def __init__(
        self, project_id: str | None = None, location: str | None = None
    ):
        # If not set, projectId will be read by plugin
        project_id = (
            project_id if project_id else os.getenv(const.GCLOUD_PROJECT)
        )
        location = location if location else const.DEFAULT_REGION

        self._gemini = Gemini(self.VERTEX_AI_GENERATIVE_MODEL_NAME)
        vertexai.init(project=project_id, location=location)

    def attach_to_veneer(self, veneer: Genkit) -> None:
        self._add_model_to_veneer(veneer=veneer)

    def _add_model_to_veneer(self, veneer: Genkit, **kwargs) -> None:
        return super()._add_model_to_veneer(
            veneer=veneer,
            name=vertexai_name(self.VERTEX_AI_GENERATIVE_MODEL_NAME),
            metadata=self.vertex_ai_model_metadata,
        )

    @property
    def vertex_ai_model_metadata(self) -> dict[str, dict[str, Any]]:
        return {
            'model': {
                'supports': {'multiturn': True},
            }
        }

    def _model_callback(self, request: GenerateRequest) -> GenerateResponse:
        return self._gemini.handle_request(request=request)
