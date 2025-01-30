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
  ActionContext,
  GenkitError,
  StreamingCallback,
  runWithContext,
  runWithStreamingCallback,
  sentinelNoopStreamingCallback,
  stripUndefinedProps,
  z,
} from '@genkit-ai/core';
import { Channel } from '@genkit-ai/core/async';
import { Registry } from '@genkit-ai/core/registry';
import { toJsonSchema } from '@genkit-ai/core/schema';
import { DocumentData } from './document.js';
import {
  injectInstructions,
  resolveFormat,
  resolveInstructions,
} from './formats/index.js';
import { generateHelper } from './generate/action.js';
import { GenerateResponseChunk } from './generate/chunk.js';
import { GenerateResponse } from './generate/response.js';
import { Message } from './message.js';
import {
  GenerateActionOptions,
  GenerateRequest,
  GenerationCommonConfigSchema,
  MessageData,
  ModelArgument,
  ModelMiddleware,
  Part,
  ToolResponsePart,
  resolveModel,
} from './model.js';
import { ExecutablePrompt } from './prompt.js';
import { ToolArgument, resolveTools, toToolDefinition } from './tool.js';
export { GenerateResponse, GenerateResponseChunk };

/** Specifies how tools should be called by the model. */
export type ToolChoice = 'auto' | 'required' | 'none';

export interface OutputOptions<O extends z.ZodTypeAny = z.ZodTypeAny> {
  format?: string;
  contentType?: string;
  instructions?: boolean | string;
  schema?: O;
  jsonSchema?: any;
}

/** ResumeOptions configure how to resume generation after an interrupt. */
export interface ResumeOptions {
  /**
   * reply should contain a single or list of `toolResponse` parts corresponding
   * to interrupt `toolRequest` parts from the most recent model message. Each
   * entry must have a matching `name` and `ref` (if supplied) for its `toolRequest`
   * counterpart.
   *
   * Tools have a `.reply` helper method to construct a reply ToolResponse and validate
   * the data against its schema. Call `myTool.reply(interruptToolRequest, yourReplyData)`.
   */
  reply: ToolResponsePart | ToolResponsePart[];
  /** Additional metadata to annotate the created tool message with in the "resume" key. */
  metadata?: Record<string, any>;
}

export interface GenerateOptions<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> {
  /** A model name (e.g. `vertexai/gemini-1.0-pro`) or reference. */
  model?: ModelArgument<CustomOptions>;
  /** The system prompt to be included in the generate request. Can be a string for a simple text prompt or one or more parts for multi-modal prompts (subject to model support). */
  system?: string | Part | Part[];
  /** The prompt for which to generate a response. Can be a string for a simple text prompt or one or more parts for multi-modal prompts. */
  prompt?: string | Part | Part[];
  /** Retrieved documents to be used as context for this generation. */
  docs?: DocumentData[];
  /** Conversation messages (history) for multi-turn prompting when supported by the underlying model. */
  messages?: (MessageData & { content: Part[] | string | (string | Part)[] })[];
  /** List of registered tool names or actions to treat as a tool for this generation if supported by the underlying model. */
  tools?: ToolArgument[];
  /** Specifies how tools should be called by the model.  */
  toolChoice?: ToolChoice;
  /** Configuration for the generation request. */
  config?: z.infer<CustomOptions>;
  /** Configuration for the desired output of the request. Defaults to the model's default output if unspecified. */
  output?: OutputOptions<O>;
  /**
   * resume provides convenient capabilities for continuing generation
   * after an interrupt is triggered. Example:
   *
   * ```ts
   * const myInterrupt = ai.defineInterrupt({...});
   *
   * const response = await ai.generate({
   *   tools: [myInterrupt],
   *   prompt: "Call myInterrupt",
   * });
   *
   * const interrupt = response.interrupts[0];
   *
   * const resumedResponse = await ai.generate({
   *   messages: response.messages,
   *   resume: myInterrupt.reply(interrupt, {note: "this is the reply data"}),
   * });
   * ```
   */
  resume?: ResumeOptions;
  /** When true, return tool calls for manual processing instead of automatically resolving them. */
  returnToolRequests?: boolean;
  /** Maximum number of tool call iterations that can be performed in a single generate call (default 5). */
  maxTurns?: number;
  /** When provided, models supporting streaming will call the provided callback with chunks as generation progresses. */
  onChunk?: StreamingCallback<GenerateResponseChunk>;
  /**
   * When provided, models supporting streaming will call the provided callback with chunks as generation progresses.
   *
   * @deprecated use {@link onChunk} instead.
   */
  streamingCallback?: StreamingCallback<GenerateResponseChunk>;
  /** Middleware to be used with this model call. */
  use?: ModelMiddleware[];
  /** Additional context (data, like e.g. auth) to be passed down to tools, prompts and other sub actions. */
  context?: ActionContext;
}

/** Amends message history to handle `resume` arguments. Returns the amended history. */
async function applyResumeOption(
  options: GenerateOptions,
  messages: MessageData[]
): Promise<MessageData[]> {
  if (!options.resume) return messages;
  if (
    messages.at(-1)?.role !== 'model' ||
    !messages
      .at(-1)
      ?.content.find((p) => p.toolRequest && p.metadata?.interrupt)
  ) {
    throw new GenkitError({
      status: 'FAILED_PRECONDITION',
      message: `Cannot 'resume' generation unless the previous message is a model message with at least one interrupt.`,
    });
  }
  const lastModelMessage = messages.at(-1)!;
  const toolRequests = lastModelMessage.content.filter((p) => !!p.toolRequest);

  const pendingResponses: ToolResponsePart[] = toolRequests
    .filter((t) => !!t.metadata?.pendingOutput)
    .map((t) =>
      stripUndefinedProps({
        toolResponse: {
          name: t.toolRequest!.name,
          ref: t.toolRequest!.ref,
          output: t.metadata!.pendingOutput,
        },
        metadata: { source: 'pending' },
      })
    ) as ToolResponsePart[];

  const reply = Array.isArray(options.resume.reply)
    ? options.resume.reply
    : [options.resume.reply];

  const message: MessageData = {
    role: 'tool',
    content: [...pendingResponses, ...reply],
    metadata: {
      resume: options.resume.metadata || true,
    },
  };
  return [...messages, message];
}

export async function toGenerateRequest(
  registry: Registry,
  options: GenerateOptions
): Promise<GenerateRequest> {
  let messages: MessageData[] = [];
  if (options.system) {
    messages.push({
      role: 'system',
      content: Message.parseContent(options.system),
    });
  }
  if (options.messages) {
    messages.push(...options.messages.map((m) => Message.parseData(m)));
  }
  // resuming from interrupts occurs after message history but before user prompt
  messages = await applyResumeOption(options, messages);
  if (options.prompt) {
    messages.push({
      role: 'user',
      content: Message.parseContent(options.prompt),
    });
  }
  if (messages.length === 0) {
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: 'at least one message is required in generate request',
    });
  }
  let tools: Action<any, any>[] | undefined;
  if (options.tools) {
    tools = await resolveTools(registry, options.tools);
  }

  const resolvedSchema = toJsonSchema({
    schema: options.output?.schema,
    jsonSchema: options.output?.jsonSchema,
  });

  const resolvedFormat = await resolveFormat(registry, options.output);
  const instructions = resolveInstructions(
    resolvedFormat,
    resolvedSchema,
    options?.output?.instructions
  );

  const out = {
    messages: injectInstructions(messages, instructions),
    config: options.config,
    docs: options.docs,
    tools: tools?.map(toToolDefinition) || [],
    output: {
      ...(resolvedFormat?.config || {}),
      schema: resolvedSchema,
    },
  };
  if (!out.output.schema) delete out.output.schema;
  return out;
}

export class GenerationResponseError extends GenkitError {
  detail: {
    response: GenerateResponse;
    [otherDetails: string]: any;
  };

  constructor(
    response: GenerateResponse<any>,
    message: string,
    status?: GenkitError['status'],
    detail?: Record<string, any>
  ) {
    super({
      status: status || 'FAILED_PRECONDITION',
      message,
    });
    this.detail = { response, ...detail };
  }
}

async function toolsToActionRefs(
  registry: Registry,
  toolOpt?: ToolArgument[]
): Promise<string[] | undefined> {
  if (!toolOpt) return;

  let tools: string[] = [];

  for (const t of toolOpt) {
    if (typeof t === 'string') {
      tools.push(await resolveFullToolName(registry, t));
    } else if ((t as Action).__action) {
      tools.push(
        `/${(t as Action).__action.metadata?.type}/${(t as Action).__action.name}`
      );
    } else if (typeof (t as ExecutablePrompt).asTool === 'function') {
      const promptToolAction = await (t as ExecutablePrompt).asTool();
      tools.push(`/prompt/${promptToolAction.__action.name}`);
    } else if (t.name) {
      tools.push(await resolveFullToolName(registry, t.name));
    } else {
      throw new Error(`Unable to determine type of tool: ${JSON.stringify(t)}`);
    }
  }
  return tools;
}

function messagesFromOptions(options: GenerateOptions): MessageData[] {
  const messages: MessageData[] = [];
  if (options.system) {
    messages.push({
      role: 'system',
      content: Message.parseContent(options.system),
    });
  }
  if (options.messages) {
    messages.push(...options.messages);
  }
  if (options.prompt) {
    messages.push({
      role: 'user',
      content: Message.parseContent(options.prompt),
    });
  }
  if (messages.length === 0) {
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: 'at least one message is required in generate request',
    });
  }
  return messages;
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
  registry: Registry,
  options:
    | GenerateOptions<O, CustomOptions>
    | PromiseLike<GenerateOptions<O, CustomOptions>>
): Promise<GenerateResponse<z.infer<O>>> {
  const resolvedOptions: GenerateOptions<O, CustomOptions> = {
    ...(await Promise.resolve(options)),
  };
  const resolvedModel = await resolveModel(registry, resolvedOptions.model);

  const tools = await toolsToActionRefs(registry, resolvedOptions.tools);

  const messages: MessageData[] = messagesFromOptions(resolvedOptions);

  const resolvedSchema = toJsonSchema({
    schema: resolvedOptions.output?.schema,
    jsonSchema: resolvedOptions.output?.jsonSchema,
  });

  // If is schema is set but format is not explicitly set, default to `json` format.
  if (
    (resolvedOptions.output?.schema || resolvedOptions.output?.jsonSchema) &&
    !resolvedOptions.output?.format
  ) {
    resolvedOptions.output.format = 'json';
  }
  const resolvedFormat = await resolveFormat(registry, resolvedOptions.output);
  const instructions = resolveInstructions(
    resolvedFormat,
    resolvedSchema,
    resolvedOptions?.output?.instructions
  );

  const params: GenerateActionOptions = {
    model: resolvedModel.modelAction.__action.name,
    docs: resolvedOptions.docs,
    messages: injectInstructions(messages, instructions),
    tools,
    toolChoice: resolvedOptions.toolChoice,
    config: {
      version: resolvedModel.version,
      ...stripUndefinedOptions(resolvedModel.config),
      ...stripUndefinedOptions(resolvedOptions.config),
    },
    output: resolvedOptions.output && {
      format: resolvedOptions.output.format,
      jsonSchema: resolvedSchema,
    },
    returnToolRequests: resolvedOptions.returnToolRequests,
    maxTurns: resolvedOptions.maxTurns,
  };

  return await runWithStreamingCallback(
    registry,
    stripNoop(resolvedOptions.onChunk ?? resolvedOptions.streamingCallback),
    async () => {
      const response = await runWithContext(
        registry,
        resolvedOptions.context,
        () =>
          generateHelper(registry, {
            rawRequest: params,
            middleware: resolvedOptions.use,
          })
      );
      const request = await toGenerateRequest(registry, {
        ...resolvedOptions,
        tools,
      });
      return new GenerateResponse<O>(response, {
        request: response.request ?? request,
        parser: resolvedFormat?.handler(request.output?.schema).parseMessage,
      });
    }
  );
}

/**
 * Check if the callback is a noop callback and return undefined -- downstream models
 * expect undefined if no streaming is requested.
 */
function stripNoop<T>(
  callback: StreamingCallback<T> | undefined
): StreamingCallback<T> | undefined {
  if (callback === sentinelNoopStreamingCallback) {
    return undefined;
  }
  return callback;
}

function stripUndefinedOptions(input?: any): any {
  if (!input) return input;
  const copy = { ...input };
  Object.keys(input).forEach((key) => {
    if (copy[key] === undefined) {
      delete copy[key];
    }
  });
  return copy;
}

async function resolveFullToolName(
  registry: Registry,
  name: string
): Promise<string> {
  if (await registry.lookupAction(`/tool/${name}`)) {
    return `/tool/${name}`;
  } else if (await registry.lookupAction(`/prompt/${name}`)) {
    return `/prompt/${name}`;
  } else {
    throw new Error(`Unable to determine type of of tool: ${name}`);
  }
}

export type GenerateStreamOptions<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
> = Omit<GenerateOptions<O, CustomOptions>, 'streamingCallback'>;

export interface GenerateStreamResponse<O extends z.ZodTypeAny = z.ZodTypeAny> {
  get stream(): AsyncIterable<GenerateResponseChunk>;
  get response(): Promise<GenerateResponse<O>>;
}

export function generateStream<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = typeof GenerationCommonConfigSchema,
>(
  registry: Registry,
  options:
    | GenerateOptions<O, CustomOptions>
    | PromiseLike<GenerateOptions<O, CustomOptions>>
): GenerateStreamResponse<O> {
  let channel = new Channel<GenerateResponseChunk>();

  const generated = Promise.resolve(options).then((resolvedOptions) =>
    generate<O, CustomOptions>(registry, {
      ...resolvedOptions,
      onChunk: (chunk) => channel.send(chunk),
    })
  );
  generated.then(
    () => channel.close(),
    (err) => channel.error(err)
  );

  return {
    response: generated,
    stream: channel,
  };
}

export function tagAsPreamble(msgs?: MessageData[]): MessageData[] | undefined {
  if (!msgs) {
    return undefined;
  }
  return msgs.map((m) => ({
    ...m,
    metadata: {
      ...m.metadata,
      preamble: true,
    },
  }));
}
