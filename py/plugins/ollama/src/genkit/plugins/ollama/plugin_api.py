# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""
Ollama Plugin for Genkit.
"""

import logging

import ollama as ollama_api
from genkit.plugins.ollama.embedders import OllamaEmbedder
from genkit.plugins.ollama.models import (
    OllamaAPITypes,
    OllamaModel,
    OllamaPluginParams,
)
from genkit.veneer.plugin import Plugin
from genkit.veneer.registry import GenkitRegistry

LOG = logging.getLogger(__name__)


def ollama_name(name: str) -> str:
    return f'ollama/{name}'


class Ollama(Plugin):
    name = 'ollama'

    def __init__(self, plugin_params: OllamaPluginParams):
        self.plugin_params = plugin_params
        self.client = ollama_api.AsyncClient(
            host=self.plugin_params.server_address.unicode_string()
        )

    def initialize(self, ai: GenkitRegistry) -> None:
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
                    'multiturn': model_definition.api_type
                    == OllamaAPITypes.CHAT,
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
