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

import { MessageStream } from '@anthropic-ai/sdk/lib/MessageStream.js';
import type {
  CitationsDelta,
  ContentBlock,
  DocumentBlockParam,
  ImageBlockParam,
  Message,
  MessageCreateParams,
  MessageCreateParamsNonStreaming,
  MessageCreateParamsStreaming,
  MessageParam,
  MessageStreamEvent,
  RedactedThinkingBlockParam,
  TextBlock,
  TextBlockParam,
  TextCitation,
  ThinkingBlockParam,
  Tool,
  ToolResultBlockParam,
  ToolUseBlockParam,
} from '@anthropic-ai/sdk/resources/messages';
import type {
  GenerateRequest,
  GenerateResponseData,
  ModelResponseData,
  Part,
} from 'genkit';
import { logger } from 'genkit/logging';

import { KNOWN_CLAUDE_MODELS, extractVersion } from '../models.js';
import {
  AnthropicConfigSchema,
  type AnthropicCitation,
  type AnthropicDocumentOptions,
  type ClaudeRunnerParams,
} from '../types.js';
import { removeUndefinedProperties } from '../utils.js';
import { BaseRunner } from './base.js';
import { RunnerTypes as BaseRunnerTypes } from './types.js';

interface RunnerTypes extends BaseRunnerTypes {
  Message: Message;
  Stream: MessageStream;
  StreamEvent: MessageStreamEvent;
  RequestBody: MessageCreateParamsNonStreaming;
  StreamingRequestBody: MessageCreateParamsStreaming;
  Tool: Tool;
  MessageParam: MessageParam;
  ToolResponseContent: TextBlockParam | ImageBlockParam;
  ContentBlockParam:
    | TextBlockParam
    | ImageBlockParam
    | DocumentBlockParam
    | ToolUseBlockParam
    | ToolResultBlockParam
    | ThinkingBlockParam
    | RedactedThinkingBlockParam;
}

export class Runner extends BaseRunner<RunnerTypes> {
  constructor(params: ClaudeRunnerParams) {
    super(params);
  }

  protected toAnthropicMessageContent(
    part: Part
  ):
    | TextBlockParam
    | ImageBlockParam
    | DocumentBlockParam
    | ToolUseBlockParam
    | ToolResultBlockParam
    | ThinkingBlockParam
    | RedactedThinkingBlockParam {
    if (part.reasoning) {
      const signature = this.getThinkingSignature(part);
      if (!signature) {
        throw new Error(
          'Anthropic thinking parts require a signature when sending back to the API. Preserve the `custom.anthropicThinking.signature` value from the original response.'
        );
      }
      return {
        type: 'thinking',
        thinking: part.reasoning,
        signature,
      };
    }

    const redactedThinking = this.getRedactedThinkingData(part);
    if (redactedThinking !== undefined) {
      return {
        type: 'redacted_thinking',
        data: redactedThinking,
      };
    }

    // Custom document (for citations support)
    if (part.custom?.anthropicDocument) {
      return this.toAnthropicDocumentBlock(
        part.custom.anthropicDocument as AnthropicDocumentOptions
      );
    }

    if (part.text) {
      return {
        type: 'text',
        text: part.text,
        citations: null,
      };
    }

    if (part.media) {
      if (part.media.contentType === 'application/pdf') {
        return {
          type: 'document',
          source: this.toPdfDocumentSource(part.media),
        };
      }

      const source = this.toImageSource(part.media);
      if (source.kind === 'base64') {
        return {
          type: 'image',
          source: {
            type: 'base64',
            data: source.data,
            media_type: source.mediaType,
          },
        };
      }
      return {
        type: 'image',
        source: {
          type: 'url',
          url: source.url,
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

  protected toAnthropicRequestBody(
    modelName: string,
    request: GenerateRequest<typeof AnthropicConfigSchema>,
    cacheSystemPrompt?: boolean
  ): MessageCreateParamsNonStreaming {
    if (request.output?.format && request.output.format !== 'text') {
      throw new Error(
        `Only text output format is supported for Claude models currently`
      );
    }

    const model = KNOWN_CLAUDE_MODELS[modelName];
    const { system, messages } = this.toAnthropicMessages(request.messages);
    const mappedModelName =
      request.config?.version ?? extractVersion(model, modelName);

    const systemValue =
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

    const thinkingConfig = this.toAnthropicThinkingConfig(
      request.config?.thinking
    ) as MessageCreateParams['thinking'] | undefined;

    // Need to extract topP and topK from request.config to avoid duplicate properties being added to the body
    // This happens because topP and topK have different property names (top_p and top_k) in the Anthropic API.
    // Thinking is extracted separately to avoid type issues.
    // ApiVersion is extracted separately as it's not a valid property for the Anthropic API.
    const {
      topP,
      topK,
      apiVersion: _1,
      thinking: _2,
      ...restConfig
    } = request.config ?? {};

    const body: MessageCreateParamsNonStreaming = {
      model: mappedModelName,
      max_tokens:
        request.config?.maxOutputTokens ?? this.DEFAULT_MAX_OUTPUT_TOKENS,
      messages,
      system: systemValue,
      stop_sequences: request.config?.stopSequences,
      temperature: request.config?.temperature,
      top_k: topK,
      top_p: topP,
      tool_choice: request.config?.tool_choice,
      metadata: request.config?.metadata,
      tools: request.tools?.map((tool) => this.toAnthropicTool(tool)),
      thinking: thinkingConfig,
      ...restConfig,
    };

    return removeUndefinedProperties(body);
  }

  protected toAnthropicStreamingRequestBody(
    modelName: string,
    request: GenerateRequest<typeof AnthropicConfigSchema>,
    cacheSystemPrompt?: boolean
  ): MessageCreateParamsStreaming {
    if (request.output?.format && request.output.format !== 'text') {
      throw new Error(
        `Only text output format is supported for Claude models currently`
      );
    }

    const model = KNOWN_CLAUDE_MODELS[modelName];
    const { system, messages } = this.toAnthropicMessages(request.messages);
    const mappedModelName =
      request.config?.version ?? extractVersion(model, modelName);

    const systemValue =
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

    const thinkingConfig = this.toAnthropicThinkingConfig(
      request.config?.thinking
    ) as MessageCreateParams['thinking'] | undefined;

    // Need to extract topP and topK from request.config to avoid duplicate properties being added to the body
    // This happens because topP and topK have different property names (top_p and top_k) in the Anthropic API.
    // Thinking is extracted separately to avoid type issues.
    // ApiVersion is extracted separately as it's not a valid property for the Anthropic API.
    const {
      topP,
      topK,
      apiVersion: _1,
      thinking: _2,
      ...restConfig
    } = request.config ?? {};

    const body: MessageCreateParamsStreaming = {
      model: mappedModelName,
      max_tokens:
        request.config?.maxOutputTokens ?? this.DEFAULT_MAX_OUTPUT_TOKENS,
      messages,
      stream: true,
      system: systemValue,
      stop_sequences: request.config?.stopSequences,
      temperature: request.config?.temperature,
      top_k: topK,
      top_p: topP,
      tool_choice: request.config?.tool_choice,
      metadata: request.config?.metadata,
      tools: request.tools?.map((tool) => this.toAnthropicTool(tool)),
      thinking: thinkingConfig,
      ...restConfig,
    };

    return removeUndefinedProperties(body);
  }

  protected async createMessage(
    body: MessageCreateParamsNonStreaming,
    abortSignal: AbortSignal
  ): Promise<Message> {
    return await this.client.messages.create(body, { signal: abortSignal });
  }

  protected streamMessages(
    body: MessageCreateParamsStreaming,
    abortSignal: AbortSignal
  ): MessageStream {
    return this.client.messages.stream(body, { signal: abortSignal });
  }

  protected toGenkitResponse(message: Message): GenerateResponseData {
    return this.fromAnthropicResponse(message);
  }

  protected toGenkitPart(event: MessageStreamEvent): Part | undefined {
    return this.fromAnthropicContentBlockChunk(event);
  }

  protected fromAnthropicContentBlockChunk(
    event: MessageStreamEvent
  ): Part | undefined {
    // Handle content_block_delta events
    if (event.type === 'content_block_delta') {
      const delta = event.delta;

      if (delta.type === 'input_json_delta') {
        throw new Error(
          'Anthropic streaming tool input (input_json_delta) is not yet supported. Please disable streaming or upgrade this plugin.'
        );
      }

      if (delta.type === 'text_delta') {
        return { text: delta.text };
      }

      if (delta.type === 'thinking_delta') {
        return { reasoning: delta.thinking };
      }

      if (delta.type === 'citations_delta') {
        const citationsDelta = delta as CitationsDelta;
        const citation = this.fromAnthropicCitation(citationsDelta.citation);
        if (citation) {
          // Citations are emitted as text parts with empty text and citation data in metadata.
          // Empty text is intentional: genkit's `.text` getter concatenates all text parts,
          // so empty strings contribute nothing to the final text while preserving the citation
          // in the parts array for consumers who need to access citation metadata.
          return {
            text: '',
            metadata: { citations: [citation] },
          };
        }
        return undefined;
      }

      // signature_delta - ignore
      return undefined;
    }

    // Handle content_block_start events
    if (event.type === 'content_block_start') {
      const block = event.content_block;

      switch (block.type) {
        case 'server_tool_use':
          return {
            text: `[Anthropic server tool ${block.name}] input: ${JSON.stringify(block.input)}`,
            custom: {
              anthropicServerToolUse: {
                id: block.id,
                name: block.name,
                input: block.input,
              },
            },
          };

        case 'web_search_tool_result':
          return this.toWebSearchToolResultPart({
            type: block.type,
            toolUseId: block.tool_use_id,
            content: block.content,
          });

        case 'text':
          return { text: block.text };

        case 'thinking':
          return this.createThinkingPart(block.thinking, block.signature);

        case 'redacted_thinking':
          return { custom: { redactedThinking: block.data } };

        case 'tool_use':
          return {
            toolRequest: {
              ref: block.id,
              name: block.name,
              input: block.input,
            },
          };

        default: {
          const unknownType = (block as { type: string }).type;
          logger.warn(
            `Unexpected Anthropic content block type in stream: ${unknownType}. Returning undefined. Content block: ${JSON.stringify(block)}`
          );
          return undefined;
        }
      }
    }

    // Other event types (message_start, message_delta, etc.) - ignore
    return undefined;
  }

  protected fromAnthropicContentBlock(contentBlock: ContentBlock): Part {
    switch (contentBlock.type) {
      case 'server_tool_use':
        return {
          text: `[Anthropic server tool ${contentBlock.name}] input: ${JSON.stringify(contentBlock.input)}`,
          custom: {
            anthropicServerToolUse: {
              id: contentBlock.id,
              name: contentBlock.name,
              input: contentBlock.input,
            },
          },
        };

      case 'web_search_tool_result':
        return this.toWebSearchToolResultPart({
          type: contentBlock.type,
          toolUseId: contentBlock.tool_use_id,
          content: contentBlock.content,
        });

      case 'tool_use':
        return {
          toolRequest: {
            ref: contentBlock.id,
            name: contentBlock.name,
            input: contentBlock.input,
          },
        };

      case 'text': {
        const textBlock = contentBlock as TextBlock;
        if (textBlock.citations && textBlock.citations.length > 0) {
          const citations = textBlock.citations
            .map((c) => this.fromAnthropicCitation(c))
            .filter((c): c is AnthropicCitation => c !== undefined);
          if (citations.length > 0) {
            return {
              text: textBlock.text,
              metadata: { citations },
            };
          }
        }
        return { text: textBlock.text };
      }

      case 'thinking':
        return this.createThinkingPart(
          contentBlock.thinking,
          contentBlock.signature
        );

      case 'redacted_thinking':
        return { custom: { redactedThinking: contentBlock.data } };

      default: {
        const unknownType = (contentBlock as { type: string }).type;
        logger.warn(
          `Unexpected Anthropic content block type: ${unknownType}. Returning empty text. Content block: ${JSON.stringify(contentBlock)}`
        );
        return { text: '' };
      }
    }
  }

  /**
   * Convert AnthropicDocumentOptions to Anthropic's document block format.
   */
  private toAnthropicDocumentBlock(
    options: AnthropicDocumentOptions
  ): DocumentBlockParam {
    const block: DocumentBlockParam = {
      type: 'document',
      source: this.toAnthropicDocumentSource(options.source),
    };

    if (options.title) {
      block.title = options.title;
    }
    if (options.context) {
      block.context = options.context;
    }
    if (options.citations) {
      block.citations = options.citations;
    }

    return block;
  }

  /**
   * Convert document source options to Anthropic's source format.
   * Note: The stable API does not support file-based sources (Files API).
   * Use the beta API for file-based document sources.
   */
  private toAnthropicDocumentSource(
    source: AnthropicDocumentOptions['source']
  ): DocumentBlockParam['source'] {
    switch (source.type) {
      case 'text':
        return {
          type: 'text',
          media_type: (source.mediaType ?? 'text/plain') as 'text/plain',
          data: source.data,
        };
      case 'base64':
        return {
          type: 'base64',
          media_type: source.mediaType as 'application/pdf',
          data: source.data,
        };
      case 'file':
        throw new Error(
          'File-based document sources require the beta API. Set apiVersion: "beta" in your plugin config or request config.'
        );
      case 'content':
        return {
          type: 'content',
          content: source.content.map((item) => {
            if (item.type === 'text') {
              return item;
            }
            // Image content - cast media_type to literal type
            return {
              type: 'image' as const,
              source: {
                type: 'base64' as const,
                media_type: item.source.mediaType as
                  | 'image/jpeg'
                  | 'image/png'
                  | 'image/gif'
                  | 'image/webp',
                data: item.source.data,
              },
            };
          }),
        };
      case 'url':
        return {
          type: 'url',
          url: source.url,
        };
      default:
        throw new Error(
          `Unsupported document source type: ${(source as { type: string }).type}`
        );
    }
  }

  /**
   * Convert Anthropic's citation format (snake_case) to genkit format (camelCase).
   * Only handles document-based citations (char_location, page_location, content_block_location).
   */
  private fromAnthropicCitation(
    citation: TextCitation
  ): AnthropicCitation | undefined {
    switch (citation.type) {
      case 'char_location':
        return {
          type: 'char_location',
          citedText: citation.cited_text,
          documentIndex: citation.document_index,
          documentTitle: citation.document_title ?? undefined,
          startCharIndex: citation.start_char_index,
          endCharIndex: citation.end_char_index,
        };
      case 'page_location':
        return {
          type: 'page_location',
          citedText: citation.cited_text,
          documentIndex: citation.document_index,
          documentTitle: citation.document_title ?? undefined,
          startPageNumber: citation.start_page_number,
          endPageNumber: citation.end_page_number,
        };
      case 'content_block_location':
        return {
          type: 'content_block_location',
          citedText: citation.cited_text,
          documentIndex: citation.document_index,
          documentTitle: citation.document_title ?? undefined,
          startBlockIndex: citation.start_block_index,
          endBlockIndex: citation.end_block_index,
        };
      default:
        // Skip web search and other citation types - they're not from documents
        logger.warn(
          `Skipping unsupported citation type: ${(citation as { type: string }).type}`
        );
        return undefined;
    }
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
}
