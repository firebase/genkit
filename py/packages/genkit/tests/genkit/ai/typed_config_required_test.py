#!/usr/bin/env python3
#
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""A missing required config field is the model action's call, not the pre-turn check.

``wrap_model`` middleware runs after the pre-turn check and can still fill
a field, so only the model action knows a field is missing for real. Both
ways of typing a model (``config_schema=`` and the ``ModelRequest[...]``
annotation) give the same outcome.
"""

from collections.abc import Awaitable, Callable
from typing import Literal

import pytest
from pydantic import BaseModel

from genkit import FinishReason, Genkit, Part
from genkit._core._action import ActionRunContext
from genkit._core._model import Message, ModelRequest, ModelResponse
from genkit._core._typing import Role
from genkit.middleware import BaseMiddleware, GenerateMiddlewareContext, ModelHookParams

NextModel = Callable[[ModelHookParams, GenerateMiddlewareContext], Awaitable[ModelResponse]]


class VoiceConfig(BaseModel):
    """A text-to-speech config whose voice has no default."""

    voice: Literal['alloy', 'echo']
    speed: float = 1.0


def define_tts(ai: Genkit, *, config_schema: bool) -> list[object]:
    """Register a TTS model typed with VoiceConfig; return the configs it saw."""
    configs: list[object] = []

    async def tts(request: ModelRequest[VoiceConfig], ctx: ActionRunContext) -> ModelResponse:
        configs.append(request.config)
        return ModelResponse(message=Message(role=Role.MODEL, content=[Part.from_text('audio')]))

    if config_schema:
        ai.define_model('acme/tts', tts, config_schema=VoiceConfig)
    else:
        ai.define_model('acme/tts', tts)
    return configs


class DefaultVoice(BaseMiddleware):
    """Fills a house voice when the caller left it out."""

    async def wrap_model(
        self, params: ModelHookParams, ctx: GenerateMiddlewareContext, next_fn: NextModel
    ) -> ModelResponse:
        config = params.request.config
        if isinstance(config, dict) and 'voice' not in config:
            params.request.config = {**config, 'voice': 'echo'}
        return await next_fn(params, ctx)


@pytest.mark.asyncio
@pytest.mark.parametrize('config_schema', [True, False], ids=['config_schema', 'annotation'])
async def test_missing_required_field_fails_the_turn_on_both_paths(config_schema: bool) -> None:
    """No middleware fills voice, so the model action rejects it: a failed response either way."""
    ai = Genkit()
    configs = define_tts(ai, config_schema=config_schema)

    response = await ai.generate(model='acme/tts', prompt='Your table is ready.', config={'speed': 1.2})

    assert response.finish_reason == FinishReason.FAILED
    assert configs == []


@pytest.mark.asyncio
@pytest.mark.parametrize('config_schema', [True, False], ids=['config_schema', 'annotation'])
async def test_middleware_can_fill_missing_required_field(config_schema: bool) -> None:
    """A wrap_model middleware that supplies voice still works on both paths."""
    ai = Genkit()
    configs = define_tts(ai, config_schema=config_schema)
    ai.define_middleware(DefaultVoice, name='default_voice')

    response = await ai.generate(
        model='acme/tts', prompt='Your table is ready.', config={'speed': 1.2}, use=[DefaultVoice()]
    )

    assert response.text == 'audio'
    assert configs == [VoiceConfig(voice='echo', speed=1.2)]


@pytest.mark.asyncio
async def test_required_field_from_prompt_config_satisfies_call_override() -> None:
    """The prompt supplies voice, the call overrides speed: the merged bag is complete."""
    ai = Genkit()
    configs = define_tts(ai, config_schema=False)
    announce = ai.define_prompt(model='acme/tts', prompt='Your table is ready.', config={'voice': 'echo'})

    await announce(config={'speed': 1.2})

    assert configs == [VoiceConfig(voice='echo', speed=1.2)]


@pytest.mark.asyncio
async def test_call_override_clearing_required_field_fails_the_turn() -> None:
    """A call that clears the prompt's voice with None leaves it missing for the model action."""
    ai = Genkit()
    configs = define_tts(ai, config_schema=False)
    announce = ai.define_prompt(model='acme/tts', prompt='Your table is ready.', config={'voice': 'echo'})

    response = await announce(config={'voice': None})

    assert response.finish_reason == FinishReason.FAILED
    assert configs == []
