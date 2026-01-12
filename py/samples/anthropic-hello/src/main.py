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

"""Anthropic hello sample.

Key features demonstrated in this sample:

| Feature Description                     | Example Function / Code Snippet     |
|-----------------------------------------|-------------------------------------|
| Plugin Initialization                   | `ai = Genkit(plugins=[Anthropic()])` |
| Default Model Configuration             | `ai = Genkit(model=...)`            |
| Defining Flows                          | `@ai.flow()` decorator              |
| Defining Tools                          | `@ai.tool()` decorator              |
| Pydantic for Tool Input Schema          | `WeatherInput`, `CurrencyInput`     |
| Simple Generation (Prompt String)       | `say_hi`                            |
| Streaming Generation                    | `say_hi_stream`                     |
| Generation with Tools                   | `weather_flow`, `currency_exchange` |
| Generation Configuration (temperature)  | `say_hi_with_config`                |
"""

import structlog
from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.plugins.anthropic import Anthropic, anthropic_name
from genkit.types import ActionRunContext, GenerationCommonConfig

logger = structlog.get_logger(__name__)

ai = Genkit(
    plugins=[Anthropic()],
    model=anthropic_name('claude-3-5-haiku'),
)


class WeatherInput(BaseModel):
    """Weather input schema."""

    location: str = Field(description='Location to get weather for')


class CurrencyInput(BaseModel):
    """Currency conversion input schema."""

    amount: float = Field(description='Amount to convert')
    from_currency: str = Field(description='Source currency code (e.g., USD)')
    to_currency: str = Field(description='Target currency code (e.g., EUR)')


class CurrencyExchangeInput(BaseModel):
    """Currency exchange flow input schema."""

    amount: float = Field(description='Amount to convert')
    from_curr: str = Field(description='Source currency code')
    to_curr: str = Field(description='Target currency code')


@ai.tool()
def get_weather(input: WeatherInput) -> str:
    """Get weather for a location.

    Args:
        input: Weather input with location.

    Returns:
        Weather information.
    """
    return f'Weather in {input.location}: Sunny, 23°C'


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
async def say_hi(name: str) -> str:
    """Generate a simple greeting.

    Args:
        name: Name to greet.

    Returns:
        Greeting message.
    """
    response = await ai.generate(
        prompt=f'Say hello to {name} in a friendly way',
    )
    return response.text


@ai.flow()
async def say_hi_stream(topic: str, ctx: ActionRunContext) -> str:
    """Generate streaming response.

    Args:
        topic: Topic to write about.
        ctx: Action run context for streaming.

    Returns:
        Complete generated text.
    """
    response = await ai.generate(
        prompt=f'Write a short story about {topic}',
        on_chunk=ctx.send_chunk,
    )
    return response.text


@ai.flow()
async def weather_flow(location: str) -> str:
    """Get weather using tools.

    Args:
        location: Location to get weather for.

    Returns:
        Weather information.
    """
    response = await ai.generate(
        prompt=f'What is the weather in {location}?',
        tools=['get_weather'],
    )
    return response.text


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
async def say_hi_with_config(name: str) -> str:
    """Generate greeting with custom configuration.

    Args:
        name: Name to greet.

    Returns:
        Greeting message.
    """
    response = await ai.generate(
        prompt=f'Say hello to {name}',
        config=GenerationCommonConfig(
            temperature=0.7,
            max_output_tokens=100,
        ),
    )
    return response.text


async def main() -> None:
    """Main entry point for the Anthropic sample."""
    result = await say_hi('John Doe')
    await logger.ainfo('Simple greeting', result=result)

    result = await say_hi_with_config('John Doe')
    await logger.ainfo('Custom config', result=result)

    result = await weather_flow('Paris')
    await logger.ainfo('Weather', result=result)

    result = await currency_exchange(CurrencyExchangeInput(amount=100.0, from_curr='USD', to_curr='EUR'))
    await logger.ainfo('Currency', result=result)


if __name__ == '__main__':
    ai.run_main(main())
