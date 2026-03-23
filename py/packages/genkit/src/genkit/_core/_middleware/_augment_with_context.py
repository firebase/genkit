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

"""augment_with_context middleware."""

from collections.abc import Awaitable, Callable

from genkit._core._model import Document, ModelResponse
from genkit._core._typing import Part, TextPart

from ._base import BaseMiddleware, ModelHookParams
from ._utils import _CONTEXT_PREFACE, _context_item_template, _last_user_message


def augment_with_context(
    preface: str | None = _CONTEXT_PREFACE,
    item_template: Callable[[Document, int], str] | None = None,
    citation_key: str | None = None,
) -> BaseMiddleware:
    """Middleware that injects document context into the last user message."""
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
        params: ModelHookParams,
        next_fn: Callable[[ModelHookParams], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        req = params.request
        if not req.docs:
            return await next_fn(params)

        user_message = _last_user_message(req.messages)  # type: ignore[arg-type]
        if not user_message:
            return await next_fn(params)

        context_part_index = -1
        for i, part in enumerate(user_message.content):
            part_metadata = part.root.metadata if hasattr(part.root, 'metadata') else None
            if isinstance(part_metadata, dict) and part_metadata.get('purpose') == 'context':
                context_part_index = i
                break

        context_part = user_message.content[context_part_index] if context_part_index >= 0 else None

        if context_part:
            metadata = (
                context_part.root.metadata
                if hasattr(context_part.root, 'metadata')
                else None
            )
            if not (isinstance(metadata, dict) and metadata.get('pending')):
                return await next_fn(params)

        out = self._preface or ''
        for i, doc_data in enumerate(req.docs):
            doc = Document(content=doc_data.content, metadata=doc_data.metadata)
            if self._citation_key and doc.metadata:
                doc.metadata['ref'] = doc.metadata.get(self._citation_key, i)
            out += self._item_template(doc, i)
        out += '\n'

        text_part = Part(root=TextPart(text=out, metadata={'purpose': 'context'}))

        if context_part_index >= 0:
            user_message.content[context_part_index] = text_part
        else:
            if not user_message.content:
                user_message.content = []
            user_message.content.append(text_part)

        return await next_fn(params)
