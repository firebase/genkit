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

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ DeepSeek            │ Chinese AI company known for efficient models.     │
    │                     │ Great performance at lower cost.                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ deepseek-chat       │ The standard chat model. Good for most tasks       │
    │                     │ like writing, Q&A, and coding help.                │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ deepseek-reasoner   │ The R1 reasoning model. Shows its thinking         │
    │                     │ step by step - great for math and logic.           │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Chain-of-Thought    │ When AI explains its reasoning step by step.       │
    │                     │ Like showing your work on a test.                  │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Streaming           │ Get the response word-by-word as it's generated.   │
    │                     │ Feels faster, like watching someone type.          │
    └─────────────────────┴────────────────────────────────────────────────────┘

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

import asyncio
import os
import random

from pydantic import BaseModel, Field
from rich.traceback import install as install_rich_traceback

from genkit.ai import Genkit, Output
from genkit.core.action import ActionRunContext
from genkit.core.logging import get_logger
from genkit.core.typing import Message, Part, Role, TextPart, ToolChoice
from genkit.plugins.deepseek import DeepSeek, deepseek_name

install_rich_traceback(show_locals=True, width=120, extra_lines=3)

if 'DEEPSEEK_API_KEY' not in os.environ:
    os.environ['DEEPSEEK_API_KEY'] = input('Please enter your DEEPSEEK_API_KEY: ')

logger = get_logger(__name__)

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

    location: str = Field(description='City or location name')


class SayHiInput(BaseModel):
    """Input for say_hi flow."""

    name: str = Field(default='Mittens', description='Name to greet')


class StreamInput(BaseModel):
    """Input for streaming flow."""

    topic: str = Field(default='cats', description='Topic to generate about')


class CharacterInput(BaseModel):
    """Input for character generation."""

    name: str = Field(default='Whiskers', description='Character name')


class WeatherFlowInput(BaseModel):
    """Input for weather flow."""

    location: str = Field(default='London', description='Location to get weather for')


class ReasoningInput(BaseModel):
    """Input for reasoning flow."""

    prompt: str = Field(
        default='What is heavier, one kilo of steel or one kilo of feathers?',
        description='Reasoning question to solve',
    )


class CustomConfigInput(BaseModel):
    """Input for custom config flow."""

    task: str = Field(default='creative', description='Task type: creative, precise, or detailed')


@ai.tool()
def get_weather(input: WeatherInput) -> str:
    """Return a random realistic weather string for a location.

    Args:
        input: Weather input location.

    Returns:
        Weather information with temperature in degrees Celsius.
    """
    weather_options = [
        '32° C sunny',
        '17° C cloudy',
        '22° C cloudy',
        '19° C humid',
    ]
    return random.choice(weather_options)


@ai.flow()
async def reasoning_flow(input: ReasoningInput) -> str:
    """Solve reasoning problems using deepseek-reasoner model.

    Args:
        input: Input with reasoning question to solve.

    Returns:
        The reasoning and answer.
    """
    response = await ai.generate(
        model=deepseek_name('deepseek-reasoner'),
        prompt=input.prompt,
    )
    return response.text


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
async def custom_config_flow(input: CustomConfigInput) -> str:
    """Demonstrate custom model configurations for different tasks.

    Shows how different config parameters affect generation behavior:
    - 'creative': High temperature for diverse, creative outputs
    - 'precise': Low temperature with penalties for consistent, focused outputs
    - 'detailed': Extended output with frequency penalty to avoid repetition

    Args:
        input: Input with task type.

    Returns:
        Generated response showing the effect of different configs.
    """
    task = input.task

    prompts = {
        'creative': 'Write a creative story opener about a robot discovering art',
        'precise': 'List the exact steps to make a cup of tea',
        'detailed': 'Explain how photosynthesis works in detail',
    }

    configs = {
        'creative': {
            'temperature': 1.5,
            'max_tokens': 200,
            'top_p': 0.95,
        },
        'precise': {
            'temperature': 0.1,
            'max_tokens': 150,
            'presence_penalty': 0.5,
        },
        'detailed': {
            'temperature': 0.7,
            'max_tokens': 400,
            'frequency_penalty': 0.8,
        },
    }

    prompt = prompts.get(task, prompts['creative'])
    config = configs.get(task, configs['creative'])

    # pyrefly: ignore[no-matching-overload] - config dict is compatible with dict[str, object]
    response = await ai.generate(
        prompt=prompt,
        config=config,
    )
    return response.text


@ai.flow()
async def generate_character(input: CharacterInput) -> RpgCharacter:
    """Generate an RPG character.

    Args:
        input: Input with character name.

    Returns:
        The generated RPG character.
    """
    # DeepSeek JSON mode: prompt must mention 'json' and provide an example
    prompt = (
        f'Generate an RPG character named {input.name} in JSON format.\n'
        'Example:\n'
        '{\n'
        '  "name": "<character_name>",\n'
        '  "backStory": "A mysterious cat...",\n'
        '  "abilities": ["stealth", "agility", "night vision"],\n'
        '  "skills": {"strength": 10, "charisma": 15, "endurance": 12}\n'
        '}\n'
    )
    result = await ai.generate(
        model=deepseek_name('deepseek-chat'),
        prompt=prompt,
        output=Output(schema=RpgCharacter),
    )
    return result.output


@ai.flow()
async def say_hi(input: SayHiInput) -> str:
    """Generate a simple greeting.

    Args:
        input: Input with name to greet.

    Returns:
        Greeting message.
    """
    response = await ai.generate(prompt=f'Say hello to {input.name}!')
    return response.text


@ai.flow()
async def streaming_flow(
    input: StreamInput,
    ctx: ActionRunContext | None = None,
) -> str:
    """Generate with streaming response.

    Args:
        input: Input with topic to generate about.
        ctx: Action run context for streaming chunks to client.

    Returns:
        Generated text.
    """
    response = await ai.generate(
        prompt=f'Tell me a fun fact about {input.topic}',
        on_chunk=ctx.send_chunk if ctx else None,
    )
    return response.text


@ai.flow()
async def weather_flow(input: WeatherFlowInput) -> str:
    """Get weather using compat-oai auto tool calling."""
    response = await ai.generate(
        model=deepseek_name('deepseek-chat'),
        prompt=f'What is the weather in {input.location}?',
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
    await logger.ainfo('Genkit server running. Press Ctrl+C to stop.')
    # Keep the process alive for Dev UI
    await asyncio.Event().wait()


if __name__ == '__main__':
    ai.run_main(main())
