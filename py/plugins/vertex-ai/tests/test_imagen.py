# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Test Gemini models."""

import pytest

from genkit.ai import ActionRunContext
from genkit.plugins.vertex_ai.imagen import Imagen, ImagenVersion
from genkit.types import (
    GenerateRequest,
    GenerateResponse,
    Media,
    Message,
    Role,
    TextPart,
)


@pytest.mark.parametrize('version', [x for x in ImagenVersion])
def test_generate(mocker, version):
    mocked_respond = 'Supposed Base64 string'
    request = GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text='Draw a test.'),
                ],
            ),
        ]
    )
    imagen = Imagen(version)
    genai_model_mock = mocker.MagicMock()
    model_response_mock = mocker.MagicMock()
    model_response_mock._mime_type = ''
    model_response_mock._as_base64_string.return_value = mocked_respond
    genai_model_mock.generate_images.return_value = [model_response_mock]
    mocker.patch('genkit.plugins.vertex_ai.imagen.Imagen.model', genai_model_mock)

    ctx = ActionRunContext()
    response = imagen.generate(request, ctx)
    assert isinstance(response, GenerateResponse)
    assert isinstance(response.message.content[0].root.media, Media)
    assert response.message.content[0].root.media.url == mocked_respond


@pytest.mark.parametrize('version', [x for x in ImagenVersion])
def test_gemini_metadata(version):
    imagen = Imagen(version)
    supports = imagen.model_metadata['model']['supports']
    assert isinstance(supports, dict)
    assert not supports['multiturn']
    assert not supports['tools']
    assert not supports['system_role']


def test_create_prompt():
    content = ['Text1', 'Text2', 'Text3']
    request = GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text=x) for x in content],
            ),
        ],
    )
    imagen = Imagen(ImagenVersion.IMAGEN3_FAST)
    result = imagen.build_prompt(request)
    expected = ' '.join(content)
    assert isinstance(result, str)
    assert result == expected
