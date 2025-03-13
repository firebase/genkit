# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
import asyncio
import json

from genkit.core.typing import Message, Role, TextPart
from genkit.plugins.ollama import Ollama, ollama_name
from genkit.plugins.ollama.models import (
    ModelDefinition,
    OllamaAPITypes,
    OllamaPluginParams,
)
from genkit.veneer import Genkit
from pydantic import BaseModel

# model can be pulled with `ollama pull *LLM_VERSION*`
LLM_VERSION = 'gemma2:latest'

plugin_params = OllamaPluginParams(
    models=[
        ModelDefinition(
            name=LLM_VERSION,
            api_type=OllamaAPITypes.CHAT,
        )
    ],
)

ai = Genkit(
    plugins=[
        Ollama(
            plugin_params=plugin_params,
        )
    ],
    model=ollama_name(LLM_VERSION),
)


class HelloSchema(BaseModel):
    text: str
    receiver: str


def on_chunk(chunk):
    print('received chunk: ', chunk)


@ai.flow()
async def say_hi(hi_input: str):
    """Generate a request to greet a user.

    Args:
        hi_input: Input data containing user information.

    Returns:
        A GenerateRequest object with the greeting message.
    """
    return await ai.generate(
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


if __name__ == '__main__':
    asyncio.run(main())
