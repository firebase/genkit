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

"""Abstract middleware runtime hook signatures.

``MiddlewareRuntime`` lives here with types from ``genkit._core._model`` and
``genkit._core._typing`` only (no ``BaseMiddleware`` / registry imports), keeping this
module low in the middleware import graph.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from genkit._core._model import GenerateHookParams, ModelHookParams, ModelResponse, ToolHookParams
from genkit._core._typing import ToolRequestPart, ToolResponsePart


class MiddlewareRuntime(ABC):
    """Abstract hook contract implemented by ``BaseMiddleware`` at runtime.

    ``BaseMiddleware`` subclasses this and provides default pass-through behavior.
    """

    @abstractmethod
    def wrap_generate(
        self,
        params: GenerateHookParams,
        next_fn: Callable[[GenerateHookParams], Awaitable[ModelResponse]],
    ) -> Awaitable[ModelResponse]:
        """Wrap each iteration of the tool loop (model call + optional tool resolution)."""

    @abstractmethod
    def wrap_model(
        self,
        params: ModelHookParams,
        next_fn: Callable[[ModelHookParams], Awaitable[ModelResponse]],
    ) -> Awaitable[ModelResponse]:
        """Wrap each model API call."""

    @abstractmethod
    def wrap_tool(
        self,
        params: ToolHookParams,
        next_fn: Callable[
            [ToolHookParams],
            Awaitable[tuple[ToolResponsePart | None, ToolRequestPart | None]],
        ],
    ) -> Awaitable[tuple[ToolResponsePart | None, ToolRequestPart | None]]:
        """Wrap each tool execution.

        Return ``(tool_response, interrupt)``: one of the tuple elements is non-``None``.
        """
