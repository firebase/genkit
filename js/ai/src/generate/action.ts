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
  StreamingCallback,
  defineAction,
  stripUndefinedProps,
  type Action,
  type z,
} from '@genkit-ai/core';
import { logger } from '@genkit-ai/core/logging';
import type { Registry } from '@genkit-ai/core/registry';
import { SPAN_TYPE_ATTR, runInNewSpan } from '@genkit-ai/core/tracing';
import {
  injectInstructions,
  resolveFormat,
  resolveInstructions,
} from '../formats/index.js';
import type { Formatter } from '../formats/types.js';
import {
  GenerateResponse,
  GenerationResponseError,
  tagAsPreamble,
} from '../generate.js';
import { GenerateResponseChunk } from '../generate/chunk.js';
import {
  GenerateActionOptionsSchema,
  GenerateResponseChunkSchema,
  GenerateResponseSchema,
  MessageData,
  resolveModel,
  type GenerateActionOptions,
  type GenerateActionOutputConfig,
  type GenerateRequest,
  type GenerateRequestSchema,
  type GenerateResponseChunkData,
  type GenerateResponseData,
  type ModelAction,
  type ModelInfo,
  type ModelMiddleware,
  type ModelRequest,
  type Part,
  type Role,
} from '../model.js';
import {
  findMatchingResource,
  resolveResources,
  type ResourceAction,
} from '../resource.js';
import { resolveTools, toToolDefinition, type ToolAction } from '../tool.js';
import {
  assertValidToolNames,
  resolveResumeOption,
  resolveToolRequests,
} from './resolve-tool-requests.js';

export type GenerateAction = Action<
  typeof GenerateActionOptionsSchema,
  typeof GenerateResponseSchema,
  typeof GenerateResponseChunkSchema
>;

/** Defines (registers) a utilty generate action. */
export function defineGenerateAction(registry: Registry): GenerateAction {
  return defineAction(
    registry,
    {
      actionType: 'util',
      name: 'generate',
      inputSchema: GenerateActionOptionsSchema,
      outputSchema: GenerateResponseSchema,
      streamSchema: GenerateResponseChunkSchema,
    },
    async (request, { streamingRequested, sendChunk }) => {
      const generateFn = (
        sendChunk?: StreamingCallback<GenerateResponseChunk>
      ) =>
        generate(registry, {
          rawRequest: request,
          currentTurn: 0,
          messageIndex: 0,
          // Generate util action does not support middleware. Maybe when we add named/registered middleware....
          middleware: [],
          streamingCallback: sendChunk,
        });
      return streamingRequested
        ? generateFn((c: GenerateResponseChunk) =>
            sendChunk(c.toJSON ? c.toJSON() : c)
          )
        : generateFn();
    }
  );
}

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
    abortSignal?: AbortSignal;
    streamingCallback?: StreamingCallback<GenerateResponseChunk>;
  }
): Promise<GenerateResponseData> {
  const currentTurn = options.currentTurn ?? 0;
  const messageIndex = options.messageIndex ?? 0;
  // do tracing
  return await runInNewSpan(
    registry,
    {
      metadata: {
        name: options.rawRequest.stepName || 'generate',
      },
      labels: {
        [SPAN_TYPE_ATTR]: 'util',
      },
    },
    async (metadata) => {
      metadata.name = options.rawRequest.stepName || 'generate';
      metadata.input = options.rawRequest;
      const output = await generate(registry, {
        rawRequest: options.rawRequest,
        middleware: options.middleware,
        currentTurn,
        messageIndex,
        abortSignal: options.abortSignal,
        streamingCallback: options.streamingCallback,
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
  const [model, tools, resources, format] = await Promise.all([
    resolveModel(registry, request.model, { warnDeprecated: true }).then(
      (r) => r.modelAction
    ),
    resolveTools(registry, request.tools),
    resolveResources(registry, request.resources),
    resolveFormat(registry, request.output),
  ]);
  return { model, tools, resources, format };
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
    if (
      shouldInjectFormatInstructions(resolvedFormat.config, rawRequest?.output)
    ) {
      outRequest.messages = injectInstructions(
        outRequest.messages,
        instructions
      );
    }
    outRequest.output = {
      // use output config from the format
      ...resolvedFormat.config,
      // if anything is set explicitly, use that
      ...outRequest.output,
    };
  }

  return outRequest;
}

export function shouldInjectFormatInstructions(
  formatConfig?: Formatter['config'],
  rawRequestConfig?: z.infer<typeof GenerateActionOutputConfig>
) {
  return (
    formatConfig?.defaultInstructions !== false ||
    rawRequestConfig?.instructions
  );
}

function applyTransferPreamble(
  rawRequest: GenerateActionOptions,
  transferPreamble?: GenerateActionOptions
): GenerateActionOptions {
  if (!transferPreamble) {
    return rawRequest;
  }

  // if the transfer preamble has a model, use it for the next request
  if (transferPreamble?.model) {
    rawRequest.model = transferPreamble.model;
  }

  return stripUndefinedProps({
    ...rawRequest,
    messages: [
      ...tagAsPreamble(transferPreamble.messages!)!,
      ...rawRequest.messages.filter((m) => !m.metadata?.preamble),
    ],
    toolChoice: transferPreamble.toolChoice || rawRequest.toolChoice,
    tools: transferPreamble.tools || rawRequest.tools,
    config: transferPreamble.config || rawRequest.config,
  });
}

async function generate(
  registry: Registry,
  {
    rawRequest,
    middleware,
    currentTurn,
    messageIndex,
    abortSignal,
    streamingCallback,
  }: {
    rawRequest: GenerateActionOptions;
    middleware: ModelMiddleware[] | undefined;
    currentTurn: number;
    messageIndex: number;
    abortSignal?: AbortSignal;
    streamingCallback?: StreamingCallback<GenerateResponseChunk>;
  }
): Promise<GenerateResponseData> {
  const { model, tools, resources, format } = await resolveParameters(
    registry,
    rawRequest
  );
  rawRequest = applyFormat(rawRequest, format);
  rawRequest = await applyResources(registry, rawRequest, resources);

  // check to make sure we don't have overlapping tool names *before* generation
  await assertValidToolNames(tools);

  const {
    revisedRequest,
    interruptedResponse,
    toolMessage: resumedToolMessage,
  } = await resolveResumeOption(registry, rawRequest);
  // NOTE: in the future we should make it possible to interrupt a restart, but
  // at the moment it's too complicated because it's not clear how to return a
  // response that amends history but doesn't generate a new message, so we throw
  if (interruptedResponse) {
    throw new GenkitError({
      status: 'FAILED_PRECONDITION',
      message:
        'One or more tools triggered an interrupt during a restarted execution.',
      detail: { message: interruptedResponse.message },
    });
  }
  rawRequest = revisedRequest!;

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
    if (role !== chunkRole && previousChunks.length) messageIndex++;
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

  // if resolving the 'resume' option above generated a tool message, stream it.
  if (resumedToolMessage && streamingCallback) {
    streamingCallback(makeChunk('tool', resumedToolMessage));
  }

  var response: GenerateResponse;
  const dispatch = async (
    index: number,
    req: z.infer<typeof GenerateRequestSchema>
  ) => {
    if (!middleware || index === middleware.length) {
      // end of the chain, call the original model action
      return await model(req, {
        abortSignal,
        onChunk:
          streamingCallback &&
          (((chunk: GenerateResponseChunkData) =>
            streamingCallback &&
            streamingCallback(makeChunk('model', chunk))) as any),
      });
    }

    const currentMiddleware = middleware[index];
    return currentMiddleware(req, async (modifiedReq) =>
      dispatch(index + 1, modifiedReq || req)
    );
  };

  const modelResponse = await dispatch(0, request);

  if (model.__action.actionType === 'background-model') {
    response = new GenerateResponse(
      { operation: modelResponse },
      {
        request,
        parser: format?.handler(request.output?.schema).parseMessage,
      }
    );
  } else {
    response = new GenerateResponse(modelResponse, {
      request,
      parser: format?.handler(request.output?.schema).parseMessage,
    });
  }
  if (model.__action.actionType === 'background-model') {
    return response.toJSON();
  }

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

    messages: [...rawRequest.messages, generatedMessage.toJSON(), toolMessage!],
  };

  nextRequest = applyTransferPreamble(nextRequest, transferPreamble);

  // then recursively call for another loop
  return await generateHelper(registry, {
    rawRequest: nextRequest,
    middleware: middleware,
    currentTurn: currentTurn + 1,
    messageIndex: messageIndex + 1,
    streamingCallback,
    abortSignal,
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
    output: stripUndefinedProps({
      constrained: options.output?.constrained,
      contentType: options.output?.contentType,
      format: options.output?.format,
      schema: options.output?.jsonSchema,
    }),
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

async function applyResources(
  registry: Registry,
  rawRequest: GenerateActionOptions,
  resources: ResourceAction[]
): Promise<GenerateActionOptions> {
  // quick check, if no resources bail.
  if (!rawRequest.messages.find((m) => !!m.content.find((c) => c.resource))) {
    return rawRequest;
  }

  const updatedMessages = [] as MessageData[];
  for (const m of rawRequest.messages) {
    if (!m.content.find((c) => c.resource)) {
      updatedMessages.push(m);
      continue;
    }
    const updatedContent = [] as Part[];
    for (const p of m.content) {
      if (!p.resource) {
        updatedContent.push(p);
        continue;
      }

      const resource = await findMatchingResource(
        registry,
        resources,
        p.resource
      );
      if (!resource) {
        throw new GenkitError({
          status: 'NOT_FOUND',
          message: `failed to find matching resource for ${p.resource.uri}`,
        });
      }
      const resourceParts = await resource(p.resource);
      updatedContent.push(...resourceParts.content);
    }

    updatedMessages.push({
      ...m,
      content: updatedContent,
    });
  }

  return {
    ...rawRequest,
    messages: updatedMessages,
  };
}
