#!/usr/bin/env python3
#
# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Tests for the action module."""

import pytest

from genkit.codec import dump_json
from genkit.core.action import (
    Action,
    ActionRunContext,
    create_action_key,
    parse_action_key,
    parse_plugin_name_from_action_name,
)
from genkit.core.action.types import ActionKind
from genkit.core.error import GenkitError


def test_action_enum_behaves_like_str() -> None:
    """Ensure the ActionType behaves like a string.

    This test verifies that the ActionType enum values can be compared
    directly with strings and that the correct variants are used.
    """
    assert ActionKind.CUSTOM == 'custom'
    assert ActionKind.EMBEDDER == 'embedder'
    assert ActionKind.EVALUATOR == 'evaluator'
    assert ActionKind.EXECUTABLE_PROMPT == 'executable-prompt'
    assert ActionKind.FLOW == 'flow'
    assert ActionKind.MODEL == 'model'
    assert ActionKind.PROMPT == 'prompt'
    assert ActionKind.RERANKER == 'reranker'
    assert ActionKind.RETRIEVER == 'retriever'
    assert ActionKind.TOOL == 'tool'
    assert ActionKind.UTIL == 'util'


def test_parse_action_key_valid() -> None:
    """Parse action key valid."""
    test_cases = [
        ('/prompt/my-prompt', (ActionKind.PROMPT, 'my-prompt')),
        ('/model/gpt-4', (ActionKind.MODEL, 'gpt-4')),
        (
            '/model/vertexai/gemini-1.0',
            (ActionKind.MODEL, 'vertexai/gemini-1.0'),
        ),
        ('/custom/test-action', (ActionKind.CUSTOM, 'test-action')),
        ('/flow/my-flow', (ActionKind.FLOW, 'my-flow')),
    ]

    for key, expected in test_cases:
        kind, name = parse_action_key(key)
        assert kind == expected[0]
        assert name == expected[1]


def test_parse_action_key_invalid_format() -> None:
    """Parse action key invalid format."""
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
    """Create action key."""
    assert create_action_key(ActionKind.CUSTOM, 'foo') == '/custom/foo'
    assert create_action_key(ActionKind.MODEL, 'foo') == '/model/foo'
    assert create_action_key(ActionKind.PROMPT, 'foo') == '/prompt/foo'
    assert create_action_key(ActionKind.RETRIEVER, 'foo') == '/retriever/foo'
    assert create_action_key(ActionKind.TOOL, 'foo') == '/tool/foo'
    assert create_action_key(ActionKind.UTIL, 'foo') == '/util/foo'


@pytest.mark.asyncio
async def test_define_sync_action() -> None:
    """Define and run a sync action."""

    def sync_foo():
        """A sync action that returns 'syncFoo'."""
        return 'syncFoo'

    action = Action(name='syncFoo', kind=ActionKind.CUSTOM, fn=sync_foo)

    assert (await action.arun()).response == 'syncFoo'
    assert sync_foo() == 'syncFoo'


@pytest.mark.asyncio
async def test_define_sync_action_with_input_without_type_annotation() -> None:
    """Define and run a sync action with input without type annotation."""

    def sync_foo(input):
        """A sync action that returns 'syncFoo' with an input."""
        return f'syncFoo {input}'

    action = Action(name='syncFoo', kind=ActionKind.CUSTOM, fn=sync_foo)

    assert (await action.arun('foo')).response == 'syncFoo foo'
    assert sync_foo('foo') == 'syncFoo foo'


@pytest.mark.asyncio
async def test_define_sync_action_with_input() -> None:
    """Define and run a sync action with input."""

    def sync_foo(input: str):
        """A sync action that returns 'syncFoo' with an input."""
        return f'syncFoo {input}'

    action = Action(name='syncFoo', kind=ActionKind.CUSTOM, fn=sync_foo)

    assert (await action.arun('foo')).response == 'syncFoo foo'
    assert sync_foo('foo') == 'syncFoo foo'


@pytest.mark.asyncio
async def test_define_sync_action_with_input_and_context() -> None:
    """Define and run a sync action with input and context."""

    def sync_foo(input: str, ctx: ActionRunContext):
        """A sync action that returns 'syncFoo' with an input and context."""
        return f'syncFoo {input} {ctx.context["foo"]}'

    action = Action(name='syncFoo', kind=ActionKind.CUSTOM, fn=sync_foo)

    assert (await action.arun('foo', context={'foo': 'bar'})).response == 'syncFoo foo bar'
    assert sync_foo('foo', ActionRunContext(context={'foo': 'bar'})) == 'syncFoo foo bar'


@pytest.mark.asyncio
async def test_define_sync_streaming_action() -> None:
    """Define and run a sync streaming action."""

    def sync_foo(input: str, ctx: ActionRunContext):
        """A sync action that returns 'syncFoo' with streaming output."""
        ctx.send_chunk('1')
        ctx.send_chunk('2')
        return 3

    action = Action(name='syncFoo', kind=ActionKind.CUSTOM, fn=sync_foo)

    chunks = []

    def on_chunk(c):
        chunks.append(c)

    assert (await action.arun('foo', context={'foo': 'bar'}, on_chunk=on_chunk)).response == 3
    assert chunks == ['1', '2']


@pytest.mark.asyncio
async def test_define_streaming_action_and_stream_it() -> None:
    """Define and stream a streaming action."""

    def sync_foo(input: str, ctx: ActionRunContext):
        """A sync action that returns 'syncFoo' with streaming output."""
        ctx.send_chunk('1')
        ctx.send_chunk('2')
        return 3

    action = Action(name='syncFoo', kind=ActionKind.CUSTOM, fn=sync_foo)

    chunks = []

    stream, response = action.stream('foo', context={'foo': 'bar'})
    async for chunk in stream:
        chunks.append(chunk)

    assert (await response) == 3
    assert chunks == ['1', '2']


@pytest.mark.asyncio
async def test_define_async_action() -> None:
    """Define and run an async action."""

    async def async_foo():
        """An async action that returns 'asyncFoo'."""
        return 'asyncFoo'

    action = Action(name='asyncFoo', kind=ActionKind.CUSTOM, fn=async_foo)

    assert (await action.arun()).response == 'asyncFoo'
    assert (await async_foo()) == 'asyncFoo'


@pytest.mark.asyncio
async def test_define_async_action_with_input() -> None:
    """Define and run an async action with input."""

    async def async_foo(input: str):
        """An async action that returns 'asyncFoo' with an input."""
        return f'asyncFoo {input}'

    action = Action(name='asyncFoo', kind=ActionKind.CUSTOM, fn=async_foo)

    assert (await action.arun('foo')).response == 'asyncFoo foo'
    assert (await async_foo('foo')) == 'asyncFoo foo'


@pytest.mark.asyncio
async def test_define_async_action_with_input_and_context() -> None:
    """Define and run async action with input and context."""

    async def async_foo(input: str, ctx: ActionRunContext):
        """An async action that returns 'syncFoo' with an input and context."""
        return f'syncFoo {input} {ctx.context["foo"]}'

    action = Action(name='syncFoo', kind=ActionKind.CUSTOM, fn=async_foo)

    assert (await action.arun('foo', context={'foo': 'bar'})).response == 'syncFoo foo bar'
    assert (await async_foo('foo', ActionRunContext(context={'foo': 'bar'}))) == 'syncFoo foo bar'


@pytest.mark.asyncio
async def test_define_async_streaming_action() -> None:
    """Define and run an async streaming action."""

    async def async_foo(input: str, ctx: ActionRunContext):
        """An async action that returns 'syncFoo' with streaming output."""
        ctx.send_chunk('1')
        ctx.send_chunk('2')
        return 3

    action = Action(name='syncFoo', kind=ActionKind.CUSTOM, fn=async_foo)

    chunks = []

    def on_chunk(c):
        chunks.append(c)

    assert (await action.arun('foo', context={'foo': 'bar'}, on_chunk=on_chunk)).response == 3
    assert chunks == ['1', '2']


def test_parse_plugin_name_from_action_name():
    """Parse plugin name from the action name."""
    assert parse_plugin_name_from_action_name('foo') is None
    assert parse_plugin_name_from_action_name('foo/bar') == 'foo'
    assert parse_plugin_name_from_action_name('foo/bar/baz') == 'foo'


@pytest.mark.asyncio
async def test_propagates_context_via_contextvar() -> None:
    """Context is properly propagated via contextvar."""

    async def foo(_: str | None, ctx: ActionRunContext):
        return dump_json(ctx.context)

    foo_action = Action(name='foo', kind=ActionKind.CUSTOM, fn=foo)

    async def bar():
        return (await foo_action.arun()).response

    bar_action = Action(name='bar', kind=ActionKind.CUSTOM, fn=bar)

    async def baz():
        return (await bar_action.arun()).response

    baz_action = Action(name='baz', kind=ActionKind.CUSTOM, fn=baz)

    first = baz_action.arun(context={'foo': 'bar'})
    second = baz_action.arun(context={'bar': 'baz'})

    assert (await second).response == '{"bar": "baz"}'
    assert (await first).response == '{"foo": "bar"}'


@pytest.mark.asyncio
async def test_sync_action_raises_errors() -> None:
    """Sync action raises error with necessary metadata."""

    def sync_foo(_: str | None, ctx: ActionRunContext):
        raise Exception('oops')

    action = Action(name='fooAction', kind=ActionKind.CUSTOM, fn=sync_foo)

    with pytest.raises(GenkitError, match=r'.*Error while running action fooAction.*') as e:
        await action.arun()

    assert 'stack' in e.value.details
    assert 'trace_id' in e.value.details
    assert str(e.value.cause) == 'oops'


@pytest.mark.asyncio
async def test_async_action_raises_errors() -> None:
    """Async action raises error with necessary metadata."""

    async def async_foo(_: str | None, ctx: ActionRunContext):
        raise Exception('oops')

    action = Action(name='fooAction', kind=ActionKind.CUSTOM, fn=async_foo)

    with pytest.raises(GenkitError, match=r'.*Error while running action fooAction.*') as e:
        await action.arun()

    assert 'stack' in e.value.details
    assert 'trace_id' in e.value.details
    assert str(e.value.cause) == 'oops'
