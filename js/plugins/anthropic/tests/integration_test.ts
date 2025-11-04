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

import * as assert from 'assert';
import { genkit, z } from 'genkit';
import { describe, it } from 'node:test';
import { anthropic } from '../src/index.js';
import { __testClient } from '../src/types.js';
import {
  createMockAnthropicClient,
  createMockAnthropicMessage,
  mockContentBlockStart,
  mockMessageWithToolUse,
  mockTextChunk,
} from './mocks/anthropic-client.js';

import { PluginOptions } from '../src/types.js';

describe('Anthropic Integration', () => {
  it('should successfully generate a response', async () => {
    const mockClient = createMockAnthropicClient();
    const ai = genkit({
      plugins: [anthropic({ [__testClient]: mockClient } as PluginOptions)],
    });

    const result = await ai.generate({
      model: 'anthropic/claude-3-5-haiku',
      prompt: 'Hello',
    });

    assert.strictEqual(result.text, 'Hello! How can I help you today?');
  });

  it('should handle tool calling workflow (call tool, receive result, generate final response)', async () => {
    const mockClient = createMockAnthropicClient({
      sequentialResponses: [
        // First response: tool use request
        mockMessageWithToolUse('get_weather', { city: 'NYC' }),
        // Second response: final text after tool result
        createMockAnthropicMessage({
          text: 'The weather in NYC is sunny, 72°F',
        }),
      ],
    });

    const ai = genkit({
      plugins: [anthropic({ [__testClient]: mockClient } as PluginOptions)],
    });

    // Define the tool
    ai.defineTool(
      {
        name: 'get_weather',
        description: 'Get the weather for a city',
        inputSchema: z.object({
          city: z.string(),
        }),
      },
      async (input: { city: string }) => {
        return `The weather in ${input.city} is sunny, 72°F`;
      }
    );

    const result = await ai.generate({
      model: 'anthropic/claude-3-5-haiku',
      prompt: 'What is the weather in NYC?',
      tools: ['get_weather'],
    });

    assert.ok(
      result.text.includes('NYC') ||
        result.text.includes('sunny') ||
        result.text.includes('72')
    );
  });

  it('should handle multi-turn conversations', async () => {
    const mockClient = createMockAnthropicClient();
    const ai = genkit({
      plugins: [anthropic({ [__testClient]: mockClient } as PluginOptions)],
    });

    // First turn
    const response1 = await ai.generate({
      model: 'anthropic/claude-3-5-haiku',
      prompt: 'My name is Alice',
    });

    // Second turn with conversation history
    const response2 = await ai.generate({
      model: 'anthropic/claude-3-5-haiku',
      prompt: "What's my name?",
      messages: response1.messages,
    });

    // Verify conversation history is maintained
    assert.ok(
      response2.messages.length >= 2,
      'Should have conversation history'
    );
    assert.strictEqual(response2.messages[0].role, 'user');
    assert.ok(
      response2.messages[0].content[0].text?.includes('Alice') ||
        response2.messages[0].content[0].text?.includes('name')
    );
  });

  it('should stream responses with streaming callback', async () => {
    const mockClient = createMockAnthropicClient({
      streamChunks: [
        mockContentBlockStart('Hello'),
        mockTextChunk(' world'),
        mockTextChunk('!'),
      ],
      messageResponse: {
        content: [{ type: 'text', text: 'Hello world!', citations: null }],
        usage: {
          input_tokens: 5,
          output_tokens: 15,
          cache_creation_input_tokens: 0,
          cache_read_input_tokens: 0,
        },
      },
    });

    const ai = genkit({
      plugins: [anthropic({ [__testClient]: mockClient } as PluginOptions)],
    });

    const chunks: any[] = [];
    const result = await ai.generate({
      model: 'anthropic/claude-3-5-haiku',
      prompt: 'Say hello world',
      streamingCallback: (chunk) => {
        chunks.push(chunk);
      },
    });

    assert.ok(chunks.length > 0, 'Should have received streaming chunks');
    assert.ok(result.text, 'Should have final response text');
  });

  it('should handle media/image inputs', async () => {
    const mockClient = createMockAnthropicClient();
    const ai = genkit({
      plugins: [anthropic({ [__testClient]: mockClient } as PluginOptions)],
    });

    const result = await ai.generate({
      model: 'anthropic/claude-3-5-haiku',
      messages: [
        {
          role: 'user',
          content: [
            { text: 'Describe this image:' },
            {
              media: {
                url: 'data:image/png;base64,R0lGODlhAQABAAAAACw=',
                contentType: 'image/png',
              },
            },
          ],
        },
      ],
    });

    assert.ok(result.text, 'Should generate response for image input');
  });

  it('should propagate API errors correctly', async () => {
    const apiError = new Error('API Error: 401 Unauthorized');
    const mockClient = createMockAnthropicClient({
      shouldError: apiError,
    });

    const ai = genkit({
      plugins: [anthropic({ [__testClient]: mockClient } as PluginOptions)],
    });

    await assert.rejects(
      async () => {
        await ai.generate({
          model: 'anthropic/claude-3-5-haiku',
          prompt: 'Hello',
        });
      },
      (error: Error) => {
        assert.strictEqual(error.message, 'API Error: 401 Unauthorized');
        return true;
      }
    );
  });

  it('should respect abort signals for cancellation', async () => {
    // Note: Detailed abort signal handling is tested in converters_test.ts
    // This test verifies that errors (including abort errors) are properly propagated at the integration layer
    const mockClient = createMockAnthropicClient({
      shouldError: new Error('AbortError'),
    });
    const ai = genkit({
      plugins: [anthropic({ [__testClient]: mockClient } as PluginOptions)],
    });

    await assert.rejects(
      async () => {
        await ai.generate({
          model: 'anthropic/claude-3-5-haiku',
          prompt: 'Hello',
        });
      },
      (error: Error) => {
        // Should propagate the error
        assert.ok(
          error.message.includes('AbortError'),
          'Should propagate errors'
        );
        return true;
      }
    );
  });

  it('should track token usage in responses', async () => {
    const mockClient = createMockAnthropicClient({
      messageResponse: {
        usage: {
          input_tokens: 25,
          output_tokens: 50,
          cache_creation_input_tokens: 5,
          cache_read_input_tokens: 10,
        },
      },
    });

    const ai = genkit({
      plugins: [anthropic({ [__testClient]: mockClient } as PluginOptions)],
    });

    const result = await ai.generate({
      model: 'anthropic/claude-3-5-haiku',
      prompt: 'Hello',
    });

    assert.ok(result.usage, 'Should have usage information');
    assert.strictEqual(result.usage.inputTokens, 25);
    assert.strictEqual(result.usage.outputTokens, 50);
  });
});
