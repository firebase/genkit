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
    operation: str = Field(description='Math operation: add, subtract, multiply, divide')
    a: float = Field(description='First number')
    b: float = Field(description='Second number')


@ai.tool()
def get_weather(input: WeatherInput) -> dict:
    weather_data = {
        'New York': {'temp': 15, 'condition': 'cloudy', 'humidity': 65},
        'London': {'temp': 12, 'condition': 'rainy', 'humidity': 78},
        'Tokyo': {'temp': 20, 'condition': 'sunny', 'humidity': 55},
        'Paris': {'temp': 14, 'condition': 'partly cloudy', 'humidity': 60},
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
    operations = {
        'add': lambda a, b: a + b,
        'subtract': lambda a, b: a - b,
        'multiply': lambda a, b: a * b,
        'divide': lambda a, b: a / b if b != 0 else None,
    }

    operation = input.operation.lower()
    if operation not in operations:
        return {'error': f'Unknown operation: {operation}'}

    result = operations[operation](input.a, input.b)
    return {
        'operation': operation,
        'a': input.a,
        'b': input.b,
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
    weather_data = get_weather(WeatherInput(location=location))
    return (
        f'Weather in {location}: {weather_data.get("temp")}°{weather_data.get("unit")}, {weather_data.get("condition")}'
    )


@ai.flow()
async def calculator_flow(expression: str) -> str:
    parts = expression.split('_')
    if len(parts) < 3:
        return 'Invalid expression format. Use: operation_a_b (e.g., add_5_3)'

    operation, a, b = parts[0], float(parts[1]), float(parts[2])
    result = calculate(CalculatorInput(operation=operation, a=a, b=b))
    if 'error' in result:
        return f'Error: {result["error"]}'
    return f'{operation.title()}({a}, {b}) = {result.get("result")}'


if __name__ == '__main__':
    import asyncio

    async def main():
        result = await say_hi('Alice')
        logger.info('say_hi', result=result)

        result = await say_hi_stream('Bob')
        logger.info('say_hi_stream', result=result[:150])

        result = await say_hi_with_config('Charlie')
        logger.info('say_hi_with_config', result=result)

        result = await weather_flow('New York')
        logger.info('weather_flow', result=result)

        result = await calculator_flow('add_5_3')
        logger.info('calculator_flow', result=result)
