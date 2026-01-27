# Copyright 2026 Google LLC
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

"""DeepSeek hello sample - DeepSeek models with Genkit.

This sample demonstrates how to use DeepSeek's models with Genkit,
including the powerful reasoning model (deepseek-reasoner).

See README.md for testing instructions.

Key Features
============
| Feature Description                     | Example Function / Code Snippet         |
|-----------------------------------------|-----------------------------------------|
| Plugin Initialization                   | `ai = Genkit(plugins=[DeepSeek(...)])`  |
| Default Model Configuration             | `ai = Genkit(model=deepseek_name(...))` |
| Defining Flows                          | `@ai.flow()` decorator                  |
| Defining Tools                          | `@ai.tool()` decorator                  |
| Pydantic for Tool Input Schema          | `WeatherInput`                          |
| Simple Generation (Prompt String)       | `say_hi`                                |
| Streaming Response                      | `streaming_flow`                        |
| Generation with Tools                   | `weather_flow`                          |
| Reasoning Model (deepseek-reasoner)     | `reasoning_flow`                        |
| Generation with Config                  | `custom_config_flow`                    |
| Multi-turn Chat                         | `chat_flow`                             |
"""

import os
from typing import Annotated, cast

import structlog
from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.core.action import ActionRunContext
from genkit.core.typing import Message, Part, Role, TextPart, ToolChoice
from genkit.plugins.deepseek import DeepSeek, deepseek_name

if 'DEEPSEEK_API_KEY' not in os.environ:
    os.environ['DEEPSEEK_API_KEY'] = input('Please enter your DEEPSEEK_API_KEY: ')

logger = structlog.get_logger(__name__)

ai = Genkit(
    plugins=[DeepSeek()],
    model=deepseek_name('deepseek-chat'),
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
    """Input schema for the weather tool."""

    location: str = Field(description='The city and state, e.g. San Francisco, CA')


@ai.flow()
async def chat_flow() -> str:
    """Multi-turn chat example demonstrating context retention.

    Returns:
        Final chat response.
    """
    history = []

    # First turn - User shares information
    prompt1 = (
        "Hi! I'm planning a trip to Tokyo next month. I'm really excited because I love Japanese cuisine, "
        'especially ramen and sushi.'
    )
    response1 = await ai.generate(
        prompt=prompt1,
        system='You are a helpful travel assistant.',
    )
    history.append(Message(role=Role.USER, content=[Part(root=TextPart(text=prompt1))]))
    if response1.message:
        history.append(response1.message)
    await logger.ainfo('chat_flow turn 1', result=response1.text)

    # Second turn - Ask question requiring context from first turn
    response2 = await ai.generate(
        messages=history
        + [Message(role=Role.USER, content=[Part(root=TextPart(text='What foods did I say I enjoy?'))])],
        system='You are a helpful travel assistant.',
    )
    history.append(Message(role=Role.USER, content=[Part(root=TextPart(text='What foods did I say I enjoy?'))]))
    if response2.message:
        history.append(response2.message)
    await logger.ainfo('chat_flow turn 2', result=response2.text)

    # Third turn - Ask question requiring context from both previous turns
    response3 = await ai.generate(
        messages=history
        + [
            Message(
                role=Role.USER,
                content=[Part(root=TextPart(text='Based on our conversation, suggest one restaurant I should visit.'))],
            )
        ],
        system='You are a helpful travel assistant.',
    )
    return response3.text


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
async def custom_config_flow(task: str | None = None) -> str:
    """Demonstrate custom model configurations for different tasks.

    Shows how different config parameters affect generation behavior:
    - 'creative': High temperature for diverse, creative outputs
    - 'precise': Low temperature with penalties for consistent, focused outputs
    - 'detailed': Extended output with frequency penalty to avoid repetition

    Args:
        task: Type of task - 'creative', 'precise', or 'detailed'

    Returns:
        Generated response showing the effect of different configs.
    """
    if task is None:
        task = 'creative'

    prompts = {
        'creative': 'Write a creative story opener about a robot discovering art',
        'precise': 'List the exact steps to make a cup of tea',
        'detailed': 'Explain how photosynthesis works in detail',
    }

    configs = {
        'creative': {
            'temperature': 1.5,  # High temperature for creativity
            'max_tokens': 200,
            'top_p': 0.95,
        },
        'precise': {
            'temperature': 0.1,  # Low temperature for consistency
            'max_tokens': 150,
            'presence_penalty': 0.5,  # Encourage covering all steps
        },
        'detailed': {
            'temperature': 0.7,
            'max_tokens': 400,  # More tokens for detailed explanation
            'frequency_penalty': 0.8,  # Reduce repetitive phrasing
        },
    }

    prompt = prompts.get(task, prompts['creative'])
    config = configs.get(task, configs['creative'])

    response = await ai.generate(
        prompt=prompt,
        config=config,
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
        model=deepseek_name('deepseek-chat'),
        prompt=f'generate an RPG character named {name}',
        output_schema=RpgCharacter,
    )
    return cast(RpgCharacter, result.output)


@ai.tool()
def get_weather(input: WeatherInput) -> str:
    """Get weather of a location, the user should supply a location first.

    Args:
        input: Weather input with location (city and state, e.g. San Francisco, CA).

    Returns:
        Weather information with temperature in degrees Fahrenheit.
    """
    # Mocked weather data
    weather_data = {
        'San Francisco, CA': {'temp': 72, 'condition': 'sunny', 'humidity': 65},
        'Seattle, WA': {'temp': 55, 'condition': 'rainy', 'humidity': 85},
    }

    location = input.location
    data = weather_data.get(location, {'temp': 70, 'condition': 'partly cloudy', 'humidity': 55})

    return f'The weather in {location} is {data["temp"]}°F and {data["condition"]}. Humidity is {data["humidity"]}%.'


@ai.flow()
async def reasoning_flow(prompt: str | None = None) -> str:
    """Solve reasoning problems using deepseek-reasoner model.

    Args:
        prompt: The reasoning question to solve. Defaults to a classic logic problem.

    Returns:
        The reasoning and answer.
    """
    if prompt is None:
        prompt = 'What is heavier, one kilo of steel or one kilo of feathers?'

    response = await ai.generate(
        model=deepseek_name('deepseek-reasoner'),
        prompt=prompt,
    )
    return response.text


@ai.flow()
async def say_hi(name: Annotated[str, Field(default='Alice')] = 'Alice') -> str:
    """Generate a simple greeting.

    Args:
        name: Name to greet.

    Returns:
        Greeting message.
    """
    response = await ai.generate(prompt=f'Say hello to {name}!')
    return response.text


@ai.flow()
async def streaming_flow(
    topic: Annotated[str, Field(default='pandas')] = 'pandas',
    ctx: ActionRunContext = None,  # type: ignore[assignment]
) -> str:
    """Generate with streaming response.

    Args:
        topic: Topic to generate about.
        ctx: Action run context for streaming chunks to client.

    Returns:
        Generated text.
    """
    response = await ai.generate(
        prompt=f'Tell me a fun fact about {topic}',
        on_chunk=ctx.send_chunk,
    )
    return response.text


@ai.flow()
async def weather_flow(location: Annotated[str, Field(default='San Francisco, CA')] = 'San Francisco, CA') -> str:
    """Get weather using compat-oai auto tool calling."""
    response = await ai.generate(
        model=deepseek_name('deepseek-chat'),
        prompt=f'What is the weather in {location}?',
        system=(
            'You have a tool called get_weather. '
            "It takes an object with a 'location' field. "
            'Always use this tool when asked about weather.'
        ),
        tools=['get_weather'],
        tool_choice=ToolChoice.REQUIRED,
        max_turns=2,
    )

    return response.text


async def main() -> None:
    """Main entry point for the DeepSeek sample - keep alive for Dev UI."""
    import asyncio

    await logger.ainfo('Genkit server running. Press Ctrl+C to stop.')
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
