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
import sys  # noqa

if sys.version_info < (3, 11):  # noqa
    from strenum import StrEnum  # noqa
else:  # noqa
    from enum import StrEnum  # noqa

import pytest
from google import genai
from google.genai import types as genai_types
from pydantic import BaseModel, Field

from genkit.ai import ActionRunContext
from genkit.core.schema import to_json_schema
from genkit.plugins.google_genai.models.gemini import (
    GeminiModel,
    GoogleAIGeminiVersion,
    VertexAIGeminiVersion,
)
from genkit.types import (
    GenerateRequest,
    GenerateResponse,
    MediaPart,
    Message,
    Part,
    Role,
    TextPart,
)

ALL_VERSIONS = list(GoogleAIGeminiVersion) + list(VertexAIGeminiVersion)
IMAGE_GENERATION_VERSIONS = [GoogleAIGeminiVersion.GEMINI_2_0_FLASH_EXP]


@pytest.mark.asyncio
@pytest.mark.parametrize('version', [x for x in ALL_VERSIONS])
async def test_generate_text_response(mocker, version):
    """Test the generate method for text responses."""
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
    candidate = genai.types.Candidate(content=genai.types.Content(parts=[genai.types.Part(text=response_text)]))
    resp = genai.types.GenerateContentResponse(candidates=[candidate])

    googleai_client_mock = mocker.AsyncMock()
    googleai_client_mock.aio.models.generate_content.return_value = resp

    gemini = GeminiModel(version, googleai_client_mock, mocker.MagicMock())

    ctx = ActionRunContext()
    response = await gemini.generate(request, ctx)

    googleai_client_mock.assert_has_calls([
        mocker.call.aio.models.generate_content(
            model=version,
            contents=[genai.types.Content(parts=[genai.types.Part(text=request_text)], role=Role.USER)],
            config=None,
        )
    ])
    assert isinstance(response, GenerateResponse)
    assert response.message.content[0].root.text == response_text


@pytest.mark.asyncio
@pytest.mark.parametrize('version', [x for x in ALL_VERSIONS])
async def test_generate_stream_text_response(mocker, version):
    """Test the generate method for text responses."""
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
    candidate = genai.types.Candidate(content=genai.types.Content(parts=[genai.types.Part(text=response_text)]))

    resp = genai.types.GenerateContentResponse(candidates=[candidate])

    googleai_client_mock = mocker.AsyncMock()
    googleai_client_mock.aio.models.generate_content_stream.__aiter__.side_effect = [resp]
    on_chunk_mock = mocker.MagicMock()
    gemini = GeminiModel(version, googleai_client_mock, mocker.MagicMock())

    ctx = ActionRunContext(on_chunk=on_chunk_mock)
    response = await gemini.generate(request, ctx)

    googleai_client_mock.assert_has_calls([
        mocker.call.aio.models.generate_content_stream(
            model=version,
            contents=[genai.types.Content(parts=[genai.types.Part(text=request_text)], role=Role.USER)],
            config=None,
        )
    ])
    assert isinstance(response, GenerateResponse)
    assert response.message.content == []


@pytest.mark.asyncio
@pytest.mark.parametrize('version', [x for x in IMAGE_GENERATION_VERSIONS])
async def test_generate_media_response(mocker, version):
    """Test generate method for media responses."""
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
                genai.types.Part(inline_data=genai.types.Blob(data=response_byte_string, mime_type=response_mimetype))
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
            contents=[genai.types.Content(parts=[genai.types.Part(text=request_text)], role=Role.USER)],
            config=genai.types.GenerateContentConfig(response_modalities=modalities),
        )
    ])
    assert isinstance(response, GenerateResponse)

    content = response.message.content[0]
    assert isinstance(content.root, MediaPart)

    assert content.root.media.content_type == response_mimetype

    decoded_url = base64.b64decode(content.root.media.url)
    assert decoded_url == response_byte_string


def test_convert_schema_property(mocker):
    googleai_client_mock = mocker.AsyncMock()
    gemini = GeminiModel('abc', googleai_client_mock, mocker.MagicMock())

    class Simple(BaseModel):
        foo: str = Field(description='foo field')
        bar: int = Field(description='bar field')
        baz: list[str] = Field(default=None, description='bar field')

    assert gemini._convert_schema_property(to_json_schema(Simple)) == genai_types.Schema(
        type='OBJECT',
        properties={
            'foo': genai_types.Schema(
                type='STRING',
                description='foo field',
            ),
            'bar': genai_types.Schema(
                type='INTEGER',
                description='bar field',
            ),
            'baz': genai_types.Schema(
                type='ARRAY',
                description='bar field',
                items={'type': 'string'},
            ),
        },
        required=['foo', 'bar'],
    )

    class Nested(BaseModel):
        baz: int = Field(description='baz field')

    class WithNested(BaseModel):
        foo: str = Field(description='foo field')
        bar: Nested = Field(description='bar field')

    assert gemini._convert_schema_property(to_json_schema(WithNested)) == genai_types.Schema(
        type='OBJECT',
        properties={
            'foo': genai_types.Schema(
                type='STRING',
                description='foo field',
            ),
            'bar': genai_types.Schema(
                type='OBJECT',
                description='bar field',
                properties={
                    'baz': genai_types.Schema(
                        type='INTEGER',
                        description='baz field',
                    ),
                },
                required=['baz'],
            ),
        },
        required=['foo', 'bar'],
    )

    class TestEnum(StrEnum):
        FOO = 'foo'
        BAR = 'bar'

    class WitEnum(BaseModel):
        foo: TestEnum = Field(description='foo field')

    assert gemini._convert_schema_property(to_json_schema(WitEnum)) == genai_types.Schema(
        type='OBJECT',
        properties={
            'foo': genai_types.Schema(
                type='STRING',
                description='foo field',
                enum=['foo', 'bar'],
            ),
        },
        required=['foo'],
    )


@pytest.mark.asyncio
async def test_generate_with_system_instructions(mocker):
    response_text = 'request answer'
    request_text = 'response question'
    system_instruction = 'system instruciton text'
    version = GoogleAIGeminiVersion.GEMINI_2_0_FLASH

    request = GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text=request_text),
                ],
            ),
            Message(
                role=Role.SYSTEM,
                content=[
                    TextPart(text=system_instruction),
                ],
            ),
        ]
    )
    candidate = genai.types.Candidate(content=genai.types.Content(parts=[genai.types.Part(text=response_text)]))
    resp = genai.types.GenerateContentResponse(candidates=[candidate])

    expected_system_instruction = genai.types.Content(parts=[genai.types.Part(text=system_instruction)])

    googleai_client_mock = mocker.AsyncMock()
    googleai_client_mock.aio.models.generate_content.return_value = resp

    gemini = GeminiModel(version, googleai_client_mock, mocker.MagicMock())
    ctx = ActionRunContext()

    response = await gemini.generate(request, ctx)

    googleai_client_mock.assert_has_calls([
        mocker.call.aio.models.generate_content(
            model=version,
            contents=[genai.types.Content(parts=[genai.types.Part(text=request_text)], role=Role.USER)],
            config=genai.types.GenerateContentConfig(system_instruction=expected_system_instruction),
        )
    ])
    assert isinstance(response, GenerateResponse)
    assert response.message.content[0].root.text == response_text
