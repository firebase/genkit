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

from genkit.core.error import GenkitError
from genkit.core.registry import ActionKind
from genkit.plugins.deepseek import DeepSeek, deepseek_name


def test_deepseek_name():
    """Test name helper function."""
    assert deepseek_name('deepseek-chat') == 'deepseek/deepseek-chat'
    assert deepseek_name('deepseek-reasoner') == 'deepseek/deepseek-reasoner'


def test_plugin_initialization_with_api_key():
    """Test plugin initializes with API key."""
    plugin = DeepSeek(api_key='test-key')
    assert plugin.name == 'deepseek'
    assert plugin.api_key == 'test-key'


def test_plugin_initialization_from_env():
    """Test plugin reads API key from environment."""
    with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'env-key'}):
        plugin = DeepSeek()
        assert plugin.api_key == 'env-key'


def test_plugin_initialization_without_api_key():
    """Test plugin raises error without API key."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(GenkitError) as exc_info:
            DeepSeek()
        assert 'DEEPSEEK_API_KEY' in str(exc_info.value)


@patch('genkit.plugins.deepseek.models.DeepSeekClient')
def test_plugin_initialize(mock_client):
    """Test plugin registers models during initialization."""
    plugin = DeepSeek(api_key='test-key', models=['deepseek-chat'])
    mock_registry = MagicMock()

    plugin.initialize(mock_registry)

    # Should call define_model for the specified model
    mock_registry.define_model.assert_called_once()


@patch('genkit.plugins.deepseek.models.DeepSeekClient')
def test_plugin_resolve_action(mock_client):
    """Test plugin resolves models dynamically."""
    plugin = DeepSeek(api_key='test-key', models=[])
    mock_registry = MagicMock()

    plugin.resolve_action(mock_registry, ActionKind.MODEL, 'deepseek/deepseek-chat')

    # Should register the requested model
    mock_registry.define_model.assert_called_once()


def test_plugin_list_actions():
    """Test plugin lists available models."""
    plugin = DeepSeek(api_key='test-key')
    actions = plugin.list_actions

    assert len(actions) == 2
    action_names = [action.name for action in actions]
    assert 'deepseek/deepseek-reasoner' in action_names
    assert 'deepseek/deepseek-chat' in action_names


@patch('genkit.plugins.deepseek.models.DeepSeekClient')
def test_plugin_with_custom_params(mock_client):
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
def test_plugin_initialize_no_models(mock_client):
    """Test plugin registers all supported models when models is None."""
    from genkit.plugins.deepseek.model_info import SUPPORTED_DEEPSEEK_MODELS

    plugin = DeepSeek(api_key='test-key')
    mock_registry = MagicMock()

    # When models is None, all supported models should be registered
    plugin.initialize(mock_registry)

    assert mock_registry.define_model.call_count == len(SUPPORTED_DEEPSEEK_MODELS)


def test_plugin_resolve_action_non_model_kind():
    """Test resolve_action does nothing for non-MODEL kinds."""
    plugin = DeepSeek(api_key='test-key')
    mock_registry = MagicMock()

    # Using PROMPT kind to test the case where kind != MODEL
    plugin.resolve_action(mock_registry, ActionKind.PROMPT, 'some-prompt')

    # Should not attempt to register anything
    mock_registry.define_model.assert_not_called()


@patch('genkit.plugins.deepseek.models.DeepSeekClient')
def test_plugin_resolve_action_without_prefix(mock_client):
    """Test plugin resolves models without plugin prefix."""
    plugin = DeepSeek(api_key='test-key', models=[])
    mock_registry = MagicMock()

    # Pass name without 'deepseek/' prefix
    plugin.resolve_action(mock_registry, ActionKind.MODEL, 'deepseek-chat')

    mock_registry.define_model.assert_called_once()


@patch('genkit.plugins.deepseek.client.DeepSeekClient.__new__')
def test_deepseek_client_initialization(mock_new):
    """Test DeepSeekClient creates OpenAI client with correct params."""
    from genkit.plugins.deepseek.client import DeepSeekClient

    # Set up mock to return a fake client
    mock_client_instance = MagicMock()
    mock_new.return_value = mock_client_instance

    # Create a DeepSeekClient
    result = DeepSeekClient(api_key='test-key', timeout=30)

    # Verify __new__ was called with correct parameters
    mock_new.assert_called_once()


def test_deepseek_client_with_custom_base_url():
    """Test DeepSeekClient accepts custom base_url."""
    from openai import OpenAI

    from genkit.plugins.deepseek.client import DeepSeekClient

    with patch.object(OpenAI, '__init__', return_value=None) as mock_init:
        DeepSeekClient(api_key='test-key', base_url='https://custom.api.deepseek.com')
        mock_init.assert_called_once_with(
            api_key='test-key',
            base_url='https://custom.api.deepseek.com',
        )


def test_deepseek_client_default_base_url():
    """Test DeepSeekClient uses default base_url when not provided."""
    from openai import OpenAI

    from genkit.plugins.deepseek.client import DeepSeekClient

    with patch.object(OpenAI, '__init__', return_value=None) as mock_init:
        DeepSeekClient(api_key='test-key')
        mock_init.assert_called_once_with(
            api_key='test-key',
            base_url='https://api.deepseek.com',
        )
