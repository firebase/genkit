import { embed } from '@genkit-ai/ai/embedder';
import assert from 'node:assert';
import { describe, it } from 'node:test';

import { defineOllamaEmbedder } from '../src/embeddings.js'; // Adjust the import path as necessary
import { OllamaPluginParams } from '../src/index.js'; // Adjust the import path as necessary

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

describe('defineOllamaEmbedder - Live Tests', () => {
  const options: OllamaPluginParams = {
    models: [{ name: modelName }],
    serverAddress,
  };

  it('should successfully return embeddings', async () => {
    const embedder = defineOllamaEmbedder(
      'live-test-embedder',
      'nomic-embed-text',
      768,
      options
    );

    const result = await embed({
      embedder,
      content: 'Hello, world!',
    });

    assert.strictEqual(result.length, 768);
  });
});
