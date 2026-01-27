from __future__ import annotations

from genkit import Genkit

ai = Genkit()


@ai.flow()
async def hello_world() -> str:
    return "Hello, World!"


async def main() -> None:
    result = await hello_world()
    reveal_type(result)
