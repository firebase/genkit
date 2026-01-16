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

"""xAI Genkit sample.

Demonstrates:
- Plugin initialization
- Simple text generation
- Streaming generation
- Tool usage
- Generation with configuration
"""

import structlog
from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.plugins.xai import XAI, xai_name
from genkit.types import ActionRunContext

logger = structlog.get_logger(__name__)

ai = Genkit(
    plugins=[XAI()],
    model=xai_name('grok-3'),
)


class WeatherInput(BaseModel):
    location: str = Field(description='City or location name')
    unit: str = Field(default='celsius', description='Temperature unit: celsius or fahrenheit')


class CalculatorInput(BaseModel):
    num1: float = Field(description='First number')
    num2: float = Field(description='Second number')
    operation: str = Field(description='Operation: +, -, *, /')


@ai.tool()
def get_weather(input: WeatherInput) -> dict:
    weather_data = {
        'New York': {'temp': 15, 'condition': 'cloudy'},
        'London': {'temp': 12, 'condition': 'rainy'},
        'Tokyo': {'temp': 20, 'condition': 'sunny'},
        'Paris': {'temp': 14, 'condition': 'windy'},
    }

    location = input.location.title()
    data = weather_data.get(location, {'temp': 18, 'condition': 'unknown', 'humidity': 50})

    if input.unit == 'fahrenheit' and 'temp' in data:
        data['temp'] = round((data['temp'] * 9 / 5) + 32, 1)
        data['unit'] = 'F'
    else:
        data['unit'] = 'C'

    data['location'] = location
    return data


@ai.tool()
def calculate(input: CalculatorInput) -> dict:
    a, op, b = input.num1, input.operation, input.num2

    if op == '+':
        result = a + b
    elif op == '-':
        result = a - b
    elif op == '*':
        result = a * b
    elif op == '/':
        if b == 0:
            return {'error': 'Division by zero'}
        result = a / b
    else:
        return {'error': f'Unknown operator: {op}'}

    return {
        'num1': a,
        'operation': op,
        'num2': b,
        'result': result,
    }


@ai.flow()
async def say_hi(name: str) -> str:
    response = await ai.generate(prompt=f'Say hello to {name}!')
    return response.text


@ai.flow()
async def say_hi_stream(name: str, ctx: ActionRunContext) -> str:
    response = await ai.generate(
        prompt=f'Tell me a short story about {name}',
        on_chunk=ctx.send_chunk,
    )
    return response.text


@ai.flow()
async def say_hi_with_config(name: str) -> str:
    response = await ai.generate(
        prompt=f'Write a creative greeting for {name}',
        config={'temperature': 1.0, 'max_output_tokens': 200},
    )
    return response.text


@ai.flow()
async def weather_flow(location: str) -> str:
    response = await ai.generate(
        prompt=f'What is the weather in {location}? Be concise and only provide the weather information.',
        tools=['get_weather'],
    )
    return response.text


@ai.flow()
async def calculator_flow(input: CalculatorInput) -> str:
    result = calculate(input)
    if 'error' in result:
        return f'Error: {result["error"]}'
    return f'{result["num1"]} {result["operation"]} {result["num2"]} = {result["result"]}'


async def main():
    result = await say_hi('Alice')
    logger.info('say_hi', result=result)

    result = await say_hi_stream('Bob')
    logger.info('say_hi_stream', result=result[:150])

    result = await say_hi_with_config('Charlie')
    logger.info('say_hi_with_config', result=result)

    result = await weather_flow('New York')
    logger.info('weather_flow', result=result)

    result = await calculator_flow(CalculatorInput(num1=5.0, operation='+', num2=3.0))
    logger.info('calculator_flow', result=result)


if __name__ == '__main__':
    ai.run_main(main())
