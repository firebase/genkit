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

from typing import Annotated, Any, cast

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
def gablorken_tool(input: GablorkenInput) -> int:
    """Calculate a gablorken."""
    return input.value * 3 - 5


class WeatherToolInput(BaseModel):
    """Input for the weather tool."""

    location: str = Field(description='weather location')


@ai.tool()
def get_weather(input: WeatherToolInput) -> str:
    """Use it get the weather."""
    return f'Weather in {input.location} is 23°'


@ai.flow()
async def say_hi(hi_input: Annotated[str, Field(default='World')] = 'World') -> str:
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
async def weather_flow(location: Annotated[str, Field(default='San Francisco')] = 'San Francisco') -> str:
    """Generate a request to calculate gablorken according to gablorken_tool.

    Args:
        location: The location to get weather for.

    Returns:
        A GenerateRequest object with the evaluation output

    Example:
        >>> await weather_flow('San Francisco')
        'Weather in San Francisco is 23°'
    """
    response = await ai.generate(
        prompt=f'Use the get_weather tool to tell me the weather in {location}',
        model=ollama_name(MISTRAL_MODEL),
        tools=['get_weather'],
    )
    return response.text


@ai.flow()
async def calculate_gablorken(value: Annotated[int, Field(default=33)] = 33) -> str:
    """Generate a request to calculate gablorken according to gablorken_tool.

    Args:
        value: Input data containing number

    Returns:
        A GenerateRequest object with the evaluation output

    Example:
        >>> await calculate_gablorken(33)
        '94'
    """
    response = await ai.generate(
        prompt=f'Use the gablorken_tool to calculate the gablorken of {value}',
        model=ollama_name(MISTRAL_MODEL),
        tools=['gablorken_tool'],
    )
    return response.text


@ai.flow()
async def say_hi_constrained(hi_input: Annotated[str, Field(default='John Doe')] = 'John Doe') -> str:
    """Generate a request to greet a user with response following `HelloSchema` schema.

    Args:
        hi_input: Input data containing user information.

    Returns:
        The greeting text.

    Example:
        >>> await say_hi_constrained('John Doe')
        'Hi John Doe'
    """
    response = await ai.generate(
        prompt=f'Say hi to {hi_input} and put {hi_input} in receiver field',
        output_schema=HelloSchema,
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


async def main() -> None:
    """Main function.

    Returns:
        None.
    """
    await logger.ainfo(await say_hi('John Doe'))
    await logger.ainfo(await say_hi_constrained('John Doe'))
    await logger.ainfo(await calculate_gablorken(33))
    await logger.ainfo(await weather_flow('San Francisco'))


if __name__ == '__main__':
    ai.run_main(main())
