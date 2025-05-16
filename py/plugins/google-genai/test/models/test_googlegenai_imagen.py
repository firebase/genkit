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

from genkit.ai import ActionRunContext
from genkit.plugins.google_genai.models.imagen import ImagenModel, ImagenVersion
from genkit.types import (
    GenerateRequest,
    GenerateResponse,
    MediaPart,
    Message,
    Role,
    TextPart,
)


@pytest.mark.asyncio
@pytest.mark.parametrize('version', [x for x in ImagenVersion])
async def test_generate_media_response(mocker, version):
    """Test generate method for media responses."""
    request_text = 'response question'
    response_byte_string = b'\x89PNG\r\n\x1a\n'
    response_mimetype = 'image/png'

    request = GenerateRequest(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text=request_text),
                ],
            ),
        ],
    )

    response_images = genai.types.GenerateImagesResponse(
        generated_images=[
            genai.types.GeneratedImage(
                image=genai.types.Image(image_bytes=response_byte_string, mime_type=response_mimetype)
            )
        ]
    )

    googleai_client_mock = mocker.AsyncMock()
    googleai_client_mock.aio.models.generate_images.return_value = response_images

    imagen = ImagenModel(version, googleai_client_mock)

    ctx = ActionRunContext()
    response = await imagen.generate(request, ctx)

    googleai_client_mock.assert_has_calls([
        mocker.call.aio.models.generate_images(model=version, prompt=request_text, config=None)
    ])
    assert isinstance(response, GenerateResponse)

    content = response.message.content[0]
    assert isinstance(content.root, MediaPart)

    assert content.root.media.content_type == response_mimetype

    decoded_url = base64.b64decode(content.root.media.url)
    assert decoded_url == response_byte_string
