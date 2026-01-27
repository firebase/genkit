from __future__ import annotations

from pydantic import BaseModel

from genkit import Genkit

ai = Genkit()


class UserOutput(BaseModel):
    name: str


@ai.tool()
def get_user(name: str) -> UserOutput:
    return UserOutput(name=name)


async def main() -> None:
    output = get_user("alice")
    upper: str = output.name.upper()
    assert upper
    reveal_type(output)
