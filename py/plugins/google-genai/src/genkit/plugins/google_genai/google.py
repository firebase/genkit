# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
import os

from genkit.plugins.google_genai.models.gemini import GeminiModel, GeminiVersion
from genkit.plugins.google_genai.schemas import GoogleGenaiPluginOptions
from genkit.veneer.plugin import Plugin
from genkit.veneer.registry import GenkitRegistry
from google import genai

PLUGIN_NAME = 'google_genai'


def google_genai_name(name: str) -> str:
    """Create a Google AI action name.

    Args:
        name: Base name for the action.

    Returns:
        The fully qualified Google AI action name.
    """
    return f'{PLUGIN_NAME}/{name}'


class GoogleGenai(Plugin):
    """Google Ai plugin for Firebase Genkit"""

    name = PLUGIN_NAME

    def __init__(
        self,
        plugin_params: GoogleGenaiPluginOptions | None = None,
    ):
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
        pass
        self._client = (
            genai.client.Client(**plugin_params.model_dump())
            if plugin_params
            else genai.client.Client(api_key=api_key)
        )

    def initialize(self, ai: GenkitRegistry) -> None:
        """Initialize the plugin by registering actions in the registry.

        Args:
            registry: the action registry.

        Returns:
            None
        """

        for version in GeminiVersion:
            gemini_model = GeminiModel(version, self._client)
            ai.define_model(
                name=google_genai_name(version),
                fn=gemini_model.generate,
                metadata=gemini_model.metadata,
            )
