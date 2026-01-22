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

"""This sample demonstrates how to use Gemini to describe, draw, and edit images."""

import asyncio
import base64
import os
import pathlib
import sys

# Allow running from source without setting PYTHONPATH
sys.path.append(str(pathlib.Path(__file__).parent.parent.parent.parent / 'packages' / 'genkit' / 'src'))
sys.path.append(
    str(pathlib.Path(__file__).parent.parent.parent.parent / 'plugins' / 'google-genai' / 'src')
)
sys.path.append(
    str(pathlib.Path(__file__).parent.parent.parent.parent / 'plugins' / 'google-cloud' / 'src')
)
# Add user site-packages where uv/pip likely installed dependencies
sys.path.append('/Users/mengqin.shen/Library/Python/3.13/lib/python/site-packages')

from typing import Any, Annotated

from genkit.ai import Genkit
from genkit.plugins.google_genai import (
    GoogleAI,
    GeminiConfigSchema,
    GeminiImageConfigSchema,
)
from genkit.types import (
    GenerationCommonConfig,
    Media,
    MediaPart,
    Message,
    Role,
    TextPart,
)
from google import genai
from google.genai import types as genai_types



if 'GEMINI_API_KEY' not in os.environ:
    os.environ['GEMINI_API_KEY'] = input('Please enter your GEMINI_API_KEY: ')

ai = Genkit(plugins=[GoogleAI()])


@ai.flow()
async def draw_image_with_gemini(prompt: str = '') -> str:
    """Draw an image.

    Args:
        prompt: The prompt to draw.

    Returns:
        The image.
    """
    if not prompt:
        prompt = 'Draw a cat in a hat.'

    return await ai.generate(
        prompt=prompt,
        config={'response_modalities': ['Text', 'Image']},
        model='googleai/gemini-2.5-flash-image',
    )


@ai.flow()
async def describe_image_with_gemini(data: str = '') -> str:
    """Describe an image.

    Args:
        data: The image data as a data URI (e.g., 'data:image/jpeg;base64,...').

    Returns:
        The description of the image.
    """
    if not data:
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(current_dir, '..', 'image.jpg')
            with open(image_path, 'rb') as image_file:
                buffer = image_file.read()
                img_base64 = base64.b64encode(buffer).decode('utf-8')
                data = f'data:image/jpeg;base64,{img_base64}'
        except FileNotFoundError as e:
            raise ValueError("Default image 'image.jpg' not found. Please provide image data.") from e

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


@ai.flow()
async def generate_images(name: str, ctx):
    """Generate images for the given name.

    Args:
        name: the name to send to test function
        ctx: the context of the tool

    Returns:
        The generated response with a function.
    """

    result = await ai.generate(
        model='googleai/gemini-3-pro-image-preview',
        prompt=f'tell me about {name} with photos',
        config=GeminiConfigSchema(response_modalities=['text', 'image'], api_version='v1alpha').model_dump(
            exclude_none=True
        ),
    )
    return result


@ai.tool(name='screenshot')
def screenshot() -> dict:
    """Takes a screenshot."""
    room_path = pathlib.Path(__file__).parent.parent / 'my_room.png'
    with open(room_path, 'rb') as f:
        room_b64 = base64.b64encode(f.read()).decode('utf-8')

    return {
        'output': 'success',
        'content': [{'media': {'url': f'data:image/png;base64,{room_b64}', 'contentType': 'image/png'}}],
    }


@ai.flow()
async def multipart_tool_calling():
    """Multipart tool calling."""
    response = await ai.generate(
        model='googleai/gemini-3-pro-preview',
        tools=['screenshot'],
        config=GenerationCommonConfig(temperature=1),
        prompt="Tell me what I'm seeing on the screen.",
    )
    return response.text


@ai.flow()
async def gemini_image_editing():
    """Image editing with Gemini."""
    plant_path = pathlib.Path(__file__).parent.parent / 'palm_tree.png'
    room_path = pathlib.Path(__file__).parent.parent / 'my_room.png'

    with open(plant_path, 'rb') as f:
        plant_b64 = base64.b64encode(f.read()).decode('utf-8')
    with open(room_path, 'rb') as f:
        room_b64 = base64.b64encode(f.read()).decode('utf-8')

    response = await ai.generate(
        model='googleai/gemini-3-pro-image-preview',
        prompt=[
            TextPart(text='add the plant to my room'),
            MediaPart(media=Media(url=f'data:image/png;base64,{plant_b64}')),
            MediaPart(media=Media(url=f'data:image/png;base64,{room_b64}')),
        ],
        config=GeminiImageConfigSchema(
            response_modalities=['TEXT', 'IMAGE'],
            image_config={'aspect_ratio': '1:1'},
            api_version='v1alpha',
        ).model_dump(exclude_none=True),
    )
    for part in response.message.content:
        if isinstance(part.root, MediaPart):
            return part.root.media

    return None


@ai.flow()
async def nano_banana_pro():
    """Nano banana pro config."""
    response = await ai.generate(
        model='googleai/gemini-3-pro-image-preview',
        prompt='Generate a picture of a sunset in the mountains by a lake',
        config={
            'response_modalities': ['TEXT', 'IMAGE'],
            'image_config': {
                'aspect_ratio': '21:9',
                'image_size': '4K',
            },
            'api_version': 'v1alpha',
        },
    )
    for part in response.message.content:
        if isinstance(part.root, MediaPart):
            return part.root.media
    return response.media


@ai.flow()
async def photo_move_veo(_: Any, context: Any = None):
    """An example of using Ver 3 model to make a static photo move."""
    # Find photo.jpg (or my_room.png)
    room_path = pathlib.Path(__file__).parent.parent / 'my_room.png'
    if not room_path.exists():
        # Fallback search
        room_path = pathlib.Path('samples/google-genai-hello/src/my_room.png')
        if not room_path.exists():
            room_path = pathlib.Path('my_room.png')

    encoded_image = ''
    if room_path.exists():
        with open(room_path, 'rb') as f:
            encoded_image = base64.b64encode(f.read()).decode('utf-8')
    else:
        # Fallback dummy
        encoded_image = (
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
        )

    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_GENAI_API_KEY')
    if not api_key:
        raise ValueError('GEMINI_API_KEY not set')

    # Use v1alpha for Veo
    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})

    # Prompt construction
    prompt_parts = [
        genai_types.Part(text='make the subject in the photo move'),
        genai_types.Part(inline_data=genai_types.Blob(mime_type='image/jpeg', data=base64.b64decode(encoded_image))),
    ]

    if context:
        context.send_chunk(f'Starting generation with veo-3.0-generate-001...')

    try:
        operation = await client.aio.models.generate_videos(
            model='veo-3.0-generate-001',
            prompt='make the subject in the photo move',
            image=genai_types.Image(image_bytes=base64.b64decode(encoded_image), mime_type='image/png'),
            config={
                # 'aspect_ratio': '9:16',
            },
        )

        if not operation:
            raise ValueError('Expected operation to be returned')

        while not operation.done:
            op_id = operation.name.split('/')[-1] if operation.name else 'unknown'
            if context:
                context.send_chunk(f'check status of operation {op_id}')

            # Poll
            operation = await client.aio.operations.get(operation)
            await asyncio.sleep(5)

        if operation.error:
            if context:
                context.send_chunk(f'Error: {operation.error.message}')
            raise ValueError(f'Failed to generate video: {operation.error.message}')

        # Done
        result_info = 'Video generated successfully.'
        if hasattr(operation, 'result') and operation.result:
            if hasattr(operation.result, 'generated_videos') and operation.result.generated_videos:
                vid = operation.result.generated_videos[0]
                if vid.video and vid.video.uri:
                    result_info += f' URI: {vid.video.uri}'

        if context:
            context.send_chunk(f'Done! {result_info}')

        return operation

    except Exception as e:
        raise ValueError(f'Flow failed: {e}')


@ai.flow()
async def gemini_media_resolution():
    """Media resolution."""
    # Placeholder base64 for sample
    plant_path = pathlib.Path(__file__).parent.parent / 'palm_tree.png'
    with open(plant_path, 'rb') as f:
        plant_b64 = base64.b64encode(f.read()).decode('utf-8')
    response = await ai.generate(
        model='googleai/gemini-3-pro-image-preview',
        prompt=[
            TextPart(text='What is in this picture?'),
            MediaPart(
                media=Media(url=f'data:image/png;base64,{plant_b64}'),
                metadata={'mediaResolution': {'level': 'MEDIA_RESOLUTION_HIGH'}},
            ),
        ],
        config={'api_version': 'v1alpha'},
    )
    return response.text


@ai.flow()
async def multimodal_input():
    """Multimodal input."""
    photo_path = pathlib.Path(__file__).parent.parent / 'photo.jpg'
    with open(photo_path, 'rb') as f:
        photo_b64 = base64.b64encode(f.read()).decode('utf-8')

    response = await ai.generate(
        model='googleai/gemini-3-pro-image-preview',
        prompt=[
            TextPart(text='describe this photo'),
            MediaPart(media=Media(url=f'data:image/jpeg;base64,{photo_b64}', content_type='image/jpeg')),
        ],
    )
    return response.text


async def main() -> None:
    """Main function."""
    import asyncio

    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info('Genkit server running. Press Ctrl+C to stop.')
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
