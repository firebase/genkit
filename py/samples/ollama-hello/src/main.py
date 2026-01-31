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

"""Ollama hello sample - Local LLM inference with Genkit.

This sample demonstrates how to use Ollama for local LLM inference with Genkit,
enabling offline AI capabilities without external API dependencies.

See README.md for testing instructions.

Key Concepts (ELI5)::

    ┌─────────────────────┬────────────────────────────────────────────────────┐
    │ Concept             │ ELI5 Explanation                                   │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Ollama              │ Software that runs AI on YOUR computer. No cloud  │
    │                     │ needed - your data stays private!                 │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Local LLM           │ An AI that runs offline on your machine.          │
    │                     │ Like having a mini ChatGPT at home.               │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Gemma               │ Google's open-source model. Free to run locally.  │
    │                     │ Good for general tasks and coding help.           │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ Mistral             │ Another open-source model. Good at reasoning      │
    │                     │ and supports tool calling.                        │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ ollama pull         │ Downloads a model. Run "ollama pull gemma3"       │
    │                     │ before using it in your code.                     │
    ├─────────────────────┼────────────────────────────────────────────────────┤
    │ localhost:11434     │ Where Ollama listens. Your code talks to this     │
    │                     │ address to use local models.                      │
    └─────────────────────┴────────────────────────────────────────────────────┘

Key Features
============
| Feature Description                                      | Example Function / Code Snippet        |
|----------------------------------------------------------|----------------------------------------|
| Plugin Initialization                                    | `ai = Genkit(plugins=[Ollama()])`      |
| Default Model Configuration                              | `ai = Genkit(model=...)`               |
| Defining Flows                                           | `@ai.flow()` decorator (multiple uses) |
| Defining Tools                                           | `@ai.tool()` decorator (multiple uses) |
| Tool Input Schema (Pydantic)                             | `GablorkenInput`                       |
| Simple Generation (Prompt String)                        | `say_hi`                               |
| Streaming Generation                                     | `say_hi_stream`                        |
| Generation with Messages (`Message`, `Role`, `TextPart`) | `say_hi_constrained`                   |
| Generation with Tools                                    | `calculate_gablorken`                  |
| Tool Response Handling                                   | `say_hi_constrained`                   |
"""

from typing import Any, cast

from pydantic import BaseModel, Field
from rich.traceback import install as install_rich_traceback

from genkit.ai import Genkit, Output
from genkit.core.action import ActionRunContext
from genkit.core.logging import get_logger
from genkit.plugins.ollama import Ollama, ollama_name
from genkit.plugins.ollama.models import (
    ModelDefinition,
)

install_rich_traceback(show_locals=True, width=120, extra_lines=3)

logger = get_logger(__name__)

# Model can be pulled with `ollama pull *LLM_VERSION*`
GEMMA_MODEL = 'gemma3:latest'

# NOTE: gemma2:latest does not support tools calling as of 12.03.2025
# temporary using mistral-nemo instead.
MISTRAL_MODEL = 'mistral-nemo:latest'

# Run your ollama models with `ollama run *MODEL_NAME*`
# e.g. `ollama run gemma3:latest`

ai = Genkit(
    plugins=[
        Ollama(
            models=[
                ModelDefinition(name=GEMMA_MODEL),
                ModelDefinition(name=MISTRAL_MODEL),
            ],
        )
    ],
    model=ollama_name(GEMMA_MODEL),
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


class GablorkenInput(BaseModel):
    """Input model for the gablorken tool function.

    Attributes:
        value: The value to calculate gablorken for.
    """

    value: int = Field(description='value to calculate gablorken for')


class GablorkenOutputSchema(BaseModel):
    """Gablorken output schema.

    Args:
        result: The result of the gablorken.
    """

    result: int


class HelloSchema(BaseModel):
    """Hello schema.

    Args:
        text: The text to say hello to.
        receiver: The receiver of the hello.
    """

    text: str
    receiver: str


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


class WeatherToolInput(BaseModel):
    """Input for the weather tool."""

    location: str = Field(description='weather location')


class GablorkenFlowInput(BaseModel):
    """Input for gablorken calculation flow."""

    value: int = Field(default=33, description='Value to calculate gablorken for')


class SayHiInput(BaseModel):
    """Input for say_hi flow."""

    hi_input: str = Field(default='Mittens', description='Name to greet')


class SayHiConstrainedInput(BaseModel):
    """Input for constrained greeting flow."""

    hi_input: str = Field(default='Fluffy', description='Name to greet')


class StreamInput(BaseModel):
    """Input for streaming flow."""

    name: str = Field(default='Shadow', description='Name for streaming greeting')


class CharacterInput(BaseModel):
    """Input for character generation."""

    name: str = Field(default='Whiskers', description='Character name')


class WeatherFlowInput(BaseModel):
    """Input for weather flow."""

    location: str = Field(default='San Francisco', description='Location for weather')


@ai.flow()
async def calculate_gablorken(input: GablorkenFlowInput) -> str:
    """Generate a request to calculate gablorken according to gablorken_tool.

    Args:
        input: Input with value for gablorken calculation.

    Returns:
        A GenerateRequest object with the evaluation output

    Example:
        >>> await calculate_gablorken(GablorkenFlowInput(value=33))
        '94'
    """
    response = await ai.generate(
        prompt=f'Use the gablorken_tool to calculate the gablorken of {input.value}',
        model=ollama_name(MISTRAL_MODEL),
        tools=['gablorken_tool'],
    )
    return response.text


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
    # Note: Using GEMMA_MODEL as it typically supports tool use, but always verify tool support
    response = await ai.generate(
        model=ollama_name(MISTRAL_MODEL),
        prompt=f'Convert {input.amount} {input.from_curr} to {input.to_curr}',
        tools=['convert_currency'],
    )
    return response.text


@ai.tool()
def gablorken_tool(input: GablorkenInput) -> int:
    """Calculate a gablorken."""
    return input.value * 3 - 5


@ai.flow()
async def generate_character(input: CharacterInput) -> RpgCharacter:
    """Generate an RPG character.

    Args:
        input: Input with character name.

    Returns:
        The generated RPG character.
    """
    result = await ai.generate(
        model=ollama_name(GEMMA_MODEL),
        prompt=f'generate an RPG character named {input.name}',
        output=Output(schema=RpgCharacter),
    )
    return result.output


@ai.tool()
def get_weather(input: WeatherToolInput) -> str:
    """Use it get the weather."""
    return f'Weather in {input.location} is 23°'


@ai.flow()
async def say_hi(input: SayHiInput) -> str:
    """Generate a request to greet a user.

    Args:
        input: Input with name to greet.

    Returns:
        A GenerateRequest object with the greeting message.
    """
    response = await ai.generate(
        model=ollama_name(GEMMA_MODEL),
        prompt='hi ' + input.hi_input,
    )
    return response.text


@ai.flow()
async def say_hi_constrained(input: SayHiConstrainedInput) -> str:
    """Generate a request to greet a user with response following `HelloSchema` schema.

    Args:
        input: Input with name to greet.

    Returns:
        The greeting text.

    Example:
        >>> await say_hi_constrained(SayHiConstrainedInput(hi_input='John Doe'))
        'Hi John Doe'
    """
    response = await ai.generate(
        prompt=f'Say hi to {input.hi_input} and put {input.hi_input} in receiver field',
        output=Output(schema=HelloSchema),
    )
    output = response.output
    if isinstance(output, HelloSchema):
        return output.text
    if isinstance(output, dict):
        # Cast to proper dict type to satisfy type checker
        output_dict = cast(dict[str, Any], output)
        text_val = output_dict.get('text')
        if isinstance(text_val, str):
            return text_val
    raise ValueError('Received invalid output from model')


@ai.flow()
async def say_hi_stream(
    input: StreamInput,
    ctx: ActionRunContext | None = None,
) -> str:
    """Generate a greeting for the given name.

    Args:
        input: Input with name for streaming.
        ctx: the context of the tool

    Returns:
        The generated response with a function.
    """
    stream, _ = ai.generate_stream(
        model=ollama_name(GEMMA_MODEL),
        prompt=f'hi {input.name}',
    )
    result: str = ''
    async for data in stream:
        if ctx is not None:
            ctx.send_chunk(data.text)
        result += data.text

    return result


@ai.flow()
async def weather_flow(input: WeatherFlowInput) -> str:
    """Generate a request to get weather using the get_weather tool.

    Args:
        input: Input with location for weather.

    Returns:
        Weather information for the location.

    Example:
        >>> await weather_flow(WeatherFlowInput(location='San Francisco'))
        'Weather in San Francisco is 23°'
    """
    response = await ai.generate(
        prompt=f'Use the get_weather tool to tell me the weather in {input.location}',
        model=ollama_name(MISTRAL_MODEL),
        tools=['get_weather'],
    )
    return response.text


async def main() -> None:
    """Main function.

    Returns:
        None.
    """
    await logger.ainfo(await say_hi(SayHiInput(hi_input='John Doe')))
    await logger.ainfo(await say_hi_constrained(SayHiConstrainedInput(hi_input='John Doe')))
    await logger.ainfo(await calculate_gablorken(GablorkenFlowInput(value=33)))
    await logger.ainfo(await weather_flow(WeatherFlowInput(location='San Francisco')))


if __name__ == '__main__':
    ai.run_main(main())
