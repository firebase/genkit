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

"""Anthropic hello sample.

Key features demonstrated in this sample:

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
| Thinking (CoT)                          | `thinking_demo`                     |
| Multimodal (Image Input)                | `describe_image`                    |
"""

import os
from typing import Annotated, cast

import structlog
from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.plugins.anthropic import Anthropic, anthropic_name
from genkit.types import ActionRunContext, GenerationCommonConfig

if 'ANTHROPIC_API_KEY' not in os.environ:
    os.environ['ANTHROPIC_API_KEY'] = input('Please enter your ANTHROPIC_API_KEY: ')

logger = structlog.get_logger(__name__)

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
async def describe_image(
    image_url: Annotated[
        str,
        Field(default='https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png'),
    ] = 'https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png',
) -> str:
    """Describe an image using Anthropic."""
    from genkit.types import Media, MediaPart, Part, TextPart

    response = await ai.generate(
        prompt=[
            Part(root=TextPart(text='Describe this image')),
            Part(root=MediaPart(media=Media(url=image_url, content_type='image/png'))),
        ],
    )
    return response.text


@ai.flow()
async def generate_character(
    name: Annotated[str, Field(default='Bartholomew')] = 'Bartholomew',
) -> RpgCharacter:
    """Generate an RPG character.

    Args:
        name: the name of the character

    Returns:
        The generated RPG character.
    """
    result = await ai.generate(
        prompt=f'generate an RPG character named {name}',
        output_schema=RpgCharacter,
    )
    return cast(RpgCharacter, result.output)


@ai.tool()
def get_weather(input: WeatherInput) -> str:
    """Get weather for a location.

    Args:
        input: Weather input with location.

    Returns:
        Weather information.
    """
    return f'Weather in {input.location}: Sunny, 23°C'


@ai.flow()
async def say_hi(name: Annotated[str, Field(default='Alice')] = 'Alice') -> str:
    """Generate a simple greeting.

    Args:
        name: Name to greet.

    Returns:
        Greeting message.
    """
    response = await ai.generate(
        prompt=f'Say hello to {name} in a friendly way',
    )
    return response.text


@ai.flow()
async def say_hi_stream(
    topic: Annotated[str, Field(default='space exploration')] = 'space exploration',
    ctx: ActionRunContext = None,  # type: ignore[assignment]
) -> str:
    """Generate streaming response.

    Args:
        topic: Topic to write about.
        ctx: Action run context for streaming.

    Returns:
        Complete generated text.
    """
    response = await ai.generate(
        prompt=f'Write a short story about {topic}',
        on_chunk=ctx.send_chunk,
    )
    return response.text


@ai.flow()
async def say_hi_with_config(name: Annotated[str, Field(default='Alice')] = 'Alice') -> str:
    """Generate greeting with custom configuration.

    Args:
        name: Name to greet.

    Returns:
        Greeting message.
    """
    response = await ai.generate(
        prompt=f'Say hello to {name}',
        config=GenerationCommonConfig(
            temperature=0.7,
            max_output_tokens=100,
        ),
    )
    return response.text


@ai.flow()
async def thinking_demo(
    question: Annotated[str, Field(default='Explain quantum entanglement')] = 'Explain quantum entanglement',
) -> str:
    """Demonstrate Anthropic thinking capability.

    Note: 'thinking' requires a compatible model (e.g., Claude 3.7 Sonnet).
    """
    response = await ai.generate(
        model=anthropic_name('claude-3-7-sonnet-20250219'),
        prompt=question,
        config={
            'thinking': {'type': 'enabled', 'budget_tokens': 1024},
            'max_output_tokens': 4096,  # Required when thinking is enabled
        },
    )
    return response.text


@ai.flow()
async def weather_flow(location: Annotated[str, Field(default='San Francisco')] = 'San Francisco') -> str:
    """Get weather using tools.

    Args:
        location: Location to get weather for.

    Returns:
        Weather information.
    """
    response = await ai.generate(
        prompt=f'What is the weather in {location}?',
        tools=['get_weather'],
    )
    return response.text


async def main() -> None:
    """Main entry point for the Anthropic sample - keep alive for Dev UI."""
    import asyncio

    await logger.ainfo('Genkit server running. Press Ctrl+C to stop.')
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
