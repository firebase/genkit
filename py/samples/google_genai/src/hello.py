# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import asyncio

from genkit.ai.document import Document
from genkit.core.typing import GenerationCommonConfig, Message, Role, TextPart
from genkit.plugins.google_genai import (
    EmbeddingTaskType,
    GeminiEmbeddingModels,
    GoogleGenai,
    google_genai_name,
)
from genkit.veneer import Genkit

ai = Genkit(
    plugins=[GoogleGenai()],
    model=google_genai_name('gemini-2.0-flash'),
)


@ai.flow()
async def say_hi(data: str):
    return await ai.generate(
        messages=[
            Message(role=Role.USER, content=[TextPart(text=f'hi {data}')])
        ],
        output_format='json',
    )


@ai.flow()
async def embed_docs(docs: list[str]):
    """Generate an embedding for the words in a list.

    Args:
        docs: list of texts (string)

    Returns:
        The generated embedding.
    """
    options = {'task_type': EmbeddingTaskType.CLUSTERING}
    return await ai.embed(
        model=google_genai_name(GeminiEmbeddingModels.TEXT_EMBEDDING_004),
        documents=[Document.from_text(doc) for doc in docs],
        options=options,
    )


@ai.flow()
async def say_hi_with_configured_temperature(data: str):
    return await ai.generate(
        messages=[
            Message(role=Role.USER, content=[TextPart(text=f'hi {data}')])
        ],
        config=GenerationCommonConfig(temperature=0.1),
    )


@ai.flow()
async def say_hi_stream(name: str):
    stream, _ = ai.generate_stream(
        prompt=f'hi {name}',
    )
    result = ''
    async for data in stream:
        for part in data.content:
            result += part.root.text
    return result


def main() -> None:
    print(asyncio.run(say_hi(', tell me a joke')).message.content)
    print(asyncio.run(say_hi_stream(', tell me a joke')))

    print(
        asyncio.run(
            embed_docs(['banana muffins? ', 'banana bread? banana muffins?'])
        )
    )


if __name__ == '__main__':
    main()
