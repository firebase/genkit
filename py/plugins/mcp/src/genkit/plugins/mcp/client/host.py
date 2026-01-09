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

from typing import Dict, List, Optional

from genkit.ai import Genkit

from .client import McpClient, McpServerConfig


class McpHost:
    """Host for managing multiple MCP clients."""

    def __init__(self, clients: Dict[str, McpServerConfig]):
        self.clients_config = clients
        self.clients: Dict[str, McpClient] = {name: McpClient(name, config) for name, config in clients.items()}

    async def start(self):
        """Starts all enabled MCP clients."""
        for client in self.clients.values():
            if not client.config.disabled:
                await client.connect()

    async def close(self):
        """Closes all MCP clients."""
        for client in self.clients.values():
            await client.close()

    async def register_tools(self, ai: Genkit):
        """Registers all tools from connected clients to Genkit."""
        for client in self.clients.values():
            if client.session:
                await client.register_tools(ai)

    async def enable(self, name: str):
        """Enables and connects an MCP client."""
        if name in self.clients:
            client = self.clients[name]
            client.config.disabled = False
            await client.connect()

    async def disable(self, name: str):
        """Disables and closes an MCP client."""
        if name in self.clients:
            client = self.clients[name]
            client.config.disabled = True
            await client.close()

    async def get_active_tools(self, ai: Optional[Genkit] = None) -> List[str]:
        """Returns all active tool names across all clients."""
        all_tools = []
        for client in self.clients.values():
            if client.session and not client.config.disabled:
                tools = await client.get_active_tools()
                all_tools.extend([f'{client.server_name}/{t.name}' for t in tools])
        return all_tools

    async def get_active_resources(self, ai: Optional[Genkit] = None) -> List[str]:
        """Returns all active resource URIs across all clients."""
        all_resources = []
        for client in self.clients.values():
            if client.session and not client.config.disabled:
                resources = await client.get_active_resources()
                all_resources.extend([r.uri for r in resources])
        return all_resources


def create_mcp_host(configs: Dict[str, McpServerConfig]) -> McpHost:
    return McpHost(configs)
