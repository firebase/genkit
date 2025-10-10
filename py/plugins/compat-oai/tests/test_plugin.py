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

from unittest.mock import ANY, MagicMock, patch

import pytest
from openai.types import Model

from genkit.ai._aio import Genkit
from genkit.core.action import ActionMetadata
from genkit.core.action.types import ActionKind
from genkit.plugins.compat_oai import OpenAIConfig
from genkit.plugins.compat_oai.models.model_info import SUPPORTED_OPENAI_MODELS
from genkit.plugins.compat_oai.openai_plugin import OpenAI, openai_model


def test_openai_plugin_initialize() -> None:
    """Test OpenAI plugin registry initialization."""
    registry = MagicMock(spec=Genkit)
    plugin = OpenAI(api_key='test-key')

    with patch('genkit.plugins.compat_oai.models.OpenAIModelHandler.get_model_handler') as mock_get_handler:
        mock_handler = MagicMock()
        mock_get_handler.return_value = mock_handler

        plugin.initialize(registry)

        assert mock_get_handler.call_count == len(SUPPORTED_OPENAI_MODELS)
        assert registry.define_model.call_count == len(SUPPORTED_OPENAI_MODELS)


@pytest.mark.parametrize(
    'kind, name',
    [(ActionKind.MODEL, 'gpt-3.5-turbo')],
)
def test_openai_plugin_resolve_action(kind, name):
    """Unit Tests for resolve action method."""
    plugin = OpenAI(api_key='test-key')
    registry = MagicMock(spec=Genkit)
    plugin.resolve_action(registry, kind, name)

    model_info = SUPPORTED_OPENAI_MODELS[name]

    registry.define_model.assert_called_once_with(
        name=f'openai/{name}',
        fn=ANY,
        config_schema=OpenAIConfig,
        metadata={
            'model': {
                'label': model_info.label,
                'supports': {
                    'media': False,
                    'multiturn': True,
                    'output': [
                        'json_mode',
                        'text',
                    ],
                    'system_role': True,
                    'tools': True,
                },
            },
        },
    )


def test_openai_plugin_list_actions() -> None:
    entries = [
        Model(id='gpt-4-0613', created=1686588896, object='model', owned_by='openai'),
        Model(id='gpt-4', created=1687882411, object='model', owned_by='openai'),
        Model(id='gpt-3.5-turbo', created=1677610602, object='model', owned_by='openai'),
        Model(id='o4-mini-deep-research-2025-06-26', created=1750866121, object='model', owned_by='system'),
        Model(id='codex-mini-latest', created=1746673257, object='model', owned_by='system'),
        Model(id='text-embedding-ada-002', created=1671217299, object='model', owned_by='openai-internal'),
    ]
    plugin = OpenAI(api_key='test-key')
    mock_client = MagicMock()

    mock_result_ = MagicMock()
    mock_result_.data = entries
    mock_client.models.list.return_value = mock_result_

    plugin._openai_client = mock_client

    actions: list[ActionMetadata] = plugin.list_actions
    mock_client.models.list.assert_called_once()
    _ = plugin.list_actions
    mock_client.models.list.assert_called_once()

    assert len(actions) == len(entries)
    assert actions[0].name == 'openai/gpt-4-0613'
    assert actions[-1].name == 'openai/text-embedding-ada-002'


@pytest.mark.parametrize(
    'kind, name',
    [(ActionKind.MODEL, 'model_doesnt_exist')],
)
def test_openai_plugin_resolve_action_not_found(kind, name):
    """Unit Tests for resolve action method."""

    plugin = OpenAI(api_key='test-key')
    registry = MagicMock(spec=Genkit)
    plugin.resolve_action(registry, kind, name)

    registry.define_model.assert_called_once()


def test_openai_model_function() -> None:
    """Test openai_model function."""
    assert openai_model('gpt-4') == 'openai/gpt-4'
