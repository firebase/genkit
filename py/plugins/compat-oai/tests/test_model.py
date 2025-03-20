# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import MagicMock

import pytest

from genkit.core.typing import (
    GenerateResponse,
    GenerateResponseChunk,
    Role,
)
from genkit.plugins.compat_oai.models import OpenAIModel
from genkit.plugins.compat_oai.models.model_info import GPT_4


def test_get_messages(sample_request):
    """
    Test _get_messages method.
    Ensures the method correctly converts GenerateRequest messages into OpenAI-compatible ChatMessage format.
    """
    model = OpenAIModel(model=GPT_4, client=MagicMock())
    messages = model._get_messages(sample_request.messages)

    assert len(messages) == 1
    assert messages[0].role == Role.USER
    assert messages[0].content == 'Hello, world!'


def test_get_messages_empty():
    """
    Test _get_messages raises ValueError when no messages are provided.
    """
    model = OpenAIModel(model=GPT_4, client=MagicMock())
    with pytest.raises(
        ValueError, match='No messages provided in the request.'
    ):
        model._get_messages([])


def test_get_openai_config(sample_request):
    """
    Test _get_openai_config method.
    Ensures the method correctly constructs the OpenAI API configuration dictionary.
    """
    model = OpenAIModel(model=GPT_4, client=MagicMock())
    openai_config = model._get_openai_config(sample_request)

    assert isinstance(openai_config, dict)
    assert openai_config['model'] == GPT_4
    assert 'messages' in openai_config
    assert isinstance(openai_config['messages'], list)


def test_generate(sample_request):
    """
    Test generate method calls OpenAI API and returns GenerateResponse.
    """
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='Hello, user!'))]
    )

    model = OpenAIModel(model=GPT_4, client=mock_client)
    response = model.generate(sample_request)

    mock_client.chat.completions.create.assert_called_once()
    assert isinstance(response, GenerateResponse)
    assert response.message.role == Role.MODEL
    assert response.message.content[0].root.text == 'Hello, user!'


def test_generate_stream(sample_request):
    """
    Test generate_stream method ensures it processes streamed responses correctly.
    """
    mock_client = MagicMock()
    mock_stream = [
        MagicMock(
            choices=[MagicMock(index=0, delta=MagicMock(content='Hello'))]
        ),
        MagicMock(
            choices=[MagicMock(index=0, delta=MagicMock(content=', world!'))]
        ),
    ]
    mock_client.chat.completions.create.return_value = mock_stream

    model = OpenAIModel(model=GPT_4, client=mock_client)
    collected_chunks = []

    def callback(chunk: GenerateResponseChunk):
        collected_chunks.append(chunk.content[0].root.text)

    model.generate_stream(sample_request, callback)

    assert collected_chunks == ['Hello', ', world!']
