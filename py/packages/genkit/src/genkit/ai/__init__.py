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

"""Genkit AI module - core Genkit class and related utilities.

This module provides the main Genkit class for building AI applications.
"""

from genkit.blocks.document import Document
from genkit.blocks.model import GenerateResponseWrapper
from genkit.blocks.prompt import (
    ExecutablePrompt,
    GenerateStreamResponse,
    OutputOptions,
    PromptGenerateOptions,
    ResumeOptions,
)
from genkit.blocks.tools import ToolRunContext, tool_response
from genkit.core import GENKIT_CLIENT_HEADER, GENKIT_VERSION
from genkit.core.action import ActionRunContext
from genkit.core.action.types import ActionKind
from genkit.core.plugin import Plugin
from genkit.session import Chat, ChatOptions, ChatStreamResponse

from ._aio import Genkit, Input, Output
from ._registry import FlowWrapper, GenkitRegistry, SimpleRetrieverOptions

__all__ = [
    # Main class
    'Genkit',
    'Input',
    'Output',
    # Response types
    'GenerateResponseWrapper',
    # Registry and flow
    'GenkitRegistry',
    'FlowWrapper',
    'SimpleRetrieverOptions',
    # Actions
    'ActionKind',
    'ActionRunContext',
    # Tools
    'ToolRunContext',
    'tool_response',
    # Prompts
    'ExecutablePrompt',
    'GenerateStreamResponse',
    'OutputOptions',
    'PromptGenerateOptions',
    'ResumeOptions',
    # Session/Chat
    'Chat',
    'ChatOptions',
    'ChatStreamResponse',
    # Document
    'Document',
    # Plugin
    'Plugin',
    # Version info
    'GENKIT_CLIENT_HEADER',
    'GENKIT_VERSION',
]
