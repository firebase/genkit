#!/usr/bin/env python3
#
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""A missing required config field is the model action's call, not the pre-turn check.

``wrap_model`` middleware runs after the pre-turn check and can still fill
a field, so only the model action knows a field is missing for real. Every
way of declaring a model's config gives the same outcome: the
``ModelRequest[...]`` annotation, a ``config_schema=`` class (with or
without the annotation), and a ``config_schema=`` JSON-schema dict.
"""

from collections.abc import Awaitable, Callable
from typing import Literal

import pytest
from pydantic import BaseModel, ConfigDict

from genkit import FinishReason, Genkit, Part
from genkit._core._action import ActionRunContext
from genkit._core._error import GenkitError
from genkit._core._model import Message, ModelRequest, ModelResponse
from genkit._core._typing import Role
from genkit.middleware import BaseMiddleware, GenerateMiddlewareContext, ModelHookParams
from genkit.model import model_ref

NextModel = Callable[[ModelHookParams, GenerateMiddlewareContext], Awaitable[ModelResponse]]

Declared = Literal['annotation', 'config_schema', 'class_only', 'json_schema']
EVERY_DECLARATION: list[Declared] = ['annotation', 'config_schema', 'class_only', 'json_schema']


class VoiceConfig(BaseModel):
    """A text-to-speech config whose voice has no default."""

    voice: Literal['alloy', 'echo']
    speed: float = 1.0


def define_tts(ai: Genkit, *, declared: Declared) -> list[object]:
    """Register a TTS model with VoiceConfig declared as ``declared``; return the configs it saw."""
    configs: list[object] = []

    async def typed_tts(request: ModelRequest[VoiceConfig], ctx: ActionRunContext) -> ModelResponse:
        configs.append(request.config)
        return ModelResponse(message=Message(role=Role.MODEL, content=[Part.from_text('audio')]))

    async def plain_tts(request: ModelRequest, ctx: ActionRunContext) -> ModelResponse:
        configs.append(request.config)
        return ModelResponse(message=Message(role=Role.MODEL, content=[Part.from_text('audio')]))

    if declared == 'annotation':
        ai.define_model('acme/tts', typed_tts)
    elif declared == 'config_schema':
        ai.define_model('acme/tts', typed_tts, config_schema=VoiceConfig)
    elif declared == 'class_only':
        ai.define_model('acme/tts', plain_tts, config_schema=VoiceConfig)
    else:
        ai.define_model('acme/tts', plain_tts, config_schema=VoiceConfig.model_json_schema())
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


def voice_of(config: object) -> object:
    """The voice a model saw, whether its config arrived typed or as a dict."""
    return config.voice if isinstance(config, VoiceConfig) else dict(config)['voice']  # type: ignore[arg-type]


@pytest.mark.asyncio
@pytest.mark.parametrize('declared', EVERY_DECLARATION)
async def test_missing_required_field_fails_the_turn(declared: Declared) -> None:
    """No middleware fills voice, so the model action rejects it: a failed response every way."""
    ai = Genkit()
    configs = define_tts(ai, declared=declared)

    response = await ai.generate(model='acme/tts', prompt='Your table is ready.', config={'speed': 1.2})

    assert response.finish_reason == FinishReason.FAILED
    assert response.error is not None
    assert response.error.status == 'INVALID_ARGUMENT'
    # The annotated paths fail in the action's input validation, which names
    # the field in details rather than the message.
    assert 'voice' in f'{response.error.message} {response.error.details}'
    assert configs == []


@pytest.mark.asyncio
@pytest.mark.parametrize('declared', EVERY_DECLARATION)
async def test_middleware_can_fill_missing_required_field(declared: Declared) -> None:
    """A wrap_model middleware that supplies voice still works every way."""
    ai = Genkit()
    configs = define_tts(ai, declared=declared)
    ai.define_middleware(DefaultVoice, name='default_voice')

    response = await ai.generate(
        model='acme/tts', prompt='Your table is ready.', config={'speed': 1.2}, use=[DefaultVoice()]
    )

    assert response.text == 'audio'
    assert [voice_of(config) for config in configs] == ['echo']


@pytest.mark.asyncio
@pytest.mark.parametrize('declared', EVERY_DECLARATION)
async def test_bad_value_raises_before_the_turn(declared: Declared) -> None:
    """A value the schema rejects raises INVALID_ARGUMENT every way; the model never runs."""
    ai = Genkit()
    configs = define_tts(ai, declared=declared)

    with pytest.raises(GenkitError) as err:
        await ai.generate(model='acme/tts', prompt='Your table is ready.', config={'voice': 'opera'})

    assert err.value.status == 'INVALID_ARGUMENT'
    assert "'voice'" in str(err.value)
    assert configs == []


@pytest.mark.asyncio
async def test_required_field_from_prompt_config_satisfies_call_override() -> None:
    """The prompt supplies voice, the call overrides speed: the merged bag is complete."""
    ai = Genkit()
    configs = define_tts(ai, declared='annotation')
    announce = ai.define_prompt(model='acme/tts', prompt='Your table is ready.', config={'voice': 'echo'})

    await announce(config={'speed': 1.2})

    assert configs == [VoiceConfig(voice='echo', speed=1.2)]


@pytest.mark.asyncio
async def test_call_override_clearing_required_field_fails_the_turn() -> None:
    """A call that clears the prompt's voice with None leaves it missing for the model action."""
    ai = Genkit()
    configs = define_tts(ai, declared='annotation')
    announce = ai.define_prompt(model='acme/tts', prompt='Your table is ready.', config={'voice': 'echo'})

    response = await announce(config={'voice': None})

    assert response.finish_reason == FinishReason.FAILED
    assert configs == []


@pytest.mark.asyncio
async def test_json_schema_nested_missing_field_raises_before_the_turn() -> None:
    """A nested object is sent whole, so a field missing inside it raises before the turn, as with a class."""

    class Pronunciation(BaseModel):
        lexicon: str

    class LexiconVoiceConfig(VoiceConfig):
        pronunciation: Pronunciation | None = None

    ai = Genkit()
    seen: list[object] = []

    async def tts(request: ModelRequest, ctx: ActionRunContext) -> ModelResponse:
        seen.append(request.config)
        return ModelResponse(message=Message(role=Role.MODEL, content=[Part.from_text('audio')]))

    ai.define_model('acme/tts', tts, config_schema=LexiconVoiceConfig.model_json_schema())

    with pytest.raises(GenkitError) as err:
        await ai.generate(model='acme/tts', prompt='Your table is ready.', config={'pronunciation': {}})

    assert err.value.status == 'INVALID_ARGUMENT'
    assert 'lexicon' in str(err.value)
    assert seen == []


@pytest.mark.parametrize('declared', ['class_only', 'json_schema'])
def test_sync_model_fn_still_fails_at_define(declared: Declared) -> None:
    """The config check wraps fn, but a sync fn is still rejected when the model is defined."""
    ai = Genkit()
    schema = VoiceConfig if declared == 'class_only' else VoiceConfig.model_json_schema()

    def tts(request: ModelRequest, ctx: ActionRunContext) -> ModelResponse:
        return ModelResponse(message=Message(role=Role.MODEL, content=[Part.from_text('audio')]))

    with pytest.raises(TypeError, match='must be async'):
        ai.define_model('acme/tts', tts, config_schema=schema)  # type: ignore[arg-type]


def test_invalid_json_schema_fails_at_define() -> None:
    """A config_schema dict that isn't a JSON schema is the model author's bug; it raises at define."""
    ai = Genkit()

    async def tts(request: ModelRequest, ctx: ActionRunContext) -> ModelResponse:
        return ModelResponse(message=Message(role=Role.MODEL, content=[Part.from_text('audio')]))

    with pytest.raises(GenkitError, match='not a valid JSON schema'):
        ai.define_model('acme/tts', tts, config_schema={'type': 'bogus'})


class StrictVoice(BaseModel):
    """A user config class that forbids keys it doesn't declare, version included."""

    model_config = ConfigDict(extra='forbid')
    voice: Literal['alloy', 'echo']


@pytest.mark.asyncio
@pytest.mark.parametrize('declared', ['class_only', 'json_schema'])
async def test_model_ref_version_passes_a_schema_that_does_not_name_it(declared: Declared) -> None:
    """ModelRef.version rides in config; a strict schema without a version field still runs."""
    ai = Genkit()
    seen: list[object] = []

    async def tts(request: ModelRequest, ctx: ActionRunContext) -> ModelResponse:
        seen.append(request.config)
        return ModelResponse(message=Message(role=Role.MODEL, content=[Part.from_text('audio')]))

    schema = StrictVoice if declared == 'class_only' else StrictVoice.model_json_schema()
    ai.define_model('acme/tts', tts, config_schema=schema)
    ref = model_ref('acme/tts', config_schema=StrictVoice, version='v2')

    response = await ai.generate(model=ref, prompt='Your table is ready.', config={'voice': 'echo'})

    assert response.text == 'audio'
    assert len(seen) == 1
    assert dict(seen[0]) == {'voice': 'echo', 'version': 'v2'}  # type: ignore[call-overload]


@pytest.mark.asyncio
async def test_direct_run_with_unannotated_request_checks_config() -> None:
    """A direct action run (Dev UI) hands an unannotated fn the raw dict; the check reads config from it."""
    ai = Genkit()

    async def tts(request, ctx: ActionRunContext) -> ModelResponse:  # noqa: ANN001
        return ModelResponse(message=Message(role=Role.MODEL, content=[Part.from_text('audio')]))

    action = ai.define_model('acme/tts', tts, config_schema=VoiceConfig)

    with pytest.raises(GenkitError) as err:
        await action.run({'messages': [], 'config': {'speed': 1.2}})

    assert err.value.status == 'INVALID_ARGUMENT'
    assert "config 'voice': Field required" in str(err.value)


@pytest.mark.asyncio
@pytest.mark.parametrize('declared', ['class_only', 'json_schema'])
async def test_missing_field_message_is_the_same_for_class_and_dict(declared: Declared) -> None:
    """Class and dict schemas name a missing field the same way."""
    ai = Genkit()
    define_tts(ai, declared=declared)

    response = await ai.generate(model='acme/tts', prompt='Your table is ready.', config={'speed': 1.2})

    assert response.error is not None
    assert response.error.message == "acme/tts: config 'voice': Field required"
