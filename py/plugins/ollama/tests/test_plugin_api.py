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

"""Unit tests for Ollama Plugin."""

import unittest
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from genkit.ai import ActionKind
from genkit.plugins.ollama import Ollama, ollama_name
from genkit.plugins.ollama.embedders import EmbeddingDefinition
from genkit.plugins.ollama.models import ModelDefinition


class TestOllamaInit(unittest.TestCase):
    """Test cases for Ollama.__init__ plugin."""

    def test_init_with_models(self) -> None:
        """Test correct propagation of models param."""
        model_ref = ModelDefinition(name='test_model')
        plugin = Ollama(models=[model_ref])

        assert plugin.models[0] == model_ref

    def test_init_with_embedders(self) -> None:
        """Test correct propagation of embedders param."""
        embedder_ref = EmbeddingDefinition(name='test_embedder')
        plugin = Ollama(embedders=[embedder_ref])

        assert plugin.embedders[0] == embedder_ref

    def test_init_with_options(self) -> None:
        """Test correct propagation of other options param."""
        model_ref = ModelDefinition(name='test_model')
        embedder_ref = EmbeddingDefinition(name='test_embedder')
        server_address = 'new.server.address'
        headers = {'Content-Type': 'json'}

        plugin = Ollama(
            models=[model_ref],
            embedders=[embedder_ref],
            server_address=server_address,
            request_headers=headers,
        )

        assert plugin.embedders[0] == embedder_ref
        assert plugin.models[0] == model_ref
        assert plugin.server_address == server_address
        assert plugin.request_headers == headers


@pytest.mark.asyncio
async def test_initialize(ollama_plugin_instance) -> None:
    """Test init method of Ollama plugin."""
    model_ref = ModelDefinition(name='test_model')
    embedder_ref = EmbeddingDefinition(name='test_embedder')
    ollama_plugin_instance.models = [model_ref]
    ollama_plugin_instance.embedders = [embedder_ref]

    result = await ollama_plugin_instance.init()

    # init returns actions for pre-configured models and embedders
    assert len(result) == 2
    assert result[0].kind == ActionKind.MODEL
    assert result[1].kind == ActionKind.EMBEDDER


# _initialize_models and _initialize_embedders methods no longer exist in new plugin architecture
# Models and embedders are now created lazily via the resolve() method


@pytest.mark.parametrize(
    'kind, name',
    [
        (ActionKind.MODEL, 'test_model'),
        (ActionKind.EMBEDDER, 'test_embedder'),
    ],
)
@pytest.mark.asyncio
async def test_resolve_action(kind, name, ollama_plugin_instance) -> None:
    """Unit Tests for resolve action method."""
    action = await ollama_plugin_instance.resolve(kind, ollama_name(name))

    assert action is not None
    assert action.kind == kind
    assert action.name == ollama_name(name)

    if kind == ActionKind.MODEL:
        assert action.metadata['model']['label'] == f'Ollama - {name}'
        assert action.metadata['model']['multiturn']
        assert action.metadata['model']['system_role']
    else:
        assert action.metadata['embedder']['label'] == f'Ollama Embedding - {name}'
        assert action.metadata['embedder']['supports'] == {'input': ['text']}


# _define_ollama_model and _define_ollama_embedder methods no longer exist in new plugin architecture
# Actions are now created via _create_model_action and _create_embedder_action methods


@pytest.mark.asyncio
async def test_list_actions(ollama_plugin_instance) -> None:
    """Unit tests for list_actions method."""

    class MockModelResponse(BaseModel):
        model: str

    class MockListResponse(BaseModel):
        models: list[MockModelResponse]

    _client_mock = MagicMock()
    list_method_mock = AsyncMock()
    _client_mock.list = list_method_mock

    list_method_mock.return_value = MockListResponse(
        models=[
            MockModelResponse(model='test_model'),
            MockModelResponse(model='test_embed'),
        ]
    )

    def mock_client():
        return _client_mock

    ollama_plugin_instance.client = mock_client

    actions = await ollama_plugin_instance.list_actions()

    assert len(actions) == 2

    has_model = False
    for action in actions:
        if hasattr(action, 'name') and 'test_model' in action.name:
            has_model = True
            break

    assert has_model

    has_embedder = False
    for action in actions:
        if hasattr(action, 'name') and 'test_embed' in action.name:
            has_embedder = True
            break

    assert has_embedder
