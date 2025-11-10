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
import type {
  ContentBlock,
  Message,
  MessageStreamEvent,
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

import {
  AnthropicConfigSchema,
  Media,
  MediaSchema,
  MediaType,
  MediaTypeSchema,
} from '../types.js';

/**
 * Type constraint for runner type parameters.
 */
export type RunnerTypes = {
  Message: unknown;
  Stream: AsyncIterable<unknown> & { finalMessage(): Promise<unknown> };
  StreamEvent: unknown;
  RequestBody: unknown;
  Tool: unknown;
  MessageParam: unknown;
  ToolResponseContent: unknown;
};

type RunnerMessage<T extends RunnerTypes> = T['Message'];
type RunnerStream<T extends RunnerTypes> = T['Stream'];
type RunnerStreamEvent<T extends RunnerTypes> = T['StreamEvent'];
type RunnerRequestBody<T extends RunnerTypes> = T['RequestBody'];
type RunnerTool<T extends RunnerTypes> = T['Tool'];
type RunnerMessageParam<T extends RunnerTypes> = T['MessageParam'];
type RunnerToolResponseContent<T extends RunnerTypes> =
  T['ToolResponseContent'];

export abstract class BaseRunner<TTypes extends RunnerTypes> {
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

  protected isMediaType(value: string): value is MediaType {
    return MediaTypeSchema.safeParse(value).success;
  }

  protected isMediaObject(obj: unknown): obj is Media {
    return MediaSchema.safeParse(obj).success;
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

  protected toPdfDocumentSource(media: Media):
    | {
        type: 'base64';
        media_type: 'application/pdf';
        data: string;
      }
    | {
        type: 'url';
        url: string;
      } {
    if (media.contentType !== 'application/pdf') {
      throw new Error(
        `PDF contentType mismatch: expected application/pdf, got ${media.contentType}`
      );
    }
    const url = media.url;
    if (this.isDataUrl(url)) {
      const extracted = this.extractDataFromBase64Url(url);
      if (!extracted) {
        throw new Error(
          `Invalid PDF data URL format: ${url.substring(0, 50)}...`
        );
      }
      const { data, contentType } = extracted;
      if (contentType !== 'application/pdf') {
        throw new Error(
          `PDF contentType mismatch: expected application/pdf, got ${contentType}`
        );
      }
      return {
        type: 'base64',
        media_type: 'application/pdf',
        data,
      };
    }
    return {
      type: 'url',
      url,
    };
  }

  protected toImageSource(media: Media): {
    data: string;
    mediaType: MediaType;
  } {
    const extracted = this.extractDataFromBase64Url(media.url);
    const { data, contentType } = extracted ?? {};
    if (!data || !contentType) {
      throw new Error(
        `Invalid genkit part media provided to toAnthropicMessageContent: ${JSON.stringify(
          media
        )}.`
      );
    }
    const resolvedMediaType = media.contentType ?? contentType;
    if (!resolvedMediaType) {
      throw new Error('Media type is required but was not provided');
    }
    if (!this.isMediaType(resolvedMediaType)) {
      throw new Error(`Unsupported media type: ${resolvedMediaType}`);
    }
    return {
      data,
      mediaType: resolvedMediaType,
    };
  }

  /**
   * Converts tool response output to the appropriate Anthropic content format.
   * Handles Media objects, data URLs, strings, and other outputs.
   */
  protected toAnthropicToolResponseContent(
    part: Part
  ): RunnerToolResponseContent<TTypes> {
    const output = part.toolResponse?.output ?? {};

    // Handle Media objects (images returned by tools)
    if (this.isMediaObject(output)) {
      const { data, contentType } =
        this.extractDataFromBase64Url(output.url) ?? {};
      if (data && contentType && this.isMediaType(contentType)) {
        return {
          type: 'image',
          source: {
            type: 'base64',
            data,
            media_type: contentType,
          },
        } as RunnerToolResponseContent<TTypes>;
      }
    }

    // Handle string outputs - check if it's a data URL
    if (typeof output === 'string') {
      // Check if string is a data URL (e.g., "data:image/gif;base64,...")
      if (this.isDataUrl(output)) {
        const { data, contentType } =
          this.extractDataFromBase64Url(output) ?? {};
        if (data && contentType && this.isMediaType(contentType)) {
          return {
            type: 'image',
            source: {
              type: 'base64',
              data,
              media_type: contentType,
            },
          } as RunnerToolResponseContent<TTypes>;
        }
      }
      // Regular string output
      return {
        type: 'text',
        text: output,
      } as RunnerToolResponseContent<TTypes>;
    }

    // Handle other outputs by stringifying
    return {
      type: 'text',
      text: JSON.stringify(output),
    } as RunnerToolResponseContent<TTypes>;
  }

  /**
   * Converts a Genkit Part to the corresponding Anthropic content block.
   * Each runner implements this to return its specific API type.
   */
  protected abstract toAnthropicMessageContent(part: Part): any;

  /**
   * Converts Genkit messages to Anthropic format.
   * Extracts system message and converts remaining messages using the runner's
   * toAnthropicMessageContent implementation.
   */
  protected toAnthropicMessages(messages: MessageData[]): {
    system?: string;
    messages: RunnerMessageParam<TTypes>[];
  } {
    const system =
      messages[0]?.role === 'system'
        ? messages[0].content?.[0]?.text
        : undefined;
    const messagesToIterate = system ? messages.slice(1) : messages;
    const anthropicMsgs: RunnerMessageParam<TTypes>[] = [];
    for (const message of messagesToIterate) {
      const msg = new GenkitMessage(message);
      const content = msg.content.map((part) =>
        this.toAnthropicMessageContent(part)
      );
      const toolMessageType = content.find(
        (c: any) => c.type === 'tool_use' || c.type === 'tool_result'
      );
      const role = this.toAnthropicRole(
        message.role,
        toolMessageType?.type as 'tool_use' | 'tool_result' | undefined
      );
      anthropicMsgs.push({
        role: role,
        content,
      } as RunnerMessageParam<TTypes>);
    }
    return { system, messages: anthropicMsgs };
  }

  /**
   * Converts a Genkit ToolDefinition to an Anthropic Tool object.
   */
  protected toAnthropicTool(tool: ToolDefinition): RunnerTool<TTypes> {
    return {
      name: tool.name,
      description: tool.description,
      input_schema: tool.inputSchema,
    } as RunnerTool<TTypes>;
  }

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
  ): RunnerRequestBody<TTypes>;

  protected abstract createMessage(
    body: RunnerRequestBody<TTypes>,
    abortSignal: AbortSignal
  ):
    | Promise<RunnerMessage<TTypes> | RunnerStream<TTypes>>
    | PromiseLike<RunnerMessage<TTypes> | RunnerStream<TTypes>>;

  protected abstract streamMessages(
    body: RunnerRequestBody<TTypes>,
    abortSignal: AbortSignal
  ): RunnerStream<TTypes>;

  protected abstract toGenkitResponse(
    message: RunnerMessage<TTypes>
  ): GenerateResponseData;

  protected abstract toGenkitPart(
    event: RunnerStreamEvent<TTypes>
  ): Part | undefined;

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
    // Type narrowing: ensure we got a message, not a stream
    if (
      typeof response === 'object' &&
      response !== null &&
      'finalMessage' in response
    ) {
      throw new Error(
        'Unexpected stream returned from non-streaming createMessage request'
      );
    }
    return this.toGenkitResponse(response as RunnerMessage<TTypes>);
  }
}
