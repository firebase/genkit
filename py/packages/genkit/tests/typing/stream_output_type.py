"""Test that generate_stream() preserves Output[T] type information."""

from __future__ import annotations

from pydantic import BaseModel

from genkit import Genkit, Output


class Recipe(BaseModel):
    name: str
    ingredients: list[str]


ai = Genkit()


async def test_stream_typed_output() -> None:
    """Verify generate_stream with Output[T] returns properly typed future."""
    stream, future = ai.generate_stream(
        prompt='Give me a pasta recipe',
        output=Output(schema=Recipe),
    )

    # The future should resolve to GenerateResponseWrapper[Recipe]
    response = await future

    # response.output should be typed as Recipe
    # This line should type-check correctly:
    recipe_name: str = response.output.name
    ingredients: list[str] = response.output.ingredients

    reveal_type(response.output)

    # Consume the stream
    async for _chunk in stream:
        pass
