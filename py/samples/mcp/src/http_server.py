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

"""
HTTP MCP Server Example

This demonstrates creating an HTTP-based MCP server using SSE transport
with Starlette and the official MCP Python SDK.
"""

import asyncio
import logging

import mcp.types as types
import uvicorn
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Mount, Route

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Start the HTTP MCP server."""

    # Create SSE transport logic
    # The endpoint '/mcp/' is where clients will POST messages
    sse = SseServerTransport('/mcp/')

    async def handle_sse(request):
        """Handle incoming SSE connections."""
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            read_stream, write_stream = streams

            # Create a new server instance for this session
            server = Server('example-server', version='1.0.0')

            @server.list_tools()
            async def list_tools() -> list[types.Tool]:
                return [
                    types.Tool(
                        name='test_http',
                        description='Test HTTP transport',
                        inputSchema={'type': 'object', 'properties': {}},
                    )
                ]

            @server.call_tool()
            async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
                if name == 'test_http':
                    # In this SSE implementation, valid session ID is internal
                    # but we can return a confirmation.
                    return [types.TextContent(type='text', text='Session Active')]
                raise ValueError(f'Unknown tool: {name}')

            # Run the server with the streams
            await server.run(read_stream, write_stream, server.create_initialization_options())

        # Return empty response after connection closes
        return Response()

    # Define routes
    # GET /mcp -> Starts SSE stream
    # POST /mcp/ -> Handles messages (via SseServerTransport)
    routes = [
        Route('/mcp', endpoint=handle_sse, methods=['GET']),
        Mount('/mcp/', app=sse.handle_post_message),
    ]

    app = Starlette(routes=routes)

    config = uvicorn.Config(app, host='0.0.0.0', port=3334, log_level='info')
    server = uvicorn.Server(config)

    print('HTTP MCP server running on http://localhost:3334/mcp')
    await server.serve()


if __name__ == '__main__':
    asyncio.run(main())
