/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import type { Client } from '@modelcontextprotocol/sdk/client/index.js' with { 'resolution-mode': 'import' };
import type { Prompt } from '@modelcontextprotocol/sdk/types.js' with { 'resolution-mode': 'import' };
import { Genkit, JSONSchema } from 'genkit';
import { logger } from 'genkit/logging';
import type { McpClientOptions } from '../index.js';
import { fromMcpPromptMessage } from './message.js';

function toSchema(args: Prompt['arguments']) {
  if (!args) return {};
  const schema: JSONSchema = { type: 'object', properties: {}, required: [] };
  for (const arg of args) {
    schema.properties[arg.name] = {
      type: 'string',
      description: arg.description,
    };
    if (arg.required) schema.required.push(arg.name);
  }
  return schema;
}

function registerPrompt(
  ai: Genkit,
  client: Client,
  prompt: Prompt,
  params: McpClientOptions
) {
  logger.debug(
    `[@genkit-ai/mcp] Registering MCP prompt ${params.name}/${prompt.name}`
  );
  ai.definePrompt(
    {
      name: prompt.name,
      description: prompt.description || '',
      input: { jsonSchema: toSchema(prompt.arguments) },
      output: { format: 'text' },
    },
    async (args) => {
      logger.debug(
        `[@genkit-ai/mcp] Calling MCP prompt ${params.name}/${prompt.name} with arguments`,
        JSON.stringify(args)
      );
      const result = await client.getPrompt({
        name: prompt.name,
        arguments: args,
      });
      return {
        messages: result.messages.map(fromMcpPromptMessage),
      };
    }
  );
}

/**
 * Lookup all tools available in the server and register each as a Genkit tool.
 */
export async function registerAllPrompts(
  ai: Genkit,
  client: Client,
  params: McpClientOptions
): Promise<void> {
  let cursor: string | undefined;
  while (true) {
    const { nextCursor, prompts } = await client.listPrompts({ cursor });
    prompts.forEach((p) => registerPrompt(ai, client, p, params));
    cursor = nextCursor;
    if (!cursor) break;
  }
}
