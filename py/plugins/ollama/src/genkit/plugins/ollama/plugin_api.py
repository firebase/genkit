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

from functools import partial

import structlog

import ollama as ollama_api
from genkit.ai import Plugin
from genkit.blocks.embedding import EmbedderOptions, EmbedderSupports, embedder, embedder_action_metadata
from genkit.blocks.model import model, model_action_metadata
from genkit.core.action import Action
from genkit.core.registry import ActionKind
from genkit.core.schema import to_json_schema
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

    async def init(self):
        """Return eagerly-initialized model and embedder actions."""
        actions = []
        for model_definition in self.models:
            actions.append(self._create_model_action(model_definition))
        for embedder_definition in self.embedders:
            actions.append(self._create_embedder_action(embedder_definition))
        return actions

    async def resolve(self, action_type: ActionKind, name: str):
        """Resolve a model or embedder action on-demand."""
        clean_name = name.replace(f'{OLLAMA_PLUGIN_NAME}/', '') if name.startswith(OLLAMA_PLUGIN_NAME) else name

        if action_type == ActionKind.MODEL:
            # Prefer configured model definitions (api_type, supports) when available.
            for model_def in self.models:
                configured_name = (
                    model_def.name.replace(OLLAMA_PLUGIN_NAME + '/', '')
                    if model_def.name.startswith(OLLAMA_PLUGIN_NAME)
                    else model_def.name
                )
                if configured_name == clean_name:
                    return self._create_model_action(model_def)
            return self._create_model_action(ModelDefinition(name=clean_name))
        elif action_type == ActionKind.EMBEDDER:
            for embedder_def in self.embedders:
                configured_name = (
                    embedder_def.name.replace(OLLAMA_PLUGIN_NAME + '/', '')
                    if embedder_def.name.startswith(OLLAMA_PLUGIN_NAME)
                    else embedder_def.name
                )
                if configured_name == clean_name:
                    return self._create_embedder_action(embedder_def)
            return self._create_embedder_action(EmbeddingDefinition(name=clean_name))
        return None

    async def list_actions(self):
        """List all available Ollama models and embedders."""
        _client = self.client()
        response = await _client.list()

        actions = []
        for model_info in response.models:
            _name = model_info.model
            if 'embed' in _name:
                actions.append(
                    embedder_action_metadata(
                        name=_name,
                        options=EmbedderOptions(
                            config_schema=to_json_schema(ollama_api.Options),
                            label=f'Ollama Embedding - {_name}',
                            supports=EmbedderSupports(input=['text']),
                        ),
                    )
                )
            else:
                actions.append(
                    model_action_metadata(
                        name=_name,
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

    def _create_model_action(self, model_ref: ModelDefinition) -> Action:
        """Create an Ollama model action (doesn't register)."""
        _clean_name = (
            model_ref.name.replace(OLLAMA_PLUGIN_NAME + '/', '')
            if model_ref.name.startswith(OLLAMA_PLUGIN_NAME)
            else model_ref.name
        )

        model_ref.name = _clean_name
        ollama_model = OllamaModel(
            client=self.client,
            model_definition=model_ref,
        )

        return model(
            name=model_ref.name,
            fn=ollama_model.generate,
            config_schema=GenerationCommonConfig,
            metadata={
                'label': f'Ollama - {_clean_name}',
                'multiturn': model_ref.api_type == OllamaAPITypes.CHAT,
                'system_role': True,
                'tools': model_ref.supports.tools,
            },
        )

    def _create_embedder_action(self, embedder_ref: EmbeddingDefinition) -> Action:
        """Create an Ollama embedder action (doesn't register)."""
        _clean_name = (
            embedder_ref.name.replace(OLLAMA_PLUGIN_NAME + '/', '')
            if embedder_ref.name.startswith(OLLAMA_PLUGIN_NAME)
            else embedder_ref.name
        )

        embedder_ref.name = _clean_name
        ollama_embedder = OllamaEmbedder(
            client=self.client,
            embedding_definition=embedder_ref,
        )

        return embedder(
            name=embedder_ref.name,
            fn=ollama_embedder.embed,
            options=EmbedderOptions(
                config_schema=to_json_schema(ollama_api.Options),
                label=f'Ollama Embedding - {_clean_name}',
                dimensions=embedder_ref.dimensions,
                supports=EmbedderSupports(input=['text']),
            ),
        )
