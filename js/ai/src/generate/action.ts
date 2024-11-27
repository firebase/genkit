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
  GenkitError,
  getStreamingCallback,
  runWithStreamingCallback,
  z,
} from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';
import { Registry } from '@genkit-ai/core/registry';
import { toJsonSchema } from '@genkit-ai/core/schema';
import { SPAN_TYPE_ATTR, runInNewSpan } from '@genkit-ai/core/tracing';
import * as clc from 'colorette';
import { DocumentDataSchema } from '../document.js';
import { resolveFormat } from '../formats/index.js';
import { Formatter } from '../formats/types.js';
import {
  GenerateResponse,
  GenerateResponseChunk,
  tagAsPreamble,
} from '../generate.js';
import {
  GenerateRequest,
  GenerateRequestSchema,
  GenerateResponseChunkData,
  GenerateResponseData,
  MessageData,
  MessageSchema,
  ModelMiddleware,
  Part,
  Role,
  ToolDefinitionSchema,
  ToolResponsePart,
  resolveModel,
} from '../model.js';
import { ToolAction, resolveTools, toToolDefinition } from '../tool.js';

export const GenerateUtilParamSchema = z.object({
  /** A model name (e.g. `vertexai/gemini-1.0-pro`). */
  model: z.string(),
  /** Retrieved documents to be used as context for this generation. */
  docs: z.array(DocumentDataSchema).optional(),
  /** Conversation history for multi-turn prompting when supported by the underlying model. */
  messages: z.array(MessageSchema),
  /** List of registered tool names for this generation if supported by the underlying model. */
  tools: z.array(z.union([z.string(), ToolDefinitionSchema])).optional(),
  /** Configuration for the generation request. */
  config: z.any().optional(),
  /** Configuration for the desired output of the request. Defaults to the model's default output if unspecified. */
  output: z
    .object({
      format: z.string().optional(),
      contentType: z.string().optional(),
      instructions: z.union([z.boolean(), z.string()]).optional(),
      jsonSchema: z.any().optional(),
    })
    .optional(),
  /** When true, return tool calls for manual processing instead of automatically resolving them. */
  returnToolRequests: z.boolean().optional(),
});

/**
 * Encapsulates all generate logic. This is similar to `generateAction` except not an action and can take middleware.
 */
export async function generateHelper(
  registry: Registry,
  input: z.infer<typeof GenerateUtilParamSchema>,
  middleware?: ModelMiddleware[]
): Promise<GenerateResponseData> {
  // do tracing
  return await runInNewSpan(
    {
      metadata: {
        name: 'generate',
      },
      labels: {
        [SPAN_TYPE_ATTR]: 'helper',
      },
    },
    async (metadata) => {
      metadata.name = 'generate';
      metadata.input = input;
      const output = await generate(registry, input, middleware);
      metadata.output = JSON.stringify(output);
      return output;
    }
  );
}

async function generate(
  registry: Registry,
  rawRequest: z.infer<typeof GenerateUtilParamSchema>,
  middleware?: ModelMiddleware[]
): Promise<GenerateResponseData> {
  const { modelAction: model } = await resolveModel(registry, rawRequest.model);
  if (model.__action.metadata?.model.stage === 'deprecated') {
    logger.warn(
      `${clc.bold(clc.yellow('Warning:'))} ` +
        `Model '${model.__action.name}' is deprecated and may be removed in a future release.`
    );
  }

  const tools = await resolveTools(registry, rawRequest.tools);

  const resolvedFormat = await resolveFormat(registry, rawRequest.output);
  // Create a lookup of tool names with namespaces stripped to original names
  const toolMap = tools.reduce<Record<string, ToolAction>>((acc, tool) => {
    const name = tool.__action.name;
    const shortName = name.substring(name.lastIndexOf('/') + 1);
    if (acc[shortName]) {
      throw new GenkitError({
        status: 'INVALID_ARGUMENT',
        message: `Cannot provide two tools with the same name: '${name}' and '${acc[shortName]}'`,
      });
    }
    acc[shortName] = tool;
    return acc;
  }, {});

  const request = await actionToGenerateRequest(
    rawRequest,
    tools,
    resolvedFormat
  );

  const accumulatedChunks: GenerateResponseChunkData[] = [];

  const streamingCallback = getStreamingCallback();
  const response = await runWithStreamingCallback(
    streamingCallback
      ? (chunk: GenerateResponseChunkData) => {
          // Store accumulated chunk data
          if (streamingCallback) {
            streamingCallback!(
              new GenerateResponseChunk(chunk, {
                index: 0,
                role: 'model',
                previousChunks: accumulatedChunks,
                parser: resolvedFormat?.handler(request.output?.schema)
                  .parseChunk,
              })
            );
          }
          accumulatedChunks.push(chunk);
        }
      : undefined,
    async () => {
      const dispatch = async (
        index: number,
        req: z.infer<typeof GenerateRequestSchema>
      ) => {
        if (!middleware || index === middleware.length) {
          // end of the chain, call the original model action
          return await model(req);
        }

        const currentMiddleware = middleware[index];
        return currentMiddleware(req, async (modifiedReq) =>
          dispatch(index + 1, modifiedReq || req)
        );
      };

      return new GenerateResponse(await dispatch(0, request), {
        request,
        parser: resolvedFormat?.handler(request.output?.schema).parseMessage,
      });
    }
  );

  // Throw an error if the response is not usable.
  response.assertValid(request);
  const message = response.message!; // would have thrown if no message

  const toolCalls = message.content.filter((part) => !!part.toolRequest);
  if (rawRequest.returnToolRequests || toolCalls.length === 0) {
    return response.toJSON();
  }
  const toolResponses: ToolResponsePart[] = [];
  let messages: MessageData[] = [...request.messages, message];
  let newTools = rawRequest.tools;
  for (const part of toolCalls) {
    if (!part.toolRequest) {
      throw Error(
        'Tool request expected but not provided in tool request part'
      );
    }
    const tool = toolMap[part.toolRequest?.name];
    if (!tool) {
      throw Error(`Tool ${part.toolRequest?.name} not found`);
    }
    if ((tool.__action.metadata.type as string) === 'prompt') {
      const newPreamble = await tool(part.toolRequest?.input);
      toolResponses.push({
        toolResponse: {
          name: part.toolRequest.name,
          ref: part.toolRequest.ref,
          output: `transferred to ${part.toolRequest.name}`,
        },
      });
      // swap out the preamble
      messages = [
        ...tagAsPreamble(newPreamble.messages)!,
        ...messages.filter((m) => !m?.metadata?.preamble),
      ];
      newTools = newPreamble.tools;
    } else {
      toolResponses.push({
        toolResponse: {
          name: part.toolRequest.name,
          ref: part.toolRequest.ref,
          output: await tool(part.toolRequest?.input),
        },
      });
    }
  }
  const nextRequest = {
    ...rawRequest,
    messages: [
      ...messages,
      {
        role: 'tool',
        content: toolResponses,
      },
    ] as MessageData[],
    tools: newTools,
  };
  return await generateHelper(registry, nextRequest, middleware);
}

async function actionToGenerateRequest(
  options: z.infer<typeof GenerateUtilParamSchema>,
  resolvedTools?: ToolAction[],
  resolvedFormat?: Formatter
): Promise<GenerateRequest> {
  const out = {
    messages: options.messages,
    config: options.config,
    docs: options.docs,
    tools: resolvedTools?.map(toToolDefinition) || [],
    output: {
      ...(resolvedFormat?.config || {}),
      schema: toJsonSchema({
        jsonSchema: options.output?.jsonSchema,
      }),
    },
  };
  if (!out.output.schema) delete out.output.schema;
  return out;
}

export function inferRoleFromParts(parts: Part[]): Role {
  const uniqueRoles = new Set<Role>();
  for (const part of parts) {
    const role = getRoleFromPart(part);
    uniqueRoles.add(role);
    if (uniqueRoles.size > 1) {
      throw new Error('Contents contain mixed roles');
    }
  }
  return Array.from(uniqueRoles)[0];
}

function getRoleFromPart(part: Part): Role {
  if (part.toolRequest !== undefined) return 'model';
  if (part.toolResponse !== undefined) return 'tool';
  if (part.text !== undefined) return 'user';
  if (part.media !== undefined) return 'user';
  if (part.data !== undefined) return 'user';
  throw new Error('No recognized fields in content');
}
