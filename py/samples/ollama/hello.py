# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
import asyncio

from genkit.core.typing import Message, Role, TextPart
from genkit.plugins.ollama import Ollama, ollama_name
from genkit.plugins.ollama.models import (
    ModelDefinition,
    OllamaAPITypes,
    OllamaPluginParams,
)
from genkit.veneer import Genkit

# model can be pulled with `ollama pull *LLM_VERSION*`
LLM_VERSION = 'gemma2:latest'

plugin_params = OllamaPluginParams(
    models=[
        ModelDefinition(
            name=LLM_VERSION,
            api_type=OllamaAPITypes.CHAT,
        )
    ],
    use_async_api=True,
)

ai = Genkit(
    plugins=[
        Ollama(
            plugin_params=plugin_params,
        )
    ],
    model=ollama_name(LLM_VERSION),
)


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
        ]
    )


async def main() -> None:
    response = await say_hi('John Doe')
    print(response)


if __name__ == '__main__':
    asyncio.run(main())
