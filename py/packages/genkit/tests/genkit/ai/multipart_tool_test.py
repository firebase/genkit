#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for multipart tool support (tool.v2 action kind)."""

from typing import cast

import pytest

from genkit.ai import Genkit
from genkit.core.action.types import ActionKind


@pytest.mark.asyncio
async def test_regular_tool_registers_both_kinds() -> None:
    """A non-multipart tool registers under both 'tool' and 'tool.v2'."""
    ai = Genkit()

    @ai.tool()
    def add(x: int) -> int:
        """Add one."""
        return x + 1

    tool_action = await ai.registry.resolve_action(ActionKind.TOOL, 'add')
    if tool_action is None:
        raise AssertionError('Expected tool action registered under ActionKind.TOOL')

    v2_action = await ai.registry.resolve_action(ActionKind.TOOL_V2, 'add')
    if v2_action is None:
        raise AssertionError('Expected tool.v2 wrapper action registered under ActionKind.TOOL_V2')


@pytest.mark.asyncio
async def test_regular_tool_v2_wrapper_wraps_output() -> None:
    """The tool.v2 wrapper for a regular tool wraps output in {output: result}."""
    ai = Genkit()

    @ai.tool()
    def double(x: int) -> int:
        """Double."""
        return x * 2

    v2_action = await ai.registry.resolve_action(ActionKind.TOOL_V2, 'double')
    if v2_action is None:
        raise AssertionError('Expected tool.v2 wrapper')

    result = await v2_action.arun(5)
    if not isinstance(result.response, dict):
        raise AssertionError(f'Expected dict response, got {type(result.response).__name__}')
    if result.response.get('output') != 10:
        raise AssertionError(f'Expected output=10, got {result.response}')


@pytest.mark.asyncio
async def test_multipart_tool_registers_as_tool_v2() -> None:
    """A multipart tool is registered under 'tool.v2' only."""
    ai = Genkit()

    @ai.tool(multipart=True)
    def rich_tool(query: str) -> dict:
        """Return rich content."""
        return {'output': f'result for {query}', 'content': [{'text': 'extra'}]}

    # Should be under tool.v2
    v2_action = await ai.registry.resolve_action(ActionKind.TOOL_V2, 'rich_tool')
    if v2_action is None:
        raise AssertionError('Expected multipart tool registered under ActionKind.TOOL_V2')

    # Should NOT be under tool
    tool_action = await ai.registry.resolve_action(ActionKind.TOOL, 'rich_tool')
    if tool_action is not None:
        raise AssertionError('Multipart tool should NOT be registered under ActionKind.TOOL')


@pytest.mark.asyncio
async def test_multipart_tool_metadata() -> None:
    """Multipart tool has correct metadata: type='tool.v2' and tool.multipart=True."""
    ai = Genkit()

    @ai.tool(multipart=True)
    def my_multipart(x: int) -> dict:
        """Multipart."""
        return {'output': x}

    v2_action = await ai.registry.resolve_action(ActionKind.TOOL_V2, 'my_multipart')
    if v2_action is None:
        raise AssertionError('Expected multipart tool')

    if v2_action.metadata.get('type') != 'tool.v2':
        raise AssertionError(f'Expected type="tool.v2", got {v2_action.metadata.get("type")!r}')

    tool_meta = v2_action.metadata.get('tool')
    if not isinstance(tool_meta, dict):
        raise AssertionError(f'Expected dict for tool metadata, got {type(tool_meta).__name__}')
    tool_meta_dict = cast(dict[str, object], tool_meta)
    if tool_meta_dict.get('multipart') is not True:
        raise AssertionError(f'Expected tool.multipart=True, got {tool_meta!r}')


@pytest.mark.asyncio
async def test_multipart_tool_execution() -> None:
    """Multipart tool can be executed and returns the function result directly."""
    ai = Genkit()

    @ai.tool(multipart=True)
    def search(query: str) -> dict:
        """Search."""
        return {'output': 'found it', 'content': [{'text': f'Details for {query}'}]}

    v2_action = await ai.registry.resolve_action(ActionKind.TOOL_V2, 'search')
    if v2_action is None:
        raise AssertionError('Expected multipart tool')

    result = await v2_action.arun('test query')
    response = result.response
    if not isinstance(response, dict):
        raise AssertionError(f'Expected dict, got {type(response).__name__}')
    if response.get('output') != 'found it':
        raise AssertionError(f'Expected output="found it", got {response.get("output")!r}')


@pytest.mark.asyncio
async def test_regular_tool_metadata_type() -> None:
    """Regular (non-multipart) tool has metadata type='tool'."""
    ai = Genkit()

    @ai.tool()
    def simple(x: int) -> int:
        """Simple."""
        return x

    tool_action = await ai.registry.resolve_action(ActionKind.TOOL, 'simple')
    if tool_action is None:
        raise AssertionError('Expected tool action')

    if tool_action.metadata.get('type') != 'tool':
        raise AssertionError(f'Expected type="tool", got {tool_action.metadata.get("type")!r}')
