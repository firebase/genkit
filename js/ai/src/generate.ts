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
  GenkitError,
  StreamingCallback,
  defineAction,
  config as genkitConfig,
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
import { DocumentData, DocumentDataSchema } from './document.js';
import { extractJson } from './extract.js';
import {
  CandidateData,
  GenerateRequest,
  GenerateResponseChunkData,
  GenerateResponseData,
  GenerateResponseSchema,
  GenerationCommonConfigSchema,
  GenerationUsage,
  MessageData,
  MessageSchema,
  ModelAction,
  ModelArgument,
  ModelReference,
  Part,
  PartSchema,
  Role,
  ToolDefinition,
  ToolDefinitionSchema,
  ToolRequestPart,
  ToolResponsePart,
} from './model.js';
import {
  ToolAction,
  ToolArgument,
  resolveTools,
  toToolDefinition,
} from './tool.js';

/**
 * Message represents a single role's contribution to a generation. Each message
 * can contain multiple parts (for example text and an image), and each generation
 * can contain multiple messages.
 */
export class Message<T = unknown> implements MessageData {
  role: MessageData['role'];
  content: Part[];

  constructor(message: MessageData) {
    this.role = message.role;
    this.content = message.content;
  }

  /**
   * If a message contains a `data` part, it is returned. Otherwise, the `output()`
   * method extracts the first valid JSON object or array from the text contained in
   * the message and returns it.
   *
   * @returns The structured output contained in the message.
   */
  output(): T {
    return this.data() || extractJson<T>(this.text());
  }

  toolResponseParts(): ToolResponsePart[] {
    const res = this.content.filter((part) => !!part.toolResponse);
    return res as ToolResponsePart[];
  }

  /**
   * Concatenates all `text` parts present in the message with no delimiter.
   * @returns A string of all concatenated text parts.
   */
  text(): string {
    return this.content.map((part) => part.text || '').join('');
  }

  /**
   * Returns the first media part detected in the message. Useful for extracting
   * (for example) an image from a generation expected to create one.
   * @returns The first detected `media` part in the message.
   */
  media(): { url: string; contentType?: string } | null {
    return this.content.find((part) => part.media)?.media || null;
  }

  /**
   * Returns the first detected `data` part of a message.
   * @returns The first `data` part detected in the message (if any).
   */
  data(): T | null {
    return this.content.find((part) => part.data)?.data as T | null;
  }

  /**
   * Returns all tool request found in this message.
   * @returns Array of all tool request found in this message.
   */
  toolRequests(): ToolRequestPart[] {
    return this.content.filter(
      (part) => !!part.toolRequest
    ) as ToolRequestPart[];
  }

  /**
   * Converts the Message to a plain JS object.
   * @returns Plain JS object representing the data contained in the message.
   */
  toJSON(): MessageData {
    return {
      role: this.role,
      content: [...this.content],
    };
  }
}

/**
 * Candidate represents one of several possible generated responses from a generation
 * request. A candidate contains a single generated message along with additional
 * metadata about its generation. A generation request can create multiple candidates.
 */
export class Candidate<O = unknown> implements CandidateData {
  /** The message this candidate generated. */
  message: Message<O>;
  /** The positional index of this candidate in the generation response. */
  index: number;
  /** Usage information about this candidate. */
  usage: GenerationUsage;
  /** The reason generation stopped for this candidate. */
  finishReason: CandidateData['finishReason'];
  /** Additional information about why the candidate stopped generating, if any. */
  finishMessage?: string;
  /** Additional provider-specific information about this candidate. */
  custom: unknown;
  /** The request that led to the generation of this candidate. */
  request?: GenerateRequest;

  constructor(candidate: CandidateData, request?: GenerateRequest) {
    this.message = new Message(candidate.message);
    this.index = candidate.index;
    this.usage = candidate.usage || {};
    this.finishReason = candidate.finishReason;
    this.finishMessage = candidate.finishMessage || '';
    this.custom = candidate.custom;
    this.request = request;
  }

  /**
   * If a candidate's message contains a `data` part, it is returned. Otherwise, the `output()`
   * method extracts the first valid JSON object or array from the text contained in
   * the candidate's message and returns it.
   *
   * @returns The structured output contained in the candidate.
   */
  output(): O | null {
    return this.message.output();
  }

  /**
   * Concatenates all `text` parts present in the candidate's message with no delimiter.
   * @returns A string of all concatenated text parts.
   */
  text(): string {
    return this.message.text();
  }

  /**
   * Returns the first detected media part in the candidate's message. Useful for extracting
   * (for example) an image from a generation expected to create one.
   * @returns The first detected `media` part in the candidate.
   */
  media(): { url: string; contentType?: string } | null {
    return this.message.media();
  }

  /**
   * Returns the first detected `data` part of a candidate's message.
   * @returns The first `data` part detected in the candidate (if any).
   */
  data(): O | null {
    return this.message.data();
  }

  /**
   * Returns all tool request found in this candidate.
   * @returns Array of all tool request found in this candidate.
   */
  toolRequests(): ToolRequestPart[] {
    return this.message.toolRequests();
  }

  /**
   * Determine whether this candidate has output that conforms to a provided schema.
   *
   * @param request A request containing output schema to validate against. If not provided, uses request embedded in candidate.
   * @returns True if output matches request schema or if no request schema is provided.
   */
  hasValidOutput(request?: GenerateRequest): boolean {
    const o = this.output();
    if (!request && !this.request) {
      return true;
    }
    const { valid } = validateSchema(o, {
      jsonSchema: request?.output?.schema || this.request?.output?.schema,
    });
    return valid;
  }

  /**
   * Appends the message generated by this candidate to the messages already
   * present in the generation request. The result of this method can be safely
   * serialized to JSON for persistence in a database.
   * @returns A serializable list of messages compatible with `generate({history})`.
   */
  toHistory(): MessageData[] {
    if (!this.request)
      throw new Error(
        "Can't construct history for candidate without request data."
      );
    return [...this.request?.messages, this.message.toJSON()];
  }

  /**
   * Converts the Candidate to a plain JS object.
   * @returns Plain JS object representing the data contained in the candidate.
   */
  toJSON(): CandidateData {
    return {
      message: this.message.toJSON(),
      index: this.index,
      usage: this.usage,
      finishReason: this.finishReason,
      finishMessage: this.finishMessage,
      custom:
        (!!this.custom && (this.custom as { toJSON?: () => any }).toJSON?.()) ||
        this.custom,
    };
  }
}

/**
 * GenerateResponse is the result from a `generate()` call and contains one or
 * more generated candidate messages.
 */
export class GenerateResponse<O = unknown> implements GenerateResponseData {
  /** The potential generated messages. */
  candidates: Candidate<O>[];
  /** Usage information. */
  usage: GenerationUsage;
  /** Provider-specific response data. */
  custom: unknown;
  /** The request that generated this response. */
  request?: GenerateRequest;

  /**
   * If the selected candidate's message contains a `data` part, it is returned. Otherwise,
   * the `output()` method extracts the first valid JSON object or array from the text
   * contained in the selected candidate's message and returns it.
   *
   * @param index The candidate index from which to extract output. If not provided, finds first candidate that conforms to output schema.
   * @returns The structured output contained in the selected candidate.
   */
  output(index?: number): O | null {
    if (index === undefined) {
      const c = this.candidates.find((c) => c.hasValidOutput(this.request));
      return c?.output() || this.candidates[0]?.output();
    }
    return this.candidates[index!]?.output() || null;
  }

  /**
   * Concatenates all `text` parts present in the candidate's message with no delimiter.
   * @param index The candidate index from which to extract text, defaults to first candidate.
   * @returns A string of all concatenated text parts.
   */
  text(index: number = 0): string {
    return this.candidates[index]?.text() || '';
  }

  /**
   * Returns the first detected media part in the selected candidate's message. Useful for
   * extracting (for example) an image from a generation expected to create one.
   * @param index The candidate index from which to extract media, defaults to first candidate.
   * @returns The first detected `media` part in the candidate.
   */
  media(index: number = 0): { url: string; contentType?: string } | null {
    return this.candidates[index]?.media() || null;
  }

  /**
   * Returns the first detected `data` part of the selected candidate's message.
   * @param index The candidate index from which to extract data, defaults to first candidate.
   * @returns The first `data` part detected in the candidate (if any).
   */
  data(index: number = 0): O | null {
    return this.candidates[index]?.data() || null;
  }

  /**
   * Returns all tool request found in the candidate.
   * @param index The candidate index from which to extract tool requests, defaults to first candidate.
   * @returns Array of all tool request found in the candidate.
   */
  toolRequests(index: number = 0): ToolRequestPart[] {
    return this.candidates[index].toolRequests();
  }

  /**
   * Appends the message generated by the selected candidate to the messages already
   * present in the generation request. The result of this method can be safely
   * serialized to JSON for persistence in a database.
   * @param index The candidate index to utilize during conversion, defaults to first candidate.
   * @returns A serializable list of messages compatible with `generate({history})`.
   */
  toHistory(index: number = 0): MessageData[] {
    return this.candidates[index].toHistory();
  }

  constructor(response: GenerateResponseData, request?: GenerateRequest) {
    this.candidates = (response.candidates || []).map(
      (candidate) => new Candidate(candidate, request)
    );
    this.usage = response.usage || {};
    this.custom = response.custom || {};
    this.request = request;
  }

  toJSON(): GenerateResponseData {
    return {
      candidates: this.candidates.map((candidate) => candidate.toJSON()),
      usage: this.usage,
      custom: (this.custom as { toJSON?: () => any }).toJSON?.() || this.custom,
      request: this.request,
    };
  }
}

export class GenerateResponseChunk<T = unknown>
  implements GenerateResponseChunkData
{
  /** The index of the candidate this chunk corresponds to. */
  index: number;
  /** The content generated in this chunk. */
  content: Part[];
  /** Custom model-specific data for this chunk. */
  custom?: unknown;
  /** Accumulated chunks for partial output extraction. */
  accumulatedChunks?: GenerateResponseChunkData[];

  constructor(
    data: GenerateResponseChunkData,
    accumulatedChunks?: GenerateResponseChunkData[]
  ) {
    this.index = data.index;
    this.content = data.content || [];
    this.custom = data.custom;
    this.accumulatedChunks = accumulatedChunks;
  }

  /**
   * Concatenates all `text` parts present in the chunk with no delimiter.
   * @returns A string of all concatenated text parts.
   */
  text(): string {
    return this.content.map((part) => part.text || '').join('');
  }

  /**
   * Returns the first media part detected in the chunk. Useful for extracting
   * (for example) an image from a generation expected to create one.
   * @returns The first detected `media` part in the chunk.
   */
  media(): { url: string; contentType?: string } | null {
    return this.content.find((part) => part.media)?.media || null;
  }

  /**
   * Returns the first detected `data` part of a chunk.
   * @returns The first `data` part detected in the chunk (if any).
   */
  data(): T | null {
    return this.content.find((part) => part.data)?.data as T | null;
  }

  /**
   * Returns all tool request found in this chunk.
   * @returns Array of all tool request found in this chunk.
   */
  toolRequests(): ToolRequestPart[] {
    return this.content.filter(
      (part) => !!part.toolRequest
    ) as ToolRequestPart[];
  }

  /**
   * Attempts to extract the longest valid JSON substring from the accumulated chunks.
   * @returns The longest valid JSON substring found in the accumulated chunks.
   */
  output(): T | null {
    if (!this.accumulatedChunks) return null;
    const accumulatedText = this.accumulatedChunks
      .map((chunk) => chunk.content.map((part) => part.text || '').join(''))
      .join('');
    return extractJson<T>(accumulatedText, false);
  }

  toJSON(): GenerateResponseChunkData {
    return { index: this.index, content: this.content, custom: this.custom };
  }
}

function getRoleFromPart(part: Part): Role {
  if (part.toolRequest !== undefined) return 'model';
  if (part.toolResponse !== undefined) return 'tool';
  if (part.text !== undefined) return 'user';
  if (part.media !== undefined) return 'user';
  if (part.data !== undefined) return 'user';
  throw new Error('No recognized fields in content');
}

function inferRoleFromParts(parts: Part[]): Role {
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

export async function toGenerateRequest(
  options: GenerateOptions
): Promise<GenerateRequest> {
  const promptMessage: MessageData = { role: 'user', content: [] };
  if (typeof options.prompt === 'string') {
    promptMessage.content.push({ text: options.prompt });
  } else if (Array.isArray(options.prompt)) {
    promptMessage.role = inferRoleFromParts(options.prompt);
    promptMessage.content.push(...options.prompt);
  } else {
    promptMessage.role = inferRoleFromParts([options.prompt]);
    promptMessage.content.push(options.prompt);
  }
  const messages: MessageData[] = [...(options.history || []), promptMessage];
  let tools: Action<any, any>[] | undefined;
  if (options.tools) {
    tools = await resolveTools(options.tools);
  }

  const out = {
    messages,
    candidates: options.candidates,
    config: options.config,
    context: options.context,
    tools: tools?.map((tool) => toToolDefinition(tool)) || [],
    output: {
      format:
        options.output?.format ||
        (options.output?.schema || options.output?.jsonSchema
          ? 'json'
          : 'text'),
      schema: toJsonSchema({
        schema: options.output?.schema,
        jsonSchema: options.output?.jsonSchema,
      }),
    },
  };
  if (!out.output.schema) delete out.output.schema;
  return out;
}

export interface GenerateOptions<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> {
  /** A model name (e.g. `vertexai/gemini-1.0-pro`) or reference. */
  model?: ModelArgument<CustomOptions>;
  /** The prompt for which to generate a response. Can be a string for a simple text prompt or one or more parts for multi-modal prompts. */
  prompt: string | Part | Part[];
  /** Retrieved documents to be used as context for this generation. */
  context?: DocumentData[];
  /** Conversation history for multi-turn prompting when supported by the underlying model. */
  history?: MessageData[];
  /** List of registered tool names or actions to treat as a tool for this generation if supported by the underlying model. */
  tools?: ToolArgument[];
  /** Number of candidate messages to generate. */
  candidates?: number;
  /** Configuration for the generation request. */
  config?: z.infer<CustomOptions>;
  /** Configuration for the desired output of the request. Defaults to the model's default output if unspecified. */
  output?: {
    format?: 'text' | 'json' | 'media';
    schema?: O;
    jsonSchema?: any;
  };
  /** When true, return tool calls for manual processing instead of automatically resolving them. */
  returnToolRequests?: boolean;
  /** When provided, models supporting streaming will call the provided callback with chunks as generation progresses. */
  streamingCallback?: StreamingCallback<GenerateResponseChunk>;
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

async function resolveModel(options: GenerateOptions): Promise<ModelAction> {
  let model = options.model;
  if (!model) {
    if (genkitConfig?.options?.defaultModel) {
      model =
        typeof genkitConfig.options.defaultModel.name === 'string'
          ? genkitConfig.options.defaultModel.name
          : genkitConfig.options.defaultModel.name.name;
      if (
        (!options.config || Object.keys(options.config).length === 0) &&
        genkitConfig.options.defaultModel.config
      ) {
        // use configured global config
        options.config = genkitConfig.options.defaultModel.config;
      }
    } else {
      throw new Error('Unable to resolve model.');
    }
  }
  if (typeof model === 'string') {
    return (await lookupAction(`/model/${model}`)) as ModelAction;
  } else if (model.hasOwnProperty('info')) {
    const ref = model as ModelReference<any>;
    return (await lookupAction(`/model/${ref.name}`)) as ModelAction;
  } else {
    return model as ModelAction;
  }
}

export class NoValidCandidatesError extends GenkitError {
  detail: {
    response: GenerateResponse;
    [otherDetails: string]: any;
  };

  constructor({
    message,
    response,
    detail,
  }: {
    message: string;
    response: GenerateResponse;
    detail?: Record<string, any>;
  }) {
    super({
      status: 'FAILED_PRECONDITION',
      message,
      detail,
    });
    this.detail = { response, ...detail };
  }
}

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

const generateAction = defineAction(
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

/**
 * Generate calls a generative model based on the provided prompt and configuration. If
 * `history` is provided, the generation will include a conversation history in its
 * request. If `tools` are provided, the generate method will automatically resolve
 * tool calls returned from the model unless `returnToolRequests` is set to `true`.
 *
 * See `GenerateOptions` for detailed information about available options.
 *
 * @param options The options for this generation request.
 * @returns The generated response based on the provided parameters.
 */
export async function generate<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
>(
  options:
    | GenerateOptions<O, CustomOptions>
    | PromiseLike<GenerateOptions<O, CustomOptions>>
): Promise<GenerateResponse<z.infer<O>>> {
  const resolvedOptions: GenerateOptions<O, CustomOptions> =
    await Promise.resolve(options);
  const model = await resolveModel(resolvedOptions);
  if (!model) {
    throw new Error(`Model ${JSON.stringify(resolvedOptions.model)} not found`);
  }

  // convert tools to action refs (strings).
  let tools: (string | ToolDefinition)[] | undefined;
  if (resolvedOptions.tools) {
    tools = resolvedOptions.tools.map((t) => {
      if (typeof t === 'string') {
        return `/tool/${t}`;
      } else if ((t as Action).__action) {
        return `/${(t as Action).__action.metadata?.type}/${(t as Action).__action.name}`;
      } else if (t.name) {
        return `/tool/${t.name}`;
      }
      throw new Error(
        `Unable to determine type of of tool: ${JSON.stringify(t)}`
      );
    });
  }

  const params: z.infer<typeof GenerateUtilParamSchema> = {
    model: model.__action.name,
    prompt: resolvedOptions.prompt,
    context: resolvedOptions.context,
    history: resolvedOptions.history,
    tools,
    candidates: resolvedOptions.candidates,
    config: resolvedOptions.config,
    output: resolvedOptions.output && {
      format: resolvedOptions.output.format,
      jsonSchema: resolvedOptions.output.schema
        ? toJsonSchema({
            schema: resolvedOptions.output.schema,
            jsonSchema: resolvedOptions.output.jsonSchema,
          })
        : resolvedOptions.output.jsonSchema,
    },
    returnToolRequests: resolvedOptions.returnToolRequests,
  };

  return await runWithStreamingCallback(
    resolvedOptions.streamingCallback,
    async () => new GenerateResponse<O>(await generateAction(params))
  );
}

export type GenerateStreamOptions<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
> = Omit<GenerateOptions<O, CustomOptions>, 'streamingCallback'>;

export interface GenerateStreamResponse<O extends z.ZodTypeAny = z.ZodTypeAny> {
  stream: () => AsyncIterable<GenerateResponseChunkData>;
  response: () => Promise<GenerateResponse<O>>;
}

function createPromise<T>(): {
  resolve: (result: T) => unknown;
  reject: (err: unknown) => unknown;
  promise: Promise<T>;
} {
  let resolve, reject;
  let promise = new Promise<T>((res, rej) => ([resolve, reject] = [res, rej]));
  return { resolve, reject, promise };
}

export async function generateStream<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
>(
  options:
    | GenerateOptions<O, CustomOptions>
    | PromiseLike<GenerateOptions<O, CustomOptions>>
): Promise<GenerateStreamResponse<O>> {
  let firstChunkSent = false;
  return new Promise<GenerateStreamResponse<O>>(
    (initialResolve, initialReject) => {
      const {
        resolve: finalResolve,
        reject: finalReject,
        promise: finalPromise,
      } = createPromise<GenerateResponse<O>>();

      let provideNextChunk, nextChunk;
      ({ resolve: provideNextChunk, promise: nextChunk } =
        createPromise<GenerateResponseChunkData | null>());
      async function* chunkStream(): AsyncIterable<GenerateResponseChunkData> {
        while (true) {
          const next = await nextChunk;
          if (!next) break;
          yield next;
        }
      }

      try {
        generate<O, CustomOptions>({
          ...options,
          streamingCallback: (chunk) => {
            firstChunkSent = true;
            provideNextChunk(chunk);
            ({ resolve: provideNextChunk, promise: nextChunk } =
              createPromise<GenerateResponseChunkData | null>());
          },
        }).then((result) => {
          provideNextChunk(null);
          finalResolve(result);
        });
      } catch (e) {
        if (!firstChunkSent) {
          initialReject(e);
          return;
        }
        provideNextChunk(null);
        finalReject(e);
      }

      initialResolve({
        response: () => finalPromise,
        stream: chunkStream,
      });
    }
  );
}
