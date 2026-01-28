from __future__ import annotations

from pydantic import BaseModel

from genkit import Genkit

ai = Genkit()


class UserInput(BaseModel):
    name: str


@ai.flow()
async def stringify(x: int) -> str:
    return str(x)


@ai.flow()
async def greet(user: UserInput) -> str:
    return f'Hello, {user.name}'


async def negative_tests() -> None:
    result = await stringify(123)

    wrong_type: int = result

    result.nonexistent

    await greet('alice')
