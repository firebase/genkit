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

import {
  // GenerateResponse as AiGenerateResponse,
  // GenerateStreamResponse as AiGenerateStreamResponse,
  ExecutablePrompt,
  GenerateResponseChunk,
  PromptGenerateOptions,
} from '@genkit-ai/ai';
import type { Prompt } from '@modelcontextprotocol/sdk/types.js';
import {
  GenerateOptions,
  GenerateResponse as AiGenerateResponse,
  GenerateStreamResponse as AiGenerateStreamResponse,
  Genkit,
  GenkitError,
  JSONSchema,
  MessageData,
  ToolAction,
  z,
} from 'genkit';
import { logger } from 'genkit/logging';
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

/**
 * Registers a single MCP prompt as a Genkit prompt.
 * It defines a new Genkit prompt action that, when called, will
 * interact with the MCP client to fetch and render the corresponding MCP prompt.
 *
 * @param ai The Genkit instance to define the prompt on.
 * @param client The MCP client instance used to interact with the MCP server.
 * @param prompt The MCP Prompt object to register.
 * @param params Contains the Genkit client name and the MCP server name for namespacing and logging.
 */
function registerPrompt(
  ai: Genkit,
  client: any, // Use 'any' or let TS infer; removing specific type import
  prompt: Prompt,
  params: { name: string; serverName: string }
) {
  logger.debug(`[MCP] Registering MCP prompt ${params.name}/${prompt.name}`);
  ai.definePrompt({
    name: prompt.name,
    description: prompt.description || '',
    input: { jsonSchema: toSchema(prompt.arguments) },
    output: { format: 'text' },
    messages: async (args) => {
      logger.debug(
        `[MCP] Calling MCP prompt ${params.name}/${prompt.name} with arguments`,
        JSON.stringify(args)
      );
      const result = await client.getPrompt({
        name: prompt.name,
        arguments: args,
      });
      return result.messages.map(fromMcpPromptMessage);
    },
  });
}

function createExecutablePrompt<
  I extends z.ZodTypeAny = z.ZodTypeAny,
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  client: any, // Use 'any' or let TS infer; removing specific type import
  prompt: Prompt,
  params: { name: string; serverName: string }
): ExecutablePrompt<z.infer<I>, O, CustomOptions> {
  const callPrompt = async (
    input?: z.infer<I>,
    opts?: PromptGenerateOptions<O, CustomOptions>
  ): Promise<AiGenerateResponse<z.infer<O>>> => {
    logger.debug(
      `[MCP] Calling MCP prompt ${params.name}/${prompt.name} with arguments`,
      JSON.stringify(input)
    );
    const result = await client.getPrompt({
      name: prompt.name,
      arguments: input,
    });
    const messages = result.messages.map(fromMcpPromptMessage);
    return new AiGenerateResponse<z.infer<O>>({ message: messages.at(-1) });
  };

  callPrompt.stream = (
    input?: z.infer<I>,
    opts?: PromptGenerateOptions<O, CustomOptions>
  ): AiGenerateStreamResponse<z.infer<O>> => {
    logger.debug(
      `[MCP] Streaming MCP prompt ${params.name}/${prompt.name} with arguments`,
      JSON.stringify(input)
    );
    // const result = await client.getPrompt({
    //   name: prompt.name,
    //   arguments: input,
    // });
    // const messages: MessageData[] = result.messages.map(fromMcpPromptMessage);

    return {
      get stream(): AsyncIterable<GenerateResponseChunk> {
        async function* generateAsyncIterable() {
          const result = await client.getPrompt({
            name: prompt.name,
            arguments: input,
          });
          const messages: MessageData[] =
            result.messages.map(fromMcpPromptMessage);

          for (let index = 0; index < messages.length; index++) {
            yield new GenerateResponseChunk(messages[index], {
              role: messages[index].role,
              index,
            });
          }
        }
        return generateAsyncIterable();
      },

      get response(): Promise<AiGenerateResponse<O>> {
        return new Promise(async (resolve) => {
          const result = await client.getPrompt({
            name: prompt.name,
            arguments: input,
          });
          const messages = result.messages.map(fromMcpPromptMessage);

          resolve(
            new AiGenerateResponse<z.infer<O>>({ message: messages.at(-1) })
          );
        });
      },
    } as AiGenerateStreamResponse<O>;
  };

  callPrompt.render = async (
    input?: I,
    opts?: PromptGenerateOptions<O, CustomOptions>
  ): Promise<GenerateOptions<O, CustomOptions>> => {
    throw new GenkitError({
      status: 'UNIMPLEMENTED',
      message: `[MCP] prompt.render not supported with MCP`,
    });
  };

  callPrompt.asTool = async (): Promise<ToolAction> => {
    throw new GenkitError({
      status: 'UNIMPLEMENTED',
      message: `[MCP] prompt.asTool not supported with MCP`,
    });
  };

  return callPrompt as ExecutablePrompt<z.infer<I>, O, CustomOptions>;
}

/**
 * Lookup all tools available in the server and register each as a Genkit tool.
 */
export async function registerAllPrompts(
  ai: Genkit,
  client: any, // Use 'any' or let TS infer; removing specific type import
  params: { name: string; serverName: string }
): Promise<void> {
  let cursor: string | undefined;
  while (true) {
    const { nextCursor, prompts } = await client.listPrompts({ cursor });
    prompts.forEach((p) => registerPrompt(ai, client, p, params));
    cursor = nextCursor;
    if (!cursor) break;
  }
}

/**
 * Lookup all tools available in the server and register each as a Genkit tool.
 */
export async function createExecutablePrompts(
  client: any, // Use 'any' or let TS infer; removing specific type import
  params: { name: string; serverName: string }
): Promise<ExecutablePrompt[]> {
  let cursor: string | undefined;

  let allPrompts: ExecutablePrompt[] = [];
  while (true) {
    const { nextCursor, prompts } = await client.listPrompts({ cursor });
    allPrompts.push(
      ...prompts.map((p) => createExecutablePrompt(client, p, params))
    );
    cursor = nextCursor;
    if (!cursor) break;
  }
  return allPrompts;
}

/**
 * Lookup a specified prompt from the server and return as an ExecutablePrompt.
 */
export async function getExecutablePrompt(
  client: any, // Use 'any' or let TS infer; removing specific type import
  params: { name: string; serverName: string; promptName: string }
): Promise<ExecutablePrompt | undefined> {
  let cursor: string | undefined;

  while (true) {
    const { nextCursor, prompts } = await client.listPrompts({ cursor });
    const maybePrompt = prompts.find(
      (p: Prompt) => p.name === params.promptName
    );
    if (maybePrompt) {
      return createExecutablePrompt(client, maybePrompt, params);
    }
    cursor = nextCursor;
    if (!cursor) break;
  }
  return undefined;
}
