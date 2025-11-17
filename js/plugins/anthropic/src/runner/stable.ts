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
  TextBlockParam,
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

import { KNOWN_CLAUDE_MODELS } from '../models.js';
import { AnthropicConfigSchema, type ClaudeRunnerParams } from '../types.js';
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
    const model = KNOWN_CLAUDE_MODELS[modelName];
    const { system, messages } = this.toAnthropicMessages(request.messages);
    const mappedModelName =
      request.config?.version ?? model?.version ?? modelName;

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

    const body: MessageCreateParamsNonStreaming = {
      model: mappedModelName,
      max_tokens:
        request.config?.maxOutputTokens ?? this.DEFAULT_MAX_OUTPUT_TOKENS,
      messages,
    };

    if (systemValue !== undefined) {
      body.system = systemValue;
    }

    if (request.tools) {
      body.tools = request.tools.map((tool) => this.toAnthropicTool(tool));
    }
    if (request.config?.topK !== undefined) {
      body.top_k = request.config.topK;
    }
    if (request.config?.topP !== undefined) {
      body.top_p = request.config.topP;
    }
    if (request.config?.temperature !== undefined) {
      body.temperature = request.config.temperature;
    }
    if (request.config?.stopSequences !== undefined) {
      body.stop_sequences = request.config.stopSequences;
    }
    if (request.config?.metadata !== undefined) {
      body.metadata = request.config.metadata;
    }
    if (request.config?.tool_choice !== undefined) {
      body.tool_choice = request.config.tool_choice;
    }
    const thinkingConfig = this.toAnthropicThinkingConfig(
      request.config?.thinking
    );
    if (thinkingConfig) {
      body.thinking = thinkingConfig as MessageCreateParams['thinking'];
    }

    if (request.output?.format && request.output.format !== 'text') {
      throw new Error(
        `Only text output format is supported for Claude models currently`
      );
    }
    return body;
  }

  protected toAnthropicStreamingRequestBody(
    modelName: string,
    request: GenerateRequest<typeof AnthropicConfigSchema>,
    cacheSystemPrompt?: boolean
  ): MessageCreateParamsStreaming {
    const model = KNOWN_CLAUDE_MODELS[modelName];
    const { system, messages } = this.toAnthropicMessages(request.messages);
    const mappedModelName =
      request.config?.version ?? model?.version ?? modelName;

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

    const body: MessageCreateParamsStreaming = {
      model: mappedModelName,
      max_tokens:
        request.config?.maxOutputTokens ?? this.DEFAULT_MAX_OUTPUT_TOKENS,
      messages,
      stream: true,
    };

    if (systemValue !== undefined) {
      body.system = systemValue;
    }

    if (request.tools) {
      body.tools = request.tools.map((tool) => this.toAnthropicTool(tool));
    }
    if (request.config?.topK !== undefined) {
      body.top_k = request.config.topK;
    }
    if (request.config?.topP !== undefined) {
      body.top_p = request.config.topP;
    }
    if (request.config?.temperature !== undefined) {
      body.temperature = request.config.temperature;
    }
    if (request.config?.stopSequences !== undefined) {
      body.stop_sequences = request.config.stopSequences;
    }
    if (request.config?.metadata !== undefined) {
      body.metadata = request.config.metadata;
    }
    if (request.config?.tool_choice !== undefined) {
      body.tool_choice = request.config.tool_choice;
    }
    const thinkingConfig = this.toAnthropicThinkingConfig(
      request.config?.thinking
    );
    if (thinkingConfig) {
      body.thinking =
        thinkingConfig as MessageCreateParamsStreaming['thinking'];
    }

    if (request.output?.format && request.output.format !== 'text') {
      throw new Error(
        `Only text output format is supported for Claude models currently`
      );
    }
    return body;
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
          console.warn(
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

      case 'text':
        return { text: contentBlock.text };

      case 'thinking':
        return this.createThinkingPart(
          contentBlock.thinking,
          contentBlock.signature
        );

      case 'redacted_thinking':
        return { custom: { redactedThinking: contentBlock.data } };

      default: {
        const unknownType = (contentBlock as { type: string }).type;
        console.warn(
          `Unexpected Anthropic content block type: ${unknownType}. Returning empty text. Content block: ${JSON.stringify(contentBlock)}`
        );
        return { text: '' };
      }
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
