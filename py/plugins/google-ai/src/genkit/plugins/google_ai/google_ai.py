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

import os

from google import genai

from genkit.ai.plugin import Plugin
from genkit.ai.registry import GenkitRegistry
from genkit.plugins.google_ai.models import gemini
from genkit.plugins.google_ai.schemas import GoogleAiPluginOptions

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
    """Google Ai plugin for Genkit"""

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
