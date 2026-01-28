from __future__ import annotations

from pydantic import BaseModel

from genkit import Genkit

ai = Genkit()


class UserInput(BaseModel):
    name: str


@ai.flow()
async def greet(user: UserInput) -> str:
    return f'Hello, {user.name}'


async def main() -> None:
    result = await greet(UserInput(name='alice'))
    reveal_type(result)
