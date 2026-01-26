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
| Thinking Mode (CoT)                                      | `thinking_level_pro`, `thinking_level_flash` |
| Search Grounding                                         | `search_grounding`                     |
| URL Context                                              | `url_context`                          |
| Multimodal Generation (Video input)                      | `youtube_videos`                       |
"""

import argparse
import asyncio
import os
import sys

if sys.version_info < (3, 11):
    from strenum import StrEnum
else:
    from enum import StrEnum
from typing import Annotated, cast

import structlog
from pydantic import BaseModel, Field

from genkit.ai import Genkit, ToolRunContext, tool_response
from genkit.blocks.model import GenerateResponseWrapper
from genkit.core.action import ActionRunContext
from genkit.plugins.evaluators import GenkitMetricType, MetricConfig, define_genkit_evaluators
from genkit.plugins.google_cloud import add_gcp_telemetry
from genkit.plugins.google_genai import (
    EmbeddingTaskType,
    GoogleAI,
)
from genkit.types import (
    Embedding,
    GenerationCommonConfig,
    Media,
    MediaPart,
    Message,
    Part,
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


class CurrencyExchangeInput(BaseModel):
    """Currency exchange flow input schema."""

    amount: float = Field(description='Amount to convert', default=100)
    from_curr: str = Field(description='Source currency code', default='USD')
    to_curr: str = Field(description='Target currency code', default='EUR')


class CurrencyInput(BaseModel):
    """Currency conversion input schema."""

    amount: float = Field(description='Amount to convert', default=100)
    from_currency: str = Field(description='Source currency code (e.g., USD)', default='USD')
    to_currency: str = Field(description='Target currency code (e.g., EUR)', default='EUR')


class GablorkenInput(BaseModel):
    """The Pydantic model for tools."""

    value: int = Field(description='value to calculate gablorken for')


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


class ThinkingLevel(StrEnum):
    """Thinking level enum."""

    LOW = 'LOW'
    HIGH = 'HIGH'


class ThinkingLevelFlash(StrEnum):
    """Thinking level flash enum."""

    MINIMAL = 'MINIMAL'
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'


class WeatherInput(BaseModel):
    """Input for getting weather."""

    location: str = Field(description='The city and state, e.g. San Francisco, CA')


@ai.tool(name='celsiusToFahrenheit')
def celsius_to_fahrenheit(celsius: float) -> float:
    """Converts Celsius to Fahrenheit."""
    return (celsius * 9) / 5 + 32


@ai.tool()
def convert_currency(input: CurrencyInput) -> str:
    """Convert currency amount.

    Args:
        input: Currency conversion parameters.

    Returns:
        Converted amount.
    """
    # Mock conversion rates
    rates = {
        ('USD', 'EUR'): 0.85,
        ('EUR', 'USD'): 1.18,
        ('USD', 'GBP'): 0.73,
        ('GBP', 'USD'): 1.37,
    }

    rate = rates.get((input.from_currency, input.to_currency), 1.0)
    converted = input.amount * rate

    return f'{input.amount} {input.from_currency} = {converted:.2f} {input.to_currency}'


@ai.flow()
async def currency_exchange(input: CurrencyExchangeInput) -> str:
    """Convert currency using tools.

    Args:
        input: Currency exchange parameters.

    Returns:
        Conversion result.
    """
    response = await ai.generate(
        prompt=f'Convert {input.amount} {input.from_curr} to {input.to_curr}',
        tools=['convert_currency'],
    )
    return response.text


@ai.flow()
async def demo_dynamic_tools(
    input_val: Annotated[str, Field(default='Dynamic tools demo')] = 'Dynamic tools demo',
) -> dict:
    """Demonstrates advanced Genkit features: ai.run() and ai.dynamic_tool().

    This flow shows how to:
    1. Use `ai.run()` to create sub-spans (steps) within a flow trace.
    2. Use `ai.dynamic_tool()` to create tools on-the-fly without registration.

    To test this in the Dev UI:
    1. Select 'demo_dynamic_tools' from the flows list.
    2. Run it with the default input or provide a custom string.
    3. Click 'View trace' to see the 'process_data_step' sub-span and tool execution.
    """

    # ai.run() allows you to wrap any function in a trace span, which is visible
    # in the Dev UI. It supports an optional input argument as the second parameter.
    def process_data(data: str) -> str:
        return f'processed: {data}'

    run_result = await ai.run('process_data_step', input_val, process_data)

    # ai.dynamic_tool() creates a tool that isn't globally registered but can be
    # used immediately or passed to generate() calls.
    def multiplier_fn(x: int) -> int:
        return x * 10

    dynamic_multiplier = ai.dynamic_tool('dynamic_multiplier', multiplier_fn, description='Multiplies by 10')
    tool_res = await dynamic_multiplier.arun(5)

    return {
        'step_result': run_result,
        'dynamic_tool_result': tool_res.response,
        'tool_metadata': dynamic_multiplier.metadata,
    }


@ai.flow()
async def describe_image(
    image_url: Annotated[
        str, Field(default='https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png')
    ] = 'https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png',
) -> str:
    """Describe an image."""
    response = await ai.generate(
        model='googleai/gemini-3-flash-preview',
        prompt=[
            Part(root=TextPart(text='Describe this image')),
            Part(root=MediaPart(media=Media(url=image_url, content_type='image/png'))),
        ],
        config={'api_version': 'v1alpha'},
    )
    return response.text


@ai.flow()
async def embed_docs(
    docs: list[str] | None = None,
) -> list[Embedding]:
    """Generate an embedding for the words in a list.

    Args:
        docs: list of texts (string)

    Returns:
        The generated embedding.
    """
    if docs is None:
        docs = ['Hello world', 'Genkit is great', 'Embeddings are fun']
    options = {'task_type': EmbeddingTaskType.CLUSTERING}
    return await ai.embed_many(
        embedder='googleai/text-embedding-004',
        content=docs,
        options=options,
    )


@ai.flow()
async def file_search() -> str:
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


@ai.tool(name='gablorkenTool')
def gablorken_tool(input_: GablorkenInput) -> dict[str, int]:
    """Calculate a gablorken.

    Returns:
        The calculated gablorken.
    """
    return {'result': input_.value * 3 - 5}


@ai.tool(name='gablorkenTool2')
def gablorken_tool2(input_: GablorkenInput, ctx: ToolRunContext) -> None:
    """The user-defined tool function.

    Args:
        input_: the input to the tool
        ctx: the tool run context

    Returns:
        The calculated gablorken.
    """
    ctx.interrupt()


@ai.flow()
async def generate_character(
    name: Annotated[str, Field(default='Bartholomew')] = 'Bartholomew',
    ctx: ActionRunContext = None,  # type: ignore[assignment]
) -> RpgCharacter:
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

        return cast(RpgCharacter, (await result).output)
    else:
        result = await ai.generate(
            prompt=f'generate an RPG character named {name}',
            output_schema=RpgCharacter,
        )
        return cast(RpgCharacter, result.output)


@ai.flow()
async def generate_character_unconstrained(
    name: Annotated[str, Field(default='Bartholomew')] = 'Bartholomew',
    ctx: ActionRunContext = None,  # type: ignore[assignment]
) -> RpgCharacter:
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
    return cast(RpgCharacter, result.output)


@ai.tool(name='getWeather')
def get_weather(input_: WeatherInput) -> dict:
    """Used to get current weather for a location."""
    return {
        'location': input_.location,
        'temperature_celcius': 21.5,
        'conditions': 'cloudy',
    }


@ai.flow()
async def say_hi(name: Annotated[str, Field(default='Alice')] = 'Alice') -> str:
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
async def say_hi_stream(
    name: Annotated[str, Field(default='Alice')] = 'Alice',
    ctx: ActionRunContext = None,  # type: ignore[assignment]
) -> str:
    """Generate a greeting for the given name.

    Args:
        name: the name to send to test function
        ctx: the context of the tool

    Returns:
        The generated response with a function.
    """
    stream, _ = ai.generate_stream(prompt=f'hi {name}')
    result: str = ''
    async for data in stream:
        ctx.send_chunk(data.text)
        result += data.text

    return result


@ai.flow()
async def say_hi_with_configured_temperature(
    data: Annotated[str, Field(default='Alice')] = 'Alice',
) -> GenerateResponseWrapper:
    """Generate a greeting for the given name.

    Args:
        data: the name to send to test function

    Returns:
        The generated response with a function.
    """
    return await ai.generate(
        messages=[Message(role=Role.USER, content=[Part(root=TextPart(text=f'hi {data}'))])],
        config=GenerationCommonConfig(temperature=0.1),
    )


@ai.flow()
async def search_grounding() -> str:
    """Search grounding."""
    response = await ai.generate(
        model='googleai/gemini-3-flash-preview',
        prompt='Who is Albert Einstein?',
        config={'tools': [{'googleSearch': {}}], 'api_version': 'v1alpha'},
    )
    return response.text


@ai.flow()
async def simple_generate_with_interrupts(value: Annotated[int, Field(default=42)] = 42) -> str:
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
                content=[Part(root=TextPart(text=f'what is a gablorken of {value}'))],
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
    return response.text


@ai.flow()
async def simple_generate_with_tools_flow(
    value: Annotated[int, Field(default=42)] = 42,
    ctx: ActionRunContext = None,  # type: ignore[assignment]
) -> str:
    """Generate a greeting for the given name.

    Args:
        value: the integer to send to test function
        ctx: the flow context

    Returns:
        The generated response with a function.
    """
    response = await ai.generate(
        prompt=f'what is a gablorken of {value}',
        tools=['gablorkenTool'],
        on_chunk=ctx.send_chunk,
    )
    return response.text


@ai.flow()
async def thinking_level_flash(level: ThinkingLevelFlash) -> str:
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
async def thinking_level_pro(level: ThinkingLevel) -> str:
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


@ai.flow()
async def tool_calling(location: Annotated[str, Field(default='Paris, France')] = 'Paris, France') -> str:
    """Tool calling with Gemini."""
    response = await ai.generate(
        model='googleai/gemini-2.5-flash',
        tools=['getWeather', 'celsiusToFahrenheit'],
        prompt=f"What's the weather in {location}? Convert the temperature to Fahrenheit.",
        config=GenerationCommonConfig(temperature=1),
    )
    return response.text


@ai.flow()
async def url_context() -> str:
    """Url context."""
    response = await ai.generate(
        model='googleai/gemini-3-flash-preview',
        prompt='Compare the ingredients and cooking times from the recipes at https://www.foodnetwork.com/recipes/ina-garten/'
        'perfect-roast-chicken-recipe-1940592 and https://www.allrecipes.com/recipe/70679/'
        'simple-whole-roasted-chicken/',
        config={'url_context': {}, 'api_version': 'v1alpha'},
    )
    return response.text


@ai.flow()
async def youtube_videos() -> str:
    """YouTube videos."""
    response = await ai.generate(
        model='googleai/gemini-3-flash-preview',
        prompt=[
            Part(root=TextPart(text='transcribe this video')),
            Part(
                root=MediaPart(media=Media(url='https://www.youtube.com/watch?v=3p1P5grjXIQ', content_type='video/mp4'))
            ),
        ],
        config={'api_version': 'v1alpha'},
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
