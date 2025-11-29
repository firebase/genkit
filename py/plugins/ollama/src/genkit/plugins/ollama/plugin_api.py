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

import asyncio
from functools import cached_property, partial

import structlog

import ollama as ollama_api
from genkit.ai import GenkitRegistry, Plugin
from genkit.blocks.embedding import embedder_action_metadata
from genkit.blocks.model import model_action_metadata
from genkit.core.registry import ActionKind
from genkit.plugins.ollama.constants import (
    DEFAULT_OLLAMA_SERVER_URL,
    OllamaAPITypes,
)
from genkit.plugins.ollama.embedders import (
    EmbeddingDefinition,
    OllamaEmbedder,
)
from genkit.plugins.ollama.models import (
    ModelDefinition,
    OllamaModel,
)
from genkit.types import GenerationCommonConfig

OLLAMA_PLUGIN_NAME = 'ollama'
logger = structlog.get_logger(__name__)


def ollama_name(name: str) -> str:
    """Get the name of the Ollama model.

    Args:
        name: The name of the Ollama model.

    Returns:
        The name of the Ollama model.
    """
    return f'{OLLAMA_PLUGIN_NAME}/{name}'


class Ollama(Plugin):
    """Ollama plugin for Genkit.

    This plugin integrates Ollama models and embedding capabilities into Genkit
    for local or custom server-based generative AI applications.
    """

    name = OLLAMA_PLUGIN_NAME

    def __init__(
        self,
        models: list[ModelDefinition] | None = None,
        embedders: list[EmbeddingDefinition] | None = None,
        server_address: str | None = None,
        request_headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize the Ollama plugin.

        Args:
            models: An Optional list of model definitions to be registered with Genkit.
            embedders: An Optional list of embedding model definitions to be
                registered with Genkit.
            server_address: The URL of the Ollama server. Defaults to a predefined
                Ollama server URL if not provided.
            request_headers: Optional HTTP headers to include with requests to the
                Ollama server.
        """
        self.models = models or []
        self.embedders = embedders or []
        self.server_address = server_address or DEFAULT_OLLAMA_SERVER_URL
        self.request_headers = request_headers or {}

        self.client = partial(ollama_api.AsyncClient, host=self.server_address)

    def initialize(self, ai: GenkitRegistry) -> None:
        """Initialize the Ollama plugin.

        Registers the defined Ollama models and embedders with the Genkit AI registry.

        Args:
            ai: The AI registry to initialize the plugin with.
        """
        self._initialize_models(ai=ai)
        self._initialize_embedders(ai=ai)

    def _initialize_models(self, ai: GenkitRegistry) -> None:
        """Initializes and registers the specified Ollama models with Genkit.

        Args:
            ai: The Genkit AI registry instance.
        """
        for model_definition in self.models:
            self._define_ollama_model(ai, model_definition)

    def _initialize_embedders(self, ai: GenkitRegistry) -> None:
        """Initializes and registers the specified Ollama embedders with Genkit.

        Args:
            ai: The Genkit AI registry instance.
        """
        for embedding_definition in self.embedders:
            self._define_ollama_embedder(ai, embedding_definition)

    def resolve_action(
        self,
        ai: GenkitRegistry,
        kind: ActionKind,
        name: str,
    ) -> None:
        """Resolves and action.

        Args:
            ai: The Genkit registry.
            kind: The kind of action to resolve.
            name: The name of the action to resolve.
        """
        if kind == ActionKind.MODEL:
            self._define_ollama_model(ai, ModelDefinition(name=name))
        elif kind == ActionKind.EMBEDDER:
            self._define_ollama_embedder(ai, EmbeddingDefinition(name=name))

    def _define_ollama_model(self, ai: GenkitRegistry, model_ref: ModelDefinition) -> None:
        """Defines and registers an Ollama model with Genkit.

        Cleans the model name, instantiates an OllamaModel, and registers it
        with the provided Genkit AI registry, including metadata about its capabilities.

        Args:
            ai: The Genkit AI registry instance.
            model_ref: The definition of the model to be registered.
        """
        _clean_name = (
            model_ref.name.replace(OLLAMA_PLUGIN_NAME + '/', '')
            if model_ref.name.startswith(OLLAMA_PLUGIN_NAME)
            else model_ref.name
        )

        model_ref.name = _clean_name
        model = OllamaModel(
            client=self.client,
            model_definition=model_ref,
        )

        ai.define_model(
            name=ollama_name(model_ref.name),
            fn=model.generate,
            config_schema=GenerationCommonConfig,
            metadata={
                'label': f'Ollama - {_clean_name}',
                'multiturn': model_ref.api_type == OllamaAPITypes.CHAT,
                'system_role': True,
                'tools': model_ref.supports.tools,
            },
        )

    def _define_ollama_embedder(self, ai: GenkitRegistry, embedder_ref: EmbeddingDefinition) -> None:
        """Defines and registers an Ollama embedder with Genkit.

        Cleans the embedder name, instantiates an OllamaEmbedder, and registers it
        with the provided Genkit AI registry, including metadata about its capabilities
        and expected output dimensions.

        Args:
            ai: The Genkit AI registry instance.
            embedder_ref: The definition of the embedding model to be registered.
        """
        _clean_name = (
            embedder_ref.name.replace(OLLAMA_PLUGIN_NAME + '/', '')
            if embedder_ref.name.startswith(OLLAMA_PLUGIN_NAME)
            else embedder_ref.name
        )

        embedder_ref.name = _clean_name
        embedder = OllamaEmbedder(
            client=self.client,
            embedding_definition=embedder_ref,
        )

        ai.define_embedder(
            name=ollama_name(embedder_ref.name),
            fn=embedder.embed,
            config_schema=ollama_api.Options,
            metadata={
                'label': f'Ollama Embedding - {_clean_name}',
                'dimensions': embedder_ref.dimensions,
                'supports': {
                    'input': ['text'],
                },
            },
        )

    @cached_property
    def list_actions(self) -> list[dict[str, str]]:
        """Generate a list of available actions or models.

        Returns:
            list[ActionMetadata]: A list of ActionMetadata objects, each with the following attributes:
                - name (str): The name of the action or model.
                - kind (ActionKind): The type or category of the action.
                - info (dict): The metadata dictionary describing the model configuration and properties.
                - config_schema (type): The schema class used for validating the model's configuration.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        _client = self.client()
        response = loop.run_until_complete(_client.list())

        actions = []
        for model in response.models:
            _name = model.model
            if 'embed' in _name:
                actions.append(
                    embedder_action_metadata(
                        name=ollama_name(_name),
                        config_schema=ollama_api.Options,
                        info={
                            'label': f'Ollama Embedding - {_name}',
                            'dimensions': None,
                            'supports': {
                                'input': ['text'],
                            },
                        },
                    )
                )
            else:
                actions.append(
                    model_action_metadata(
                        name=ollama_name(_name),
                        config_schema=GenerationCommonConfig,
                        info={
                            'label': f'Ollama - {_name}',
                            'multiturn': True,
                            'system_role': True,
                            'tools': False,
                        },
                    )
                )
        return actions
