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

"""This sample demonstrates how to use Gemini to describe and draw images."""

import asyncio
import base64
import os
from io import BytesIO

from PIL import Image

from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI, googleai_name
from genkit.types import Media, MediaPart, Message, Role, TextPart

ai = Genkit(plugins=[GoogleAI()])


@ai.flow()
async def draw_image_with_gemini() -> str:
    """Draw an image.

    Returns:
        The image.
    """
    return await ai.agenerate(
        messages=[Message(role=Role.USER, content=[TextPart(text='Draw a cat in a hat.')])],
        config={'response_modalities': ['Text', 'Image']},
        model=googleai_name('gemini-2.0-flash-exp'),
    )


@ai.flow()
async def describe_image_with_gemini(data: str) -> str:
    """Describe an image.

    Args:
        data: The image to describe.

    Returns:
        The description of the image.
    """
    result = await ai.agenerate(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text='What is shown in this image?'),
                    MediaPart(media=Media(contentType='image/jpeg', url=data)),
                ],
            ),
        ],
        model=googleai_name('gemini-2.5-pro-exp-03-25'),
    )
    return result.text


if __name__ == '__main__':
    # Gemini describes an image.  Works both on Gemini API and VertexAI API.
    # Make sure that there is image.jpg on root directory of current sample.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = os.path.join(current_dir, '..', 'image.jpg')

    with open(image_path, 'rb') as image_file:
        buffer = image_file.read()
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        print(asyncio.run(describe_image_with_gemini(img_base64)))

    # Gemini draws an image by description. The model used is available only in
    # Gemini API.
    result = asyncio.run(draw_image_with_gemini())
    decoded_image = BytesIO(base64.b64decode(result.message.content[0].root.media.url))
    image = Image.open(decoded_image)
    image.show('Image generated by Gemini')
