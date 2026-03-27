# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for tool restart builder and run_tool_after_restart."""

import pytest

from genkit import ActionKind, Genkit
from genkit._ai._generate import run_tool_after_restart
from genkit._ai._tools import (
    Interrupt,
    ToolRunContext,
    _tool_original_input,
    _tool_resumed_metadata,
)
from genkit._core._error import GenkitError
from genkit._core._typing import ToolRequest, ToolRequestPart


@pytest.mark.asyncio
async def test_restart_sets_resumed_metadata_and_strips_interrupt() -> None:
    """``tool.restart`` → TRP.metadata.resumed plus ``interrupt`` removed; input unchanged when replace is None."""
    ai = Genkit()

    @ai.tool(name='pay')
    async def pay(inp: dict) -> str:  # noqa: ARG001
        return 'ok'

    interrupt_trp = ToolRequestPart(
        tool_request=ToolRequest(name='pay', ref='r1', input={'amount': 10}),
        metadata={'interrupt': {'reason': 'hold'}},
    )
    out = pay.restart(None, interrupt=interrupt_trp, resumed_metadata={'k': 'v'})
    assert isinstance(out, ToolRequestPart)
    assert out.metadata is not None
    assert out.metadata.get('resumed') == {'k': 'v'}
    assert 'interrupt' not in out.metadata
    assert out.tool_request.input == {'amount': 10}


@pytest.mark.asyncio
async def test_restart_replace_input_sets_replaced_input() -> None:
    """Restart with new input sets ``replacedInput`` to prior input and updates ``tool_request.input``."""
    ai = Genkit()

    @ai.tool(name='pay')
    async def pay(inp: dict) -> str:  # noqa: ARG001
        return 'ok'

    interrupt_trp = ToolRequestPart(
        tool_request=ToolRequest(name='pay', ref='r1', input={'amount': 10}),
        metadata={'interrupt': True},
    )
    out = pay.restart({'amount': 99}, interrupt=interrupt_trp, resumed_metadata={'by': 'u'})
    assert isinstance(out, ToolRequestPart)
    assert out.metadata is not None
    assert out.metadata.get('replacedInput') == {'amount': 10}
    assert out.tool_request.input == {'amount': 99}
    assert out.metadata.get('resumed') == {'by': 'u'}


@pytest.mark.asyncio
async def test_restart_resumed_defaults_to_true() -> None:
    """When ``resumed_metadata=None``, restart TRP sets ``metadata.resumed`` to True."""
    ai = Genkit()

    @ai.tool(name='pay')
    async def pay(inp: dict) -> str:  # noqa: ARG001
        return 'ok'

    interrupt_trp = ToolRequestPart(
        tool_request=ToolRequest(name='pay', ref='r1', input={}),
        metadata={'interrupt': True},
    )
    out = pay.restart(None, interrupt=interrupt_trp, resumed_metadata=None)
    assert isinstance(out, ToolRequestPart)
    assert out.metadata is not None
    assert out.metadata.get('resumed') is True


@pytest.mark.asyncio
async def test_run_tool_after_restart_resumed_true_maps_to_empty_dict_in_context() -> None:
    """``run_tool_after_restart``: ``metadata.resumed is True`` → ``ToolRunContext.resumed_metadata`` is ``{}``."""
    ai = Genkit()
    captured: list[tuple[dict | None, object | None]] = []

    @ai.tool(name='t2')
    async def t2(inp: dict, ctx: ToolRunContext) -> str:  # noqa: ARG001
        captured.append((ctx.resumed_metadata, ctx.original_input))
        return 'done'

    action = await ai.registry.resolve_action(kind=ActionKind.TOOL, name='t2')
    assert action is not None

    restart_trp = ToolRequestPart(
        tool_request=ToolRequest(name='t2', ref='x', input={'q': 1}),
        metadata={'resumed': True},
    )
    await run_tool_after_restart(action, restart_trp)
    assert len(captured) == 1
    assert captured[0][0] == {}
    assert captured[0][1] is None


@pytest.mark.asyncio
async def test_run_tool_after_restart_resumed_dict() -> None:
    """Restart TRP with ``metadata.resumed`` dict is passed through to ``ToolRunContext.resumed_metadata``."""
    ai = Genkit()
    captured: list[dict | None] = []

    @ai.tool(name='t2')
    async def t2(inp: dict, ctx: ToolRunContext) -> str:  # noqa: ARG001
        captured.append(ctx.resumed_metadata)
        return 'done'

    action = await ai.registry.resolve_action(kind=ActionKind.TOOL, name='t2')
    assert action is not None

    restart_trp = ToolRequestPart(
        tool_request=ToolRequest(name='t2', ref='x', input={}),
        metadata={'resumed': {'by': 'x'}},
    )
    await run_tool_after_restart(action, restart_trp)
    assert captured == [{'by': 'x'}]


@pytest.mark.asyncio
async def test_run_tool_after_restart_replaced_input() -> None:
    """``replacedInput`` on TRP sets tool input from current request and ``original_input`` from prior."""
    ai = Genkit()
    captured: list[tuple[object, object | None]] = []

    @ai.tool(name='t2')
    async def t2(inp: dict, ctx: ToolRunContext) -> str:  # noqa: ARG001
        captured.append((inp, ctx.original_input))
        return 'done'

    action = await ai.registry.resolve_action(kind=ActionKind.TOOL, name='t2')
    assert action is not None

    restart_trp = ToolRequestPart(
        tool_request=ToolRequest(name='t2', ref='x', input={'new': True}),
        metadata={'resumed': True, 'replacedInput': {'old': True}},
    )
    await run_tool_after_restart(action, restart_trp)
    assert len(captured) == 1
    assert captured[0][0] == {'new': True}
    assert captured[0][1] == {'old': True}


@pytest.mark.asyncio
async def test_run_tool_after_restart_resets_contextvars() -> None:
    """After ``run_tool_after_restart`` returns, resume ContextVars are cleared (no leak between runs)."""
    ai = Genkit()

    @ai.tool(name='t2')
    async def t2(inp: dict, ctx: ToolRunContext) -> str:  # noqa: ARG001
        return 'done'

    action = await ai.registry.resolve_action(kind=ActionKind.TOOL, name='t2')
    assert action is not None

    restart_trp = ToolRequestPart(
        tool_request=ToolRequest(name='t2', ref='x', input={}),
        metadata={'resumed': True},
    )
    await run_tool_after_restart(action, restart_trp)
    assert _tool_resumed_metadata.get() is None
    assert _tool_original_input.get() is None


@pytest.mark.asyncio
async def test_run_tool_after_restart_nested_interrupt_raises() -> None:
    """Tool raising ``Interrupt`` during a restart run raises ``GenkitError`` (nested interrupt unsupported)."""
    ai = Genkit()

    @ai.tool(name='t2')
    async def t2(inp: dict, ctx: ToolRunContext) -> str:  # noqa: ARG001
        raise Interrupt()

    action = await ai.registry.resolve_action(kind=ActionKind.TOOL, name='t2')
    assert action is not None

    restart_trp = ToolRequestPart(
        tool_request=ToolRequest(name='t2', ref='x', input={}),
        metadata={'resumed': True},
    )
    with pytest.raises(GenkitError) as ei:
        await run_tool_after_restart(action, restart_trp)
    msg = ei.value.original_message.lower()
    assert 'restart' in msg or 'nested' in msg or 'not supported' in msg
