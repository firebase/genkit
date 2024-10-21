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
import { configureGenkit } from '@genkit-ai/core';
import assert from 'node:assert';
import { describe, it } from 'node:test';
import { defineOllamaEmbedder } from '../src/embeddings.js'; // Adjust the import path as necessary
import { OllamaPluginParams, ollama } from '../src/index.js'; // Adjust the import path as necessary
// Utility function to parse command-line arguments
function parseArgs() {
  const args = process.argv.slice(2);
  const serverAddress =
    args.find((arg) => arg.startsWith('--server-address='))?.split('=')[1] ||
    'http://localhost:11434';
  const modelName =
    args.find((arg) => arg.startsWith('--model-name='))?.split('=')[1] ||
    'nomic-embed-text';
  return { serverAddress, modelName };
}
const { serverAddress, modelName } = parseArgs();
if (process.env.LIVE_TEST) {
  describe('Live Test: defineOllamaEmbedder', () => {
    const options: OllamaPluginParams = {
      models: [{ name: modelName }],
      serverAddress,
    };
    it('live: should successfully return embeddings', async () => {
      configureGenkit({
        plugins: [
          ollama({
            serverAddress: 'http://127.0.0.1:11434', // default local address
          }),
        ],
      });
      const embedder = defineOllamaEmbedder({
        name: 'ollama/live-test-embedder',
        modelName: 'nomic-embed-text',
        dimensions: 768,
        options,
      });
      const result = await embed({
        embedder,
        content: 'Hello, world!',
      });
      assert.strictEqual(result.length, 768);
    });
  });

  describe('E2E Test: Ollama Embedder', () => {
    it('e2e: should successfully return embeddings using configureGenkit', async () => {
      configureGenkit({
        plugins: [
          ollama({
            embedders: [
              { name: 'nomic-embed-text', dimensions: 768 }, // Use the existing embedder
            ],
            serverAddress: 'http://127.0.0.1:11434', // default local address
          }),
        ],
      });

      const result = await embed({
        embedder: 'ollama/nomic-embed-text',
        content: 'foo',
        options: {
          truncate: true,
        },
      });

      assert.strictEqual(result.length, 768); // Assuming the embeddings should have 768 dimensions
    });
  });
}
