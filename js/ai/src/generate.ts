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
  runWithStreamingCallback,
  StreamingCallback,
  z,
} from '@genkit-ai/core';
import { lookupAction } from '@genkit-ai/core/registry';
import { parseSchema, toJsonSchema } from '@genkit-ai/core/schema';
import { StatusName } from '../../core/lib/statusTypes.js';
import { DocumentData } from './document.js';
import { extractJson } from './extract.js';
import {
  generateHelper,
  GenerateUtilParamSchema,
  inferRoleFromParts,
} from './generateAction.js';
import {
  GenerateRequest,
  GenerateResponseChunkData,
  GenerateResponseData,
  GenerationCommonConfigSchema,
  GenerationUsage,
  MessageData,
  ModelAction,
  ModelArgument,
  ModelMiddleware,
  ModelReference,
  ModelResponseData,
  Part,
  ToolDefinition,
  ToolRequestPart,
  ToolResponsePart,
} from './model.js';
import { resolveTools, ToolArgument, toToolDefinition } from './tool.js';

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
 * GenerateResponse is the result from a `generate()` call and contains one or
 * more generated candidate messages.
 */
export class GenerateResponse<O = unknown> implements ModelResponseData {
  /** The generated message. */
  message?: Message<O>;
  /** The reason generation stopped for this request. */
  finishReason: ModelResponseData['finishReason'];
  /** Additional information about why the model stopped generating, if any. */
  finishMessage?: string;
  /** Usage information. */
  usage: GenerationUsage;
  /** Provider-specific response data. */
  custom: unknown;
  /** The request that generated this response. */
  request?: GenerateRequest;

  constructor(response: GenerateResponseData, request?: GenerateRequest) {
    // Check for candidates in addition to message for backwards compatibility.
    const generatedMessage =
      response.message || response.candidates?.[0]?.message;
    if (generatedMessage) {
      this.message = new Message(generatedMessage);
    }
    this.finishReason =
      response.finishReason || response.candidates?.[0]?.finishReason!;
    this.finishMessage =
      response.finishMessage || response.candidates?.[0]?.finishMessage;
    this.usage = response.usage || {};
    this.custom = response.custom || {};
    this.request = request;
  }

  private get assertMessage(): Message<O> {
    if (!this.message)
      throw new Error(
        'Operation could not be completed because the response does not contain a generated message.'
      );
    return this.message;
  }

  /**
   * Throws an error if the response does not contain valid output.
   */
  assertValid(request?: GenerateRequest): void {
    if (this.finishReason === 'blocked') {
      throw new GenerationBlockedError(
        this,
        `Generation blocked${this.finishMessage ? `: ${this.finishMessage}` : '.'}`
      );
    }

    if (!this.message) {
      throw new GenerationResponseError(
        this,
        `Model did not generate a message. Finish reason: '${this.finishReason}': ${this.finishMessage}`
      );
    }

    if (request?.output?.schema || this.request?.output?.schema) {
      const o = this.output();
      parseSchema(o, {
        jsonSchema: request?.output?.schema || this.request?.output?.schema,
      });
    }
  }

  isValid(request?: GenerateRequest): boolean {
    try {
      this.assertValid(request);
      return true;
    } catch (e) {
      return false;
    }
  }

  /**
   * If the selected candidate's message contains a `data` part, it is returned. Otherwise,
   * the `output()` method extracts the first valid JSON object or array from the text
   * contained in the selected candidate's message and returns it.
   *
   * @param index The candidate index from which to extract output. If not provided, finds first candidate that conforms to output schema.
   * @returns The structured output contained in the selected candidate.
   */
  output(): O | null {
    return this.message?.output() || null;
  }

  /**
   * Concatenates all `text` parts present in the candidate's message with no delimiter.
   * @param index The candidate index from which to extract text, defaults to first candidate.
   * @returns A string of all concatenated text parts.
   */
  text(): string {
    return this.message?.text() || '';
  }

  /**
   * Returns the first detected media part in the selected candidate's message. Useful for
   * extracting (for example) an image from a generation expected to create one.
   * @param index The candidate index from which to extract media, defaults to first candidate.
   * @returns The first detected `media` part in the candidate.
   */
  media(): { url: string; contentType?: string } | null {
    return this.message?.media() || null;
  }

  /**
   * Returns the first detected `data` part of the selected candidate's message.
   * @param index The candidate index from which to extract data, defaults to first candidate.
   * @returns The first `data` part detected in the candidate (if any).
   */
  data(): O | null {
    return this.message?.data() || null;
  }

  /**
   * Returns all tool request found in the candidate.
   * @param index The candidate index from which to extract tool requests, defaults to first candidate.
   * @returns Array of all tool request found in the candidate.
   */
  toolRequests(): ToolRequestPart[] {
    return this.message?.toolRequests() || [];
  }

  /**
   * Appends the message generated by the selected candidate to the messages already
   * present in the generation request. The result of this method can be safely
   * serialized to JSON for persistence in a database.
   * @param index The candidate index to utilize during conversion, defaults to first candidate.
   * @returns A serializable list of messages compatible with `generate({history})`.
   */
  toHistory(): MessageData[] {
    if (!this.request)
      throw new Error(
        "Can't construct history for response without request reference."
      );
    if (!this.message)
      throw new Error(
        "Can't construct history for response without generated message."
      );
    return [...this.request?.messages, this.message.toJSON()];
  }

  toJSON(): ModelResponseData {
    const out = {
      message: this.message?.toJSON(),
      finishReason: this.finishReason,
      finishMessage: this.finishMessage,
      usage: this.usage,
      custom: (this.custom as { toJSON?: () => any }).toJSON?.() || this.custom,
      request: this.request,
    };
    if (!out.finishMessage) delete out.finishMessage;
    if (!out.request) delete out.request;
    return out;
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
  /** Middleware to be used with this model call. */
  use?: ModelMiddleware[];
}

async function resolveModel(options: GenerateOptions): Promise<ModelAction> {
  let model = options.model;
  if (!model) {
    // TODO: Fix this...
    // if (genkitConfig?.options?.defaultModel) {
    //   model =
    //     typeof genkitConfig.options.defaultModel.name === 'string'
    //       ? genkitConfig.options.defaultModel.name
    //       : genkitConfig.options.defaultModel.name.name;
    //   if (
    //     (!options.config || Object.keys(options.config).length === 0) &&
    //     genkitConfig.options.defaultModel.config
    //   ) {
    //     // use configured global config
    //     options.config = genkitConfig.options.defaultModel.config;
    //   }
    // } else {
    throw new Error('Unable to resolve model.');
    // }
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

export class GenerationResponseError extends GenkitError {
  detail: {
    response: GenerateResponse;
    [otherDetails: string]: any;
  };

  constructor(
    response: GenerateResponse,
    message: string,
    status?: StatusName,
    detail?: Record<string, any>
  ) {
    super({
      status: status || 'FAILED_PRECONDITION',
      message,
    });
    this.detail = { response, ...detail };
  }
}
/** A GenerationBlockedError is thrown when a generation is blocked. */
export class GenerationBlockedError extends GenerationResponseError {}

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
    async () =>
      new GenerateResponse<O>(
        await generateHelper(params, resolvedOptions.use),
        await toGenerateRequest(resolvedOptions)
      )
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
