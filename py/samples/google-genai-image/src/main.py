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

import base64
import os
from io import BytesIO

from PIL import Image

from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI
from genkit.types import Media, MediaPart, Message, Role, TextPart

ai = Genkit(plugins=[GoogleAI()])


@ai.flow()
async def draw_image_with_gemini() -> str:
    """Draw an image.

    Returns:
        The image.
    """
    return await ai.generate(
        prompt='Draw a cat in a hat.',
        config={'response_modalities': ['Text', 'Image']},
        model='googleai/gemini-2.5-flash-image',
    )


@ai.flow()
async def describe_image_with_gemini(data: str) -> str:
    """Describe an image.

    Args:
        data: The image data as a data URI (e.g., 'data:image/jpeg;base64,...').

    Returns:
        The description of the image.
    """
    if not (data.startswith('data:') and ',' in data):
        raise ValueError(f'Expected a data URI (e.g., "data:image/jpeg;base64,..."), but got: {data[:50]}...')

    result = await ai.generate(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text='What is shown in this image?'),
                    MediaPart(media=Media(content_type='image/jpeg', url=data)),
                ],
            ),
        ],
        model='googleai/gemini-3-flash-preview',
    )
    return result.text


async def main() -> None:
    """Main function - keep alive for Dev UI."""
    import asyncio
    print("Genkit server running. Press Ctrl+C to stop.")
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
