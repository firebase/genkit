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
  runWithStreamingCallback,
  StreamingCallback,
} from '@genkit-ai/common';
import { lookupAction } from '@genkit-ai/common/registry';
import { z } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';
import { extractJson } from './extract';
import {
  CandidateData,
  GenerationConfig,
  GenerationRequest,
  GenerationResponseChunkData,
  GenerationResponseData,
  GenerationUsage,
  MessageData,
  ModelAction,
  ModelArgument,
  ModelReference,
  Part,
  Role,
  ToolResponsePart,
} from './model.js';
import {
  resolveTools,
  ToolAction,
  ToolArgument,
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
  output(): T | null {
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
  request?: GenerationRequest;

  constructor(candidate: CandidateData, request?: GenerationRequest) {
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
      custom: (this.custom as { toJSON?: () => any }).toJSON?.() || this.custom,
    };
  }
}

/**
 * GenerationResponse is the result from a `generate()` call and contains one or
 * more generated candidate messages.
 */
export class GenerationResponse<O = unknown> implements GenerationResponseData {
  /** The potential generated messages. */
  candidates: Candidate<O>[];
  /** Usage information. */
  usage: GenerationUsage;
  /** Provider-specific response data. */
  custom: unknown;
  /** The request that generated this response. */
  request?: GenerationRequest;

  /**
   * If the selected candidate's message contains a `data` part, it is returned. Otherwise,
   * the `output()` method extracts the first valid JSON object or array from the text
   * contained in the selected candidate's message and returns it.
   *
   * @param index The candidate index from which to extract output, defaults to first candidate.
   * @returns The structured output contained in the selected candidate.
   */
  output(index: number = 0): O | null {
    return this.candidates[index]?.output() || null;
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
   * Appends the message generated by the selected candidate to the messages already
   * present in the generation request. The result of this method can be safely
   * serialized to JSON for persistence in a database.
   * @param index The candidate index to utilize during conversion, defaults to first candidate.
   * @returns A serializable list of messages compatible with `generate({history})`.
   */
  toHistory(index: number = 0): MessageData[] {
    return this.candidates[index].toHistory();
  }

  constructor(response: GenerationResponseData, request?: GenerationRequest) {
    this.candidates = (response.candidates || []).map(
      (candidate) => new Candidate(candidate, request)
    );
    this.usage = response.usage || {};
    this.custom = response.custom || {};
    this.request = request;
  }

  toJSON(): GenerationResponseData {
    return {
      candidates: this.candidates.map((candidate) => candidate.toJSON()),
      usage: this.usage,
      custom: (this.custom as { toJSON?: () => any }).toJSON?.() || this.custom,
    };
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

async function toGenerateRequest(
  prompt: GenerateOptions
): Promise<GenerationRequest> {
  const promptMessage: MessageData = { role: 'user', content: [] };
  if (typeof prompt.prompt === 'string') {
    promptMessage.content.push({ text: prompt.prompt });
  } else if (Array.isArray(prompt.prompt)) {
    promptMessage.role = inferRoleFromParts(prompt.prompt);
    promptMessage.content.push(...prompt.prompt);
  } else {
    promptMessage.role = inferRoleFromParts([prompt.prompt]);
    promptMessage.content.push(prompt.prompt);
  }
  const messages: MessageData[] = [...(prompt.history || []), promptMessage];
  let tools: Action<any, any>[] | undefined;
  if (prompt.tools) {
    tools = await resolveTools(prompt.tools);
  }
  return {
    messages,
    candidates: prompt.candidates,
    config: prompt.config,
    tools: tools?.map((tool) => toToolDefinition(tool)) || [],
    output: {
      format:
        prompt.output?.format || (prompt.output?.schema ? 'json' : 'text'),
      schema: prompt.output?.schema
        ? zodToJsonSchema(prompt.output.schema)
        : prompt.output?.jsonSchema,
    },
  };
}

export interface GenerateOptions<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny
> {
  /** A model name (e.g. `vertex-ai/gemini-1.0-pro`) or reference. */
  model: ModelArgument;
  /** The prompt for which to generate a response. Can be a string for a simple text prompt or one or more parts for multi-modal prompts. */
  prompt: string | Part | Part[];
  /** Conversation history for multi-turn prompting when supported by the underlying model. */
  history?: MessageData[];
  /** List of registered tool names or actions to treat as a tool for this generation if supported by the underlying model. */
  tools?: ToolArgument[];
  /** Number of candidate messages to generate. */
  candidates?: number;
  /** Configuration for the generation request. */
  config?: GenerationConfig<z.infer<CustomOptions>>;
  /** Configuration for the desired output of the request. Defaults to the model's default output if unspecified. */
  output?: {
    format?: 'text' | 'json' | 'media';
    schema?: O;
    jsonSchema?: any;
  };
  /** When true, return tool calls for manual processing instead of automatically resolving them. */
  returnToolRequests?: boolean;
  /** When provided, models supporting streaming will call the provided callback with chunks as generation progresses. */
  streamingCallback?: StreamingCallback<GenerationResponseChunkData>;
}

const isValidCandidate = (
  candidate: CandidateData,
  tools: Action<any, any>[]
): boolean => {
  // Check if tool calls are vlaid
  const toolCalls = candidate.message.content.filter(
    (part) => !!part.toolRequest
  );
  let toolCallsValid = true;
  toolCalls.forEach((toolCall) => {
    const input = toolCall.toolRequest?.input;
    const tool = tools?.find(
      (tool) => tool.__action.name === toolCall.toolRequest?.name
    );
    if (!tool) {
      toolCallsValid = false;
      return;
    }
    try {
      tool.__action.inputSchema.parse(input);
    } catch (err) {
      toolCallsValid = false;
      return;
    }
  });
  return toolCallsValid;
};

async function resolveModel(
  model: ModelAction<any> | ModelReference<any> | string
): Promise<ModelAction> {
  if (typeof model === 'string') {
    return (await lookupAction(`/model/${model}`)) as ModelAction;
  } else if (model.hasOwnProperty('info')) {
    const ref = model as ModelReference<any>;
    return (await lookupAction(`/model/${ref.name}`)) as ModelAction;
  } else {
    return model as ModelAction;
  }
}

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
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny
>(
  options:
    | GenerateOptions<O, CustomOptions>
    | PromiseLike<GenerateOptions<O, CustomOptions>>
): Promise<GenerationResponse<z.infer<O>>> {
  const prompt: GenerateOptions<O, CustomOptions> = await Promise.resolve(
    options
  );
  const model = await resolveModel(prompt.model);
  if (!model) {
    throw new Error(`Model ${prompt.model} not found`);
  }

  let tools: ToolAction[] | undefined;
  if (prompt.tools) {
    tools = await resolveTools(prompt.tools);
  }

  const request = await toGenerateRequest(prompt);
  const response = await runWithStreamingCallback(
    prompt.streamingCallback,
    async () =>
      new GenerationResponse<z.infer<O>>(await model(request), request)
  );
  if (prompt.output?.schema) {
    const outputData = response.output();
    prompt.output.schema.parse(outputData);
  }

  // Pick the first valid candidate.
  let selected: Candidate<z.TypeOf<O>> | undefined;
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
  if (prompt.returnToolRequests || toolCalls.length === 0) {
    return response;
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
  prompt.history = request.messages;
  prompt.history.push(selected.message);
  prompt.prompt = toolResponses;
  return await generate(prompt);
}
