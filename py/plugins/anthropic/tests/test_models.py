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

"""Tests for Anthropic models."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from genkit.plugins.anthropic.models import AnthropicModel
from genkit.types import (
    GenerateRequest,
    GenerateResponseChunk,
    GenerationCommonConfig,
    Message,
    Part,
    Role,
    TextPart,
    ToolDefinition,
    ToolRequestPart,
)


def _create_sample_request() -> GenerateRequest:
    """Create a sample generation request for testing."""
    return GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[Part(root=TextPart(text='Hello, how are you?'))],
            )
        ],
        config=GenerationCommonConfig(),
        tools=[
            ToolDefinition(
                name='get_weather',
                description='Get weather for a location',
                inputSchema={
                    'type': 'object',
                    'properties': {'location': {'type': 'string', 'description': 'Location name'}},
                    'required': ['location'],
                },
            )
        ],
    )


@pytest.mark.asyncio
async def test_generate_basic():
    """Test basic generation."""
    sample_request = _create_sample_request()

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type='text', text="Hello! I'm doing well.")]
    mock_response.usage = MagicMock(input_tokens=10, output_tokens=15)
    mock_response.stop_reason = 'end_turn'

    mock_client.messages.create = AsyncMock(return_value=mock_response)

    model = AnthropicModel(model_name='claude-sonnet-4', client=mock_client)
    response = await model.generate(sample_request)

    assert len(response.message.content) == 1
    part = response.message.content[0]
    actual_part = part.root if isinstance(part, Part) else part
    assert isinstance(actual_part, TextPart)
    assert actual_part.text == "Hello! I'm doing well."
    assert response.usage.input_tokens == 10
    assert response.usage.output_tokens == 15
    assert response.finish_reason == 'stop'


@pytest.mark.asyncio
async def test_generate_with_tools():
    """Test generation with tool calls."""
    sample_request = _create_sample_request()

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_block = MagicMock()
    mock_block.type = 'tool_use'
    mock_block.id = 'tool_123'
    mock_block.name = 'get_weather'
    mock_block.input = {'location': 'Paris'}
    mock_response.content = [mock_block]
    mock_response.usage = MagicMock(input_tokens=20, output_tokens=10)
    mock_response.stop_reason = 'tool_use'

    mock_client.messages.create = AsyncMock(return_value=mock_response)

    model = AnthropicModel(model_name='claude-sonnet-4', client=mock_client)
    response = await model.generate(sample_request)

    assert len(response.message.content) == 1
    part = response.message.content[0]
    actual_part = part.root if isinstance(part, Part) else part
    assert isinstance(actual_part, ToolRequestPart)
    assert actual_part.tool_request.name == 'get_weather'
    assert actual_part.tool_request.ref == 'tool_123'
    assert actual_part.tool_request.input == {'location': 'Paris'}


@pytest.mark.asyncio
async def test_generate_with_config():
    """Test generation with custom config."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type='text', text='Response')]
    mock_response.usage = MagicMock(input_tokens=5, output_tokens=5)
    mock_response.stop_reason = 'end_turn'

    mock_client.messages.create = AsyncMock(return_value=mock_response)

    model = AnthropicModel(model_name='claude-sonnet-4', client=mock_client)

    request = GenerateRequest(
        messages=[Message(role=Role.USER, content=[Part(root=TextPart(text='Test'))])],
        config=GenerationCommonConfig(
            temperature=0.7,
            maxOutputTokens=100,
            topP=0.9,
        ),
    )

    await model.generate(request)

    call_args = mock_client.messages.create.call_args
    assert call_args.kwargs['temperature'] == 0.7
    assert call_args.kwargs['max_tokens'] == 100
    assert call_args.kwargs['top_p'] == 0.9


def test_extract_system():
    """Test system prompt extraction."""
    mock_client = MagicMock()
    model = AnthropicModel(model_name='claude-sonnet-4', client=mock_client)

    messages = [
        Message(role=Role.SYSTEM, content=[Part(root=TextPart(text='You are helpful.'))]),
        Message(role=Role.USER, content=[Part(root=TextPart(text='Hello'))]),
    ]

    system = model._extract_system(messages)
    assert system == 'You are helpful.'


def test_to_anthropic_messages():
    """Test message conversion."""
    mock_client = MagicMock()
    model = AnthropicModel(model_name='claude-sonnet-4', client=mock_client)

    messages = [
        Message(role=Role.USER, content=[Part(root=TextPart(text='Hello'))]),
        Message(role=Role.MODEL, content=[Part(root=TextPart(text='Hi there'))]),
    ]

    anthropic_messages = model._to_anthropic_messages(messages)

    assert len(anthropic_messages) == 2
    assert anthropic_messages[0]['role'] == 'user'
    assert anthropic_messages[0]['content'][0]['text'] == 'Hello'
    assert anthropic_messages[1]['role'] == 'assistant'
    assert anthropic_messages[1]['content'][0]['text'] == 'Hi there'


class MockStreamManager:
    """Mock stream manager for testing streaming."""

    def __init__(self, chunks, final_content=None):
        self.chunks = chunks
        self.final_message = MagicMock()
        self.final_message.content = final_content if final_content else []
        self.final_message.usage = MagicMock(input_tokens=10, output_tokens=20)
        self.final_message.stop_reason = 'end_turn'

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.chunks:
            raise StopAsyncIteration
        return self.chunks.pop(0)

    async def get_final_message(self):
        return self.final_message


@pytest.mark.asyncio
async def test_streaming_generation():
    """Test streaming generation."""
    sample_request = _create_sample_request()

    mock_client = MagicMock()

    chunks = [
        MagicMock(type='content_block_delta', delta=MagicMock(text='Hello')),
        MagicMock(type='content_block_delta', delta=MagicMock(text=' world')),
        MagicMock(type='content_block_delta', delta=MagicMock(text='!')),
    ]

    final_content = [MagicMock(type='text', text='Hello world!')]
    mock_stream = MockStreamManager(chunks, final_content=final_content)
    mock_client.messages.stream.return_value = mock_stream

    model = AnthropicModel(model_name='claude-sonnet-4', client=mock_client)

    ctx = MagicMock()
    ctx.is_streaming = True
    collected_chunks = []

    def send_chunk(chunk: GenerateResponseChunk):
        collected_chunks.append(chunk)

    ctx.send_chunk = send_chunk

    response = await model.generate(sample_request, ctx)

    assert len(collected_chunks) == 3
    chunk0_part = collected_chunks[0].content[0]
    chunk0_actual = chunk0_part.root if isinstance(chunk0_part, Part) else chunk0_part
    assert chunk0_actual.text == 'Hello'

    chunk1_part = collected_chunks[1].content[0]
    chunk1_actual = chunk1_part.root if isinstance(chunk1_part, Part) else chunk1_part
    assert chunk1_actual.text == ' world'

    chunk2_part = collected_chunks[2].content[0]
    chunk2_actual = chunk2_part.root if isinstance(chunk2_part, Part) else chunk2_part
    assert chunk2_actual.text == '!'

    assert response.usage.input_tokens == 10
    assert response.usage.output_tokens == 20

    # Verify final response content is populated
    assert len(response.message.content) == 1
    final_part = response.message.content[0]
    assert isinstance(final_part, Part)
    assert isinstance(final_part.root, TextPart)
    assert final_part.root.text == 'Hello world!'
