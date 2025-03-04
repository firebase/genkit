# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import MagicMock

import pytest
from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    Role,
)
from genkit.plugins.openai_compat.models import OpenAIModel
from genkit.plugins.openai_compat.models.model_info import GPT_4
from genkit.plugins.openai_compat.typing import ChatCompletionRequest


def test_build_messages(sample_request):
    """Test _build_messages method."""
    model = OpenAIModel(model=GPT_4, client=MagicMock())
    messages = model._build_messages(sample_request)

    assert len(messages) == 1
    assert messages[0].role == Role.USER
    assert messages[0].content == 'Hello, world!'


def test_build_messages_empty():
    """Test _build_messages raises ValueError when no messages are provided."""
    model = OpenAIModel(model=GPT_4, client=MagicMock())
    empty_request = GenerateRequest(messages=[])

    with pytest.raises(
        ValueError, match='No messages provided in the request.'
    ):
        model._build_messages(empty_request)


def test_get_request_data(sample_request):
    """Test _get_request_data method."""
    model = OpenAIModel(model=GPT_4, client=MagicMock())
    request_data = model._get_request_data(sample_request)

    assert isinstance(request_data, ChatCompletionRequest)
    assert request_data.model == GPT_4
    assert request_data.top_p == 0.9
    assert request_data.temperature == 0.7
    assert request_data.stop == ['stop']
    assert request_data.max_tokens == 100


def test_generate(sample_request):
    """Test generate method calls OpenAI API and returns GenerateResponse."""
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
