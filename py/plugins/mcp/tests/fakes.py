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


"""Fakes for MCP tests."""

import sys
from typing import Any
from unittest.mock import MagicMock

from genkit.ai import Genkit


class MockSchema:
    """Mock schema."""

    def __init__(self, **kwargs):
        """Initialize mock schema."""
        for k, v in kwargs.items():
            setattr(self, k, v)


def mock_mcp_modules():
    """Sets up comprehensive MCP mocks in sys.modules."""
    # We only mock the runtime components that do I/O or logic we want to control
    # types are imported from the real library now
    mock_mcp = MagicMock()
    # sys.modules['mcp'] = mock_mcp  <-- removed
    # sys.modules['mcp.types'] = ... <-- removed

    sys.modules['mcp.server'] = MagicMock()
    sys.modules['mcp.server.stdio'] = MagicMock()
    sys.modules['mcp.client'] = MagicMock()
    sys.modules['mcp.client'].__path__ = []
    sys.modules['mcp.client.stdio'] = MagicMock()
    sys.modules['mcp.client.sse'] = MagicMock()
    sys.modules['mcp.server.sse'] = MagicMock()

    return mock_mcp, None


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
        """Initialize fake transport."""
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
        """Start the transport."""
        pass

    async def send(self, message: dict[str, Any]):
        """Handle incoming JSON-RPC message (simulating server)."""
        # msg_id = request.get("id")

        # In a real transport we'd write back to the stream.
        # Here we just store handling logic or print.
        # Since we are mocking the ClientSession in our python tests,
        # this logic might need to be hooked up to the mock session's methods.
        pass

    # Helper methods to populate the fake state
    def add_tool(self, name: str, description: str = '', schema: dict | None = None):
        """Add a tool."""
        self.tools.append({'name': name, 'description': description, 'input_schema': schema or {'type': 'object'}})

    def add_prompt(self, name: str, description: str = '', arguments: list | None = None):
        """Add a prompt."""
        self.prompts.append({'name': name, 'description': description, 'arguments': arguments or []})
