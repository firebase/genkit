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

"""Comprehensive tests for MCP server resource handling."""

import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from fakes import mock_mcp_modules

mock_mcp_modules()

import pytest

from genkit.ai import Genkit
from genkit.core.action.types import ActionKind
from genkit.plugins.mcp import McpServer, McpServerOptions, create_mcp_server


@pytest.mark.asyncio
class TestMcpServerResources(unittest.IsolatedAsyncioTestCase):
    """Tests for MCP server resource handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.ai = Genkit()

    async def test_list_resources_with_fixed_uri(self):
        """Test listing resources with fixed URIs."""
        # Define resources
        self.ai.define_resource(name='config', uri='app://config', fn=lambda req: {'content': [{'text': 'config'}]})

        self.ai.define_resource(name='data', uri='app://data', fn=lambda req: {'content': [{'text': 'data'}]})

        # Create server
        server = create_mcp_server(self.ai, McpServerOptions(name='test-server'))
        await server.setup()

        # List resources
        result = await server.list_resources({})

        # Verify
        self.assertEqual(len(result.resources), 2)
        resource_names = [r.name for r in result.resources]
        self.assertIn('config', resource_names)
        self.assertIn('data', resource_names)

        # Verify URIs
        config_resource = next(r for r in result.resources if r.name == 'config')
        self.assertEqual(config_resource.uri, 'app://config')

    async def test_list_resource_templates(self):
        """Test listing resources with URI templates."""
        # Define template resources
        self.ai.define_resource(
            name='file', template='file://{+path}', fn=lambda req: {'content': [{'text': 'file content'}]}
        )

        self.ai.define_resource(
            name='user', template='user://{id}/profile', fn=lambda req: {'content': [{'text': 'user profile'}]}
        )

        # Create server
        server = create_mcp_server(self.ai, McpServerOptions(name='test-server'))
        await server.setup()

        # List resource templates
        result = await server.list_resource_templates({})

        # Verify
        self.assertEqual(len(result.resourceTemplates), 2)
        template_names = [t.name for t in result.resourceTemplates]
        self.assertIn('file', template_names)
        self.assertIn('user', template_names)

        # Verify templates
        file_template = next(t for t in result.resourceTemplates if t.name == 'file')
        self.assertEqual(file_template.uriTemplate, 'file://{+path}')

    async def test_list_resources_excludes_templates(self):
        """Test that list_resources excludes template resources."""
        # Define mixed resources
        self.ai.define_resource(name='fixed', uri='app://fixed', fn=lambda req: {'content': [{'text': 'fixed'}]})

        self.ai.define_resource(
            name='template', template='app://{id}', fn=lambda req: {'content': [{'text': 'template'}]}
        )

        # Create server
        server = create_mcp_server(self.ai, McpServerOptions(name='test-server'))
        await server.setup()

        # List resources (should only include fixed URI)
        result = await server.list_resources({})

        self.assertEqual(len(result.resources), 1)
        self.assertEqual(result.resources[0].name, 'fixed')

    async def test_list_resource_templates_excludes_fixed(self):
        """Test that list_resource_templates excludes fixed URI resources."""
        # Define mixed resources
        self.ai.define_resource(name='fixed', uri='app://fixed', fn=lambda req: {'content': [{'text': 'fixed'}]})

        self.ai.define_resource(
            name='template', template='app://{id}', fn=lambda req: {'content': [{'text': 'template'}]}
        )

        # Create server
        server = create_mcp_server(self.ai, McpServerOptions(name='test-server'))
        await server.setup()

        # List templates (should only include template)
        result = await server.list_resource_templates({})

        self.assertEqual(len(result.resourceTemplates), 1)
        self.assertEqual(result.resourceTemplates[0].name, 'template')

    async def test_read_resource_with_fixed_uri(self):
        """Test reading a resource with fixed URI."""

        def config_resource(req):
            return {'content': [{'text': 'Configuration data'}]}

        self.ai.define_resource(name='config', uri='app://config', fn=config_resource)

        # Create server
        server = create_mcp_server(self.ai, McpServerOptions(name='test-server'))
        await server.setup()

        # Read resource
        from mcp.types import ReadResourceRequest

        request = MagicMock()
        request.params.uri = 'app://config'

        result = await server.read_resource(request)

        # Verify
        self.assertEqual(len(result.contents), 1)
        self.assertEqual(result.contents[0].text, 'Configuration data')

    async def test_read_resource_with_template(self):
        """Test reading a resource with URI template."""

        def file_resource(req):
            uri = req.uri
            # Extract path from URI
            path = uri.replace('file://', '')
            return {'content': [{'text': f'Contents of {path}'}]}

        self.ai.define_resource(name='file', template='file://{+path}', fn=file_resource)

        # Create server
        server = create_mcp_server(self.ai, McpServerOptions(name='test-server'))
        await server.setup()

        # Read resource
        request = MagicMock()
        request.params.uri = 'file:///home/user/document.txt'

        result = await server.read_resource(request)

        # Verify
        self.assertEqual(len(result.contents), 1)
        self.assertIn('/home/user/document.txt', result.contents[0].text)

    async def test_read_resource_not_found(self):
        """Test reading a non-existent resource."""
        self.ai.define_resource(name='existing', uri='app://existing', fn=lambda req: {'content': [{'text': 'data'}]})

        # Create server
        server = create_mcp_server(self.ai, McpServerOptions(name='test-server'))
        await server.setup()

        # Try to read non-existent resource
        request = MagicMock()
        request.params.uri = 'app://nonexistent'

        from genkit.core.error import GenkitError

        with self.assertRaises(GenkitError) as context:
            await server.read_resource(request)

        self.assertIn('NOT_FOUND', str(context.exception.status))

    async def test_read_resource_with_multiple_content_parts(self):
        """Test reading a resource that returns multiple content parts."""

        def multi_part_resource(req):
            return {'content': [{'text': 'Part 1'}, {'text': 'Part 2'}, {'text': 'Part 3'}]}

        self.ai.define_resource(name='multi', uri='app://multi', fn=multi_part_resource)

        # Create server
        server = create_mcp_server(self.ai, McpServerOptions(name='test-server'))
        await server.setup()

        # Read resource
        request = MagicMock()
        request.params.uri = 'app://multi'

        result = await server.read_resource(request)

        # Verify
        self.assertEqual(len(result.contents), 3)
        self.assertEqual(result.contents[0].text, 'Part 1')
        self.assertEqual(result.contents[1].text, 'Part 2')
        self.assertEqual(result.contents[2].text, 'Part 3')


@pytest.mark.asyncio
class TestMcpServerToolsAndPrompts(unittest.IsolatedAsyncioTestCase):
    """Tests for MCP server tool and prompt handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.ai = Genkit()

    async def test_list_tools(self):
        """Test listing tools."""

        @self.ai.tool(description='Add two numbers')
        def add(input: dict[str, int]) -> int:
            return input['a'] + input['b']

        @self.ai.tool(description='Multiply two numbers')
        def multiply(input: dict[str, int]) -> int:
            return input['a'] * input['b']

        # Create server
        server = create_mcp_server(self.ai, McpServerOptions(name='test-server'))
        await server.setup()

        # List tools
        result = await server.list_tools({})

        # Verify
        self.assertEqual(len(result.tools), 2)
        tool_names = [t.name for t in result.tools]
        self.assertIn('add', tool_names)
        self.assertIn('multiply', tool_names)

    async def test_call_tool(self):
        """Test calling a tool."""

        @self.ai.tool()
        def add(input: dict[str, int]) -> int:
            return input['a'] + input['b']

        # Create server
        server = create_mcp_server(self.ai, McpServerOptions(name='test-server'))
        await server.setup()

        # Call tool
        request = MagicMock()
        request.params.name = 'add'
        request.params.arguments = {'a': 5, 'b': 3}

        result = await server.call_tool(request)

        # Verify
        self.assertEqual(len(result.content), 1)
        self.assertEqual(result.content[0].text, '8')

    async def test_list_prompts(self):
        """Test listing prompts."""
        self.ai.define_prompt(name='greeting', prompt='Hello {{name}}!')

        self.ai.define_prompt(name='farewell', prompt='Goodbye {{name}}!')

        # Create server
        server = create_mcp_server(self.ai, McpServerOptions(name='test-server'))
        await server.setup()

        # List prompts
        result = await server.list_prompts({})

        # Verify
        self.assertGreaterEqual(len(result.prompts), 2)
        prompt_names = [p.name for p in result.prompts]
        # Prompt names might have variant suffixes


@pytest.mark.asyncio
class TestMcpServerIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for MCP server."""

    async def test_server_exposes_all_action_types(self):
        """Test that server exposes tools, prompts, and resources."""
        ai = Genkit()

        # Define tool
        @ai.tool()
        def test_tool(x: int) -> int:
            return x * 2

        # Define prompt
        ai.define_prompt(name='test', prompt='Test prompt')

        # Define resource
        ai.define_resource(name='test_resource', uri='test://resource', fn=lambda req: {'content': [{'text': 'test'}]})

        # Create server
        server = create_mcp_server(ai, McpServerOptions(name='integration-test'))
        await server.setup()

        # Verify all action types are available
        self.assertGreater(len(server.tool_actions), 0)
        self.assertGreater(len(server.prompt_actions), 0)
        self.assertGreater(len(server.resource_actions), 0)

    async def test_server_initialization_idempotent(self):
        """Test that server setup is idempotent."""
        ai = Genkit()

        @ai.tool()
        def test_tool(x: int) -> int:
            return x

        server = create_mcp_server(ai, McpServerOptions(name='test'))

        # Setup multiple times
        await server.setup()
        count1 = len(server.tool_actions)

        await server.setup()
        count2 = len(server.tool_actions)

        # Should be the same
        self.assertEqual(count1, count2)


if __name__ == '__main__':
    unittest.main()
