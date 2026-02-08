# Copyright 2025 Google LLC
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

"""Model middleware for the Genkit framework.

Provides reusable middleware functions that can be composed into model
generation pipelines via ``ai.generate(use=[...])``. Each middleware
intercepts the ``GenerateRequest`` before it reaches the model and/or
the ``GenerateResponse`` after it returns.

Middleware catalogue:

    ┌──────────────────────────────────────┬──────────────────────────────────────┐
    │ Middleware                           │ Purpose                              │
    ├──────────────────────────────────────┼──────────────────────────────────────┤
    │ ``augment_with_context()``           │ Inject RAG context into prompt       │
    │ ``download_request_media()``         │ Inline HTTP media as data URIs       │
    │ ``validate_support()``               │ Check model capability support       │
    │ ``simulate_system_prompt()``         │ Fold system prompt into user msgs    │
    │ ``simulate_constrained_generation()``│ Inject JSON schema instructions      │
    │ ``retry()``                          │ Retry with exponential backoff       │
    │ ``fallback()``                       │ Cascade to fallback models           │
    └──────────────────────────────────────┴──────────────────────────────────────┘

See Also:
    - JS reference: ``js/ai/src/model/middleware.ts``
"""

from __future__ import annotations

import asyncio
import base64
import json
import random
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from genkit.blocks.messages import inject_instructions
from genkit.blocks.model import (
    ModelMiddleware,
    ModelMiddlewareNext,
    text_from_content,
)
from genkit.core.action import ActionRunContext
from genkit.core.error import GenkitError
from genkit.core.http_client import get_cached_client
from genkit.core.logging import get_logger
from genkit.core.status_types import StatusName
from genkit.core.typing import (
    DocumentData,
    GenerateRequest,
    GenerateResponse,
    Media,
    MediaPart,
    Message,
    Metadata,
    OutputConfig,
    Part,
    Supports,
    TextPart,
)

if TYPE_CHECKING:
    from genkit.core.registry import Registry

logger = get_logger(__name__)

CONTEXT_PREFACE = '\n\nUse the following information to complete your task:\n\n'

DEFAULT_RETRY_STATUSES: list[StatusName] = [
    'UNAVAILABLE',
    'DEADLINE_EXCEEDED',
    'RESOURCE_EXHAUSTED',
    'ABORTED',
    'INTERNAL',
]

DEFAULT_FALLBACK_STATUSES: list[StatusName] = [
    'UNAVAILABLE',
    'DEADLINE_EXCEEDED',
    'RESOURCE_EXHAUSTED',
    'ABORTED',
    'INTERNAL',
    'NOT_FOUND',
    'UNIMPLEMENTED',
]


def last_user_message(messages: list[Message]) -> Message | None:
    """Finds the last message with the role 'user' in a list of messages.

    Args:
        messages: A list of Message objects.

    Returns:
        The last message with the role 'user', or None if no such message exists.
    """
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].role == 'user':
            return messages[i]
    return None


def part_has_media(part: Part) -> bool:
    """Check whether a Part contains a media attachment.

    This is a safe accessor that works regardless of the concrete Part
    variant (TextPart, MediaPart, ToolRequestPart, etc.).

    Args:
        part: The Part to inspect.

    Returns:
        True if the part is a MediaPart with a non-None media field.
    """
    return hasattr(part.root, 'media') and part.root.media is not None


def has_media_in_messages(messages: list[Message]) -> bool:
    """Check whether any message in a list contains a media part.

    Args:
        messages: The messages to scan.

    Returns:
        True if at least one Part in any message contains media.
    """
    return any(part_has_media(part) for msg in messages for part in msg.content)


def find_system_message_index(messages: list[Message]) -> int:
    """Find the index of the first system message.

    Args:
        messages: The messages to scan.

    Returns:
        The index of the first system message, or -1 if none found.
    """
    for i, msg in enumerate(messages):
        if msg.role == 'system':
            return i
    return -1


def context_item_template(d: DocumentData, index: int) -> str:
    """Renders a DocumentData object into a formatted string for context injection.

    Creates a string representation of the document, typically for inclusion in a
    prompt. It attempts to use metadata fields ('ref', 'id') or the provided index
    as a citation marker.

    Args:
        d: The DocumentData object to render.
        index: The index of the document in a list, used as a fallback citation.

    Returns:
        A formatted string representing the document content with a citation.
    """
    out = '- '
    ref = (d.metadata and (d.metadata.get('ref') or d.metadata.get('id'))) or index
    out += f'[{ref}]: '
    out += text_from_content(d.content) + '\n'
    return out


def _default_constrained_generation_instructions(schema: dict[str, Any]) -> str:
    """Default instructions renderer for simulated constrained generation."""
    return f'Output should be in JSON format and conform to the following schema:\n\n```\n{json.dumps(schema)}\n```\n'


def augment_with_context() -> ModelMiddleware:
    """Returns a ModelMiddleware that augments the prompt with document context.

    This middleware checks if the ``GenerateRequest`` includes documents (``req.docs``).
    If documents are present, it finds the last user message and injects the
    rendered content of the documents into it as a special context Part.

    Returns:
        A ModelMiddleware function.
    """

    async def middleware(
        req: GenerateRequest,
        ctx: ActionRunContext,
        next_middleware: ModelMiddlewareNext,
    ) -> GenerateResponse:
        """Inject context documents into the last user message.

        Args:
            req: The incoming GenerateRequest.
            ctx: The ActionRunContext.
            next_middleware: The next function in the middleware chain.

        Returns:
            The result from the next middleware or the final GenerateResponse.
        """
        if not req.docs:
            return await next_middleware(req, ctx)

        user_message = last_user_message(req.messages)
        if not user_message:
            return await next_middleware(req, ctx)

        context_part_index = -1
        for i, part in enumerate(user_message.content):
            part_metadata = part.root.metadata
            if isinstance(part_metadata, Metadata) and part_metadata.root.get('purpose') == 'context':
                context_part_index = i
                break

        context_part = user_message.content[context_part_index] if context_part_index >= 0 else None

        if context_part:
            metadata = context_part.root.metadata
            if not (isinstance(metadata, Metadata) and metadata.root.get('pending')):
                return await next_middleware(req, ctx)

        out = CONTEXT_PREFACE
        for i, doc_data in enumerate(req.docs):
            doc = DocumentData(content=doc_data.content, metadata=doc_data.metadata)
            out += context_item_template(doc, i)
        out += '\n'

        text_part = Part(root=TextPart(text=out, metadata=Metadata(root={'purpose': 'context'})))
        if context_part_index >= 0:
            user_message.content[context_part_index] = text_part
        else:
            if not user_message.content:
                user_message.content = []
            user_message.content.append(text_part)

        return await next_middleware(req, ctx)

    return middleware


def download_request_media(
    *,
    max_bytes: int | None = None,
    filter_fn: Callable[[MediaPart], bool] | None = None,
) -> ModelMiddleware:
    """Download referenced HTTP(S) media URLs and inline them as data URIs.

    Iterates over all message parts in the request. For each ``MediaPart``
    whose URL starts with ``http``, the middleware downloads the content and
    replaces the URL with an inline ``data:`` URI.

    Matches the JS ``downloadRequestMedia()`` middleware.

    Args:
        max_bytes: Optional maximum number of bytes to download per media.
        filter_fn: Optional predicate to decide which ``MediaPart`` objects
            to download. If the filter returns ``False``, the part is left
            unchanged.

    Returns:
        A ``ModelMiddleware`` function.
    """

    async def middleware(
        req: GenerateRequest,
        ctx: ActionRunContext,
        next_fn: ModelMiddlewareNext,
    ) -> GenerateResponse:
        client = get_cached_client(cache_key='download-request-media', timeout=60.0)

        new_messages: list[Message] = []
        for message in req.messages:
            new_content: list[Part] = []
            for part in message.content:
                if not part_has_media(part) or not isinstance(part.root, MediaPart):
                    new_content.append(part)
                    continue

                media = part.root.media
                if not media.url.startswith('http'):
                    new_content.append(part)
                    continue

                if filter_fn and not filter_fn(part.root):
                    new_content.append(part)
                    continue

                response = await client.get(media.url)
                if response.status_code != 200:
                    raise GenkitError(
                        message=f"HTTP error {response.status_code} downloading media '{media.url}'",
                        status='INTERNAL',
                    )

                raw_bytes = response.content
                if max_bytes and len(raw_bytes) > max_bytes:
                    raw_bytes = raw_bytes[:max_bytes]

                content_type = media.content_type or response.headers.get('content-type', '')
                b64 = base64.b64encode(raw_bytes).decode('ascii')
                data_uri = f'data:{content_type};base64,{b64}'

                new_content.append(Part(root=MediaPart(media=Media(url=data_uri, content_type=content_type))))
            new_messages.append(Message(role=message.role, content=new_content))

        new_req = req.model_copy(update={'messages': new_messages})
        return await next_fn(new_req, ctx)

    return middleware


def validate_support(
    *,
    name: str,
    supports: Supports | None = None,
) -> ModelMiddleware:
    """Validate that a GenerateRequest does not include unsupported features.

    Raises a ``GenkitError`` with ``INVALID_ARGUMENT`` if the request contains
    media, tools, or multiturn when the model explicitly marks them as
    unsupported (``False``).

    Matches the JS ``validateSupport()`` middleware.

    Args:
        name: The model name (used in error messages).
        supports: A ``Supports`` object describing model capabilities. If
            ``None``, all features are assumed supported.

    Returns:
        A ``ModelMiddleware`` function.
    """

    async def middleware(
        req: GenerateRequest,
        ctx: ActionRunContext,
        next_fn: ModelMiddlewareNext,
    ) -> GenerateResponse:
        if supports is None:
            return await next_fn(req, ctx)

        def invalid(message: str) -> None:
            raise GenkitError(
                message=(f"Model '{name}' does not support {message}. Request: {req.model_dump_json(indent=2)}"),
                status='INVALID_ARGUMENT',
            )

        if supports.media is False and has_media_in_messages(req.messages):
            invalid('media, but media was provided')

        if supports.tools is False and req.tools:
            invalid('tool use, but tools were provided')

        if supports.multiturn is False and len(req.messages) > 1:
            invalid(f'multiple messages, but {len(req.messages)} were provided')

        return await next_fn(req, ctx)

    return middleware


def simulate_system_prompt(
    *,
    preface: str = 'SYSTEM INSTRUCTIONS:\n',
    acknowledgement: str = 'Understood.',
) -> ModelMiddleware:
    """Simulate system prompts for models that don't support them natively.

    Converts the first ``system`` message into a user/model exchange:
    - The system message content is prepended with ``preface`` and sent as
      a ``user`` message.
    - A short ``model`` message with ``acknowledgement`` follows.

    Matches the JS ``simulateSystemPrompt()`` middleware.

    Args:
        preface: Text prepended to the system message content.
        acknowledgement: The model's simulated acknowledgement.

    Returns:
        A ``ModelMiddleware`` function.
    """

    async def middleware(
        req: GenerateRequest,
        ctx: ActionRunContext,
        next_fn: ModelMiddlewareNext,
    ) -> GenerateResponse:
        messages = list(req.messages)
        idx = find_system_message_index(messages)
        if idx >= 0:
            system_content = messages[idx].content
            messages[idx : idx + 1] = [
                Message(
                    role='user',
                    content=[Part(root=TextPart(text=preface)), *system_content],
                ),
                Message(
                    role='model',
                    content=[Part(root=TextPart(text=acknowledgement))],
                ),
            ]

        new_req = req.model_copy(update={'messages': messages})
        return await next_fn(new_req, ctx)

    return middleware


def simulate_constrained_generation(
    *,
    instructions_renderer: Callable[[dict[str, Any]], str] | None = None,
) -> ModelMiddleware:
    """Simulate constrained generation by injecting JSON schema instructions.

    When the request has ``output.constrained`` set and a schema, this
    middleware injects generation instructions into the user message and
    then removes the constrained/format/schema fields so the model
    generates unconstrained text.

    Matches the JS ``simulateConstrainedGeneration()`` middleware.

    Args:
        instructions_renderer: Optional custom function to render the
            schema into instruction text.

    Returns:
        A ``ModelMiddleware`` function.
    """
    renderer = instructions_renderer or _default_constrained_generation_instructions

    async def middleware(
        req: GenerateRequest,
        ctx: ActionRunContext,
        next_fn: ModelMiddlewareNext,
    ) -> GenerateResponse:
        if not (req.output and req.output.constrained and req.output.schema):
            return await next_fn(req, ctx)

        instructions = renderer(req.output.schema)
        new_messages = inject_instructions(req.messages, instructions)

        new_output = OutputConfig(
            constrained=False,
            format=None,
            content_type=None,
            schema=None,
        )

        new_req = req.model_copy(
            update={
                'messages': new_messages,
                'output': new_output,
            }
        )
        return await next_fn(new_req, ctx)

    return middleware


def retry(
    *,
    max_retries: int = 3,
    statuses: list[StatusName] | None = None,
    initial_delay_ms: int = 1000,
    max_delay_ms: int = 60000,
    backoff_factor: int = 2,
    no_jitter: bool = False,
    on_error: Callable[[Exception, int], None] | None = None,
) -> ModelMiddleware:
    """Retry model requests with exponential backoff and optional jitter.

    On transient errors (matching the configured status codes), the
    middleware retries up to ``max_retries`` times with exponentially
    increasing delay.

    Matches the JS ``retry()`` middleware.

    Example::

        response = await ai.generate(
            model='googleai/gemini-2.0-flash',
            prompt='Hello',
            use=[
                retry(
                    max_retries=2,
                    initial_delay_ms=1000,
                    backoff_factor=2,
                ),
            ],
        )

    Args:
        max_retries: Maximum number of retry attempts. Default: 3.
        statuses: List of status names that trigger a retry. Defaults to
            ``UNAVAILABLE``, ``DEADLINE_EXCEEDED``, ``RESOURCE_EXHAUSTED``,
            ``ABORTED``, ``INTERNAL``.
        initial_delay_ms: Initial delay between retries in milliseconds.
        max_delay_ms: Maximum delay cap in milliseconds.
        backoff_factor: Multiplicative factor for exponential backoff.
        no_jitter: If ``True``, disable random jitter on delay.
        on_error: Optional callback invoked on each retry attempt with
            the error and attempt number (1-based).

    Returns:
        A ``ModelMiddleware`` function.
    """
    retry_statuses = statuses or DEFAULT_RETRY_STATUSES

    async def middleware(
        req: GenerateRequest,
        ctx: ActionRunContext,
        next_fn: ModelMiddlewareNext,
    ) -> GenerateResponse:
        last_error: Exception | None = None
        current_delay = initial_delay_ms

        for attempt in range(max_retries + 1):
            try:
                return await next_fn(req, ctx)
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    should_retry = False
                    if isinstance(e, GenkitError):
                        if e.status in retry_statuses:
                            should_retry = True
                    else:
                        should_retry = True

                    if should_retry:
                        if on_error:
                            on_error(e, attempt + 1)

                        delay_s = current_delay / 1000.0
                        if not no_jitter:
                            jitter = random.uniform(0, 1)
                            delay_s += jitter

                        await asyncio.sleep(delay_s)
                        current_delay = min(
                            current_delay * backoff_factor,
                            max_delay_ms,
                        )
                        continue

                raise

        if last_error:
            raise last_error
        raise RuntimeError('retry middleware: unexpected state')

    return middleware


def fallback(
    *,
    models: list[str],
    statuses: list[StatusName] | None = None,
    on_error: Callable[[Exception], None] | None = None,
) -> ModelMiddleware:
    """Falls back to alternative models when the primary model fails.

    If the primary model raises a ``GenkitError`` with a status in the
    configured list, the middleware tries each fallback model in order.

    Matches the JS ``fallback()`` middleware. In the Python version,
    fallback models are specified by name (string) rather than by
    ``ModelArgument``, because the model action is resolved at call time
    via the action run context.

    Example::

        response = await ai.generate(
            model='googleai/gemini-2.0-flash',
            prompt='Hello',
            use=[
                fallback(
                    models=['googleai/gemini-1.5-flash-latest'],
                    statuses=['RESOURCE_EXHAUSTED'],
                ),
            ],
        )

    Args:
        models: List of fallback model names to try in order.
        statuses: List of status names that trigger fallback. Defaults to
            ``UNAVAILABLE``, ``DEADLINE_EXCEEDED``, ``RESOURCE_EXHAUSTED``,
            ``ABORTED``, ``INTERNAL``, ``NOT_FOUND``, ``UNIMPLEMENTED``.
        on_error: Optional callback invoked on each error before fallback.

    Returns:
        A ``ModelMiddleware`` function.
    """
    fallback_statuses = statuses or DEFAULT_FALLBACK_STATUSES

    async def middleware(
        req: GenerateRequest,
        ctx: ActionRunContext,
        next_fn: ModelMiddlewareNext,
    ) -> GenerateResponse:
        try:
            return await next_fn(req, ctx)
        except GenkitError as e:
            if e.status not in fallback_statuses:
                raise

            if on_error:
                on_error(e)

            last_error: Exception = e
            for model_name in models:
                try:
                    registry: Registry = cast('Registry', ctx.context.get('registry'))
                    if registry is None:
                        raise GenkitError(
                            message='fallback middleware requires registry in context',
                            status='INTERNAL',
                        )
                    model_action = await registry.resolve_model(model_name)
                    if model_action is None:
                        raise GenkitError(
                            message=f"Fallback model '{model_name}' not found",
                            status='NOT_FOUND',
                        )
                    result = await model_action.arun(req)
                    return result.response
                except GenkitError as e2:
                    last_error = e2
                    if e2.status in fallback_statuses:
                        if on_error:
                            on_error(e2)
                        continue
                    raise
                except Exception as e2:
                    raise e2 from e

            raise last_error from e

    return middleware
