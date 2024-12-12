/**
 * Copyright 2024 Google LLC
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
import { Genkit, genkit, z } from 'genkit';
import assert from 'node:assert';
import { after, before, beforeEach, describe, it } from 'node:test';

import { ollama } from '../src/index.js';

// Define a sample schema for testing
const CountrySchema = z.object({
  name: z.string(),
  capital: z.string(),
  languages: z.array(z.string()),
});

// Mock response data
const sampleCountryData = {
  name: 'Canada',
  capital: 'Ottawa',
  languages: ['English', 'French'],
};

describe('Ollama Structured Output', () => {
  let ai: Genkit;
  let originalFetch: typeof fetch;

  before(() => {
    // Store the original fetch
    originalFetch = global.fetch;

    // Set up mock fetch
    global.fetch = async (input: RequestInfo | URL, options?: RequestInit) => {
      const url = typeof input === 'string' ? input : input.toString();
      const requestBody = options?.body
        ? JSON.parse(options.body as string)
        : {};

      const mockResponse = (data: any) => {
        return {
          ok: true,
          body: {
            getReader: () => ({
              read: async () => ({ done: true, value: undefined }),
            }),
          },
          text: async () => JSON.stringify(data),
        } as Response;
      };

      if (url.includes('/api/chat')) {
        // Check if format is specified in the request
        if (requestBody.format) {
          return mockResponse({
            model: 'llama2',
            created_at: '2024-03-14T12:00:00Z',
            message: {
              role: 'assistant',
              content: JSON.stringify(sampleCountryData),
            },
            done: true,
          });
        }
        // Regular chat response
        return mockResponse({
          model: 'llama2',
          created_at: '2024-03-14T12:00:00Z',
          message: {
            role: 'assistant',
            content: 'Some regular text response',
          },
          done: true,
        });
      }

      if (url.includes('/api/generate')) {
        if (requestBody.format) {
          return mockResponse({
            model: 'llama2',
            created_at: '2024-03-14T12:00:00Z',
            response: JSON.stringify(sampleCountryData),
            done: true,
          });
        }
        return mockResponse({
          model: 'llama2',
          created_at: '2024-03-14T12:00:00Z',
          response: 'Some regular text response',
          done: true,
        });
      }

      throw new Error('Unknown API endpoint');
    };
  });

  after(() => {
    // Restore the original fetch
    global.fetch = originalFetch;
  });

  beforeEach(() => {
    ai = genkit({
      plugins: [
        ollama({
          serverAddress: 'http://localhost:11434',
          models: [
            {
              name: 'chat-model',
              type: 'chat',
            },
            {
              name: 'generate-model',
              type: 'generate',
            },
          ],
        }),
      ],
    });
  });

  it('should handle structured output in chat mode', async () => {
    const response = await ai.generate({
      model: 'ollama/chat-model',
      messages: [
        {
          role: 'user',
          content: [{ text: 'Tell me about Canada' }],
        },
      ],
      output: {
        format: 'json',
        schema: CountrySchema,
      },
    });

    assert.notEqual(response.message, undefined);
    assert.notEqual(response.message!.content, undefined);
    assert.notEqual(response.message!.content[0].text, undefined);

    const content = JSON.parse(response.message!.content[0].text!);
    assert.deepStrictEqual(content, sampleCountryData);
  });

  it('should handle structured output in generate mode', async () => {
    const response = await ai.generate({
      model: 'ollama/generate-model',
      messages: [
        {
          role: 'user',
          content: [{ text: 'Tell me about Canada' }],
        },
      ],
      output: {
        format: 'json',
        schema: CountrySchema,
      },
    });

    assert.notEqual(response.message, undefined);
    assert.notEqual(response.message!.content, undefined);
    assert.notEqual(response.message!.content[0].text, undefined);

    const content = JSON.parse(response.message!.content[0].text!);
    assert.deepStrictEqual(content, sampleCountryData);
  });

  it('should handle schema validation errors', async () => {
    // Override fetch for this specific test
    global.fetch = async () =>
      ({
        ok: true,
        body: {
          getReader: () => ({
            read: async () => ({ done: true, value: undefined }),
          }),
        },
        text: async () =>
          JSON.stringify({
            model: 'llama2',
            created_at: '2024-03-14T12:00:00Z',
            message: {
              role: 'assistant',
              content: JSON.stringify({ invalid: 'data' }),
            },
            done: true,
          }),
      }) as Response;

    await assert.rejects(
      async () => {
        await ai.generate({
          model: 'ollama/chat-model',
          messages: [
            {
              role: 'user',
              content: [{ text: 'Tell me about Canada' }],
            },
          ],
          output: {
            format: 'json',
            schema: CountrySchema,
          },
        });
      },
      (error) => {
        assert(error instanceof Error);
        assert(error.message.includes('Required'));
        return true;
      }
    );
  });

  it('should handle API errors gracefully', async () => {
    // Override fetch for this specific test
    global.fetch = async () =>
      ({
        ok: false,
        statusText: 'Internal Server Error',
        text: async () => 'Internal Server Error',
      }) as Response;

    await assert.rejects(
      async () => {
        await ai.generate({
          model: 'ollama/chat-model',
          messages: [
            {
              role: 'user',
              content: [{ text: 'Tell me about Canada' }],
            },
          ],
          output: {
            format: 'json',
            schema: CountrySchema,
          },
        });
      },
      (error) => {
        assert(error instanceof Error);
        assert.strictEqual(error.message, 'Response has no body');
        return true;
      }
    );
  });
});
