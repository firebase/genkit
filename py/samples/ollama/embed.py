# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
import asyncio

from genkit.plugins.ollama import Ollama, ollama_name
from genkit.plugins.ollama.models import (
    EmbeddingModelDefinition,
    OllamaPluginParams,
)
from genkit.veneer import Genkit

# model can be pulled with `ollama pull *LLM_VERSION*`
EMBEDDER_VERSION = 'mxbai-embed-large'

plugin_params = OllamaPluginParams(
    embedders=[
        EmbeddingModelDefinition(
            name=EMBEDDER_VERSION,
            dimensions=512,
        )
    ],
)

ai = Genkit(
    plugins=[
        Ollama(
            plugin_params=plugin_params,
        )
    ],
)


async def sample_embed(documents: list[str]):
    """Generate a request to greet a user.

    Args:
        hi_input: Input data containing user information.

    Returns:
        A GenerateRequest object with the greeting message.
    """
    return await ai.embed(
        model=ollama_name(EMBEDDER_VERSION),
        documents=documents,
    )


async def main() -> None:
    response = await sample_embed(
        documents=[
            'test document 1',
            'test document 2',
        ]
    )
    print(response)


if __name__ == '__main__':
    asyncio.run(main())
