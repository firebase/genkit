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
  DocumentBlockParam,
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
} from '@anthropic-ai/sdk/resources/messages';
import type {
  GenerateRequest,
  GenerateResponseData,
  MessageData,
  ModelReference,
  ModelResponseData,
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
  GenerateResponseChunkData,
  ModelAction,
  ToolDefinition,
} from 'genkit/model';
import { modelRef } from 'genkit/model';
import { model } from 'genkit/plugin';

import { MediaType, type Media } from './types.js';

/**
 * Default maximum output tokens for Claude models when not specified in the request.
 */
const DEFAULT_MAX_OUTPUT_TOKENS = 4096;

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

const isMediaObject = (obj: unknown): obj is Media =>
  typeof obj === 'object' &&
  obj !== null &&
  'url' in obj &&
  typeof (obj as Media).url === 'string';

/**
 * Checks if a URL is a data URL (starts with 'data:').
 * This follows the Google GenAI plugin pattern for distinguishing inline data from file references.
 */
const isDataUrl = (url: string): boolean => {
  return url.startsWith('data:');
};

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
    throw new Error(
      `Invalid genkit part provided to toAnthropicToolResponseContent: ${JSON.stringify(
        part
      )}.`
    );
  }

  // Check if the output is a media object or a string
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

  // Handle media content
  if (base64Data) {
    const resolvedMediaType: string | undefined =
      (part.toolResponse?.output as Media)?.contentType ??
      base64Data?.contentType;
    if (
      !resolvedMediaType ||
      !Object.values(MediaType).includes(resolvedMediaType as MediaType)
    ) {
      throw new Error(`Invalid media type: ${resolvedMediaType}`);
    }
    const mediaTypeValue: MediaType = resolvedMediaType as MediaType;

    return {
      type: 'image',
      source: {
        type: 'base64',
        data: base64Data.data,
        media_type: mediaTypeValue,
      },
    };
  }

  // Handle text content
  return {
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
):
  | TextBlock
  | ImageBlockParam
  | DocumentBlockParam
  | ToolUseBlockParam
  | ToolResultBlockParam {
  if (part.text) {
    // Anthropic SDK expects citations field to be explicitly set to null
    // when not provided (tests confirm this pattern is correct)
    return {
      type: 'text',
      text: part.text,
      citations: null,
    };
  }
  if (part.media) {
    const resolvedContentType = part.media.contentType;

    // Check if this is a PDF document
    if (resolvedContentType === 'application/pdf') {
      const url = part.media.url;

      if (isDataUrl(url)) {
        // Extract base64 data and MIME type from data URL
        const base64Match = url.match(/^data:([^;]+);base64,(.+)$/);
        if (!base64Match) {
          throw new Error(
            `Invalid PDF data URL format: ${url.substring(0, 50)}...`
          );
        }

        const extractedContentType = base64Match[1];
        const base64Data = base64Match[2];

        // Verify the extracted type matches PDF
        if (extractedContentType !== 'application/pdf') {
          throw new Error(
            `PDF contentType mismatch: expected application/pdf, got ${extractedContentType}`
          );
        }

        return {
          type: 'document',
          source: {
            type: 'base64',
            media_type: 'application/pdf',
            data: base64Data,
          },
        };
      } else {
        // File URL (HTTP/HTTPS/other) - contentType is already verified as 'application/pdf'
        return {
          type: 'document',
          source: {
            type: 'url',
            url: url,
          },
        };
      }
    }

    // Handle non-PDF media (images) - existing logic
    const { data, contentType } =
      extractDataFromBase64Url(part.media.url) ?? {};
    if (!data) {
      throw new Error(
        `Invalid genkit part media provided to toAnthropicMessageContent: ${JSON.stringify(
          part.media
        )}.`
      );
    }

    // Resolve and validate the media type
    const resolvedMediaType: string | undefined =
      part.media.contentType ?? contentType;
    if (!resolvedMediaType) {
      throw new Error('Media type is required but was not provided');
    }
    if (!Object.values(MediaType).includes(resolvedMediaType as MediaType)) {
      throw new Error(`Unsupported media type: ${resolvedMediaType}`);
    }
    const mediaTypeValue: MediaType = resolvedMediaType as MediaType;

    return {
      type: 'image',
      source: {
        type: 'base64',
        data,
        media_type: mediaTypeValue,
      },
    };
  }
  if (part.toolRequest) {
    if (!part.toolRequest.ref) {
      throw new Error(
        `Tool request ref is required for Anthropic API. Part: ${JSON.stringify(
          part.toolRequest
        )}`
      );
    }
    return {
      type: 'tool_use',
      id: part.toolRequest.ref,
      name: part.toolRequest.name,
      input: part.toolRequest.input,
    };
  }
  if (part.toolResponse) {
    if (!part.toolResponse.ref) {
      throw new Error(
        `Tool response ref is required for Anthropic API. Part: ${JSON.stringify(
          part.toolResponse
        )}`
      );
    }
    return {
      type: 'tool_result',
      tool_use_id: part.toolResponse.ref,
      content: [toAnthropicToolResponseContent(part)],
    };
  }
  throw new Error(
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
    // Handle unexpected content block types
    // Log warning for debugging, but return empty text to avoid breaking the flow
    const unknownType = (contentBlock as { type: string }).type;
    console.warn(
      `Unexpected Anthropic content block type: ${unknownType}. Returning empty text. Content block: ${JSON.stringify(contentBlock)}`
    );
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
): ModelResponseData['finishReason'] {
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
 * @throws An error if an unsupported output format is requested.
 */
export function toAnthropicRequestBody(
  modelName: string,
  request: GenerateRequest<typeof AnthropicConfigSchema>,
  stream?: boolean,
  cacheSystemPrompt?: boolean
): MessageCreateParams {
  // Use supported model ref if available for version mapping, otherwise use modelName directly
  const model = SUPPORTED_CLAUDE_MODELS[modelName];
  const { system, messages } = toAnthropicMessages(request.messages);
  const mappedModelName =
    request.config?.version ?? model?.version ?? modelName;
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
    max_tokens: request.config?.maxOutputTokens ?? DEFAULT_MAX_OUTPUT_TOKENS,
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
  // Remove undefined, null, and empty array values using a type-safe approach
  const cleanedBody = Object.fromEntries(
    Object.entries(body).filter(([_, value]) => {
      if (value === undefined || value === null) return false;
      if (Array.isArray(value) && value.length === 0) return false;
      return true;
    })
  ) as MessageCreateParams;
  return cleanedBody;
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
 * Generic Claude model info for unknown/unsupported models.
 * Used when a model name is not in SUPPORTED_CLAUDE_MODELS.
 */
const GENERIC_CLAUDE_MODEL_INFO = {
  versions: [],
  label: 'Anthropic - Claude',
  supports: {
    multiturn: true,
    tools: true,
    media: true,
    systemRole: true,
    output: ['text'],
  },
};

/**
 * Defines a Claude model with the given name and Anthropic client.
 * Accepts any model name and lets the API validate it. If the model is in SUPPORTED_CLAUDE_MODELS, uses that modelRef
 * for better defaults; otherwise creates a generic model reference.
 */
export function claudeModel(
  name: string,
  client: Anthropic,
  cacheSystemPrompt?: boolean
): ModelAction<typeof AnthropicConfigSchema> {
  // Use supported model ref if available, otherwise create generic model ref
  const modelRef = SUPPORTED_CLAUDE_MODELS[name];
  const modelInfo = modelRef ? modelRef.info : GENERIC_CLAUDE_MODEL_INFO;

  return model(
    {
      name: `anthropic/${name}`,
      ...modelInfo,
      configSchema: AnthropicConfigSchema,
    },
    claudeRunner(name, client, cacheSystemPrompt)
  );
}
