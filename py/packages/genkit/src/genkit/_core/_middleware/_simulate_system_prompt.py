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

"""simulate_system_prompt middleware."""

from collections.abc import Awaitable, Callable

from genkit._ai._model import Message
from genkit._core._model import ModelResponse
from genkit._core._typing import Part, TextPart

from ._base import BaseMiddleware, ModelHookParams


def simulate_system_prompt(
    preface: str = 'SYSTEM INSTRUCTIONS:\n',
    acknowledgement: str = 'Understood.',
) -> BaseMiddleware:
    r"""Middleware that simulates system prompt for models without native support.

    Converts system messages to user+model message pairs.

    Args:
        preface: Text to prepend to the system content.
        acknowledgement: Model's acknowledgement response.

    Returns:
        Middleware that transforms system messages.
    """
    return _SimulateSystemPromptMiddleware(preface=preface, acknowledgement=acknowledgement)


class _SimulateSystemPromptMiddleware(BaseMiddleware):
    def __init__(
        self,
        preface: str = 'SYSTEM INSTRUCTIONS:\n',
        acknowledgement: str = 'Understood.',
    ) -> None:
        self._preface = preface
        self._acknowledgement = acknowledgement

    async def wrap_model(
        self,
        params: ModelHookParams,
        next_fn: Callable[[ModelHookParams], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        req = params.request
        new_messages: list[Message] = []

        for msg in req.messages:
            if msg.role == 'system':
                user_content: list[Part] = [Part(root=TextPart(text=self._preface))]
                user_content.extend(msg.content)
                new_messages.append(Message(role='user', content=user_content))
                new_messages.append(
                    Message(
                        role='model',
                        content=[Part(root=TextPart(text=self._acknowledgement))],
                    )
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
