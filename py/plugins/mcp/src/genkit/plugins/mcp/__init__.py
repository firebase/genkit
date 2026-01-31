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

"""MCP (Model Context Protocol) plugin for Genkit.

This plugin provides integration with the Model Context Protocol (MCP),
enabling Genkit to communicate with MCP servers and host MCP capabilities.

Overview:
    MCP is an open protocol for communication between AI applications and
    context providers. This plugin allows Genkit to:
    - Connect to MCP servers as a client (use external tools/resources)
    - Host an MCP server (expose Genkit tools/resources to other clients)

    ┌─────────────────────────────────────────────────────────────────────────┐
    │                        MCP Architecture                                 │
    ├─────────────────────────────────────────────────────────────────────────┤
    │                                                                         │
    │  ┌──────────────────┐                    ┌──────────────────┐          │
    │  │   Genkit App     │◄──── MCP ─────────►│   MCP Server     │          │
    │  │  (MCP Client)    │      Protocol      │  (tools/prompts) │          │
    │  └──────────────────┘                    └──────────────────┘          │
    │                                                                         │
    │  ┌──────────────────┐                    ┌──────────────────┐          │
    │  │   MCP Client     │◄──── MCP ─────────►│   Genkit App     │          │
    │  │  (Claude, etc.)  │      Protocol      │  (MCP Server)    │          │
    │  └──────────────────┘                    └──────────────────┘          │
    │                                                                         │
    └─────────────────────────────────────────────────────────────────────────┘

Terminology:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Term              │ Description                                         │
    ├───────────────────┼─────────────────────────────────────────────────────┤
    │ McpClient         │ Connect to a single MCP server                      │
    │ McpHost           │ Manage multiple MCP client connections              │
    │ McpServer         │ Expose Genkit tools as an MCP server                │
    │ McpServerConfig   │ Configuration for connecting to an MCP server       │
    └───────────────────┴─────────────────────────────────────────────────────┘

Key Components:
    ┌─────────────────────────────────────────────────────────────────────────┐
    │ Component           │ Purpose                                           │
    ├─────────────────────┼───────────────────────────────────────────────────┤
    │ create_mcp_client() │ Create a client to connect to an MCP server       │
    │ create_mcp_host()   │ Create a host managing multiple MCP connections   │
    │ create_mcp_server() │ Create an MCP server exposing Genkit tools        │
    │ McpServerOptions    │ Configuration options for the MCP server          │
    └─────────────────────┴───────────────────────────────────────────────────┘

Example:
    Using MCP client to connect to external tools:

    ```python
    from genkit import Genkit
    from genkit.plugins.mcp import create_mcp_client, McpServerConfig

    ai = Genkit(...)

    # Connect to an MCP server
    mcp = create_mcp_client(
        ai,
        McpServerConfig(
            name='filesystem',
            command='npx',
            args=['@anthropic-ai/mcp-server-filesystem', '/path/to/files'],
        ),
    )

    # The MCP tools are now available to Genkit
    response = await ai.generate(
        prompt='List files in the current directory',
        tools=[mcp.tools['list_files']],
    )
    ```

    Exposing Genkit tools as an MCP server:

    ```python
    from genkit.plugins.mcp import create_mcp_server, McpServerOptions

    server = create_mcp_server(
        ai,
        McpServerOptions(name='my-genkit-server'),
    )

    # Start the server
    await server.start()
    ```

See Also:
    - MCP specification: https://modelcontextprotocol.io/
    - Genkit documentation: https://genkit.dev/
"""

from .client.client import (
    McpClient,
    McpServerConfig,
    create_mcp_client,
)
from .client.host import McpHost, create_mcp_host
from .server import McpServer, McpServerOptions, create_mcp_server


def package_name() -> str:
    """Returns the package name of the MCP plugin."""
    return 'genkit.plugins.mcp'


__all__ = [
    'McpClient',
    'McpHost',
    'McpServerConfig',
    'create_mcp_client',
    'create_mcp_host',
    'McpServer',
    'McpServerOptions',
    'create_mcp_server',
    'package_name',
]
