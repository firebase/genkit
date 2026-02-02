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

"""Tests for Mistral AI model implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mistralai.models import (
    AssistantMessage,
    ChatCompletionChoice,
    ChatCompletionResponse,
    FunctionCall,
    SystemMessage,
    ToolCall,
    ToolMessage,
    UsageInfo,
    UserMessage,
)

from genkit.core.typing import (
    GenerateRequest,
    Message,
    Part,
    Role,
    TextPart,
    ToolDefinition,
    ToolRequest,
    ToolRequestPart,
    ToolResponse,
    ToolResponsePart,
)
from genkit.plugins.mistral.models import MistralModel


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock Mistral client."""
    return MagicMock()


@pytest.fixture
def model(mock_client: MagicMock) -> MistralModel:
    """Create a MistralModel with mocked client."""
    with patch('genkit.plugins.mistral.models.MistralClient', return_value=mock_client):
        return MistralModel(
            model='mistral-large-latest',
            api_key='test-key',
        )


def test_model_initialization(model: MistralModel) -> None:
    """Test model initialization."""
    assert model.name == 'mistral-large-latest'


def test_get_model_info(model: MistralModel) -> None:
    """Test get_model_info returns expected structure."""
    info = model.get_model_info()
    assert info is not None
    assert 'name' in info
    assert 'supports' in info


def test_convert_messages_text_only(model: MistralModel) -> None:
    """Test converting simple text messages."""
    messages = [
        Message(role=Role.USER, content=[Part(root=TextPart(text='Hello'))]),
        Message(role=Role.MODEL, content=[Part(root=TextPart(text='Hi there!'))]),
    ]

    mistral_messages = model._convert_messages(messages)

    assert len(mistral_messages) == 2
    assert isinstance(mistral_messages[0], UserMessage)
    assert mistral_messages[0].content == 'Hello'
    assert isinstance(mistral_messages[1], AssistantMessage)
    assert mistral_messages[1].content == 'Hi there!'


def test_convert_messages_system_role(model: MistralModel) -> None:
    """Test converting system messages."""
    messages = [
        Message(role=Role.SYSTEM, content=[Part(root=TextPart(text='You are helpful.'))]),
        Message(role=Role.USER, content=[Part(root=TextPart(text='Hello'))]),
    ]

    mistral_messages = model._convert_messages(messages)

    assert len(mistral_messages) == 2
    assert isinstance(mistral_messages[0], SystemMessage)
    assert mistral_messages[0].content == 'You are helpful.'


def test_convert_messages_with_tool_request(model: MistralModel) -> None:
    """Test converting messages with tool requests."""
    messages = [
        Message(
            role=Role.MODEL,
            content=[
                Part(
                    root=ToolRequestPart(
                        tool_request=ToolRequest(
                            ref='call_123',
                            name='get_weather',
                            input={'city': 'Paris'},
                        )
                    )
                )
            ],
        ),
    ]

    mistral_messages = model._convert_messages(messages)

    assert len(mistral_messages) == 1
    assert isinstance(mistral_messages[0], AssistantMessage)
    tool_calls = mistral_messages[0].tool_calls
    assert tool_calls is not None
    assert isinstance(tool_calls, list)
    assert len(tool_calls) == 1
    assert tool_calls[0].id == 'call_123'
    assert tool_calls[0].function.name == 'get_weather'


def test_convert_messages_with_tool_response(model: MistralModel) -> None:
    """Test converting messages with tool responses."""
    messages = [
        Message(
            role=Role.TOOL,
            content=[
                Part(
                    root=ToolResponsePart(
                        tool_response=ToolResponse(
                            ref='call_123',
                            name='get_weather',
                            output={'temperature': 20},
                        )
                    )
                )
            ],
        ),
    ]

    mistral_messages = model._convert_messages(messages)

    assert len(mistral_messages) == 1
    assert isinstance(mistral_messages[0], ToolMessage)
    assert mistral_messages[0].tool_call_id == 'call_123'


def test_convert_tools(model: MistralModel) -> None:
    """Test converting tool definitions."""
    tools = [
        ToolDefinition(
            name='get_weather',
            description='Get weather for a city',
            input_schema={
                'type': 'object',
                'properties': {'city': {'type': 'string'}},
                'required': ['city'],
            },
        ),
    ]

    mistral_tools = model._convert_tools(tools)

    assert len(mistral_tools) == 1
    assert mistral_tools[0].type == 'function'
    assert mistral_tools[0].function.name == 'get_weather'
    assert mistral_tools[0].function.description == 'Get weather for a city'
    assert 'additionalProperties' in mistral_tools[0].function.parameters


def test_get_response_format_json(model: MistralModel) -> None:
    """Test response format for JSON output."""
    from genkit.core.typing import OutputConfig

    output = OutputConfig(format='json')
    result = model._get_response_format(output)

    assert result == {'type': 'json_object'}


def test_get_response_format_json_with_schema(model: MistralModel) -> None:
    """Test response format for JSON with schema."""
    from genkit.core.typing import OutputConfig

    schema = {'type': 'object', 'title': 'Person', 'properties': {'name': {'type': 'string'}}}
    output = OutputConfig(format='json', schema=schema)
    result = model._get_response_format(output)

    assert result is not None
    assert result['type'] == 'json_schema'
    assert result['json_schema']['name'] == 'Person'
    assert result['json_schema']['strict'] is True


def test_get_response_format_text(model: MistralModel) -> None:
    """Test response format for text output returns None."""
    from genkit.core.typing import OutputConfig

    output = OutputConfig(format='text')
    result = model._get_response_format(output)

    assert result is None


def test_convert_response_text_only(model: MistralModel) -> None:
    """Test converting simple text response."""
    response = ChatCompletionResponse(
        id='test-id',
        object='chat.completion',
        created=1234567890,
        model='mistral-large-latest',
        choices=[
            ChatCompletionChoice(
                index=0,
                message=AssistantMessage(content='Hello, world!'),
                finish_reason='stop',
            )
        ],
        usage=UsageInfo(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )

    result = model._convert_response(response)

    assert result.message is not None
    assert result.message.role == Role.MODEL
    assert len(result.message.content) == 1
    assert result.message.content[0].root.text == 'Hello, world!'
    assert result.usage is not None
    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 5


def test_convert_response_with_tool_calls(model: MistralModel) -> None:
    """Test converting response with tool calls."""
    response = ChatCompletionResponse(
        id='test-id',
        object='chat.completion',
        created=1234567890,
        model='mistral-large-latest',
        choices=[
            ChatCompletionChoice(
                index=0,
                message=AssistantMessage(
                    content=None,
                    tool_calls=[
                        ToolCall(
                            id='call_abc',
                            type='function',
                            function=FunctionCall(
                                name='get_weather',
                                arguments='{"city": "Paris"}',
                            ),
                        )
                    ],
                ),
                finish_reason='tool_calls',
            )
        ],
        usage=UsageInfo(prompt_tokens=0, completion_tokens=0, total_tokens=0),
    )

    result = model._convert_response(response)

    assert result.message is not None
    assert len(result.message.content) == 1
    tool_part = result.message.content[0].root
    assert isinstance(tool_part, ToolRequestPart)
    assert tool_part.tool_request.name == 'get_weather'
    assert tool_part.tool_request.ref == 'call_abc'


@patch('genkit.plugins.mistral.models.MistralClient')
@pytest.mark.asyncio
async def test_generate_simple_request(mock_client_class: MagicMock) -> None:
    """Test simple generate request."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    # Mock response
    mock_response = ChatCompletionResponse(
        id='test-id',
        object='chat.completion',
        created=1234567890,
        model='mistral-large-latest',
        choices=[
            ChatCompletionChoice(
                index=0,
                message=AssistantMessage(content='Hello, world!'),
                finish_reason='stop',
            )
        ],
        usage=UsageInfo(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )
    mock_client.chat.complete_async = AsyncMock(return_value=mock_response)

    model = MistralModel(
        model='mistral-large-latest',
        api_key='test-key',
    )

    request = GenerateRequest(
        messages=[Message(role=Role.USER, content=[Part(root=TextPart(text='Hi'))])],
    )

    response = await model.generate(request)

    assert response.message is not None
    assert response.message.role == Role.MODEL
    assert len(response.message.content) == 1
    assert response.message.content[0].root.text == 'Hello, world!'


@patch('genkit.plugins.mistral.models.MistralClient')
@pytest.mark.asyncio
async def test_generate_returns_empty_on_none_response(mock_client_class: MagicMock) -> None:
    """Test generate handles None response gracefully."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.chat.complete_async = AsyncMock(return_value=None)

    model = MistralModel(
        model='mistral-large-latest',
        api_key='test-key',
    )

    request = GenerateRequest(
        messages=[Message(role=Role.USER, content=[Part(root=TextPart(text='Hi'))])],
    )

    response = await model.generate(request)

    assert response.message is not None
    assert response.message.role == Role.MODEL
    assert len(response.message.content) == 1
    assert response.message.content[0].root.text == ''


def test_to_generate_fn(model: MistralModel) -> None:
    """Test to_generate_fn returns callable."""
    fn = model.to_generate_fn()
    assert callable(fn)
    assert fn == model.generate
