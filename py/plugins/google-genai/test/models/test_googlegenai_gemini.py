# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import pytest
from google import genai

from genkit.core.action import ActionRunContext
from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    Message,
    Role,
    TextPart,
)
from genkit.plugins.google_genai.models.gemini import GeminiModel, GeminiVersion


@pytest.mark.asyncio
@pytest.mark.parametrize('version', [x for x in GeminiVersion])
async def test_generate_text_response(mocker, version):
    response_text = 'request answer'
    request_text = 'response question'

    request = GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text=request_text),
                ],
            ),
        ]
    )
    candidate = genai.types.Candidate(
        content=genai.types.Content(
            parts=[genai.types.Part(text=response_text)]
        )
    )
    resp = genai.types.GenerateContentResponse(candidates=[candidate])

    googleai_client_mock = mocker.AsyncMock()
    googleai_client_mock.aio.models.generate_content.return_value = resp

    gemini = GeminiModel(version, googleai_client_mock)

    ctx = ActionRunContext()
    response = await gemini.generate(request, ctx)

    googleai_client_mock.assert_has_calls([
        mocker.call.aio.models.generate_content(
            model=version,
            contents=[
                genai.types.Content(
                    parts=[genai.types.Part(text=request_text)], role='user'
                )
            ],
            config=None,
        )
    ])
    assert isinstance(response, GenerateResponse)
    assert response.message.content[0].root.text == response_text


@pytest.mark.asyncio
@pytest.mark.parametrize('version', [x for x in GeminiVersion])
async def test_generate_stream_text_response(mocker, version):
    response_text = 'request answer'
    request_text = 'response question'

    request = GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text=request_text),
                ],
            ),
        ]
    )
    candidate = genai.types.Candidate(
        content=genai.types.Content(
            parts=[genai.types.Part(text=response_text)]
        )
    )

    resp = genai.types.GenerateContentResponse(candidates=[candidate])

    googleai_client_mock = mocker.AsyncMock()
    googleai_client_mock.aio.models.generate_content_stream.__aiter__.side_effect = [
        resp
    ]
    on_chunk_mock = mocker.MagicMock()
    gemini = GeminiModel(version, googleai_client_mock)

    ctx = ActionRunContext(on_chunk=on_chunk_mock)
    response = await gemini.generate(request, ctx)

    googleai_client_mock.assert_has_calls([
        mocker.call.aio.models.generate_content_stream(
            model=version,
            contents=[
                genai.types.Content(
                    parts=[genai.types.Part(text=request_text)], role='user'
                )
            ],
            config=None,
        )
    ])
    assert isinstance(response, GenerateResponse)
    assert response.message.content[0].root.text == ''
