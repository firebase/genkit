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
  Message,
  MessageStreamEvent,
} from '@anthropic-ai/sdk/resources/messages.mjs';
import { mock } from 'node:test';

export interface MockAnthropicClientOptions {
  messageResponse?: Partial<Message>;
  sequentialResponses?: Partial<Message>[]; // For tool calling - multiple responses
  streamChunks?: MessageStreamEvent[];
  modelList?: Array<{ id: string; display_name?: string }>;
  shouldError?: Error;
  streamErrorAfterChunk?: number; // Throw error after this many chunks
  streamError?: Error; // Error to throw during streaming
  abortSignal?: AbortSignal; // Abort signal to check
}

/**
 * Creates a mock Anthropic client for testing
 */
export function createMockAnthropicClient(
  options: MockAnthropicClientOptions = {}
): Anthropic {
  const messageResponse = {
    ...mockDefaultMessage(),
    ...options.messageResponse,
  };

  // Support sequential responses for tool calling workflows
  let callCount = 0;
  const createStub = options.shouldError
    ? mock.fn(async () => {
        throw options.shouldError;
      })
    : options.sequentialResponses
      ? mock.fn(async () => {
          const response =
            options.sequentialResponses![callCount] || messageResponse;
          callCount++;
          return {
            ...mockDefaultMessage(),
            ...response,
          };
        })
      : mock.fn(async () => messageResponse);

  const streamStub = options.shouldError
    ? mock.fn(() => {
        throw options.shouldError;
      })
    : mock.fn((body: any, opts?: { signal?: AbortSignal }) => {
        // Check abort signal before starting stream
        if (opts?.signal?.aborted) {
          throw new Error('AbortError');
        }
        return createMockStream(
          options.streamChunks || [],
          messageResponse as Message,
          options.streamErrorAfterChunk,
          options.streamError,
          opts?.signal
        );
      });

  const listStub = options.shouldError
    ? mock.fn(async () => {
        throw options.shouldError;
      })
    : mock.fn(async () => ({
        data: options.modelList || mockDefaultModels(),
      }));

  return {
    messages: {
      create: createStub,
      stream: streamStub,
    },
    models: {
      list: listStub,
    },
  } as unknown as Anthropic;
}

/**
 * Creates a mock async iterable stream for streaming responses
 */
function createMockStream(
  chunks: MessageStreamEvent[],
  finalMsg: Message,
  errorAfterChunk?: number,
  streamError?: Error,
  abortSignal?: AbortSignal
) {
  let index = 0;
  return {
    [Symbol.asyncIterator]() {
      return {
        async next() {
          // Check abort signal
          if (abortSignal?.aborted) {
            const error = new Error('AbortError');
            error.name = 'AbortError';
            throw error;
          }

          // Check if we should throw an error after this chunk
          if (
            errorAfterChunk !== undefined &&
            streamError &&
            index >= errorAfterChunk
          ) {
            throw streamError;
          }

          if (index < chunks.length) {
            return { value: chunks[index++], done: false };
          }
          return { value: undefined, done: true };
        },
      };
    },
    async finalMessage() {
      // Check abort signal before returning final message
      if (abortSignal?.aborted) {
        const error = new Error('AbortError');
        error.name = 'AbortError';
        throw error;
      }
      return finalMsg;
    },
  };
}

export interface CreateMockAnthropicMessageOptions {
  id?: string;
  text?: string;
  toolUse?: {
    id?: string;
    name: string;
    input: any;
  };
  stopReason?: Message['stop_reason'];
  usage?: {
    input_tokens?: number;
    output_tokens?: number;
    cache_creation_input_tokens?: number;
    cache_read_input_tokens?: number;
  };
}

/**
 * Creates a customizable mock Anthropic Message response
 *
 * @example
 * // Simple text response
 * createMockAnthropicMessage({ text: 'Hi there!' })
 *
 * // Tool use response
 * createMockAnthropicMessage({
 *   toolUse: { name: 'get_weather', input: { city: 'NYC' } }
 * })
 *
 * // Custom usage
 * createMockAnthropicMessage({ usage: { input_tokens: 5, output_tokens: 15 } })
 */
export function createMockAnthropicMessage(
  options: CreateMockAnthropicMessageOptions = {}
): Message {
  const content: Message['content'] = [];

  if (options.toolUse) {
    content.push({
      type: 'tool_use',
      id: options.toolUse.id || 'toolu_test123',
      name: options.toolUse.name,
      input: options.toolUse.input,
    });
  } else {
    content.push({
      type: 'text',
      text: options.text || 'Hello! How can I help you today?',
      citations: null,
    });
  }

  return {
    id: options.id || 'msg_test123',
    type: 'message',
    role: 'assistant',
    model: 'claude-3-5-sonnet-20241022',
    content,
    stop_reason:
      options.stopReason || (options.toolUse ? 'tool_use' : 'end_turn'),
    stop_sequence: null,
    usage: {
      input_tokens: options.usage?.input_tokens ?? 10,
      output_tokens: options.usage?.output_tokens ?? 20,
      cache_creation_input_tokens:
        options.usage?.cache_creation_input_tokens ?? 0,
      cache_read_input_tokens: options.usage?.cache_read_input_tokens ?? 0,
    },
  };
}

/**
 * Creates a default mock Message response
 */
export function mockDefaultMessage(): Message {
  return createMockAnthropicMessage();
}

/**
 * Creates a mock text content block chunk event
 */
export function mockTextChunk(text: string): MessageStreamEvent {
  return {
    type: 'content_block_delta',
    index: 0,
    delta: {
      type: 'text_delta',
      text,
    },
  } as MessageStreamEvent;
}

/**
 * Creates a mock content block start event with text
 */
export function mockContentBlockStart(text: string): MessageStreamEvent {
  return {
    type: 'content_block_start',
    index: 0,
    content_block: {
      type: 'text',
      text,
    },
  } as MessageStreamEvent;
}

/**
 * Creates a mock tool use content block
 */
export function mockToolUseChunk(
  id: string,
  name: string,
  input: any
): MessageStreamEvent {
  return {
    type: 'content_block_start',
    index: 0,
    content_block: {
      type: 'tool_use',
      id,
      name,
      input,
    },
  } as MessageStreamEvent;
}

/**
 * Creates a default list of mock models
 */
export function mockDefaultModels() {
  return [
    { id: 'claude-3-5-sonnet-20241022', display_name: 'Claude 3.5 Sonnet' },
    { id: 'claude-3-5-haiku-20241022', display_name: 'Claude 3.5 Haiku' },
    { id: 'claude-3-opus-20240229', display_name: 'Claude 3 Opus' },
  ];
}

/**
 * Creates a mock Message with tool use
 */
export function mockMessageWithToolUse(
  toolName: string,
  toolInput: any
): Partial<Message> {
  return {
    content: [
      {
        type: 'tool_use',
        id: 'toolu_test123',
        name: toolName,
        input: toolInput,
      },
    ],
    stop_reason: 'tool_use',
  };
}

/**
 * Creates a mock Message with custom content
 */
export function mockMessageWithContent(
  content: Message['content']
): Partial<Message> {
  return {
    content,
    stop_reason: 'end_turn',
  };
}
