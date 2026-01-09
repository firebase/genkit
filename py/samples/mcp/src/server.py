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

"""
MCP Server Example

This demonstrates creating an MCP server that exposes Genkit tools, prompts,
and resources through the Model Context Protocol.
"""

import asyncio

from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI
from genkit.plugins.mcp import McpServerOptions, create_mcp_server

# Initialize Genkit
ai = Genkit(plugins=[])


# Define a tool
class AddInput(BaseModel):
    a: int = Field(..., description='First number')
    b: int = Field(..., description='Second number')


@ai.tool(name='add', description='add two numbers together')
def add(input: AddInput) -> int:
    return input.a + input.b


# Define a prompt
happy_prompt = ai.define_prompt(
    name='happy',
    input_schema={'action': str},
    prompt="If you're happy and you know it, {{action}}.",
)


# Define resources
def my_resource_handler(inp):
    return {'content': [{'text': 'my resource'}]}


ai.define_resource(name='my resources', uri='test://static/resource/1', fn=my_resource_handler)


def file_resource_handler(inp):
    uri = inp.uri
    return {'content': [{'text': f'file contents for {uri}'}]}


ai.define_resource(name='file', template='file://{path}', fn=file_resource_handler)


async def main():
    """Start the MCP server."""
    # Create MCP server
    server = create_mcp_server(ai, McpServerOptions(name='example_server', version='0.0.1'))

    print('Starting MCP server on stdio...')
    await server.start()


if __name__ == '__main__':
    asyncio.run(main())
