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

"""Model protocol types for plugin authors."""

from genkit._ai._model import (
    ModelConfig,
    model_action_metadata,
    model_ref,
)
from genkit._core._background import BackgroundAction
from collections.abc import Awaitable, Callable
from typing import Any

from genkit._core._action import ActionRunContext
from genkit._core._model import (
    Message,
    ModelRef,
    ModelRequest,
    ModelResponse,
    ModelResponseChunk,
    get_basic_usage_stats,
)
from genkit._core._typing import (
    Candidate,
    Constrained,
    Error,
    FinishReason,
    GenerateActionOptions,
    GenerationUsage,
    ModelInfo,
    Operation,
    OutputConfig,
    Stage,
    Supports,
    ToolDefinition,
    ToolRequest,
    ToolResponse,
)

# Type alias for the next() handler passed to model middleware
ModelMiddlewareNext = Callable[[ModelRequest, ActionRunContext], Awaitable[ModelResponse[Any]]]

__all__ = [
    # Request/Response types
    'BackgroundAction',
    'ModelRequest',
    'ModelResponse',
    'ModelResponseChunk',
    # Usage and metadata
    'GenerationUsage',
    'Candidate',
    'OutputConfig',
    'FinishReason',
    'GenerateActionOptions',
    # Error and operation
    'Error',
    'Operation',
    # Tool types
    'ToolRequest',
    'ToolDefinition',
    'ToolResponse',
    # Model info
    'ModelInfo',
    'Supports',
    'Constrained',
    'Stage',
    # Factory functions and metadata
    'model_action_metadata',
    'model_ref',
    # Reference types
    'ModelRef',
    # Config
    'ModelConfig',
    # Message
    'Message',
    # Middleware
    'ModelMiddlewareNext',
    # Usage
    'get_basic_usage_stats',
]
