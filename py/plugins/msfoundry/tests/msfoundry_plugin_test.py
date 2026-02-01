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

"""Microsoft Foundry plugin tests.

Tests for the Microsoft Foundry plugin following the patterns from other Genkit plugins.

See: https://ai.azure.com/catalog/models

This module includes:
- Plugin initialization tests
- Model and embedder resolution tests
- Config schema validation tests
- Generate and embed functionality tests (with mocked client)
- Request/response conversion tests
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from genkit.core.registry import ActionKind
from genkit.plugins.msfoundry import (
    MSFOUNDRY_PLUGIN_NAME,
    MSFoundry,
    MSFoundryConfig,
    gpt4o,
    msfoundry_model,
)
from genkit.plugins.msfoundry.models.model import MSFoundryModel
from genkit.plugins.msfoundry.models.model_info import get_model_info
from genkit.types import (
    GenerateRequest,
    Message,
    Part,
    Role,
    TextPart,
)


def test_plugin_name() -> None:
    """Test that plugin name is correct."""
    assert MSFOUNDRY_PLUGIN_NAME == 'msfoundry'


def test_plugin_init() -> None:
    """Test plugin initialization with API key."""
    plugin = MSFoundry(
        api_key='test-key',
        endpoint='https://test.openai.azure.com/',
    )
    assert plugin.name == 'msfoundry'


def test_msfoundry_model_helper() -> None:
    """Test the msfoundry_model helper function."""
    assert msfoundry_model('gpt-4o') == 'msfoundry/gpt-4o'
    assert msfoundry_model('gpt-4') == 'msfoundry/gpt-4'
    assert msfoundry_model('gpt-3.5-turbo') == 'msfoundry/gpt-3.5-turbo'
    # Test with other provider models
    assert msfoundry_model('DeepSeek-V3.2') == 'msfoundry/DeepSeek-V3.2'
    assert msfoundry_model('claude-opus-4-5') == 'msfoundry/claude-opus-4-5'


def test_predefined_model_refs() -> None:
    """Test pre-defined model reference constants."""
    assert gpt4o == 'msfoundry/gpt-4o'


def test_config_schema() -> None:
    """Test MSFoundryConfig schema."""
    config = MSFoundryConfig(
        temperature=0.7,
        max_tokens=100,
        frequency_penalty=0.5,
        presence_penalty=0.5,
    )
    assert config.temperature == 0.7
    assert config.max_tokens == 100
    assert config.frequency_penalty == 0.5
    assert config.presence_penalty == 0.5


def test_config_schema_with_aliases() -> None:
    """Test MSFoundryConfig with camelCase aliases."""
    config = MSFoundryConfig.model_validate({
        'maxTokens': 200,
        'topP': 0.9,
        'frequencyPenalty': 0.3,
        'visualDetailLevel': 'high',
    })
    assert config.max_tokens == 200
    assert config.top_p == 0.9
    assert config.frequency_penalty == 0.3
    assert config.visual_detail_level == 'high'


@pytest.mark.asyncio
async def test_resolve_model() -> None:
    """Test resolving a model action."""
    plugin = MSFoundry(
        api_key='test-key',
        endpoint='https://test.openai.azure.com/',
    )
    action = await plugin.resolve(ActionKind.MODEL, 'msfoundry/gpt-4o')
    assert action is not None
    assert action.name == 'msfoundry/gpt-4o'
    assert action.kind == ActionKind.MODEL


@pytest.mark.asyncio
async def test_resolve_embedder() -> None:
    """Test resolving an embedder action."""
    plugin = MSFoundry(
        api_key='test-key',
        endpoint='https://test.openai.azure.com/',
    )
    action = await plugin.resolve(ActionKind.EMBEDDER, 'msfoundry/text-embedding-3-small')
    assert action is not None
    assert action.name == 'msfoundry/text-embedding-3-small'
    assert action.kind == ActionKind.EMBEDDER


@pytest.mark.asyncio
async def test_list_actions() -> None:
    """Test listing all available actions."""
    plugin = MSFoundry(
        api_key='test-key',
        endpoint='https://test.openai.azure.com/',
    )
    actions = await plugin.list_actions()
    assert len(actions) > 0

    # Check for expected models
    action_names = [a.name for a in actions]
    assert 'msfoundry/gpt-4o' in action_names
    assert 'msfoundry/gpt-4o-mini' in action_names
    assert 'msfoundry/gpt-4' in action_names

    # Check for embedders
    assert 'msfoundry/text-embedding-3-small' in action_names
    assert 'msfoundry/text-embedding-3-large' in action_names


@pytest.mark.asyncio
async def test_init_registers_actions() -> None:
    """Test that init() registers all supported actions."""
    plugin = MSFoundry(
        api_key='test-key',
        endpoint='https://test.openai.azure.com/',
    )
    actions = await plugin.init()
    assert len(actions) > 0

    # Should include both models and embedders
    model_actions = [a for a in actions if a.kind == ActionKind.MODEL]
    embedder_actions = [a for a in actions if a.kind == ActionKind.EMBEDDER]

    assert len(model_actions) > 0
    assert len(embedder_actions) > 0


class TestMSFoundryModel:
    """Tests for MSFoundryModel generation logic."""

    def test_normalize_config_with_none(self) -> None:
        """Test config normalization with None input."""
        mock_client = MagicMock()
        model = MSFoundryModel(model_name='gpt-4o', client=mock_client)

        config = model._normalize_config(None)
        assert isinstance(config, MSFoundryConfig)

    def test_normalize_config_with_msfoundry_config(self) -> None:
        """Test config normalization with MSFoundryConfig input."""
        mock_client = MagicMock()
        model = MSFoundryModel(model_name='gpt-4o', client=mock_client)

        input_config = MSFoundryConfig(temperature=0.5, max_tokens=100)
        config = model._normalize_config(input_config)
        assert config.temperature == 0.5
        assert config.max_tokens == 100

    def test_normalize_config_with_dict(self) -> None:
        """Test config normalization with dict input (camelCase keys)."""
        mock_client = MagicMock()
        model = MSFoundryModel(model_name='gpt-4o', client=mock_client)

        input_config = {'temperature': 0.8, 'maxTokens': 200, 'topP': 0.9}
        config = model._normalize_config(input_config)
        assert config.temperature == 0.8
        assert config.max_tokens == 200
        assert config.top_p == 0.9

    def test_to_openai_role_conversion(self) -> None:
        """Test role conversion from Genkit to OpenAI format."""
        mock_client = MagicMock()
        model = MSFoundryModel(model_name='gpt-4o', client=mock_client)

        assert model._to_openai_role(Role.USER) == 'user'
        assert model._to_openai_role(Role.MODEL) == 'assistant'
        assert model._to_openai_role(Role.SYSTEM) == 'system'
        assert model._to_openai_role(Role.TOOL) == 'tool'
        # Test string roles
        assert model._to_openai_role('user') == 'user'
        assert model._to_openai_role('model') == 'assistant'

    def test_extract_text_from_message(self) -> None:
        """Test text extraction from a message."""
        mock_client = MagicMock()
        model = MSFoundryModel(model_name='gpt-4o', client=mock_client)

        msg = Message(
            role=Role.USER,
            content=[
                Part(root=TextPart(text='Hello ')),
                Part(root=TextPart(text='world!')),
            ],
        )
        text = model._extract_text(msg)
        assert text == 'Hello world!'

    @pytest.mark.asyncio
    async def test_generate_basic_request(self) -> None:
        """Test basic generation with mocked client."""
        mock_client = AsyncMock()

        # Mock the chat completion response
        mock_choice = MagicMock()
        mock_choice.message.content = 'Hello! How can I help you?'
        mock_choice.message.tool_calls = None
        mock_choice.finish_reason = 'stop'

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 8
        mock_response.usage.total_tokens = 18

        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        model = MSFoundryModel(model_name='gpt-4o', client=mock_client)

        request = GenerateRequest(
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(root=TextPart(text='Hello'))],
                )
            ]
        )

        response = await model.generate(request, ctx=None)

        assert response is not None
        assert response.message is not None
        assert len(response.message.content) > 0
        assert response.usage is not None
        assert response.usage.input_tokens == 10
        assert response.usage.output_tokens == 8


class TestMSFoundryEmbed:
    """Tests for embedding functionality."""

    @pytest.mark.asyncio
    async def test_embed_action_created(self) -> None:
        """Test that embedder action is created correctly."""
        plugin = MSFoundry(
            api_key='test-key',
            endpoint='https://test.openai.azure.com/',
        )
        action = await plugin.resolve(ActionKind.EMBEDDER, 'msfoundry/text-embedding-3-small')

        assert action is not None
        assert action.kind == ActionKind.EMBEDDER
        assert 'text-embedding-3-small' in action.name


class TestMSFoundryModelInfo:
    """Tests for model info and capabilities."""

    def test_get_model_info_known_model(self) -> None:
        """Test getting info for a known model."""
        info = get_model_info('gpt-4o')
        assert info is not None
        assert info.label is not None
        assert 'gpt-4o' in info.label.lower() or 'Microsoft Foundry' in info.label

    def test_get_model_info_unknown_model(self) -> None:
        """Test getting info for an unknown model returns default."""
        info = get_model_info('unknown-model-xyz')
        assert info is not None
        assert info.label is not None
        assert 'unknown-model-xyz' in info.label
