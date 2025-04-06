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

"""Sync and async flows."""

import argparse

import structlog
from pydantic import BaseModel, Field

from async_vs_sync import parse_args, server_main
from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI, googleai_name
from genkit.plugins.google_genai.models.gemini import GoogleAIGeminiVersion
from genkit.types import (
    GenerationCommonConfig,
    Message,
    Role,
    TextPart,
)
from genkit.web.manager import run_loop

logger = structlog.get_logger(__name__)

ai = Genkit(
    plugins=[GoogleAI()],
    model=googleai_name(GoogleAIGeminiVersion.GEMINI_2_0_FLASH),
)


@ai.flow()
async def namaste(name: str) -> str:
    """Namaste a person.

    Args:
        name: The name of the person to namaste.
    """
    response = await ai.generate(prompt=f'Namaste {name}')
    return response.text


@ai.flow()
async def say_hi_with_configured_temperature(data: str):
    """Generate a greeting for the given name.

    Args:
        data: the name to send to test function

    Returns:
        The generated response with a function.
    """
    return await ai.generate(
        messages=[Message(role=Role.USER, content=[TextPart(text=f'hi {data}')])],
        config=GenerationCommonConfig(temperature=0.1),
    )


@ai.flow()
async def say_hi_stream(name: str, ctx):
    """Generate a greeting for the given name.

    Args:
        name: the name to send to test function
        ctx: the context of the tool

    Returns:
        The generated response with a function.
    """
    stream, _ = ai.generate_stream(prompt=f'hi {name}')
    result = ''
    async for data in stream:
        ctx.send_chunk(data.text)
        for part in data.content:
            result += part.root.text

    return result


class GablorkenInput(BaseModel):
    """Input model for the gablorkenTool function.

    Attributes:
        value: The value to calculate gablorken for.
    """

    value: int = Field(description='value to calculate gablorken for')


@ai.tool(name='gablorkenTool', description='calculates a gablorken')
def gablorken_tool(input: GablorkenInput) -> int:
    """Calculate a gablorken.

    Args:
        input: The input to calculate gablorken for.

    Returns:
        The calculated gablorken.
    """
    return input.value * 3 - 5


@ai.flow()
async def simple_generate_with_tools_flow(value: int) -> str:
    """Generate a greeting for the given name.

    Args:
        value: the integer to send to test function

    Returns:
        The generated response with a function.
    """
    response = await ai.generate(
        model=googleai_name(GoogleAIGeminiVersion.GEMINI_2_0_FLASH),
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text=f'what is a gablorken of {value}')],
            ),
        ],
        tools=['gablorkenTool'],
    )
    return response.text


async def short_lived_main(ai: Genkit) -> None:
    """Main entry point for a short-lived app.

    This function demonstrates the usage of the AI flow by generating
    greetings and performing simple arithmetic operations.
    """
    await logger.ainfo(await namaste('John Doe'))
    await logger.ainfo(gablorken_tool(GablorkenInput(value=10)))


if __name__ == '__main__':
    config: argparse.Namespace = parse_args()
    if config.server:
        run_loop(server_main(ai))
    else:
        run_loop(short_lived_main(ai))
