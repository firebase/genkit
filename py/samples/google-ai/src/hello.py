# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import asyncio

from genkit.ai import Genkit
from genkit.core.typing import GenerationCommonConfig, Message, Role, TextPart
from genkit.plugins.google_ai import (
    GoogleAi,
    GoogleAiPluginOptions,
    googleai_name,
)
from genkit.plugins.google_ai.models import gemini

ai = Genkit(
    plugins=[GoogleAi(plugin_params=GoogleAiPluginOptions())],
    model=googleai_name(gemini.GoogleAiVersion.GEMINI_2_0_FLASH),
)


@ai.flow()
async def say_hi(data: str):
    return await ai.generate(
        messages=[
            Message(role=Role.USER, content=[TextPart(text=f'hi {data}')])
        ]
    )


async def say_hi_with_configured_temperature(data: str):
    return await ai.generate(
        messages=[
            Message(role=Role.USER, content=[TextPart(text=f'hi {data}')])
        ],
        config=GenerationCommonConfig(temperature=0.1),
    )


def main() -> None:
    print(asyncio.run(say_hi(', tell me a joke')).message.content)
    print(
        asyncio.run(
            say_hi_with_configured_temperature(', tell me a joke')
        ).message.content
    )


if __name__ == '__main__':
    main()
