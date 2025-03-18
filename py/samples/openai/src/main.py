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

import asyncio
from decimal import Decimal

import requests
from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.core.typing import Message, TextPart
from genkit.plugins.compat_oai import OpenAI, openai_model

ai = Genkit(plugins=[OpenAI()], model=openai_model('gpt-4'))


class MyInput(BaseModel):
    a: int = Field(description='a field')
    b: int = Field(description='b field')


class WeatherRequest(BaseModel):
    latitude: Decimal
    longitude: Decimal


@ai.flow()
def sum_two_numbers2(my_input: MyInput):
    return my_input.a + my_input.b


@ai.flow()
async def say_hi(name: str):
    response = await ai.generate(
        model=openai_model('gpt-4'),
        config={'model': 'gpt-4-0613', 'temperature': 1},
        prompt=f'hi {name}',
    )
    return response.message.content[0].root.text


@ai.flow()
async def say_hi_stream(name: str):
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


@ai.tool('Get current temperature for provided coordinates in celsius')
def get_weather_tool(coordinates: WeatherRequest) -> str:
    url = (
        f'https://api.open-meteo.com/v1/forecast?'
        f'latitude={coordinates.latitude}&longitude={coordinates.longitude}'
        f'&current=temperature_2m'
    )
    response = requests.get(url=url)
    data = response.json()
    return data['current']['temperature_2m']


@ai.flow()
async def get_weather_flow(location: str):
    response = await ai.generate(
        model=openai_model('gpt-4'),
        config={'model': 'gpt-4-0613', 'temperature': 1},
        prompt=f"What's the weather like in {location} today?",
        tools=['get_weather_tool'],
    )
    return response.message.content[0].root.text


@ai.flow()
async def get_weather_flow_stream(location: str):
    stream, _ = ai.generate_stream(
        model=openai_model('gpt-4'),
        config={'model': 'gpt-4-0613', 'temperature': 1},
        prompt=f"What's the weather like in {location} today?",
        tools=['get_weather_tool'],
    )
    result = ''
    async for data in stream:
        for part in data.content:
            result += part.root.text
    return result


async def main() -> None:
    print(sum_two_numbers2(MyInput(a=1, b=3)))

    print(await say_hi('John Doe'))
    print(await say_hi_stream('John Doe'))

    print(await get_weather_flow('London and Paris'))
    print(await get_weather_flow_stream('London and Paris'))


if __name__ == '__main__':
    asyncio.run(main())
