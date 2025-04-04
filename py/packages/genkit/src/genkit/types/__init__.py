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

"""Types for Genkit users.

Users should import Genkit types from this module.
"""

from genkit.blocks.model import GenerateResponseChunkWrapper, GenerateResponseWrapper, MessageWrapper
from genkit.core.error import GenkitError, StatusName
from genkit.core.typing import (
    BaseEvalDataPoint,
    CustomPart,
    Details,
    Docs,
    DocumentData,
    Embedding,
    EmbedRequest,
    EmbedResponse,
    EvalFnResponse,
    EvalRequest,
    EvalResponse,
    GenerateRequest,
    GenerateResponse,
    GenerateResponseChunk,
    GenerationCommonConfig,
    GenerationUsage,
    Media,
    MediaPart,
    Message,
    ModelInfo,
    Part,
    RetrieverRequest,
    RetrieverResponse,
    Role,
    Score,
    Stage,
    Supports,
    TextPart,
    ToolChoice,
    ToolDefinition,
    ToolRequest,
    ToolRequestPart,
    ToolResponse,
    ToolResponsePart,
)

__all__ = [
    BaseEvalDataPoint.__name__,
    CustomPart.__name__,
    Details.__name__,
    Docs.__name__,
    DocumentData.__name__,
    EmbedRequest.__name__,
    EmbedResponse.__name__,
    Embedding.__name__,
    EvalFnResponse.__name__,
    EvalRequest.__name__,
    EvalResponse.__name__,
    GenerateRequest.__name__,
    GenerateResponse.__name__,
    GenerateResponseChunk.__name__,
    GenerateResponseChunkWrapper.__name__,
    GenerateResponseWrapper.__name__,
    GenerationCommonConfig.__name__,
    GenerationUsage.__name__,
    GenkitError.__name__,
    Media.__name__,
    MediaPart.__name__,
    Message.__name__,
    MessageWrapper.__name__,
    ModelInfo.__name__,
    Part.__name__,
    RetrieverRequest.__name__,
    RetrieverResponse.__name__,
    Role.__name__,
    Score.__name__,
    Stage.__name__,
    StatusName.__name__,
    Supports.__name__,
    TextPart.__name__,
    ToolChoice.__name__,
    ToolDefinition.__name__,
    ToolRequest.__name__,
    ToolRequestPart.__name__,
    ToolResponse.__name__,
    ToolResponsePart.__name__,
]
