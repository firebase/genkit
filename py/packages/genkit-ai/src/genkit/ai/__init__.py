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

"""Veneer package for managing server and client interactions.

This package provides functionality for managing server-side operations,
including server configuration, runtime management, and client-server
communication protocols.
"""

from genkit.ai.plugin import Plugin
from genkit.ai.veneer import Genkit, GenkitRegistry
from genkit.blocks.document import Document
from genkit.blocks.tools import ToolRunContext, tool_response
from genkit.core.action import ActionKind, ActionRunContext
from genkit.core.typing import (
    CustomPart,
    DataPart,
    Embedding,
    EmbedRequest,
    EmbedResponse,
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
    Supports,
    TextPart,
    ToolDefinition,
    ToolRequest,
    ToolRequestPart,
    ToolResponse,
    ToolResponsePart,
)

__all__ = [
    ActionRunContext.__name__,
    Document.__name__,
    Embedding.__name__,
    EmbedRequest.__name__,
    EmbedResponse.__name__,
    GenerateRequest.__name__,
    GenerateResponse.__name__,
    GenerateResponseChunk.__name__,
    Genkit.__name__,
    GenkitRegistry.__name__,
    Media.__name__,
    Message.__name__,
    Plugin.__name__,
    RetrieverRequest.__name__,
    RetrieverResponse.__name__,
    Role.__name__,
    ToolRunContext.__name__,
    ToolResponse.__name__,
    ToolRequest.__name__,
    Part.__name__,
    ModelInfo.__name__,
    Supports.__name__,
    ActionKind.__name__,
    TextPart.__name__,
    MediaPart.__name__,
    DataPart.__name__,
    CustomPart.__name__,
    ToolRequestPart.__name__,
    ToolResponsePart.__name__,
    GenerationCommonConfig.__name__,
    GenerationUsage.__name__,
    ToolDefinition.__name__,
    tool_response.__name__,
]
