# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import os

from genkit.plugins.google_ai.models import gemini
from genkit.plugins.google_ai.schemas import GoogleAiPluginOptions
from genkit.veneer.plugin import Plugin
from genkit.veneer.registry import GenkitRegistry
from google import genai

PLUGIN_NAME = 'googleai'


def googleai_name(name: str) -> str:
    """Create a Google AI action name.

    Args:
        name: Base name for the action.

    Returns:
        The fully qualified Google AI action name.
    """
    return f'{PLUGIN_NAME}/{name}'


class GoogleAi(Plugin):
    """Google Ai plugin for Firebase Genkit"""

    def __init__(self, plugin_params: GoogleAiPluginOptions | None = None):
        self.name = PLUGIN_NAME

        api_key = (
            plugin_params.api_key
            if plugin_params and plugin_params.api_key
            else os.getenv('GEMINI_API_KEY')
        )
        if not api_key:
            raise ValueError(
                'Gemini api key should be passed in plugin params '
                'or as a GEMINI_API_KEY environment variable'
            )
        self._client = genai.client.Client(api_key=api_key)

    def initialize(self, ai: GenkitRegistry) -> None:
        """Initialize the plugin by registering actions in the registry.

        Args:
            registry: the action registry.

        Returns:
            None
        """

        for name, model in gemini.SUPPORTED_MODELS.items():
            gemini_model = gemini.GeminiModel(self._client, name, model)
            ai.define_model(
                name=googleai_name(name),
                fn=gemini_model.generate_callback,
                metadata=gemini_model.metadata,
            )
