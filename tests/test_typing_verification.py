from __future__ import annotations

import pytest
from pydantic import BaseModel

from genkit import Genkit
from genkit.core.action import Action, ActionRunContext
from genkit.core.action.types import ActionKind


class UserOutput(BaseModel):
    name: str


class UserInput(BaseModel):
    name: str


@pytest.mark.asyncio
async def test_flow_return_type() -> None:
    """Test 1: Flow return type is preserved at runtime."""
    ai = Genkit()

    @ai.flow()
    async def stringify(x: int) -> str:
        return str(x)

    result = await stringify(123)
    assert result == '123'
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_tool_return_type() -> None:
    """Test 2: Tool return type is preserved at runtime."""
    ai = Genkit()

    @ai.tool()
    def get_user(name: str) -> UserOutput:
        return UserOutput(name=name)

    output = get_user('alice')
    assert output.name == 'alice'
    assert isinstance(output, UserOutput)


def test_action_response_type() -> None:
    """Test 3: ActionResponse preserves OutputT at runtime."""

    def int_to_str(x: int) -> str:
        return str(x)

    action: Action[int, str] = Action(
        kind=ActionKind.FLOW,
        name='int_to_str',
        fn=int_to_str,
    )
    result = action.run(7)
    assert result.response == '7'
    assert isinstance(result.response, str)


@pytest.mark.asyncio
async def test_streaming() -> None:
    """Test 4: Streaming returns chunks and final result."""
    ai = Genkit()
    chunks_received: list[str] = []

    @ai.flow()
    async def streaming_flow(x: int, ctx: ActionRunContext) -> str:
        for i in range(x):
            ctx.send_chunk(f'chunk-{i}')
        return str(x)

    stream_iter, final_future = streaming_flow.stream(3)

    async for chunk in stream_iter:
        chunks_received.append(str(chunk))

    final = await final_future
    assert final.response == '3'
    assert chunks_received == ['chunk-0', 'chunk-1', 'chunk-2']


@pytest.mark.asyncio
async def test_no_input_flow() -> None:
    """Test 6: Flows with no input work correctly."""
    ai = Genkit()

    @ai.flow()
    async def hello_world() -> str:
        return 'Hello, World!'

    result = await hello_world()
    assert result == 'Hello, World!'


def test_unparameterized_action() -> None:
    """Test 8: Bare Action works (backwards compat)."""

    def identity(x: object) -> object:
        return x

    action = Action(
        kind=ActionKind.FLOW,
        name='identity',
        fn=identity,
    )
    result = action.run('test')
    assert result.response == 'test'
