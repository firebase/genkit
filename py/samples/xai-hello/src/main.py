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

Key features demonstrated in this sample:

| Feature Description                     | Example Function / Code Snippet     |
|-----------------------------------------|-------------------------------------|
| Plugin Initialization                   | `ai = Genkit(plugins=[XAI()])`      |
| Model Configuration                     | `xai_name('grok-2')`                |
| Simple Text Generation                  | `say_hi`                            |
| Streaming Generation                    | `say_hi_stream`                     |
| Tool Usage (Decorated)                  | `get_weather`, `calculate`          |
| Generation Configuration                | `say_hi_with_config`                |
| Tool Calling                            | `weather_flow`                      |
"""

import os
from typing import Annotated, cast

import structlog
from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.core.action import ActionRunContext
from genkit.plugins.xai import XAI, xai_name

if 'XAI_API_KEY' not in os.environ:
    os.environ['XAI_API_KEY'] = input('Please enter your XAI_API_KEY: ')

logger = structlog.get_logger(__name__)

ai = Genkit(
    plugins=[XAI()],
    model=xai_name('grok-3'),
)


class CalculatorInput(BaseModel):
    """Input for the calculator tool."""

    operation: str = Field(description='Math operation: add, subtract, multiply, divide')
    a: float = Field(description='First number')
    b: float = Field(description='Second number')


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
    """Input for the weather tool."""

    location: str = Field(description='City or location name')
    unit: str = Field(default='celsius', description='Temperature unit: celsius or fahrenheit')


@ai.tool()
def calculate(input: CalculatorInput) -> dict:
    """Perform basic arithmetic operations.

    Args:
        input: Calculation request input.

    Returns:
        Calculation result dictionary.
    """
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
async def calculator_flow(expression: Annotated[str, Field(default='add_5_3')] = 'add_5_3') -> str:
    """Parse and calculate a math expression.

    Args:
        expression: String in format 'operation_a_b'.

    Returns:
        Calculation result string.

    Example:
        >>> await calculator_flow('add_5_3')
        "Add(5.0, 3.0) = 8.0"
    """
    parts = expression.split('_')
    if len(parts) < 3:
        return 'Invalid expression format. Use: operation_a_b (e.g., add_5_3)'

    operation, a, b = parts[0], float(parts[1]), float(parts[2])
    result = calculate(CalculatorInput(operation=operation, a=a, b=b))
    if 'error' in result:
        return f'Error: {result["error"]}'
    return f'{operation.title()}({a}, {b}) = {result.get("result")}'


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
def get_weather(input: WeatherInput) -> dict:
    """Get weather information for a location.

    Args:
        input: Weather request input.

    Returns:
        Weather data dictionary.
    """
    weather_data = {
        'New York': {'temp': 15, 'condition': 'cloudy', 'humidity': 65},
        'London': {'temp': 12, 'condition': 'rainy', 'humidity': 78},
        'Tokyo': {'temp': 20, 'condition': 'sunny', 'humidity': 55},
        'Paris': {'temp': 14, 'condition': 'partly cloudy', 'humidity': 60},
    }

    location = input.location.title()
    data = weather_data.get(location, {'temp': 18, 'condition': 'unknown', 'humidity': 50})

    if input.unit == 'fahrenheit' and 'temp' in data:
        temp = data['temp']
        if isinstance(temp, (int, float)):
            data['temp'] = round((temp * 9 / 5) + 32, 1)
            data['unit'] = 'F'
    else:
        data['unit'] = 'C'

    data['location'] = location
    return data


@ai.flow()
async def say_hi(name: Annotated[str, Field(default='Alice')] = 'Alice') -> str:
    """Generate a simple greeting.

    Args:
        name: Name to greet.

    Returns:
        Greeting message.

    Example:
        >>> await say_hi('Alice')
        "Hello Alice!"
    """
    response = await ai.generate(prompt=f'Say hello to {name}!')
    return response.text


@ai.flow()
async def say_hi_stream(
    name: Annotated[str, Field(default='Bob')] = 'Bob',
    ctx: ActionRunContext = None,  # type: ignore[assignment]
) -> str:
    """Generate a streaming story response.

    Args:
        name: Subject of the story.
        ctx: Action context for streaming.

    Returns:
        Complete story text.

    Example:
        >>> await say_hi_stream('Bob', ctx)
        "Once upon a time..."
    """
    response = await ai.generate(
        prompt=f'Tell me a short story about {name}',
        on_chunk=ctx.send_chunk,
    )
    return response.text


@ai.flow()
async def say_hi_with_config(name: Annotated[str, Field(default='Charlie')] = 'Charlie') -> str:
    """Generate a greeting with custom model configuration.

    Args:
        name: User name.

    Returns:
        Greeting message.

    Example:
        >>> await say_hi_with_config('Charlie')
        "Greetings, Charlie!"
    """
    response = await ai.generate(
        prompt=f'Write a creative greeting for {name}',
        config={'temperature': 1.0, 'max_output_tokens': 200},
    )
    return response.text


@ai.flow()
async def weather_flow(location: Annotated[str, Field(default='New York')] = 'New York') -> str:
    """Get weather info using the weather tool (via model tool calling).

    Args:
        location: City name.

    Returns:
        Formatted weather string.

    Example:
        >>> await weather_flow('New York')
        "Weather in New York: 15°C, cloudy"
    """
    response = await ai.generate(
        prompt=f'What is the weather in {location}?',
        tools=['get_weather'],
    )
    return response.text


async def main() -> None:
    """Main entry point - keep alive for Dev UI."""
    import asyncio

    logger.info('Genkit server running. Press Ctrl+C to stop.')
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
