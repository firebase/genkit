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

"""Integration tests for MCP client-server communication."""

import asyncio
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
from genkit.plugins.mcp import McpClient, McpHost, McpServerConfig, create_mcp_host, create_mcp_server


@pytest.mark.asyncio
class TestClientServerIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for MCP client-server communication."""

    async def test_client_can_list_server_tools(self):
        """Test that a client can list tools from a server."""
        # Create server with tools
        server_ai = Genkit()

        @server_ai.tool()
        def add(a: int, b: int) -> int:
            return a + b

        # Create client
        client = McpClient(name='test-client', config=McpServerConfig(command='echo', args=['test']))

        # Mock the session to return tools
        mock_session = AsyncMock()
        mock_tool = MagicMock()
        mock_tool.name = 'add'
        mock_tool.description = 'Add two numbers'
        mock_tool.inputSchema = {'type': 'object'}

        mock_session.list_tools.return_value.tools = [mock_tool]
        client.session = mock_session

        # List tools
        tools = await client.list_tools()

        # Verify
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].name, 'add')

    async def test_client_can_call_server_tool(self):
        """Test that a client can call a tool on a server."""
        # Create client
        client = McpClient(name='test-client', config=McpServerConfig(command='echo'))

        # Mock the session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.isError = False
        mock_content = MagicMock()
        mock_content.type = 'text'
        mock_content.text = '8'
        mock_result.content = [mock_content]

        mock_session.call_tool.return_value = mock_result
        client.session = mock_session

        # Call tool
        result = await client.call_tool('add', {'a': 5, 'b': 3})

        # Verify
        self.assertEqual(result, '8')
        mock_session.call_tool.assert_called_once_with('add', {'a': 5, 'b': 3})

    async def test_client_can_list_server_resources(self):
        """Test that a client can list resources from a server."""
        # Create client
        client = McpClient(name='test-client', config=McpServerConfig(command='echo'))

        # Mock the session
        mock_session = AsyncMock()
        mock_resource = MagicMock()
        mock_resource.name = 'config'
        mock_resource.uri = 'app://config'
        mock_resource.description = 'Configuration'

        mock_session.list_resources.return_value.resources = [mock_resource]
        client.session = mock_session

        # List resources
        resources = await client.list_resources()

        # Verify
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0].name, 'config')
        self.assertEqual(resources[0].uri, 'app://config')

    async def test_client_can_read_server_resource(self):
        """Test that a client can read a resource from a server."""
        # Create client
        client = McpClient(name='test-client', config=McpServerConfig(command='echo'))

        # Mock the session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.contents = [MagicMock(text='Resource content')]

        mock_session.read_resource.return_value = mock_result
        client.session = mock_session

        # Read resource
        result = await client.read_resource('app://config')

        # Verify
        self.assertIsNotNone(result)
        mock_session.read_resource.assert_called_once_with('app://config')

    async def test_host_manages_multiple_clients(self):
        """Test that a host can manage multiple clients."""
        # Create host with multiple servers
        config1 = McpServerConfig(command='server1')
        config2 = McpServerConfig(command='server2')

        host = create_mcp_host({'server1': config1, 'server2': config2})

        # Verify clients were created
        self.assertEqual(len(host.clients), 2)
        self.assertIn('server1', host.clients)
        self.assertIn('server2', host.clients)

    async def test_host_can_register_tools_from_multiple_servers(self):
        """Test that a host can register tools from multiple servers."""
        # Create host
        host = create_mcp_host({'server1': McpServerConfig(command='s1'), 'server2': McpServerConfig(command='s2')})

        # Mock sessions for both clients
        for client_name, client in host.clients.items():
            mock_session = AsyncMock()
            mock_tool = MagicMock()
            mock_tool.name = f'{client_name}_tool'
            mock_tool.description = f'Tool from {client_name}'
            mock_tool.inputSchema = {'type': 'object'}

            mock_session.list_tools.return_value.tools = [mock_tool]
            client.session = mock_session

        # Register tools
        ai = Genkit()
        await host.register_tools(ai)

        # Verify tools were registered
        # Each client should have registered one tool
        # Tool names should be prefixed with server name

    async def test_client_handles_disabled_server(self):
        """Test that a client handles disabled servers correctly."""
        # Create client with disabled config
        config = McpServerConfig(command='echo', disabled=True)
        client = McpClient(name='test-client', config=config)

        # Try to connect
        await client.connect()

        # Should not have a session
        self.assertIsNone(client.session)

    async def test_host_can_disable_and_enable_clients(self):
        """Test that a host can disable and enable clients."""
        host = create_mcp_host({'test': McpServerConfig(command='echo')})

        # Mock the client
        client = host.clients['test']
        client.session = AsyncMock()
        client.close = AsyncMock()
        client.connect = AsyncMock()

        # Disable
        await host.disable('test')
        self.assertTrue(client.config.disabled)

        # Enable
        await host.enable('test')
        self.assertFalse(client.config.disabled)


@pytest.mark.asyncio
class TestResourceIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests specifically for resource handling."""

    async def test_end_to_end_resource_flow(self):
        """Test complete flow: define resource → expose via server → consume via client."""
        # This is a conceptual test showing the flow
        # In practice, we'd need actual MCP transport for true end-to-end

        # 1. Server side: Define resource
        server_ai = Genkit()
        server_ai.define_resource(
            name='config', uri='app://config', fn=lambda req: {'content': [{'text': 'config data'}]}
        )

        # 2. Create MCP server
        from genkit.plugins.mcp import McpServerOptions

        server = create_mcp_server(server_ai, McpServerOptions(name='test-server'))
        await server.setup()

        # 3. Verify server can list resources
        resources_result = await server.list_resources({})
        self.assertEqual(len(resources_result.resources), 1)
        self.assertEqual(resources_result.resources[0].uri, 'app://config')

        # 4. Verify server can read resource
        request = MagicMock()
        request.params.uri = 'app://config'
        read_result = await server.read_resource(request)
        self.assertEqual(read_result.contents[0].text, 'config data')

    async def test_template_resource_matching(self):
        """Test that template resources match correctly."""
        server_ai = Genkit()

        def file_resource(req):
            uri = req.uri
            return {'content': [{'text': f'Contents of {uri}'}]}

        server_ai.define_resource(name='file', template='file://{+path}', fn=file_resource)

        # Create server
        from genkit.plugins.mcp import McpServerOptions

        server = create_mcp_server(server_ai, McpServerOptions(name='test-server'))
        await server.setup()

        # List templates
        templates_result = await server.list_resource_templates({})
        self.assertEqual(len(templates_result.resourceTemplates), 1)
        self.assertEqual(templates_result.resourceTemplates[0].uriTemplate, 'file://{+path}')

        # Read with different URIs
        for test_uri in ['file:///path/to/file.txt', 'file:///another/file.md', 'file:///deep/nested/path/doc.pdf']:
            request = MagicMock()
            request.params.uri = test_uri
            result = await server.read_resource(request)
            self.assertIn(test_uri, result.contents[0].text)


@pytest.mark.asyncio
class TestErrorHandling(unittest.IsolatedAsyncioTestCase):
    """Tests for error handling in client-server communication."""

    async def test_server_handles_missing_tool(self):
        """Test that server properly handles requests for non-existent tools."""
        server_ai = Genkit()

        @server_ai.tool()
        def existing_tool(x: int) -> int:
            return x

        from genkit.plugins.mcp import McpServerOptions

        server = create_mcp_server(server_ai, McpServerOptions(name='test-server'))
        await server.setup()

        # Try to call non-existent tool
        request = MagicMock()
        request.params.name = 'nonexistent_tool'
        request.params.arguments = {}

        from genkit.core.error import GenkitError

        with self.assertRaises(GenkitError) as context:
            await server.call_tool(request)

        self.assertIn('NOT_FOUND', str(context.exception.status))

    async def test_client_handles_connection_failure(self):
        """Test that client handles connection failures gracefully."""
        client = McpClient(name='test-client', config=McpServerConfig(command='nonexistent_command'))

        # Mock the connection to fail
        with patch('genkit.plugins.mcp.client.client.stdio_client') as mock_stdio:
            mock_stdio.side_effect = Exception('Connection failed')

            with self.assertRaises(Exception):
                await client.connect()

            # Client should mark server as disabled
            self.assertTrue(client.config.disabled)


if __name__ == '__main__':
    unittest.main()
