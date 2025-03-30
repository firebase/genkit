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

from unittest import mock

import ollama as ollama_api
import pytest

from genkit.ai import ActionKind, Genkit
from genkit.types import GenerateResponse, Message, Role, TextPart


def test_adding_ollama_chat_model_to_genkit_veneer(
    ollama_model: str,
    genkit_veneer_chat_model: Genkit,
) -> None:
    """Test adding ollama chat model to genkit veneer."""
    assert genkit_veneer_chat_model.registry.lookup_action(ActionKind.MODEL, ollama_model)


def test_adding_ollama_generation_model_to_genkit_veneer(
    ollama_model: str,
    genkit_veneer_generate_model: Genkit,
) -> None:
    """Test adding ollama generation model to genkit veneer."""
    assert genkit_veneer_generate_model.registry.lookup_action(ActionKind.MODEL, ollama_model)


@pytest.mark.asyncio
async def test_async_get_chat_model_response_from_llama_api_flow(
    mock_ollama_api_async_client: mock.Mock,
    genkit_veneer_chat_model: Genkit,
) -> None:
    """Test async get chat model response from llama api flow."""
    mock_response_message = 'Mocked response message'

    async def fake_chat_response(*args, **kwargs):
        return ollama_api.ChatResponse(
            message=ollama_api.Message(
                content=mock_response_message,
                role=Role.USER,
            )
        )

    mock_ollama_api_async_client.return_value.chat.side_effect = fake_chat_response

    async def _test_fun():
        return await genkit_veneer_chat_model.generate(
            messages=[
                Message(
                    role=Role.USER,
                    content=[
                        TextPart(text='Test message'),
                    ],
                )
            ]
        )

    response = await genkit_veneer_chat_model.flow()(_test_fun)()

    assert isinstance(response, GenerateResponse)
    assert response.message.content[0].root.text == mock_response_message


@pytest.mark.asyncio
async def test_async_get_generate_model_response_from_llama_api_flow(
    mock_ollama_api_async_client: mock.Mock,
    genkit_veneer_generate_model: Genkit,
) -> None:
    """Test async get generate model response from llama api flow."""
    mock_response_message = 'Mocked response message'

    async def fake_generate_response(*args, **kwargs):
        return ollama_api.GenerateResponse(
            response=mock_response_message,
        )

    mock_ollama_api_async_client.return_value.generate.side_effect = fake_generate_response

    async def _test_fun():
        return await genkit_veneer_generate_model.generate(
            messages=[
                Message(
                    role=Role.USER,
                    content=[
                        TextPart(text='Test message'),
                    ],
                )
            ]
        )

    response = await genkit_veneer_generate_model.flow()(_test_fun)()

    assert isinstance(response, GenerateResponse)
    assert response.message.content[0].root.text == mock_response_message
