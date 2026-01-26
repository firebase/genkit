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

"""OpenAI hello sample.

Key features demonstrated in this sample:

| Feature Description                                      | Example Function / Code Snippet        |
|----------------------------------------------------------|----------------------------------------|
| Plugin Initialization                                    | `ai = Genkit(plugins=[OpenAI()])`      |
| Default Model Configuration                              | `ai = Genkit(model=...)`               |
| Defining Flows                                           | `@ai.flow()` decorator (multiple uses) |
| Defining Tools                                           | `@ai.tool()` decorator (multiple uses) |
| Pydantic for Tool Input Schema                           | `GablorkenOutputSchema`                |
| Simple arithmetic addition(Input integers a,b)           | `sum_two_numbers2`                     |
| Simple Generation (Prompt String)                        | `say_hi`                               |
| Generation with Messages (`Message`, `Role`, `TextPart`) | `say_hi_constrained`                   |
| Generated response as stream (Prompt String)             | `say_hi_stream`                        |
| Generation with Tools                                    | `calculate_gablorken`                  |
| Generate current weather response using tools            | `get_weather_flow`                     |
| Weather response generated as stream                     | `get_weather_flow_stream`              |
| Tool Response Handling with context                      | `generate_character`                   |


"""

import os
from decimal import Decimal
from typing import Annotated, cast

import httpx
import structlog
from pydantic import BaseModel, Field

from genkit.ai import ActionRunContext, Genkit
from genkit.plugins.compat_oai import OpenAI, openai_model

if 'OPENAI_API_KEY' not in os.environ:
    os.environ['OPENAI_API_KEY'] = input('Please enter your OPENAI_API_KEY: ')

logger = structlog.get_logger(__name__)

ai = Genkit(plugins=[OpenAI()], model=openai_model('gpt-4o'))


class MyInput(BaseModel):
    """My input."""

    a: int = Field(default=5, description='a field')
    b: int = Field(default=3, description='b field')


class HelloSchema(BaseModel):
    """Hello schema.

    Args:
        text: The text to say hello to.
        receiver: The receiver of the hello.
    """

    text: str
    receiver: str


@ai.flow()
def sum_two_numbers2(my_input: MyInput) -> int:
    """Sum two numbers.

    Args:
        my_input: The input to sum.

    Returns:
        The sum of the input.
    """
    return my_input.a + my_input.b


@ai.flow()
async def say_hi(name: Annotated[str, Field(default='Alice')] = 'Alice') -> str:
    """Say hi to a name.

    Args:
        name: The name to say hi to.

    Returns:
        The response from the OpenAI API.
    """
    response = await ai.generate(
        model=openai_model('gpt-4o'),
        config={'temperature': 1},
        prompt=f'hi {name}',
    )
    return response.text


@ai.flow()
async def say_hi_stream(name: Annotated[str, Field(default='Alice')] = 'Alice') -> str:
    """Say hi to a name and stream the response.

    Args:
        name: The name to say hi to.

    Returns:
        The response from the OpenAI API.
    """
    stream, _ = ai.generate_stream(
        model=openai_model('gpt-4'),
        config={'model': 'gpt-4-0613', 'temperature': 1},
        prompt=f'hi {name}',
    )
    result: str = ''
    async for data in stream:
        result += data.text
    return result


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


@ai.flow()
async def get_weather_flow(location: Annotated[str, Field(default='New York')] = 'New York') -> str:
    """Get the weather for a location.

    Args:
        location: The location to get the weather for.

    Returns:
        The weather for the location.
    """
    response = await ai.generate(
        model=openai_model('gpt-4o-mini'),
        system='You are an assistant that provides current weather information in JSON format.',
        config={'model': 'gpt-4o-mini-2024-07-18', 'temperature': 1},
        prompt=f"What's the weather like in {location} today?",
        tools=['get_weather_tool'],
        output_schema=WeatherResponse,
    )
    return response.text


@ai.flow()
async def get_weather_flow_stream(location: Annotated[str, Field(default='New York')] = 'New York') -> str:
    """Get the weather for a location using a stream.

    Args:
        location: The location to get the weather for.

    Returns:
        The weather for the location as a string.
    """
    stream, _ = ai.generate_stream(
        model=openai_model('gpt-4o'),
        system='You are an assistant that provides current weather information in JSON format and calculates '
        'gablorken based on weather value',
        config={'model': 'gpt-4o-2024-08-06', 'temperature': 1},
        prompt=f"What's the weather like in {location} today?",
        tools=['get_weather_tool', 'gablorkenTool'],
        output_schema=WeatherResponse,
    )
    result: str = ''
    async for data in stream:
        result += data.text
    return result


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


class GablorkenInput(BaseModel):
    """The Pydantic model for tools."""

    value: int = Field(description='value to calculate gablorken for')


@ai.tool(description='calculates a gablorken', name='gablorkenTool')
def gablorken_tool(input_: GablorkenInput) -> int:
    """Calculate a gablorken.

    Args:
        input_: The input to calculate gablorken for.

    Returns:
        The calculated gablorken.
    """
    return input_.value * 3 - 5


@ai.flow()
async def calculate_gablorken(value: Annotated[int, Field(default=42)] = 42) -> str:
    """Generate a request to calculate gablorken according to gablorken_tool.

    Args:
        value: Input data containing number

    Returns:
        A GenerateRequest object with the evaluation output
    """
    response = await ai.generate(
        prompt=f'what is the gablorken of {value}',
        model=openai_model('gpt-4'),
        tools=['gablorkenTool'],
    )

    return response.text


@ai.flow()
async def say_hi_constrained(hi_input: Annotated[str, Field(default='World')] = 'World') -> HelloSchema:
    """Generate a request to greet a user with response following `HelloSchema` schema.

    Args:
        hi_input: Input data containing user information.

    Returns:
        A `HelloSchema` object with the greeting message.
    """
    response = await ai.generate(
        prompt='hi ' + hi_input,
        output_schema=HelloSchema,
    )
    return cast(HelloSchema, response.output)


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
            prompt=f'generate an RPG character named {name} with gablorken based on 42',
            output_schema=RpgCharacter,
            config={'model': 'gpt-4o-2024-08-06', 'temperature': 1},
            tools=['gablorkenTool'],
        )
        async for data in stream:
            ctx.send_chunk(data.output)

        return cast(RpgCharacter, (await result).output)
    else:
        result = await ai.generate(
            prompt=f'generate an RPG character named {name} with gablorken based on 13',
            output_schema=RpgCharacter,
            config={'model': 'gpt-4o-2024-08-06', 'temperature': 1},
            tools=['gablorkenTool'],
        )
        return cast(RpgCharacter, result.output)


async def main() -> None:
    """Main entry point for the OpenAI sample - keep alive for Dev UI."""
    import asyncio

    await logger.ainfo('Genkit server running. Press Ctrl+C to stop.')
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
