# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
import asyncio
import json

from pydantic import BaseModel

from genkit.core.typing import Message, Role, TextPart
from genkit.plugins.ollama import Ollama, ollama_name
from genkit.plugins.ollama.models import (
    ModelDefinition,
    OllamaAPITypes,
    OllamaPluginParams,
)
from genkit.veneer import Genkit

# model can be pulled with `ollama pull *LLM_VERSION*`
GEMMA_MODEL = 'gemma2:latest'

# gemma2:latest does not support tools calling as of 12.03.2025
# temporary using mistral-nemo instead
MISTRAL_MODEL = 'mistral-nemo:latest'

plugin_params = OllamaPluginParams(
    models=[
        ModelDefinition(
            name=GEMMA_MODEL,
            api_type=OllamaAPITypes.CHAT,
        ),
        ModelDefinition(
            name=MISTRAL_MODEL,
            api_type=OllamaAPITypes.CHAT,
        ),
    ],
)

ai = Genkit(
    plugins=[
        Ollama(
            plugin_params=plugin_params,
        )
    ],
    model=ollama_name(GEMMA_MODEL),
)


class HelloSchema(BaseModel):
    text: str
    receiver: str


def on_chunk(chunk):
    print('received chunk: ', chunk)


class GablorkenOutputSchema(BaseModel):
    result: int


@ai.tool('calculates a gablorken')
def gablorken_tool(input: int) -> int:
    return input * 3 - 5


@ai.flow()
async def say_hi(hi_input: str):
    """Generate a request to greet a user.

    Args:
        hi_input: Input data containing user information.

    Returns:
        A GenerateRequest object with the greeting message.
    """
    return await ai.generate(
        model=ollama_name(GEMMA_MODEL),
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text='hi ' + hi_input),
                ],
            )
        ],
    )


@ai.flow()
async def calculate_gablorken(value: int):
    """Generate a request to calculate gablorken according to gablorken_tool

    Args:
        value: Input data containing number

    Returns:
        A GenerateRequest object with the evaluation output
    """
    response = await ai.generate(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text=f'run "gablorken_tool" for {value}'),
                ],
            )
        ],
        output_schema=GablorkenOutputSchema,
        model=ollama_name(MISTRAL_MODEL),
        tools=['gablorken_tool'],
    )
    message_raw = response.message.content[0].root.text
    return GablorkenOutputSchema.model_validate(json.loads(message_raw))


@ai.flow()
async def say_hi_constrained(hi_input: str):
    """Generate a request to greet a user with response
    following `HelloSchema` schema

    Args:
        hi_input: Input data containing user information.

    Returns:
        A `HelloSchema` object with the greeting message.
    """
    response = await ai.generate(
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text='hi ' + hi_input),
                ],
            )
        ],
        output_schema=HelloSchema,
    )
    message_raw = response.message.content[0].root.text
    return HelloSchema.model_validate(json.loads(message_raw))


async def main() -> None:
    print(await say_hi('John Doe'))
    print(await say_hi_constrained('John Doe'))
    print(await calculate_gablorken(3))


if __name__ == '__main__':
    asyncio.run(main())
