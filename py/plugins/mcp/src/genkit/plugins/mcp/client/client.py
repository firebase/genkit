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
from contextlib import AsyncExitStack
from typing import Any

import structlog
from pydantic import BaseModel

from genkit.ai import Genkit
from genkit.ai._registry import GenkitRegistry
from genkit.core.action.types import ActionKind
from genkit.core.plugin import Plugin
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, Prompt, Resource, Tool

logger = structlog.get_logger(__name__)


class McpServerConfig(BaseModel):
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    url: str | None = None
    disabled: bool = False


class McpClient:
    """Client for connecting to a single MCP server."""

    def __init__(self, name: str, config: McpServerConfig, server_name: str | None = None):
        self.name = name
        self.config = config
        self.server_name = server_name or name
        self.session: ClientSession | None = None
        self._exit_stack = AsyncExitStack()
        self.ai: GenkitRegistry | None = None

    def plugin_name(self) -> str:
        return self.name

    def initialize(self, ai: GenkitRegistry) -> None:
        self.ai = ai

    def resolve_action(self, ai: GenkitRegistry, kind: ActionKind, name: str) -> None:
        # MCP tools are dynamic and currently registered upon connection/Discovery.
        # This hook allows lazy resolution if we implement it.
        pass

    async def connect(self):
        """Connects to the MCP server."""
        if self.session:
            return

        if self.config.disabled:
            logger.info(f'MCP server {self.server_name} is disabled.')
            return

        try:
            if self.config.command:
                server_params = StdioServerParameters(
                    command=self.config.command, args=self.config.args or [], env=self.config.env
                )
                # stdio_client returns (read, write) streams
                stdio_context = stdio_client(server_params)
                read, write = await self._exit_stack.enter_async_context(stdio_context)

                # Create and initialize session
                session_context = ClientSession(read, write)
                self.session = await self._exit_stack.enter_async_context(session_context)

            elif self.config.url:
                # TODO: Verify SSE client usage in mcp python SDK
                sse_context = sse_client(self.config.url)
                read, write = await self._exit_stack.enter_async_context(sse_context)

                session_context = ClientSession(read, write)
                self.session = await self._exit_stack.enter_async_context(session_context)

            await self.session.initialize()
            logger.info(f'Connected to MCP server: {self.server_name}')

        except Exception as e:
            logger.error(f'Failed to connect to MCP server {self.server_name}: {e}')
            self.config.disabled = True
            # Clean up on error
            await self.close()
            raise e

    async def close(self):
        """Closes the connection."""
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except (Exception, asyncio.CancelledError):
                # Ignore errors during cleanup, especially cancellation from anyio
                pass

        # Reset exit stack for potential reuse (reconnect)
        self._exit_stack = AsyncExitStack()
        self.session = None

    async def list_tools(self) -> list[Tool]:
        if not self.session:
            return []
        result = await self.session.list_tools()
        return result.tools

    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        if not self.session:
            raise RuntimeError('MCP client is not connected')
        logger.debug(f'MCP {self.server_name}: calling tool {tool_name}', arguments=arguments)
        try:
            result: CallToolResult = await self.session.call_tool(tool_name, arguments)
            logger.debug(f'MCP {self.server_name}: tool {tool_name} returned')

            # Process result similarly to JS SDK
            if result.isError:
                raise RuntimeError(f'Tool execution failed: {result.content}')

            # Simple text extraction for now
            texts = [c.text for c in result.content if c.type == 'text']
            return {'content': ''.join(texts)}
        except Exception as e:
            logger.error(f'MCP {self.server_name}: tool {tool_name} failed', error=str(e))
            raise

    async def list_prompts(self) -> list[Prompt]:
        if not self.session:
            return []
        result = await self.session.list_prompts()
        return result.prompts

    async def get_prompt(self, name: str, arguments: dict | None = None) -> Any:
        if not self.session:
            raise RuntimeError('MCP client is not connected')
        return await self.session.get_prompt(name, arguments)

    async def list_resources(self) -> list[Resource]:
        if not self.session:
            return []
        result = await self.session.list_resources()
        return result.resources

    async def read_resource(self, uri: str) -> Any:
        if not self.session:
            raise RuntimeError('MCP client is not connected')
        return await self.session.read_resource(uri)

    async def register_tools(self, ai: Genkit | None = None):
        """Registers all tools from connected client to Genkit."""
        registry = ai.registry if ai else (self.ai.registry if self.ai else None)
        if not registry:
            logger.warning('No Genkit registry available to register tools.')
            return

        if not self.session:
            return

        try:
            tools = await self.list_tools()
            for tool in tools:
                # Create a wrapper function for the tool using a factory to capture tool name
                def create_wrapper(tool_name: str):
                    async def tool_wrapper(args: Any = None):
                        # args might be Pydantic model or dict. Genkit passes dict usually?
                        # TODO: Validate args against schema if needed
                        arguments = args
                        if hasattr(args, 'model_dump'):
                            arguments = args.model_dump()
                        return await self.call_tool(tool_name, arguments or {})

                    return tool_wrapper

                tool_wrapper = create_wrapper(tool.name)

                # Use metadata to store MCP specific info
                metadata = {'mcp': {'_meta': tool._meta}} if hasattr(tool, '_meta') else {}

                # Define the tool in Genkit registry
                action = registry.register_action(
                    kind=ActionKind.TOOL,
                    name=f'{self.server_name}_{tool.name}',
                    fn=tool_wrapper,
                    description=tool.description,
                    metadata=metadata,
                )

                # Patch input schema from MCP tool definition
                if tool.inputSchema:
                    action._input_schema = tool.inputSchema
                    action._metadata['inputSchema'] = tool.inputSchema

                logger.debug(f'Registered MCP tool: {self.server_name}_{tool.name}')
        except Exception as e:
            logger.error(f'Error registering tools for {self.server_name}: {e}')

    async def get_active_tools(self) -> list[Any]:
        """Returns all active tools."""
        if not self.session:
            return []
        return await self.list_tools()


def create_mcp_client(config: McpServerConfig, name: str = 'mcp-client') -> McpClient:
    return McpClient(name, config)
