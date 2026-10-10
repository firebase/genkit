#!/usr/bin/env python3
#
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""What app code gets back from lookup_model, lookup_tool, lookup_value, and define_value."""

import re
from collections.abc import Awaitable, Callable

import pytest

from genkit import ActionRunContext, FinishReason, Genkit, Message, ModelResponse, Operation, Part, Role, Tool
from genkit.middleware import BaseMiddleware, GenerateMiddlewareContext, ModelHookParams
from genkit.model import ModelRequest, model
from genkit.plugin_api import Action, ActionKind, ActionMetadata, Plugin

NextModel = Callable[[ModelHookParams, GenerateMiddlewareContext], Awaitable[ModelResponse]]


def _answer(text: str) -> ModelResponse:
    return ModelResponse(
        finish_reason=FinishReason.STOP,
        message=Message(role=Role.MODEL, content=[Part.from_text(text)]),
    )


def _define_answering_model(ai: Genkit, name: str, text: str) -> None:
    async def fn(request: ModelRequest, ctx: ActionRunContext) -> ModelResponse:
        return _answer(text)

    ai.define_model(name=name, fn=fn)


class LazyPlugin(Plugin):
    """Serves `lazy/fast` only through resolve, never from init."""

    name = 'lazy'

    async def init(self) -> list[Action]:
        return []

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        if action_type != ActionKind.MODEL or name != 'fast':
            return None

        async def fn(request: ModelRequest, ctx: ActionRunContext) -> ModelResponse:
            return _answer('from lazy fast')

        return model(name, fn)

    async def list_actions(self) -> list[ActionMetadata]:
        return []


@pytest.mark.asyncio
async def test_lookup_model_returns_registered_model_action() -> None:
    """`await ai.lookup_model('test/echo')` returns the model action, and running it gets that model's answer."""
    ai = Genkit()
    _define_answering_model(ai, 'test/echo', 'echoed')

    action = await ai.lookup_model('test/echo')

    assert action is not None
    assert action.name == 'test/echo'
    result = await action.run(ModelRequest(messages=[Message(role=Role.USER, content=[Part.from_text('hi')])]))
    assert isinstance(result.response, ModelResponse)
    assert result.response.text == 'echoed'


@pytest.mark.asyncio
async def test_lookup_model_unknown_name_returns_none() -> None:
    """`await ai.lookup_model('nope')` returns None instead of raising."""
    ai = Genkit()

    assert await ai.lookup_model('nope') is None


@pytest.mark.asyncio
async def test_lookup_model_resolves_plugin_model_not_yet_loaded() -> None:
    """A plugin model only reachable through the plugin's resolve comes back from `lookup_model` before any generate."""
    ai = Genkit(plugins=[LazyPlugin()])

    action = await ai.lookup_model('lazy/fast')

    assert action is not None
    assert action.name == 'lazy/fast'
    result = await action.run(ModelRequest(messages=[]))
    assert result.response.text == 'from lazy fast'


def test_define_value_then_lookup_value_returns_it() -> None:
    """A value stored with `ai.define_value(...)` comes back from `ai.lookup_value(...)` for the same kind and name."""
    ai = Genkit()
    catalog = {'id': 'banner', 'components': []}

    ai.define_value(kind='catalog', name='banner', value=catalog)

    assert ai.lookup_value(kind='catalog', name='banner') is catalog


def test_lookup_value_unknown_returns_none() -> None:
    """`ai.lookup_value(kind=..., name=...)` for nothing defined returns None."""
    ai = Genkit()
    ai.define_value(kind='catalog', name='banner', value={'id': 'banner'})

    assert ai.lookup_value(kind='catalog', name='other') is None
    assert ai.lookup_value(kind='other-kind', name='banner') is None


def test_define_value_same_name_twice_raises() -> None:
    """Defining the same kind and name twice raises ValueError and the first value stays."""
    ai = Genkit()
    ai.define_value(kind='catalog', name='banner', value='first')

    with pytest.raises(ValueError, match='already registered'):
        ai.define_value(kind='catalog', name='banner', value='second')

    assert ai.lookup_value(kind='catalog', name='banner') == 'first'


def test_define_value_requires_keywords() -> None:
    """`ai.define_value('k', 'n', v)` raises TypeError, so swapped kind and name can't store under the wrong key."""
    ai = Genkit()

    with pytest.raises(TypeError):
        ai.define_value('catalog', 'banner', 'value')  # type: ignore[misc]  # pyright: ignore[reportCallIssue]

    assert ai.lookup_value(kind='catalog', name='banner') is None
    assert ai.lookup_value(kind='banner', name='catalog') is None


def test_genkit_has_no_registry_attribute() -> None:
    """`ai.registry` raises AttributeError; app code uses the lookup and define methods."""
    ai = Genkit()

    with pytest.raises(AttributeError):
        _ = ai.registry  # type: ignore[attr-defined]  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.asyncio
async def test_middleware_ctx_has_no_registry_attribute() -> None:
    """`ctx.ai` has no public `registry` attribute."""
    ai = Genkit()
    _define_answering_model(ai, 'test/echo', 'from echo')
    has_registry: list[bool] = []

    class PeekRegistry(BaseMiddleware):
        async def wrap_model(
            self, params: ModelHookParams, ctx: GenerateMiddlewareContext, next_fn: NextModel
        ) -> ModelResponse:
            has_registry.append(hasattr(ctx.ai, 'registry'))
            return await next_fn(params, ctx)

    await ai.generate(model='test/echo', prompt='hi', use=[PeekRegistry()])

    assert has_registry == [False]


@pytest.mark.parametrize(
    ('kind', 'api'),
    [('middleware', 'define_middleware'), ('format', 'define_format'), ('defaultModel', 'Genkit(model=...)')],
)
def test_define_value_rejects_kinds_genkit_owns(kind: str, api: str) -> None:
    """`define_value` on a kind core reads with a fixed type raises and names the API to use."""
    ai = Genkit()

    with pytest.raises(ValueError, match=f'reserved; use {re.escape(api)}'):
        ai.define_value(kind=kind, name='audit', value={'not': 'the right type'})

    assert ai.lookup_value(kind=kind, name='audit') is None


def test_define_value_rejects_none() -> None:
    """`define_value(value=None)` raises, so None from `lookup_value` always means "not defined"."""
    ai = Genkit()

    with pytest.raises(ValueError, match='must not be None'):
        ai.define_value(kind='catalog', name='banner', value=None)

    ai.define_value(kind='catalog', name='banner', value='later')
    assert ai.lookup_value(kind='catalog', name='banner') == 'later'


@pytest.mark.asyncio
async def test_lookup_model_does_not_return_background_models() -> None:
    """A background model runs through `generate_operation`, so `lookup_model` returns None for it."""
    ai = Genkit()

    async def start(request: ModelRequest, ctx: ActionRunContext) -> Operation:
        return Operation(id='op-1')

    async def check(operation: Operation, ctx: ActionRunContext) -> Operation:
        return operation

    ai.define_background_model('veo', start=start, check=check)

    assert await ai.lookup_model('veo') is None


@pytest.mark.asyncio
async def test_lookup_tool_returns_a_callable_tool_with_the_same_definition() -> None:
    """`ai.lookup_tool('menu_price')` gives back a Tool that runs and describes itself like the decorated one."""
    ai = Genkit()

    @ai.tool()
    async def menu_price(dish: str) -> float:
        """Price of a dish in dollars."""
        return 14.5

    found = await ai.lookup_tool('menu_price')

    assert isinstance(found, Tool)
    assert found.definition() == menu_price.definition()
    assert (await found('ramen')).output == 14.5


@pytest.mark.asyncio
async def test_lookup_tool_unknown_name_returns_none() -> None:
    """A name nothing answers to returns None."""
    ai = Genkit()

    assert await ai.lookup_tool('missing') is None


@pytest.mark.asyncio
async def test_lookup_tool_finds_interrupts() -> None:
    """An interrupt is a tool, so `lookup_tool` finds it."""
    ai = Genkit()
    ai.define_interrupt('confirm_order', description='Ask the diner to confirm.')

    found = await ai.lookup_tool('confirm_order')

    assert found is not None
    assert found.name == 'confirm_order'
