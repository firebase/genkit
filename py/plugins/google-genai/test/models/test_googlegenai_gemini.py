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

import base64

import pytest
from google import genai

from genkit.ai import (
    ActionRunContext,
    GenerateRequest,
    GenerateResponse,
    MediaPart,
    Message,
    Part,
    Role,
    TextPart,
)
from genkit.plugins.google_genai.models.gemini import (
    GeminiApiOnlyVersion,
    GeminiModel,
    GeminiVersion,
)


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

    gemini = GeminiModel(version, googleai_client_mock, mocker.MagicMock())

    ctx = ActionRunContext()
    response = await gemini.generate(request, ctx)

    googleai_client_mock.assert_has_calls([
        mocker.call.aio.models.generate_content(
            model=version,
            contents=[
                genai.types.Content(
                    parts=[genai.types.Part(text=request_text)], role=Role.USER
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
                    Part(text=request_text),
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
    gemini = GeminiModel(version, googleai_client_mock, mocker.MagicMock())

    ctx = ActionRunContext(on_chunk=on_chunk_mock)
    response = await gemini.generate(request, ctx)

    googleai_client_mock.assert_has_calls([
        mocker.call.aio.models.generate_content_stream(
            model=version,
            contents=[
                genai.types.Content(
                    parts=[genai.types.Part(text=request_text)], role=Role.USER
                )
            ],
            config=None,
        )
    ])
    assert isinstance(response, GenerateResponse)
    assert response.message.content == []


@pytest.mark.asyncio
@pytest.mark.parametrize('version', [x for x in GeminiApiOnlyVersion])
async def test_generate_media_response(mocker, version):
    request_text = 'response question'
    response_byte_string = b'\x89PNG\r\n\x1a\n'
    response_mimetype = 'image/png'
    modalities = ['Text', 'Image']

    request = GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text=request_text),
                ],
            ),
        ],
        config={'response_modalities': modalities},
    )

    candidate = genai.types.Candidate(
        content=genai.types.Content(
            parts=[
                genai.types.Part(
                    inline_data=genai.types.Blob(
                        data=response_byte_string, mime_type=response_mimetype
                    )
                )
            ]
        )
    )
    resp = genai.types.GenerateContentResponse(candidates=[candidate])

    googleai_client_mock = mocker.AsyncMock()
    googleai_client_mock.aio.models.generate_content.return_value = resp

    gemini = GeminiModel(version, googleai_client_mock, mocker.MagicMock())

    ctx = ActionRunContext()
    response = await gemini.generate(request, ctx)

    googleai_client_mock.assert_has_calls([
        mocker.call.aio.models.generate_content(
            model=version,
            contents=[
                genai.types.Content(
                    parts=[genai.types.Part(text=request_text)], role=Role.USER
                )
            ],
            config=genai.types.GenerateContentConfig(
                response_modalities=modalities
            ),
        )
    ])
    assert isinstance(response, GenerateResponse)

    content = response.message.content[0]
    assert isinstance(content.root, MediaPart)

    assert content.root.media.content_type == response_mimetype

    decoded_url = base64.b64decode(content.root.media.url)
    assert decoded_url == response_byte_string
