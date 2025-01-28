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
  getStreamingCallback,
  runWithStreamingCallback,
  stripUndefinedProps,
  z,
} from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';
import { Registry } from '@genkit-ai/core/registry';
import { toJsonSchema } from '@genkit-ai/core/schema';
import { SPAN_TYPE_ATTR, runInNewSpan } from '@genkit-ai/core/tracing';
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
  MessageSchema,
  ModelAction,
  ModelInfo,
  ModelMiddleware,
  ModelRequest,
  Part,
  Role,
  ToolDefinitionSchema,
  resolveModel,
} from '../model.js';
import { ToolAction, resolveTools, toToolDefinition } from '../tool.js';
import {
  assertValidToolNames,
  resolveToolRequests,
} from './resolve-tool-requests.js';

export const GenerateActionOptionsSchema = z.object({
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
export type GenerateActionOptions = z.infer<typeof GenerateActionOptionsSchema>;

/**
 * Encapsulates all generate logic. This is similar to `generateAction` except not an action and can take middleware.
 */
export async function generateHelper(
  registry: Registry,
  options: {
    rawRequest: GenerateActionOptions;
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

/** Take the raw request and resolve tools, model, and format into their registry action counterparts. */
async function resolveParameters(
  registry: Registry,
  request: GenerateActionOptions
) {
  const [model, tools, format] = await Promise.all([
    resolveModel(registry, request.model, { warnDeprecated: true }).then(
      (r) => r.modelAction
    ),
    resolveTools(registry, request.tools),
    resolveFormat(registry, request.output),
  ]);
  return { model, tools, format };
}

/** Given a raw request and a formatter, apply the formatter's logic and instructions to the request. */
function applyFormat(
  rawRequest: GenerateActionOptions,
  resolvedFormat?: Formatter
) {
  const outRequest = { ...rawRequest };
  // If is schema is set but format is not explicitly set, default to `json` format.
  if (rawRequest.output?.jsonSchema && !rawRequest.output?.format) {
    outRequest.output = { ...rawRequest.output, format: 'json' };
  }

  const instructions = resolveInstructions(
    resolvedFormat,
    outRequest.output?.jsonSchema,
    outRequest?.output?.instructions
  );

  if (resolvedFormat) {
    outRequest.messages = injectInstructions(outRequest.messages, instructions);
    outRequest.output = {
      // use output config from the format
      ...resolvedFormat.config,
      // if anything is set explicitly, use that
      ...outRequest.output,
    };
  }

  return outRequest;
}

function applyTransferPreamble(
  rawRequest: GenerateActionOptions,
  transferPreamble?: GenerateActionOptions
): GenerateActionOptions {
  if (!transferPreamble) {
    return rawRequest;
  }

  return stripUndefinedProps({
    ...rawRequest,
    messages: [
      ...tagAsPreamble(transferPreamble.messages!)!,
      ...rawRequest.messages.filter((m) => !m.metadata?.preamble),
    ],
    toolChoice: transferPreamble.toolChoice || rawRequest.toolChoice,
    tools: transferPreamble.tools || rawRequest.tools,
  });
}

async function generate(
  registry: Registry,
  {
    rawRequest,
    middleware,
    currentTurn,
    messageIndex,
  }: {
    rawRequest: GenerateActionOptions;
    middleware: ModelMiddleware[] | undefined;
    currentTurn: number;
    messageIndex: number;
  }
): Promise<GenerateResponseData> {
  const { model, tools, format } = await resolveParameters(
    registry,
    rawRequest
  );
  rawRequest = applyFormat(rawRequest, format);

  // check to make sure we don't have overlapping tool names *before* generation
  await assertValidToolNames(tools);

  const request = await actionToGenerateRequest(
    rawRequest,
    tools,
    format,
    model
  );

  const previousChunks: GenerateResponseChunkData[] = [];

  let chunkRole: Role = 'model';
  // convenience method to create a full chunk from role and data, append the chunk
  // to the previousChunks array, and increment the message index as needed
  const makeChunk = (
    role: Role,
    chunk: GenerateResponseChunkData
  ): GenerateResponseChunk => {
    if (role !== chunkRole) messageIndex++;
    chunkRole = role;

    const prevToSend = [...previousChunks];
    previousChunks.push(chunk);

    return new GenerateResponseChunk(chunk, {
      index: messageIndex,
      role,
      previousChunks: prevToSend,
      parser: format?.handler(request.output?.schema).parseChunk,
    });
  };

  const streamingCallback = getStreamingCallback(registry);
  const response = await runWithStreamingCallback(
    registry,
    streamingCallback &&
      ((chunk: GenerateResponseChunkData) =>
        streamingCallback(makeChunk('model', chunk))),
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
        parser: format?.handler(request.output?.schema).parseMessage,
      });
    }
  );

  // Throw an error if the response is not usable.
  response.assertValid();
  const generatedMessage = response.message!; // would have thrown if no message

  const toolRequests = generatedMessage.content.filter(
    (part) => !!part.toolRequest
  );

  if (rawRequest.returnToolRequests || toolRequests.length === 0) {
    if (toolRequests.length === 0) response.assertValidSchema(request);
    return response.toJSON();
  }

  const maxIterations = rawRequest.maxTurns ?? 5;
  if (currentTurn + 1 > maxIterations) {
    throw new GenerationResponseError(
      response,
      `Exceeded maximum tool call iterations (${maxIterations})`,
      'ABORTED',
      { request }
    );
  }

  const { revisedModelMessage, toolMessage, transferPreamble } =
    await resolveToolRequests(registry, rawRequest, generatedMessage);

  // if an interrupt message is returned, stop the tool loop and return a response
  if (revisedModelMessage) {
    return {
      ...response.toJSON(),
      finishReason: 'interrupted',
      finishMessage: 'One or more tool calls resulted in interrupts.',
      message: revisedModelMessage,
    };
  }

  // if the loop will continue, stream out the tool response message...
  streamingCallback?.(
    makeChunk('tool', {
      content: toolMessage!.content,
    })
  );

  let nextRequest = {
    ...rawRequest,
    messages: [...rawRequest.messages, generatedMessage, toolMessage!],
  };
  nextRequest = applyTransferPreamble(nextRequest, transferPreamble);

  // then recursively call for another loop
  return await generateHelper(registry, {
    rawRequest: nextRequest,
    middleware: middleware,
    currentTurn: currentTurn + 1,
    messageIndex: messageIndex + 1,
  });
}

async function actionToGenerateRequest(
  options: GenerateActionOptions,
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
