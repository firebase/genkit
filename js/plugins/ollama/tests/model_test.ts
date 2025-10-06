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

// Mock fetch to simulate the multi-turn tool calling flow:
// 1. Initial request with tools → returns tool_calls response
// 2. Follow-up request with tool results (role='tool') → returns final answer
global.fetch = async (input: RequestInfo | URL, options?: RequestInit) => {
  const url = typeof input === 'string' ? input : input.toString();
  if (url.includes('/api/chat')) {
    const body = JSON.parse((options?.body as string) || '{}');

    // Check if this request contains tool responses (second call in tool flow)
    const hasToolResponses = body.messages?.some((m) => m.role === 'tool');
    if (hasToolResponses) {
      return new Response(JSON.stringify(MOCK_END_RESPONSE));
    }

    // Initial request with tools → return tool call
    if (body.tools && body.tools.length > 0) {
      return new Response(JSON.stringify(MOCK_TOOL_CALL_RESPONSE));
    }

    // Basic request without tools → return final response
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
    assert.ok(result.text === 'The weather is sunny');
  });

  it('should successfully return tool call response', async () => {
    const get_current_weather = ai.defineTool(
      {
        name: 'get_current_weather',
        description: 'gets weather',
        inputSchema: z.object({ format: z.string(), location: z.string() }),
      },
      async () => {
        return 'sunny';
      }
    );

    const result = await ai.generate({
      model: 'ollama/test-model',
      prompt: 'Hello',
      tools: [get_current_weather],
    });
    assert.ok(result.text === 'The weather is sunny');
  });

  it('should throw for tools with primitive (non-object) input schema.', async () => {
    // This tool will throw an error because it has a primitive (non-object) input schema.
    const toolWithNonObjectInput = ai.defineTool(
      {
        name: 'toolWithNonObjectInput',
        description: 'tool with non-object input schema',
        inputSchema: z.string(),
      },
      async () => {
        return 'anything';
      }
    );

    try {
      await ai.generate({
        model: 'ollama/test-model',
        prompt: 'Hello',
        tools: [toolWithNonObjectInput],
      });
    } catch (error) {
      assert.ok(error instanceof Error);

      assert.ok(
        error.message.includes('Ollama only supports tools with object inputs')
      );
    }
  });
});
