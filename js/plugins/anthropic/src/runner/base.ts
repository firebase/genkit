/**
 * Original work Copyright 2024 Bloom Labs Inc
 * Modifications Copyright 2025 Google LLC
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
import type { DocumentBlockParam } from '@anthropic-ai/sdk/resources/messages';
import type {
  GenerateRequest,
  GenerateResponseChunkData,
  GenerateResponseData,
  MessageData,
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
  type ClaudeRunnerParams,
} from '../types.js';

import {
  RunnerContentBlockParam,
  RunnerMessage,
  RunnerMessageParam,
  RunnerRequestBody,
  RunnerStream,
  RunnerStreamEvent,
  RunnerStreamingRequestBody,
  RunnerTool,
  RunnerToolResponseContent,
  RunnerTypes,
} from './types.js';

export abstract class BaseRunner<ApiTypes extends RunnerTypes> {
  protected name: string;
  protected client: Anthropic;
  protected cacheSystemPrompt?: boolean;

  /**
   * Default maximum output tokens for Claude models when not specified in the request.
   */
  protected readonly DEFAULT_MAX_OUTPUT_TOKENS = 4096;

  constructor(params: ClaudeRunnerParams) {
    this.name = params.name;
    this.client = params.client;
    this.cacheSystemPrompt = params.cacheSystemPrompt;
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
   * Both the stable and beta Anthropic SDKs accept the same JSON shape for PDF
   * document sources (either `type: 'base64'` with a base64 payload or `type: 'url'`
   * with a public URL). Even though the return type references the stable SDK
   * union, TypeScript’s structural typing lets the beta runner reuse this helper.
   */
  protected toPdfDocumentSource(media: Media): DocumentBlockParam['source'] {
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
  ): RunnerToolResponseContent<ApiTypes> {
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
        };
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

  /**
   * Converts a Genkit Part to the corresponding Anthropic content block.
   * Each runner implements this to return its specific API type.
   */
  protected abstract toAnthropicMessageContent(
    part: Part
  ): RunnerContentBlockParam<ApiTypes>;

  /**
   * Converts Genkit messages to Anthropic format.
   * Extracts system message and converts remaining messages using the runner's
   * toAnthropicMessageContent implementation.
   */
  protected toAnthropicMessages(messages: MessageData[]): {
    system?: string;
    messages: RunnerMessageParam<ApiTypes>[];
  } {
    const system =
      messages[0]?.role === 'system'
        ? messages[0].content?.[0]?.text
        : undefined;

    const messagesToIterate = system ? messages.slice(1) : messages;
    const anthropicMsgs: RunnerMessageParam<ApiTypes>[] = [];

    for (const message of messagesToIterate) {
      const msg = new GenkitMessage(message);

      // Detect tool message kind from Genkit Parts (no SDK typing needed)
      const hadToolUse = msg.content.some((p) => !!p.toolRequest);
      const hadToolResult = msg.content.some((p) => !!p.toolResponse);

      const toolMessageType = hadToolUse
        ? ('tool_use' as const)
        : hadToolResult
          ? ('tool_result' as const)
          : undefined;

      const role = this.toAnthropicRole(message.role, toolMessageType);

      const content = msg.content.map((part) =>
        this.toAnthropicMessageContent(part)
      );

      anthropicMsgs.push({ role, content });
    }

    return { system, messages: anthropicMsgs };
  }

  /**
   * Converts a Genkit ToolDefinition to an Anthropic Tool object.
   */
  protected toAnthropicTool(tool: ToolDefinition): RunnerTool<ApiTypes> {
    return {
      name: tool.name,
      description: tool.description,
      input_schema: tool.inputSchema,
    } as RunnerTool<ApiTypes>;
  }

  /**
   * Converts an Anthropic request to a non-streaming Anthropic API request body.
   * @param modelName The name of the Anthropic model to use.
   * @param request The Genkit GenerateRequest to convert.
   * @param cacheSystemPrompt Whether to cache the system prompt.
   * @returns The converted Anthropic API non-streaming request body.
   * @throws An error if an unsupported output format is requested.
   */
  protected abstract toAnthropicRequestBody(
    modelName: string,
    request: GenerateRequest<typeof AnthropicConfigSchema>,
    cacheSystemPrompt?: boolean
  ): RunnerRequestBody<ApiTypes>;

  /**
   * Converts an Anthropic request to a streaming Anthropic API request body.
   * @param modelName The name of the Anthropic model to use.
   * @param request The Genkit GenerateRequest to convert.
   * @param cacheSystemPrompt Whether to cache the system prompt.
   * @returns The converted Anthropic API streaming request body.
   * @throws An error if an unsupported output format is requested.
   */
  protected abstract toAnthropicStreamingRequestBody(
    modelName: string,
    request: GenerateRequest<typeof AnthropicConfigSchema>,
    cacheSystemPrompt?: boolean
  ): RunnerStreamingRequestBody<ApiTypes>;

  protected abstract createMessage(
    body: RunnerRequestBody<ApiTypes>,
    abortSignal: AbortSignal
  ): Promise<RunnerMessage<ApiTypes>>;

  protected abstract streamMessages(
    body: RunnerStreamingRequestBody<ApiTypes>,
    abortSignal: AbortSignal
  ): RunnerStream<ApiTypes>;

  protected abstract toGenkitResponse(
    message: RunnerMessage<ApiTypes>
  ): GenerateResponseData;

  protected abstract toGenkitPart(
    event: RunnerStreamEvent<ApiTypes>
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

    if (streamingRequested) {
      const body = this.toAnthropicStreamingRequestBody(
        this.name,
        request,
        this.cacheSystemPrompt
      );
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

    const body = this.toAnthropicRequestBody(
      this.name,
      request,
      this.cacheSystemPrompt
    );
    const response = await this.createMessage(body, abortSignal);
    return this.toGenkitResponse(response);
  }
}
