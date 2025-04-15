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

from unittest.mock import MagicMock

import pytest

from genkit.plugins.compat_oai.models import OpenAIModel
from genkit.plugins.compat_oai.models.model_info import GPT_4
from genkit.types import (
    GenerateResponse,
    GenerateResponseChunk,
    Role,
)


def test_get_messages(sample_request):
    """Test _get_messages method.
    Ensures the method correctly converts GenerateRequest messages into OpenAI-compatible ChatMessage format.
    """
    model = OpenAIModel(model=GPT_4, client=MagicMock(), registry=MagicMock())
    messages = model._get_messages(sample_request.messages)

    assert len(messages) == 2
    assert messages[0]['role'] == 'system'
    assert messages[0]['content'] == 'You are an assistant'
    assert messages[1]['role'] == 'user'
    assert messages[1]['content'] == 'Hello, world!'


def test_get_openai_config(sample_request):
    """
    Test _get_openai_request_config method.
    Ensures the method correctly constructs the OpenAI API configuration dictionary.
    """
    model = OpenAIModel(model=GPT_4, client=MagicMock(), registry=MagicMock())
    openai_config = model._get_openai_request_config(sample_request)

    assert isinstance(openai_config, dict)
    assert openai_config['model'] == GPT_4
    assert 'messages' in openai_config
    assert isinstance(openai_config['messages'], list)


def test_generate(sample_request):
    """
    Test generate method calls OpenAI API and returns GenerateResponse.
    """
    mock_message = MagicMock()
    mock_message.content = 'Hello, user!'
    mock_message.role = 'model'

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=mock_message)]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    model = OpenAIModel(model=GPT_4, client=mock_client, registry=MagicMock())
    response = model.generate(sample_request)

    mock_client.chat.completions.create.assert_called_once()
    assert isinstance(response, GenerateResponse)
    assert response.message.role == Role.MODEL
    assert response.message.content[0].root.text == 'Hello, user!'


def test_generate_stream(sample_request):
    """Test generate_stream method ensures it processes streamed responses correctly."""
    mock_client = MagicMock()

    class MockStream:
        def __init__(self, data: list[str]) -> None:
            self._data = data
            self._current = 0

        def __iter__(self):
            return self

        def __next__(self):
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

    model = OpenAIModel(model=GPT_4, client=mock_client, registry=MagicMock())
    collected_chunks = []

    def callback(chunk: GenerateResponseChunk):
        collected_chunks.append(chunk.content[0].root.text)

    model.generate_stream(sample_request, callback)

    assert collected_chunks == ['Hello', ', world!']
