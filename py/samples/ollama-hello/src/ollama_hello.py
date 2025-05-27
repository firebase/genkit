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

"""Ollama hello sample.

Key features demonstrated in this sample:

| Feature Description                                      | Example Function / Code Snippet        |
|----------------------------------------------------------|----------------------------------------|
| Plugin Initialization                                    | `ai = Genkit(plugins=[Ollama()])` |
| Default Model Configuration                              | `ai = Genkit(model=...)`               |
| Defining Flows                                           | `@ai.flow()` decorator (multiple uses) |
| Defining Tools                                           | `@ai.tool()` decorator (multiple uses) |
| Pydantic for Tool Input Schema                           | `GablorkenOutputSchema`               |
| Simple Generation (Prompt String)                        | `say_hi`                               |
| Generation with Messages (`Message`, `Role`, `TextPart`) | `say_hi_constrained`                   |
| Generation with Tools                                    | `calculate_gablorken`                  |
| Tool Response Handling                                   | `say_hi_constrained`                   |


"""

import asyncio
import json

import structlog
from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.plugins.ollama import Ollama, ollama_name
from genkit.plugins.ollama.models import (
    ModelDefinition,
)

logger = structlog.get_logger(__name__)

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


class HelloSchema(BaseModel):
    """Hello schema.

    Args:
        text: The text to say hello to.
        receiver: The receiver of the hello.
    """

    text: str
    receiver: str


class GablorkenOutputSchema(BaseModel):
    """Gablorken output schema.

    Args:
        result: The result of the gablorken.
    """

    result: int


class GablorkenInput(BaseModel):
    """Input model for the gablorken tool function.

    Attributes:
        value: The value to calculate gablorken for.
    """

    value: int = Field(description='value to calculate gablorken for')


@ai.tool()
def gablorken_tool(input: GablorkenInput):
    """Calculate a gablorken."""
    return input.value * 3 - 5


class WeatherToolInput(BaseModel):
    location: str = Field(description='weather location')


@ai.tool()
def get_weather(input: WeatherToolInput) -> str:
    """Use it get the weather."""
    return f'Weather in {input.location} is 23°'


@ai.flow()
async def say_hi(hi_input: str):
    """Generate a request to greet a user.

    Args:
        hi_input: Input data containing user information.

    Returns:
        A GenerateRequest object with the greeting message.
    """
    response = await ai.generate(
        model=ollama_name(GEMMA_MODEL),
        prompt='hi ' + hi_input,
    )
    return response.text


@ai.flow()
async def weather_flow(location: str):
    """Generate a request to calculate gablorken according to gablorken_tool.

    Args:
        value: Input data containing number

    Returns:
        A GenerateRequest object with the evaluation output
    """
    response = await ai.generate(
        prompt=f'what is the weather in {location}',
        model=ollama_name(MISTRAL_MODEL),
        tools=['get_weather'],
    )
    return response.text


@ai.flow()
async def calculate_gablorken(value: int):
    """Generate a request to calculate gablorken according to gablorken_tool.

    Args:
        value: Input data containing number

    Returns:
        A GenerateRequest object with the evaluation output
    """
    response = await ai.generate(
        prompt=f'what is the gablorken of {value}',
        model=ollama_name(MISTRAL_MODEL),
        tools=['gablorken_tool'],
    )
    return response.text


@ai.flow()
async def say_hi_constrained(hi_input: str):
    """Generate a request to greet a user with response following `HelloSchema` schema.

    Args:
        hi_input: Input data containing user information.

    Returns:
        A `HelloSchema` object with the greeting message.
    """
    response = await ai.generate(
        prompt='hi ' + hi_input,
        output_schema=HelloSchema,
    )
    return response.output


async def main() -> None:
    """Main function.

    Returns:
        None.
    """
    await logger.ainfo(await say_hi('John Doe'))
    await logger.ainfo(await say_hi_constrained('John Doe'))
    await logger.ainfo(await calculate_gablorken(33))


if __name__ == '__main__':
    ai.run_main(main())
