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
import assert from 'node:assert';
import { describe, it } from 'node:test';
import {
  OllamaEmbeddingConfigSchema,
  defineOllamaEmbedder,
} from '../src/embeddings.js'; // Adjust the import path as necessary
import { OllamaPluginParams } from '../src/index.js'; // Adjust the import path as necessary

// Mock fetch to simulate API responses
global.fetch = async (input: RequestInfo | URL, options?: RequestInit) => {
  const url = typeof input === 'string' ? input : input.toString();

  if (url.includes('/api/embedding')) {
    if (options?.body && JSON.stringify(options.body).includes('fail')) {
      return {
        ok: false,
        statusText: 'Internal Server Error',
        json: async () => ({}),
      } as Response;
    }
    return {
      ok: true,
      json: async () => ({
        embedding: [0.1, 0.2, 0.3], // Example embedding values
      }),
    } as Response;
  }

  throw new Error('Unknown API endpoint');
};

describe('defineOllamaEmbedder', () => {
  const options: OllamaPluginParams = {
    models: [{ name: 'test-model' }],
    serverAddress: 'http://localhost:3000',
  };

  it('should successfully return embeddings', async () => {
    const embedder = defineOllamaEmbedder({
      name: 'test-embedder',
      modelName: 'test-model',
      dimensions: 123,
      options,
    });

    const result = await embed({
      embedder,
      content: 'Hello, world!',
    });
    assert.deepStrictEqual(result, [0.1, 0.2, 0.3]);
  });

  it('should handle API errors correctly', async () => {
    const embedder = defineOllamaEmbedder({
      name: 'test-embedder',
      modelName: 'test-model',
      dimensions: 123,
      options,
    });

    await assert.rejects(
      async () => {
        await embed({
          embedder,
          content: 'fail',
        });
      },
      (error) => {
        // Check if error is an instance of Error
        assert(error instanceof Error);

        assert.strictEqual(
          error.message,
          'Error fetching embedding from Ollama: Internal Server Error'
        );
        return true;
      }
    );
  });

  it('should validate the embedding configuration schema', async () => {
    const validConfig = {
      modelName: 'test-model',
      serverAddress: 'http://localhost:3000',
    };

    const invalidConfig = {
      modelName: 123, // Invalid type
      serverAddress: 'http://localhost:3000',
    };

    // Valid configuration should pass
    assert.doesNotThrow(() => {
      OllamaEmbeddingConfigSchema.parse(validConfig);
    });

    // Invalid configuration should throw
    assert.throws(() => {
      OllamaEmbeddingConfigSchema.parse(invalidConfig);
    });
  });

  it('should throw an error if the fetch response is not ok', async () => {
    const embedder = defineOllamaEmbedder({
      name: 'test-embedder',
      modelName: 'test-model',
      dimensions: 123,
      options,
    });

    await assert.rejects(async () => {
      await embed({
        embedder,
        content: 'fail',
      });
    }, new Error('Error fetching embedding from Ollama: Internal Server Error'));
  });
});
