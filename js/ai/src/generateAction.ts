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
  defineAction,
  getStreamingCallback,
  runWithStreamingCallback,
} from '@genkit-ai/core';
import { lookupAction } from '@genkit-ai/core/registry';
import {
  parseSchema,
  toJsonSchema,
  validateSchema,
} from '@genkit-ai/core/schema';
import { z } from 'zod';
import { DocumentDataSchema } from './document.js';
import {
  Candidate,
  GenerateResponse,
  GenerateResponseChunk,
  NoValidCandidatesError,
} from './generate.js';
import {
  CandidateData,
  GenerateRequest,
  GenerateResponseChunkData,
  GenerateResponseSchema,
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
  /** Number of candidate messages to generate. */
  candidates: z.number().optional(),
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

export const generateAction = defineAction(
  {
    actionType: 'util',
    name: 'generate',
    inputSchema: GenerateUtilParamSchema,
    outputSchema: GenerateResponseSchema,
  },
  async (input) => {
    const model = (await lookupAction(`/model/${input.model}`)) as ModelAction;
    if (!model) {
      throw new Error(`Model ${input.model} not found`);
    }

    let tools: ToolAction[] | undefined;
    if (input.tools?.length) {
      if (!model.__action.metadata?.model.supports?.tools) {
        throw new Error(
          `Model ${input.model} does not support tools, but some tools were supplied to generate(). Please call generate() without tools if you would like to use this model.`
        );
      }
      tools = await Promise.all(
        input.tools.map(async (toolRef) => {
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

    const request = await actionToGenerateRequest(input, tools);

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
      async () => new GenerateResponse(await model(request))
    );

    // throw NoValidCandidates if all candidates are blocked or
    if (
      !response.candidates.some((c) =>
        ['stop', 'length'].includes(c.finishReason)
      )
    ) {
      throw new NoValidCandidatesError({
        message: `All candidates returned finishReason issues: ${JSON.stringify(response.candidates.map((c) => c.finishReason))}`,
        response,
      });
    }

    if (input.output?.jsonSchema && !response.toolRequests()?.length) {
      // find a candidate with valid output schema
      const candidateErrors = response.candidates.map((c) => {
        // don't validate messages that have no text or data
        if (c.text() === '' && c.data() === null) return null;

        try {
          parseSchema(c.output(), {
            jsonSchema: input.output?.jsonSchema,
          });
          return null;
        } catch (e) {
          return e as Error;
        }
      });
      // if all candidates have a non-null error...
      if (candidateErrors.every((c) => !!c)) {
        throw new NoValidCandidatesError({
          message: `Generation resulted in no candidates matching provided output schema.${candidateErrors.map((e, i) => `\n\nCandidate[${i}] ${e!.toString()}`)}`,
          response,
          detail: {
            candidateErrors: candidateErrors,
          },
        });
      }
    }

    // Pick the first valid candidate.
    let selected: Candidate<any> | undefined;
    for (const candidate of response.candidates) {
      if (isValidCandidate(candidate, tools || [])) {
        selected = candidate;
        break;
      }
    }

    if (!selected) {
      throw new Error('No valid candidates found');
    }

    const toolCalls = selected.message.content.filter(
      (part) => !!part.toolRequest
    );
    if (input.returnToolRequests || toolCalls.length === 0) {
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
    input.history = request.messages;
    input.history.push(selected.message);
    input.prompt = toolResponses;
    return await generateAction(input);
  }
);

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
    candidates: options.candidates,
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
