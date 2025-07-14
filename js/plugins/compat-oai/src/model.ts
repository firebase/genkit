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
  ToolRequestPart,
} from 'genkit';
import { GenerationCommonConfigSchema, Message, z } from 'genkit';
import type { ModelAction, ToolDefinition } from 'genkit/model';
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

const VisualDetailLevelSchema = z.enum(['auto', 'low', 'high']).optional();

type VisualDetailLevel = z.infer<typeof VisualDetailLevelSchema>;

export const ChatCompletionCommonConfigSchema =
  GenerationCommonConfigSchema.extend({
    temperature: z.number().min(0).max(2).optional(),
    frequencyPenalty: z.number().min(-2).max(2).optional(),
    logProbs: z.boolean().optional(),
    presencePenalty: z.number().min(-2).max(2).optional(),
    topLogProbs: z.number().int().min(0).max(20).optional(),
  });

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
export function toOpenAITool(tool: ToolDefinition): ChatCompletionTool {
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
export function toOpenAITextAndMedia(
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
export function toOpenAIMessages(
  messages: MessageData[],
  visualDetailLevel: VisualDetailLevel = 'auto'
): ChatCompletionMessageParam[] {
  const apiMessages: ChatCompletionMessageParam[] = [];
  for (const message of messages) {
    const msg = new Message(message);
    const role = toOpenAIRole(message.role);
    switch (role) {
      case 'user':
        const content = msg.content.map((part) =>
          toOpenAITextAndMedia(part, visualDetailLevel)
        );
        // Check if we have only text content
        const onlyTextContent = content.some((item) => item.type !== 'text');

        // If all items are strings, just add them as text
        if (!onlyTextContent) {
          content.forEach((item) => {
            if (item.type === 'text') {
              apiMessages.push({
                role: role,
                content: item.text,
              });
            }
          });
        } else {
          apiMessages.push({
            role: role,
            content: content,
          });
        }
        break;
      case 'system':
        apiMessages.push({
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
          apiMessages.push({
            role: role,
            tool_calls: toolCalls,
          });
        } else {
          apiMessages.push({
            role: role,
            content: msg.text,
          });
        }
        break;
      }
      case 'tool': {
        const toolResponseParts = msg.toolResponseParts();
        toolResponseParts.map((part) => {
          apiMessages.push({
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
  return apiMessages;
}

const finishReasonMap: Record<
  // OpenAI Node SDK doesn't support tool_call in the enum, but it is returned from the API
  CompletionChoice['finish_reason'] | 'tool_calls',
  GenerateResponseData['finishReason']
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
export function fromOpenAIToolCall(
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
 * Converts an OpenAI message event to a Genkit GenerateResponseData object.
 * @param choice The OpenAI message event to convert.
 * @param jsonMode Whether the event is a JSON response.
 * @returns The converted Genkit GenerateResponseData object.
 */
export function fromOpenAIChoice(
  choice: ChatCompletion.Choice,
  jsonMode = false
): GenerateResponseData {
  const toolRequestParts = choice.message.tool_calls?.map((toolCall) =>
    fromOpenAIToolCall(toolCall, choice)
  );
  return {
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
  };
}

/**
 * Converts an OpenAI message stream event to a Genkit GenerateResponseData
 * object.
 * @param choice The OpenAI message stream event to convert.
 * @param jsonMode Whether the event is a JSON response.
 * @returns The converted Genkit GenerateResponseData object.
 */
export function fromOpenAIChunkChoice(
  choice: ChatCompletionChunk.Choice,
  jsonMode = false
): GenerateResponseData {
  const toolRequestParts = choice.delta.tool_calls?.map((toolCall) =>
    fromOpenAIToolCall(toolCall, choice)
  );
  return {
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
  };
}

/**
 * Converts an OpenAI request to an OpenAI API request body.
 * @param modelName The name of the OpenAI model to use.
 * @param request The Genkit GenerateRequest to convert.
 * @returns The converted OpenAI API request body.
 * @throws An error if the specified model is not supported or if an unsupported output format is requested.
 */
export function toOpenAIRequestBody(
  modelName: string,
  request: GenerateRequest
) {
  const messages = toOpenAIMessages(
    request.messages,
    request.config?.visualDetailLevel
  );
  const {
    temperature,
    maxOutputTokens, // unused
    topK, // unused
    topP: top_p,
    frequencyPenalty: frequency_penalty,
    logProbs: logprobs,
    presencePenalty: presence_penalty,
    topLogProbs: top_logprobs,
    stopSequences: stop,
    version: modelVersion,
    tools: toolsFromConfig,
    ...restOfConfig
  } = request.config ?? {};

  const tools: ChatCompletionTool[] = request.tools?.map(toOpenAITool) ?? [];
  if (toolsFromConfig) {
    tools.push(...(toolsFromConfig as any[]));
  }
  const body = {
    model: modelVersion ?? modelName,
    messages,
    tools: tools.length > 0 ? tools : undefined,
    temperature,
    top_p,
    stop,
    frequency_penalty,
    presence_penalty,
    top_logprobs,
    logprobs,
    ...restOfConfig, // passthrough for other config
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
export function openAIModelRunner(name: string, client: OpenAI) {
  return;
}

/**
 * Method to define a new Genkit Model that is compatible with Open AI
 * Chat Completions API. 
 *
 * These models are to be used to chat with a large language model.
 *
 * @param params An object containing parameters for defining the OpenAI
 * Chat model.
 * @param params.ai The Genkit AI instance.
 * @param params.name The name of the model.
 * @param params.client The OpenAI client instance.
 * @param params.modelRef Optional reference to the model's configuration and
 * custom options.

 * @returns the created {@link ModelAction}
 */
export function defineCompatOpenAIModel<
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(params: {
  ai: Genkit;
  name: string;
  client: OpenAI;
  modelRef?: ModelReference<CustomOptions>;
}): ModelAction {
  const { ai, name, client, modelRef } = params;
  const modelName = name.split('/').pop();

  return ai.defineModel(
    {
      name,
      apiVersion: 'v2',
      ...modelRef?.info,
      configSchema: modelRef?.configSchema,
    },
    async (request, { streamingRequested, sendChunk, abortSignal }) => {
      let response: ChatCompletion;
      const body = toOpenAIRequestBody(modelName!, request);
      if (streamingRequested) {
        const stream = client.beta.chat.completions.stream(
          {
            ...body,
            stream: true,
            stream_options: {
              include_usage: true,
            },
          },
          { signal: abortSignal }
        );
        for await (const chunk of stream) {
          chunk.choices?.forEach((chunk) => {
            const c = fromOpenAIChunkChoice(chunk);
            sendChunk({
              index: chunk.index,
              content: c.message?.content ?? [],
            });
          });
        }
        response = await stream.finalChatCompletion();
      } else {
        response = await client.chat.completions.create(body, {
          signal: abortSignal,
        });
      }
      const standardResponse: GenerateResponseData = {
        usage: {
          inputTokens: response.usage?.prompt_tokens,
          outputTokens: response.usage?.completion_tokens,
          totalTokens: response.usage?.total_tokens,
        },
        raw: response,
      };
      if (response.choices.length === 0) {
        return standardResponse;
      } else {
        const choice = response.choices[0];
        return {
          ...fromOpenAIChoice(choice, request.output?.format === 'json'),
          ...standardResponse,
        };
      }
    }
  );
}
