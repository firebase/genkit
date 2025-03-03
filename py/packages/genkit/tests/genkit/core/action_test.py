#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the action module."""

import pytest
from genkit.core.action import (
    Action,
    ActionKind,
    ActionRunContext,
    create_action_key,
    parse_action_key,
    parse_plugin_name_from_action_name,
)


def test_action_enum_behaves_like_str() -> None:
    """Ensure the ActionType behaves like a string.

    This test verifies that the ActionType enum values can be compared
    directly with strings and that the correct variants are used.
    """
    assert ActionKind.CHATLLM == 'chat-llm'
    assert ActionKind.CUSTOM == 'custom'
    assert ActionKind.EMBEDDER == 'embedder'
    assert ActionKind.EVALUATOR == 'evaluator'
    assert ActionKind.FLOW == 'flow'
    assert ActionKind.INDEXER == 'indexer'
    assert ActionKind.MODEL == 'model'
    assert ActionKind.PROMPT == 'prompt'
    assert ActionKind.RETRIEVER == 'retriever'
    assert ActionKind.TEXTLLM == 'text-llm'
    assert ActionKind.TOOL == 'tool'
    assert ActionKind.UTIL == 'util'


def test_parse_action_key_valid() -> None:
    """Test valid inputs."""
    test_cases = [
        ('/prompt/my-prompt', (ActionKind.PROMPT, 'my-prompt')),
        ('/model/gpt-4', (ActionKind.MODEL, 'gpt-4')),
        ('/custom/test-action', (ActionKind.CUSTOM, 'test-action')),
        ('/flow/my-flow', (ActionKind.FLOW, 'my-flow')),
    ]

    for key, expected in test_cases:
        kind, name = parse_action_key(key)
        assert kind == expected[0]
        assert name == expected[1]


def test_parse_action_key_invalid_format() -> None:
    """Test invalid formats."""
    invalid_keys = [
        'invalid_key',  # Missing separator
        '/missing-kind',  # Missing kind
        'missing-name/',  # Missing name
        '',  # Empty string
        '/',  # Just separator
    ]

    for key in invalid_keys:
        with pytest.raises(ValueError, match='Invalid action key format'):
            parse_action_key(key)


def test_create_action_key() -> None:
    """Test that create_action_key returns the correct action key."""
    assert create_action_key(ActionKind.CUSTOM, 'foo') == '/custom/foo'
    assert create_action_key(ActionKind.MODEL, 'foo') == '/model/foo'
    assert create_action_key(ActionKind.PROMPT, 'foo') == '/prompt/foo'
    assert create_action_key(ActionKind.RETRIEVER, 'foo') == '/retriever/foo'
    assert create_action_key(ActionKind.TEXTLLM, 'foo') == '/text-llm/foo'
    assert create_action_key(ActionKind.TOOL, 'foo') == '/tool/foo'
    assert create_action_key(ActionKind.UTIL, 'foo') == '/util/foo'


@pytest.mark.asyncio
async def test_define_sync_action() -> None:
    """Test that a sync action can be defined and run."""

    def syncFoo():
        """A sync action that returns 'syncFoo'."""
        return 'syncFoo'

    syncFooAction = Action(name='syncFoo', kind=ActionKind.CUSTOM, fn=syncFoo)

    assert (await syncFooAction.arun()).response == 'syncFoo'
    assert syncFoo() == 'syncFoo'


@pytest.mark.asyncio
@pytest.mark.skip('bug, action ignores args without type annotation')
async def test_define_sync_action_with_input_without_type_annotation() -> None:
    """Test that a sync action can be defined and run with an input without a type annotation."""

    def syncFoo(input):
        """A sync action that returns 'syncFoo' with an input."""
        return f'syncFoo {input}'

    syncFooAction = Action(name='syncFoo', kind=ActionKind.CUSTOM, fn=syncFoo)

    assert (await syncFooAction.arun('foo')).response == 'syncFoo foo'
    assert syncFoo('foo') == 'syncFoo foo'


@pytest.mark.asyncio
async def test_define_sync_action_with_input() -> None:
    """Test that a sync action can be defined and run with an input."""

    def syncFoo(input: str):
        """A sync action that returns 'syncFoo' with an input."""
        return f'syncFoo {input}'

    syncFooAction = Action(name='syncFoo', kind=ActionKind.CUSTOM, fn=syncFoo)

    assert (await syncFooAction.arun('foo')).response == 'syncFoo foo'
    assert syncFoo('foo') == 'syncFoo foo'


@pytest.mark.asyncio
async def test_define_sync_action_with_input_and_context() -> None:
    """Test that a sync action can be defined and run with an input and context."""

    def syncFoo(input: str, ctx: ActionRunContext):
        """A sync action that returns 'syncFoo' with an input and context."""
        return f'syncFoo {input} {ctx.context["foo"]}'

    syncFooAction = Action(name='syncFoo', kind=ActionKind.CUSTOM, fn=syncFoo)

    assert (
        await syncFooAction.arun('foo', context={'foo': 'bar'})
    ).response == 'syncFoo foo bar'
    assert (
        syncFoo('foo', ActionRunContext(context={'foo': 'bar'}))
        == 'syncFoo foo bar'
    )


@pytest.mark.asyncio
async def test_define_sync_streaming_action() -> None:
    """Test that a sync action can be defined and run with streaming output."""

    def syncFoo(input: str, ctx: ActionRunContext):
        """A sync action that returns 'syncFoo' with streaming output."""
        ctx.send_chunk('1')
        ctx.send_chunk('2')
        return 3

    syncFooAction = Action(name='syncFoo', kind=ActionKind.CUSTOM, fn=syncFoo)

    chunks = []

    def on_chunk(c):
        chunks.append(c)

    assert (
        await syncFooAction.arun(
            'foo', context={'foo': 'bar'}, on_chunk=on_chunk
        )
    ).response == 3
    assert chunks == ['1', '2']


@pytest.mark.asyncio
async def test_define_async_action() -> None:
    """Test that an async action can be defined and run."""

    async def asyncFoo():
        """An async action that returns 'asyncFoo'."""
        return 'asyncFoo'

    asyncFooAction = Action(
        name='asyncFoo', kind=ActionKind.CUSTOM, fn=asyncFoo
    )

    assert (await asyncFooAction.arun()).response == 'asyncFoo'
    assert (await asyncFoo()) == 'asyncFoo'


@pytest.mark.asyncio
async def test_define_async_action_with_input() -> None:
    """Test that an async action can be defined and run with an input."""

    async def asyncFoo(input: str):
        """An async action that returns 'asyncFoo' with an input."""
        return f'syncFoo {input}'

    asyncFooAction = Action(name='syncFoo', kind=ActionKind.CUSTOM, fn=asyncFoo)

    assert (await asyncFooAction.arun('foo')).response == 'syncFoo foo'
    assert (await asyncFoo('foo')) == 'syncFoo foo'


@pytest.mark.asyncio
async def test_define_async_action_with_input_and_context() -> None:
    """Test that an async action can be defined and run with an input and context."""

    async def asyncFoo(input: str, ctx: ActionRunContext):
        """An async action that returns 'syncFoo' with an input and context."""
        return f'syncFoo {input} {ctx.context["foo"]}'

    asyncFooAction = Action(name='syncFoo', kind=ActionKind.CUSTOM, fn=asyncFoo)

    assert (
        await asyncFooAction.arun('foo', context={'foo': 'bar'})
    ).response == 'syncFoo foo bar'
    assert (
        await asyncFoo('foo', ActionRunContext(context={'foo': 'bar'}))
    ) == 'syncFoo foo bar'


@pytest.mark.asyncio
async def test_define_async_streaming_action() -> None:
    """Test that an async action can be defined and run with streaming output."""

    async def asyncFoo(input: str, ctx: ActionRunContext):
        """An async action that returns 'syncFoo' with streaming output."""
        ctx.send_chunk('1')
        ctx.send_chunk('2')
        return 3

    asyncFooAction = Action(name='syncFoo', kind=ActionKind.CUSTOM, fn=asyncFoo)

    chunks = []

    def on_chunk(c):
        chunks.append(c)

    assert (
        await asyncFooAction.arun(
            'foo', context={'foo': 'bar'}, on_chunk=on_chunk
        )
    ).response == 3
    assert chunks == ['1', '2']


def test_parse_plugin_name_from_action_name():
    assert parse_plugin_name_from_action_name('foo') == None
    assert parse_plugin_name_from_action_name('foo/bar') == 'foo'
    assert parse_plugin_name_from_action_name('foo/bar/baz') == 'foo'
