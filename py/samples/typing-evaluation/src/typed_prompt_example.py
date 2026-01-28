#!/usr/bin/env python3
"""
Typed ExecutablePrompt Example

This demonstrates how to use Input[T] and Output[T] with ai.define_prompt() 
to get fully typed input AND output with autocomplete support.

This matches the JS SDK's ExecutablePrompt<I, O> pattern.

NOTE: Requires a model plugin to run. Install google-genai plugin:
    pip install genkit-google-genai

Then set GOOGLE_API_KEY environment variable.
"""

from pydantic import BaseModel

from genkit.ai import Genkit, Input, Output


# =============================================================================
# 1. Define your input and output schemas as Pydantic models
# =============================================================================


class RecipeInput(BaseModel):
    """Input schema for recipe generation."""

    dish: str
    servings: int = 4


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
# 3. Define a prompt with typed INPUT AND OUTPUT (Full JS Parity!)
# =============================================================================

# Both input and output typed - FULL JS PARITY!
recipe_prompt = ai.define_prompt(
    name='recipe',
    prompt='Create a detailed recipe for {dish} serving {servings} people.',
    input=Input(schema=RecipeInput),   # <-- Input type captured!
    output=Output(schema=Recipe),      # <-- Output type captured!
)

# recipe_prompt is ExecutablePrompt[RecipeInput, Recipe]
# - Input is type-checked when calling
# - Output is typed on response.output


# =============================================================================
# 4. Define a prompt with ALL OPTIONS
# =============================================================================

# Full usage - all Input and Output fields
recipe_prompt_full = ai.define_prompt(
    name='recipe_constrained',
    prompt='Create a detailed recipe for {dish} serving {servings} people.',
    input=Input(schema=RecipeInput),
    output=Output(
        schema=Recipe,           # Required: Pydantic model for output type
        format='json',           # Output format (default: 'json')
        content_type='application/json',  # MIME type for response
        instructions=True,       # Include schema instructions in prompt
        constrained=True,        # Constrain model output strictly to schema
    ),
)


# =============================================================================
# 5. Use the typed prompt - INPUT IS NOW TYPE CHECKED!
# =============================================================================


async def main() -> None:
    """Demonstrate typed prompt usage."""
    # Call the prompt - BOTH input and response are typed!
    
    # ✅ Input is type-checked - must be RecipeInput
    response = await recipe_prompt(RecipeInput(dish='chocolate chip cookies', servings=4))

    # ✅ Output is typed - response.output is Recipe (not Any!)
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
    """Demonstrate streaming with typed input/output."""
    # Stream the response - input is still type-checked!
    result = recipe_prompt.stream(RecipeInput(dish='pasta carbonara', servings=2))

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
# 6. Type checking catches input errors!
# =============================================================================


async def type_errors_demo() -> None:
    """These would be caught by pyright/mypy before runtime."""
    # ✅ These work - proper input type:
    _ = await recipe_prompt(RecipeInput(dish='pizza', servings=4))
    
    # ❌ These would show errors in IDE (uncomment to see):
    
    # Wrong input type - should be RecipeInput, not dict:
    # await recipe_prompt({'dish': 'pizza'})  # Error!
    
    # Missing required field:
    # await recipe_prompt(RecipeInput())  # Error: 'dish' is required
    
    # Wrong field name:
    # await recipe_prompt(RecipeInput(food='pizza'))  # Error: unexpected 'food'


# =============================================================================
# Run the demo
# =============================================================================

if __name__ == '__main__':
    import asyncio  # noqa: F811

    print('Typed ExecutablePrompt Demo')
    print('=' * 50)
    print()
    print('Now with FULL JS PARITY:')
    print('- Input[T] for typed input')
    print('- Output[T] for typed output')
    print('- ExecutablePrompt[InputT, OutputT]')
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
