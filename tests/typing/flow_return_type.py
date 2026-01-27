from __future__ import annotations

from pydantic import BaseModel

from genkit import Genkit

ai = Genkit()


@ai.flow()
async def stringify(x: int) -> str:
    return str(x)


class UserInput(BaseModel):
    name: str


@ai.flow()
async def greet(user: UserInput) -> str:
    return f"Hello, {user.name}"


async def main() -> None:
    result = await stringify(123)
    length: int = len(result)
    assert length >= 0
    reveal_type(result)
