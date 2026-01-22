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

"""Hello Google GenAI sample.

Key features demonstrated in this sample:

| Feature Description                                      | Example Function / Code Snippet        |
|----------------------------------------------------------|----------------------------------------|
| Plugin Initialization                                    | `ai = Genkit(plugins=[GoogleAI()])` |
| Default Model Configuration                              | `ai = Genkit(model=...)`               |
| Defining Flows                                           | `@ai.flow()` decorator (multiple uses) |
| Defining Tools                                           | `@ai.tool()` decorator (multiple uses) |
| Pydantic for Tool Input Schema                           | `GablorkenInput`                       |
| Simple Generation (Prompt String)                        | `say_hi`                               |
| Generation with Messages (`Message`, `Role`, `TextPart`) | `simple_generate_with_tools_flow`      |
| Generation with Tools                                    | `simple_generate_with_tools_flow`      |
| Tool Response Handling                                   | `simple_generate_with_interrupts`      |
| Tool Interruption (`ctx.interrupt`)                      | `gablorken_tool2`                      |
| Embedding (`ai.embed`, `Document`)                       | `embed_docs`                           |
| Generation Configuration (`temperature`, etc.)           | `say_hi_with_configured_temperature`   |
| Streaming Generation (`ai.generate_stream`)              | `say_hi_stream`                        |
| Streaming Chunk Handling (`ctx.send_chunk`)              | `say_hi_stream`, `generate_character`  |
| Structured Output (Schema)                               | `generate_character`                   |
| Pydantic for Structured Output Schema                    | `RpgCharacter`                         |
| Unconstrained Structured Output                          | `generate_character_unconstrained`     |
| Multi-modal Output Configuration                         | `generate_images`                      |
| GCP Telemetry (Traces and Metrics)                       | `add_gcp_telemetry()`                  |

"""

import argparse
import asyncio
import os
from enum import StrEnum
from typing import Annotated

import structlog
from pydantic import BaseModel, Field

from genkit.ai import Document, Genkit, ToolRunContext, tool_response
from genkit.core.action import ActionRunContext
from genkit.plugins.evaluators import GenkitMetricType, MetricConfig, define_genkit_evaluators
from genkit.plugins.google_cloud import add_gcp_telemetry
from genkit.plugins.google_genai import (
    EmbeddingTaskType,
    GoogleAI,
)
from genkit.types import (
    GenerationCommonConfig,
    Media,
    MediaPart,
    Message,
    Role,
    TextPart,
)

logger = structlog.get_logger(__name__)


if 'GEMINI_API_KEY' not in os.environ:
    os.environ['GEMINI_API_KEY'] = input('Please enter your GEMINI_API_KEY: ')


ai = Genkit(
    plugins=[GoogleAI()],
    model='googleai/gemini-3-flash-preview',
)

define_genkit_evaluators(
    ai,
    [
        MetricConfig(metric_type=GenkitMetricType.REGEX),
        MetricConfig(metric_type=GenkitMetricType.DEEP_EQUAL),
        MetricConfig(metric_type=GenkitMetricType.JSONATA),
    ],
)


class GablorkenInput(BaseModel):
    """The Pydantic model for tools."""

    value: int = Field(description='value to calculate gablorken for')


@ai.tool(name='gablorkenTool')
def gablorken_tool(input_: GablorkenInput) -> dict[str, int]:
    """Calculate a gablorken.

    Returns:
        The calculated gablorken.
    """
    return {'result': input_.value * 3 - 5}


@ai.flow()
async def simple_generate_with_tools_flow(value: int, ctx: ActionRunContext) -> str:
    """Generate a greeting for the given name.

    Args:
        value: the integer to send to test function

    Returns:
        The generated response with a function.
    """
    response = await ai.generate(
        prompt=f'what is a gablorken of {value}',
        tools=['gablorkenTool'],
        on_chunk=ctx.send_chunk,
    )
    return response.text


@ai.tool(name='gablorkenTool2')
def gablorken_tool2(input_: GablorkenInput, ctx: ToolRunContext):
    """The user-defined tool function.

    Args:
        input_: the input to the tool
        ctx: the tool run context

    Returns:
        The calculated gablorken.
    """
    ctx.interrupt()


@ai.flow()
async def simple_generate_with_interrupts(value: int) -> str:
    """Generate a greeting for the given name.

    Args:
        value: the integer to send to test function

    Returns:
        The generated response with a function.
    """
    response1 = await ai.generate(
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text=f'what is a gablorken of {value}')],
            ),
        ],
        tools=['gablorkenTool2'],
    )
    await logger.ainfo(f'len(response.tool_requests)={len(response1.tool_requests)}')
    if len(response1.interrupts) == 0:
        return response1.text

    tr = tool_response(response1.interrupts[0], {'output': 178})
    response = await ai.generate(
        messages=response1.messages,
        tool_responses=[tr],
        tools=['gablorkenTool'],
    )
    return response


@ai.flow()
async def say_hi(name: str):
    """Generate a greeting for the given name.

    Args:
        name: the name to send to test function

    Returns:
        The generated response with a function.
    """
    resp = await ai.generate(
        prompt=f'hi {name}',
    )

    await logger.ainfo(
        'generation_response',
        has_usage=hasattr(resp, 'usage'),
        usage_dict=resp.usage.model_dump() if hasattr(resp, 'usage') and resp.usage else None,
        text_length=len(resp.text),
    )

    return resp.text


@ai.flow()
async def embed_docs(docs: Annotated[list[str], Field(default=[''], description='List of texts to embed')] = None):
    """Generate an embedding for the words in a list.

    Args:
        docs: list of texts (string)

    Returns:
        The generated embedding.
    """
    if docs is None:
        docs = ['']
    options = {'task_type': EmbeddingTaskType.CLUSTERING}
    return await ai.embed(
        embedder='googleai/text-embedding-004',
        documents=[Document.from_text(doc) for doc in docs],
        options=options,
    )


@ai.flow()
async def say_hi_with_configured_temperature(data: str):
    """Generate a greeting for the given name.

    Args:
        data: the name to send to test function

    Returns:
        The generated response with a function.
    """
    return await ai.generate(
        messages=[Message(role=Role.USER, content=[TextPart(text=f'hi {data}')])],
        config=GenerationCommonConfig(temperature=0.1),
    )


@ai.flow()
async def say_hi_stream(name: str, ctx):
    """Generate a greeting for the given name.

    Args:
        name: the name to send to test function
        ctx: the context of the tool

    Returns:
        The generated response with a function.
    """
    stream, _ = ai.generate_stream(prompt=f'hi {name}')
    result = ''
    async for data in stream:
        ctx.send_chunk(data.text)
        for part in data.content:
            result += part.root.text

    return result


class Skills(BaseModel):
    """Skills for an RPG character."""

    strength: int = Field(description='strength (0-100)')
    charisma: int = Field(description='charisma (0-100)')
    endurance: int = Field(description='endurance (0-100)')


class RpgCharacter(BaseModel):
    """An RPG character."""

    name: str = Field(description='name of the character')
    back_story: str = Field(description='back story', alias='backStory')
    abilities: list[str] = Field(description='list of abilities (3-4)')
    skills: Skills


@ai.flow()
async def generate_character(name: str, ctx):
    """Generate an RPG character.

    Args:
        name: the name of the character
        ctx: the context of the tool

    Returns:
        The generated RPG character.
    """
    if ctx.is_streaming:
        stream, result = ai.generate_stream(
            prompt=f'generate an RPG character named {name}',
            output_schema=RpgCharacter,
        )
        async for data in stream:
            ctx.send_chunk(data.output)

        return (await result).output
    else:
        result = await ai.generate(
            prompt=f'generate an RPG character named {name}',
            output_schema=RpgCharacter,
        )
        return result.output


@ai.flow()
async def generate_character_unconstrained(name: str, ctx):
    """Generate an unconstrained RPG character.

    Args:
        name: the name of the character
        ctx: the context of the tool

    Returns:
        The generated RPG character.
    """
    result = await ai.generate(
        prompt=f'generate an RPG character named {name}',
        output_schema=RpgCharacter,
        output_constrained=False,
        output_instructions=True,
    )
    return result.output


class ThinkingLevel(StrEnum):
    LOW = 'LOW'
    HIGH = 'HIGH'


@ai.flow()
async def thinking_level_pro(level: ThinkingLevel):
    """Gemini 3.0 thinkingLevel config (Pro)."""
    response = await ai.generate(
        model='googleai/gemini-3-pro-preview',
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
            }
        },
    )
    return response.text


class ThinkingLevelFlash(StrEnum):
    MINIMAL = 'MINIMAL'
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'


@ai.flow()
async def thinking_level_flash(level: ThinkingLevelFlash):
    """Gemini 3.0 thinkingLevel config (Flash)."""
    response = await ai.generate(
        model='googleai/gemini-3-flash-preview',
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
            }
        },
    )
    return response.text


@ai.flow()
async def search_grounding():
    """Search grounding."""
    response = await ai.generate(
        model='googleai/gemini-3-flash-preview',
        prompt='Who is Albert Einstein?',
        config={'tools': [{'googleSearch': {}}], 'api_version': 'v1alpha'},
    )
    return response.text


@ai.flow()
async def url_context():
    """Url context."""
    response = await ai.generate(
        model='googleai/gemini-3-flash-preview',
        prompt='Compare the ingredients and cooking times from the recipes at https://www.foodnetwork.com/recipes/ina-garten/perfect-roast-chicken-recipe-1940592 and https://www.allrecipes.com/recipe/70679/simple-whole-roasted-chicken/',
        config={'url_context': {}, 'api_version': 'v1alpha'},
    )
    return response.text


@ai.flow()
async def file_search():
    """File Search."""
    # TODO: add file search store
    store_name = 'fileSearchStores/sample-store'
    response = await ai.generate(
        model='googleai/gemini-3-flash-preview',
        prompt="What is the character's name in the story?",
        config={
            'file_search': {
                'file_search_store_names': [store_name],
                'metadata_filter': 'author=foo',
            },
            'api_version': 'v1alpha',
        },
    )
    return response.text


@ai.flow()
async def youtube_videos():
    """YouTube videos."""
    response = await ai.generate(
        model='googleai/gemini-3-flash-preview',
        prompt=[
            TextPart(text='transcribe this video'),
            MediaPart(media=Media(url='https://www.youtube.com/watch?v=3p1P5grjXIQ', content_type='video/mp4')),
        ],
        config={'api_version': 'v1alpha'},
    )
    return response.text


class WeatherInput(BaseModel):
    """Input for getting weather."""

    location: str = Field(description='The city and state, e.g. San Francisco, CA')


@ai.tool(name='getWeather')
def get_weather(input_: WeatherInput) -> dict:
    """Used to get current weather for a location."""
    return {
        'location': input_.location,
        'temperature_celcius': 21.5,
        'conditions': 'cloudy',
    }


@ai.tool(name='celsiusToFahrenheit')
def celsius_to_fahrenheit(celsius: float) -> float:
    """Converts Celsius to Fahrenheit."""
    return (celsius * 9) / 5 + 32


@ai.flow()
async def tool_calling(location: Annotated[str, Field(default='Paris, France')]):
    """Tool calling with Gemini."""
    response = await ai.generate(
        model='googleai/gemini-2.5-flash',
        tools=['getWeather', 'celsiusToFahrenheit'],
        prompt=f"What's the weather in {location}? Convert the temperature to Fahrenheit.",
        config=GenerationCommonConfig(temperature=1),
    )
    return response.text


async def main() -> None:
    """Main function - keep alive for Dev UI."""
    await logger.ainfo('Genkit server running. Press Ctrl+C to stop.')
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Google GenAI Hello Sample')
    parser.add_argument(
        '--enable-gcp-telemetry',
        action='store_true',
        help='Enable Google Cloud Platform telemetry',
    )
    args = parser.parse_args()
    if args.enable_gcp_telemetry:
        add_gcp_telemetry()
    ai.run_main(main())
