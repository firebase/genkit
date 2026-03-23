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

"""validate_support middleware."""

from collections.abc import Awaitable, Callable

from genkit._core._error import GenkitError
from genkit._core._model import ModelResponse
from genkit._core._typing import MediaPart, Supports

from ._base import BaseMiddleware, ModelHookParams


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
        params: ModelHookParams,
        next_fn: Callable[[ModelHookParams], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        req = params.request
        if self._supports is None:
            return await next_fn(params)

        if self._supports.media is False:
            for msg in req.messages:
                for part in msg.content:
                    if (
                        isinstance(part.root, MediaPart)
                        and part.root.media is not None
                    ):
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
                message=(
                    f"Model '{self._name}' does not support multiple messages, but {len(req.messages)} were provided."
                ),
            )

        if self._supports.system_role is False:
            for msg in req.messages:
                if msg.role == 'system':
                    raise GenkitError(
                        status='INVALID_ARGUMENT',
                        message=f"Model '{self._name}' does not support system role, but system role was provided.",
                    )

        if (
            self._supports.tool_choice is False
            and req.tool_choice
            and req.tool_choice != 'auto'
        ):
            raise GenkitError(
                status='INVALID_ARGUMENT',
                message=f"Model '{self._name}' does not support tool choice, but tool choice was provided.",
            )

        return await next_fn(params)
