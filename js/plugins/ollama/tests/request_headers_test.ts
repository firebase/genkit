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

import { embed } from '@genkit-ai/ai/embedder';
import { Document } from '@genkit-ai/ai/retriever';
import { configureGenkit } from '@genkit-ai/core';
import assert from 'node:assert';
import { beforeEach, describe, it } from 'node:test';
import { OllamaPluginParams, ollama } from '../src'; // Adjust the import path as necessary
import { defineOllamaEmbedder } from '../src/embeddings.js'; // Adjust the import path as necessary

// Create a variable to hold the fetch calls
let fetchCalls: any[] = [];

// Mock fetch to capture request headers
global.fetch = async (input: RequestInfo | URL, options?: RequestInit) => {
  const url = typeof input === 'string' ? input : input.toString();

  // Store the fetch call for assertions
  fetchCalls.push({ input, options });

  if (url.includes('/api/embeddings')) {
    // Return a successful response
    return {
      ok: true,
      json: async () => ({
        embedding: [0.1, 0.2, 0.3], // Example embedding values
      }),
      headers: options?.headers || {},
    } as Response;
  }
  throw new Error('Unknown API endpoint');
};

describe('Ollama Embedder - Request Headers', () => {
  // Reset the fetchCalls array before each test
  beforeEach(() => {
    fetchCalls = [];
  });

  it('should apply custom request headers when provided', async () => {
    configureGenkit({
      plugins: [
        ollama({
          serverAddress: 'http://localhost:3000',
          models: [{ name: 'test-model' }],
        }),
      ],
    });

    const options: OllamaPluginParams = {
      serverAddress: 'http://localhost:3000',
      models: [{ name: 'test-model' }],
      requestHeaders: async ({ params, request }) => ({
        'X-Custom-Header': 'custom-value',
        Authorization: 'Bearer token-value',
      }),
    };

    // Define the embedder
    const embedder = defineOllamaEmbedder({
      name: 'test-embedder',
      modelName: 'test-model',
      dimensions: 123,
      options,
    });

    // Create a mock document
    const doc = new Document({
      content: [
        {
          text: 'Hello, world!',
        },
      ],
    });

    // Run the embedder
    const result = await embed({
      embedder,
      content: doc,
    });

    // Assert the result
    assert.deepStrictEqual(result, [0.1, 0.2, 0.3]);

    // Capture the request headers from the fetch calls
    const headers = fetchCalls[0].options?.headers;

    // Assert the custom headers were applied correctly
    assert.strictEqual(headers['X-Custom-Header'], 'custom-value');
    assert.strictEqual(headers['Authorization'], 'Bearer token-value');
  });
});
