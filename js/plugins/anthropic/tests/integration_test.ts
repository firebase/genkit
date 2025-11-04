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
import { genkit } from 'genkit';
import { describe, it } from 'node:test';
import { anthropic } from '../src/index.js';
import { __testClient } from '../src/types.js';
import { createMockAnthropicClient } from './mocks/anthropic-client.js';

import { PluginOptions } from '../src/types.js';

describe('Anthropic Integration', () => {
  const mockClient = createMockAnthropicClient();
  const ai = genkit({
    plugins: [anthropic({ [__testClient]: mockClient } as PluginOptions)],
  });

  it('should successfully generate a response', async () => {
    const result = await ai.generate({
      model: 'anthropic/claude-3-5-haiku',
      prompt: 'Hello',
    });

    assert.strictEqual(result.text, 'Hello! How can I help you today?');
  });

  it.todo(
    'should handle tool calling workflow (call tool, receive result, generate final response)'
  );

  it.todo('should handle multi-turn conversations');

  it.todo('should stream responses with streaming callback');

  it.todo('should handle media/image inputs');

  it.todo('should propagate API errors correctly');

  it.todo('should respect abort signals for cancellation');

  it.todo('should track token usage in responses');
});
