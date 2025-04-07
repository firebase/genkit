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
"""Tests for the OpenAI Model Handler compatibility plugin."""

from unittest.mock import MagicMock

import pytest

from genkit.ai import ActionRunContext
from genkit.plugins.compat_oai.models import OpenAIModelHandler
from genkit.plugins.compat_oai.models.model import OpenAIModel
from genkit.plugins.compat_oai.models.model_info import (
    GPT_3_5_TURBO,
    GPT_4,
    SUPPORTED_OPENAI_MODELS,
)
from genkit.types import GenerateRequest, GenerateResponse, Message, Role, TextPart


def test_get_model_handler() -> None:
    """Test get_model_handler method returns a callable."""
    model_name = GPT_4
    handler = OpenAIModelHandler.get_model_handler(model=model_name, client=MagicMock(), registry=MagicMock())
    assert callable(handler)


def test_get_model_handler_invalid() -> None:
    """Test get_model_handler raises ValueError for unsupported models."""
    with pytest.raises(ValueError, match="Model 'unsupported-model' is not supported."):
        OpenAIModelHandler.get_model_handler(model='unsupported-model', client=MagicMock(), registry=MagicMock())


def test_validate_version() -> None:
    """Test validate_version method validates supported versions."""
    model = MagicMock()
    model.name = GPT_4
    SUPPORTED_OPENAI_MODELS[GPT_4] = MagicMock(versions=[GPT_4, GPT_3_5_TURBO])
    handler = OpenAIModelHandler(model)

    handler._validate_version(GPT_4)  # Should not raise an error

    with pytest.raises(ValueError, match="Model version 'invalid-version' is not supported."):
        handler._validate_version('invalid-version')


def test_handler_generate_non_streaming(sample_request: GenerateRequest) -> None:
    """Test OpenAIModelHandler generate method in non-streaming mode."""
    mock_model = MagicMock(spec=OpenAIModel)
    mock_model.name = GPT_4
    mock_model.generate.return_value = GenerateResponse(
        message=Message(role=Role.MODEL, content=[TextPart(text='Hello, user!')])
    )

    handler = OpenAIModelHandler(mock_model)
    mock_ctx = MagicMock(spec=ActionRunContext, is_streaming=False)

    response = handler.generate(sample_request, mock_ctx)

    mock_model.generate.assert_called_once()
    assert isinstance(response, GenerateResponse)
    assert response.message.role == Role.MODEL
    assert response.message.content[0].root.text == 'Hello, user!'


def test_handler_generate_streaming(sample_request: GenerateRequest) -> None:
    """Test OpenAIModelHandler generate method in streaming mode."""
    mock_model = MagicMock(spec=OpenAIModel)
    mock_model.name = GPT_4

    handler = OpenAIModelHandler(mock_model)
    mock_ctx = MagicMock(spec=ActionRunContext, is_streaming=True)

    handler.generate(sample_request, mock_ctx)

    mock_model.generate_stream.assert_called_once_with(sample_request, mock_ctx.send_chunk)
