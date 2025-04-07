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

"""Basic gemini usage samples and examples."""

import asyncio
import json

import structlog
from pydantic import BaseModel, Field, ValidationError

from genkit.ai import ActionRunContext, Genkit
from genkit.blocks.generate import generate_action
from genkit.plugins.google_genai import (
    ImagenVersion,
    VertexAI,
    vertexai_name,
)
from genkit.plugins.google_genai.models import gemini
from genkit.types import (
    GenerateActionOptions,
    GenerateResponseChunk,
    GenerationCommonConfig,
    Message,
    Role,
    TextPart,
)

logger = structlog.get_logger(__name__)

ai = Genkit(
    plugins=[VertexAI()],
    model=vertexai_name(gemini.VertexAIGeminiVersion.GEMINI_2_0_FLASH),
)


@ai.flow()
async def generate_joke(subject: str) -> str:
    """Generate a silly short joke about the provided subjet.

    Args:
        subject(str): The topic about which the joke will be generated.

    Returns:
        str: The generated joke.
    """
    return await ai.generate(
        config=GenerationCommonConfig(temperature=0.1, version='gemini-2.0-flash-001'),
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text=f'Tell silly short jokes about {subject}')],
            ),
        ],
    )


class ConversionInput(BaseModel):
    """Input for currency conversion."""

    amount: float = Field(description='The currency amount to convert')


@ai.tool()
def convert_currency(input: ConversionInput) -> float:
    """Tool to convert the currency with latest exchange rate.

    Args:
        input: GetWeatherInput object containing amount.

    Returns:
        float: Converted amount.
    """
    # Replace this with an actual API call to currency converter
    return input.amount * 0.9


@ai.flow()
async def convert_with_tools(amount: float) -> str:
    """Converts the currency with latest exchange rate.

    Args:
        amount(float): Amount to be converted.

    Returns:
        str: The generated conversion description.
    """
    response = await generate_action(
        ai.registry,
        GenerateActionOptions(
            model=vertexai_name(gemini.VertexAIGeminiVersion.GEMINI_2_0_FLASH),
            messages=[
                Message(
                    role=Role.USER,
                    content=[TextPart(text=f'What is {amount} USD in EUR?')],
                ),
            ],
            tools=['convert_currency'],
        ),
    )
    return response.text


@ai.flow()
async def draw_image(description: str):
    """Generates an image based on the provided description."""
    return await ai.generate(
        model=vertexai_name(ImagenVersion.IMAGEN3_FAST),
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text=f'Draw an image of {description}')],
            )
        ],
    )


class Recipe(BaseModel):
    """Recipe."""

    recipe_name: str
    ingredients: list[str]


@ai.flow()
async def generate_structured_content(food: str):
    """Generate a list of recipes and their ingredients for a food type.

    Args:
        food: Type of food for which recipes will be generated.

    Returns:
        List of recipes that follows schema config.
    """
    response = await ai.generate(
        model=vertexai_name(gemini.VertexAIGeminiVersion.GEMINI_2_0_FLASH),
        messages=[
            Message(
                role=Role.USER,
                content=[TextPart(text=f'List a few popular {food} recipes')],
            )
        ],
        output_constrained=True,
        output_content_type='application/json',
        output_schema=Recipe,
        output_instructions=True,
    )
    cleaned_data = undecorate(response.text, '```json\n', '```')
    return Recipe.model_validate(json.loads(cleaned_data)[0])


def undecorate(text: str, left: str, right: str) -> str:
    """Unwrap text between left and right markers."""
    if text.startswith(left) and text.endswith(right):
        return text[len(left) : -len(right)]
    return text


@ai.flow()
async def generate_long_joke(subject: str) -> str:
    """Generate a joke stream about the provided subjet.

    Args:
        subject(str): A string representing the joke topic.

    Returns:
        str: A joke stream containing the generated joke.
    """
    ctx = ActionRunContext()
    stream, res = ai.generate_stream(
        model=vertexai_name(gemini.VertexAIGeminiVersion.GEMINI_2_5_PRO_EXP_03_25),
        prompt=f'Tell a long and detailed joke about {subject}.',
    )
    async for chunk in stream:
        await logger.ainfo(chunk.text)
        ctx.send_chunk(
            GenerateResponseChunk(
                role=Role.MODEL,
                content=[TextPart(text=chunk.text)],
            )
        )
    return (await res).text


async def main() -> None:
    """Main entry point for the basic Gemini sample.

    This function demonstrates basic usage of the Gemini model in the Genkit
    framework.
    """
    await logger.ainfo(await generate_joke('banana'))
    await draw_image('A panda playing soccer')
    await generate_long_joke('banana')
    # TODO: fix this.
    # await logger.ainfo(await convert_with_tools(100.0))
    # await logger.ainfo(await generate_structured_content('cookie'))


if __name__ == '__main__':
    asyncio.run(main())
