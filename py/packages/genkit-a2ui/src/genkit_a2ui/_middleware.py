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

"""A2ui generate middleware."""

from __future__ import annotations

import json
import uuid
from collections.abc import Awaitable, Callable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from genkit._core._model import Message, ModelRequest, ModelResponse, ModelResponseChunk
from genkit._core._typing import FinishReason, Part, Role, TextPart
from genkit.middleware import BaseMiddleware, GenerateMiddlewareContext, ModelHookParams

from ._catalog import BASIC_CATALOG, A2uiCatalog, render_catalog_instructions
from ._parser import A2uiParseError, Segment, StreamParser
from ._part import a2ui_part, envelopes_from_parts, has_a2ui_mime
from ._types import DEFAULT_VERSION, SURFACE_KEYS, Envelope, SupportedVersion, ValidateMode

ABNORMAL_FINISH_REASONS = frozenset({
    FinishReason.BLOCKED,
    FinishReason.ABORTED,
    FinishReason.INTERRUPTED,
    FinishReason.OTHER,
})


class A2uiConfig(BaseModel):
    """Options for :class:`A2ui`."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    instructions: Literal['system', 'none'] = 'system'
    validation: ValidateMode = Field(default='warn', alias='validate')
    surface_id: str | None = Field(default=None, alias='surfaceId')
    # A typo here would stamp envelopes the renderer cannot paint.
    version: SupportedVersion = DEFAULT_VERSION


class A2ui(BaseMiddleware[A2uiConfig]):
    """Rewrites A2UI fenced model output into data parts.

    On the next turn, inbound A2UI parts become text so the model can see
    prior surfaces and button clicks. A stopped turn (blocked / cancelled /
    aborted / other) is left alone — the stop is the result, not a salvaged card.
    """

    async def wrap_model(
        self,
        params: ModelHookParams,
        ctx: GenerateMiddlewareContext,
        next_fn: Callable[[ModelHookParams, GenerateMiddlewareContext], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        catalog = BASIC_CATALOG
        version = self.config.version or DEFAULT_VERSION
        validate = self.config.validation
        # Chunks are rewritten as fences close. The finished message is parsed
        # again so response.message matches; SurfaceIdReplay replays the same ids.
        replay = SurfaceIdReplay(mint=surface_id_factory(policy=self.config.surface_id))
        parser = StreamParser(
            catalog=catalog,
            validate=validate,
            version=version,
            surface_id=replay.next,
        )

        params.request = sanitize_inbound(request=params.request)
        if self.config.instructions != 'none':
            params.request = inject_instructions(request=params.request, catalog=catalog)

        original_on_chunk = ctx.on_chunk
        parse_error: A2uiParseError | None = None
        if original_on_chunk is not None:

            def handler(chunk: ModelResponseChunk) -> None:
                nonlocal parse_error
                if parse_error is not None:
                    return
                try:
                    transformed = transform_chunk(chunk=chunk, parser=parser)
                except A2uiParseError as exc:
                    # Raising here would wrap this as a model INTERNAL error.
                    # Hold it until the model call finishes so the caller still
                    # sees A2uiParseError.
                    parse_error = exc
                    return
                if transformed is not None:
                    original_on_chunk(transformed)

            ctx.replace_on_chunk(handler)
        try:
            response = await next_fn(params, ctx)
        finally:
            if original_on_chunk is not None:
                ctx.replace_on_chunk(original_on_chunk)

        if response.finish_reason in ABNORMAL_FINISH_REASONS:
            return response
        if parse_error is not None:
            raise parse_error

        if original_on_chunk is not None:
            tail = parts_from_segments(segments=parser.flush())
            if tail:
                original_on_chunk(ModelResponseChunk(role=Role.MODEL, content=tail))

        replay.reset()
        return transform_response(
            response=response,
            catalog=catalog,
            validate=validate,
            version=version,
            surface_id=replay.replay_next,
        )


def surface_id_factory(*, policy: str | None) -> Callable[[], str]:
    if policy:
        return lambda: policy
    return lambda: str(uuid.uuid4())


class SurfaceIdReplay:
    """Mints surface ids on the stream, then replays the same ids on the final parse."""

    def __init__(self, *, mint: Callable[[], str]) -> None:
        self.mint = mint
        self.recorded: list[str] = []
        self.cursor = 0

    def next(self) -> str:
        value = self.mint()
        self.recorded.append(value)
        return value

    def reset(self) -> None:
        self.cursor = 0

    def replay_next(self) -> str:
        if self.cursor < len(self.recorded):
            value = self.recorded[self.cursor]
            self.cursor += 1
            return value
        return self.next()


def part_text(*, part: Part) -> str | None:
    root = part.root
    if isinstance(root, TextPart) and root.text:
        return root.text
    return None


def parts_from_segments(*, segments: list[Segment]) -> list[Part]:
    out: list[Part] = []
    for seg in segments:
        if seg.envelopes:
            out.append(a2ui_part(seg.envelopes))
        elif seg.prose:
            out.append(Part(TextPart(text=seg.prose)))
    return out


def rewrite_parts(*, parts: list[Part], parser: StreamParser, flush_nontext: bool) -> list[Part]:
    out: list[Part] = []
    for part in parts:
        text = part_text(part=part)
        if text:
            segments = parser.push(text=text)
            # Keep the original part when the parser did not split or rewrite it.
            if len(segments) == 1 and not segments[0].envelopes and segments[0].prose == text:
                out.append(part)
            else:
                out.extend(parts_from_segments(segments=segments))
            continue
        if flush_nontext:
            out.extend(parts_from_segments(segments=parser.flush()))
        out.append(part)
    if flush_nontext:
        out.extend(parts_from_segments(segments=parser.flush()))
    return out


def transform_chunk(*, chunk: ModelResponseChunk, parser: StreamParser) -> ModelResponseChunk | None:
    if not chunk.content:
        return chunk
    new_content = rewrite_parts(parts=chunk.content, parser=parser, flush_nontext=False)
    if not new_content:
        return None
    return chunk.model_copy(update={'content': new_content})


def transform_response(
    *,
    response: ModelResponse,
    catalog: A2uiCatalog,
    validate: ValidateMode,
    version: str,
    surface_id: Callable[[], str],
) -> ModelResponse:
    message = response.message
    if message is None and response.candidates:
        message = response.candidates[0].message
    if message is None:
        return response
    parser = StreamParser(
        catalog=catalog,
        validate=validate,
        version=version,
        surface_id=surface_id,
    )
    new_content = rewrite_parts(parts=message.content, parser=parser, flush_nontext=True)
    new_message = message.model_copy(update={'content': new_content})
    # Providers that also expose candidates[0] would otherwise leave the fence
    # there after the top-level message is rewritten.
    update: dict[str, object] = {'message': new_message}
    if response.candidates:
        update['candidates'] = [
            candidate.model_copy(update={'message': new_message}) if i == 0 else candidate
            for i, candidate in enumerate(response.candidates)
        ]
    return response.model_copy(update=update)


def inject_instructions(*, request: ModelRequest, catalog: A2uiCatalog) -> ModelRequest:
    text = render_catalog_instructions(catalog)
    messages = list(request.messages)
    for i, message in enumerate(messages):
        if message.role != Role.SYSTEM:
            continue
        extra = Part(TextPart(text='\n\n' + text))
        messages[i] = message.model_copy(update={'content': [*message.content, extra]})
        return request.model_copy(update={'messages': messages})
    system = Message(role=Role.SYSTEM, content=[Part(TextPart(text=text))])
    return request.model_copy(update={'messages': [system, *messages]})


def sanitize_inbound(*, request: ModelRequest) -> ModelRequest:
    changed = False
    messages: list[Message] = []
    for message in request.messages:
        rewritten = False
        content: list[Part] = []
        for part in message.content:
            # The mime type is what the renderer and the next generate treat as
            # a card, even when the part has no envelopes yet.
            if not has_a2ui_mime(part=part):
                content.append(part)
                continue
            rewritten = True
            text = summarize_envelopes(envelopes=envelopes_from_parts([part]))
            if text:
                content.append(Part(TextPart(text=text)))
        if not rewritten:
            messages.append(message)
            continue
        changed = True
        if not content:
            content.append(Part(TextPart(text='[UI]')))
        messages.append(message.model_copy(update={'content': content}))
    if not changed:
        return request
    return request.model_copy(update={'messages': messages})


def summarize_envelopes(*, envelopes: list[Envelope]) -> str:
    out: list[str] = []
    pending: list[Envelope] = []

    def flush_surface() -> None:
        if not pending:
            return
        out.append('```a2ui\n' + json.dumps(pending, separators=(',', ':')) + '\n```')
        pending.clear()

    for env in envelopes:
        if not env:
            continue
        action = env.get('action')
        if isinstance(action, dict):
            flush_surface()
            name = action.get('name', '')
            surface_id = action.get('surfaceId', '')
            ctx = ''
            context = action.get('context')
            if isinstance(context, dict) and context:
                ctx = ' context=' + json.dumps(context, separators=(',', ':'))
            out.append(f'[UI action "{name}" on surface {surface_id}{ctx}]')
        elif any(env.get(key) for key in SURFACE_KEYS):
            pending.append(env)
    flush_surface()
    return '\n'.join(out)
