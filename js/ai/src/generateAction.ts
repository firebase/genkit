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
  Action,
  getStreamingCallback,
  Middleware,
  runWithStreamingCallback,
  z,
} from '@genkit-ai/core';
import { lookupAction } from '@genkit-ai/core/registry';
import { toJsonSchema, validateSchema } from '@genkit-ai/core/schema';
import { runInNewSpan, SPAN_TYPE_ATTR } from '@genkit-ai/core/tracing';
import * as clc from 'colorette';
import { DocumentDataSchema } from './document.js';
import { GenerateResponse, GenerateResponseChunk } from './generate.js';
import {
  CandidateData,
  GenerateRequest,
  GenerateRequestSchema,
  GenerateResponseChunkData,
  GenerateResponseData,
  MessageData,
  MessageSchema,
  ModelAction,
  Part,
  PartSchema,
  Role,
  ToolDefinitionSchema,
  ToolResponsePart,
} from './model.js';
import { ToolAction, toToolDefinition } from './tool.js';

export const GenerateUtilParamSchema = z.object({
  /** A model name (e.g. `vertexai/gemini-1.0-pro`). */
  model: z.string(),
  /** The prompt for which to generate a response. Can be a string for a simple text prompt or one or more parts for multi-modal prompts. */
  prompt: z.union([z.string(), PartSchema, z.array(PartSchema)]),
  /** Retrieved documents to be used as context for this generation. */
  context: z.array(DocumentDataSchema).optional(),
  /** Conversation history for multi-turn prompting when supported by the underlying model. */
  history: z.array(MessageSchema).optional(),
  /** List of registered tool names for this generation if supported by the underlying model. */
  tools: z.array(z.union([z.string(), ToolDefinitionSchema])).optional(),
  /** Configuration for the generation request. */
  config: z.any().optional(),
  /** Configuration for the desired output of the request. Defaults to the model's default output if unspecified. */
  output: z
    .object({
      format: z
        .union([z.literal('text'), z.literal('json'), z.literal('media')])
        .optional(),
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
  input: z.infer<typeof GenerateUtilParamSchema>,
  middleware?: Middleware[]
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
      const output = await generate(input, middleware);
      metadata.output = JSON.stringify(output);
      return output;
    }
  );
}

async function generate(
  rawRequest: z.infer<typeof GenerateUtilParamSchema>,
  middleware?: Middleware[]
): Promise<GenerateResponseData> {
  const model = (await lookupAction(
    `/model/${rawRequest.model}`
  )) as ModelAction;
  if (!model) {
    throw new Error(`Model ${rawRequest.model} not found`);
  }
  if (model.__action.metadata?.model.stage === 'deprecated') {
    console.warn(
      `${clc.bold(clc.yellow('Warning:'))} ` +
        `Model '${model.__action.name}' is deprecated and may be removed in a future release.`
    );
  }

  let tools: ToolAction[] | undefined;
  if (rawRequest.tools?.length) {
    if (!model.__action.metadata?.model.supports?.tools) {
      throw new Error(
        `Model ${rawRequest.model} does not support tools, but some tools were supplied to generate(). Please call generate() without tools if you would like to use this model.`
      );
    }
    tools = await Promise.all(
      rawRequest.tools.map(async (toolRef) => {
        if (typeof toolRef === 'string') {
          const tool = (await lookupAction(toolRef)) as ToolAction;
          if (!tool) {
            throw new Error(`Tool ${toolRef} not found`);
          }
          return tool;
        }
        throw '';
      })
    );
  }

  const request = await actionToGenerateRequest(rawRequest, tools);

  const accumulatedChunks: GenerateResponseChunkData[] = [];

  const streamingCallback = getStreamingCallback();
  const response = await runWithStreamingCallback(
    streamingCallback
      ? (chunk: GenerateResponseChunkData) => {
          // Store accumulated chunk data
          accumulatedChunks.push(chunk);
          if (streamingCallback) {
            streamingCallback!(
              new GenerateResponseChunk(chunk, accumulatedChunks)
            );
          }
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

      return new GenerateResponse(await dispatch(0, request));
    }
  );

  // Throw an error if the response is not usable.
  response.assertValid(request);
  const message = response.message!; // would have thrown if no message

  const toolCalls = message.content.filter((part) => !!part.toolRequest);
  if (rawRequest.returnToolRequests || toolCalls.length === 0) {
    return response.toJSON();
  }
  const toolResponses: ToolResponsePart[] = await Promise.all(
    toolCalls.map(async (part) => {
      if (!part.toolRequest) {
        throw Error(
          'Tool request expected but not provided in tool request part'
        );
      }
      const tool = tools?.find(
        (tool) => tool.__action.name === part.toolRequest?.name
      );
      if (!tool) {
        throw Error('Tool not found');
      }
      return {
        toolResponse: {
          name: part.toolRequest.name,
          ref: part.toolRequest.ref,
          output: await tool(part.toolRequest?.input),
        },
      };
    })
  );
  const nextRequest = {
    ...rawRequest,
    history: [...request.messages, message],
    prompt: toolResponses,
  };
  return await generateHelper(nextRequest, middleware);
}

async function actionToGenerateRequest(
  options: z.infer<typeof GenerateUtilParamSchema>,
  resolvedTools?: ToolAction[]
): Promise<GenerateRequest> {
  const promptMessage: MessageData = { role: 'user', content: [] };
  if (typeof options.prompt === 'string') {
    promptMessage.content.push({ text: options.prompt });
  } else if (Array.isArray(options.prompt)) {
    promptMessage.role = inferRoleFromParts(options.prompt);
    promptMessage.content.push(...(options.prompt as Part[]));
  } else {
    promptMessage.role = inferRoleFromParts([options.prompt]);
    promptMessage.content.push(options.prompt);
  }
  const messages: MessageData[] = [...(options.history || []), promptMessage];

  const out = {
    messages,
    config: options.config,
    context: options.context,
    tools: resolvedTools?.map((tool) => toToolDefinition(tool)) || [],
    output: {
      format:
        options.output?.format ||
        (options.output?.jsonSchema ? 'json' : 'text'),
      schema: toJsonSchema({
        jsonSchema: options.output?.jsonSchema,
      }),
    },
  };
  if (!out.output.schema) delete out.output.schema;
  return out;
}

const isValidCandidate = (
  candidate: CandidateData,
  tools: Action<any, any>[]
): boolean => {
  // Check if tool calls are vlaid
  const toolCalls = candidate.message.content.filter(
    (part) => !!part.toolRequest
  );

  // make sure every tool called exists and has valid input
  return toolCalls.every((toolCall) => {
    const tool = tools?.find(
      (tool) => tool.__action.name === toolCall.toolRequest?.name
    );
    if (!tool) return false;
    const { valid } = validateSchema(toolCall.toolRequest?.input, {
      schema: tool.__action.inputSchema,
      jsonSchema: tool.__action.inputJsonSchema,
    });
    return valid;
  });
};

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
