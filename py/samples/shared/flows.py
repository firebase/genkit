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

"""Common flows for samples."""

from genkit.ai import Genkit, Output
from genkit.core.action import ActionRunContext

from .types import CalculatorInput, CurrencyExchangeInput, RpgCharacter, WeatherInput


async def calculation_logic(ai: Genkit, input: CalculatorInput) -> str:
    """Business logic to perform currency conversion via an LLM tool call.

    Args:
        ai: The initialized Genkit instance.
        input: Validated currency exchange parameters.

    Returns:
        Conversion result.
    """
    response = await ai.generate(
        prompt=f'Calculate {input.a} {input.operation} {input.b}',
        tools=['calculate'],
    )

    return response.text


async def currency_exchange_logic(ai: Genkit, input: CurrencyExchangeInput) -> str:
    """Business logic to perform currency conversion via an LLM tool call.

    Args:
        ai: The initialized Genkit instance.
        input: Validated currency exchange parameters.

    Returns:
        Conversion result.
    """
    response = await ai.generate(
        prompt=f'Convert {input.amount} {input.from_currency} to {input.to_currency}',
        tools=['convert_currency'],
    )

    return response.text


async def generate_character_logic(ai: Genkit, name: str) -> RpgCharacter:
    """Generate an RPG character.

    Args:
        ai: The Genkit instance.
        name: The name of the character

    Returns:
        The generated RPG character.
    """
    result = await ai.generate(
        prompt=f'Generate a structured RPG character named {name}. Output ONLY the JSON object.',
        output=Output(schema=RpgCharacter),
    )
    return result.output  # type: RpgCharacter from Output(schema=RpgCharacter)


async def say_hi_logic(ai: Genkit, name: str) -> str:
    """Generates a simple greeting via the AI model.

    Args:
        ai: The Genkit instance.
        name: Name to greet.

    Returns:
        Greeting message from the LLM.
    """
    response = await ai.generate(prompt=f'Say hello to {name}!')
    return response.text


async def say_hi_stream_logic(ai: Genkit, name: str, ctx: ActionRunContext | None) -> str:
    """Generates a streaming story.

    Args:
        ai: The Genkit instance.
        name: Name to greet.
        ctx: Action context for streaming.
    """
    response = await ai.generate(
        prompt=f'Tell me a short story about {name}',
        on_chunk=ctx.send_chunk if ctx is not None else None,
    )
    return response.text


async def say_hi_with_config_logic(ai: Genkit, name: str) -> str:
    """Generates a greeting with custom model configuration.

    Args:
        ai: The Genkit instance.
        name: User name.

    Returns:
        Greeting message from the LLM.
    """
    response = await ai.generate(
        prompt=f'Write a creative greeting for {name}',
        config={'temperature': 1.0, 'max_output_tokens': 200},
    )
    return response.text


async def weather_logic(ai: Genkit, input: WeatherInput) -> str:
    """Get weather info using the weather tool (via model tool calling).

    Args:
        ai: The AI model or client used to generate the weather response.
        input: Weather input data.

    Returns:
        Formatted weather string.

    Example:
        >>> await weather_flow(WeatherInput(location='London'))
        "Weather in London: 15°C, cloudy"
    """
    response = await ai.generate(
        prompt=f'What is the weather in {input.location}?',
        tools=['get_weather'],
    )
    return response.text
