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

"""Google Cloud Vertex AI Plugin for Genkit."""

import os

import vertexai

from genkit.ai import GenkitRegistry, Plugin
from genkit.plugins.vertex_ai import constants as const
from genkit.plugins.vertex_ai.embedding import Embedder, EmbeddingModels
from genkit.plugins.vertex_ai.gemini import Gemini, GeminiVersion
from genkit.plugins.vertex_ai.imagen import Imagen, ImagenVersion


def vertexai_name(name: str) -> str:
    """Create a Vertex AI action name.

    Args:
        name: Base name for the action.

    Returns:
        The fully qualified Vertex AI action name.
    """
    return f'vertexai/{name}'


class VertexAI(Plugin):
    """Vertex AI plugin for Genkit.

    This plugin provides integration with Google Cloud's Vertex AI platform,
    enabling the use of Vertex AI models and services within the Genkit
    framework. It handles initialization of the Vertex AI client and
    registration of model actions.
    """

    name = 'vertexai'

    def __init__(self, project_id: str | None = None, location: str | None = None):
        """Initialize the Vertex AI plugin.

        Args:
            project_id: Optional Google Cloud project ID. If not provided,
                will attempt to detect from environment.
            location: Optional Google Cloud region. If not provided, will
                use a default region.
        """
        # If not set, projectId will be read by plugin
        project_id = project_id if project_id else os.getenv(const.GCLOUD_PROJECT)
        location = location if location else const.DEFAULT_REGION
        vertexai.init(project=project_id, location=location)

    def initialize(self, ai: GenkitRegistry) -> None:
        """Initialize the plugin by registering actions with the registry.

        This method registers the Vertex AI model actions with the provided
        registry, making them available for use in the Genkit framework.

        Args:
            ai: The registry to register actions with.

        Returns:
            None
        """
        for model_version in GeminiVersion:
            gemini = Gemini(model_version, ai)
            ai.define_model(
                name=vertexai_name(model_version),
                fn=gemini.generate,
                metadata=gemini.model_metadata,
            )

        for embed_model in EmbeddingModels:
            embedder = Embedder(embed_model)
            ai.define_embedder(
                name=vertexai_name(embed_model),
                fn=embedder.generate,
                metadata=embedder.model_metadata,
            )

        for imagen_version in ImagenVersion:
            imagen = Imagen(imagen_version)
            ai.define_model(
                name=vertexai_name(imagen_version),
                fn=imagen.generate,
                metadata=imagen.model_metadata,
            )
