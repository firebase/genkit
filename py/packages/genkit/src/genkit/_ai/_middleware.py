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

"""Middleware for the Genkit framework."""

from __future__ import annotations

import asyncio
import base64
import random
from collections.abc import Awaitable, Callable

import httpx

from genkit._ai._document import Document
from genkit._ai._model import (
    Message,
    ModelMiddleware,
    ModelRequest,
    ModelResponse,
    text_from_content,
)
from genkit._core._action import ActionRunContext
from genkit._core._error import GenkitError, StatusName
from genkit._core._registry import Registry
from genkit._core._typing import (
    Media,
    MediaPart,
    Metadata,
    Part,
    Supports,
    TextPart,
)

# =============================================================================
# Constants
# =============================================================================

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


# =============================================================================
# Helper Functions
# =============================================================================


def last_user_message(messages: list[Message]) -> Message | None:
    """Find the last user message in a list."""
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].role == 'user':
            return messages[i]
    return None


def context_item_template(d: Document, index: int) -> str:
    """Render a document as a citation line for context injection."""
    out = '- '
    ref = (d.metadata and (d.metadata.get('ref') or d.metadata.get('id'))) or index
    out += f'[{ref}]: '
    out += text_from_content(d.content) + '\n'
    return out


# =============================================================================
# validate_support()
# =============================================================================


def validate_support(
    name: str,
    supports: Supports | None = None,
) -> ModelMiddleware:
    """Middleware that validates request against model capabilities.

    Args:
        name: The model name (for error messages).
        supports: The model's capability flags.

    Returns:
        A middleware function that validates requests.

    Raises:
        GenkitError: With INVALID_ARGUMENT status if validation fails.
    """

    async def middleware(
        req: ModelRequest,
        ctx: ActionRunContext,
        next_middleware: Callable[..., Awaitable[ModelResponse]],
    ) -> ModelResponse:
        if supports is None:
            return await next_middleware(req, ctx)

        # Check media support
        if supports.media is False:
            for msg in req.messages:
                for part in msg.content:
                    if hasattr(part.root, 'media') and part.root.media is not None:
                        raise GenkitError(
                            status='INVALID_ARGUMENT',
                            message=f"Model '{name}' does not support media, but media was provided.",
                        )

        # Check tools support
        if supports.tools is False and req.tools:
            raise GenkitError(
                status='INVALID_ARGUMENT',
                message=f"Model '{name}' does not support tool use, but tools were provided.",
            )

        # Check multiturn support
        if supports.multiturn is False and len(req.messages) > 1:
            raise GenkitError(
                status='INVALID_ARGUMENT',
                message=f"Model '{name}' does not support multiple messages, but {len(req.messages)} were provided.",
            )

        # Check system role support
        if supports.system_role is False:
            for msg in req.messages:
                if msg.role == 'system':
                    raise GenkitError(
                        status='INVALID_ARGUMENT',
                        message=f"Model '{name}' does not support system role, but system role was provided.",
                    )

        # Check tool choice support
        if supports.tool_choice is False and req.tool_choice and req.tool_choice != 'auto':
            raise GenkitError(
                status='INVALID_ARGUMENT',
                message=f"Model '{name}' does not support tool choice, but tool choice was provided.",
            )

        return await next_middleware(req, ctx)

    return middleware


# =============================================================================
# download_request_media()
# =============================================================================


def download_request_media(
    max_bytes: int | None = None,
    filter_fn: Callable[[Part], bool] | None = None,
) -> ModelMiddleware:
    """Middleware that downloads HTTP media URLs and converts to base64 data URIs.

    Args:
        max_bytes: Maximum number of bytes to download per media item.
        filter_fn: Optional function to filter which parts to process.
            Return True to download, False to skip.

    Returns:
        A middleware function that inlines media URLs.

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

    async def middleware(
        req: ModelRequest,
        ctx: ActionRunContext,
        next_middleware: Callable[..., Awaitable[ModelResponse]],
    ) -> ModelResponse:
        async with httpx.AsyncClient() as client:
            new_messages: list[Message] = []

            for msg in req.messages:
                new_content: list[Part] = []
                content_changed = False

                for part in msg.content:
                    # Check if this is a MediaPart with an HTTP URL
                    if isinstance(part.root, MediaPart) and part.root.media.url.startswith('http'):
                        # Apply filter if provided
                        if filter_fn is not None and not filter_fn(part):
                            new_content.append(part)
                            continue

                        content_changed = True
                        try:
                            # Download the media
                            response = await client.get(part.root.media.url)
                            response.raise_for_status()

                            # Read content (with optional size limit)
                            content = response.content
                            if max_bytes is not None and len(content) > max_bytes:
                                content = content[:max_bytes]

                            # Get content type from response or original part
                            content_type = part.root.media.content_type or response.headers.get(
                                'content-type', 'application/octet-stream'
                            )

                            # Convert to base64 data URI
                            b64_data = base64.b64encode(content).decode('utf-8')
                            data_uri = f'data:{content_type};base64,{b64_data}'

                            # Create new media part with data URI
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

                # Create new message with updated content
                if content_changed:
                    new_messages.append(Message(role=msg.role, content=new_content, metadata=msg.metadata))
                elif isinstance(msg, Message):
                    new_messages.append(msg)
                else:
                    new_messages.append(Message(message=msg))

        # Create new request with updated messages
        new_req = req.model_copy(update={'messages': new_messages})
        return await next_middleware(new_req, ctx)

    return middleware


# =============================================================================
# simulate_system_prompt()
# =============================================================================


def simulate_system_prompt(
    preface: str = 'SYSTEM INSTRUCTIONS:\n',
    acknowledgement: str = 'Understood.',
) -> ModelMiddleware:
    r"""Middleware that simulates system prompt for models without native support.

    Converts system messages to user+model message pairs.

    Args:
        preface: Text to prepend to the system content (default: "SYSTEM INSTRUCTIONS:\\n").
        acknowledgement: Model's acknowledgement response (default: "Understood.").

    Returns:
        A middleware function that transforms system messages.
    """

    async def middleware(
        req: ModelRequest,
        ctx: ActionRunContext,
        next_middleware: Callable[..., Awaitable[ModelResponse]],
    ) -> ModelResponse:
        # Find and transform ONLY THE FIRST system message (matches JS/Go behavior)
        new_messages: list[Message] = []
        system_found = False

        for msg in req.messages:
            if msg.role == 'system' and not system_found:
                # Convert system message to user message with preface
                user_content: list[Part] = [Part(root=TextPart(text=preface))]
                user_content.extend(msg.content)
                new_messages.append(Message(role='user', content=user_content))

                # Add model acknowledgement
                new_messages.append(
                    Message(
                        role='model',
                        content=[Part(root=TextPart(text=acknowledgement))],
                    )
                )
                system_found = True  # Only transform first system message
            else:
                # Wrap in Message if needed
                if isinstance(msg, Message):
                    new_messages.append(msg)
                else:
                    new_messages.append(Message(message=msg))

        # Create new request with transformed messages
        new_req = req.model_copy(update={'messages': new_messages})
        return await next_middleware(new_req, ctx)

    return middleware


# =============================================================================
# augment_with_context()
# =============================================================================


def augment_with_context(
    preface: str | None = CONTEXT_PREFACE,
    item_template: Callable[[Document, int], str] | None = None,
    citation_key: str | None = None,
) -> ModelMiddleware:
    """Middleware that injects document context into the last user message.

    Args:
        preface: Text to prepend before context (default: CONTEXT_PREFACE).
            Pass None to omit preface.
        item_template: Function to render each document (default: context_item_template).
        citation_key: Metadata key to use for citations (default: uses 'ref', 'id', or index).

    Returns:
        A middleware function that injects context.
    """
    template_fn = item_template or context_item_template

    async def middleware(
        req: ModelRequest,
        ctx: ActionRunContext,
        next_middleware: Callable[..., Awaitable[ModelResponse]],
    ) -> ModelResponse:
        if not req.docs:
            return await next_middleware(req, ctx)

        user_message = last_user_message(req.messages)  # type: ignore[arg-type]
        if not user_message:
            return await next_middleware(req, ctx)

        # Check for existing context part
        context_part_index = -1
        for i, part in enumerate(user_message.content):
            part_metadata = part.root.metadata
            if isinstance(part_metadata, Metadata) and part_metadata.root.get('purpose') == 'context':
                context_part_index = i
                break

        context_part = user_message.content[context_part_index] if context_part_index >= 0 else None

        # If context already exists and not pending, skip
        if context_part:
            metadata = context_part.root.metadata
            if not (isinstance(metadata, Metadata) and metadata.root.get('pending')):
                return await next_middleware(req, ctx)

        # Build context string
        out = preface or ''
        for i, doc_data in enumerate(req.docs):
            doc = Document(content=doc_data.content, metadata=doc_data.metadata)
            # Override citation if citation_key is specified
            if citation_key and doc.metadata:
                doc.metadata['ref'] = doc.metadata.get(citation_key, i)
            out += template_fn(doc, i)
        out += '\n'

        # Create context part
        text_part = Part(root=TextPart(text=out, metadata=Metadata(root={'purpose': 'context'})))

        # Insert or replace context part
        if context_part_index >= 0:
            user_message.content[context_part_index] = text_part
        else:
            if not user_message.content:
                user_message.content = []
            user_message.content.append(text_part)

        return await next_middleware(req, ctx)

    return middleware


# =============================================================================
# retry()
# =============================================================================


def retry(
    max_retries: int = 3,
    statuses: list[StatusName] | None = None,
    initial_delay_ms: int = 1000,
    max_delay_ms: int = 60000,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    on_error: Callable[[Exception, int], None] | None = None,
) -> ModelMiddleware:
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
        A middleware function that implements retry logic.
    """
    retry_statuses = statuses or DEFAULT_RETRY_STATUSES

    async def middleware(
        req: ModelRequest,
        ctx: ActionRunContext,
        next_middleware: Callable[..., Awaitable[ModelResponse]],
    ) -> ModelResponse:
        last_error: Exception | None = None
        current_delay_ms: float = float(initial_delay_ms)

        for attempt in range(int(max_retries) + 1):
            try:
                return await next_middleware(req, ctx)
            except Exception as e:
                last_error = e

                # Check if we should retry
                if attempt < max_retries:
                    should_retry = False

                    if isinstance(e, GenkitError) and e.status in retry_statuses:
                        should_retry = True
                    elif not isinstance(e, GenkitError):
                        # Retry non-GenkitError exceptions
                        should_retry = True

                    if should_retry:
                        if on_error:
                            on_error(e, attempt + 1)

                        # Calculate delay with optional jitter
                        delay = current_delay_ms
                        if jitter:
                            # Add jitter: delay + random(0, 2^attempt * 1000)
                            delay = delay + random.random() * (2**attempt) * 1000

                        # Wait before retry
                        await asyncio.sleep(delay / 1000.0)

                        # Update delay for next attempt
                        current_delay_ms = min(current_delay_ms * backoff_factor, float(max_delay_ms))
                        continue

                # Don't retry - re-raise the error
                raise

        # Should not reach here, but raise last error if we do
        if last_error:
            raise last_error
        raise RuntimeError('Retry loop completed without result')

    return middleware


# =============================================================================
# fallback()
# =============================================================================


def fallback(
    registry: Registry,
    models: list[str],
    statuses: list[StatusName] | None = None,
    on_error: Callable[[Exception], None] | None = None,
) -> ModelMiddleware:
    """Middleware that falls back to alternative models on failure.

    Args:
        registry: The registry to resolve model references (internal; use fallback(ai, ...) from genkit.middleware).
        models: Ordered list of fallback model names to try.
        statuses: List of status codes that trigger fallback (default: UNAVAILABLE,
            DEADLINE_EXCEEDED, RESOURCE_EXHAUSTED, ABORTED, INTERNAL, NOT_FOUND,
            UNIMPLEMENTED).
        on_error: Optional callback called when fallback is triggered.

    Returns:
        A middleware function that implements fallback logic.
    """
    fallback_statuses = statuses or DEFAULT_FALLBACK_STATUSES

    async def middleware(
        req: ModelRequest,
        ctx: ActionRunContext,
        next_middleware: Callable[..., Awaitable[ModelResponse]],
    ) -> ModelResponse:
        try:
            return await next_middleware(req, ctx)
        except Exception as e:
            # Check if this error should trigger fallback
            if isinstance(e, GenkitError) and e.status in fallback_statuses:
                if on_error:
                    on_error(e)

                last_error: Exception = e

                # Try each fallback model
                for model_name in models:
                    try:
                        # Resolve and call the fallback model
                        model = await registry.resolve_model(model_name)
                        if model is None:
                            raise GenkitError(
                                status='NOT_FOUND',
                                message=f"Fallback model '{model_name}' not found.",
                            )

                        result = await model.run(
                            input=req,
                            context=ctx.context,
                            on_chunk=ctx.send_chunk if ctx.is_streaming else None,
                        )
                        return result.response

                    except Exception as e2:
                        last_error = e2
                        if isinstance(e2, GenkitError) and e2.status in fallback_statuses:
                            if on_error:
                                on_error(e2)
                            continue
                        # Non-fallbackable error, re-raise
                        raise

                # All fallbacks failed
                raise last_error from None

            # Not a fallbackable error, re-raise
            raise

    return middleware


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'CONTEXT_PREFACE',
    'DEFAULT_FALLBACK_STATUSES',
    'DEFAULT_RETRY_STATUSES',
    'augment_with_context',
    'download_request_media',
    'fallback',
    'retry',
    'simulate_system_prompt',
    'validate_support',
]
