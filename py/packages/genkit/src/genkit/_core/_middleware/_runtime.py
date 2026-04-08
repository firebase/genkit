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

"""Abstract middleware runtime hooks (leaf module: avoids importing genkit._core._model)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MiddlewareRuntime(ABC):
    """Abstract contract for values allowed inline in GenerateActionOptions.use.

    BaseMiddleware subclasses this and provides default pass-through behavior. Keeping
    this type in a leaf module lets genkit._core._model validate use with isinstance
    without importing the full middleware base module.
    """

    @abstractmethod
    def wrap_generate(self, params: Any, next_fn: Any) -> Any:
        """Wrap each iteration of the tool loop (model call + optional tool resolution)."""

    @abstractmethod
    def wrap_model(self, params: Any, next_fn: Any) -> Any:
        """Wrap each model API call."""

    @abstractmethod
    def wrap_tool(self, params: Any, next_fn: Any) -> Any:
        """Wrap each tool execution."""
