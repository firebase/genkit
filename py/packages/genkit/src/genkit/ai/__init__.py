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

"""Genkit is a Python library for building AI applications.

Genkit is an open-source Python toolkit designed to help you build
AI-powered features in web and mobile apps.

It offers a unified interface for integrating AI models from Google, OpenAI,
Anthropic, Ollama, and more, so you can explore and choose the best models for
your needs. Genkit simplifies AI development with streamlined APIs for
multimodal content generation, structured data generation, tool calling,
human-in-the-loop, and other advanced capabilities.

Whether you're building chatbots, intelligent agents, workflow automations, or
recommendation systems, Genkit handles the complexity of AI integration so you
can focus on creating incredible user experiences.
"""

from genkit.blocks.document import Document
from genkit.blocks.tools import ToolRunContext, tool_response
from genkit.core import GENKIT_CLIENT_HEADER, GENKIT_VERSION
from genkit.core.action import ActionRunContext
from genkit.core.action.types import ActionKind

from ._aio import Genkit
from ._plugin import Plugin
from ._registry import FlowWrapper, GenkitRegistry

__all__ = [
    ActionKind.__name__,
    ActionRunContext.__name__,
    Document.__name__,
    GenkitRegistry.__name__,
    Genkit.__name__,
    Plugin.__name__,
    ToolRunContext.__name__,
    tool_response.__name__,
    FlowWrapper.__name__,
    'GENKIT_CLIENT_HEADER',
    'GENKIT_VERSION',
]
