# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Test Gemini models."""

import pytest

from genkit.core.action import ActionRunContext
from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    Message,
    Role,
    TextPart,
)
from genkit.plugins.vertex_ai.gemini import Gemini, GeminiVersion

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
                    TextPart(text=f'Hi, mock!'),
                ],
            ),
        ]
    )
    gemini = Gemini(version, mocker.MagicMock())
    genai_model_mock = mocker.MagicMock()
    model_response_mock = mocker.MagicMock()
    model_response_mock.text = mocked_respond
    genai_model_mock.generate_content.return_value = model_response_mock
    mocker.patch(
        'genkit.plugins.vertex_ai.gemini.Gemini.gemini_model', genai_model_mock
    )

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

    for part, text in zip(result[0].parts, MULTILINE_CONTENT):
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
    for message, text in zip(result, MULTILINE_CONTENT):
        assert message.parts[0].text == text
