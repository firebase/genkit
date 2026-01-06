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

import { BetaMessageStream } from '@anthropic-ai/sdk/lib/BetaMessageStream.js';
import type {
  BetaContentBlock,
  BetaImageBlockParam,
  BetaMessage,
  MessageCreateParams as BetaMessageCreateParams,
  MessageCreateParamsNonStreaming as BetaMessageCreateParamsNonStreaming,
  MessageCreateParamsStreaming as BetaMessageCreateParamsStreaming,
  BetaMessageParam,
  BetaRawMessageStreamEvent,
  BetaRedactedThinkingBlockParam,
  BetaRequestDocumentBlock,
  BetaStopReason,
  BetaTextBlockParam,
  BetaThinkingBlockParam,
  BetaTool,
  BetaToolResultBlockParam,
  BetaToolUseBlockParam,
} from '@anthropic-ai/sdk/resources/beta/messages';

import type {
  GenerateRequest,
  GenerateResponseData,
  ModelResponseData,
  Part,
} from 'genkit';
import { logger } from 'genkit/logging';

import { KNOWN_CLAUDE_MODELS, extractVersion } from '../models.js';
import { AnthropicConfigSchema, type ClaudeRunnerParams } from '../types.js';
import { removeUndefinedProperties } from '../utils.js';
import { BaseRunner } from './base.js';
import { RunnerTypes } from './types.js';
import {
  redactedThinkingBlockToPart,
  textBlockToPart,
  thinkingBlockToPart,
  toolUseBlockToPart,
  webSearchToolResultBlockToPart,
} from './utils.js';

/**
 * Server-managed tool blocks emitted by the beta API that Genkit cannot yet
 * interpret. We fail fast on these so callers do not accidentally treat them as
 * locally executable tool invocations.
 */
/**
 * Server tool types that exist in beta but are not yet supported.
 * Note: server_tool_use and web_search_tool_result ARE supported (same as stable API).
 */
const BETA_UNSUPPORTED_SERVER_TOOL_BLOCK_TYPES = new Set<string>([
  'web_fetch_tool_result',
  'code_execution_tool_result',
  'bash_code_execution_tool_result',
  'text_editor_code_execution_tool_result',
  'mcp_tool_result',
  'mcp_tool_use',
  'container_upload',
]);

function unsupportedServerToolError(blockType: string): string {
  return `Anthropic beta runner does not yet support server-managed tool block '${blockType}'. Please retry against the stable API or wait for dedicated support.`;
}

const BETA_APIS = [
  // 'message-batches-2024-09-24',
  // 'prompt-caching-2024-07-31',
  // 'computer-use-2025-01-24',
  // 'pdfs-2024-09-25',
  // 'token-counting-2024-11-01',
  // 'token-efficient-tools-2025-02-19',
  // 'output-128k-2025-02-19',
  'files-api-2025-04-14',
  // 'mcp-client-2025-04-04',
  // 'dev-full-thinking-2025-05-14',
  // 'interleaved-thinking-2025-05-14',
  // 'code-execution-2025-05-22',
  // 'extended-cache-ttl-2025-04-11',
  // 'context-1m-2025-08-07',
  // 'context-management-2025-06-27',
  // 'model-context-window-exceeded-2025-08-26',
  // 'skills-2025-10-02',
  'effort-2025-11-24',
  // 'advanced-tool-use-2025-11-20',
  'structured-outputs-2025-11-13',
];

/**
 * Transforms a JSON schema to be compatible with Anthropic's structured output requirements.
 * Anthropic requires `additionalProperties: false` on all object types.
 * @see https://docs.anthropic.com/en/docs/build-with-claude/structured-outputs#json-schema-limitations
 */
function toAnthropicSchema(
  schema: Record<string, unknown>
): Record<string, unknown> {
  const out = structuredClone(schema);

  // Remove $schema if present
  delete out.$schema;

  // Add additionalProperties: false to objects
  if (out.type === 'object') {
    out.additionalProperties = false;
  }

  // Recursively process nested objects
  for (const key in out) {
    if (typeof out[key] === 'object' && out[key] !== null) {
      out[key] = toAnthropicSchema(out[key] as Record<string, unknown>);
    }
  }

  return out;
}

/**
 * Converts a beta server_tool_use block to a Genkit Part.
 * Beta API has an optional server_name prefix that stable doesn't have.
 */
function betaServerToolUseBlockToPart(block: {
  id: string;
  name?: string;
  input: unknown;
  server_name?: string;
}): Part {
  const baseName = block.name ?? 'unknown_tool';
  const serverToolName = block.server_name
    ? `${block.server_name}/${baseName}`
    : baseName;
  return {
    text: `[Anthropic server tool ${serverToolName}] input: ${JSON.stringify(block.input)}`,
    custom: {
      anthropicServerToolUse: {
        id: block.id,
        name: serverToolName,
        input: block.input,
      },
    },
  };
}

interface BetaRunnerTypes extends RunnerTypes {
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
    | BetaToolResultBlockParam
    | BetaThinkingBlockParam
    | BetaRedactedThinkingBlockParam;
}

/**
 * Runner for the Anthropic Beta API.
 */
export class BetaRunner extends BaseRunner<BetaRunnerTypes> {
  constructor(params: ClaudeRunnerParams) {
    super(params);
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
    | BetaToolResultBlockParam
    | BetaThinkingBlockParam
    | BetaRedactedThinkingBlockParam {
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

    // Text
    if (part.text) {
      return { type: 'text', text: part.text };
    }

    // Media
    if (part.media) {
      if (part.media.contentType === 'anthropic/file') {
        return {
          type: 'document',
          source: {
            type: 'file',
            file_id: part.media.url,
          },
        };
      }

      if (part.media.contentType === 'anthropic/image') {
        return {
          type: 'image',
          source: {
            type: 'file',
            file_id: part.media.url,
          },
        };
      }

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
      request.config?.version ?? extractVersion(model, modelName);

    let betaSystem: BetaMessageCreateParamsNonStreaming['system'];

    if (system !== undefined) {
      betaSystem = cacheSystemPrompt
        ? [
            {
              type: 'text' as const,
              text: system,
              cache_control: { type: 'ephemeral' as const },
            },
          ]
        : system;
    }

    const thinkingConfig = this.toAnthropicThinkingConfig(
      request.config?.thinking
    ) as BetaMessageCreateParams['thinking'] | undefined;

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

    const body = {
      model: mappedModelName,
      max_tokens:
        request.config?.maxOutputTokens ?? this.DEFAULT_MAX_OUTPUT_TOKENS,
      messages,
      system: betaSystem,
      stop_sequences: request.config?.stopSequences,
      temperature: request.config?.temperature,
      top_k: topK,
      top_p: topP,
      tool_choice: request.config?.tool_choice,
      metadata: request.config?.metadata,
      tools: request.tools?.map((tool) => this.toAnthropicTool(tool)),
      thinking: thinkingConfig,
      output_format: this.isStructuredOutputEnabled(request)
        ? {
            type: 'json_schema',
            schema: toAnthropicSchema(request.output!.schema!),
          }
        : undefined,
      betas: Array.isArray(request.config?.betas)
        ? [...(request.config?.betas ?? [])]
        : [...BETA_APIS],
      ...restConfig,
    } as BetaMessageCreateParamsNonStreaming;

    return removeUndefinedProperties(body);
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
      request.config?.version ?? extractVersion(model, modelName);

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

    const thinkingConfig = this.toAnthropicThinkingConfig(
      request.config?.thinking
    ) as BetaMessageCreateParams['thinking'] | undefined;

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

    const body = {
      model: mappedModelName,
      max_tokens:
        request.config?.maxOutputTokens ?? this.DEFAULT_MAX_OUTPUT_TOKENS,
      messages,
      stream: true,
      system: betaSystem,
      stop_sequences: request.config?.stopSequences,
      temperature: request.config?.temperature,
      top_k: topK,
      top_p: topP,
      tool_choice: request.config?.tool_choice,
      metadata: request.config?.metadata,
      tools: request.tools?.map((tool) => this.toAnthropicTool(tool)),
      thinking: thinkingConfig,
      output_format: this.isStructuredOutputEnabled(request)
        ? {
            type: 'json_schema',
            schema: toAnthropicSchema(request.output!.schema!),
          }
        : undefined,
      betas: Array.isArray(request.config?.betas)
        ? [...(request.config?.betas ?? [])]
        : [...BETA_APIS],
      ...restConfig,
    } as BetaMessageCreateParamsStreaming;

    return removeUndefinedProperties(body);
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
      const blockType = (event.content_block as { type?: string }).type;
      if (
        blockType &&
        BETA_UNSUPPORTED_SERVER_TOOL_BLOCK_TYPES.has(blockType)
      ) {
        throw new Error(unsupportedServerToolError(blockType));
      }
      return this.fromBetaContentBlock(event.content_block);
    }
    if (event.type === 'content_block_delta') {
      if (event.delta.type === 'text_delta') {
        return { text: event.delta.text };
      }
      if (event.delta.type === 'thinking_delta') {
        return { reasoning: event.delta.thinking };
      }
      // server/client tool input_json_delta not supported yet
      return undefined;
    }
    return undefined;
  }

  private fromBetaContentBlock(contentBlock: BetaContentBlock): Part {
    switch (contentBlock.type) {
      case 'tool_use':
        // Beta API may have undefined name, fallback to 'unknown_tool'
        return toolUseBlockToPart({
          id: contentBlock.id,
          name: contentBlock.name ?? 'unknown_tool',
          input: contentBlock.input,
        });

      case 'mcp_tool_use':
        throw new Error(unsupportedServerToolError(contentBlock.type));

      case 'server_tool_use':
        return betaServerToolUseBlockToPart(contentBlock);

      case 'web_search_tool_result':
        return webSearchToolResultBlockToPart(contentBlock);

      case 'text':
        return textBlockToPart(contentBlock);

      case 'thinking':
        return thinkingBlockToPart(contentBlock);

      case 'redacted_thinking':
        return redactedThinkingBlockToPart(contentBlock);

      default: {
        if (BETA_UNSUPPORTED_SERVER_TOOL_BLOCK_TYPES.has(contentBlock.type)) {
          throw new Error(unsupportedServerToolError(contentBlock.type));
        }
        const unknownType = (contentBlock as { type: string }).type;
        logger.warn(
          `Unexpected Anthropic beta content block type: ${unknownType}. Returning empty text. Content block: ${JSON.stringify(
            contentBlock
          )}`
        );
        return { text: '' };
      }
    }
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

  private isStructuredOutputEnabled(
    request: GenerateRequest<typeof AnthropicConfigSchema>
  ): boolean {
    return !!(
      request.output?.schema &&
      request.output.constrained &&
      request.output.format === 'json'
    );
  }
}
