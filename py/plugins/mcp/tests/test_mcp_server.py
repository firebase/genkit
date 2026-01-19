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

"""
MCP Server Tests

Mirrors the functionality of js/plugins/mcp/tests/server_test.ts
Tests tools, prompts, and resources exposed via MCP server.
"""

import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Mock mcp module before importing
mock_mcp = MagicMock()
sys.modules['mcp'] = mock_mcp


class MockSchema:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


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
types_mock.TextResourceContents = MockSchema
types_mock.BlobResourceContents = MockSchema
types_mock.ImageContent = MockSchema
types_mock.TextResourceContents = MockSchema
types_mock.BlobResourceContents = MockSchema
types_mock.ImageContent = MockSchema
types_mock.TextContent = MockSchema
types_mock.PromptMessage = MockSchema

sys.modules['mcp.server'] = MagicMock()
sys.modules['mcp.server.stdio'] = MagicMock()
sys.modules['mcp.client'] = MagicMock()
sys.modules['mcp.client'].__path__ = []
sys.modules['mcp.client.stdio'] = MagicMock()
sys.modules['mcp.client.sse'] = MagicMock()
sys.modules['mcp.server.sse'] = MagicMock()

import pytest

from genkit.ai import Genkit
from genkit.core.action.types import ActionKind
from genkit.plugins.mcp import McpServer, McpServerOptions, create_mcp_server


@pytest.mark.asyncio
class TestMcpServer(unittest.IsolatedAsyncioTestCase):
    """Test MCP server functionality - mirrors JS server_test.ts"""

    def setUp(self):
        """Set up test fixtures before each test."""
        self.ai = Genkit()

        # Define test tool
        @self.ai.tool(description='test tool')
        def test_tool(input: dict[str, str]) -> str:
            foo = input.get('foo', '')
            return f'yep {{"foo":"{foo}"}}'

        # Define test prompt
        self.ai.define_prompt(name='testPrompt', model='test-model', prompt='prompt says: {{input}}')

        # Define test resource with fixed URI
        self.ai.define_resource(
            name='testResources', uri='my://resource', fn=lambda req: {'content': [{'text': 'my resource'}]}
        )

        # Define test resource with template
        self.ai.define_resource(
            name='testTmpl',
            template='file://{+path}',
            fn=lambda req: {'content': [{'text': f'file contents for {req.uri}'}]},
        )

        # Create MCP server
        self.server = create_mcp_server(self.ai, McpServerOptions(name='test-server', version='0.0.1'))

    async def asyncSetUp(self):
        """Async setup - initialize server."""
        await self.server.setup()

    # ===== TOOL TESTS =====

    async def test_list_tools(self):
        """Test listing tools - mirrors JS 'should list tools'."""
        result = await self.server.list_tools({})

        # Verify we have the test tool
        self.assertEqual(len(result.tools), 1)
        tool = result.tools[0]

        self.assertEqual(tool.name, 'test_tool')
        self.assertEqual(tool.description, 'test tool')
        self.assertIsNotNone(tool.inputSchema)

    async def test_call_tool(self):
        """Test calling a tool - mirrors JS 'should call the tool'."""
        # Create mock request
        request = MagicMock()
        request.params.name = 'test_tool'
        request.params.arguments = {'foo': 'bar'}

        result = await self.server.call_tool(request)

        # Verify response
        self.assertEqual(len(result.content), 1)
        self.assertEqual(result.content[0].type, 'text')
        self.assertEqual(result.content[0].text, 'yep {"foo":"bar"}')

    # ===== PROMPT TESTS =====

    async def test_list_prompts(self):
        """Test listing prompts - mirrors JS 'should list prompts'."""
        result = await self.server.list_prompts({})

        # Verify we have the test prompt
        prompt_names = [p.name for p in result.prompts]
        self.assertIn('testPrompt', prompt_names)

    async def test_get_prompt(self):
        """Test rendering a prompt - mirrors JS 'should render prompt'."""
        # Create mock request
        request = MagicMock()
        request.params.name = 'testPrompt'
        request.params.arguments = {'input': 'hello'}

        result = await self.server.get_prompt(request)

        # Verify response
        self.assertIsNotNone(result.messages)
        self.assertGreater(len(result.messages), 0)

        # Check message content
        message = result.messages[0]
        self.assertEqual(message.role, 'user')
        self.assertEqual(message.content.type, 'text')
        self.assertIn('prompt says: hello', message.content.text)

    # ===== RESOURCE TESTS =====

    async def test_list_resources(self):
        """Test listing resources - mirrors JS 'should list resources'."""
        result = await self.server.list_resources({})

        # Verify we have the fixed URI resource
        self.assertEqual(len(result.resources), 1)
        resource = result.resources[0]

        self.assertEqual(resource.name, 'testResources')
        self.assertEqual(resource.uri, 'my://resource')

    async def test_list_resource_templates(self):
        """Test listing resource templates - mirrors JS 'should list templates'."""
        result = await self.server.list_resource_templates({})

        # Verify we have the template resource
        self.assertEqual(len(result.resourceTemplates), 1)
        template = result.resourceTemplates[0]

        self.assertEqual(template.name, 'testTmpl')
        self.assertEqual(template.uriTemplate, 'file://{+path}')

    async def test_read_resource(self):
        """Test reading a resource - mirrors JS 'should read resource'."""
        # Create mock request
        request = MagicMock()
        request.params.uri = 'my://resource'

        result = await self.server.read_resource(request)

        # Verify response
        self.assertEqual(len(result.contents), 1)
        content = result.contents[0]

        self.assertEqual(content.uri, 'my://resource')
        self.assertEqual(content.text, 'my resource')

    async def test_read_template_resource(self):
        """Test reading a template resource."""
        # Create mock request
        request = MagicMock()
        request.params.uri = 'file:///path/to/file.txt'

        result = await self.server.read_resource(request)

        # Verify response
        self.assertEqual(len(result.contents), 1)
        content = result.contents[0]

        self.assertEqual(content.uri, 'file:///path/to/file.txt')
        self.assertIn('file contents for file:///path/to/file.txt', content.text)

    # ===== ADDITIONAL TESTS =====

    async def test_server_initialization(self):
        """Test that server initializes correctly."""
        self.assertIsNotNone(self.server)
        self.assertEqual(self.server.options.name, 'test-server')
        self.assertEqual(self.server.options.version, '0.0.1')
        self.assertTrue(self.server.actions_resolved)

    async def test_server_has_all_action_types(self):
        """Test that server has tools, prompts, and resources."""
        self.assertGreater(len(self.server.tool_actions), 0)
        self.assertGreater(len(self.server.prompt_actions), 0)
        self.assertGreater(len(self.server.resource_actions), 0)

    async def test_tool_not_found(self):
        """Test calling a non-existent tool."""
        from genkit.core.error import GenkitError

        request = MagicMock()
        request.params.name = 'nonexistent_tool'
        request.params.arguments = {}

        with self.assertRaises(GenkitError) as context:
            await self.server.call_tool(request)

        self.assertEqual(context.exception.status, 'NOT_FOUND')

    async def test_prompt_not_found(self):
        """Test getting a non-existent prompt."""
        from genkit.core.error import GenkitError

        request = MagicMock()
        request.params.name = 'nonexistent_prompt'
        request.params.arguments = {}

        with self.assertRaises(GenkitError) as context:
            await self.server.get_prompt(request)

        self.assertEqual(context.exception.status, 'NOT_FOUND')

    async def test_resource_not_found(self):
        """Test reading a non-existent resource."""
        from genkit.core.error import GenkitError

        request = MagicMock()
        request.params.uri = 'nonexistent://resource'

        with self.assertRaises(GenkitError) as context:
            await self.server.read_resource(request)

        self.assertEqual(context.exception.status, 'NOT_FOUND')


# Additional test class for resource-specific functionality
@pytest.mark.asyncio
class TestResourceFunctionality(unittest.IsolatedAsyncioTestCase):
    """Test resource-specific functionality."""

    async def test_resource_registration_with_fixed_uri(self):
        """Test registering a resource with fixed URI."""
        ai = Genkit()

        action = ai.define_resource(
            name='test_resource', uri='test://resource', fn=lambda req: {'content': [{'text': 'test'}]}
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, ActionKind.RESOURCE)
        self.assertEqual(action.metadata['resource']['uri'], 'test://resource')

    async def test_resource_registration_with_template(self):
        """Test registering a resource with URI template."""
        ai = Genkit()

        action = ai.define_resource(
            name='file', template='file://{+path}', fn=lambda req: {'content': [{'text': 'file content'}]}
        )

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, ActionKind.RESOURCE)
        self.assertEqual(action.metadata['resource']['template'], 'file://{+path}')

    async def test_resource_requires_uri_or_template(self):
        """Test that resource requires either uri or template."""
        ai = Genkit()

        with self.assertRaises(ValueError) as context:
            ai.define_resource(name='invalid', fn=lambda req: {'content': []})

        self.assertIn('uri', str(context.exception).lower())
        self.assertIn('template', str(context.exception).lower())

    async def test_uri_template_matching(self):
        """Test URI template matching."""
        from genkit.blocks.resource import matches_uri_template

        # Test exact match
        result = matches_uri_template('file://{+path}', 'file:///home/user/doc.txt')
        self.assertIsNotNone(result)
        self.assertIn('path', result)

        # Test no match
        result = matches_uri_template('file://{path}', 'http://example.com')
        self.assertIsNone(result)

        # Test multiple parameters
        result = matches_uri_template('user://{id}/posts/{post_id}', 'user://123/posts/456')
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], '123')
        self.assertEqual(result['post_id'], '456')


if __name__ == '__main__':
    unittest.main()
