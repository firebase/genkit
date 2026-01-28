#!/usr/bin/env python3
"""
Typed ExecutablePrompt Example

This demonstrates how to use Output[T] with ai.define_prompt() to get
fully typed responses with autocomplete support.

NOTE: Requires a model plugin to run. Install google-genai plugin:
    pip install genkit-google-genai

Then set GOOGLE_API_KEY environment variable.
"""

from pydantic import BaseModel

from genkit.ai import Genkit, Output


# =============================================================================
# 1. Define your output schema as a Pydantic model
# =============================================================================


class Recipe(BaseModel):
    """A recipe with name, ingredients, and cooking steps."""

    name: str
    ingredients: list[str]
    steps: list[str]
    prep_time_minutes: int
    difficulty: str  # e.g., "easy", "medium", "hard"


# =============================================================================
# 2. Initialize Genkit (with a model plugin for real usage)
# =============================================================================

# For real usage, uncomment and configure a plugin:
# from genkit.plugins.google_genai import GoogleAI
# ai = Genkit(plugins=[GoogleAI()])

# For type-checking demo (no actual model calls):
ai = Genkit()


# =============================================================================
# 3. Define a prompt with typed output - BASIC
# =============================================================================

# Basic usage - just schema
recipe_prompt = ai.define_prompt(
    name='recipe',
    prompt='Create a detailed recipe for {dish}. Include exact measurements.',
    output=Output(schema=Recipe),  # <-- Type captured here!
)

# recipe_prompt is ExecutablePrompt[Recipe]
# All calls return GenerateResponseWrapper[Recipe]


# =============================================================================
# 4. Define a prompt with typed output - ALL OPTIONS
# =============================================================================

# Full usage - all Output fields
recipe_prompt_full = ai.define_prompt(
    name='recipe_constrained',
    prompt='Create a detailed recipe for {dish}. Include exact measurements.',
    output=Output(
        schema=Recipe,           # Required: Pydantic model for output type
        format='json',           # Output format (default: 'json')
        content_type='application/json',  # MIME type for response
        instructions=True,       # Include schema instructions in prompt
        constrained=True,        # Constrain model output strictly to schema
    ),
)


# =============================================================================
# 5. Use the typed prompt
# =============================================================================


async def main() -> None:
    """Demonstrate typed prompt usage."""
    # Call the prompt - response is typed!
    response = await recipe_prompt({'dish': 'chocolate chip cookies'})

    # response.output is Recipe (not Any!)
    # Full autocomplete works here:
    print(f'Recipe: {response.output.name}')
    print(f'Prep time: {response.output.prep_time_minutes} minutes')
    print(f'Difficulty: {response.output.difficulty}')
    print(f'Ingredients ({len(response.output.ingredients)}):')
    for ingredient in response.output.ingredients:
        print(f'  - {ingredient}')
    print(f'Steps ({len(response.output.steps)}):')
    for i, step in enumerate(response.output.steps, 1):
        print(f'  {i}. {step}')


async def main_streaming() -> None:
    """Demonstrate streaming with typed output."""
    # Stream the response
    result = recipe_prompt.stream({'dish': 'pasta carbonara'})

    # Stream chunks as they arrive
    print('Generating recipe...')
    async for chunk in result.stream:
        print(chunk.text, end='', flush=True)

    # Get the final typed response
    final = await result.response

    # final.output is still Recipe!
    print(f'\n\nFinal recipe: {final.output.name}')
    print(f'Difficulty: {final.output.difficulty}')


# =============================================================================
# 6. Type checking catches errors!
# =============================================================================


async def type_errors_demo() -> None:
    """These would be caught by pyright/mypy before runtime."""
    response = await recipe_prompt({'dish': 'pizza'})

    # ✅ These work - autocomplete shows all Recipe fields:
    _ = response.output.name
    _ = response.output.ingredients
    _ = response.output.steps
    _ = response.output.prep_time_minutes
    _ = response.output.difficulty

    # ❌ These would show errors in IDE (uncomment to see):
    # response.output.nonexistent_field  # Error: no attribute 'nonexistent_field'
    # response.output.name + 123  # Error: can't add str and int


# =============================================================================
# Run the demo
# =============================================================================

if __name__ == '__main__':
    import asyncio  # noqa: F401 - used when uncommenting the run lines

    print('Typed ExecutablePrompt Demo')
    print('=' * 50)
    print()
    print('To run with a real model:')
    print('1. pip install genkit-google-genai')
    print('2. export GOOGLE_API_KEY=your-key')
    print('3. Uncomment the GoogleAI plugin initialization')
    print()
    print('For now, this demonstrates the TYPE CHECKING features.')
    print('Open this file in your IDE and hover over variables')
    print('to see the inferred types!')
    print()

    # Uncomment to run with a real model:
    # asyncio.run(main())
    # asyncio.run(main_streaming())
