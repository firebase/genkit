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

"""OpenAI hello sample - GPT models with Genkit.

This sample demonstrates how to use OpenAI's GPT models with Genkit
using the OpenAI-compatible plugin.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ OpenAI              │ The company that made ChatGPT. This sample         │
    │                     │ talks to their API directly.                       │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ GPT-4o              │ OpenAI's multimodal model. Can see images,         │
    │                     │ hear audio, and chat - all in one model.           │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ OpenAI-compatible   │ Many AI providers copy OpenAI's API format.        │
    │                     │ This plugin works with ALL of them!                │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Tool Calling        │ Let GPT use functions you define. Like giving      │
    │                     │ it a calculator or search engine to use.           │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Streaming           │ Get the response word-by-word as it's generated.   │
    │                     │ Feels faster, like watching someone type.          │
    └─────────────────────┴────────────────────────────────────────────────────┘

Key Features
============
| Feature Description                                      | Example Function / Code Snippet        |
|----------------------------------------------------------|----------------------------------------|
| Plugin Initialization                                    | `ai = Genkit(plugins=[OpenAI()])`      |
| Default Model Configuration                              | `ai = Genkit(model=...)`               |
| Defining Flows                                           | `@ai.flow()` decorator (multiple uses) |
| Defining Tools                                           | `@ai.tool()` decorator (multiple uses) |
| Tool Input Schema (Pydantic)                             | `GablorkenInput`                       |
| Simple Generation (Prompt String)                        | `say_hi`                               |
| Generation with Messages (`Message`, `Role`, `TextPart`) | `say_hi_constrained`                   |
| Streaming Generation                                     | `say_hi_stream`                        |
| Generation with Tools                                    | `calculate_gablorken`                  |
| Tool Response Handling with context                      | `generate_character`                   |

See README.md for testing instructions.
"""

import asyncio
import os
from decimal import Decimal

import httpx
from pydantic import BaseModel, Field
from rich.traceback import install as install_rich_traceback

from genkit.ai import ActionRunContext, Genkit, Output
from genkit.core.logging import get_logger
from genkit.plugins.compat_oai import OpenAI, openai_model

install_rich_traceback(show_locals=True, width=120, extra_lines=3)

if 'OPENAI_API_KEY' not in os.environ:
    os.environ['OPENAI_API_KEY'] = input('Please enter your OPENAI_API_KEY: ')

logger = get_logger(__name__)

ai = Genkit(plugins=[OpenAI()], model=openai_model('gpt-4o'))


class CurrencyExchangeInput(BaseModel):
    """Currency exchange flow input schema."""

    amount: float = Field(description='Amount to convert', default=100)
    from_curr: str = Field(description='Source currency code', default='USD')
    to_curr: str = Field(description='Target currency code', default='EUR')


class CurrencyInput(BaseModel):
    """Currency conversion input schema."""

    amount: float = Field(description='Amount to convert')
    from_currency: str = Field(description='Source currency code (e.g., USD)')
    to_currency: str = Field(description='Target currency code (e.g., EUR)')


class GablorkenInput(BaseModel):
    """The Pydantic model for tools."""

    value: int = Field(description='value to calculate gablorken for')


class HelloSchema(BaseModel):
    """Hello schema.

    Args:
        text: The text to say hello to.
        receiver: The receiver of the hello.
    """

    text: str
    receiver: str


class MyInput(BaseModel):
    """My input."""

    a: int = Field(default=5, description='a field')
    b: int = Field(default=3, description='b field')


class Skills(BaseModel):
    """A set of core character skills for an RPG character."""

    strength: int = Field(description='strength (0-100)')
    charisma: int = Field(description='charisma (0-100)')
    endurance: int = Field(description='endurance (0-100)')
    gablorket: int = Field(description='gablorken (0-100)')


class RpgCharacter(BaseModel):
    """An RPG character."""

    name: str = Field(description='name of the character')
    back_story: str = Field(description='back story', alias='backStory')
    abilities: list[str] = Field(description='list of abilities (3-4)')
    skills: Skills


class WeatherRequest(BaseModel):
    """Weather request."""

    latitude: Decimal
    longitude: Decimal


class Temperature(BaseModel):
    """Temperature by location."""

    location: str
    temperature: Decimal
    gablorken: Decimal


class WeatherResponse(BaseModel):
    """Weather response."""

    answer: list[Temperature]


class GablorkenFlowInput(BaseModel):
    """Input for gablorken calculation flow."""

    value: int = Field(default=42, description='Value to calculate gablorken for')


class SayHiInput(BaseModel):
    """Input for say_hi flow."""

    name: str = Field(default='Mittens', description='Name to greet')


class SayHiConstrainedInput(BaseModel):
    """Input for constrained greeting flow."""

    hi_input: str = Field(default='Mittens', description='Name to greet')


class StreamInput(BaseModel):
    """Input for streaming flow."""

    name: str = Field(default='Shadow', description='Name for streaming greeting')


class CharacterInput(BaseModel):
    """Input for character generation."""

    name: str = Field(default='Whiskers', description='Character name')


class WeatherFlowInput(BaseModel):
    """Input for weather flow."""

    location: str = Field(default='New York', description='Location to get weather for')


@ai.tool(description='calculates a gablorken', name='gablorkenTool')
def gablorken_tool(input_: GablorkenInput) -> int:
    """Calculate a gablorken.

    Args:
        input_: The input to calculate gablorken for.

    Returns:
        The calculated gablorken.
    """
    return input_.value * 3 - 5


@ai.tool(description='Get current temperature for provided coordinates in celsius')
def get_weather_tool(coordinates: WeatherRequest) -> float:
    """Get the current temperature for provided coordinates in celsius.

    Args:
        coordinates: The coordinates to get the weather for.

    Returns:
        The current temperature for the provided coordinates.
    """
    url = (
        f'https://api.open-meteo.com/v1/forecast?'
        f'latitude={coordinates.latitude}&longitude={coordinates.longitude}'
        f'&current=temperature_2m'
    )
    with httpx.Client() as client:
        response = client.get(url)
        data = response.json()
        return float(data['current']['temperature_2m'])


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
async def calculate_gablorken(input: GablorkenFlowInput) -> str:
    """Generate a request to calculate gablorken according to gablorken_tool.

    Args:
        input: Input with value for gablorken calculation.

    Returns:
        A GenerateRequest object with the evaluation output
    """
    response = await ai.generate(
        prompt=f'what is the gablorken of {input.value}',
        model=openai_model('gpt-4'),
        tools=['gablorkenTool'],
    )

    return response.text


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
async def generate_character(
    input: CharacterInput,
    ctx: ActionRunContext | None = None,
) -> RpgCharacter:
    """Generate an RPG character.

    Args:
        input: Input with character name.
        ctx: the context of the tool

    Returns:
        The generated RPG character.
    """
    if ctx is not None and ctx.is_streaming:
        stream, result = ai.generate_stream(
            prompt=f'generate an RPG character named {input.name} with gablorken based on 42',
            output=Output(schema=RpgCharacter),
            config={'model': 'gpt-4o-2024-08-06', 'temperature': 1},
            tools=['gablorkenTool'],
        )
        async for data in stream:
            ctx.send_chunk(data.output)

        return (await result).output
    else:
        result = await ai.generate(
            prompt=f'generate an RPG character named {input.name} with gablorken based on 13',
            output=Output(schema=RpgCharacter),
            config={'model': 'gpt-4o-2024-08-06', 'temperature': 1},
            tools=['gablorkenTool'],
        )
        return result.output


@ai.flow()
async def get_weather_flow(input: WeatherFlowInput) -> str:
    """Get the weather for a location.

    Args:
        input: Input with location to get weather for.

    Returns:
        The weather for the location.
    """
    response = await ai.generate(
        model=openai_model('gpt-4o-mini'),
        system='You are an assistant that provides current weather information in JSON format.',
        config={'model': 'gpt-4o-mini-2024-07-18', 'temperature': 1},
        prompt=f"What's the weather like in {input.location} today?",
        tools=['get_weather_tool'],
        output=Output(schema=WeatherResponse),
    )
    return response.text


@ai.flow()
async def get_weather_flow_stream(input: WeatherFlowInput) -> str:
    """Get the weather for a location using a stream.

    Args:
        input: Input with location to get weather for.

    Returns:
        The weather for the location as a string.
    """
    stream, _ = ai.generate_stream(
        model=openai_model('gpt-4o'),
        system=(
            'You are an assistant that provides current weather information in JSON format and calculates '
            'gablorken based on weather value'
        ),
        config={'model': 'gpt-4o-2024-08-06', 'temperature': 1},
        prompt=f"What's the weather like in {input.location} today?",
        tools=['get_weather_tool', 'gablorkenTool'],
        output=Output(schema=WeatherResponse),
    )
    result: str = ''
    async for data in stream:
        result += data.text
    return result


@ai.flow()
async def say_hi(input: SayHiInput) -> str:
    """Say hi to a name.

    Args:
        input: Input with name to greet.

    Returns:
        The response from the OpenAI API.
    """
    response = await ai.generate(
        model=openai_model('gpt-4o'),
        config={'temperature': 1},
        prompt=f'hi {input.name}',
    )
    return response.text


@ai.flow()
async def say_hi_constrained(input: SayHiConstrainedInput) -> HelloSchema:
    """Generate a request to greet a user with response following `HelloSchema` schema.

    Args:
        input: Input with name to greet.

    Returns:
        A `HelloSchema` object with the greeting message.
    """
    response = await ai.generate(
        prompt='hi ' + input.hi_input,
        output=Output(schema=HelloSchema),
    )
    return response.output


@ai.flow()
async def say_hi_stream(input: StreamInput) -> str:
    """Say hi to a name and stream the response.

    Args:
        input: Input with name for streaming greeting.

    Returns:
        The response from the OpenAI API.
    """
    stream, _ = ai.generate_stream(
        model=openai_model('gpt-4'),
        config={'model': 'gpt-4-0613', 'temperature': 1},
        prompt=f'hi {input.name}',
    )
    result: str = ''
    async for data in stream:
        result += data.text
    return result


@ai.flow()
async def sum_two_numbers2(my_input: MyInput) -> int:
    """Sum two numbers.

    Args:
        my_input: The input to sum.

    Returns:
        The sum of the input.
    """
    return my_input.a + my_input.b


async def main() -> None:
    """Main entry point for the OpenAI sample - keep alive for Dev UI."""
    await logger.ainfo('Genkit server running. Press Ctrl+C to stop.')
    # Keep the process alive for Dev UI
    _ = await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
