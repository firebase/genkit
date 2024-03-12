import { zodToJsonSchema } from 'zod-to-json-schema';
import {
  CandidateData,
  GenerationConfig,
  GenerationRequest,
  GenerationResponseChunkData,
  GenerationResponseData,
  GenerationUsage,
  MessageData,
  ModelAction,
  ModelReference,
  Part,
  ToolDefinition,
  ToolResponsePart,
} from './model.js';
import { extractJson } from './extract';
import { Action } from '@google-genkit/common';
import { z } from 'zod';
import { lookupAction } from '@google-genkit/common/registry';
import { StreamingCallback } from '@google-genkit/common';
import { runWithStreamingCallback } from '@google-genkit/common';
import { action } from '@google-genkit/common';
import * as registry from '@google-genkit/common/registry';
import { setCustomMetadataAttributes } from '@google-genkit/common/tracing';

export class Message<T = unknown> implements MessageData {
  role: MessageData['role'];
  content: Part[];

  constructor(message: MessageData) {
    this.role = message.role;
    this.content = message.content;
  }

  output(): T | null {
    return this.data() || extractJson<T>(this.text());
  }

  text(): string {
    return this.content.map((part) => part.text || '').join('');
  }

  media(): { url: string; contentType?: string } | null {
    return this.content.find((part) => part.media)?.media || null;
  }

  data(): T | null {
    return this.content.find((part) => part.data)?.data as T | null;
  }

  toJSON(): MessageData {
    return {
      role: this.role,
      content: [...this.content],
    };
  }
}

export class Candidate<O = unknown> implements CandidateData {
  message: Message<O>;
  index: number;
  usage: GenerationUsage;
  finishReason: CandidateData['finishReason'];
  finishMessage: string;
  custom: unknown;
  request?: GenerationRequest;

  output(): O | null {
    return this.message.output();
  }

  text(): string {
    return this.message.text();
  }

  media(): { url: string; contentType?: string } | null {
    return this.message.media();
  }

  data(): O | null {
    return this.message.data();
  }

  toHistory(): MessageData[] {
    if (!this.request)
      throw new Error(
        "Can't construct history for candidate without request data."
      );
    return [...this.request?.messages, this.message.toJSON()];
  }

  constructor(candidate: CandidateData, request?: GenerationRequest) {
    this.message = new Message(candidate.message);
    this.index = candidate.index;
    this.usage = candidate.usage || {};
    this.finishReason = candidate.finishReason;
    this.finishMessage = candidate.finishMessage || '';
    this.custom = candidate.custom;
    this.request = request;
  }

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

export class GenerationResponse<O = unknown> implements GenerationResponseData {
  candidates: Candidate<O>[];
  usage: GenerationUsage;
  custom: unknown;
  request?: GenerationRequest;

  output(): O | null {
    return this.candidates[0]?.output() || null;
  }

  text(): string {
    return this.candidates[0]?.text() || '';
  }

  media(): { url: string; contentType?: string } | null {
    return this.candidates[0]?.media() || null;
  }

  data(): O | null {
    return this.candidates[0]?.data() || null;
  }

  toHistory(): MessageData[] {
    return this.candidates[0].toHistory();
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

function toToolDefinition(
  tool: Action<z.ZodTypeAny, z.ZodTypeAny>
): ToolDefinition {
  return {
    name: tool.__action.name,
    description: tool.__action.description || '',
    outputSchema: tool.__action.outputSchema
      ? zodToJsonSchema(tool.__action.outputSchema)
      : {}, // JSON schema matching anything
    inputSchema: zodToJsonSchema(tool.__action.inputSchema!),
  };
}

async function toGenerateRequest(
  prompt: ModelPrompt
): Promise<GenerationRequest> {
  const promptMessage: MessageData = { role: 'user', content: [] };
  if (typeof prompt.prompt === 'string') {
    promptMessage.content.push({ text: prompt.prompt });
  } else if (Array.isArray(prompt.prompt)) {
    promptMessage.content.push(...prompt.prompt);
  } else {
    promptMessage.content.push(prompt.prompt);
  }

  const messages: MessageData[] = [...(prompt.history || []), promptMessage];
  let tools: Action<any, any>[] | undefined;
  if (prompt.tools) {
    tools = await resolveTools(prompt);
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

export interface ModelPrompt<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny
> {
  model: ModelAction<CustomOptions> | ModelReference<CustomOptions> | string;
  prompt: string | Part | Part[];
  history?: MessageData[];
  tools?: (Action<z.ZodTypeAny, z.ZodTypeAny> | string)[];
  candidates?: number;
  config?: GenerationConfig<z.infer<CustomOptions>>;
  output?: {
    format?: 'text' | 'json';
    schema?: O;
    jsonSchema?: any;
  };
  returnToolRequests?: boolean;
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

async function resolveTools<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny
>(prompt: ModelPrompt<O, CustomOptions>) {
  if (!prompt.tools) {
    throw new Error('Tools not provided.');
  }
  const tools: Action<any, any>[] = [];
  for (const tool of prompt.tools) {
    let toolName;
    if (typeof tool === 'string') {
      toolName = tool;
    } else {
      toolName = tool.__action.name;
    }
    const resolvedTool = await lookupAction(`tool/${toolName}`);
    if (!resolvedTool) {
      throw new Error(`Tool ${toolName} not found`);
    }
    tools.push(resolvedTool);
  }
  return tools;
}

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
 *
 */
export async function generate<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny
>(
  options:
    | ModelPrompt<O, CustomOptions>
    | PromiseLike<ModelPrompt<O, CustomOptions>>
): Promise<GenerationResponse<z.infer<O>>> {
  const prompt: ModelPrompt<O, CustomOptions> = await Promise.resolve(options);
  const model = await resolveModel(prompt.model);
  if (!model) {
    throw new Error(`Model ${prompt.model} not found`);
  }

  let tools: Action<any, any>[] | undefined;
  if (prompt.tools) {
    tools = await resolveTools(prompt);
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
  let selected;
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
      const tool = tools?.find(
        (tool) => tool.__action.name === part.toolRequest?.name
      );
      if (!tool) {
        throw Error('Tool not found');
      }
      return {
        name: part.toolRequest.name,
        ref: part.toolRequest.ref,
        output: await tool(part.toolRequest?.input),
      };
    })
  );
  prompt.history?.push({ role: 'tool', content: toolResponses });
  return await generate(prompt);
}

export function tool<I extends z.ZodTypeAny, O extends z.ZodTypeAny>({
  name,
  description,
  input,
  output,
  fn,
}: {
  name: string;
  description: string;
  input: I;
  output: O;
  fn: (input: z.infer<I>) => Promise<z.infer<O>>;
}): Action<I, O> {
  const a = action({ name, description, input, output }, (i) => {
    setCustomMetadataAttributes({ subtype: 'tool' });
    return fn(i);
  });
  registry.registerAction('tool', name, a);
  return a;
}
