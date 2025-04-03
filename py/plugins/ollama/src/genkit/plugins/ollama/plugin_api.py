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

"""Ollama Plugin for Genkit."""

import ollama as ollama_api
from genkit.ai.plugin import Plugin
from genkit.ai.registry import GenkitRegistry
from genkit.plugins.ollama.embedders import OllamaEmbedder
from genkit.plugins.ollama.models import (
    OllamaAPITypes,
    OllamaModel,
    OllamaPluginParams,
)


def ollama_name(name: str) -> str:
    """Get the name of the Ollama model.

    Args:
        name: The name of the Ollama model.

    Returns:
        The name of the Ollama model.
    """
    return f'ollama/{name}'


class Ollama(Plugin):
    """Ollama plugin for Genkit."""

    name = 'ollama'

    def __init__(self, plugin_params: OllamaPluginParams):
        """Initialize the Ollama plugin.

        Args:
            plugin_params: The plugin parameters to initialize the plugin with.
        """
        self.plugin_params = plugin_params
        self.client = ollama_api.AsyncClient(host=self.plugin_params.server_address.unicode_string())

    def initialize(self, ai: GenkitRegistry) -> None:
        """Initialize the Ollama plugin.

        Args:
            ai: The AI registry to initialize the plugin with.
        """
        self._initialize_models(ai=ai)
        self._initialize_embedders(ai=ai)

    def _initialize_models(self, ai: GenkitRegistry):
        for model_definition in self.plugin_params.models:
            model = OllamaModel(
                client=self.client,
                model_definition=model_definition,
            )
            ai.define_model(
                name=ollama_name(model_definition.name),
                fn=model.generate,
                metadata={
                    'multiturn': model_definition.api_type == OllamaAPITypes.CHAT,
                    'system_role': True,
                },
            )

    def _initialize_embedders(self, ai: GenkitRegistry):
        for embedding_definition in self.plugin_params.embedders:
            embedder = OllamaEmbedder(
                client=self.client,
                embedding_definition=embedding_definition,
            )
            ai.define_embedder(
                name=ollama_name(embedding_definition.name),
                fn=embedder.embed,
                metadata={
                    'label': f'Ollama Embedding - {embedding_definition.name}',
                    'dimensions': embedding_definition.dimensions,
                    'supports': {
                        'input': ['text'],
                    },
                },
            )
