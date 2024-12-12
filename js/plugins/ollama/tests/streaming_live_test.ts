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
import { genkit } from 'genkit';
import assert from 'node:assert';
import { describe, it } from 'node:test';
import { ollama } from '../src/index.js';
import { OllamaPluginParams } from '../src/types.js';

// Utility function to parse command-line arguments
function parseArgs() {
  const args = process.argv.slice(2);
  const serverAddress =
    args.find((arg) => arg.startsWith('--server-address='))?.split('=')[1] ||
    'http://localhost:11434';
  const modelName =
    args.find((arg) => arg.startsWith('--model-name='))?.split('=')[1] ||
    'phi3.5:latest';
  return { serverAddress, modelName };
}

const { serverAddress, modelName } = parseArgs();

describe('Ollama Streaming - Live Tests', () => {
  const options: OllamaPluginParams = {
    serverAddress,
    models: [{ name: modelName, type: 'chat' }],
  };

  it('should stream responses in chat mode', async () => {
    const ai = genkit({
      plugins: [ollama(options)],
    });

    const streamedChunks: string[] = [];
    let streamingCallCount = 0;

    const response = await ai.generate({
      model: `ollama/${modelName}`,
      messages: [
        {
          role: 'user',
          content: [{ text: 'Count from 1 to 5 slowly.' }],
        },
      ],
      streamingCallback: (chunk) => {
        streamingCallCount++;
        if (chunk.content[0].text) {
          streamedChunks.push(chunk.content[0].text);
        }
      },
    });

    // Verify that streaming occurred
    assert.ok(
      streamingCallCount > 1,
      'Streaming callback should be called multiple times'
    );
    assert.ok(streamedChunks.length > 1, 'Should receive multiple chunks');

    // Verify final response matches the accumulated streamed content
    const finalText = response.message?.content[0].text;
    const streamedText = streamedChunks.join('');
    assert.strictEqual(
      finalText,
      streamedText,
      'Final text should match accumulated streamed content'
    );
  });

  it('should stream responses with generate mode', async () => {
    const ai = genkit({
      plugins: [ollama(options)],
    });

    const streamedChunks: string[] = [];
    let streamingCallCount = 0;

    const response = await ai.generate({
      model: `ollama/${modelName}`,
      messages: [
        {
          role: 'user',
          content: [{ text: 'Write a short story about a cat.' }],
        },
      ],
      streamingCallback: (chunk) => {
        streamingCallCount++;
        if (chunk.content[0].text) {
          streamedChunks.push(chunk.content[0].text);
        }
      },
    });

    // Verify that streaming occurred
    assert.ok(
      streamingCallCount > 1,
      'Streaming callback should be called multiple times'
    );
    assert.ok(streamedChunks.length > 1, 'Should receive multiple chunks');

    // Verify final response matches the accumulated streamed content
    const finalText = response.message?.content[0].text;
    const streamedText = streamedChunks.join('');
    assert.strictEqual(
      finalText,
      streamedText,
      'Final text should match accumulated streamed content'
    );
  });

  it('should handle errors during streaming', async () => {
    const ai = genkit({
      plugins: [ollama(options)],
    });

    const streamedChunks: string[] = [];

    await assert.rejects(
      async () => {
        await ai.generate({
          model: `ollama/nonexistent-model`,
          messages: [
            {
              role: 'user',
              content: [{ text: 'This should fail.' }],
            },
          ],
          streamingCallback: (chunk) => {
            if (chunk.content[0].text) {
              streamedChunks.push(chunk.content[0].text);
            }
          },
        });
      },
      (error) => {
        assert(error instanceof Error);
        // Check if error message indicates model not found or similar
        return true;
      }
    );

    // Verify no content was streamed before error
    assert.strictEqual(
      streamedChunks.length,
      0,
      'No content should be streamed on error'
    );
  });
});
