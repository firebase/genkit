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

"""OpenAI sample."""

from decimal import Decimal

import httpx
import structlog
from pydantic import BaseModel, Field

from genkit.ai import ActionRunContext, Genkit
from genkit.plugins.compat_oai import OpenAI, openai_model

logger = structlog.get_logger(__name__)

ai = Genkit(plugins=[OpenAI()], model=openai_model('gpt-4o'))


class MyInput(BaseModel):
    """My input."""

    a: int = Field(description='a field')
    b: int = Field(description='b field')


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
async def say_hi(name: str) -> str:
    """Say hi to a name.

    Args:
        name: The name to say hi to.

    Returns:
        The response from the OpenAI API.
    """
    response = await ai.generate(
        model=openai_model('gpt-4'),
        config={'model': 'gpt-4-0613', 'temperature': 1},
        prompt=f'hi {name}',
    )
    return response.message.content[0].root.text


@ai.flow()
async def say_hi_stream(name: str) -> str:
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
    result = ''
    async for data in stream:
        for part in data.content:
            result += part.root.text
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
async def get_weather_flow(location: str) -> str:
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
    return response.message.content[0].root.text


@ai.flow()
async def get_weather_flow_stream(location: str) -> str:
    """Get the weather for a location using a stream.

    Args:
        location: The location to get the weather for.

    Returns:
        The weather for the location as a string.
    """
    stream, _ = ai.generate_stream(
        model=openai_model('gpt-4o'),
        system='You are an assistant that provides current weather information in JSON format and calculates gablorken based on weather value',
        config={'model': 'gpt-4o-2024-08-06', 'temperature': 1},
        prompt=f"What's the weather like in {location} today?",
        tools=['get_weather_tool', 'gablorkenTool'],
        output_schema=WeatherResponse,
    )
    result = ''
    async for data in stream:
        for part in data.content:
            result += part.root.text or ''
    return result


class Skills(BaseModel):
    """A set of core character skills for an RPG character"""

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
async def generate_character(name: str, ctx: ActionRunContext):
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

        return (await result).output
    else:
        result = await ai.generate(
            prompt=f'generate an RPG character named {name} with gablorken based on 13',
            output_schema=RpgCharacter,
            config={'model': 'gpt-4o-2024-08-06', 'temperature': 1},
            tools=['gablorkenTool'],
        )
        return result.output


async def main() -> None:
    """Main entry point for the OpenAI sample."""
    await logger.ainfo(sum_two_numbers2(MyInput(a=1, b=3)))

    await logger.ainfo(await say_hi('John Doe'))
    await logger.ainfo(await say_hi_stream('John Doe'))
    await logger.ainfo(await get_weather_flow('London and Paris'))
    await logger.ainfo(await get_weather_flow_stream('London and Paris'))

    await logger.ainfo(await generate_character('LunaDoodle', lambda x: x))
    await logger.ainfo(await generate_character('NoodleMan'))


if __name__ == '__main__':
    ai.run_main(main())
