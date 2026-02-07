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

"""xAI Genkit sample - Grok models with Genkit.

This sample demonstrates how to use xAI's Grok models with Genkit,
including basic generation, streaming, and tool calling.

See README.md for testing instructions.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ xAI                 │ Elon Musk's AI company. Makes the Grok models.     │
    │                     │                                                    │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Grok                │ xAI's AI assistant. Known for being witty and      │
    │                     │ having access to real-time X/Twitter data.         │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Grok-3              │ The main Grok model. Good balance of speed         │
    │                     │ and capability for most tasks.                     │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Tool Calling        │ Let Grok use functions you define. Like giving     │
    │                     │ it a calculator or weather lookup to use.          │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Streaming           │ Get the response word-by-word as it's generated.   │
    │                     │ Feels faster, like watching someone type.          │
    └─────────────────────┴────────────────────────────────────────────────────┘

Key Features
============
| Feature Description                     | Example Function / Code Snippet     |
|-----------------------------------------|-------------------------------------|
| Plugin Initialization                   | `ai = Genkit(plugins=[XAI()])`      |
| Model Configuration                     | `xai_name('grok-3')`                |
| Simple Text Generation                  | `say_hi`                            |
| Streaming Generation                    | `say_hi_stream`                     |
| Tool Usage (Decorated)                  | `get_weather`, `calculate`          |
| Generation Configuration                | `say_hi_with_config`                |
| Code Generation                         | `code_flow`                         |
| Tool Calling                            | `weather_flow`                      |
| Vision (Image Input)                    | `describe_image`                    |
| Web Search                              | `web_search_flow`                   |
| Reasoning Effort (Grok 4)              | `reasoning_flow`                    |
"""

import asyncio
import os

from pydantic import BaseModel, Field
from rich.traceback import install as install_rich_traceback

from genkit.ai import Genkit
from genkit.core.action import ActionRunContext
from genkit.core.logging import get_logger
from genkit.plugins.google_cloud import add_gcp_telemetry
from genkit.plugins.xai import XAI, xai_name
from genkit.types import Media, MediaPart, Part, TextPart
from samples.shared import (
    CalculatorInput,
    CurrencyExchangeInput,
    RpgCharacter,
    WeatherInput,
    calculate,
    calculation_logic,
    convert_currency,
    currency_exchange_logic,
    generate_character_logic,
    get_weather,
    say_hi_logic,
    say_hi_stream_logic,
    say_hi_with_config_logic,
    weather_logic,
)

install_rich_traceback(show_locals=True, width=120, extra_lines=3)

if 'XAI_API_KEY' not in os.environ:
    os.environ['XAI_API_KEY'] = input('Please enter your XAI_API_KEY: ')

logger = get_logger(__name__)

# Enable GCP telemetry
add_gcp_telemetry(
    project_id=os.environ.get('GCP_PROJECT_ID'),
    log_input_and_output=False,
)

ai = Genkit(
    plugins=[XAI()],
    model=xai_name('grok-3'),
)


class SayHiInput(BaseModel):
    """Input for say_hi flow."""

    name: str = Field(default='Mittens', description='Name to greet')


class StreamInput(BaseModel):
    """Input for streaming flow."""

    name: str = Field(default='Shadow', description='Name for streaming story')


class CharacterInput(BaseModel):
    """Input for character generation."""

    name: str = Field(default='Whiskers', description='Character name')


class ConfigInput(BaseModel):
    """Input for config flow."""

    name: str = Field(default='Ginger', description='User name for greeting')


class CodeInput(BaseModel):
    """Input for code generation flow."""

    task: str = Field(
        default='Write a Python function to calculate fibonacci numbers',
        description='Coding task description',
    )


class ImageDescribeInput(BaseModel):
    """Input for image description flow."""

    # Public domain cat image from Wikimedia Commons
    image_url: str = Field(
        default='https://upload.wikimedia.org/wikipedia/commons/1/13/Cute_kitten.jpg',
        description='URL of the image to describe',
    )


class WebSearchInput(BaseModel):
    """Input for web search flow."""

    query: str = Field(
        default='What are the latest developments in AI?',
        description='Query to search the web for',
    )


class ReasoningInput(BaseModel):
    """Input for reasoning flow."""

    problem: str = Field(
        default='A farmer has 17 sheep. All but 9 run away. How many does the farmer have left?',
        description='Problem requiring careful reasoning',
    )


# Decorated tools
ai.tool()(get_weather)
ai.tool()(convert_currency)
ai.tool()(calculate)


@ai.flow()
async def currency_exchange_flow(input_data: CurrencyExchangeInput) -> str:
    """Genkit entry point for the currency exchange flow.

    Exposes conversion logic as a traceable Genkit flow.
    """
    return await currency_exchange_logic(ai, input_data)


@ai.flow()
async def calculator_flow(input_data: CalculatorInput) -> str:
    """Genkit entry point for the calculator flow.

    Exposes calculation logic as a traceable Genkit flow.
    """
    return await calculation_logic(ai, input_data)


@ai.flow()
async def generate_character(input: CharacterInput) -> RpgCharacter:
    """Generate an RPG character.

    Args:
        input: Input with character name.

    Returns:
        The generated RPG character.
    """
    return await generate_character_logic(ai, input.name)


@ai.flow()
async def say_hi(input: SayHiInput) -> str:
    """Generate a simple greeting.

    Args:
        input: Input with name to greet.

    Returns:
        Greeting message.

    Example:
        >>> await say_hi(SayHiInput(name='Alice'))
        "Hello Alice!"
    """
    return await say_hi_logic(ai, input.name)


@ai.flow()
async def say_hi_stream(
    input: StreamInput,
    ctx: ActionRunContext | None = None,
) -> str:
    """Generate a streaming story response.

    Args:
        input: Input with name for story.
        ctx: Action context for streaming.

    Returns:
        Complete story text.

    Example:
        >>> await say_hi_stream(StreamInput(name='Bob'), ctx)
        "Once upon a time..."
    """
    return await say_hi_stream_logic(ai, input.name, ctx)


@ai.flow()
async def say_hi_with_config(input: ConfigInput) -> str:
    """Generate a greeting with custom model configuration.

    Args:
        input: Input with user name.

    Returns:
        Greeting message.
    """
    return await say_hi_with_config_logic(ai, input.name)


@ai.flow()
async def weather_flow(input_data: WeatherInput) -> str:
    """Genkit entry point for the weather information flow.

    Exposes weather logic as a traceable Genkit flow.
    """
    return await weather_logic(ai, input_data)


@ai.flow()
async def code_flow(input: CodeInput) -> str:
    """Generate code using Grok.

    Args:
        input: Input with coding task description.

    Returns:
        Generated code.
    """
    response = await ai.generate(
        prompt=input.task,
        system='You are an expert programmer. Provide clean, well-documented code with explanations.',
    )
    return response.text


@ai.flow()
async def describe_image(input: ImageDescribeInput) -> str:
    """Describe an image using Grok's vision capabilities.

    Uses grok-2-vision-1212 to analyze images. Demonstrates multimodal
    input by sending both text and image content to the model.

    Args:
        input: Input with image URL.

    Returns:
        Description of the image.
    """
    response = await ai.generate(
        model=xai_name('grok-2-vision-1212'),
        prompt=[
            Part(root=TextPart(text='Describe this image in detail.')),
            Part(root=MediaPart(media=Media(url=input.image_url, content_type='image/jpeg'))),
        ],
    )
    return response.text


@ai.flow()
async def web_search_flow(input: WebSearchInput) -> str:
    """Search the web using Grok's built-in web search.

    Demonstrates the web_search_options config parameter, which enables
    Grok to access real-time web information when answering queries.
    This is a server-side feature — xAI handles the search autonomously.

    Args:
        input: Input with search query.

    Returns:
        Response informed by web search results.
    """
    response = await ai.generate(
        prompt=input.query,
        config={
            'web_search_options': {},
        },
    )
    return response.text


@ai.flow()
async def reasoning_flow(input: ReasoningInput) -> str:
    """Solve a problem using Grok 4's reasoning capabilities.

    Demonstrates the reasoning_effort config parameter with Grok 4,
    xAI's most capable reasoning model. The model thinks harder
    about complex problems, similar to OpenAI's o-series models.

    Args:
        input: Input with problem to solve.

    Returns:
        Reasoned solution to the problem.
    """
    response = await ai.generate(
        model=xai_name('grok-4'),
        prompt=input.problem,
        system='Think step by step. Show your reasoning clearly.',
    )
    return response.text


async def main() -> None:
    """Main entry point - keep alive for Dev UI."""
    logger.info('Genkit server running. Press Ctrl+C to stop.')
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
