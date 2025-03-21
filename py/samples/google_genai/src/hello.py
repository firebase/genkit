# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

import asyncio

from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.blocks.generate import generate_action
from genkit.core.typing import (
    GenerateActionOptions,
    GenerationCommonConfig,
    Message,
    Role,
    TextPart,
)
from genkit.plugins.google_ai.models import gemini
from genkit.plugins.google_genai import (
    GoogleGenai,
    google_genai_name,
)

ai = Genkit(
    plugins=[GoogleGenai()],
    model=google_genai_name('gemini-2.0-flash'),
)


class GablorkenInput(BaseModel):
    """The Pydantic model for tools."""

    value: int = Field(description='value to calculate gablorken for')


@ai.tool('calculates a gablorken')
def gablorkenTool(input_: GablorkenInput) -> int:
    """The user-defined tool function."""
    return input_.value * 3 - 5


@ai.flow()
async def simple_generate_action_with_tools_flow(value: int) -> str:
    """Generate a greeting for the given name.

    Args:
        value: the integer to send to test function

    Returns:
        The generated response with a function.
    """
    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model=google_genai_name(gemini.GoogleAiVersion.GEMINI_1_5_FLASH),
            messages=[
                Message(
                    role=Role.USER,
                    content=[TextPart(text=f'what is a gablorken of {value}')],
                ),
            ],
            tools=['gablorkenTool'],
        ),
    )
    return response.text


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
    print(asyncio.run(simple_generate_action_with_tools_flow(7)))


if __name__ == '__main__':
    main()
