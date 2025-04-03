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

from genkit.ai.base import GenkitRegistry
from genkit.ai.plugin import Plugin
from genkit.blocks.document import Document
from genkit.blocks.tools import ToolRunContext, tool_response
from genkit.core import GENKIT_CLIENT_HEADER, GENKIT_VERSION
from genkit.core.action import ActionRunContext
from genkit.core.action.types import ActionKind

from .aio import Genkit

__all__ = [
    ActionKind.__name__,
    ActionRunContext.__name__,
    Document.__name__,
    GenkitRegistry.__name__,
    Genkit.__name__,
    Plugin.__name__,
    ToolRunContext.__name__,
    tool_response.__name__,
    'GENKIT_CLIENT_HEADER',
    'GENKIT_VERSION',
]
