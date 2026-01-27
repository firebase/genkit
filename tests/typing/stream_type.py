from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

from genkit import Genkit
from genkit.core.action import ActionRunContext

ai = Genkit()


@ai.flow()
async def streaming_flow(x: int, ctx: ActionRunContext) -> str:
    for i in range(x):
        ctx.send_chunk(f"chunk-{i}")
    return str(x)


async def main() -> None:
    chunks, final = streaming_flow.stream(5)
    typed_chunks = cast(AsyncIterator[str], chunks)

    async for chunk in typed_chunks:
        reveal_type(chunk)

    result = await final
    reveal_type(result.response)
