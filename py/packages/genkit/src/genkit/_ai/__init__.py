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

"""Genkit AI module - core Genkit class and related utilities."""

from genkit._core._constants import GENKIT_CLIENT_HEADER, GENKIT_VERSION
from genkit._core._plugin import Plugin
from genkit._core._action import Action, ActionKind, ActionRunContext
from genkit._ai._document import Document
from genkit._ai._model import ModelResponse
from genkit._ai._prompt import (
    ExecutablePrompt,
    ModelStreamResponse,
    PromptGenerateOptions,
    ResumeOptions,
)
from genkit._ai._tools import ToolRunContext

from ._aio import Genkit

__all__ = [
    # Version info
    'GENKIT_CLIENT_HEADER',
    'GENKIT_VERSION',
    # Main class
    'Genkit',
    # Actions
    'ActionKind',
    'ActionRunContext',
    # Document
    'Document',
    # Prompts
    'ExecutablePrompt',
    'PromptGenerateOptions',
    'ResumeOptions',
    # Registry and flow
    # Response types
    'ModelResponse',
    'ModelStreamResponse',
    # Tools
    'ToolRunContext',
    # Plugin
    'Plugin',
    'Action',
]
