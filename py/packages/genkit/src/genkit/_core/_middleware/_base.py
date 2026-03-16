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

"""Base middleware protocol, params, and default implementation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import ClassVar, Protocol

from pydantic import BaseModel, ConfigDict, Field

from genkit._ai._model import ModelRequest, ModelResponse, ModelResponseChunk
from genkit._core._action import Action
from genkit._core._typing import GenerateActionOptions, Part, ToolRequestPart


class Middleware(Protocol):
    """Middleware with hooks for Generate loop, Model call, and Tool execution.

    Use [BaseMiddleware] as a base to implement only the hooks you need.
    """

    def wrap_generate(
        self,
        params: GenerateHookParams,
        next_fn: Callable[[GenerateHookParams], Awaitable[ModelResponse]],
    ) -> Awaitable[ModelResponse]:
        """Wrap each iteration of the tool loop (model call + optional tool resolution)."""
        ...

    def wrap_model(
        self,
        params: ModelHookParams,
        next_fn: Callable[[ModelHookParams], Awaitable[ModelResponse]],
    ) -> Awaitable[ModelResponse]:
        """Wrap each model API call."""
        ...

    def wrap_tool(
        self,
        params: ToolHookParams,
        next_fn: Callable[[ToolHookParams], Awaitable[tuple[Part | None, Part | None]]],
    ) -> Awaitable[tuple[Part | None, Part | None]]:
        """Wrap each tool execution."""
        ...


class GenerateHookParams(BaseModel):
    """Params for the wrap_generate hook."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    options: GenerateActionOptions
    request: ModelRequest
    iteration: int


class ModelHookParams(BaseModel):
    """Params for the wrap_model hook."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    request: ModelRequest
    on_chunk: Callable[[ModelResponseChunk], None] | None = None
    context: dict[str, object] = Field(default_factory=dict)


class ToolHookParams(BaseModel):
    """Params for the wrap_tool hook."""

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    tool_request_part: ToolRequestPart
    tool: Action


class BaseMiddleware:
    """Base middleware with pass-through defaults. Override only the hooks you need."""

    def wrap_generate(
        self,
        params: GenerateHookParams,
        next_fn: Callable[[GenerateHookParams], Awaitable[ModelResponse]],
    ) -> Awaitable[ModelResponse]:
        return next_fn(params)

    def wrap_model(
        self,
        params: ModelHookParams,
        next_fn: Callable[[ModelHookParams], Awaitable[ModelResponse]],
    ) -> Awaitable[ModelResponse]:
        return next_fn(params)

    def wrap_tool(
        self,
        params: ToolHookParams,
        next_fn: Callable[[ToolHookParams], Awaitable[tuple[Part | None, Part | None]]],
    ) -> Awaitable[tuple[Part | None, Part | None]]:
        return next_fn(params)
