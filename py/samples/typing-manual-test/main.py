"""Manual IDE test for Phase 2 Generic Action typing.

Open this file in your IDE and verify autocomplete works.

AUTOMATED VERIFICATION PASSED:
- pyright confirms: Type of "result" is "UserOutput"
- pyright catches: Cannot access attribute "nonexistent" for class "UserOutput"
- pyright catches: Argument of type "str" cannot be assigned to "UserInput"

YOUR MANUAL CHECKS:
1. Put cursor after "result." on line 42 and press Ctrl+Space - see greeting, birth_year
2. Hover over "result" on line 40 - tooltip should show "UserOutput"
3. Uncomment line 52 - should show red squiggly error
4. Uncomment line 59 - should show red squiggly error

TYPED OUTPUT SCHEMAS (ai.generate):
5. Hover over "response.output" on line 105 - should show "Recipe"
6. Put cursor after "response.output." on line 107 - see name, ingredients, steps
"""

from __future__ import annotations

from pydantic import BaseModel

from genkit.ai import Genkit, Output

ai = Genkit()


class UserInput(BaseModel):
    name: str
    age: int


class UserOutput(BaseModel):
    greeting: str
    birth_year: int


@ai.flow()
async def greet_user(user: UserInput) -> UserOutput:
    return UserOutput(
        greeting=f'Hello, {user.name}!',
        birth_year=2026 - user.age,
    )


async def test_autocomplete() -> None:
    """TEST 1: Autocomplete - put cursor after 'result.' and press Ctrl+Space."""
    result = await greet_user(UserInput(name='Alice', age=30))

    # TEST: Type "result." below and press Ctrl+Space (Cmd+Space on Mac)
    # Autocomplete should show: greeting, birth_year

    # Hover over 'result' above - should show: UserOutput
    print(result.greeting)
    print(result.birth_year)


async def test_type_error_on_typo() -> None:
    """TEST 2: Uncomment the line below - should show red squiggly."""
    result = await greet_user(UserInput(name='Bob', age=25))

    # result.nonexistent  # UNCOMMENT: should show error


async def test_type_error_on_wrong_input() -> None:
    """TEST 3: Uncomment the line below - should show red squiggly."""

    # await greet_user("wrong")  # UNCOMMENT: should show error


async def test_return_type_preserved() -> None:
    """TEST 4: Verify return type methods work with autocomplete."""
    result = await greet_user(UserInput(name='Charlie', age=40))

    # Type "result.greeting." and press Ctrl+Space
    # Should show string methods like upper(), lower(), etc.
    upper_greeting: str = result.greeting.upper()
    year_str: str = str(result.birth_year)

    print(upper_greeting, year_str)


# =============================================================================
# TYPED OUTPUT SCHEMAS - Using Output[T] with ai.generate()
# =============================================================================


class Recipe(BaseModel):
    """A recipe schema for typed generation."""

    name: str
    ingredients: list[str]
    steps: list[str]
    prep_time_minutes: int


async def test_typed_output_schema() -> None:
    """TEST 5: Typed output from ai.generate() using Output[T].

    The key pattern is:
        response = await ai.generate(..., output=Output(schema=Recipe))

    This gives you:
        response.output  # Typed as Recipe (not Any!)

    YOUR MANUAL CHECKS:
    1. Hover over "response" - should show GenerateResponseWrapper[Recipe]
    2. Hover over "response.output" - should show Recipe
    3. Type "response.output." and press Ctrl+Space - should show:
       name, ingredients, steps, prep_time_minutes
    """
    # NOTE: Requires a model to actually run. Configure one first!
    # Example with GoogleAI:
    #   from genkit.plugins.google_genai import GoogleAI
    #   ai = Genkit(plugins=[GoogleAI()])

    response = await ai.generate(
        prompt='Create a recipe for chocolate chip cookies',
        output=Output(schema=Recipe),  # <-- The magic! Typed as Recipe
    )
    response.output

    # Now response.output is typed as Recipe, not Any!
    # Hover over response.output to see: Recipe
    # Type "response.output." to see autocomplete for name, ingredients, etc.
    print(f'Recipe: {response.output.name}')
    print(f'Ingredients: {response.output.ingredients}')
    print(f'Steps: {response.output.steps}')
    print(f'Prep time: {response.output.prep_time_minutes} minutes')

    # Try accessing a field that doesn't exist - should show red squiggly:
    # response.output.nonexistent  # UNCOMMENT: should show error


# For a runnable example, see test_typed_output_with_mock() below
async def test_typed_output_with_mock() -> None:
    """A runnable example demonstrating the typing (without a real model)."""
    # Simulate what ai.generate() returns with Output(schema=Recipe)
    # In reality, ai.generate() does this for you!

    mock_recipe = Recipe(
        name='Chocolate Chip Cookies',
        ingredients=['flour', 'butter', 'sugar', 'chocolate chips'],
        steps=['Mix ingredients', 'Form dough balls', 'Bake at 350°F'],
        prep_time_minutes=30,
    )

    # This is what you get from response.output:
    recipe: Recipe = mock_recipe  # Fully typed!

    # Autocomplete works - type "recipe." and see all fields:
    print(f'Recipe: {recipe.name}')
    print(f'Ingredients ({len(recipe.ingredients)}): {recipe.ingredients}')
    print(f'Steps ({len(recipe.steps)}): {recipe.steps}')
    print(f'Prep time: {recipe.prep_time_minutes} minutes')


# =============================================================================
# HOW IT WORKS
# =============================================================================
#
# Before (without Output[T]):
#   response = await ai.generate(prompt='...', output=Output(schema=Recipe))
#   response.output  # Type: Any - no autocomplete :(
#
# After (with Output[T]):
#   response = await ai.generate(prompt='...', output=Output(schema=Recipe))
#   response.output  # Type: Recipe - full autocomplete! :)
#
# The Output class preserves the generic type parameter through to the response,
# so the type checker knows exactly what type response.output will be.
# =============================================================================


# =============================================================================
# TYPED EXECUTABLE PROMPTS - Using Output[T] with ai.define_prompt()
# =============================================================================


class StoryOutput(BaseModel):
    """Output schema for a generated story."""

    title: str
    content: str
    moral: str


async def test_typed_executable_prompt() -> None:
    """TEST 6: Typed output from ExecutablePrompt using Output[T].

    The key pattern is:
        story_prompt = ai.define_prompt(
            name='story',
            prompt='Write a story about {topic}',
            output=Output(schema=StoryOutput),  # <-- Type captured here!
        )

        response = await story_prompt({'topic': 'friendship'})
        response.output  # Typed as StoryOutput (not Any!)

    YOUR MANUAL CHECKS:
    1. Hover over "story_prompt" - should show ExecutablePrompt[StoryOutput]
    2. Hover over "response" - should show GenerateResponseWrapper[StoryOutput]
    3. Hover over "response.output" - should show StoryOutput
    4. Type "response.output." and press Ctrl+Space - should show:
       title, content, moral
    """
    # Define a prompt with typed output (basic usage)
    story_prompt = ai.define_prompt(
        name='story',
        prompt='Write a story about {topic}',
        output=Output(schema=StoryOutput),  # <-- The magic! Type captured
    )

    # Define a prompt with ALL Output fields
    story_prompt_full = ai.define_prompt(
        name='story_full',
        prompt='Write a story about {topic}',
        output=Output(
            schema=StoryOutput,      # Required: the type for output
            format='json',           # Output format (default: 'json')
            content_type='application/json',  # MIME type
            instructions=True,       # Include formatting instructions in prompt
            constrained=True,        # Constrain model output to schema
        ),
    )

    # story_prompt is ExecutablePrompt[StoryOutput]
    # Hover over story_prompt to verify!

    # NOTE: Requires a model to actually run. Configure one first!
    response = await story_prompt({'topic': 'friendship'})

    # Now response.output is typed as StoryOutput, not Any!
    # Hover over response.output to see: StoryOutput
    print(f'Title: {response.output.title}')
    print(f'Content: {response.output.content}')
    print(f'Moral: {response.output.moral}')

    # Try accessing a field that doesn't exist - should show red squiggly:
    # response.output.nonexistent  # UNCOMMENT: should show error


async def test_typed_prompt_stream() -> None:
    """TEST 7: Streaming with typed ExecutablePrompt.

    Even when streaming, the final response is typed!
    """
    story_prompt = ai.define_prompt(
        name='story_stream',
        prompt='Write a story about {topic}',
        output=Output(schema=StoryOutput),
    )

    # Stream returns GenerateStreamResponse[StoryOutput]
    result = story_prompt.stream({'topic': 'adventure'})

    # The stream yields chunks (not typed - chunks are just text pieces)
    async for chunk in result.stream:
        print(chunk.text, end='')

    # But the final response IS typed!
    final = await result.response
    # final is GenerateResponseWrapper[StoryOutput]
    # final.output is StoryOutput
    print(f'\nMoral: {final.output.moral}')


# =============================================================================
# SUMMARY: Two ways to get typed output
# =============================================================================
#
# 1. ai.generate() with output=Output(schema=T):
#    response = await ai.generate(prompt='...', output=Output(schema=Recipe))
#    response.output  # Type: Recipe
#
# 2. ai.define_prompt() with output=Output(schema=T):
#    my_prompt = ai.define_prompt(prompt='...', output=Output(schema=Recipe))
#    response = await my_prompt(input)
#    response.output  # Type: Recipe
#
# Both patterns give you full autocomplete and type checking on response.output!
# =============================================================================
