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
import { SUPPORTED_CLAUDE_MODELS } from '../src/claude.js';
import anthropic from '../src/index.js';
import { PluginOptions, __testClient } from '../src/types.js';
import { createMockAnthropicClient } from './mocks/anthropic-client.js';

describe('Anthropic Plugin', () => {
  it('should register all supported Claude models', async () => {
    const mockClient = createMockAnthropicClient();

    const ai = genkit({
      plugins: [anthropic({ [__testClient]: mockClient } as PluginOptions)],
    });

    for (const modelName of Object.keys(SUPPORTED_CLAUDE_MODELS)) {
      const modelPath = `/model/anthropic/${modelName}`;
      const expectedBaseName = `anthropic/${modelName}`;
      const model = await ai.registry.lookupAction(modelPath);
      assert.ok(model, `${modelName} should be registered at ${modelPath}`);
      assert.strictEqual(model?.__action.name, expectedBaseName);
    }
  });

  it.todo('should throw error when API key is missing');

  it.todo('should use API key from environment variable');

  it.todo('should resolve models dynamically via resolve function');

  it.todo('should list available models from API');

  it.todo('should cache list results on subsequent calls?');
});
