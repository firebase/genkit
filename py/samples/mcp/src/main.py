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
from pathlib import Path
from typing import Optional

import structlog
from pydantic import BaseModel

from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI
from genkit.plugins.mcp import McpServerConfig, create_mcp_host

logger = structlog.get_logger(__name__)

# Get the current directory
current_dir = Path(__file__).parent
workspace_dir = current_dir.parent / 'test-workspace'
# repo_root is 4 levels up: py/samples/mcp/src -> py/samples/mcp -> py/samples -> py -> root
repo_root = current_dir.parent.parent.parent.parent

# Initialize Genkit with GoogleAI
ai = Genkit(plugins=[GoogleAI()], model='googleai/gemini-2.5-flash')

# Create MCP host with multiple servers
mcp_host = create_mcp_host({
    'git-client': McpServerConfig(command='uvx', args=['mcp-server-git']),
    'fs': McpServerConfig(command='npx', args=['-y', '@modelcontextprotocol/server-filesystem', str(workspace_dir)]),
    'everything': McpServerConfig(command='npx', args=['-y', '@modelcontextprotocol/server-everything']),
})

from functools import wraps

# ... (imports remain)

# ... (mcp_host definition remains)


def with_mcp_host(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        await mcp_host.start()
        try:
            return await func(*args, **kwargs)
        finally:
            await mcp_host.close()

    return wrapper


@ai.flow(name='git-commits')
@with_mcp_host
async def git_commits(query: str = ''):
    """Summarize recent git commits using MCP git client."""
    # Register tools to registry directly
    await mcp_host.register_tools(ai)

    # Get active tool names for this call
    tools = await mcp_host.get_active_tools(ai)

    result = await ai.generate(prompt=f"summarize last 5 commits in '{repo_root}'", tools=tools)
    return result.text


@ai.flow(name='dynamic-git-commits')
@with_mcp_host
async def dynamic_git_commits(query: str = ''):
    """Summarize recent git commits using wildcard tool selection."""
    await mcp_host.register_tools(ai)

    # In Python, we might not support wildcards in tools list yet,
    # so we'll simulate by getting all tools matching the pattern.
    # So we use the string pattern if supported.
    # tools=['git-client_*']

    all_tools = await mcp_host.get_active_tools(ai)
    tools = [t for t in all_tools if t.startswith('git-client_')]

    result = await ai.generate(
        prompt=f"summarize last 5 commits. You must use the argument key 'repo_path' set to '{repo_root}'. Do not use 'path'.",
        tools=tools,
    )
    return result.text


@ai.flow(name='get-file')
@with_mcp_host
async def get_file(query: str = ''):
    """Read and summarize a file using MCP filesystem client."""
    await mcp_host.register_tools(ai)
    tools = await mcp_host.get_active_tools(ai)

    result = await ai.generate(prompt=f"summarize contents of hello-world.txt (in '{workspace_dir}')", tools=tools)
    return result.text


@ai.flow(name='dynamic-get-file')
@with_mcp_host
async def dynamic_get_file(query: str = ''):
    """Read file using specific tool selection."""
    await mcp_host.register_tools(ai)

    # Filter for specific tool: 'fs_read_file'
    tools = [t for t in await mcp_host.get_active_tools(ai) if t == 'fs_read_file']

    result = await ai.generate(prompt=f"summarize contents of hello-world.txt (in '{workspace_dir}')", tools=tools)
    return result.text


@ai.flow(name='dynamic-prefix-tool')
@with_mcp_host
async def dynamic_prefix_tool(query: str = ''):
    """Read file using prefix tool selection."""
    await mcp_host.register_tools(ai)

    # Filter for prefix: 'fs_read_'
    all_tools = await mcp_host.get_active_tools(ai)
    tools = [t for t in all_tools if t.startswith('fs_read_')]

    result = await ai.generate(prompt=f"summarize contents of hello-world.txt (in '{workspace_dir}')", tools=tools)
    return result.text


@ai.flow(name='dynamic-disable-enable')
@with_mcp_host
async def dynamic_disable_enable(query: str = ''):
    """Test disabling and re-enabling an MCP client."""
    await mcp_host.register_tools(ai)
    tools = [t for t in await mcp_host.get_active_tools(ai) if t == 'fs_read_file']

    # Run successfully
    result1 = await ai.generate(prompt=f"summarize contents of hello-world.txt (in '{workspace_dir}')", tools=tools)
    text1 = result1.text

    # Disable 'fs' and try to run (should fail)
    await mcp_host.disable('fs')
    text2 = ''
    try:
        # We don't re-register tools, hoping the registry or generate handles the disabled client
        result = await ai.generate(prompt=f"summarize contents of hello-world.txt (in '{workspace_dir}')", tools=tools)
        text2 = f'ERROR! This should have failed but succeeded: {result.text}'
    except Exception as e:
        text2 = str(e)

    # Re-enable 'fs' and run
    await mcp_host.enable('fs')
    # Re-connect/re-register might be needed
    await mcp_host.register_tools(ai)

    result3 = await ai.generate(prompt=f"summarize contents of hello-world.txt (in '{workspace_dir}')", tools=tools)
    text3 = result3.text

    return f'Original: <br/>{text1}<br/>After Disable: <br/>{text2}<br/>After Enable: <br/>{text3}'


@ai.flow(name='test-resource')
@with_mcp_host
async def test_resource(query: str = ''):
    """Test reading a resource."""
    # Pass resources as grounding context if supported
    resources = await mcp_host.get_active_resources(ai)

    result = await ai.generate(
        prompt=[{'text': 'analyze this: '}, {'resource': {'uri': 'test://static/resource/1'}}], resources=resources
    )

    return result.text


@ai.flow(name='dynamic-test-resources')
@with_mcp_host
async def dynamic_test_resources(query: str = ''):
    """Test reading resources with wildcard."""
    # Simulate wildcard resources if not natively supported
    # resources=['resource/*']

    all_resources = await mcp_host.get_active_resources(ai)
    resources = [r for r in all_resources if r.startswith('test://')]  # simplified filter

    result = await ai.generate(
        prompt=[{'text': 'analyze this: '}, {'resource': {'uri': 'test://static/resource/1'}}], resources=resources
    )
    return result.text


@ai.flow(name='dynamic-test-one-resource')
@with_mcp_host
async def dynamic_test_one_resource(query: str = ''):
    """Test reading one specific resource."""
    resources = ['test://static/resource/1']

    result = await ai.generate(
        prompt=[{'text': 'analyze this: '}, {'resource': {'uri': 'test://static/resource/1'}}], resources=resources
    )
    return result.text


@ai.flow(name='update-file')
@with_mcp_host
async def update_file(query: str = ''):
    """Update a file using MCP filesystem client."""
    await mcp_host.register_tools(ai)
    tools = await mcp_host.get_active_tools(ai)

    result = await ai.generate(
        prompt=f"Improve hello-world.txt (in '{workspace_dir}') by rewriting the text, making it longer, use your imagination.",
        tools=tools,
    )
    return result.text


class ControlMcpInput(BaseModel):
    action: str  # 'RECONNECT', 'ENABLE', 'DISABLE', 'DISCONNECT'
    client_id: Optional[str] = 'git-client'


@ai.flow(name='controlMcp')
async def control_mcp(input: ControlMcpInput):
    """Control MCP client connections (enable/disable/reconnect)."""
    client_id = input.client_id
    action = input.action.upper()

    if action == 'DISABLE':
        await mcp_host.disable(client_id)
    elif action == 'DISCONNECT':
        # Assuming disconnect is equivalent to close for a specific client
        if client_id in mcp_host.clients:
            await mcp_host.clients[client_id].close()
    elif action == 'RECONNECT':
        await mcp_host.reconnect(client_id)
    elif action == 'ENABLE':
        await mcp_host.enable(client_id)

    return f'Action {action} completed for {client_id}'


async def main():
    """Run sample flows."""
    import os
    
    # Only run test flows if not in dev mode (Dev UI)
    if os.getenv('GENKIT_ENV') == 'dev':
        logger.info('Running in dev mode - flows available in Dev UI')
        logger.info('Genkit server running. Press Ctrl+C to stop.')
        # Keep the process alive for Dev UI
        await asyncio.Event().wait()
        return
    
    logger.info('Starting MCP sample application')
    from genkit.core.action.types import ActionKind
    flows = ai.registry.get_actions_by_kind(ActionKind.FLOW)
    logger.info(f"DEBUG: Registered flows: {list(flows.keys())}")

    # Test git commits flow
    logger.info('Testing git-commits flow...')
    try:
        result = await git_commits()
        logger.info('git-commits result', result=result[:200])
    except Exception as e:
        logger.error('git-commits failed', error=str(e), exc_info=True)

    # Test get-file flow
    logger.info('Testing get-file flow...')
    try:
        result = await get_file()
        logger.info('get-file result', result=result[:200])
    except Exception as e:
        logger.error('get-file failed', error=str(e), exc_info=True)


if __name__ == '__main__':
    import sys
    # If running directly (not via genkit start), execute the test flows
    if len(sys.argv) == 1:
        ai.run_main(main())
    # Otherwise, just keep the server running for Dev UI
    else:
        # This allows genkit start to work properly
        pass
