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


"""Tests for OpenAI compatible model implementation."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from genkit.core.action._action import ActionRunContext
from genkit.plugins.compat_oai.models import OpenAIModel
from genkit.plugins.compat_oai.typing import OpenAIConfig
from genkit.types import (
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationCommonConfig,
    Message,
    Part,
    Role,
    TextPart,
)


def test_get_messages(sample_request: GenerateRequest) -> None:
    """Test _get_messages method.

    Ensures the method correctly converts GenerateRequest messages into OpenAI-compatible ChatMessage format.
    """
    model = OpenAIModel(model='gpt-4', client=MagicMock())
    messages = model._get_messages(sample_request.messages)

    assert len(messages) == 2
    assert messages[0]['role'] == 'system'
    assert messages[0]['content'] == 'You are an assistant'
    assert messages[1]['role'] == 'user'
    assert messages[1]['content'] == 'Hello, world!'


@pytest.mark.asyncio
async def test_get_openai_config(sample_request: GenerateRequest) -> None:
    """Test _get_openai_request_config method.

    Ensures the method correctly constructs the OpenAI API configuration dictionary.
    """
    model = OpenAIModel(model='gpt-4', client=MagicMock())
    openai_config = await model._get_openai_request_config(sample_request)

    assert isinstance(openai_config, dict)
    assert openai_config['model'] == 'gpt-4'
    assert 'messages' in openai_config
    assert isinstance(openai_config['messages'], list)


@pytest.mark.asyncio
async def test__generate(sample_request: GenerateRequest) -> None:
    """Test generate method calls OpenAI API and returns GenerateResponse."""
    mock_message = MagicMock()
    mock_message.content = 'Hello, user!'
    mock_message.role = 'model'

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=mock_message)]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    model = OpenAIModel(model='gpt-4', client=mock_client)
    response = await model._generate(sample_request)

    mock_client.chat.completions.create.assert_called_once()
    assert isinstance(response, GenerateResponse)
    assert response.message is not None
    assert response.message.role == Role.MODEL
    assert response.message.content[0].root.text == 'Hello, user!'


@pytest.mark.asyncio
async def test__generate_stream(sample_request: GenerateRequest) -> None:
    """Test generate_stream method ensures it processes streamed responses correctly."""
    mock_client = MagicMock()

    class MockStream:
        def __init__(self, data: list[str]) -> None:
            self._data = data
            self._current = 0

        def __iter__(self) -> 'MockStream':
            return self

        def __next__(self) -> object:
            if self._current >= len(self._data):
                raise StopIteration

            content = self._data[self._current]
            self._current += 1

            delta_mock = MagicMock()
            delta_mock.content = content
            delta_mock.role = None
            delta_mock.tool_calls = None

            choice_mock = MagicMock()
            choice_mock.delta = delta_mock

            return MagicMock(choices=[choice_mock])

    mock_client.chat.completions.create.return_value = MockStream(['Hello', ', world!'])

    model = OpenAIModel(model='gpt-4', client=mock_client)
    collected_chunks = []

    def callback(chunk: GenerateResponseChunk) -> None:
        collected_chunks.append(chunk.content[0].root.text)

    await model._generate_stream(sample_request, callback)

    assert collected_chunks == ['Hello', ', world!']


@pytest.mark.parametrize(
    'stream',
    [
        True,
        False,
    ],
)
@pytest.mark.asyncio
async def test_generate(stream: bool, sample_request: GenerateRequest) -> None:
    """Tests for generate."""
    ctx_mock = MagicMock(spec=ActionRunContext)
    ctx_mock.is_streaming = stream

    mock_response = GenerateResponse(message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='mocked'))]))

    model = OpenAIModel(model='gpt-4', client=MagicMock())
    model._generate_stream = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]
    model._generate = AsyncMock(return_value=mock_response)  # type: ignore[method-assign]
    model.normalize_config = MagicMock(return_value={})  # type: ignore[method-assign]
    response = await model.generate(sample_request, ctx_mock)

    assert response == mock_response
    if stream:
        model._generate_stream.assert_called_once()  # type: ignore[union-attr]
    else:
        model._generate.assert_called_once()  # type: ignore[union-attr]


@pytest.mark.parametrize(
    'config, expected',
    [
        (OpenAIConfig(model='test'), OpenAIConfig(model='test')),
        ({'model': 'test'}, OpenAIConfig(model='test')),
        (
            GenerationCommonConfig(temperature=0.7),
            OpenAIConfig(temperature=0.7),
        ),
        (
            None,
            Exception(),
        ),
    ],
)
def test_normalize_config(config: object, expected: object) -> None:
    """Tests for _normalize_config."""
    if isinstance(expected, Exception):
        with pytest.raises(ValueError, match=r'Expected request.config to be a dict or OpenAIConfig, got .*'):
            OpenAIModel.normalize_config(config)
    else:
        response = OpenAIModel.normalize_config(config)
        assert response == expected
