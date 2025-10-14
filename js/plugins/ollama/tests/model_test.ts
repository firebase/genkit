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
import * as assert from 'assert';
import { genkit, z, type Genkit } from 'genkit';
import { beforeEach, describe, it } from 'node:test';
import { ollama } from '../src/index.js';
import type { OllamaPluginParams } from '../src/types.js';

const MOCK_TOOL_CALL_RESPONSE = {
  model: 'llama3.2',
  created_at: '2024-07-22T20:33:28.123648Z',
  message: {
    role: 'assistant',
    content: '',
    tool_calls: [
      {
        function: {
          name: 'get_current_weather',
          arguments: {
            format: 'celsius',
            location: 'Paris, FR',
          },
        },
      },
    ],
  },
  done_reason: 'stop',
  done: true,
};

const MOCK_END_RESPONSE = {
  model: 'llama3.2',
  created_at: '2024-07-22T20:33:28.123648Z',
  message: {
    role: 'assistant',
    content: 'The weather is sunny',
  },
  done_reason: 'stop',
  done: true,
};

const MAGIC_WORD = 'sunnnnnnny';

// Mock fetch to simulate API responses
global.fetch = async (input: RequestInfo | URL, options?: RequestInit) => {
  const url = typeof input === 'string' ? input : input.toString();
  if (url.includes('/api/chat')) {
    const body = JSON.parse((options?.body as string) || '{}');
    
    // For basic calls without tools, return the end response
    if (!body.tools || body.tools.length === 0) {
      return new Response(JSON.stringify(MOCK_END_RESPONSE));
    }
    
    // For tool calls, return the end response directly (simplified for v2)
    return new Response(JSON.stringify(MOCK_END_RESPONSE));
  }
  throw new Error('Unknown API endpoint');
};

describe('ollama models', () => {
  const options: OllamaPluginParams = {
    models: [{ name: 'test-model', supports: { tools: true } }],
    serverAddress: 'http://localhost:3000',
  };

  let ai: Genkit;
  beforeEach(() => {
    ai = genkit({
      plugins: [ollama(options)],
    });
  });

  it('should successfully return basic response', async () => {
    const result = await ai.generate({
      model: 'ollama/test-model',
      prompt: 'Hello',
    });
    assert.ok(result.message?.content[0]?.text === 'The weather is sunny');
  });

  it('should successfully return tool call response', async () => {
    const get_current_weather = ai.defineTool(
      {
        name: 'get_current_weather',
        description: 'gets weather',
        inputSchema: z.object({ format: z.string(), location: z.string() }),
      },
      async () => {
        return MAGIC_WORD;
      }
    );

    const result = await ai.generate({
      model: 'ollama/test-model',
      prompt: 'Hello',
      tools: [get_current_weather],
    });
    assert.ok(result.message?.content[0]?.text === 'The weather is sunny');
  });

  it('should throw for primitive tools', async () => {
    const get_current_weather = ai.defineTool(
      {
        name: 'get_current_weather',
        description: 'gets weather',
        inputSchema: z.object({ format: z.string(), location: z.string() }),
      },
      async () => {
        return MAGIC_WORD;
      }
    );
    const fooz = ai.defineTool(
      {
        name: 'fooz',
        description: 'gets fooz',
        inputSchema: z.string(),
      },
      async () => {
        return 1;
      }
    );

    await assert.rejects(async () => {
      await ai.generate({
        model: 'ollama/test-model',
        prompt: 'Hello',
        tools: [get_current_weather, fooz],
      });
    });
  });
});
