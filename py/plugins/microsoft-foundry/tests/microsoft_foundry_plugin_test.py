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
from genkit.plugins.microsoft_foundry import (
    MICROSOFT_FOUNDRY_PLUGIN_NAME,
    MicrosoftFoundry,
    MicrosoftFoundryConfig,
    gpt4o,
    microsoft_foundry_model,
)
from genkit.plugins.microsoft_foundry.models.converters import (
    extract_text,
    normalize_config,
    to_openai_role,
)
from genkit.plugins.microsoft_foundry.models.model import MicrosoftFoundryModel
from genkit.plugins.microsoft_foundry.models.model_info import get_model_info
from genkit.types import (
    GenerateRequest,
    Message,
    OutputConfig,
    Part,
    Role,
    TextPart,
)


def test_plugin_name() -> None:
    """Test that plugin name is correct."""
    assert MICROSOFT_FOUNDRY_PLUGIN_NAME == 'microsoft-foundry'


def test_plugin_init() -> None:
    """Test plugin initialization with API key."""
    plugin = MicrosoftFoundry(
        api_key='test-key',
        endpoint='https://test.openai.azure.com/',
    )
    assert plugin.name == 'microsoft-foundry'


def test_microsoft_foundry_model_helper() -> None:
    """Test the microsoft_foundry_model helper function."""
    assert microsoft_foundry_model('gpt-4o') == 'microsoft-foundry/gpt-4o'
    assert microsoft_foundry_model('gpt-4') == 'microsoft-foundry/gpt-4'
    assert microsoft_foundry_model('gpt-3.5-turbo') == 'microsoft-foundry/gpt-3.5-turbo'
    # Test with other provider models
    assert microsoft_foundry_model('DeepSeek-V3.2') == 'microsoft-foundry/DeepSeek-V3.2'
    assert microsoft_foundry_model('claude-opus-4-5') == 'microsoft-foundry/claude-opus-4-5'


def test_predefined_model_refs() -> None:
    """Test pre-defined model reference constants."""
    assert gpt4o == 'microsoft-foundry/gpt-4o'


def test_config_schema() -> None:
    """Test MicrosoftFoundryConfig schema."""
    config = MicrosoftFoundryConfig(
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
    """Test MicrosoftFoundryConfig with camelCase aliases."""
    config = MicrosoftFoundryConfig.model_validate({
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
    plugin = MicrosoftFoundry(
        api_key='test-key',
        endpoint='https://test.openai.azure.com/',
    )
    action = await plugin.resolve(ActionKind.MODEL, 'microsoft-foundry/gpt-4o')
    assert action is not None
    assert action.name == 'microsoft-foundry/gpt-4o'
    assert action.kind == ActionKind.MODEL


@pytest.mark.asyncio
async def test_resolve_embedder() -> None:
    """Test resolving an embedder action."""
    plugin = MicrosoftFoundry(
        api_key='test-key',
        endpoint='https://test.openai.azure.com/',
    )
    action = await plugin.resolve(ActionKind.EMBEDDER, 'microsoft-foundry/text-embedding-3-small')
    assert action is not None
    assert action.name == 'microsoft-foundry/text-embedding-3-small'
    assert action.kind == ActionKind.EMBEDDER


@pytest.mark.asyncio
async def test_list_actions() -> None:
    """Test listing all available actions."""
    plugin = MicrosoftFoundry(
        api_key='test-key',
        endpoint='https://test.openai.azure.com/',
    )
    actions = await plugin.list_actions()
    assert len(actions) > 0

    # Check for expected models
    action_names = [a.name for a in actions]
    assert 'microsoft-foundry/gpt-4o' in action_names
    assert 'microsoft-foundry/gpt-4o-mini' in action_names
    assert 'microsoft-foundry/gpt-4' in action_names

    # Check for embedders
    assert 'microsoft-foundry/text-embedding-3-small' in action_names
    assert 'microsoft-foundry/text-embedding-3-large' in action_names


@pytest.mark.asyncio
async def test_init_registers_actions() -> None:
    """Test that init() registers all supported actions."""
    plugin = MicrosoftFoundry(
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


class TestMicrosoftFoundryModel:
    """Tests for MicrosoftFoundryModel generation logic."""

    def test_normalize_config_with_none(self) -> None:
        """Test config normalization with None input."""
        config = normalize_config(None)
        assert isinstance(config, MicrosoftFoundryConfig)

    def test_normalize_config_with_microsoft_foundry_config(self) -> None:
        """Test config normalization with MicrosoftFoundryConfig input."""
        input_config = MicrosoftFoundryConfig(temperature=0.5, max_tokens=100)
        config = normalize_config(input_config)
        assert config.temperature == 0.5
        assert config.max_tokens == 100

    def test_normalize_config_with_dict(self) -> None:
        """Test config normalization with dict input (camelCase keys)."""
        input_config = {'temperature': 0.8, 'maxTokens': 200, 'topP': 0.9}
        config = normalize_config(input_config)
        assert config.temperature == 0.8
        assert config.max_tokens == 200
        assert config.top_p == 0.9

    def test_to_openai_role_conversion(self) -> None:
        """Test role conversion from Genkit to OpenAI format."""
        assert to_openai_role(Role.USER) == 'user'
        assert to_openai_role(Role.MODEL) == 'assistant'
        assert to_openai_role(Role.SYSTEM) == 'system'
        assert to_openai_role(Role.TOOL) == 'tool'
        # Test string roles
        assert to_openai_role('user') == 'user'
        assert to_openai_role('model') == 'assistant'

    def test_extract_text_from_message(self) -> None:
        """Test text extraction from a message."""
        msg = Message(
            role=Role.USER,
            content=[
                Part(root=TextPart(text='Hello ')),
                Part(root=TextPart(text='world!')),
            ],
        )
        text = extract_text(msg)
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

        model = MicrosoftFoundryModel(model_name='gpt-4o', client=mock_client)

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

    def test_build_request_body_json_schema_format(self) -> None:
        """Test that structured output uses json_schema format with schema."""
        mock_client = AsyncMock()
        model = MicrosoftFoundryModel(model_name='gpt-4o', client=mock_client)

        schema = {
            'title': 'RpgCharacter',
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'backstory': {'type': 'string'},
            },
            'required': ['name', 'backstory'],
        }

        request = GenerateRequest(
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(root=TextPart(text='Generate a character'))],
                )
            ],
            output=OutputConfig(format='json', schema=schema),
        )

        config = normalize_config(None)
        body = model._build_request_body(request, config)

        # Must use json_schema format when schema is provided
        assert body['response_format']['type'] == 'json_schema'
        assert body['response_format']['json_schema']['name'] == 'RpgCharacter'
        assert body['response_format']['json_schema']['strict'] is True
        assert 'schema' in body['response_format']['json_schema']

    def test_build_request_body_json_object_without_schema(self) -> None:
        """Test that JSON mode without schema uses json_object format."""
        mock_client = AsyncMock()
        model = MicrosoftFoundryModel(model_name='gpt-4o', client=mock_client)

        request = GenerateRequest(
            messages=[
                Message(
                    role=Role.USER,
                    content=[Part(root=TextPart(text='Give me JSON'))],
                )
            ],
            output=OutputConfig(format='json'),
        )

        config = normalize_config(None)
        body = model._build_request_body(request, config)

        assert body['response_format'] == {'type': 'json_object'}


class TestMicrosoftFoundryEmbed:
    """Tests for embedding functionality."""

    @pytest.mark.asyncio
    async def test_embed_action_created(self) -> None:
        """Test that embedder action is created correctly."""
        plugin = MicrosoftFoundry(
            api_key='test-key',
            endpoint='https://test.openai.azure.com/',
        )
        action = await plugin.resolve(ActionKind.EMBEDDER, 'microsoft-foundry/text-embedding-3-small')

        assert action is not None
        assert action.kind == ActionKind.EMBEDDER
        assert 'text-embedding-3-small' in action.name


class TestMicrosoftFoundryModelInfo:
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
