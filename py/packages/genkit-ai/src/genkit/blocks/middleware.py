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

from collections.abc import Awaitable, Callable
from functools import cached_property
from typing import Any

from pydantic import Field

from genkit.blocks.model import (
    ModelMiddleware,
    ModelMiddlewareNext,
    text_from_content,
)
from genkit.core.action import ActionRunContext
from genkit.core.typing import (
    DocumentData,
    GenerateRequest,
    GenerateResponse,
    Message,
    Part,
    TextPart,
)

CONTEXT_PREFACE = '\n\nUse the following information to complete your task:\n\n'


def context_item_template(d: DocumentData, index: int) -> str:
    """
    Renders a document into a text part.

    Uses 'ref', 'id', or index as citation, if no citationKey is available.
    """
    out = '- '
    ref = (d.metadata and (d.metadata.get('ref') or d.metadata.get('id'))) or index
    out += f'[{ref}]: '
    out += text_from_content(d.content) + '\n'
    return out


def augment_with_context() -> ModelMiddleware:
    """
    Middleware to augment the user's message with context from provided documents.
    """

    async def middleware(
        req: GenerateRequest,
        ctx: ActionRunContext,
        next_middleware: ModelMiddlewareNext,
    ) -> Awaitable[GenerateResponse]:
        if not req.docs:
            return await next_middleware(req, ctx)

        user_message = last_user_message(req.messages)
        if not user_message:
            return await next_middleware(req, ctx)

        context_part_index = -1
        for i, part in enumerate(user_message.content):
            if part.root.metadata and part.root.metadata.root.get('purpose') == 'context':
                context_part_index = i
                break

        context_part = user_message.content[context_part_index] if context_part_index >= 0 else None

        if context_part and not context_part.root.metadata.root.get('pending'):
            return await next_middleware(req, ctx)

        out = CONTEXT_PREFACE
        for i, doc_data in enumerate(req.docs):
            doc = DocumentData(content=doc_data.content, metadata=doc_data.metadata)
            out += context_item_template(doc, i)
        out += '\n'

        text_part = Part(root=TextPart(text=out, metadata={'purpose': 'context'}))
        if context_part_index >= 0:
            user_message.content[context_part_index] = text_part
        else:
            if not user_message.content:
                user_message.content = []
            user_message.content.append(text_part)

        return await next_middleware(req, ctx)

    return middleware


def last_user_message(messages: list[Message]) -> Message | None:
    """
    Finds the last message with the role 'user' in a list of messages.

    Args:
        messages: A list of message dictionaries.

    Returns:
        The last message with the role 'user', or None if no such message exists.
    """
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].role == 'user':
            return messages[i]
    return None
