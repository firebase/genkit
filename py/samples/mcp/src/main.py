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
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0


import asyncio
import os
from pathlib import Path
from pydantic import BaseModel

from genkit.ai import Genkit
from genkit.plugins.mcp import create_mcp_host, McpServerConfig
from genkit.plugins.google_genai import GoogleAI

import structlog

logger = structlog.get_logger(__name__)

# Get the current directory
current_dir = Path(__file__).parent
workspace_dir = current_dir.parent / "test-workspace"
repo_root = current_dir.parent.parent.parent.parent

# Initialize Genkit with GoogleAI
ai = Genkit(
    plugins=[GoogleAI()],
    model='googleai/gemini-2.5-flash'
)

# Create MCP host with multiple servers
mcp_host = create_mcp_host({
    'git-client': McpServerConfig(
        command='uvx',
        args=['mcp-server-git']
    ),
    'fs': McpServerConfig(
        command='npx',
        args=[
            '-y',
            '@modelcontextprotocol/server-filesystem',
            str(workspace_dir)
        ]
    ),
    'everything': McpServerConfig(
        command='npx',
        args=['-y', '@modelcontextprotocol/server-everything']
    ),
})


@ai.flow(name='git_commits')
async def git_commits(query: str = ''):
    """Summarize recent git commits using MCP git client."""
    await mcp_host.start()
    tools = await mcp_host.register_tools(ai)

    result = await ai.generate(
        prompt=f"summarize last 5 commits in '{repo_root}'",
        tools=tools
    )

    await mcp_host.close()
    return result.text


@ai.flow(name='dynamic_git_commits')
async def dynamic_git_commits(query: str = ''):
    """Summarize recent git commits using 'all' tools matching pattern."""
    await mcp_host.start()
    tools = await mcp_host.register_tools(ai)
    
    # Simulate wildcard matching "git-client:tool/*" by passing all tools 
    # (since registration prefixes with server name)
    # JS: tools: ['test-mcp-manager:tool/*']
    
    result = await ai.generate(
        prompt=f"summarize last 5 commits in '{repo_root}'",
        tools=tools
    )
    
    await mcp_host.close()
    return result.text

@ai.flow(name='get_file')
async def get_file(query: str = ''):
    """Read and summarize a file using MCP filesystem client."""
    await mcp_host.start()
    tools = await mcp_host.register_tools(ai)

    result = await ai.generate(
        prompt=f"summarize contents of hello-world.txt (in '{workspace_dir}')",
        tools=tools
    )

    await mcp_host.close()
    return result.text


@ai.flow(name='dynamic_get_file')
async def dynamic_get_file(query: str = ''):
    """Read file using specific tool selection."""
    await mcp_host.start()
    tools = await mcp_host.register_tools(ai)
    
    # Filter for specific tool: 'fs/read_file'
    # JS: tools: ['test-mcp-manager:tool/fs/read_file']
    import fnmatch
    filtered_tools = [t for t in tools if fnmatch.fnmatch(t, '*/fs/read_file') or t.endswith('fs/read_file')]

    result = await ai.generate(
        prompt=f"summarize contents of hello-world.txt (in '{workspace_dir}')",
        tools=filtered_tools
    )
    
    await mcp_host.close()
    return result.text


@ai.flow(name='dynamic_prefix_tool')
async def dynamic_prefix_tool(query: str = ''):
    """Read file using prefix tool selection."""
    await mcp_host.start()
    tools = await mcp_host.register_tools(ai)
    
    # Filter for prefix: 'fs/read_*'
    # JS: tools: ['test-mcp-manager:tool/fs/read_*']
    import fnmatch
    filtered_tools = [t for t in tools if fnmatch.fnmatch(t, '*/fs/read_*')]

    result = await ai.generate(
        prompt=f"summarize contents of hello-world.txt (in '{workspace_dir}')",
        tools=filtered_tools
    )
    
    await mcp_host.close()
    return result.text


@ai.flow(name='dynamic_disable_enable')
async def dynamic_disable_enable(query: str = ''):
    """Test disabling and re-enabling an MCP client."""
    await mcp_host.start()
    tools = await mcp_host.register_tools(ai)
    
    import fnmatch
    filtered_tools = [t for t in tools if fnmatch.fnmatch(t, '*/fs/read_file') or t.endswith('fs/read_file')]

    # 1. Run successfully
    result1 = await ai.generate(
        prompt=f"summarize contents of hello-world.txt (in '{workspace_dir}')",
        tools=filtered_tools
    )
    text1 = result1.text

    # 2. Disable 'fs' and try to run (should fail)
    await mcp_host.disable('fs')
    text2 = ""
    try:
        # Note: In Python, we might need to verify if tools list is updated 
        # or if the tool call fails. disable() closes connection.
        # register_tools should ideally be called again or the tool invocation fails.
        # Since we passed 'filtered_tools' (names), the model will try to call.
        # The tool wrapper checks connection.
        result = await ai.generate(
            prompt=f"summarize contents of hello-world.txt (in '{workspace_dir}')",
            tools=filtered_tools
        )
        text2 = f"ERROR! This should have failed but succeeded: {result.text}"
    except Exception as e:
        text2 = str(e)

    # 3. Re-enable 'fs' and run
    await mcp_host.enable('fs')
    # Re-registering might be needed if registry was cleaned, but here we just re-connnect
    # Implementation detail: Does register_tools need to be called again? 
    # Code shows wrappers capture client, client.session is updated on connect.
    await mcp_host.clients['fs'].connect()
    
    result3 = await ai.generate(
        prompt=f"summarize contents of hello-world.txt (in '{workspace_dir}')",
        tools=filtered_tools
    )
    text3 = result3.text

    await mcp_host.close()
    
    return f"Original: <br/>{text1}<br/>After Disable: <br/>{text2}<br/>After Enable: <br/>{text3}"


@ai.flow(name='test_resource')
async def test_resource(query: str = ''):
    """Test reading a resource (simulated)."""
    await mcp_host.start()
    
    # Python SDK doesn't support 'resources' param in generate yet.
    # We manually fetch the resource and add to prompt.
    # JS: resources: await mcpHost.getActiveResources(ai)
    
    resource_content = "Resource not found"
    uri = 'test://static/resource/1'
    
    # In a real implementation we would look up the resource provider.
    # Here we search 'everything' client or similar.
    found = False
    for client in mcp_host.clients.values():
        if client.session and not client.config.disabled:
            try:
                # Try reading directly
                res = await client.read_resource(uri)
                if res and res.contents:
                     resource_content = res.contents[0].text
                     found = True
                     break
            except Exception:
                continue

    result = await ai.generate(
        prompt=f"analyze this: {resource_content}",
    )
    
    await mcp_host.close()
    return result.text


@ai.flow(name='dynamic_test_resources')
async def dynamic_test_resources(query: str = ''):
    """Test reading resources with wildcard (simulated)."""
    # Same simulation as test_resource
    return await test_resource(query)


@ai.flow(name='dynamic_test_one_resource')
async def dynamic_test_one_resource(query: str = ''):
    """Test reading one specific resource (simulated)."""
    # Same simulation as test_resource
    return await test_resource(query)



@ai.flow(name='update_file')
async def update_file(query: str = ''):
    """Update a file using MCP filesystem client."""
    await mcp_host.start()
    tools = await mcp_host.register_tools(ai)

    result = await ai.generate(
        prompt=f"Improve hello-world.txt (in '{workspace_dir}') by rewriting the text, making it longer, use your imagination.",
        tools=tools
    )

    await mcp_host.close()
    return result.text


class ControlMcpInput(BaseModel):
    action: str  # 'RECONNECT', 'ENABLE', 'DISABLE', 'DISCONNECT'
    client_id: str = 'git-client'


@ai.flow(name='control_mcp')
async def control_mcp(input: ControlMcpInput):
    """Control MCP client connections (enable/disable/reconnect)."""
    client_id = input.client_id
    action = input.action.upper()

    if action == 'DISABLE':
        if client_id in mcp_host.clients:
            mcp_host.clients[client_id].config.disabled = True
            await mcp_host.clients[client_id].close()
    elif action == 'DISCONNECT':
        if client_id in mcp_host.clients:
            await mcp_host.clients[client_id].close()
    elif action == 'RECONNECT':
        if client_id in mcp_host.clients:
            await mcp_host.clients[client_id].connect()
    elif action == 'ENABLE':
        if client_id in mcp_host.clients:
            mcp_host.clients[client_id].config.disabled = False
            await mcp_host.clients[client_id].connect()

    return f"Action {action} completed for {client_id}"


async def main():
    """Run sample flows."""
    logger.info("Starting MCP sample application")

    # Test git commits flow
    logger.info("Testing git_commits flow...")
    try:
        result = await git_commits()
        logger.info("git_commits result", result=result[:200])
    except Exception as e:
        logger.error("git_commits failed", error=str(e))

    # Test get_file flow
    logger.info("Testing get_file flow...")
    try:
        result = await get_file()
        logger.info("get_file result", result=result[:200])
    except Exception as e:
        logger.error("get_file failed", error=str(e))


if __name__ == '__main__':
    ai.run_main(main())
