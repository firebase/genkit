# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Google Cloud Vertex AI Plugin for Genkit."""

import logging
import os

import vertexai
from genkit.core.plugin_abc import Plugin
from genkit.plugins.vertex_ai import constants as const
from genkit.plugins.vertex_ai.gemini import Gemini, GeminiVersion
from genkit.plugins.vertex_ai.imagen import Imagen, ImagenVersion
from genkit.veneer.veneer import Genkit

LOG = logging.getLogger(__name__)


def vertexai_name(name: str) -> str:
    return f'vertexai/{name}'


class VertexAI(Plugin):
    # This is 'gemini-1.5-pro' - the latest stable model

    def __init__(
        self, project_id: str | None = None, location: str | None = None
    ):
        # If not set, projectId will be read by plugin
        project_id = (
            project_id if project_id else os.getenv(const.GCLOUD_PROJECT)
        )
        location = location if location else const.DEFAULT_REGION
        vertexai.init(project=project_id, location=location)

    def _add_models_to_veneer(self, veneer: Genkit) -> None:
        for model_version in GeminiVersion:
            version = str(model_version.value)
            gemini = Gemini(version)
            veneer.define_model(
                name=vertexai_name(version),
                fn=gemini.handle_request,
                metadata=gemini.model_metadata,
            )

        for model_version in ImagenVersion:
            version = str(model_version.value)
            imagen = Imagen(version)
            veneer.define_model(
                name=vertexai_name(version),
                fn=imagen.handle_request,
                metadata=imagen.model_metadata,
            )

    def _add_embedders_to_veneer(self, veneer: Genkit) -> None:
        """Not defined yet."""
        pass
