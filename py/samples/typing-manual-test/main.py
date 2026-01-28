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
"""

from __future__ import annotations

from pydantic import BaseModel

from genkit import Genkit

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
