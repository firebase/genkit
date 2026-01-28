"""MANUAL IDE TEST - Delete after testing.

Hover over 'result' on line 30 - should show UserOutput.
"""

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
    return UserOutput(greeting=f'Hello, {user.name}!', birth_year=2026 - user.age)


async def main() -> None:
    result = await greet_user(UserInput(name='Alice', age=30))
    #      ^^^^^^ HOVER HERE - should show "UserOutput"

    # Type result. and press Ctrl+Space - should show greeting, birth_year
    print(result.birth_year)
