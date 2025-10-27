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

import type { Message } from '@anthropic-ai/sdk/resources/messages.mjs';
import { mock } from 'node:test';

export interface SetupAnthropicMockOptions {
  messageResponse?: Partial<Message>;
}

export interface MockAnthropicClient {
  messages: {
    create: any;
    stream: any;
  };
  models: {
    list: any;
  };
}

export interface SetupAnthropicMockResult {
  mockClient: MockAnthropicClient;
  mockResponse: Message;
}

/**
 * Sets up mocking for the Anthropic SDK module.
 * Must be called at the module level (before describe blocks).
 *
 * @param options - Configuration for mock responses
 * @returns Mock client and response for assertions
 *
 * @example
 * ```typescript
 * import { setupAnthropicMock } from './mocks/setup-anthropic-mock.js';
 *
 * const { mockClient } = setupAnthropicMock({
 *   messageResponse: { content: [{ type: 'text', text: 'Custom response' }] }
 * });
 *
 * describe('My Test Suite', () => {
 *   // tests here
 * });
 * ```
 */
export function setupAnthropicMock(
  options: SetupAnthropicMockOptions = {}
): SetupAnthropicMockResult {
  const mockResponse: Message = {
    id: 'msg_test123',
    type: 'message',
    role: 'assistant',
    model: 'claude-3-5-sonnet-20241022',
    content: [
      {
        type: 'text',
        text: 'Hello! How can I help you today?',
        citations: null,
      },
    ],
    stop_reason: 'end_turn',
    stop_sequence: null,
    usage: {
      input_tokens: 10,
      output_tokens: 20,
      cache_creation_input_tokens: 0,
      cache_read_input_tokens: 0,
    },
    ...options.messageResponse,
  };

  const mockClient = {
    messages: {
      create: mock.fn(async () => mockResponse),
      stream: mock.fn(),
    },
    models: {
      list: mock.fn(),
    },
  };

  const MockAnthropic = function (this: any, opts: any) {
    return mockClient;
  } as any;

  mock.module('@anthropic-ai/sdk', {
    defaultExport: MockAnthropic,
  });

  return { mockClient, mockResponse };
}
