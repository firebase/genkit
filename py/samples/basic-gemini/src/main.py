# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Basic gemini usage samples and examples."""

import asyncio
import json

from pydantic import BaseModel, Field

from genkit.ai.generate import generate_action
from genkit.core.action import ActionRunContext
from genkit.core.typing import (
    GenerateActionOptions,
    GenerateResponseChunk,
    GenerationCommonConfig,
    Message,
    Role,
    TextPart,
)
from genkit.plugins.vertex_ai import (
    GeminiVersion,
    ImagenVersion,
    VertexAI,
    vertexai_name,
)
from genkit.veneer.veneer import Genkit

ai = Genkit(
    plugins=[VertexAI()],
    model=vertexai_name(GeminiVersion.GEMINI_1_5_FLASH),
)


@ai.flow()
async def generate_joke(subject: str) -> str:
    """Generate a silly short joke about the provided subjet.

    Args:
        subject(str): A string representing the topic about which the joke will be generated.

    Returns:
        str: A string containing the generated joke.
    """
    return await ai.generate(
        config=GenerationCommonConfig(
            temperature=0.1, version='gemini-1.5-flash-002'
        ),
        messages=[
            Message(
                role=Role.USER,
                content=[
                    TextPart(text=f'Tell silly short jokes about {subject}')
                ],
            ),
        ],
    )


class ConversionInput(BaseModel):
    amount: float = Field(description='The currency amount to convert')


@ai.tool('Converts currency with latest exchange rate')
def convert_currency(input: ConversionInput) -> float:
    """Tool to convert the currency with latest exchange rate

    Args:
        input(ConversionInput): GetWeatherInput object containing amount

    Returns:
        float: Converted amount
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
            model=vertexai_name(GeminiVersion.GEMINI_1_5_PRO),
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
    recipe_name: str
    ingredients: list[str]


@ai.flow()
async def generate_structured_content(food: str):
    """Generate a structured list of recipes and their ingredients for a food type.

    Args:
        food(str): Type of food for which recipes will be generated.

    Returns:
        List of recipes that follows schema config.
    """

    response = await ai.generate(
        model=vertexai_name(GeminiVersion.GEMINI_1_5_PRO),
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
    cleaned_data = response.text.strip('```json\n').strip('```')
    return Recipe.model_validate(json.loads(cleaned_data)[0])


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
        model=vertexai_name(GeminiVersion.GEMINI_1_5_PRO),
        prompt=f'Tell a long and detailed joke about {subject}.',
    )
    async for chunk in stream:
        print(chunk.text)
        ctx.send_chunk(
            GenerateResponseChunk(
                role=Role.MODEL,
                content=[TextPart(text=chunk.text)],
            )
        )
    return (await res).text


async def main() -> None:
    """Main entry point for the basic Gemini sample.

    This function demonstrates basic usage of the Gemini model in the
    Genkit framework.
    """
    print(await generate_joke('banana'))
    print(await convert_with_tools(100.0))
    await draw_image('A panda playing soccer')
    print(await generate_structured_content('cookie'))
    await generate_long_joke('banana')


if __name__ == '__main__':
    asyncio.run(main())
