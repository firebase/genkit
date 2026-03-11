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

"""Built-in middleware implementations."""

from __future__ import annotations

import asyncio
import base64
import random
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, Protocol, cast

import httpx
from pydantic import BaseModel, ConfigDict, Field

from genkit._ai._document import Document
from genkit._ai._model import (
    Message,
    ModelRequest,
    ModelResponse,
    ModelResponseChunk,
    text_from_content,
)
from genkit._core._action import Action, ActionRunContext
from genkit._core._error import GenkitError, StatusName
from genkit._core._registry import HasRegistry, Registry
from genkit._core._typing import (
    GenerateActionOptions,
    Media,
    MediaPart,
    Metadata,
    ModelRequest as ModelRequestBase,
    Part,
    Supports,
    TextPart,
    ToolRequestPart,
)

# -----------------------------------------------------------------------------
# Middleware protocol (three-hook pattern: Generate, Model, Tool)
# -----------------------------------------------------------------------------


class Middleware(Protocol):
    """Middleware with hooks for Generate loop, Model call, and Tool execution.

    Use [BaseMiddleware] as a base to implement only the hooks you need.
    """

    def wrap_generate(
        self,
        params: GenerateParams,
        next_fn: Callable[[GenerateParams], Awaitable[ModelResponse]],
    ) -> Awaitable[ModelResponse]:
        """Wrap each iteration of the tool loop (model call + optional tool resolution)."""
        ...

    def wrap_model(
        self,
        params: ModelParams,
        next_fn: Callable[[ModelParams], Awaitable[ModelResponse]],
    ) -> Awaitable[ModelResponse]:
        """Wrap each model API call."""
        ...

    def wrap_tool(
        self,
        params: ToolParams,
        next_fn: Callable[[ToolParams], Awaitable[tuple[Part | None, Part | None]]],
    ) -> Awaitable[tuple[Part | None, Part | None]]:
        """Wrap each tool execution."""
        ...


class GenerateParams(BaseModel):
    """Params for the wrap_generate hook."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    options: GenerateActionOptions
    request: ModelRequestBase
    iteration: int


class ModelParams(BaseModel):
    """Params for the wrap_model hook."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    request: ModelRequestBase
    on_chunk: Callable[[ModelResponseChunk], None] | None = None
    context: dict[str, object] = Field(default_factory=dict)


class ToolParams(BaseModel):
    """Params for the wrap_tool hook."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    tool_request_part: ToolRequestPart
    tool: Action


class BaseMiddleware:
    """Base middleware with pass-through defaults. Override only the hooks you need."""

    def wrap_generate(
        self,
        params: GenerateParams,
        next_fn: Callable[[GenerateParams], Awaitable[ModelResponse]],
    ) -> Awaitable[ModelResponse]:
        return next_fn(params)

    def wrap_model(
        self,
        params: ModelParams,
        next_fn: Callable[[ModelParams], Awaitable[ModelResponse]],
    ) -> Awaitable[ModelResponse]:
        return next_fn(params)

    def wrap_tool(
        self,
        params: ToolParams,
        next_fn: Callable[[ToolParams], Awaitable[tuple[Part | None, Part | None]]],
    ) -> Awaitable[tuple[Part | None, Part | None]]:
        return next_fn(params)


# -----------------------------------------------------------------------------
# Internal constants (not exported)
# -----------------------------------------------------------------------------

_CONTEXT_PREFACE = '\n\nUse the following information to complete your task:\n\n'

_DEFAULT_RETRY_STATUSES: list[StatusName] = [
    'UNAVAILABLE',
    'DEADLINE_EXCEEDED',
    'RESOURCE_EXHAUSTED',
    'ABORTED',
    'INTERNAL',
]

_DEFAULT_FALLBACK_STATUSES: list[StatusName] = [
    'UNAVAILABLE',
    'DEADLINE_EXCEEDED',
    'RESOURCE_EXHAUSTED',
    'ABORTED',
    'INTERNAL',
    'NOT_FOUND',
    'UNIMPLEMENTED',
]


# -----------------------------------------------------------------------------
# Internal helpers (not exported)
# -----------------------------------------------------------------------------


def _last_user_message(messages: list[Message]) -> Message | None:
    """Find the last user message in a list."""
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].role == 'user':
            return messages[i]
    return None


def _context_item_template(d: Document, index: int) -> str:
    """Render a document as a citation line for context injection."""
    out = '- '
    ref = (d.metadata and (d.metadata.get('ref') or d.metadata.get('id'))) or index
    out += f'[{ref}]: '
    out += text_from_content(d.content) + '\n'
    return out


# -----------------------------------------------------------------------------
# validate_support()
# -----------------------------------------------------------------------------


def validate_support(
    name: str,
    supports: Supports | None = None,
) -> BaseMiddleware:
    """Middleware that validates request against model capabilities.

    Args:
        name: The model name (for error messages).
        supports: The model's capability flags.

    Returns:
        Middleware that validates requests.

    Raises:
        GenkitError: With INVALID_ARGUMENT status if validation fails.
    """
    return _ValidateSupportMiddleware(name=name, supports=supports)


class _ValidateSupportMiddleware(BaseMiddleware):
    def __init__(self, name: str, supports: Supports | None = None) -> None:
        self._name = name
        self._supports = supports

    async def wrap_model(
        self,
        params: ModelParams,
        next_fn: Callable[[ModelParams], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        req = params.request
        if self._supports is None:
            return await next_fn(params)

        if self._supports.media is False:
            for msg in req.messages:
                for part in msg.content:
                    if hasattr(part.root, 'media') and part.root.media is not None:
                        raise GenkitError(
                            status='INVALID_ARGUMENT',
                            message=f"Model '{self._name}' does not support media, but media was provided.",
                        )

        if self._supports.tools is False and req.tools:
            raise GenkitError(
                status='INVALID_ARGUMENT',
                message=f"Model '{self._name}' does not support tool use, but tools were provided.",
            )

        if self._supports.multiturn is False and len(req.messages) > 1:
            raise GenkitError(
                status='INVALID_ARGUMENT',
                message=f"Model '{self._name}' does not support multiple messages, but {len(req.messages)} were provided.",
            )

        if self._supports.system_role is False:
            for msg in req.messages:
                if msg.role == 'system':
                    raise GenkitError(
                        status='INVALID_ARGUMENT',
                        message=f"Model '{self._name}' does not support system role, but system role was provided.",
                    )

        if self._supports.tool_choice is False and req.tool_choice and req.tool_choice != 'auto':
            raise GenkitError(
                status='INVALID_ARGUMENT',
                message=f"Model '{self._name}' does not support tool choice, but tool choice was provided.",
            )

        return await next_fn(params)


# -----------------------------------------------------------------------------
# download_request_media()
# -----------------------------------------------------------------------------


def download_request_media(
    max_bytes: int | None = None,
    filter_fn: Callable[[Part], bool] | None = None,
) -> BaseMiddleware:
    """Middleware that downloads HTTP media URLs and converts to base64 data URIs.

    Args:
        max_bytes: Maximum number of bytes to download per media item.
        filter_fn: Optional function to filter which parts to process.
            Return True to download, False to skip.

    Returns:
        Middleware that inlines media URLs.

    Example:
        ```python
        await ai.generate(
            prompt=[
                "What's in this image?",
                Part(root=MediaPart(media=Media(url='https://example.com/cat.jpg'))),
            ],
            use=[download_request_media(max_bytes=10_000_000)],
        )
        ```
    """
    return _DownloadRequestMediaMiddleware(max_bytes=max_bytes, filter_fn=filter_fn)


class _DownloadRequestMediaMiddleware(BaseMiddleware):
    def __init__(
        self,
        max_bytes: int | None = None,
        filter_fn: Callable[[Part], bool] | None = None,
    ) -> None:
        self._max_bytes = max_bytes
        self._filter_fn = filter_fn

    async def wrap_model(
        self,
        params: ModelParams,
        next_fn: Callable[[ModelParams], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        req = params.request
        async with httpx.AsyncClient() as client:
            new_messages: list[Message] = []

            for msg in req.messages:
                new_content: list[Part] = []
                content_changed = False

                for part in msg.content:
                    if isinstance(part.root, MediaPart) and part.root.media.url.startswith('http'):
                        if self._filter_fn is not None and not self._filter_fn(part):
                            new_content.append(part)
                            continue

                        content_changed = True
                        try:
                            response = await client.get(part.root.media.url)
                            response.raise_for_status()

                            content = response.content
                            if self._max_bytes is not None and len(content) > self._max_bytes:
                                content = content[: self._max_bytes]

                            content_type = part.root.media.content_type or response.headers.get(
                                'content-type', 'application/octet-stream'
                            )

                            b64_data = base64.b64encode(content).decode('utf-8')
                            data_uri = f'data:{content_type};base64,{b64_data}'

                            new_part = Part(
                                root=MediaPart(
                                    media=Media(url=data_uri, content_type=content_type),
                                )
                            )
                            new_content.append(new_part)

                        except httpx.HTTPError as e:
                            raise GenkitError(
                                status='INVALID_ARGUMENT',
                                message=f"Failed to download media from '{part.root.media.url}': {e}",
                            ) from e
                    else:
                        new_content.append(part)

                if content_changed:
                    new_messages.append(Message(role=msg.role, content=new_content, metadata=msg.metadata))
                elif isinstance(msg, Message):
                    new_messages.append(msg)
                else:
                    new_messages.append(Message(message=msg))

            new_req = req.model_copy(update={'messages': new_messages})
            return await next_fn(ModelParams(request=new_req, on_chunk=params.on_chunk, context=params.context))


# -----------------------------------------------------------------------------
# simulate_system_prompt()
# -----------------------------------------------------------------------------


def simulate_system_prompt(
    preface: str = 'SYSTEM INSTRUCTIONS:\n',
    acknowledgement: str = 'Understood.',
) -> BaseMiddleware:
    r"""Middleware that simulates system prompt for models without native support.

    Converts system messages to user+model message pairs.

    Args:
        preface: Text to prepend to the system content (default: "SYSTEM INSTRUCTIONS:\\n").
        acknowledgement: Model's acknowledgement response (default: "Understood.").

    Returns:
        Middleware that transforms system messages.
    """
    return _SimulateSystemPromptMiddleware(preface=preface, acknowledgement=acknowledgement)


class _SimulateSystemPromptMiddleware(BaseMiddleware):
    def __init__(self, preface: str = 'SYSTEM INSTRUCTIONS:\n', acknowledgement: str = 'Understood.') -> None:
        self._preface = preface
        self._acknowledgement = acknowledgement

    async def wrap_model(
        self,
        params: ModelParams,
        next_fn: Callable[[ModelParams], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        req = params.request
        new_messages: list[Message] = []
        system_found = False

        for msg in req.messages:
            if msg.role == 'system' and not system_found:
                user_content: list[Part] = [Part(root=TextPart(text=self._preface))]
                user_content.extend(msg.content)
                new_messages.append(Message(role='user', content=user_content))
                new_messages.append(
                    Message(
                        role='model',
                        content=[Part(root=TextPart(text=self._acknowledgement))],
                    )
                )
                system_found = True
            else:
                if isinstance(msg, Message):
                    new_messages.append(msg)
                else:
                    new_messages.append(Message(message=msg))

        new_req = req.model_copy(update={'messages': new_messages})
        return await next_fn(ModelParams(request=new_req, on_chunk=params.on_chunk, context=params.context))


# -----------------------------------------------------------------------------
# augment_with_context()
# -----------------------------------------------------------------------------


def augment_with_context(
    preface: str | None = _CONTEXT_PREFACE,
    item_template: Callable[[Document, int], str] | None = None,
    citation_key: str | None = None,
) -> BaseMiddleware:
    """Middleware that injects document context into the last user message.

    Args:
        preface: Text to prepend before context (default: newline-separated instruction block).
            Pass None to omit preface.
        item_template: Function to render each document (default: citation format).
        citation_key: Metadata key to use for citations (default: uses 'ref', 'id', or index).

    Returns:
        Middleware that injects context.
    """
    return _AugmentWithContextMiddleware(
        preface=preface,
        item_template=item_template or _context_item_template,
        citation_key=citation_key,
    )


class _AugmentWithContextMiddleware(BaseMiddleware):
    def __init__(
        self,
        preface: str | None = _CONTEXT_PREFACE,
        item_template: Callable[[Document, int], str] | None = None,
        citation_key: str | None = None,
    ) -> None:
        self._preface = preface
        self._item_template = item_template or _context_item_template
        self._citation_key = citation_key

    async def wrap_model(
        self,
        params: ModelParams,
        next_fn: Callable[[ModelParams], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        req = params.request
        if not req.docs:
            return await next_fn(params)

        user_message = _last_user_message(req.messages)  # type: ignore[arg-type]
        if not user_message:
            return await next_fn(params)

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
                return await next_fn(params)

        out = self._preface or ''
        for i, doc_data in enumerate(req.docs):
            doc = Document(content=doc_data.content, metadata=doc_data.metadata)
            if self._citation_key and doc.metadata:
                doc.metadata['ref'] = doc.metadata.get(self._citation_key, i)
            out += self._item_template(doc, i)
        out += '\n'

        text_part = Part(root=TextPart(text=out, metadata=Metadata(root={'purpose': 'context'})))

        if context_part_index >= 0:
            user_message.content[context_part_index] = text_part
        else:
            if not user_message.content:
                user_message.content = []
            user_message.content.append(text_part)

        return await next_fn(params)


# -----------------------------------------------------------------------------
# retry()
# -----------------------------------------------------------------------------


def retry(
    max_retries: int = 3,
    statuses: list[StatusName] | None = None,
    initial_delay_ms: int = 1000,
    max_delay_ms: int = 60000,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    on_error: Callable[[Exception, int], None] | None = None,
) -> BaseMiddleware:
    """Middleware that retries failed requests with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default: 3).
        statuses: List of status codes that trigger retry (default: UNAVAILABLE,
            DEADLINE_EXCEEDED, RESOURCE_EXHAUSTED, ABORTED, INTERNAL).
        initial_delay_ms: Initial delay between retries in milliseconds (default: 1000).
        max_delay_ms: Maximum delay between retries in milliseconds (default: 60000).
        backoff_factor: Multiplier for delay after each retry (default: 2.0).
        jitter: Whether to add random jitter to delays (default: True).
        on_error: Optional callback called on each retry attempt with (error, attempt).

    Returns:
        Middleware that implements retry logic.
    """
    return _RetryMiddleware(
        max_retries=max_retries,
        statuses=statuses or _DEFAULT_RETRY_STATUSES,
        initial_delay_ms=initial_delay_ms,
        max_delay_ms=max_delay_ms,
        backoff_factor=backoff_factor,
        jitter=jitter,
        on_error=on_error,
    )


class _RetryMiddleware(BaseMiddleware):
    def __init__(
        self,
        max_retries: int = 3,
        statuses: list[StatusName] | None = None,
        initial_delay_ms: int = 1000,
        max_delay_ms: int = 60000,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        on_error: Callable[[Exception, int], None] | None = None,
    ) -> None:
        self._max_retries = max_retries
        self._statuses = statuses or _DEFAULT_RETRY_STATUSES
        self._initial_delay_ms = initial_delay_ms
        self._max_delay_ms = max_delay_ms
        self._backoff_factor = backoff_factor
        self._jitter = jitter
        self._on_error = on_error

    async def wrap_model(
        self,
        params: ModelParams,
        next_fn: Callable[[ModelParams], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        last_error: Exception | None = None
        current_delay_ms: float = float(self._initial_delay_ms)

        for attempt in range(int(self._max_retries) + 1):
            try:
                return await next_fn(params)
            except Exception as e:
                last_error = e

                if attempt < self._max_retries:
                    should_retry = (isinstance(e, GenkitError) and e.status in self._statuses) or not isinstance(
                        e, GenkitError
                    )

                    if should_retry:
                        if self._on_error:
                            self._on_error(e, attempt + 1)

                        delay = current_delay_ms
                        if self._jitter:
                            delay = delay + random.random() * (2**attempt) * 1000

                        await asyncio.sleep(delay / 1000.0)
                        current_delay_ms = min(
                            current_delay_ms * self._backoff_factor,
                            float(self._max_delay_ms),
                        )
                        continue

                raise

        if last_error:
            raise last_error
        raise RuntimeError('Retry loop completed without result')


# -----------------------------------------------------------------------------
# fallback()
# -----------------------------------------------------------------------------


def fallback(
    ai: HasRegistry,
    models: list[str],
    statuses: list[StatusName] | None = None,
    on_error: Callable[[GenkitError], None] | None = None,
) -> BaseMiddleware:
    """Middleware that falls back to alternative models on failure.

    Args:
        ai: Object with a registry (e.g. Genkit instance) for resolving fallback models.
        models: Ordered list of fallback model names to try.
        statuses: List of status codes that trigger fallback (default: UNAVAILABLE,
            DEADLINE_EXCEEDED, RESOURCE_EXHAUSTED, ABORTED, INTERNAL, NOT_FOUND,
            UNIMPLEMENTED).
        on_error: Optional callback called when fallback is triggered.

    Returns:
        Middleware that implements fallback logic.
    """
    return _fallback_for_registry(ai.registry, models, statuses, on_error)


def _fallback_for_registry(
    registry: Registry,
    models: list[str],
    statuses: list[StatusName] | None = None,
    on_error: Callable[[GenkitError], None] | None = None,
) -> BaseMiddleware:
    """Internal: fallback middleware that takes a Registry (for testing)."""
    return _FallbackMiddleware(
        registry=registry,
        models=models,
        statuses=statuses or _DEFAULT_FALLBACK_STATUSES,
        on_error=on_error,
    )


class _FallbackMiddleware(BaseMiddleware):
    def __init__(
        self,
        registry: Registry,
        models: list[str],
        statuses: list[StatusName],
        on_error: Callable[[GenkitError], None] | None = None,
    ) -> None:
        self._registry = registry
        self._models = models
        self._statuses = statuses
        self._on_error = on_error

    async def wrap_model(
        self,
        params: ModelParams,
        next_fn: Callable[[ModelParams], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        try:
            return await next_fn(params)
        except Exception as e:
            if isinstance(e, GenkitError) and e.status in self._statuses:
                if self._on_error:
                    self._on_error(e)

                last_error: Exception = e
                ctx = ActionRunContext(context=params.context)

                for model_name in self._models:
                    try:
                        model = await self._registry.resolve_model(model_name)
                        if model is None:
                            raise GenkitError(
                                status='NOT_FOUND',
                                message=f"Fallback model '{model_name}' not found.",
                            )
                        result = await model.run(
                            input=cast(ModelRequest, params.request),
                            context=params.context,
                            on_chunk=params.on_chunk,
                        )
                        return result.response
                    except Exception as e2:
                        last_error = e2
                        if isinstance(e2, GenkitError) and e2.status in self._statuses:
                            if self._on_error:
                                self._on_error(e2)
                            continue
                        raise
                raise last_error from None
            raise
