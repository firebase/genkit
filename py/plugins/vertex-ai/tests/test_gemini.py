# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Test Gemini models."""

import pytest
from genkit.core.typing import (
    GenerateRequest,
    GenerateResponse,
    Message,
    Role,
    TextPart,
)
from genkit.plugins.vertex_ai.gemini import Gemini, GeminiVersion


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
    gemini = Gemini(version)
    genai_model_mock = mocker.MagicMock()
    model_response_mock = mocker.MagicMock()
    model_response_mock.text = mocked_respond
    genai_model_mock.generate_content.return_value = model_response_mock
    mocker.patch(
        'genkit.plugins.vertex_ai.gemini.Gemini.gemini_model', genai_model_mock
    )

    response = gemini.handle_request(request)
    assert isinstance(response, GenerateResponse)
    assert response.message.content[0].root.text == mocked_respond


@pytest.mark.parametrize('version', [x for x in GeminiVersion])
def test_gemini_metadata(version):
    gemini = Gemini(version)
    supports = gemini.model_metadata['model']['supports']
    assert isinstance(supports, dict)
    assert supports['multiturn']
    assert supports['media']
    assert supports['tools']
    assert supports['system_role']
