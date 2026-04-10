# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

# Note: ty type checker has a known limitation with StrEnum where it sees
# enum members as Literal values instead of the enum type. We use ty: ignore
# comments to suppress these false positives. See: https://github.com/python/typing/issues/1367

"""Tests for AI plugin functionality."""

from collections.abc import Awaitable, Callable

import pytest

from genkit import Genkit, GenkitError, Message, ModelResponse, Part, Plugin, Role, TextPart, middleware_plugin
from genkit._core._action import Action, ActionMetadata, ActionRunContext
from genkit._core._middleware._base import BaseMiddleware, MiddlewareFnOptions
from genkit._core._model import ModelHookParams, ModelRequest
from genkit._core._registry import ActionKind
from genkit._core._typing import FinishReason, MiddlewareRef
from genkit.middleware import GenerateMiddleware, generate_middleware


class AsyncResolveOnlyPlugin(Plugin):
    """Plugin that only implements async resolve."""

    name = 'async-resolve-only'

    async def init(self) -> list[Action]:
        """Initialize the plugin."""
        # Intentionally register nothing eagerly.
        return []

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        """Resolve an action."""
        if action_type != ActionKind.MODEL:
            return None
        if name != f'{self.name}/lazy-model':
            return None

        async def _generate(req: ModelRequest, ctx: ActionRunContext) -> ModelResponse:
            return ModelResponse(
                message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='OK: lazy'))]),
                finish_reason=FinishReason.STOP,
            )

        return Action(
            kind=ActionKind.MODEL,
            name=name,
            fn=_generate,
        )

    async def list_actions(self) -> list[ActionMetadata]:
        """List available actions."""
        return [
            ActionMetadata(
                kind=ActionKind.MODEL,
                name=f'{self.name}/lazy-model',
            )
        ]


class AsyncInitPlugin(Plugin):
    """Plugin that implements async init."""

    name = 'async-init-plugin'

    async def init(self) -> list[Action]:
        """Initialize the plugin."""
        action = await self.resolve(ActionKind.MODEL, f'{self.name}/init-model')
        return [action] if action else []

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        """Resolve an action."""
        if action_type != ActionKind.MODEL:
            return None
        if name != f'{self.name}/init-model':
            return None

        async def _generate(req: ModelRequest, ctx: ActionRunContext) -> ModelResponse:
            return ModelResponse(
                message=Message(role=Role.MODEL, content=[Part(root=TextPart(text='OK: resolve'))]),
                finish_reason=FinishReason.STOP,
            )

        return Action(
            kind=ActionKind.MODEL,
            name=name,
            fn=_generate,
        )

    async def list_actions(self) -> list[ActionMetadata]:
        """List available actions."""
        return [
            ActionMetadata(
                kind=ActionKind.MODEL,
                name=f'{self.name}/init-model',
            )
        ]


class _NoopPluginMiddleware(BaseMiddleware):
    """Minimal middleware for plugin registration tests."""

    async def wrap_model(
        self,
        params: ModelHookParams,
        next_fn: Callable[[ModelHookParams], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        return await next_fn(params)


class _ClassMetaMiddleware(BaseMiddleware):
    """Registered via ``generate_middleware(MyClass)`` using class attributes."""

    name = 'class_meta_mw'
    description = 'from class attrs'

    async def wrap_model(
        self,
        params: ModelHookParams,
        next_fn: Callable[[ModelHookParams], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        return await next_fn(params)


class PluginWithMiddleware(Plugin):
    """Plugin that contributes ``generate_middleware`` definitions."""

    name = 'plugin-with-mw'

    async def init(self) -> list[Action]:
        return []

    async def resolve(self, action_type: ActionKind, name: str) -> Action | None:
        return None

    async def list_actions(self) -> list[ActionMetadata]:
        return []

    def generate_middleware(self) -> list[GenerateMiddleware]:
        def _factory(_opts: MiddlewareFnOptions) -> BaseMiddleware:
            return _NoopPluginMiddleware()

        return [
            GenerateMiddleware(
                name=f'{self.name}_noop',
                factory=_factory,
                description='noop plugin middleware for tests',
            )
        ]


def test_plugin_generate_middleware_registers_on_registry() -> None:
    """Plugin generate_middleware is registered after built-ins."""
    ai = Genkit(plugins=[PluginWithMiddleware()])
    gm = ai.registry.lookup_value('middleware', 'plugin-with-mw_noop')
    assert isinstance(gm, GenerateMiddleware)
    assert gm.name == 'plugin-with-mw_noop'
    assert gm.to_json()['description'] == 'noop plugin middleware for tests'


class _PluginPackMw(BaseMiddleware):
    name = 'my_pack_custom_mw'
    description = 'from plugin() helper'

    async def wrap_model(
        self,
        params: ModelHookParams,
        next_fn: Callable[[ModelHookParams], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        return await next_fn(params)


def test_middleware_plugin_registers_on_registry() -> None:
    """``middleware_plugin`` wraps definitions in a minimal ``Plugin``."""
    gm = generate_middleware(_PluginPackMw)
    plugin = middleware_plugin([gm])
    assert plugin.name == 'extension-middleware'
    ai = Genkit(plugins=[plugin])
    looked = ai.registry.lookup_value('middleware', 'my_pack_custom_mw')
    assert isinstance(looked, GenerateMiddleware)
    assert looked.name == 'my_pack_custom_mw'
    assert looked.to_json()['description'] == 'from plugin() helper'


class _MwOne(BaseMiddleware):
    name = 'mw_one'


class _MwTwo(BaseMiddleware):
    name = 'mw_two'


def test_middleware_plugin_registers_multiple_definitions() -> None:
    """One plugin can bundle several ``GenerateMiddleware`` definitions."""
    g1 = generate_middleware(_MwOne)
    g2 = generate_middleware(_MwTwo)
    ai = Genkit(plugins=[middleware_plugin([g1, g2])])
    assert ai.registry.lookup_value('middleware', 'mw_one') is not None
    assert ai.registry.lookup_value('middleware', 'mw_two') is not None


class _LoggingMw(BaseMiddleware):
    name = 'logging'
    description = 'd'


def test_middleware_plugin_namespace_prefixes_registry_key() -> None:
    """With ``namespace``, keys are ``{namespace}_{definition.name}``; ``Plugin.name`` defaults to namespace."""
    g = generate_middleware(_LoggingMw)
    plugin = middleware_plugin([g], namespace='acme')
    assert plugin.name == 'acme'
    ai = Genkit(plugins=[plugin])
    assert ai.registry.lookup_value('middleware', 'acme_logging') is not None
    assert ai.registry.lookup_value('middleware', 'logging') is None


class _XMw(BaseMiddleware):
    name = 'x'


def test_middleware_plugin_namespace_must_not_contain_slash() -> None:
    with pytest.raises(ValueError, match='namespace'):
        g = generate_middleware(_XMw)
        middleware_plugin([g], namespace='bad/ns')


class _BadSlashNameMw(BaseMiddleware):
    name = 'bad/name'


def test_generate_middleware_name_must_not_contain_slash() -> None:
    """``/`` is reserved for model/action style keys; middleware ids are flat."""
    with pytest.raises(ValueError, match='path-free'):
        generate_middleware(_BadSlashNameMw)


class _BadSpaceNameMw(BaseMiddleware):
    name = 'bad name'


def test_generate_middleware_name_rejects_whitespace_in_segment() -> None:
    with pytest.raises(ValueError, match='path-free'):
        generate_middleware(_BadSpaceNameMw)


class _BadColonNameMw(BaseMiddleware):
    name = 'bad:name'


def test_generate_middleware_name_rejects_colon_in_segment() -> None:
    with pytest.raises(ValueError, match='path-free'):
        generate_middleware(_BadColonNameMw)


def test_middleware_plugin_namespace_rejects_colon() -> None:
    g = generate_middleware(_XMw)
    with pytest.raises(ValueError, match='middleware_plugin namespace'):
        middleware_plugin([g], namespace='acme:ns')


def test_generate_middleware_from_class_reads_name_and_description() -> None:
    """``generate_middleware(MyMiddleware)`` uses ``name`` / ``description`` class attributes."""
    gm = generate_middleware(_ClassMetaMiddleware)
    assert gm.name == 'class_meta_mw'
    assert gm.to_json()['description'] == 'from class attrs'
    ai = Genkit(plugins=[middleware_plugin([gm])])
    assert ai.registry.lookup_value('middleware', 'class_meta_mw') is not None


def test_generate_middleware_from_class_requires_name() -> None:
    class EmptyNameMiddleware(BaseMiddleware):
        pass

    with pytest.raises(ValueError, match='name must be set'):
        generate_middleware(EmptyNameMiddleware)


def test_genkit_generate_middleware_accepts_class_form() -> None:
    """Genkit.generate_middleware builds a definition but does not register it."""
    ai = Genkit()
    gm = ai.generate_middleware(_ClassMetaMiddleware)
    assert gm.name == 'class_meta_mw'
    assert ai.registry.lookup_value('middleware', 'class_meta_mw') is None

    ai2 = Genkit(plugins=[middleware_plugin([gm])])
    assert ai2.registry.lookup_value('middleware', 'class_meta_mw') is gm


def test_middleware_plugin_requires_at_least_one_definition() -> None:
    """Calling ``middleware_plugin`` with an empty list raises."""
    with pytest.raises(ValueError, match='non-empty'):
        middleware_plugin([])


@pytest.mark.asyncio
async def test_unknown_middleware_ref_raises_genkit_error() -> None:
    """A ``MiddlewareRef`` name that is not registered surfaces a clear ``GenkitError``."""
    ai = Genkit(plugins=[AsyncResolveOnlyPlugin()])
    with pytest.raises(GenkitError) as exc_info:
        await ai.generate(
            model='async-resolve-only/lazy-model',
            prompt='hello',
            use=[MiddlewareRef(name='not-registered-middleware', config=None)],
        )
    assert exc_info.value.status == 'NOT_FOUND'
    assert 'not-registered-middleware' in str(exc_info.value)
    assert 'middleware_plugin' in str(exc_info.value)


@pytest.mark.asyncio
async def test_async_resolve_is_awaited_via_generate() -> None:
    """Test that async resolve is awaited when calling generate."""
    ai = Genkit(plugins=[AsyncResolveOnlyPlugin()])
    resp = await ai.generate(model='async-resolve-only/lazy-model', prompt='hello')
    assert resp.text == 'OK: lazy'


@pytest.mark.asyncio
async def test_async_init_is_awaited_via_generate() -> None:
    """Test that async init is awaited when calling generate."""
    ai = Genkit(plugins=[AsyncInitPlugin()])
    resp = await ai.generate(model='async-init-plugin/init-model', prompt='hello')
    assert resp.text == 'OK: resolve'
