# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

from unittest import mock

import ollama as ollama_api
import pytest
from genkit.core.typing import GenerateResponse, Message, Role, TextPart
from genkit.veneer import Genkit


def test_adding_ollama_chat_model_to_genkit_veneer(
    ollama_model: str,
    genkit_veneer_chat_model: Genkit,
):
    assert len(genkit_veneer_chat_model.registry.entries) == 1
    assert ollama_model in genkit_veneer_chat_model.registry.entries['model']


def test_adding_ollama_generation_model_to_genkit_veneer(
    ollama_model: str,
    genkit_veneer_generate_model: Genkit,
):
    assert len(genkit_veneer_generate_model.registry.entries) == 1
    assert (
        ollama_model in genkit_veneer_generate_model.registry.entries['model']
    )


@pytest.mark.asyncio
async def test_async_get_chat_model_response_from_llama_api_flow(
    mock_ollama_api_async_client: mock.Mock, genkit_veneer_chat_model: Genkit
):
    mock_response_message = 'Mocked response message'

    async def fake_chat_response(*args, **kwargs):
        return ollama_api.ChatResponse(
            message=ollama_api.Message(
                content=mock_response_message,
                role=Role.USER,
            )
        )

    mock_ollama_api_async_client.return_value.chat.side_effect = (
        fake_chat_response
    )

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
):
    mock_response_message = 'Mocked response message'

    async def fake_generate_response(*args, **kwargs):
        return ollama_api.GenerateResponse(
            response=mock_response_message,
        )

    mock_ollama_api_async_client.return_value.generate.side_effect = (
        fake_generate_response
    )

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
