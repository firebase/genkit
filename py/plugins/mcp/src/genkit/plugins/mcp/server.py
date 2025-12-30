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
# distributed under the License.
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""MCP Server implementation for exposing Genkit actions via Model Context Protocol."""

import asyncio
from typing import Any, Optional

import structlog
from pydantic import AnyUrl, BaseModel

import mcp.types as types
from genkit.ai import Genkit
from genkit.blocks.resource import matches_uri_template
from genkit.core.action._key import parse_action_key
from genkit.core.action.types import ActionKind
from genkit.core.error import GenkitError
from genkit.core.schema import to_json_schema
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    GetPromptRequest,
    GetPromptResult,
    ListPromptsRequest,
    ListPromptsResult,
    ListResourcesRequest,
    ListResourcesResult,
    ListResourceTemplatesRequest,
    ListResourceTemplatesResult,
    ListToolsRequest,
    ListToolsResult,
    Prompt,
    ReadResourceRequest,
    ReadResourceResult,
    Resource,
    ResourceTemplate,
    Tool,
)

from .util import (
    to_mcp_prompt_arguments,
    to_mcp_prompt_message,
    to_mcp_resource_contents,
    to_mcp_tool_result,
)

logger = structlog.get_logger(__name__)


class McpServerOptions(BaseModel):
    """Options for creating an MCP server.

    Attributes:
        name: The name of the MCP server.
        version: The version of the server (default: "1.0.0").
    """

    name: str
    version: str = '1.0.0'


class McpServer:
    """Exposes Genkit tools, prompts, and resources as an MCP server.

    This class wraps a Genkit instance and makes its registered actions
    (tools, prompts, resources) available to MCP clients via the Model Context Protocol.
    """

    def __init__(self, ai: Genkit, options: McpServerOptions):
        """Initialize the MCP server.

        Args:
            ai: The Genkit instance whose actions will be exposed.
            options: Configuration options for the MCP server.
        """
        self.ai = ai
        self.options = options
        self.server: Optional[Server] = None
        self.actions_resolved = False
        self.tool_actions: list[Any] = []
        self.prompt_actions: list[Any] = []
        self.resource_actions: list[Any] = []
        self.tool_actions_map: dict[str, Any] = {}
        self.prompt_actions_map: dict[str, Any] = {}
        self.resource_uri_map: dict[str, Any] = {}
        self.resource_templates: list[tuple[str, Any]] = []

    async def setup(self) -> None:
        """Initialize the MCP server and register request handlers.

        This method sets up the MCP Server instance, registers all request handlers,
        and resolves all actions from the Genkit registry. It's idempotent and can
        be called multiple times safely.
        """
        if self.actions_resolved:
            return

        # Create MCP Server instance
        self.server = Server(self.options.name)

        # Register request handlers using decorators

        @self.server.list_tools()
        async def list_tools() -> list[types.Tool]:
            return await self._list_tools()

        @self.server.call_tool()
        async def call_tool(
            name: str, arguments: dict | None
        ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            return await self._call_tool(name, arguments)

        @self.server.list_prompts()
        async def list_prompts() -> list[types.Prompt]:
            return await self._list_prompts()

        @self.server.get_prompt()
        async def get_prompt(name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
            return await self._get_prompt(name, arguments)

        @self.server.list_resources()
        async def list_resources() -> list[types.Resource]:
            return await self._list_resources()

        @self.server.list_resource_templates()
        async def list_resource_templates() -> list[types.ResourceTemplate]:
            return await self._list_resource_templates()

        @self.server.read_resource()
        async def read_resource(uri: AnyUrl) -> str | bytes:
            # Note: The MCP SDK signature for read_resource expects returning content
            # directly or a list of contents depending on version.
            # Based on lowlevel/server.py it returns ReadResourceContents which is content list
            return await self._read_resource(str(uri))

        # Resolve all actions from Genkit registry
        # We need the actual Action objects, not just serializable dicts
        self.tool_actions = []
        self.prompt_actions = []
        self.resource_actions = []

        # Get all actions from the registry
        # We use the internal _entries for local actions and plugins
        with self.ai.registry._lock:
            for kind, entries in self.ai.registry._entries.items():
                for name, action in entries.items():
                    if kind == ActionKind.TOOL:
                        self.tool_actions.append(action)
                        self.tool_actions_map[action.name] = action
                    elif kind == ActionKind.PROMPT:
                        self.prompt_actions.append(action)
                        self.prompt_actions_map[action.name] = action
                    elif kind == ActionKind.RESOURCE:
                        self.resource_actions.append(action)
                        metadata = action.metadata or {}
                        resource_meta = metadata.get('resource', {})
                        if resource_meta.get('uri'):
                            self.resource_uri_map[resource_meta['uri']] = action
                        if resource_meta.get('template'):
                            self.resource_templates.append((resource_meta['template'], action))

        # Also get actions from plugins that might not be in _entries yet
        # (though most plugins register them in _entries during initialization)
        plugin_actions = self.ai.registry.list_actions()
        for key in plugin_actions:
            kind, name = parse_action_key(key)
            action = self.ai.registry.lookup_action(kind, name)
            if action:
                if kind == ActionKind.TOOL and action not in self.tool_actions:
                    self.tool_actions.append(action)
                    self.tool_actions_map[action.name] = action
                elif kind == ActionKind.PROMPT and action not in self.prompt_actions:
                    self.prompt_actions.append(action)
                    self.prompt_actions_map[action.name] = action
                elif kind == ActionKind.RESOURCE and action not in self.resource_actions:
                    self.resource_actions.append(action)
                    metadata = action.metadata or {}
                    resource_meta = metadata.get('resource', {})
                    if resource_meta.get('uri'):
                        self.resource_uri_map[resource_meta['uri']] = action
                    if resource_meta.get('template'):
                        self.resource_templates.append((resource_meta['template'], action))

        self.actions_resolved = True

        logger.info(
            f'MCP Server initialized',
            tools=len(self.tool_actions),
            prompts=len(self.prompt_actions),
            resources=len(self.resource_actions),
        )

    async def _list_tools(self) -> list[types.Tool]:
        """Handle MCP requests to list available tools."""
        await self.setup()

        tools: list[Tool] = []
        for action in self.tool_actions:
            # Get tool definition
            input_schema = to_json_schema(action.input_schema) if action.input_schema else {'type': 'object'}

            tools.append(
                Tool(
                    name=action.name,
                    description=action.description or '',
                    inputSchema=input_schema,
                    _meta=action.metadata.get('mcp', {}).get('_meta') if action.metadata else None,
                )
            )

        return tools

    async def _call_tool(
        self, name: str, arguments: dict | None
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle MCP requests to call a specific tool."""
        await self.setup()

        # Find the tool action
        tool = self.tool_actions_map.get(name)

        if not tool:
            raise GenkitError(status='NOT_FOUND', message=f"Tried to call tool '{name}' but it could not be found.")

        # Execute the tool
        result = await tool.arun(arguments)
        result = result.response

        # Convert result to MCP format (list of contents)
        return to_mcp_tool_result(result)

    async def _list_prompts(self) -> list[types.Prompt]:
        """Handle MCP requests to list available prompts."""
        await self.setup()

        prompts: list[Prompt] = []
        for action in self.prompt_actions:
            # Convert input schema to MCP prompt arguments
            input_schema = to_json_schema(action.input_schema) if action.input_schema else None
            arguments = to_mcp_prompt_arguments(input_schema) if input_schema else None

            prompts.append(
                Prompt(
                    name=action.name,
                    description=action.description or '',
                    arguments=arguments,
                    _meta=action.metadata.get('mcp', {}).get('_meta') if action.metadata else None,
                )
            )

        return prompts

    async def _get_prompt(self, name: str, arguments: dict[str, str] | None) -> types.GetPromptResult:
        """Handle MCP requests to get (render) a specific prompt."""
        await self.setup()

        # Find the prompt action
        prompt = self.prompt_actions_map.get(name)

        if not prompt:
            raise GenkitError(
                status='NOT_FOUND',
                message=f"[MCP Server] Tried to call prompt '{name}' but it could not be found.",
            )

        # Execute the prompt
        result = await prompt.arun(arguments)
        result = result.response

        # Convert messages to MCP format
        messages = [to_mcp_prompt_message(msg) for msg in result.messages]

        return GetPromptResult(description=prompt.description, messages=messages)

    async def _list_resources(self) -> list[types.Resource]:
        """Handle MCP requests to list available resources with fixed URIs."""
        await self.setup()

        resources: list[Resource] = []
        for action in self.resource_actions:
            metadata = action.metadata or {}
            resource_meta = metadata.get('resource', {})

            # Only include resources with fixed URIs (not templates)
            if resource_meta.get('uri'):
                resources.append(
                    Resource(
                        name=action.name,
                        description=action.description or '',
                        uri=resource_meta['uri'],
                        _meta=metadata.get('mcp', {}).get('_meta'),
                    )
                )

        return resources

    async def _list_resource_templates(self) -> list[types.ResourceTemplate]:
        """Handle MCP requests to list available resource templates."""
        await self.setup()

        templates: list[ResourceTemplate] = []
        for action in self.resource_actions:
            metadata = action.metadata or {}
            resource_meta = metadata.get('resource', {})

            # Only include resources with templates
            if resource_meta.get('template'):
                templates.append(
                    ResourceTemplate(
                        name=action.name,
                        description=action.description or '',
                        uriTemplate=resource_meta['template'],
                        _meta=metadata.get('mcp', {}).get('_meta'),
                    )
                )

        return templates

    async def _read_resource(
        self, uri: str
    ) -> str | bytes | list[types.TextResourceContents | types.BlobResourceContents]:
        """Handle MCP requests to read a specific resource."""
        await self.setup()

        # Check for exact URI match
        resource = self.resource_uri_map.get(uri)

        # Check for template match if not found by exact URI
        if not resource:
            for template, action in self.resource_templates:
                if matches_uri_template(template, uri):
                    resource = action
                    break

        if not resource:
            raise GenkitError(status='NOT_FOUND', message=f"Tried to call resource '{uri}' but it could not be found.")

        # Execute the resource action
        result = await resource.arun({'uri': uri})
        result = result.response

        # Convert content to MCP format
        # For SDK server usage, we return the contents list directly
        content = result.get('content', []) if isinstance(result, dict) else result.content
        return to_mcp_resource_contents(uri, content)

    async def start(self, transport: Any = None) -> None:
        """Start the MCP server with the specified transport.

        Args:
            transport: Optional MCP transport instance. If not provided,
                      a StdioServerTransport will be created and used.
        """
        if not transport:
            transport = stdio_server()

        await self.setup()

        # Connect the transport
        async with transport as (read, write):
            await self.server.run(read, write, self.server.create_initialization_options())

        logger.debug(f"[MCP Server] MCP server '{self.options.name}' started successfully.")


# Schema imports (these would normally come from mcp.types)
# For now, we'll use the string names
ListToolsRequestSchema = 'ListToolsRequest'
CallToolRequestSchema = 'CallToolRequest'
ListPromptsRequestSchema = 'ListPromptsRequest'
GetPromptRequestSchema = 'GetPromptRequest'
ListResourcesRequestSchema = 'ListResourcesRequest'
ListResourceTemplatesRequestSchema = 'ListResourceTemplatesRequest'
ReadResourceRequestSchema = 'ReadResourceRequest'


def create_mcp_server(ai: Genkit, options: McpServerOptions) -> McpServer:
    """Create an MCP server based on the supplied Genkit instance.

    All tools, prompts, and resources will be automatically converted to MCP compatibility.

    Args:
        ai: Your Genkit instance with registered tools, prompts, and resources.
        options: Configuration metadata for the server.

    Returns:
        GenkitMcpServer instance.

    Example:
        ```python
        from genkit.ai import Genkit
        from genkit.plugins.mcp import create_mcp_server, McpServerOptions

        ai = Genkit()


        # Define some tools and resources
        @ai.tool()
        def add(a: int, b: int) -> int:
            return a + b


        ai.define_resource(name='my_resource', uri='my://resource', fn=lambda req: {'content': [{'text': 'resource content'}]})

        # Create and start MCP server
        server = create_mcp_server(ai, McpServerOptions(name='my-server'))
        await server.start()
        ```
    """
    return McpServer(ai, options)
