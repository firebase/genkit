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

"""Hello Google GenAI Vertex AI sample."""

import argparse
import base64
from enum import Enum
import pathlib

import structlog

from genkit.ai import Genkit, MediaPart, Media, TextPart
from genkit.plugins.google_genai import VertexAI, GeminiImageConfigSchema
from genkit.types import GenerationCommonConfig

logger = structlog.get_logger(__name__)


ai = Genkit(
    plugins=[
        VertexAI(location='us-central1'),
    ],
    model='vertexai/gemini-2.5-flash',
)


class ThinkingLevel(str, Enum):
    LOW = 'LOW'
    HIGH = 'HIGH'


@ai.flow()
async def thinking_level_pro(level: ThinkingLevel):
    """Gemini 3.0 thinkingLevel config (Pro)."""
    response = await ai.generate(
        model='vertexai/gemini-3-pro-preview',
        prompt=(
            'Alice, Bob, and Carol each live in a different house on the '
            'same street: red, green, and blue. The person who lives in the red house '
            'owns a cat. Bob does not live in the green house. Carol owns a dog. The '
            'green house is to the left of the red house. Alice does not own a cat. '
            'The person in the blue house owns a fish. '
            'Who lives in each house, and what pet do they own? Provide your '
            'step-by-step reasoning.'
        ),
        config={
            'thinking_config': {
                'include_thoughts': True,
                'thinking_level': level.value,
            }
        },
    )
    return response.text


class ThinkingLevelFlash(str, Enum):
    MINIMAL = 'MINIMAL'
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'


@ai.flow()
async def thinking_level_flash(level: ThinkingLevelFlash):
    """Gemini 3.0 thinkingLevel config (Flash)."""
    response = await ai.generate(
        model='vertexai/gemini-3-flash-preview',
        prompt=(
            'Alice, Bob, and Carol each live in a different house on the '
            'same street: red, green, and blue. The person who lives in the red house '
            'owns a cat. Bob does not live in the green house. Carol owns a dog. The '
            'green house is to the left of the red house. Alice does not own a cat. '
            'The person in the blue house owns a fish. '
            'Who lives in each house, and what pet do they own? Provide your '
            'step-by-step reasoning.'
        ),
        config={
            'thinking_config': {
                'include_thoughts': True,
                'thinking_level': level.value,
            }
        },
    )
    return response.text


@ai.flow()
async def video_understanding_metadata():
    """Video understanding with metadata."""
    response = await ai.generate(
        model='vertexai/gemini-2.5-flash',
        prompt=[
            MediaPart(
                media=Media(url='gs://cloud-samples-data/video/animals.mp4', content_type='video/mp4'),
                metadata={
                    'videoMetadata': {
                        'fps': 0.5,
                        'startOffset': '3.5s',
                        'endOffset': '10.2s',
                    }
                }
            ),
            TextPart(text='describe this video'),
        ],
    )
    return response.text


@ai.flow()
async def maps_grounding():
    """Google maps grounding."""
    response = await ai.generate(
        model='vertexai/gemini-2.5-flash',
        prompt='Describe some sights near me',
        config={
            'tools': [{'googleMaps': {'enableWidget': True}}],
            'retrieval_config': {
                'latLng': {
                    'latitude': 43.0896,
                    'longitude': -79.0849,
                },
            },
        },
    )
    return response.text


@ai.flow()
async def search_grounding():
    """Search grounding."""
    response = await ai.generate(
        model='vertexai/gemini-2.5-flash',
        prompt='Who is Albert Einstein?',
        config={'tools': [{'googleSearch': {}}]},
    )
    return response.text


@ai.flow()
async def gemini_media_resolution():
    """Media resolution."""
    # Placeholder base64 for sample
    plant_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
    response = await ai.generate(
        model='vertexai/gemini-3-pro-preview',
        prompt=[
            TextPart(text='What is in this picture?'),
            MediaPart(
                media=Media(url=f'data:image/png;base64,{plant_b64}'),
                metadata={'mediaResolution': {'level': 'MEDIA_RESOLUTION_HIGH'}}
            ),
        ],
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
        model='vertexai/gemini-2.5-flash-image-preview',
        prompt=[
            TextPart(text='add the plant to my room'),
            MediaPart(media=Media(url=f'data:image/png;base64,{plant_b64}')),
            MediaPart(media=Media(url=f'data:image/png;base64,{room_b64}')),
        ],
        config=GeminiImageConfigSchema(
            response_modalities=['TEXT', 'IMAGE'],
            image_config={'aspect_ratio': '1:1'},
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
        model='vertexai/gemini-3-pro-image-preview',
        prompt='Generate a picture of a sunset in the mountains by a lake',
        config={
            'response_modalities': ['TEXT', 'IMAGE'],
            'image_config': {
                'aspect_ratio': '3:4',
                'image_size': '1K',
            },
        },
    )
    return response.media


@ai.flow()
async def imagen_image_generation():
    """A simple example of image generation with Gemini (Imagen)."""
    response = await ai.generate(
        model='vertexai/imagen-3.0-generate-002',
        prompt='generate an image of a banana riding a bicycle',
    )
    return response.media


@ai.tool(name='getWeather')
def get_weather(location: str) -> dict:
    """Used to get current weather for a location."""
    return {
        'location': location,
        'temperature_celcius': 21.5,
        'conditions': 'cloudy',
    }


@ai.tool(name='celsiusToFahrenheit')
def celsius_to_fahrenheit(celsius: float) -> float:
    """Converts Celsius to Fahrenheit."""
    return (celsius * 9) / 5 + 32


@ai.flow()
async def tool_calling(location: str = 'Paris, France'):
    """Tool calling with Gemini."""
    response = await ai.generate(
        model='vertexai/gemini-2.5-flash',
        tools=['getWeather', 'celsiusToFahrenheit'],
        prompt=f"What's the weather in {location}? Convert the temperature to Fahrenheit.",
        config=GenerationCommonConfig(temperature=1),
    )
    return response.text


async def main() -> None:
    """Main function."""
    # Example run logic can go here or be empty for pure flow server
    pass


if __name__ == '__main__':
    ai.run_main(main())
