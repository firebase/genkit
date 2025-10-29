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
import { before, describe, it } from 'node:test';
import { setupAnthropicMock } from './mocks/setup-anthropic-mock.js';

setupAnthropicMock();

describe('Anthropic Plugin', () => {
  let anthropic: any;
  let SUPPORTED_CLAUDE_MODELS: any;

  before(async () => {
    process.env.ANTHROPIC_API_KEY = 'test-api-key';

    // Import after mocking is set up
    const indexModule = await import('../lib/index.js');
    anthropic = indexModule.default;

    const claudeModule = await import('../lib/claude.js');
    SUPPORTED_CLAUDE_MODELS = claudeModule.SUPPORTED_CLAUDE_MODELS;
  });

  it('should register all supported Claude models', async () => {
    const ai = genkit({
      plugins: [anthropic()],
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
