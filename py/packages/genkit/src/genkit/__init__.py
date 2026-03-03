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

"""Genkit — Build AI-powered applications.

Basic usage:
    from genkit import Genkit
    from genkit.plugins.google_genai import GoogleAI

    ai = Genkit(plugins=[GoogleAI()])

    @ai.flow()
    async def hello(name: str) -> str:
        response = await ai.generate(model='gemini-2.0-flash', prompt=f'Hello {name}')
        return response.text
"""

from genkit.ai import (
    ActionKind,
    ActionRunContext,
    ExecutablePrompt,
    ModelStreamResponse,
    PromptGenerateOptions,
    ResumeOptions,
    ToolRunContext,
)
from genkit.ai._aio import Genkit
from genkit.ai.document import Document
from genkit.ai.model import Message, ModelConfig, ModelResponse
from genkit.ai.tools import ToolInterruptError
from genkit.core._internal._typing import (
    Embedding,
    FinishReason,
    GenerationUsage,
    Media,
    MediaPart,
    ModelRequest,
    Part,
    Role,
    TextPart,
    ToolChoice,
    ToolRequestPart,
    ToolResponsePart,
)
from genkit.core._plugins import extend_plugin_namespace
from genkit.core.error import GenkitError, PublicError
from genkit.core.plugin import Plugin

extend_plugin_namespace()

__all__ = [
    # Main class
    'Genkit',
    # Response types
    'ModelResponse',
    'ModelStreamResponse',
    # Errors
    'GenkitError',
    'PublicError',
    'ToolInterruptError',
    # Content types
    'Embedding',
    'FinishReason',
    'GenerationUsage',
    'Media',
    'MediaPart',
    'Message',
    'ModelRequest',
    'Part',
    'Role',
    'TextPart',
    'ToolChoice',
    'ToolRequestPart',
    'ToolResponsePart',
    # Domain types
    'Document',
    'ModelConfig',
    # Plugin interface
    'Plugin',
    # AI runtime
    'ActionKind',
    'ActionRunContext',
    'ExecutablePrompt',
    'PromptGenerateOptions',
    'ResumeOptions',
    'ToolRunContext',
]
