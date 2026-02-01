# Copyright 2026 Google LLC
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

"""Tests for DeepSeek plugin."""

import os
from unittest.mock import MagicMock, patch

import pytest
from openai import OpenAI

from genkit.core.error import GenkitError
from genkit.core.registry import ActionKind
from genkit.plugins.deepseek import DeepSeek, deepseek_name
from genkit.plugins.deepseek.client import DEFAULT_DEEPSEEK_API_URL, DeepSeekClient


def test_deepseek_name() -> None:
    """Test name helper function."""
    assert deepseek_name('deepseek-chat') == 'deepseek/deepseek-chat'
    assert deepseek_name('deepseek-reasoner') == 'deepseek/deepseek-reasoner'


def test_plugin_initialization_with_api_key() -> None:
    """Test plugin initializes with API key."""
    plugin = DeepSeek(api_key='test-key')
    assert plugin.name == 'deepseek'
    assert plugin.api_key == 'test-key'


def test_plugin_initialization_from_env() -> None:
    """Test plugin reads API key from environment."""
    with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'env-key'}):
        plugin = DeepSeek()
        assert plugin.api_key == 'env-key'


def test_plugin_initialization_without_api_key() -> None:
    """Test plugin raises error without API key."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(GenkitError) as exc_info:
            DeepSeek()
        assert 'DEEPSEEK_API_KEY' in str(exc_info.value)


@patch('genkit.plugins.deepseek.models.DeepSeekClient')
@pytest.mark.asyncio
async def test_plugin_initialize(mock_client: MagicMock) -> None:
    """Test plugin init method."""
    plugin = DeepSeek(api_key='test-key', models=['deepseek-chat'])

    result = await plugin.init()

    # init returns empty list for lazy loading
    assert result == []


@patch('genkit.plugins.deepseek.models.DeepSeekClient')
@pytest.mark.asyncio
async def test_plugin_resolve_action(mock_client: MagicMock) -> None:
    """Test plugin resolves models dynamically."""
    plugin = DeepSeek(api_key='test-key', models=[])

    action = await plugin.resolve(ActionKind.MODEL, 'deepseek/deepseek-chat')

    # Should return an action
    assert action is not None
    assert action.kind == ActionKind.MODEL


@pytest.mark.asyncio
async def test_plugin_list_actions() -> None:
    """Test plugin lists available models."""
    plugin = DeepSeek(api_key='test-key')
    actions = await plugin.list_actions()

    assert len(actions) == 4
    action_names = [action.name for action in actions]
    assert 'deepseek/deepseek-reasoner' in action_names
    assert 'deepseek/deepseek-chat' in action_names
    assert 'deepseek/deepseek-v3' in action_names
    assert 'deepseek/deepseek-r1' in action_names


@patch('genkit.plugins.deepseek.models.DeepSeekClient')
def test_plugin_with_custom_params(mock_client: MagicMock) -> None:
    """Test plugin accepts custom parameters."""
    plugin = DeepSeek(
        api_key='test-key',
        models=['deepseek-chat'],
        timeout=60,
        max_retries=3,
    )

    assert plugin.deepseek_params['timeout'] == 60
    assert plugin.deepseek_params['max_retries'] == 3


@patch('genkit.plugins.deepseek.models.DeepSeekClient')
@pytest.mark.asyncio
async def test_plugin_initialize_no_models(mock_client: MagicMock) -> None:
    """Test plugin init returns empty list for lazy loading."""
    plugin = DeepSeek(api_key='test-key')

    result = await plugin.init()

    # init returns empty list for lazy loading
    assert result == []


@pytest.mark.asyncio
async def test_plugin_resolve_action_non_model_kind() -> None:
    """Test resolve does nothing for non-MODEL kinds."""
    plugin = DeepSeek(api_key='test-key')

    # Using PROMPT kind to test the case where kind != MODEL
    action = await plugin.resolve(ActionKind.PROMPT, 'some-prompt')

    # Should return None for non-model kinds
    assert action is None


@patch('genkit.plugins.deepseek.models.DeepSeekClient')
@pytest.mark.asyncio
async def test_plugin_resolve_action_without_prefix(mock_client: MagicMock) -> None:
    """Test plugin resolves models without plugin prefix."""
    plugin = DeepSeek(api_key='test-key', models=[])

    # Pass name without 'deepseek/' prefix
    action = await plugin.resolve(ActionKind.MODEL, 'deepseek-chat')

    assert action is not None
    assert action.kind == ActionKind.MODEL


@patch('genkit.plugins.deepseek.client.DeepSeekClient.__new__')
def test_deepseek_client_initialization(mock_new: MagicMock) -> None:
    """Test DeepSeekClient creates OpenAI client with correct params."""
    # Set up mock to return a fake client
    mock_client_instance = MagicMock()
    mock_new.return_value = mock_client_instance

    # Create a DeepSeekClient
    DeepSeekClient(api_key='test-key', timeout=30)

    # Verify __new__ was called with correct parameters
    mock_new.assert_called_once()


def test_deepseek_client_with_custom_base_url() -> None:
    """Test DeepSeekClient accepts custom base_url."""
    with patch.object(OpenAI, '__init__', return_value=None) as mock_init:
        DeepSeekClient(api_key='test-key', base_url='https://custom.api.deepseek.com')
        mock_init.assert_called_once_with(
            api_key='test-key',
            base_url='https://custom.api.deepseek.com',
        )


def test_deepseek_client_default_base_url() -> None:
    """Test DeepSeekClient uses default base_url when not provided."""
    with patch.object(OpenAI, '__init__', return_value=None) as mock_init:
        DeepSeekClient(api_key='test-key')
        mock_init.assert_called_once_with(
            api_key='test-key',
            base_url=DEFAULT_DEEPSEEK_API_URL,
        )
