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

"""Test Gemini models."""

import pytest

from genkit.ai import ActionRunContext
from genkit.plugins.vertex_ai.gemini import Gemini, GeminiVersion
from genkit.types import (
    GenerateRequest,
    GenerateResponse,
    Message,
    Role,
    TextPart,
)

MULTILINE_CONTENT = [
    'Hi, Gemini!',
    'I have a question for you.',
    'Where can I read a Genkit documentation?',
]


@pytest.mark.parametrize('version', [x for x in GeminiVersion])
def test_generate_text_response(mocker, version):
    mocked_respond = 'Mocked Respond'
    request = GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text='Hi, mock!'),
                ],
            ),
        ]
    )
    gemini = Gemini(version, mocker.MagicMock())
    genai_model_mock = mocker.MagicMock()
    model_response_mock = mocker.MagicMock()
    model_response_mock.text = mocked_respond
    genai_model_mock.generate_content.return_value = model_response_mock
    mocker.patch('genkit.plugins.vertex_ai.gemini.Gemini.gemini_model', genai_model_mock)

    ctx = ActionRunContext()
    response = gemini.generate(request, ctx)
    assert isinstance(response, GenerateResponse)
    assert response.message.content[0].root.text == mocked_respond


@pytest.mark.parametrize('version', [x for x in GeminiVersion])
def test_gemini_metadata(mocker, version):
    gemini = Gemini(version, mocker.MagicMock())
    supports = gemini.model_metadata['model']['supports']
    assert isinstance(supports, dict)
    assert supports['multiturn']
    assert supports['media']
    assert supports['tools']
    assert supports['system_role']


def test_built_gemini_message_multiple_parts(mocker):
    request = GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text=x) for x in MULTILINE_CONTENT],
            ),
        ],
    )
    gemini = Gemini(GeminiVersion.GEMINI_1_5_FLASH, mocker.MagicMock())
    result = gemini.build_messages(request)
    assert isinstance(result, list)
    assert isinstance(result[0].parts, list)
    assert len(result[0].parts) == len(MULTILINE_CONTENT)

    for part, text in zip(result[0].parts, MULTILINE_CONTENT, strict=False):
        assert part.text == text


def test_built_gemini_message_multiple_messages(mocker):
    request = GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text=text)],
            )
            for text in MULTILINE_CONTENT
        ],
    )
    gemini = Gemini(GeminiVersion.GEMINI_1_5_FLASH, mocker.MagicMock())
    result = gemini.build_messages(request)
    assert isinstance(result, list)
    assert len(result) == len(MULTILINE_CONTENT)
    for message, text in zip(result, MULTILINE_CONTENT, strict=False):
        assert message.parts[0].text == text
