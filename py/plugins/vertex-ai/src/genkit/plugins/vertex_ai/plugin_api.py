# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Google Cloud Vertex AI Plugin for Genkit."""

import logging
import os

import vertexai
from genkit.core.action import ActionKind
from genkit.core.plugin_abc import Plugin
from genkit.core.registry import Registry
from genkit.plugins.vertex_ai import constants as const
from genkit.plugins.vertex_ai.gemini import Gemini, GeminiVersion

LOG = logging.getLogger(__name__)


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

    # This is 'gemini-1.5-pro' - the latest stable model
    VERTEX_AI_GENERATIVE_MODEL_NAME: str = GeminiVersion.GEMINI_1_5_FLASH.value

    def __init__(
        self, project_id: str | None = None, location: str | None = None
    ):
        """Initialize the Vertex AI plugin.

        Args:
            project_id: Optional Google Cloud project ID. If not provided,
                will attempt to detect from environment.
            location: Optional Google Cloud region. If not provided, will
                use a default region.
        """
        # If not set, projectId will be read by plugin
        project_id = (
            project_id if project_id else os.getenv(const.GCLOUD_PROJECT)
        )
        location = location if location else const.DEFAULT_REGION

        self._gemini = Gemini(self.VERTEX_AI_GENERATIVE_MODEL_NAME)
        vertexai.init(project=project_id, location=location)

    def initialize(self, registry: Registry) -> None:
        """Initialize the plugin by registering actions with the registry.

        This method registers the Vertex AI model actions with the provided
        registry, making them available for use in the Genkit framework.

        Args:
            registry: The registry to register actions with.
        """
        registry.register_action(
            kind=ActionKind.MODEL,
            name=vertexai_name(self.VERTEX_AI_GENERATIVE_MODEL_NAME),
            fn=self._gemini.handle_request,
            metadata={
                'model': {
                    'supports': {'multiturn': True},
                }
            },
        )
