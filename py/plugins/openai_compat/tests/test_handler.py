# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from unittest.mock import MagicMock

import pytest
from genkit.core.action import ActionRunContext
from genkit.core.typing import GenerateResponse, Role
from genkit.plugins.openai_compat.models import OpenAIModelHandler
from genkit.plugins.openai_compat.models.model import OpenAIModel
from genkit.plugins.openai_compat.models.model_info import (
    GPT_3_5_TURBO,
    GPT_4,
    SUPPORTED_OPENAI_MODELS,
)


def test_get_model_handler():
    """Test get_model_handler method."""
    model_name = GPT_4
    handler = OpenAIModelHandler.get_model_handler(
        model=model_name, client=MagicMock()
    )

    assert callable(handler)


def test_get_model_handler_invalid():
    """Test get_model_handler raises ValueError for unsupported models."""
    with pytest.raises(
        ValueError, match="Model 'unsupported-model' is not supported."
    ):
        OpenAIModelHandler.get_model_handler(
            model='unsupported-model', client=MagicMock()
        )


def test_validate_version():
    """Test validate_version method."""
    model = MagicMock()
    model.name = GPT_4
    SUPPORTED_OPENAI_MODELS[GPT_4] = MagicMock(versions=[GPT_4, GPT_3_5_TURBO])
    handler = OpenAIModelHandler(model)

    handler.validate_version(GPT_4)  # Should not raise error

    with pytest.raises(
        ValueError, match="Model version 'invalid-version' is not supported."
    ):
        handler.validate_version('invalid-version')


def test_handler_generate(sample_request):
    """Test OpenAIModelHandler generate method calls OpenAI API and returns GenerateResponse."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='Hello, user!'))]
    )

    model = OpenAIModel(model=GPT_4, client=mock_client)
    handler = OpenAIModelHandler(model)
    response = handler.generate(
        sample_request, MagicMock(spec=ActionRunContext)
    )

    mock_client.chat.completions.create.assert_called_once()
    assert isinstance(response, GenerateResponse)
    assert response.message.role == Role.MODEL
    assert response.message.content[0].root.text == 'Hello, user!'
