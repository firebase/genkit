# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import asyncio

from genkit.core.typing import GenerationCommonConfig, Message, Role, TextPart
from genkit.plugins.google_ai.models import gemini
from genkit.plugins.google_genai import (
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
        ]
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


if __name__ == '__main__':
    main()
