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
import {
  injectInstructions,
  resolveFormat,
  resolveInstructions,
} from '../formats/index.js';
import { Formatter } from '../formats/types.js';
import {
  GenerateResponse,
  GenerateResponseChunk,
  GenerationResponseError,
  tagAsPreamble,
} from '../generate.js';
import {
  GenerateRequest,
  GenerateRequestSchema,
  GenerateResponseChunkData,
  GenerateResponseData,
  MessageData,
  MessageSchema,
  ModelAction,
  ModelInfo,
  ModelMiddleware,
  ModelRequest,
  Part,
  Role,
  ToolDefinitionSchema,
  ToolResponsePart,
  resolveModel,
} from '../model.js';
import {
  ToolAction,
  ToolInterruptError,
  resolveTools,
  toToolDefinition,
} from '../tool.js';

export const GenerateUtilParamSchema = z.object({
  /** A model name (e.g. `vertexai/gemini-1.0-pro`). */
  model: z.string(),
  /** Retrieved documents to be used as context for this generation. */
  docs: z.array(DocumentDataSchema).optional(),
  /** Conversation history for multi-turn prompting when supported by the underlying model. */
  messages: z.array(MessageSchema),
  /** List of registered tool names for this generation if supported by the underlying model. */
  tools: z.array(z.union([z.string(), ToolDefinitionSchema])).optional(),
  /** Tool calling mode. `auto` lets the model decide whether to use tools, `required` forces the model to choose a tool, and `none` forces the model not to use any tools. Defaults to `auto`.  */
  toolChoice: z.enum(['auto', 'required', 'none']).optional(),
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
  /** Maximum number of tool call iterations that can be performed in a single generate call (default 5). */
  maxTurns: z.number().optional(),
});

/**
 * Encapsulates all generate logic. This is similar to `generateAction` except not an action and can take middleware.
 */
export async function generateHelper(
  registry: Registry,
  options: {
    rawRequest: z.infer<typeof GenerateUtilParamSchema>;
    middleware?: ModelMiddleware[];
    currentTurn?: number;
    messageIndex?: number;
  }
): Promise<GenerateResponseData> {
  let currentTurn = options.currentTurn ?? 0;
  let messageIndex = options.messageIndex ?? 0;
  // do tracing
  return await runInNewSpan(
    registry,
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
      metadata.input = options.rawRequest;
      const output = await generate(registry, {
        rawRequest: options.rawRequest,
        middleware: options.middleware,
        currentTurn,
        messageIndex,
      });
      metadata.output = JSON.stringify(output);
      return output;
    }
  );
}

async function generate(
  registry: Registry,
  options: {
    rawRequest: z.infer<typeof GenerateUtilParamSchema>;
    middleware: ModelMiddleware[] | undefined;
    currentTurn: number;
    messageIndex: number;
  }
): Promise<GenerateResponseData> {
  const { modelAction: model } = await resolveModel(
    registry,
    options.rawRequest.model
  );
  if (model.__action.metadata?.model.stage === 'deprecated') {
    logger.warn(
      `${clc.bold(clc.yellow('Warning:'))} ` +
        `Model '${model.__action.name}' is deprecated and may be removed in a future release.`
    );
  }

  const tools = await resolveTools(registry, options.rawRequest.tools);

  const resolvedSchema = toJsonSchema({
    jsonSchema: options.rawRequest.output?.jsonSchema,
  });

  // If is schema is set but format is not explicitly set, default to `json` format.
  if (options.rawRequest.output?.jsonSchema && !options.rawRequest.output?.format) {
    options.rawRequest.output.format = 'json';
  }
  const resolvedFormat = await resolveFormat(registry, options.rawRequest.output);
  const instructions = resolveInstructions(
    resolvedFormat,
    resolvedSchema,
    options.rawRequest?.output?.instructions
  );
  if (resolvedFormat) {
    options.rawRequest.messages = injectInstructions(options.rawRequest.messages, instructions);
    options.rawRequest.output = {
      // use output config from the format
      ...resolvedFormat.config,
      // if anything is set explicitly, use that
      ...options.rawRequest.output,
    };
  }

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
    options.rawRequest,
    tools,
    resolvedFormat,
    model
  );

  const accumulatedChunks: GenerateResponseChunkData[] = [];

  const streamingCallback = getStreamingCallback(registry);
  const response = await runWithStreamingCallback(
    registry,
    streamingCallback
      ? (chunk: GenerateResponseChunkData) => {
          // Store accumulated chunk data
          if (streamingCallback) {
            streamingCallback!(
              new GenerateResponseChunk(chunk, {
                index: options.messageIndex,
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
        if (!options.middleware || index === options.middleware.length) {
          // end of the chain, call the original model action
          return await model(req);
        }

        const currentMiddleware = options.middleware[index];
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
  response.assertValid();
  const message = response.message!; // would have thrown if no message

  const toolCalls = message.content.filter((part) => !!part.toolRequest);
  if (options.rawRequest.returnToolRequests || toolCalls.length === 0) {
    if (toolCalls.length === 0) {
      response.assertValidSchema(request);
    }
    return response.toJSON();
  }
  const maxIterations = options.rawRequest.maxTurns ?? 5;
  if (options.currentTurn + 1 > maxIterations) {
    throw new GenerationResponseError(
      response,
      `Exceeded maximum tool call iterations (${maxIterations})`,
      'ABORTED',
      { request }
    );
  }

  const toolResponses: ToolResponsePart[] = [];
  let messages: MessageData[] = [...request.messages, message];
  let newTools = options.rawRequest.tools;
  let newToolChoice = options.rawRequest.toolChoice;
  let interruptedParts: Part[] = [];
  let pendingToolRequests: Part[] = [];
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
      try {
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
        newToolChoice = newPreamble.toolChoice;
      } catch (e) {
        if (e instanceof ToolInterruptError) {
          logger.debug(`interrupted tool ${part.toolRequest?.name}`);
          part.metadata = { ...part.metadata, interrupt: e.metadata || true };
          interruptedParts.push(part);
        } else {
          throw e;
        }
      }
    } else {
      try {
        const toolOutput = await tool(part.toolRequest?.input);
        toolResponses.push({
          toolResponse: {
            name: part.toolRequest.name,
            ref: part.toolRequest.ref,
            output: toolOutput,
          },
        });
        // we prep these in case any other tool gets interrupted.
        pendingToolRequests.push({
          ...part,
          metadata: {
            ...part.metadata,
            pendingToolResponse: {
              name: part.toolRequest.name,
              ref: part.toolRequest.ref,
              output: toolOutput,
            },
          },
        });
      } catch (e) {
        if (e instanceof ToolInterruptError) {
          logger.debug(`interrupted tool ${part.toolRequest?.name}`);
          part.metadata = { ...part.metadata, interrupt: e.metadata || true };
          interruptedParts.push(part);
        } else {
          throw e;
        }
      }
    }
  }
  options.messageIndex++;
  const nextRequest = {
    ...options.rawRequest,
    messages: [
      ...messages,
      {
        role: 'tool',
        content: toolResponses,
      },
    ] as MessageData[],
    tools: newTools,
    toolCoice: newToolChoice,
  };
  // stream out the tool responses
  streamingCallback?.(
    new GenerateResponseChunk(
      {
        content: toolResponses,
      },
      {
        index: options.messageIndex,
        role: 'model',
        previousChunks: accumulatedChunks,
        parser: resolvedFormat?.handler(request.output?.schema).parseChunk,
      }
    )
  );
  if (interruptedParts.length > 0) {
    const nonToolParts =
      (response.message?.content.filter((c) => !c.toolRequest) as Part[]) || [];
    return {
      ...response.toJSON(),
      finishReason: 'interrupted',
      message: {
        role: 'model',
        content: nonToolParts
          .concat(pendingToolRequests)
          .concat(interruptedParts),
      },
    };
  }
  return await generateHelper(registry, {
    rawRequest: nextRequest,
    middleware: options.middleware,
    currentTurn: options.currentTurn + 1,
    messageIndex: options.messageIndex + 1,
  });
}

async function actionToGenerateRequest(
  options: z.infer<typeof GenerateUtilParamSchema>,
  resolvedTools: ToolAction[] | undefined,
  resolvedFormat: Formatter | undefined,
  model: ModelAction
): Promise<GenerateRequest> {
  const modelInfo = model.__action.metadata?.model as ModelInfo;
  if (
    (options.tools?.length ?? 0) > 0 &&
    modelInfo?.supports &&
    !modelInfo?.supports?.tools
  ) {
    logger.warn(
      `The model '${model.__action.name}' does not support tools (you set: ${options.tools?.length} tools). ` +
        'The model may not behave the way you expect.'
    );
  }
  if (
    options.toolChoice &&
    modelInfo?.supports &&
    !modelInfo?.supports?.toolChoice
  ) {
    logger.warn(
      `The model '${model.__action.name}' does not support the 'toolChoice' option (you set: ${options.toolChoice}). ` +
        'The model may not behave the way you expect.'
    );
  }
  const out: ModelRequest = {
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
  if (options.toolChoice) {
    out.toolChoice = options.toolChoice;
  }
  if (out.output && !out.output.schema) delete out.output.schema;
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
