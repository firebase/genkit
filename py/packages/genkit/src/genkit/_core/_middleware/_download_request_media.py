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

"""download_request_media middleware."""

import base64
from collections.abc import Awaitable, Callable

import httpx

from genkit._ai._model import Message
from genkit._core._error import GenkitError
from genkit._core._model import ModelResponse
from genkit._core._typing import Media, MediaPart, Part

from ._base import BaseMiddleware, ModelHookParams
from ._utils import _is_safe_url


def download_request_media(
    max_bytes: int | None = None,
    filter_fn: Callable[[Part], bool] | None = None,
) -> BaseMiddleware:
    """Middleware that downloads HTTP media URLs and converts to base64 data URIs."""
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
        params: ModelHookParams,
        next_fn: Callable[[ModelHookParams], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        req = params.request
        async with httpx.AsyncClient() as client:
            new_messages: list[Message] = []

            for msg in req.messages:
                new_content: list[Part] = []
                content_changed = False

                for part in msg.content:
                    if isinstance(part.root, MediaPart) and part.root.media.url.startswith(
                        'http'
                    ):
                        if not _is_safe_url(part.root.media.url):
                            raise GenkitError(
                                status='INVALID_ARGUMENT',
                                message=f"Media URL is not allowed (SSRF protection): '{part.root.media.url}'",
                            )
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
                    new_messages.append(
                        Message(role=msg.role, content=new_content, metadata=msg.metadata)
                    )
                else:
                    new_messages.append(msg)

            new_req = req.model_copy(update={'messages': new_messages})
            return await next_fn(
                ModelHookParams(
                    request=new_req,
                    on_chunk=params.on_chunk,
                    context=params.context,
                )
            )
