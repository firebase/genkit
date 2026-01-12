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

from genkit.core.registry import ActionKind
from genkit.plugins.ollama import Ollama
from genkit.plugins.ollama.embedders import EmbeddingDefinition
from genkit.plugins.ollama.models import ModelDefinition


class TestOllamaInit(unittest.TestCase):
    """Test cases for Ollama.__init__ plugin."""

    def test_init_with_models(self):
        """Test correct propagation of models param."""
        model_ref = ModelDefinition(name='test_model')
        plugin = Ollama(models=[model_ref])

        assert plugin.models[0] == model_ref

    def test_init_with_embedders(self):
        """Test correct propagation of embedders param."""
        embedder_ref = EmbeddingDefinition(name='test_embedder')
        plugin = Ollama(embedders=[embedder_ref])

        assert plugin.embedders[0] == embedder_ref

    def test_init_with_options(self):
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
async def test_init_returns_actions(ollama_plugin_instance):
    """PluginV2 init() should return actions (models + embedders) without namespacing."""
    ollama_plugin_instance.models = [ModelDefinition(name='test_model')]
    ollama_plugin_instance.embedders = [EmbeddingDefinition(name='test_embedder', dimensions=1024)]

    actions = await ollama_plugin_instance.init()

    assert len(actions) == 2
    assert {a.kind for a in actions} == {ActionKind.MODEL, ActionKind.EMBEDDER}
    assert {a.name for a in actions} == {'test_model', 'test_embedder'}


@pytest.mark.parametrize(
    'kind, name',
    [
        (ActionKind.MODEL, 'test_model'),
        (ActionKind.EMBEDDER, 'test_embedder'),
    ],
)
@pytest.mark.asyncio
async def test_resolve_returns_action(kind, name, ollama_plugin_instance):
    """PluginV2 resolve() should return an Action for models/embedders."""
    action = await ollama_plugin_instance.resolve(kind, name)
    assert action is not None
    assert action.kind == kind
    assert action.name == name


@pytest.mark.parametrize(
    'name, expected_name, clean_name',
    [
        ('mistral', 'ollama/mistral', 'mistral'),
        ('ollama/mistral', 'ollama/mistral', 'mistral'),
    ],
)
def test_create_model_action_cleans_name(name, expected_name, clean_name, ollama_plugin_instance):
    """_create_model_action should strip namespace from input names."""
    action = ollama_plugin_instance._create_model_action(ModelDefinition(name=name))
    assert action.kind == ActionKind.MODEL
    assert action.name == clean_name


@pytest.mark.parametrize(
    'name, expected_name, clean_name',
    [
        ('mistral', 'ollama/mistral', 'mistral'),
        ('ollama/mistral', 'ollama/mistral', 'mistral'),
    ],
)
def test_create_embedder_action_cleans_name(name, expected_name, clean_name, ollama_plugin_instance):
    """_create_embedder_action should strip namespace from input names."""
    action = ollama_plugin_instance._create_embedder_action(EmbeddingDefinition(name=name, dimensions=1024))
    assert action.kind == ActionKind.EMBEDDER
    assert action.name == clean_name


@pytest.mark.asyncio
async def test_list_returns_action_metadata(ollama_plugin_instance):
    """PluginV2 list_actions() should return ActionMetadata and await the async client."""

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
            MockModelResponse(model='test_embedder'),
        ]
    )

    def mock_client():
        return _client_mock

    ollama_plugin_instance.client = mock_client

    actions = await ollama_plugin_instance.list_actions()

    assert len(actions) == 2

    has_model = False
    for action in actions:
        if action.kind == ActionKind.MODEL:
            has_model = True
            break

    assert has_model

    has_embedder = False
    for action in actions:
        if action.kind == ActionKind.EMBEDDER:
            has_embedder = True
            break

    assert has_embedder
