# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""
Ollama Plugin for Genkit.
"""

import logging
from functools import cached_property
from typing import Type

from genkit.core.action import ActionKind
from genkit.core.registry import Registry
from genkit.plugins.ollama.models import (
    AsyncOllamaModel,
    OllamaAPITypes,
    OllamaModel,
    OllamaPluginParams,
)
from genkit.veneer.plugin import Plugin
from genkit.veneer.registry import GenkitRegistry

import ollama as ollama_api

LOG = logging.getLogger(__name__)


def ollama_name(name: str) -> str:
    return f'ollama/{name}'


class Ollama(Plugin):
    name = 'ollama'

    def __init__(self, plugin_params: OllamaPluginParams):
        self.plugin_params = plugin_params
        self._sync_client = ollama_api.Client(
            host=self.plugin_params.server_address.unicode_string()
        )
        self._async_client = ollama_api.AsyncClient(
            host=self.plugin_params.server_address.unicode_string()
        )

    @cached_property
    def client(self) -> ollama_api.AsyncClient | ollama_api.Client:
        client_cls = (
            ollama_api.AsyncClient
            if self.plugin_params.use_async_api
            else ollama_api.Client
        )
        return client_cls(
            host=self.plugin_params.server_address.unicode_string(),
        )

    @cached_property
    def ollama_model_class(self) -> Type[AsyncOllamaModel | OllamaModel]:
        return (
            AsyncOllamaModel
            if self.plugin_params.use_async_api
            else OllamaModel
        )

    def initialize(self, ai: GenkitRegistry) -> None:
        for model_definition in self.plugin_params.models:
            model = self.ollama_model_class(
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
        # TODO: introduce embedders here
        # for embedder in self.plugin_params.embedders:
