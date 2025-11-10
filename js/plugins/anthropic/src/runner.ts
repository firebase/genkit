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

import { Anthropic } from '@anthropic-ai/sdk';
import type { BetaMessageStream } from '@anthropic-ai/sdk/lib/BetaMessageStream';
import type { MessageStream } from '@anthropic-ai/sdk/lib/MessageStream';
import type {
  BetaContentBlock,
  BetaContentBlockParam,
  BetaImageBlockParam,
  BetaMCPToolUseBlock,
  BetaMessage,
  MessageCreateParams as BetaMessageCreateParams,
  BetaMessageParam,
  BetaRawMessageStreamEvent,
  BetaRequestDocumentBlock,
  BetaSearchResultBlockParam,
  BetaServerToolUseBlock,
  BetaStopReason,
  BetaTextBlockParam,
  BetaToolResultBlockParam,
  BetaToolUseBlock,
} from '@anthropic-ai/sdk/resources/beta/messages';
import type {
  ContentBlock,
  DocumentBlockParam,
  ImageBlockParam,
  Message,
  MessageCreateParams,
  MessageParam,
  MessageStreamEvent,
  TextBlockParam,
  Tool,
  ToolResultBlockParam,
  ToolUseBlockParam,
} from '@anthropic-ai/sdk/resources/messages';
import type {
  GenerateRequest,
  GenerateResponseChunkData,
  GenerateResponseData,
  MessageData,
  ModelResponseData,
  Part,
  Role,
} from 'genkit';
import { Message as GenkitMessage } from 'genkit';
import type { ToolDefinition } from 'genkit/model';

import { SUPPORTED_CLAUDE_MODELS } from './models';
import { AnthropicConfigSchema, Media, MediaType } from './types';

type MessageStreamLike<TMessage, TStreamEvent> = AsyncIterable<TStreamEvent> & {
  finalMessage(): Promise<TMessage>;
};

/**
 * Type guard to check if a value is a valid MediaType.
 */
function isMediaType(value: string): value is MediaType {
  return Object.values(MediaType).includes(value as MediaType);
}

/**
 * Type guard to check if an object is a Media object.
 */
function isMedia(obj: unknown): obj is Media {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'url' in obj &&
    typeof (obj as Media).url === 'string'
  );
}

export abstract class Runner<TMessage, TStreamEvent, TRequestBody> {
  protected name: string;
  protected client: Anthropic;
  protected cacheSystemPrompt?: boolean;
  /**
   * Default maximum output tokens for Claude models when not specified in the request.
   */
  protected readonly DEFAULT_MAX_OUTPUT_TOKENS = 4096;

  constructor(name: string, client: Anthropic, cacheSystemPrompt?: boolean) {
    this.name = name;
    this.client = client;
    this.cacheSystemPrompt = cacheSystemPrompt;
  }

  /**
   * Converts a Genkit role to the corresponding Anthropic role.
   */
  protected abstract toAnthropicRole(
    role: Role,
    toolMessageType?: 'tool_use' | 'tool_result'
  ): 'user' | 'assistant';

  protected isMediaObject(obj: unknown): obj is Media {
    return isMedia(obj);
  }

  /**
   * Checks if a URL is a data URL (starts with 'data:').
   * This follows the Google GenAI plugin pattern for distinguishing inline data from file references.
   */
  protected isDataUrl(url: string): boolean {
    return url.startsWith('data:');
  }

  protected extractDataFromBase64Url(
    url: string
  ): { data: string; contentType: string } | null {
    const match = url.match(/^data:([^;]+);base64,(.+)$/);
    return (
      match && {
        contentType: match[1],
        data: match[2],
      }
    );
  }

  /**
   * Converts a Genkit message Part to the corresponding Anthropic tool response content.
   * Each runner implements this to return its specific API type.
   */
  protected abstract toAnthropicToolResponseContent(part: Part): any;

  /**
   * Converts a Genkit Part to the corresponding Anthropic content block.
   * Each runner implements this to return its specific API type.
   */
  protected abstract toAnthropicMessageContent(part: Part): any;

  /**
   * Converts a Genkit MessageData array to Anthropic system and messages.
   * Each runner implements this to return its specific API types.
   */
  protected abstract toAnthropicMessages(messages: MessageData[]): {
    system?: string;
    messages: any[];
  };

  /**
   * Converts a Genkit ToolDefinition to an Anthropic Tool object.
   * Each runner implements this to return its specific API type.
   */
  protected abstract toAnthropicTool(tool: ToolDefinition): any;

  /**
   * Converts an Anthropic content block to a Genkit Part object.
   * @param contentBlock The Anthropic content block to convert.
   * @returns The converted Genkit Part object.
   * @param event The Anthropic message stream event to convert.
   * @returns The converted Genkit Part object if the event is a content block
   *          start or delta, otherwise undefined.
   */
  protected fromAnthropicContentBlock(contentBlock: ContentBlock): Part {
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
  protected fromAnthropicContentBlockChunk(
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

  protected fromAnthropicStopReason(
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

  protected fromAnthropicResponse(response: Message): GenerateResponseData {
    return {
      candidates: [
        {
          index: 0,
          finishReason: this.fromAnthropicStopReason(response.stop_reason),
          message: {
            role: 'model',
            content: response.content.map((block) =>
              this.fromAnthropicContentBlock(block)
            ),
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
  protected abstract toAnthropicRequestBody(
    modelName: string,
    request: GenerateRequest<typeof AnthropicConfigSchema>,
    stream?: boolean,
    cacheSystemPrompt?: boolean
  ): TRequestBody;

  protected abstract createMessage(
    body: TRequestBody,
    abortSignal: AbortSignal
  ): Promise<TMessage>;

  protected abstract streamMessages(
    body: TRequestBody,
    abortSignal: AbortSignal
  ): MessageStreamLike<TMessage, TStreamEvent>;

  protected abstract toGenkitResponse(message: TMessage): GenerateResponseData;

  protected abstract toGenkitPart(event: TStreamEvent): Part | undefined;

  public async run(
    request: GenerateRequest<typeof AnthropicConfigSchema>,
    options: {
      streamingRequested: boolean;
      sendChunk: (chunk: GenerateResponseChunkData) => void;
      abortSignal: AbortSignal;
    }
  ): Promise<GenerateResponseData> {
    const { streamingRequested, sendChunk, abortSignal } = options;

    const body = this.toAnthropicRequestBody(
      this.name,
      request,
      streamingRequested,
      this.cacheSystemPrompt
    );

    if (streamingRequested) {
      const stream = this.streamMessages(body, abortSignal);
      for await (const event of stream) {
        const part = this.toGenkitPart(event);
        if (part) {
          sendChunk({
            index: 0,
            content: [part],
          });
        }
      }
      const finalMessage = await stream.finalMessage();
      return this.toGenkitResponse(finalMessage);
    }

    const response = await this.createMessage(body, abortSignal);
    return this.toGenkitResponse(response);
  }
}

export class RegularRunner extends Runner<
  Message,
  MessageStreamEvent,
  MessageCreateParams
> {
  constructor(name: string, client: Anthropic, cacheSystemPrompt?: boolean) {
    super(name, client, cacheSystemPrompt);
  }

  protected toAnthropicRole(
    role: Role,
    toolMessageType?: 'tool_use' | 'tool_result'
  ): 'user' | 'assistant' {
    if (role === 'user') {
      return 'user';
    }
    if (role === 'model') {
      return 'assistant';
    }
    if (role === 'tool') {
      return toolMessageType === 'tool_use' ? 'assistant' : 'user';
    }
    throw new Error(`Unsupported genkit role: ${role}`);
  }

  protected toAnthropicToolResponseContent(
    part: Part
  ): TextBlockParam | ImageBlockParam {
    const output = part.toolResponse?.output ?? {};

    // Handle Media objects (images returned by tools)
    if (this.isMediaObject(output)) {
      const { data, contentType } =
        this.extractDataFromBase64Url(output.url) ?? {};
      if (data && contentType && isMediaType(contentType)) {
        return {
          type: 'image',
          source: {
            type: 'base64',
            data,
            media_type: contentType,
          },
        };
      }
    }

    // Handle string outputs - check if it's a data URL
    if (typeof output === 'string') {
      // Check if string is a data URL (e.g., "data:image/gif;base64,...")
      if (this.isDataUrl(output)) {
        const { data, contentType } =
          this.extractDataFromBase64Url(output) ?? {};
        if (data && contentType && isMediaType(contentType)) {
          return {
            type: 'image',
            source: {
              type: 'base64',
              data,
              media_type: contentType,
            },
          };
        }
      }
      // Regular string output
      return {
        type: 'text',
        text: output,
      };
    }

    // Handle other outputs by stringifying
    return {
      type: 'text',
      text: JSON.stringify(output),
    };
  }

  protected toAnthropicMessageContent(
    part: Part
  ):
    | TextBlockParam
    | ImageBlockParam
    | DocumentBlockParam
    | ToolUseBlockParam
    | ToolResultBlockParam {
    if (part.text) {
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

        if (this.isDataUrl(url)) {
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
        this.extractDataFromBase64Url(part.media.url) ?? {};
      if (!data || !contentType) {
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
      if (!isMediaType(resolvedMediaType)) {
        throw new Error(`Unsupported media type: ${resolvedMediaType}`);
      }
      const mediaTypeValue: MediaType = resolvedMediaType;

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
        content: [this.toAnthropicToolResponseContent(part)],
      };
    }
    throw new Error(
      `Unsupported genkit part fields encountered for current message role: ${JSON.stringify(
        part
      )}.`
    );
  }

  protected toAnthropicMessages(messages: MessageData[]): {
    system?: string;
    messages: MessageParam[];
  } {
    const system =
      messages[0]?.role === 'system'
        ? messages[0].content?.[0]?.text
        : undefined;
    const messagesToIterate = system ? messages.slice(1) : messages;
    const anthropicMsgs: MessageParam[] = [];
    for (const message of messagesToIterate) {
      const msg = new GenkitMessage(message);
      const content = msg.content.map((part) =>
        this.toAnthropicMessageContent(part)
      );
      const toolMessageType = content.find(
        (c) => c.type === 'tool_use' || c.type === 'tool_result'
      ) as ToolUseBlockParam | ToolResultBlockParam;
      const role = this.toAnthropicRole(message.role, toolMessageType?.type);
      anthropicMsgs.push({
        role: role,
        content,
      });
    }
    return { system, messages: anthropicMsgs };
  }

  protected toAnthropicTool(tool: ToolDefinition): Tool {
    return {
      name: tool.name,
      description: tool.description,
      input_schema: tool.inputSchema as Tool.InputSchema,
    };
  }

  protected toAnthropicRequestBody(
    modelName: string,
    request: GenerateRequest<typeof AnthropicConfigSchema>,
    stream?: boolean,
    cacheSystemPrompt?: boolean
  ): MessageCreateParams {
    // Use supported model ref if available for version mapping, otherwise use modelName directly
    const model = SUPPORTED_CLAUDE_MODELS[modelName];
    const { system, messages } = this.toAnthropicMessages(request.messages);
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
      tools: request.tools?.map((tool) => this.toAnthropicTool(tool)),
      max_tokens:
        request.config?.maxOutputTokens ?? this.DEFAULT_MAX_OUTPUT_TOKENS,
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

  protected createMessage(
    body: MessageCreateParams,
    abortSignal: AbortSignal
  ): Promise<Message> {
    return this.client.messages.create(body, {
      signal: abortSignal,
    }) as Promise<Message>;
  }

  protected streamMessages(
    body: MessageCreateParams,
    abortSignal: AbortSignal
  ): MessageStreamLike<Message, MessageStreamEvent> {
    return this.client.messages.stream(body, {
      signal: abortSignal,
    }) as MessageStream;
  }

  protected toGenkitResponse(message: Message): GenerateResponseData {
    return this.fromAnthropicResponse(message);
  }

  protected toGenkitPart(event: MessageStreamEvent): Part | undefined {
    return this.fromAnthropicContentBlockChunk(event);
  }
}

type BetaToolUseLike =
  | BetaToolUseBlock
  | BetaServerToolUseBlock
  | BetaMCPToolUseBlock;

export class BetaRunner extends Runner<
  BetaMessage,
  BetaRawMessageStreamEvent,
  BetaMessageCreateParams
> {
  constructor(name: string, client: Anthropic, cacheSystemPrompt?: boolean) {
    super(name, client, cacheSystemPrompt);
  }

  protected toAnthropicRole(
    role: Role,
    toolMessageType?: 'tool_use' | 'tool_result'
  ): 'user' | 'assistant' {
    if (role === 'user') {
      return 'user';
    }
    if (role === 'model') {
      return 'assistant';
    }
    if (role === 'tool') {
      return toolMessageType === 'tool_use' ? 'assistant' : 'user';
    }
    throw new Error(`Unsupported genkit role: ${role}`);
  }

  protected toAnthropicToolResponseContent(
    part: Part
  ):
    | BetaTextBlockParam
    | BetaImageBlockParam
    | BetaRequestDocumentBlock
    | BetaSearchResultBlockParam {
    const output = part.toolResponse?.output ?? {};

    // Handle Media objects (images returned by tools)
    if (this.isMediaObject(output)) {
      const { data, contentType } =
        this.extractDataFromBase64Url(output.url) ?? {};
      if (data && contentType && isMediaType(contentType)) {
        return {
          type: 'image',
          source: {
            type: 'base64',
            data,
            media_type: contentType,
          },
        } as BetaImageBlockParam;
      }
    }

    // Handle string outputs - check if it's a data URL
    if (typeof output === 'string') {
      // Check if string is a data URL (e.g., "data:image/gif;base64,...")
      if (this.isDataUrl(output)) {
        const { data, contentType } =
          this.extractDataFromBase64Url(output) ?? {};
        if (data && contentType && isMediaType(contentType)) {
          return {
            type: 'image',
            source: {
              type: 'base64',
              data,
              media_type: contentType,
            },
          } as BetaImageBlockParam;
        }
      }
      // Regular string output
      return {
        type: 'text',
        text: output,
      } as BetaTextBlockParam;
    }

    // Handle other outputs by stringifying
    return {
      type: 'text',
      text: JSON.stringify(output),
    } as BetaTextBlockParam;
  }

  protected toAnthropicMessageContent(part: Part): BetaContentBlockParam {
    if (part.text) {
      return {
        type: 'text',
        text: part.text,
      };
    }
    if (part.media) {
      const resolvedContentType = part.media.contentType;

      // Check if this is a PDF document
      if (resolvedContentType === 'application/pdf') {
        const url = part.media.url;

        if (this.isDataUrl(url)) {
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
          // File URL (HTTP/HTTPS/other)
          return {
            type: 'document',
            source: {
              type: 'url',
              url: url,
            },
          };
        }
      }

      // Handle non-PDF media (images)
      const { data, contentType } =
        this.extractDataFromBase64Url(part.media.url) ?? {};
      if (!data || !contentType) {
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
      if (!isMediaType(resolvedMediaType)) {
        throw new Error(`Unsupported media type: ${resolvedMediaType}`);
      }
      const mediaTypeValue: MediaType = resolvedMediaType;

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
      const betaResult: BetaToolResultBlockParam = {
        type: 'tool_result',
        tool_use_id: part.toolResponse.ref,
        content: [this.toAnthropicToolResponseContent(part)],
      };
      return betaResult;
    }
    throw new Error(
      `Unsupported genkit part fields encountered for current message role: ${JSON.stringify(
        part
      )}.`
    );
  }

  protected toAnthropicMessages(messages: MessageData[]): {
    system?: string;
    messages: BetaMessageParam[];
  } {
    const system =
      messages[0]?.role === 'system'
        ? messages[0].content?.[0]?.text
        : undefined;
    const messagesToIterate = system ? messages.slice(1) : messages;
    const anthropicMsgs: BetaMessageParam[] = [];
    for (const message of messagesToIterate) {
      const msg = new GenkitMessage(message);
      const content = msg.content.map((part) =>
        this.toAnthropicMessageContent(part)
      );
      const toolMessageType = content.find(
        (c) => c.type === 'tool_use' || c.type === 'tool_result'
      );
      const role = this.toAnthropicRole(
        message.role,
        toolMessageType?.type as 'tool_use' | 'tool_result' | undefined
      );
      anthropicMsgs.push({
        role: role,
        content,
      });
    }
    return { system, messages: anthropicMsgs };
  }

  protected toAnthropicTool(tool: ToolDefinition): any {
    return {
      name: tool.name,
      description: tool.description,
      input_schema: tool.inputSchema as Tool.InputSchema,
    };
  }

  protected createMessage(
    body: BetaMessageCreateParams,
    abortSignal: AbortSignal
  ): Promise<BetaMessage> {
    return this.client.beta.messages.create(body, {
      signal: abortSignal,
    }) as Promise<BetaMessage>;
  }

  protected streamMessages(
    body: BetaMessageCreateParams,
    abortSignal: AbortSignal
  ): MessageStreamLike<BetaMessage, BetaRawMessageStreamEvent> {
    return this.client.beta.messages.stream(body, {
      signal: abortSignal,
    }) as BetaMessageStream;
  }

  protected toAnthropicRequestBody(
    modelName: string,
    request: GenerateRequest<typeof AnthropicConfigSchema>,
    stream?: boolean,
    cacheSystemPrompt?: boolean
  ): BetaMessageCreateParams {
    // Use supported model ref if available for version mapping, otherwise use modelName directly
    const model = SUPPORTED_CLAUDE_MODELS[modelName];
    const { system, messages } = this.toAnthropicMessages(request.messages);
    const mappedModelName =
      request.config?.version ?? model?.version ?? modelName;

    // Convert system to beta format with cache control if needed
    const betaSystem =
      system === undefined
        ? undefined
        : cacheSystemPrompt
          ? [
              {
                type: 'text' as const,
                text: system,
                cache_control: { type: 'ephemeral' as const },
              },
            ]
          : system;

    const body: BetaMessageCreateParams = {
      model: mappedModelName,
      max_tokens:
        request.config?.maxOutputTokens ?? this.DEFAULT_MAX_OUTPUT_TOKENS,
      messages: messages,
    };

    if (betaSystem !== undefined) {
      body.system = betaSystem;
    }
    if (stream !== undefined) {
      body.stream = stream as false;
    }
    if (request.config?.stopSequences !== undefined) {
      body.stop_sequences = request.config.stopSequences;
    }
    if (request.config?.temperature !== undefined) {
      body.temperature = request.config.temperature;
    }
    if (request.config?.topK !== undefined) {
      body.top_k = request.config.topK;
    }
    if (request.config?.topP !== undefined) {
      body.top_p = request.config.topP;
    }
    if (request.config?.tool_choice !== undefined) {
      body.tool_choice = request.config
        .tool_choice as BetaMessageCreateParams['tool_choice'];
    }
    if (request.config?.metadata !== undefined) {
      body.metadata = request.config
        .metadata as BetaMessageCreateParams['metadata'];
    }
    if (request.tools) {
      body.tools = request.tools.map((tool) => this.toAnthropicTool(tool));
    }

    if (request.output?.format && request.output.format !== 'text') {
      throw new Error(
        `Only text output format is supported for Claude models currently`
      );
    }

    return body;
  }

  protected toGenkitResponse(message: BetaMessage): GenerateResponseData {
    return {
      candidates: [
        {
          index: 0,
          finishReason: this.fromBetaStopReason(message.stop_reason),
          message: {
            role: 'model',
            content: message.content.map((block) =>
              this.fromBetaContentBlock(block)
            ),
          },
        },
      ],
      usage: {
        inputTokens: message.usage.input_tokens,
        outputTokens: message.usage.output_tokens,
      },
      custom: message,
    };
  }

  protected toGenkitPart(event: BetaRawMessageStreamEvent): Part | undefined {
    if (event.type === 'content_block_start') {
      return this.fromBetaContentBlock(event.content_block);
    }
    if (event.type === 'content_block_delta') {
      if (event.delta.type === 'text_delta') {
        return { text: event.delta.text };
      }
      if (event.delta.type === 'thinking_delta') {
        return { text: event.delta.thinking };
      }
      return undefined;
    }
    return undefined;
  }

  private fromBetaContentBlock(contentBlock: BetaContentBlock): Part {
    switch (contentBlock.type) {
      case 'tool_use':
      case 'server_tool_use':
      case 'mcp_tool_use':
        return {
          toolRequest: {
            ref: contentBlock.id,
            name: this.betaToolName(contentBlock),
            input: contentBlock.input,
          },
        };
      case 'text':
        return { text: contentBlock.text };
      case 'thinking':
        return { text: contentBlock.thinking };
      case 'redacted_thinking':
        return { text: contentBlock.data };
      default: {
        const unknownType = (contentBlock as { type: string }).type;
        console.warn(
          `Unexpected Anthropic beta content block type: ${unknownType}. Returning empty text. Content block: ${JSON.stringify(contentBlock)}`
        );
        return { text: '' };
      }
    }
  }

  private betaToolName(block: BetaToolUseLike): string {
    if ('server_name' in block && block.server_name) {
      return `${block.server_name}/${block.name}`;
    }
    return block.name ?? 'unknown_tool';
  }

  private fromBetaStopReason(
    reason: BetaStopReason | null
  ): ModelResponseData['finishReason'] {
    switch (reason) {
      case 'max_tokens':
      case 'model_context_window_exceeded':
        return 'length';
      case 'end_turn':
      case 'stop_sequence':
      case 'tool_use':
      case 'pause_turn':
        return 'stop';
      case null:
        return 'unknown';
      case 'refusal':
        return 'other';
      default:
        return 'other';
    }
  }
}
