import zodToJsonSchema from 'zod-to-json-schema';
import {
  CandidateData,
  GenerationConfig,
  GenerationRequest,
  GenerationResponseData,
  GenerationUsage,
  MessageData,
  ModelAction,
  ModelReference,
  Part,
  ToolDefinition,
  ToolResponsePart,
} from './model';
import { extractJson } from './extract';
import { Action } from '@google-genkit/common';
import { z } from 'zod';
import { lookupAction } from '@google-genkit/common/registry';

export class Message<T = unknown> implements MessageData {
  role: MessageData['role'];
  content: Part[];

  constructor(message: MessageData) {
    this.role = message.role;
    this.content = message.content;
  }

  output(): T | null {
    return extractJson<T>(this.text());
  }

  text(): string {
    return this.content.map((part) => part.text || '').join('');
  }
}

export class Candidate<O = unknown> implements CandidateData {
  message: Message<O>;
  index: number;
  usage: GenerationUsage;
  finishReason: CandidateData['finishReason'];
  finishMessage: string;
  custom: unknown;

  output(): O | null {
    return this.message.output();
  }

  text(): string {
    return this.message.text();
  }

  constructor(candidate: CandidateData) {
    this.message = new Message(candidate.message);
    this.index = candidate.index;
    this.usage = candidate.usage || {};
    this.finishReason = candidate.finishReason;
    this.finishMessage = candidate.finishMessage || '';
    this.custom = candidate.custom;
  }
}

export class GenerationResponse<O = unknown> implements GenerationResponseData {
  candidates: Candidate<O>[];
  usage: GenerationUsage;
  custom: unknown;

  output(): O | null {
    return this.candidates[0]?.output() || null;
  }

  text(): string {
    return this.candidates[0]?.text() || '';
  }

  constructor(response: GenerationResponseData) {
    this.candidates = (response.candidates || []).map(
      (candidate) => new Candidate(candidate)
    );
    this.usage = response.usage || {};
    this.custom = response.custom || {};
  }
}

function toToolDefinition(
  tool: Action<z.ZodTypeAny, z.ZodTypeAny>
): ToolDefinition {
  return {
    name: tool.__action.name,
    outputSchema: tool.__action.outputSchema
      ? zodToJsonSchema(tool.__action.outputSchema!)
      : {}, // JSON schema matching anything
    inputSchema: zodToJsonSchema(tool.__action.inputSchema!),
  };
}

function toGenerateRequest(prompt: ModelPrompt): GenerationRequest {
  const promptMessage: MessageData = { role: 'user', content: [] };
  if (typeof prompt.prompt === 'string') {
    promptMessage.content.push({ text: prompt.prompt });
  } else if (Array.isArray(prompt.prompt)) {
    promptMessage.content.push(...prompt.prompt);
  } else {
    promptMessage.content.push(prompt.prompt);
  }

  if (prompt.output?.schema) {
    const outputSchema = zodToJsonSchema(prompt.output.schema);
    promptMessage.content.push({
      text: `
    
Output should be JSON formatted and conform to the following schema:

\`\`\`
${JSON.stringify(outputSchema)}
\`\`\``,
    });
  }

  const messages: MessageData[] = [...(prompt.history || []), promptMessage];

  return {
    messages,
    candidates: prompt.candidates,
    config: prompt.config,
    tools: prompt.tools?.map((tool) => toToolDefinition(tool)) || [],
    output: {
      format:
        prompt.output?.format || (prompt.output?.schema ? 'json' : 'text'),
      schema: prompt.output?.schema
        ? zodToJsonSchema(prompt.output.schema)
        : prompt.output?.jsonSchema
        ? prompt.output.jsonSchema
        : undefined,
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
  tools?: Action<z.ZodTypeAny, z.ZodTypeAny>[];
  candidates?: number;
  config?: GenerationConfig<z.infer<CustomOptions>>;
  output?: {
    format?: 'text' | 'json';
    schema?: O;
    jsonSchema?: any;
  };
  returnToolRequests?: boolean;
}


const isValidCandidate = (candidate: CandidateData, tools: Action<any, any>[]): boolean => {
  // Check if tool calls are vlaid
  const toolCalls = candidate.message.content.filter(part => !!part.toolRequest);
  let toolCallsValid = true;
  toolCalls.forEach(toolCall => {
    const input = toolCall.toolRequest?.input;
    const tool = tools?.find(tool => tool.__action.name === toolCall.toolRequest?.name);
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
  })
  return toolCallsValid;
}

export async function generate<
  O extends z.ZodTypeAny = z.ZodTypeAny,
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny
>(
  prompt: ModelPrompt<O, CustomOptions>,
): Promise<GenerationResponse<z.infer<O>>> {
  let model: ModelAction<CustomOptions>;
  if (typeof prompt.model === 'string') {
    model = lookupAction(`/model/${prompt.model}`);
  } else if (prompt.model.hasOwnProperty("info")) {
    const ref = prompt.model as ModelReference<CustomOptions>
    model = lookupAction(`/model/${ref.name}`);
  } else {
    model = prompt.model as ModelAction<CustomOptions>;
  }
  if (!model) {
    throw new Error(`Model ${prompt.model} not found`);
  }

  const request = toGenerateRequest(prompt);
  const response = new GenerationResponse<z.infer<O>>(await model(request));
  if (prompt.output?.schema) {
    const outputData = response.output();
    prompt.output.schema.parse(outputData);
  }
  
  // Pick the first valid candidate.
  let selected;
  for (const candidate of response.candidates) {
    if (isValidCandidate(candidate, prompt.tools || [])) {
      selected = candidate; 
      break;
    }
  }

  if (!selected) {
    throw new Error(`No valid candidates found`);
  }
  
  const toolCalls = selected.message.content.filter(part => !!part.toolRequest);
  if (prompt.returnToolRequests || toolCalls.length === 0) {
    return response;
  }
  const toolResponses: ToolResponsePart[] = await Promise.all(toolCalls.map(async part => {
    const tool = prompt.tools?.find(tool => tool.__action.name === part.toolRequest?.name);
    if (!tool) {
      throw Error(`Tool not found`);
    }
    return {name: part.toolRequest.name, ref: part.toolRequest.ref, output: await tool(part.toolRequest?.input)};
  }))
  prompt.history?.push({role: "tool", content: toolResponses});
  return await generate(prompt);
}
