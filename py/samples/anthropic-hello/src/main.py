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

"""Anthropic hello sample - Claude models with Genkit.

This sample demonstrates how to use Anthropic's Claude models with Genkit,
including tools, streaming, thinking mode, and multimodal capabilities.

See README.md for testing instructions.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Claude              │ Anthropic's AI assistant. Like a helpful friend   │
    │                     │ who's great at explaining things and writing.     │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Haiku               │ Claude's fast model. Quick responses for simple   │
    │                     │ tasks. Great for chatbots and quick Q&A.          │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Sonnet              │ Claude's balanced model. Good at most tasks       │
    │                     │ without being too slow or expensive.              │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Tool Calling        │ Let Claude use functions you define. "Get the     │
    │                     │ weather" → Claude calls your weather function.    │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Thinking Mode       │ Claude shows its reasoning step by step.          │
    │                     │ Like showing your work on a math test.            │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Streaming           │ Get Claude's response word-by-word.               │
    │                     │ Feels faster, like watching someone type.         │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Multimodal          │ Claude can see images! Send a photo and ask       │
    │                     │ "What's in this picture?"                         │
    └─────────────────────┴────────────────────────────────────────────────────┘

Key Features
============
| Feature Description                     | Example Function / Code Snippet     |
|-----------------------------------------|-------------------------------------|
| Plugin Initialization                   | `ai = Genkit(plugins=[Anthropic()])` |
| Default Model Configuration             | `ai = Genkit(model=...)`            |
| Defining Flows                          | `@ai.flow()` decorator              |
| Defining Tools                          | `@ai.tool()` decorator              |
| Pydantic for Tool Input Schema          | `WeatherInput`, `CurrencyInput`     |
| Simple Generation (Prompt String)       | `say_hi`                            |
| Streaming Generation                    | `say_hi_stream`                     |
| Generation with Tools                   | `weather_flow`, `currency_exchange` |
| Generation Configuration (temperature)  | `say_hi_with_config`                |
| Thinking (CoT)                          | `reasoning_flow`                    |
| Code Generation                         | `code_flow`                         |
| Multimodal (Image Input)                | `describe_image`                    |
| Prompt Caching                          | `cached_generation`                 |
| PDF Document Input                      | `analyze_pdf`                       |
"""

import asyncio
import os
import random

from pydantic import BaseModel, Field
from rich.traceback import install as install_rich_traceback

from genkit.ai import Genkit, Output
from genkit.core.action import ActionRunContext
from genkit.core.logging import get_logger
from genkit.plugins.anthropic import Anthropic, anthropic_name
from genkit.types import GenerationCommonConfig, Media, MediaPart, Message, Metadata, Part, Role, TextPart

install_rich_traceback(show_locals=True, width=120, extra_lines=3)

if 'ANTHROPIC_API_KEY' not in os.environ:
    os.environ['ANTHROPIC_API_KEY'] = input('Please enter your ANTHROPIC_API_KEY: ')

logger = get_logger(__name__)

ai = Genkit(
    plugins=[Anthropic()],
    model=anthropic_name('claude-3-5-haiku'),
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


class Skills(BaseModel):
    """A set of core character skills for an RPG character."""

    strength: int = Field(description='strength (0-100)')
    charisma: int = Field(description='charisma (0-100)')
    endurance: int = Field(description='endurance (0-100)')


class RpgCharacter(BaseModel):
    """An RPG character."""

    name: str = Field(description='name of the character')
    back_story: str = Field(description='back story', alias='backStory')
    abilities: list[str] = Field(description='list of abilities (3-4)')
    skills: Skills


class WeatherInput(BaseModel):
    """Weather input schema."""

    location: str = Field(description='Location to get weather for')


class SayHiInput(BaseModel):
    """Input for say_hi flow."""

    name: str = Field(default='Mittens', description='Name to greet')


class StreamInput(BaseModel):
    """Input for streaming flow."""

    topic: str = Field(default='cats and their behaviors', description='Topic to write about')


class CharacterInput(BaseModel):
    """Input for character generation."""

    name: str = Field(default='Whiskers', description='Character name')


class ImageDescribeInput(BaseModel):
    """Input for image description."""

    image_url: str = Field(
        # Public domain cat image from Wikimedia Commons (no copyright, free for any use)
        # Source: https://commons.wikimedia.org/wiki/File:Cute_kitten.jpg
        default='https://upload.wikimedia.org/wikipedia/commons/1/13/Cute_kitten.jpg',
        description='URL of the image to describe (replace with your own image URL)',
    )


class ThinkingInput(BaseModel):
    """Input for thinking demo."""

    question: str = Field(default='Why do cats purr?', description='Question to answer')


class WeatherFlowInput(BaseModel):
    """Input for weather flow."""

    location: str = Field(default='San Francisco', description='Location to get weather for')


class CodeInput(BaseModel):
    """Input for code generation flow."""

    task: str = Field(
        default='Write a Python function to calculate fibonacci numbers',
        description='Coding task description',
    )


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
async def describe_image(input: ImageDescribeInput) -> str:
    """Describe an image using Anthropic."""
    response = await ai.generate(
        prompt=[
            Part(root=TextPart(text='Describe this image')),
            Part(root=MediaPart(media=Media(url=input.image_url, content_type='image/jpeg'))),
        ],
    )
    return response.text


@ai.flow()
async def generate_character(input: CharacterInput) -> RpgCharacter:
    """Generate an RPG character.

    Args:
        input: Character generation input with name.

    Returns:
        The generated RPG character.
    """
    result = await ai.generate(
        prompt=f'generate an RPG character named {input.name}',
        output=Output(schema=RpgCharacter),
    )
    return result.output


@ai.tool()
def get_weather(input: WeatherInput) -> str:
    """Return a random realistic weather string for a city name.

    Args:
        input: Weather input  location.

    Returns:
        Weather information with temperature in degree Celsius.
    """
    weather_options = [
        '32° C sunny',
        '17° C cloudy',
        '22° C cloudy',
        '19° C humid',
    ]
    return random.choice(weather_options)


@ai.flow()
async def say_hi(input: SayHiInput) -> str:
    """Generate a simple greeting.

    Args:
        input: Input with name to greet.

    Returns:
        Greeting message.
    """
    response = await ai.generate(
        prompt=f'Say hello to {input.name} in a friendly way',
    )
    return response.text


@ai.flow()
async def say_hi_stream(
    input: StreamInput,
    ctx: ActionRunContext = None,  # type: ignore[assignment]
) -> str:
    """Generate streaming response.

    Args:
        input: Input with topic to write about.
        ctx: Action run context for streaming.

    Returns:
        Complete generated text.
    """
    response = await ai.generate(
        prompt=f'Write a short story about {input.topic}',
        on_chunk=ctx.send_chunk,
    )
    return response.text


@ai.flow()
async def say_hi_with_config(input: SayHiInput) -> str:
    """Generate greeting with custom configuration.

    Args:
        input: Input with name to greet.

    Returns:
        Greeting message.
    """
    response = await ai.generate(
        prompt=f'Say hello to {input.name}',
        config=GenerationCommonConfig(
            temperature=0.7,
            max_output_tokens=100,
        ),
    )
    return response.text


@ai.flow()
async def reasoning_flow(input: ThinkingInput) -> str:
    """Demonstrate Anthropic thinking capability.

    Note: 'thinking' requires a compatible model (e.g., Claude 3.7 Sonnet).
    """
    response = await ai.generate(
        model=anthropic_name('claude-3-7-sonnet-20250219'),
        prompt=input.question,
        config={
            'thinking': {'type': 'enabled', 'budget_tokens': 1024},
            'max_output_tokens': 4096,  # Required when thinking is enabled
        },
    )
    return response.text


@ai.flow()
async def code_flow(input: CodeInput) -> str:
    """Generate code using Claude.

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
async def weather_flow(input: WeatherFlowInput) -> str:
    """Get weather using tools.

    Args:
        input: Input with location to get weather for.

    Returns:
        Weather information.
    """
    response = await ai.generate(
        prompt=f'What is the weather in {input.location}?',
        tools=['get_weather'],
    )
    return response.text


class CacheInput(BaseModel):
    """Input for prompt caching demo."""

    question: str = Field(default='What are the key themes?', description='Question about the cached text')


class PdfInput(BaseModel):
    """Input for PDF analysis demo."""

    pdf_url: str = Field(
        # Public domain sample PDF.
        default='https://pdfobject.com/pdf/sample.pdf',
        description='URL of the PDF to analyze',
    )
    question: str = Field(default='Describe the contents of this document.', description='Question about the PDF')


@ai.flow()
async def cached_generation(input: CacheInput) -> str:
    """Demonstrate Anthropic prompt caching.

    Prompt caching lets Anthropic cache large context blocks across requests,
    reducing latency and cost for repeated prompts with shared prefixes.

    Set ``cache_control`` metadata on any content part to mark it as a
    cache breakpoint. Anthropic will cache everything up to and including
    that part.

    See: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching

    Args:
        input: Input with question about the cached context.

    Returns:
        Model response leveraging cached context.
    """
    # The long context is marked with cache_control metadata.
    # On subsequent calls with the same prefix, Anthropic reuses the cache.
    long_context = (
        'The Genkit framework provides a unified interface for working with '
        'generative AI models across multiple providers. It supports flows, '
        'tools, structured output, streaming, and advanced features like '
        'prompt caching and document input. ' * 10
    )
    response = await ai.generate(
        model=anthropic_name('claude-3-5-haiku'),
        messages=[
            Message(
                role=Role.USER,
                content=[
                    Part(
                        root=TextPart(
                            text=long_context,
                            metadata=Metadata({'cache_control': {'type': 'ephemeral'}}),
                        )
                    ),
                    Part(root=TextPart(text=input.question)),
                ],
            ),
        ],
    )
    return response.text


@ai.flow()
async def analyze_pdf(input: PdfInput) -> str:
    """Analyze a PDF document using Anthropic's document input.

    Anthropic supports sending PDF files directly to Claude for analysis.
    PDFs can be provided as URLs or base64-encoded data URIs.

    See: https://docs.anthropic.com/en/docs/build-with-claude/pdf-support

    Args:
        input: Input with PDF URL and question.

    Returns:
        Model's analysis of the PDF document.
    """
    response = await ai.generate(
        model=anthropic_name('claude-3-5-haiku'),
        prompt=[
            Part(root=TextPart(text=input.question)),
            Part(root=MediaPart(media=Media(url=input.pdf_url, content_type='application/pdf'))),
        ],
    )
    return response.text


async def main() -> None:
    """Main entry point for the Anthropic sample - keep alive for Dev UI."""
    await logger.ainfo('Genkit server running. Press Ctrl+C to stop.')
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
