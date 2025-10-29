/**
 * Copyright 2025 Google LLC
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

import type Anthropic from '@anthropic-ai/sdk';
import type {
  ContentBlock,
  ImageBlockParam,
  Message,
  MessageCreateParams,
  MessageParam,
  MessageStreamEvent,
  TextBlock,
  TextBlockParam,
  Tool,
  ToolResultBlockParam,
  ToolUseBlockParam,
} from '@anthropic-ai/sdk/resources/messages.mjs';
import type {
  GenerateRequest,
  GenerateResponseData,
  MessageData,
  ModelReference,
  Part,
  Role,
  StreamingCallback,
} from 'genkit';
import {
  GenerationCommonConfigSchema,
  Message as GenkitMessage,
  z,
} from 'genkit';
import type {
  CandidateData,
  GenerateResponseChunkData,
  ModelAction,
  ToolDefinition,
} from 'genkit/model';
import { modelRef } from 'genkit/model';
import { model } from 'genkit/plugin';

export const AnthropicConfigSchema = GenerationCommonConfigSchema.extend({
  tool_choice: z
    .union([
      z.object({
        type: z.literal('auto'),
      }),
      z.object({
        type: z.literal('any'),
      }),
      z.object({
        type: z.literal('tool'),
        name: z.string(),
      }),
    ])
    .optional(),
  metadata: z
    .object({
      user_id: z.string().optional(),
    })
    .optional(),
});

export const claude4Sonnet = modelRef({
  name: 'claude-4-sonnet',
  namespace: 'anthropic',
  info: {
    versions: ['claude-sonnet-4-20250514'],
    label: 'Anthropic - Claude 4 Sonnet',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: AnthropicConfigSchema,
  version: 'claude-sonnet-4-20250514',
});

export const claude37Sonnet = modelRef({
  name: 'claude-3-7-sonnet',
  namespace: 'anthropic',
  info: {
    versions: ['claude-3-7-sonnet-20250219', 'claude-3-7-sonnet-latest'],
    label: 'Anthropic - Claude 3.7 Sonnet',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: AnthropicConfigSchema,
  version: 'claude-3-7-sonnet-latest',
});

export const claude3Opus = modelRef({
  name: 'claude-3-opus',
  namespace: 'anthropic',
  info: {
    versions: ['claude-3-opus-20240229'],
    label: 'Anthropic - Claude 3 Opus',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: AnthropicConfigSchema,
  version: 'claude-3-opus-20240229',
});

export const claude3Haiku = modelRef({
  name: 'claude-3-haiku',
  namespace: 'anthropic',
  info: {
    versions: ['claude-3-haiku-20240307'],
    label: 'Anthropic - Claude 3 Haiku',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: AnthropicConfigSchema,
  version: 'claude-3-haiku-20240307',
});

export const claude4Opus = modelRef({
  name: 'claude-4-opus',
  namespace: 'anthropic',
  info: {
    versions: ['claude-opus-4-20250514'],
    label: 'Anthropic - Claude 4 Opus',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: AnthropicConfigSchema,
  version: 'claude-opus-4-20250514',
});

export const claude35Haiku = modelRef({
  name: 'claude-3-5-haiku',
  namespace: 'anthropic',
  info: {
    versions: ['claude-3-5-haiku-20241022', 'claude-3-5-haiku-latest'],
    label: 'Anthropic - Claude 3.5 Haiku',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: AnthropicConfigSchema,
  version: 'claude-3-5-haiku-latest',
});

export const claude45Sonnet = modelRef({
  name: 'claude-4-5-sonnet',
  namespace: 'anthropic',
  info: {
    versions: ['claude-sonnet-4-5-20250929', 'claude-sonnet-4-5-latest'],
    label: 'Anthropic - Claude 4.5 Sonnet',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: AnthropicConfigSchema,
  version: 'claude-sonnet-4-5-latest',
});

export const claude45Haiku = modelRef({
  name: 'claude-4-5-haiku',
  namespace: 'anthropic',
  info: {
    versions: ['claude-haiku-4-5-20251001', 'claude-haiku-4-5-latest'],
    label: 'Anthropic - Claude 4.5 Haiku',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: AnthropicConfigSchema,
  version: 'claude-haiku-4-5-latest',
});

export const claude41Opus = modelRef({
  name: 'claude-4-1-opus',
  namespace: 'anthropic',
  info: {
    versions: ['claude-opus-4-1-20250805', 'claude-opus-4-1-latest'],
    label: 'Anthropic - Claude 4.1 Opus',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: AnthropicConfigSchema,
  version: 'claude-opus-4-1-latest',
});

export const SUPPORTED_CLAUDE_MODELS: Record<
  string,
  ModelReference<typeof AnthropicConfigSchema>
> = {
  'claude-3-7-sonnet': claude37Sonnet,
  'claude-3-opus': claude3Opus,
  'claude-3-haiku': claude3Haiku,
  'claude-3-5-haiku': claude35Haiku,
  'claude-4-sonnet': claude4Sonnet,
  'claude-4-opus': claude4Opus,
  'claude-4-5-sonnet': claude45Sonnet,
  'claude-4-5-haiku': claude45Haiku,
  'claude-4-1-opus': claude41Opus,
};

/**
 * Converts a Genkit role to the corresponding Anthropic role.
 */
export function toAnthropicRole(
  role: Role,
  toolMessageType?: 'tool_use' | 'tool_result'
): MessageParam['role'] {
  switch (role) {
    case 'user':
      return 'user';
    case 'model':
      return 'assistant';
    case 'tool':
      return toolMessageType === 'tool_use' ? 'assistant' : 'user';
    default:
      throw new Error(`role ${role} doesn't map to an Anthropic role.`);
  }
}

interface Media {
  url: string;
  contentType?: string;
}

const isMediaObject = (obj: unknown): obj is Media =>
  typeof obj === 'object' &&
  obj !== null &&
  'url' in obj &&
  typeof (obj as Media).url === 'string';

const extractDataFromBase64Url = (
  url: string
): { data: string; contentType: string } | null => {
  const match = url.match(/^data:([^;]+);base64,(.+)$/);
  return (
    match && {
      contentType: match[1],
      data: match[2],
    }
  );
};

/**
 * Converts a Genkit message Part to the corresponding Anthropic TextBlockParam or ImageBlockParam.
 */
export function toAnthropicToolResponseContent(
  part: Part
): TextBlockParam | ImageBlockParam {
  if (!part.toolResponse) {
    throw Error(
      `Invalid genkit part provided to toAnthropicToolResponseContent: ${JSON.stringify(
        part
      )}.`
    );
  }
  const isMedia = isMediaObject(part.toolResponse?.output);
  const isString = typeof part.toolResponse?.output === 'string';
  let base64Data;
  if (isMedia) {
    base64Data = extractDataFromBase64Url(
      (part.toolResponse?.output as Media).url
    );
  } else if (isString) {
    base64Data = extractDataFromBase64Url(part.toolResponse?.output as string);
  }
  return base64Data
    ? {
        type: 'image',
        source: {
          type: 'base64',
          data: base64Data.data,
          media_type:
            (part.toolResponse?.output as Media)?.contentType ??
            base64Data.contentType,
        },
      }
    : {
        type: 'text',
        text: isString
          ? (part.toolResponse?.output as string)
          : JSON.stringify(part.toolResponse?.output),
      };
}

/**
 * Converts a Genkit Part to the corresponding Anthropic TextBlock, ImageBlockParam, etc.
 */
export function toAnthropicMessageContent(
  part: Part
): TextBlock | ImageBlockParam | ToolUseBlockParam | ToolResultBlockParam {
  if (part.text) {
    return {
      type: 'text',
      text: part.text,
      citations: null,
    };
  }
  if (part.media) {
    const { data, contentType } =
      extractDataFromBase64Url(part.media.url) ?? {};
    if (!data) {
      throw Error(
        `Invalid genkit part media provided to toAnthropicMessageContent: ${JSON.stringify(
          part.media
        )}.`
      );
    }
    return {
      type: 'image',
      source: {
        type: 'base64',
        data,
        // @ts-expect-error TODO: improve these types
        media_type: part.media.contentType ?? contentType,
      },
    };
  }
  if (part.toolRequest) {
    return {
      type: 'tool_use',
      id: part.toolRequest.ref!,
      name: part.toolRequest.name,
      input: part.toolRequest.input,
    };
  }
  if (part.toolResponse) {
    return {
      type: 'tool_result',
      tool_use_id: part.toolResponse.ref!,
      content: [toAnthropicToolResponseContent(part)],
    };
  }
  throw Error(
    `Unsupported genkit part fields encountered for current message role: ${JSON.stringify(
      part
    )}.`
  );
}

/**
 * Converts a Genkit MessageData array to Anthropic system message and MessageParam array.
 * @param messages The Genkit MessageData array to convert.
 * @returns An object containing the optional Anthropic system message and the array of Anthropic MessageParam objects.
 */
export function toAnthropicMessages(messages: MessageData[]): {
  system?: string;
  messages: MessageParam[];
} {
  const system =
    messages[0]?.role === 'system' ? messages[0].content?.[0]?.text : undefined;
  const messagesToIterate = system ? messages.slice(1) : messages;
  const anthropicMsgs: MessageParam[] = [];
  for (const message of messagesToIterate) {
    const msg = new GenkitMessage(message);
    const content = msg.content.map(toAnthropicMessageContent);
    const toolMessageType = content.find(
      (c) => c.type === 'tool_use' || c.type === 'tool_result'
    ) as ToolUseBlockParam | ToolResultBlockParam;
    const role = toAnthropicRole(message.role, toolMessageType?.type);
    anthropicMsgs.push({
      role: role,
      content,
    });
  }
  return { system, messages: anthropicMsgs };
}

/**
 * Converts a Genkit ToolDefinition to an Anthropic Tool object.
 * @param tool The Genkit ToolDefinition to convert.
 * @returns The converted Anthropic Tool object.
 */
export function toAnthropicTool(tool: ToolDefinition): Tool {
  return {
    name: tool.name,
    description: tool.description,
    input_schema: tool.inputSchema as Tool.InputSchema,
  };
}

/**
 * Converts an Anthropic content block to a Genkit Part object.
 * @param contentBlock The Anthropic content block to convert.
 * @returns The converted Genkit Part object.
 * @param event The Anthropic message stream event to convert.
 * @returns The converted Genkit Part object if the event is a content block
 *          start or delta, otherwise undefined.
 */
function fromAnthropicContentBlock(contentBlock: ContentBlock): Part {
  if (contentBlock.type === 'tool_use') {
    return {
      toolRequest: {
        ref: contentBlock.id,
        name: contentBlock.name,
        input: contentBlock.input,
      },
    };
  } else if (contentBlock.type === 'text') {
    return { text: contentBlock.text };
  } else if (contentBlock.type === 'thinking') {
    return { text: contentBlock.thinking };
  } else if (contentBlock.type === 'redacted_thinking') {
    return { text: contentBlock.data };
  } else {
    // Handle other content block types
    return { text: '' };
  }
}

/**
 * Converts an Anthropic message stream event to a Genkit Part object.
 */
export function fromAnthropicContentBlockChunk(
  event: MessageStreamEvent
): Part | undefined {
  if (
    event.type !== 'content_block_start' &&
    event.type !== 'content_block_delta'
  ) {
    return;
  }
  const eventField =
    event.type === 'content_block_start' ? 'content_block' : 'delta';
  return ['text', 'text_delta'].includes(event[eventField].type)
    ? {
        text: event[eventField].text,
      }
    : {
        toolRequest: {
          ref: event[eventField].id,
          name: event[eventField].name,
          input: event[eventField].input,
        },
      };
}

export function fromAnthropicStopReason(
  reason: Message['stop_reason']
  // TODO: CandidateData is deprecated
): CandidateData['finishReason'] {
  switch (reason) {
    case 'max_tokens':
      return 'length';
    case 'end_turn':
    // fall through
    case 'stop_sequence':
    // fall through
    case 'tool_use':
      return 'stop';
    case null:
      return 'unknown';
    default:
      return 'other';
  }
}

export function fromAnthropicResponse(response: Message): GenerateResponseData {
  return {
    candidates: [
      {
        index: 0,
        finishReason: fromAnthropicStopReason(response.stop_reason),
        message: {
          role: 'model',
          content: response.content.map(fromAnthropicContentBlock),
        },
      },
    ],
    usage: {
      inputTokens: response.usage.input_tokens,
      outputTokens: response.usage.output_tokens,
    },
    custom: response,
  };
}

/**
 * Converts an Anthropic request to an Anthropic API request body.
 * @param modelName The name of the Anthropic model to use.
 * @param request The Genkit GenerateRequest to convert.
 * @param stream Whether to stream the response.
 * @param cacheSystemPrompt Whether to cache the system prompt.
 * @returns The converted Anthropic API request body.
 * @throws An error if the specified model is not supported or if an unsupported output format is requested.
 */
export function toAnthropicRequestBody(
  modelName: string,
  request: GenerateRequest<typeof AnthropicConfigSchema>,
  stream?: boolean,
  cacheSystemPrompt?: boolean
): MessageCreateParams {
  const model = SUPPORTED_CLAUDE_MODELS[modelName];
  if (!model) throw new Error(`Unsupported model: ${modelName}`);
  const { system, messages } = toAnthropicMessages(request.messages);
  const mappedModelName = request.config?.version ?? model.version ?? modelName;
  const body: MessageCreateParams = {
    system:
      cacheSystemPrompt && system
        ? [
            {
              type: 'text',
              text: system,
              cache_control: { type: 'ephemeral' },
            },
          ]
        : system,
    messages,
    tools: request.tools?.map(toAnthropicTool),
    max_tokens: request.config?.maxOutputTokens ?? 4096,
    model: mappedModelName,
    top_k: request.config?.topK,
    top_p: request.config?.topP,
    temperature: request.config?.temperature,
    stop_sequences: request.config?.stopSequences,
    metadata: request.config?.metadata,
    tool_choice: request.config?.tool_choice,
    stream,
  };

  if (request.output?.format && request.output.format !== 'text') {
    throw new Error(
      `Only text output format is supported for Claude models currently`
    );
  }
  for (const key in body) {
    if (!body[key] || (Array.isArray(body[key]) && !body[key].length))
      delete body[key];
  }
  return body;
}

/**
 * Creates the runner used by Genkit to interact with the Claude model.
 * @param name The name of the Claude model.
 * @param client The Anthropic client instance.
 * @param cacheSystemPrompt Whether to cache the system prompt.
 * @returns The runner that Genkit will call when the model is invoked.
 */
export function claudeRunner(
  name: string,
  client: Anthropic,
  cacheSystemPrompt?: boolean
) {
  return async (
    request: GenerateRequest<typeof AnthropicConfigSchema>,
    {
      streamingRequested,
      sendChunk,
      abortSignal,
    }: {
      streamingRequested: boolean;
      sendChunk: StreamingCallback<GenerateResponseChunkData>;
      abortSignal: AbortSignal;
    }
  ): Promise<GenerateResponseData> => {
    let response: Message;
    const body = toAnthropicRequestBody(
      name,
      request,
      streamingRequested,
      cacheSystemPrompt
    );

    if (streamingRequested) {
      const stream = client.messages.stream(body, { signal: abortSignal });
      for await (const chunk of stream) {
        const c = fromAnthropicContentBlockChunk(chunk);
        if (c) {
          sendChunk({
            index: 0,
            content: [c],
          });
        }
      }
      response = await stream.finalMessage();
    } else {
      response = (await client.messages.create(body, {
        signal: abortSignal,
      })) as Message;
    }
    return fromAnthropicResponse(response);
  };
}

/**
 * Defines a Claude model with the given name and Anthropic client.
 */
export function claudeModel(
  name: string,
  client: Anthropic,
  cacheSystemPrompt?: boolean
): ModelAction<typeof AnthropicConfigSchema> {
  const modelRef = SUPPORTED_CLAUDE_MODELS[name];
  if (!modelRef) throw new Error(`Unsupported model: ${name}`);

  return model(
    {
      name: `anthropic/${name}`,
      ...modelRef.info,
      configSchema: modelRef.configSchema,
    },
    claudeRunner(name, client, cacheSystemPrompt)
  );
}
