/**
 * Copyright 2024 The Fire Company
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

import type {
  GenerateRequest,
  GenerateResponseData,
  Genkit,
  MessageData,
  ModelReference,
  Part,
  Role,
  StreamingCallback,
  ToolRequestPart,
} from 'genkit';
import { GenerationCommonConfigSchema, Message, z } from 'genkit';
import type {
  CandidateData,
  GenerateResponseChunkData,
  ToolDefinition,
} from 'genkit/model';
import type OpenAI from 'openai';
import type {
  ChatCompletion,
  ChatCompletionChunk,
  ChatCompletionContentPart,
  ChatCompletionCreateParamsNonStreaming,
  ChatCompletionMessageParam,
  ChatCompletionMessageToolCall,
  ChatCompletionRole,
  ChatCompletionTool,
  CompletionChoice,
} from 'openai/resources/index.mjs';

export const OpenAiConfigSchema = GenerationCommonConfigSchema.extend({
  frequencyPenalty: z.number().min(-2).max(2).optional(),
  logitBias: z.record(z.string(), z.number().min(-100).max(100)).optional(),
  logProbs: z.boolean().optional(),
  presencePenalty: z.number().min(-2).max(2).optional(),
  seed: z.number().int().optional(),
  topLogProbs: z.number().int().min(0).max(20).optional(),
  user: z.string().optional(),
  visualDetailLevel: z.enum(['auto', 'low', 'high']).optional(),
});

type VisualDetailLevel = z.infer<
  typeof OpenAiConfigSchema
>['visualDetailLevel'];

export function toOpenAIRole(role: Role): ChatCompletionRole {
  switch (role) {
    case 'user':
      return 'user';
    case 'model':
      return 'assistant';
    case 'system':
      return 'system';
    case 'tool':
      return 'tool';
    default:
      throw new Error(`role ${role} doesn't map to an OpenAI role.`);
  }
}

/**
 * Converts a Genkit ToolDefinition to an OpenAI ChatCompletionTool object.
 * @param tool The Genkit ToolDefinition to convert.
 * @returns The converted OpenAI ChatCompletionTool object.
 */
export function toOpenAiTool(tool: ToolDefinition): ChatCompletionTool {
  return {
    type: 'function',
    function: {
      name: tool.name,
      parameters: tool.inputSchema !== null ? tool.inputSchema : undefined,
    },
  };
}

/**
 * Converts a Genkit Part to the corresponding OpenAI ChatCompletionContentPart.
 * @param part The Genkit Part to convert.
 * @param visualDetailLevel The visual detail level to use for media parts.
 * @returns The corresponding OpenAI ChatCompletionContentPart.
 * @throws Error if the part contains unsupported fields for the current message role.
 */
export function toOpenAiTextAndMedia(
  part: Part,
  visualDetailLevel: VisualDetailLevel
): ChatCompletionContentPart {
  if (part.text) {
    return {
      type: 'text',
      text: part.text,
    };
  } else if (part.media) {
    return {
      type: 'image_url',
      image_url: {
        url: part.media.url,
        detail: visualDetailLevel,
      },
    };
  }
  throw Error(
    `Unsupported genkit part fields encountered for current message role: ${JSON.stringify(part)}.`
  );
}

/**
 * Converts a Genkit MessageData array to an OpenAI ChatCompletionMessageParam array.
 * @param messages The Genkit MessageData array to convert.
 * @param visualDetailLevel The visual detail level to use for media parts.
 * @returns The converted OpenAI ChatCompletionMessageParam array.
 */
export function toOpenAiMessages(
  messages: MessageData[],
  visualDetailLevel: VisualDetailLevel = 'auto'
): ChatCompletionMessageParam[] {
  const openAiMsgs: ChatCompletionMessageParam[] = [];
  for (const message of messages) {
    const msg = new Message(message);
    const role = toOpenAIRole(message.role);
    switch (role) {
      case 'user':
        const content = msg.content.map((part) =>
          toOpenAiTextAndMedia(part, visualDetailLevel)
        );
        // Check if we have only text content
        const onlyTextContent = content.some((item) => item.type !== 'text');

        // If all items are strings, just add them as text
        if (!onlyTextContent) {
          content.forEach((item, index) => {
            if (item.type === 'text') {
              openAiMsgs.push({
                role: role,
                content: item.text,
              });
            }
          });
        } else {
          openAiMsgs.push({
            role: role,
            content: content,
          });
        }
        break;
      case 'system':
        openAiMsgs.push({
          role: role,
          content: msg.text,
        });
        break;
      case 'assistant': {
        const toolCalls: ChatCompletionMessageToolCall[] = msg.content
          .filter(
            (
              part
            ): part is Part & {
              toolRequest: NonNullable<Part['toolRequest']>;
            } => Boolean(part.toolRequest)
          )
          .map((part) => ({
            id: part.toolRequest.ref ?? '',
            type: 'function',
            function: {
              name: part.toolRequest.name,
              arguments: JSON.stringify(part.toolRequest.input),
            },
          }));
        if (toolCalls.length > 0) {
          openAiMsgs.push({
            role: role,
            tool_calls: toolCalls,
          });
        } else {
          openAiMsgs.push({
            role: role,
            content: msg.text,
          });
        }
        break;
      }
      case 'tool': {
        const toolResponseParts = msg.toolResponseParts();
        toolResponseParts.map((part) => {
          openAiMsgs.push({
            role: role,
            tool_call_id: part.toolResponse.ref ?? '',
            content:
              typeof part.toolResponse.output === 'string'
                ? part.toolResponse.output
                : JSON.stringify(part.toolResponse.output),
          });
        });
        break;
      }
    }
  }
  return openAiMsgs;
}

const finishReasonMap: Record<
  // OpenAI Node SDK doesn't support tool_call in the enum, but it is returned from the API
  CompletionChoice['finish_reason'] | 'tool_calls',
  CandidateData['finishReason']
> = {
  length: 'length',
  stop: 'stop',
  tool_calls: 'stop',
  content_filter: 'blocked',
};

/**
 * Converts an OpenAI tool call to a Genkit ToolRequestPart.
 * @param toolCall The OpenAI tool call to convert.
 * @returns The converted Genkit ToolRequestPart.
 */
export function fromOpenAiToolCall(
  toolCall:
    | ChatCompletionMessageToolCall
    | ChatCompletionChunk.Choice.Delta.ToolCall,
  choice: ChatCompletion.Choice | ChatCompletionChunk.Choice
): ToolRequestPart {
  if (!toolCall.function) {
    throw Error(
      `Unexpected openAI chunk choice. tool_calls was provided but one or more tool_calls is missing.`
    );
  }
  const f = toolCall.function;

  // Only parse arugments when it is a JSON object and the finish reason is tool_calls to avoid parsing errors
  if (choice.finish_reason === 'tool_calls') {
    return {
      toolRequest: {
        name: f.name!,
        ref: toolCall.id,
        input: f.arguments ? JSON.parse(f.arguments) : f.arguments,
      },
    };
  } else {
    return {
      toolRequest: {
        name: f.name!,
        ref: toolCall.id,
        input: '',
      },
    };
  }
}

/**
 * Converts an OpenAI message event to a Genkit CandidateData object.
 * @param choice The OpenAI message event to convert.
 * @param jsonMode Whether the event is a JSON response.
 * @returns The converted Genkit CandidateData object.
 */
export function fromOpenAiChoice(
  choice: ChatCompletion.Choice,
  jsonMode = false
): CandidateData {
  const toolRequestParts = choice.message.tool_calls?.map((toolCall) =>
    fromOpenAiToolCall(toolCall, choice)
  );
  return {
    index: choice.index,
    finishReason: finishReasonMap[choice.finish_reason] || 'other',
    message: {
      role: 'model',
      content: toolRequestParts
        ? // Note: Not sure why I have to cast here exactly.
          // Otherwise it thinks toolRequest must be 'undefined' if provided
          (toolRequestParts as ToolRequestPart[])
        : [
            jsonMode
              ? { data: JSON.parse(choice.message.content!) }
              : { text: choice.message.content! },
          ],
    },
    custom: {},
  };
}

/**
 * Converts an OpenAI message stream event to a Genkit CandidateData object.
 * @param choice The OpenAI message stream event to convert.
 * @param jsonMode Whether the event is a JSON response.
 * @returns The converted Genkit CandidateData object.
 */
export function fromOpenAiChunkChoice(
  choice: ChatCompletionChunk.Choice,
  jsonMode = false
): CandidateData {
  const toolRequestParts = choice.delta.tool_calls?.map((toolCall) =>
    fromOpenAiToolCall(toolCall, choice)
  );
  return {
    index: choice.index,
    finishReason: choice.finish_reason
      ? finishReasonMap[choice.finish_reason] || 'other'
      : 'unknown',
    message: {
      role: 'model',
      content: toolRequestParts
        ? // Note: Not sure why I have to cast here exactly.
          // Otherwise it thinks toolRequest must be 'undefined' if provided
          (toolRequestParts as ToolRequestPart[])
        : [
            jsonMode
              ? { data: JSON.parse(choice.delta.content!) }
              : { text: choice.delta.content! },
          ],
    },
    custom: {},
  };
}

/**
 * Converts an OpenAI request to an OpenAI API request body.
 * @param modelName The name of the OpenAI model to use.
 * @param request The Genkit GenerateRequest to convert.
 * @returns The converted OpenAI API request body.
 * @throws An error if the specified model is not supported or if an unsupported output format is requested.
 */
export function toOpenAiRequestBody(
  name: string,
  request: GenerateRequest<typeof OpenAiConfigSchema>
) {
  const openAiMessages = toOpenAiMessages(
    request.messages,
    request.config?.visualDetailLevel
  );
  const body = {
    model: name,
    messages: openAiMessages,
    temperature: request.config?.temperature,
    max_tokens: request.config?.maxOutputTokens,
    top_p: request.config?.topP,
    stop: request.config?.stopSequences,
    frequency_penalty: request.config?.frequencyPenalty,
    logit_bias: request.config?.logitBias,
    logprobs: request.config?.logProbs, // logprobs not snake case!
    presence_penalty: request.config?.presencePenalty,
    seed: request.config?.seed,
    top_logprobs: request.config?.topLogProbs, // logprobs not snake case!
    user: request.config?.user,
    tools: request.tools?.map(toOpenAiTool),
    n: request.candidates,
  } as ChatCompletionCreateParamsNonStreaming;

  const response_format = request.output?.format;
  if (response_format === 'json') {
    body.response_format = {
      type: 'json_object',
    };
  } else if (response_format === 'text') {
    body.response_format = {
      type: 'text',
    };
  }
  for (const key in body) {
    if (!body[key] || (Array.isArray(body[key]) && !body[key].length))
      delete body[key];
  }
  return body;
}

/**
 * Creates the runner used by Genkit to interact with an OpenAI compatible
 * model.
 * @param name The name of the GPT model.
 * @param client The OpenAI client instance.
 * @returns The runner that Genkit will call when the model is invoked.
 */
export function openAiModelRunner(name: string, client: OpenAI) {
  return async (
    request: GenerateRequest<typeof OpenAiConfigSchema>,
    streamingCallback?: StreamingCallback<GenerateResponseChunkData>
  ): Promise<GenerateResponseData> => {
    let response: ChatCompletion;
    const body = toOpenAiRequestBody(name, request);
    if (streamingCallback) {
      const stream = client.beta.chat.completions.stream({
        ...body,
        stream: true,
        stream_options: {
          include_usage: true,
        },
      });
      for await (const chunk of stream) {
        chunk.choices?.forEach((chunk) => {
          const c = fromOpenAiChunkChoice(chunk);
          streamingCallback({
            index: c.index,
            content: c.message.content,
          });
        });
      }
      response = await stream.finalChatCompletion();
    } else {
      response = await client.chat.completions.create(body);
    }
    return {
      candidates: response.choices.map((c) =>
        fromOpenAiChoice(c, request.output?.format === 'json')
      ),
      usage: {
        inputTokens: response.usage?.prompt_tokens,
        outputTokens: response.usage?.completion_tokens,
        totalTokens: response.usage?.total_tokens,
      },
      custom: response,
    };
  };
}

export function textModel(
  ai: Genkit,
  name: string,
  client: OpenAI,
  modelRef: ModelReference<typeof OpenAiConfigSchema>
) {
  return ai.defineModel(
    {
      name,
      ...modelRef.info,
      configSchema: modelRef.configSchema,
    },
    openAiModelRunner(name, client)
  );
}
