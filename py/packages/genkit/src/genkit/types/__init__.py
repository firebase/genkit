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

"""User-facing types for Genkit.

This module exports all types that users may need when building Genkit applications.
For the main Genkit class, import from `genkit` directly.
"""

from genkit.blocks.document import Document
from genkit.blocks.tools import ToolInterruptError
from genkit.core.error import GenkitError
from genkit.core.typing import (
    # Eval types
    BaseEvalDataPoint,
    CustomPart,
    DataPart,
    # Document types
    DocumentData,
    # Embedding types
    Embedding,
    EmbedRequest,
    EmbedResponse,
    EvalFnResponse,
    EvalRequest,
    EvalResponse,
    EvalStatusEnum,
    FinishReason,
    GenerateActionOptions,
    # Generation types
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationCommonConfig,
    GenerationUsage,
    Media,
    MediaPart,
    # Message and Part types
    Message,
    # Model info (for plugin authors)
    ModelInfo,
    OutputConfig,
    Part,
    ReasoningPart,
    # Retriever types
    RetrieverRequest,
    RetrieverResponse,
    Role,
    Supports,
    TextPart,
    ToolChoice,
    ToolDefinition,
    # Tool types
    ToolRequest,
    ToolRequestPart,
    ToolResponse,
    ToolResponsePart,
)

__all__ = [
    # Errors
    'GenkitError',
    'ToolInterruptError',
    # Message and Part types
    'Message',
    'Part',
    'TextPart',
    'MediaPart',
    'Media',
    'CustomPart',
    'DataPart',
    'ReasoningPart',
    'ToolRequestPart',
    'ToolResponsePart',
    'Role',
    # Document types
    'Document',
    'DocumentData',
    # Generation types
    'GenerateRequest',
    'GenerateResponse',
    'GenerateResponseChunk',
    'GenerationCommonConfig',
    'GenerationUsage',
    'OutputConfig',
    'GenerateActionOptions',
    'FinishReason',
    'ToolChoice',
    # Tool types
    'ToolRequest',
    'ToolResponse',
    'ToolDefinition',
    # Embedding types
    'Embedding',
    'EmbedRequest',
    'EmbedResponse',
    # Retriever types
    'RetrieverRequest',
    'RetrieverResponse',
    # Eval types
    'BaseEvalDataPoint',
    'EvalRequest',
    'EvalResponse',
    'EvalFnResponse',
    'EvalStatusEnum',
    # Model info (for plugin authors)
    'ModelInfo',
    'Supports',
]
