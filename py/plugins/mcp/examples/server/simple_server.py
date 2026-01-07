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

from pydantic import BaseModel, Field

from genkit.ai import Genkit
from genkit.plugins.mcp import McpServerOptions, create_mcp_server


# Define input model
class AddInput(BaseModel):
    a: int = Field(..., description='First number')
    b: int = Field(..., description='Second number')


import os


def main():
    # Load prompts from the 'prompts' directory relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    prompts_dir = os.path.join(script_dir, 'prompts')

    ai = Genkit(prompt_dir=prompts_dir)

    @ai.tool(name='add', description='add two numbers together')
    def add(input: AddInput):
        return input.a + input.b

    # Genkit Python prompt definition (simplified)
    # Note: In Python, prompts are typically loaded from files via prompt_dir
    # This inline definition is for demonstration purposes
    happy_prompt = ai.define_prompt(
        input_schema={'action': str},
        prompt="If you're happy and you know it, {{action}}.",
    )

    # Create and start MCP server
    # Note: create_mcp_server returns McpServer instance.
    # In JS example: .start() is called.
    server = create_mcp_server(ai, McpServerOptions(name='example_server', version='0.0.1'))

    print('Starting MCP server on stdio...')
    asyncio.run(server.start())


if __name__ == '__main__':
    main()
