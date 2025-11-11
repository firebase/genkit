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
import { BetaMessageStream } from '@anthropic-ai/sdk/lib/BetaMessageStream.js';
import type {
  BetaContentBlock,
  BetaImageBlockParam,
  BetaMCPToolUseBlock,
  BetaMessage,
  MessageCreateParams as BetaMessageCreateParams,
  MessageCreateParamsNonStreaming as BetaMessageCreateParamsNonStreaming,
  MessageCreateParamsStreaming as BetaMessageCreateParamsStreaming,
  BetaMessageParam,
  BetaRawMessageStreamEvent,
  BetaRequestDocumentBlock,
  BetaServerToolUseBlock,
  BetaStopReason,
  BetaTextBlockParam,
  BetaTool,
  BetaToolResultBlockParam,
  BetaToolUseBlock,
  BetaToolUseBlockParam,
} from '@anthropic-ai/sdk/resources/beta/messages';

import type {
  GenerateRequest,
  GenerateResponseData,
  ModelResponseData,
  Part,
} from 'genkit';

import { KNOWN_CLAUDE_MODELS } from '../models.js';
import { AnthropicConfigSchema } from '../types.js';
import { BaseRunner } from './base.js';

type BetaToolUseLike =
  | BetaToolUseBlock
  | BetaServerToolUseBlock
  | BetaMCPToolUseBlock;

type BetaRunnerTypes = {
  Message: BetaMessage;
  Stream: BetaMessageStream;
  StreamEvent: BetaRawMessageStreamEvent;
  RequestBody: BetaMessageCreateParamsNonStreaming;
  StreamingRequestBody: BetaMessageCreateParamsStreaming;
  Tool: BetaTool;
  MessageParam: BetaMessageParam;
  ToolResponseContent: BetaTextBlockParam | BetaImageBlockParam;
  ContentBlockParam:
    | BetaTextBlockParam
    | BetaImageBlockParam
    | BetaRequestDocumentBlock
    | BetaToolUseBlockParam
    | BetaToolResultBlockParam;
};

/**
 * Runner for the Anthropic Beta API.
 */
export class BetaRunner extends BaseRunner<BetaRunnerTypes> {
  constructor(name: string, client: Anthropic, cacheSystemPrompt?: boolean) {
    super(name, client, cacheSystemPrompt);
  }

  /**
   * Map a Genkit Part -> Anthropic beta content block param.
   * Supports: text, images (base64 data URLs), PDFs (document source),
   * tool_use (client tool request), tool_result (client tool response).
   */
  protected toAnthropicMessageContent(
    part: Part
  ):
    | BetaTextBlockParam
    | BetaImageBlockParam
    | BetaRequestDocumentBlock
    | BetaToolUseBlockParam
    | BetaToolResultBlockParam {
    // Text
    if (part.text) {
      return { type: 'text', text: part.text };
    }

    // Media
    if (part.media) {
      if (part.media.contentType === 'application/pdf') {
        return {
          type: 'document',
          source: this.toPdfDocumentSource(part.media),
        };
      }

      const { data, mediaType } = this.toImageSource(part.media);
      return {
        type: 'image',
        source: {
          type: 'base64',
          data,
          media_type: mediaType,
        },
      };
    }

    // Tool request (client tool use)
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

    // Tool response (client tool result)
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

  protected createMessage(
    body: BetaMessageCreateParamsNonStreaming,
    abortSignal: AbortSignal
  ): Promise<BetaMessage> {
    return this.client.beta.messages.create(body, { signal: abortSignal });
  }

  protected streamMessages(
    body: BetaMessageCreateParamsStreaming,
    abortSignal: AbortSignal
  ): BetaMessageStream {
    return this.client.beta.messages.stream(body, { signal: abortSignal });
  }

  /**
   * Build non-streaming request body.
   */
  protected toAnthropicRequestBody(
    modelName: string,
    request: GenerateRequest<typeof AnthropicConfigSchema>,
    cacheSystemPrompt?: boolean
  ): BetaMessageCreateParamsNonStreaming {
    const model = KNOWN_CLAUDE_MODELS[modelName];
    const { system, messages } = this.toAnthropicMessages(request.messages);
    const mappedModelName =
      request.config?.version ?? model?.version ?? modelName;

    // Convert system: either raw string or cached text block array
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

    const body: BetaMessageCreateParamsNonStreaming = {
      model: mappedModelName,
      max_tokens:
        request.config?.maxOutputTokens ?? this.DEFAULT_MAX_OUTPUT_TOKENS,
      messages,
    };

    if (betaSystem !== undefined) body.system = betaSystem;
    if (request.config?.stopSequences !== undefined)
      body.stop_sequences = request.config.stopSequences;
    if (request.config?.temperature !== undefined)
      body.temperature = request.config.temperature;
    if (request.config?.topK !== undefined) body.top_k = request.config.topK;
    if (request.config?.topP !== undefined) body.top_p = request.config.topP;
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

  /**
   * Build streaming request body.
   */
  protected toAnthropicStreamingRequestBody(
    modelName: string,
    request: GenerateRequest<typeof AnthropicConfigSchema>,
    cacheSystemPrompt?: boolean
  ): BetaMessageCreateParamsStreaming {
    const model = KNOWN_CLAUDE_MODELS[modelName];
    const { system, messages } = this.toAnthropicMessages(request.messages);
    const mappedModelName =
      request.config?.version ?? model?.version ?? modelName;

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

    const body: BetaMessageCreateParamsStreaming = {
      model: mappedModelName,
      max_tokens:
        request.config?.maxOutputTokens ?? this.DEFAULT_MAX_OUTPUT_TOKENS,
      messages,
      stream: true,
    };

    if (betaSystem !== undefined) body.system = betaSystem;
    if (request.config?.stopSequences !== undefined)
      body.stop_sequences = request.config.stopSequences;
    if (request.config?.temperature !== undefined)
      body.temperature = request.config.temperature;
    if (request.config?.topK !== undefined) body.top_k = request.config.topK;
    if (request.config?.topP !== undefined) body.top_p = request.config.topP;
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
      // server/client tool input_json_delta not supported yet
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
          `Unexpected Anthropic beta content block type: ${unknownType}. Returning empty text. Content block: ${JSON.stringify(
            contentBlock
          )}`
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
