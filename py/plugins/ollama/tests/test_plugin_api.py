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
from unittest.mock import ANY, AsyncMock, MagicMock

import ollama as ollama_api
import pytest
from pydantic import BaseModel

from genkit.ai import ActionKind, Genkit
from genkit.plugins.ollama import Ollama, ollama_name
from genkit.plugins.ollama.constants import DEFAULT_OLLAMA_SERVER_URL
from genkit.plugins.ollama.embedders import EmbeddingDefinition
from genkit.plugins.ollama.models import ModelDefinition
from genkit.types import GenerationCommonConfig


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


def test_initialize(ollama_plugin_instance):
    """Test initialize method of Ollama plugin."""
    ai_mock = MagicMock(spec=Genkit)
    model_ref = ModelDefinition(name='test_model')
    embedder_ref = EmbeddingDefinition(name='test_embedder')
    ollama_plugin_instance.models = [model_ref]
    ollama_plugin_instance.embedders = [embedder_ref]

    init_models = MagicMock()
    init_embedders = MagicMock()

    ollama_plugin_instance._initialize_models = init_models
    ollama_plugin_instance._initialize_embedders = init_embedders

    ollama_plugin_instance.initialize(ai_mock)

    init_models.assert_called_once_with(ai=ai_mock)
    init_embedders.assert_called_once_with(ai=ai_mock)


def test__initialize_models(ollama_plugin_instance):
    """Test _initialize_models method of Ollama plugin."""
    ai_mock = MagicMock(spec=Genkit)
    name = 'test_model'

    plugin = ollama_plugin_instance
    plugin.models = [ModelDefinition(name=name)]
    plugin._initialize_models(ai_mock)

    ai_mock.define_model.assert_called_once_with(
        name=ollama_name(name),
        fn=ANY,
        config_schema=GenerationCommonConfig,
        metadata={
            'label': f'Ollama - {name}',
            'multiturn': True,
            'system_role': True,
            'tools': False,
        },
    )


def test__initialize_embedders(ollama_plugin_instance):
    """Test _initialize_embedders method of Ollama plugin."""
    ai_mock = MagicMock(spec=Genkit)
    name = 'test_embedder'

    plugin = ollama_plugin_instance
    plugin.embedders = [
        EmbeddingDefinition(
            name=name,
            dimensions=1024,
        )
    ]
    plugin._initialize_embedders(ai_mock)

    ai_mock.define_embedder.assert_called_once_with(
        name=ollama_name(name),
        fn=ANY,
        config_schema=ollama_api.Options,
        metadata={
            'label': f'Ollama Embedding - {name}',
            'dimensions': 1024,
            'supports': {
                'input': ['text'],
            },
        },
    )


@pytest.mark.parametrize(
    'kind, name',
    [
        (ActionKind.MODEL, 'test_model'),
        (ActionKind.EMBEDDER, 'test_embedder'),
    ],
)
def test_resolve_action(kind, name, ollama_plugin_instance):
    """Unit Tests for resolve action method."""
    ai_mock = MagicMock(spec=Genkit)
    ollama_plugin_instance.resolve_action(ai_mock, kind, name)

    if kind == ActionKind.MODEL:
        ai_mock.define_model.assert_called_once_with(
            name=ollama_name(name),
            fn=ANY,
            config_schema=GenerationCommonConfig,
            metadata={
                'label': f'Ollama - {name}',
                'multiturn': True,
                'system_role': True,
                'tools': False,
            },
        )
    else:
        ai_mock.define_embedder.assert_called_once_with(
            name=ollama_name(name),
            fn=ANY,
            config_schema=ollama_api.Options,
            metadata={
                'label': f'Ollama Embedding - {name}',
                'dimensions': None,
                'supports': {
                    'input': ['text'],
                },
            },
        )


@pytest.mark.parametrize(
    'name, expected_name, clean_name',
    [
        ('mistral', 'ollama/mistral', 'mistral'),
        ('ollama/mistral', 'ollama/mistral', 'mistral'),
    ],
)
def test_define_ollama_model(name, expected_name, clean_name, ollama_plugin_instance):
    """Unit tests for _define_ollama_model method."""
    ai_mock = MagicMock(spec=Genkit)

    ollama_plugin_instance._define_ollama_model(ai_mock, ModelDefinition(name=name))

    ai_mock.define_model.assert_called_once_with(
        name=expected_name,
        fn=ANY,
        config_schema=GenerationCommonConfig,
        metadata={
            'label': f'Ollama - {clean_name}',
            'multiturn': True,
            'system_role': True,
            'tools': False,
        },
    )


@pytest.mark.parametrize(
    'name, expected_name, clean_name',
    [
        ('mistral', 'ollama/mistral', 'mistral'),
        ('ollama/mistral', 'ollama/mistral', 'mistral'),
    ],
)
def test_define_ollama_embedder(name, expected_name, clean_name, ollama_plugin_instance):
    """Unit tests for _define_ollama_embedder method."""
    ai_mock = MagicMock(spec=Genkit)

    ollama_plugin_instance._define_ollama_embedder(ai_mock, EmbeddingDefinition(name=name, dimensions=1024))

    ai_mock.define_embedder.assert_called_once_with(
        name=expected_name,
        fn=ANY,
        config_schema=ollama_api.Options,
        metadata={
            'label': f'Ollama Embedding - {clean_name}',
            'dimensions': 1024,
            'supports': {
                'input': ['text'],
            },
        },
    )


def test_list_actions(ollama_plugin_instance):
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
            MockModelResponse(model='test_embedder'),
        ]
    )

    def mock_client():
        return _client_mock

    ollama_plugin_instance.client = mock_client

    actions = ollama_plugin_instance.list_actions

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
