# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0


"""ModelGarden API Compatible Plugin for Genkit."""

import os
import pdb
from pprint import pprint

from pydantic import BaseModel, ConfigDict

from genkit.ai.plugin import Plugin
from genkit.ai.registry import GenkitRegistry
from genkit.plugins.vertex_ai import constants as const

from .model_garden import SUPPORTED_OPENAI_FORMAT_MODELS, ModelGarden


class CommonPluginOptions(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    project_id: str | None = None
    location: str | None = None
    models: list[str] | None = None


def vertexai_name(name: str) -> str:
    """Create a Vertex AI action name.

    Args:
        name: Base name for the action.

    Returns:
        The fully qualified Vertex AI action name.
    """
    return f'vertexai/{name}'


class VertexAIModelGarden(Plugin):
    """Model Garden plugin for Genkit.

    This plugin provides integration with Google Cloud's Vertex AI platform,
    enabling the use of Vertex AI models and services within the Genkit
    framework. It handles initialization of the Model Garden client and
    registration of model actions.
    """

    name = 'modelgarden'

    def __init__(self, **kwargs):
        """Initialize the plugin by registering actions with the registry."""
        self.plugin_options = CommonPluginOptions(
            project_id=kwargs.get('project_id', os.getenv(const.GCLOUD_PROJECT)),
            location=kwargs.get('location', const.DEFAULT_REGION),
            models=kwargs.get('models'),
        )

    def initialize(self, ai: GenkitRegistry) -> None:
        """Handles actions for various openaicompatible models."""
        for model in self.plugin_options.models:
            openai_model = SUPPORTED_OPENAI_FORMAT_MODELS.get(model).label
            if openai_model:
                ModelGarden.to_openai_compatible_model(
                    ai,
                    model=openai_model,
                    location=self.plugin_options.location,
                    project_id=self.plugin_options.project_id,
                )
