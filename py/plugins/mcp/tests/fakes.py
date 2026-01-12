# Copyright 2026 Google LLC
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

import asyncio
import json
import sys
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import MagicMock

from genkit.ai import Genkit
from genkit.core.action.types import ActionKind


class MockSchema:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def mock_mcp_modules():
    """Sets up comprehensive MCP mocks in sys.modules."""
    mock_mcp = MagicMock()
    sys.modules['mcp'] = mock_mcp
    sys.modules['mcp'].__path__ = []

    types_mock = MagicMock()
    sys.modules['mcp.types'] = types_mock
    types_mock.ListToolsResult = MockSchema
    types_mock.CallToolResult = MockSchema
    types_mock.ListPromptsResult = MockSchema
    types_mock.GetPromptResult = MockSchema
    types_mock.ListResourcesResult = MockSchema
    types_mock.ListResourceTemplatesResult = MockSchema
    types_mock.ReadResourceResult = MockSchema
    types_mock.Tool = MockSchema
    types_mock.Prompt = MockSchema
    types_mock.Resource = MockSchema
    types_mock.ResourceTemplate = MockSchema
    types_mock.TextContent = MockSchema
    types_mock.PromptMessage = MockSchema
    types_mock.TextResourceContents = MockSchema
    types_mock.BlobResourceContents = MockSchema
    types_mock.ImageContent = MockSchema

    sys.modules['mcp.server'] = MagicMock()
    sys.modules['mcp.server.stdio'] = MagicMock()
    sys.modules['mcp.client'] = MagicMock()
    sys.modules['mcp.client'].__path__ = []
    sys.modules['mcp.client.stdio'] = MagicMock()
    sys.modules['mcp.client.sse'] = MagicMock()
    sys.modules['mcp.server.sse'] = MagicMock()

    return mock_mcp, types_mock


def define_echo_model(ai: Genkit):
    """Defines a fake echo model for testing."""

    @ai.tool(name='echoModel')
    def echo_model(request: Any):
        # This is a simplified mock of a model action
        # Real model action would handle GenerateRequest and return GenerateResponse

        # logic to echo content
        # For now, just a placeholder as we generally mock the model execution in tests
        pass

    # In real usage, we would define a Model action properly.
    # For unit tests here, we might not strictly need the full model implementation
    # if we are mocking the generation or call.
    # But matching JS behavior:
    # JS defines 'echoModel' which returns "Echo: " + input.

    # We can use ai.define_model if available or just mock it.
    pass


class FakeTransport:
    """Fakes an MCP transport/server for testing."""

    def __init__(self):
        self.tools = []
        self.prompts = []
        self.resources = []
        self.resource_templates = []
        self.call_tool_result = None
        self.get_prompt_result = None
        self.read_resource_result = None
        self.roots = []

        # Callbacks that would simulate transport behavior
        self.on_message = None
        self.on_close = None
        self.on_error = None

    async def start(self):
        pass

    async def send(self, message: Dict[str, Any]):
        """Handle incoming JSON-RPC message (simulating server)."""
        request = message
        # msg_id = request.get("id")

        # In a real transport we'd write back to the stream.
        # Here we just store handling logic or print.
        # Since we are mocking the ClientSession in our python tests,
        # this logic might need to be hooked up to the mock session's methods.
        pass

    # Helper methods to populate the fake state
    def add_tool(self, name: str, description: str = '', schema: Dict = None):
        self.tools.append({'name': name, 'description': description, 'inputSchema': schema or {'type': 'object'}})

    def add_prompt(self, name: str, description: str = '', arguments: List = None):
        self.prompts.append({'name': name, 'description': description, 'arguments': arguments or []})
