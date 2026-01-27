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

"""Model Garden sample - Access third-party models via Vertex AI.

This sample demonstrates how to use Vertex AI Model Garden, which provides
access to various third-party models (like Anthropic Claude) through
Google Cloud's infrastructure.

Key Features
============
| Feature Description                     | Example Function / Code Snippet     |
|-----------------------------------------|-------------------------------------|
| Model Garden Plugin                     | `ModelGardenPlugin()`               |
| Specific Model Usage                    | `model_garden_name('anthropic/...')`|
| Generation Config                       | `max_output_tokens`, `temperature`  |

See README.md for testing instructions.
"""

from typing import Annotated, cast

import structlog
from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.core.action import ActionRunContext
from genkit.plugins.vertex_ai.model_garden import ModelGardenPlugin, model_garden_name

logger = structlog.get_logger(__name__)

ai = Genkit(
    plugins=[
        ModelGardenPlugin(),
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
    """Input for getting weather."""

    location: str = Field(description='The city and state, e.g. San Francisco, CA')


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
        model=model_garden_name('anthropic/claude-3-5-sonnet-v2@20241022'),
        prompt=f'Convert {input.amount} {input.from_curr} to {input.to_curr}',
        tools=['convert_currency'],
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
        model=model_garden_name('anthropic/claude-3-5-sonnet-v2@20241022'),
        prompt=f'generate an RPG character named {name}',
        output_schema=RpgCharacter,
    )
    return cast(RpgCharacter, result.output)


@ai.tool(name='getWeather')
def get_weather(input_: WeatherInput) -> str:
    """Used to get current weather for a location."""
    return f'Weather in {input_.location}: Sunny, 21.5°C'


@ai.flow()
async def jokes_flow(subject: Annotated[str, Field(default='banana')] = 'banana') -> str:
    """Generate a joke about the given subject.

    Args:
        subject: The subject of the joke.

    Returns:
        The generated joke.
    """
    response = await ai.generate(
        # Note: The model name usually includes the publisher prefix for Model Garden
        model=model_garden_name('anthropic/claude-3-5-sonnet-v2@20241022'),
        config={'temperature': 1, 'max_output_tokens': 1024},
        prompt=f'Tell a short joke about {subject}',
    )

    return response.text


@ai.flow()
async def say_hi(name: Annotated[str, Field(default='Alice')] = 'Alice') -> str:
    """Generate a greeting for the given name.

    Args:
        name: The name of the person to greet.

    Returns:
        The generated greeting response.
    """
    response = await ai.generate(
        # model=model_garden_name('meta/llama-3.2-90b-vision-instruct-maas'),
        # Using Anthropic for Model Garden example as it is reliably available
        model=model_garden_name('anthropic/claude-3-5-sonnet-v2@20241022'),
        config={'temperature': 1},
        prompt=f'hi {name}',
    )

    return response.text


@ai.flow()
async def say_hi_stream(
    name: Annotated[str, Field(default='Alice')] = 'Alice',
    ctx: ActionRunContext = None,  # type: ignore[assignment]
) -> str:
    """Say hi to a name and stream the response.

    Args:
        name: The name to say hi to.
        ctx: Action context for streaming.

    Returns:
        The response from the model.
    """
    stream, _ = ai.generate_stream(
        model=model_garden_name('anthropic/claude-3-5-sonnet-v2@20241022'),
        config={'temperature': 1},
        prompt=f'hi {name}',
    )
    result = ''
    async for data in stream:
        ctx.send_chunk(data.text)
        result += data.text
    return result


@ai.flow()
async def weather_flow(location: Annotated[str, Field(default='Paris, France')] = 'Paris, France') -> str:
    """Tool calling with Model Garden."""
    response = await ai.generate(
        model=model_garden_name('anthropic/claude-3-5-sonnet-v2@20241022'),
        tools=['getWeather'],
        prompt=f"What's the weather in {location}?",
        config={'temperature': 1},
    )
    return response.text


async def main() -> None:
    """Main entry point for the Model Garden sample - keep alive for Dev UI."""
    import asyncio

    # For testing/demo purposes, you can uncomment these to run them on startup:
    # await logger.ainfo(await say_hi('Alice'))
    # await logger.ainfo(await jokes_flow('banana'))

    await logger.ainfo('Genkit server running. Press Ctrl+C to stop.')
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
