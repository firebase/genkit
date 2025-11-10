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
import anthropic from '../src/index.js';
import { SUPPORTED_CLAUDE_MODELS } from '../src/models.js';
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

  it('should throw error when API key is missing', () => {
    // Save original env var if it exists
    const originalApiKey = process.env.ANTHROPIC_API_KEY;
    delete process.env.ANTHROPIC_API_KEY;

    try {
      assert.throws(() => {
        anthropic({} as PluginOptions);
      }, /Please pass in the API key or set the ANTHROPIC_API_KEY environment variable/);
    } finally {
      // Restore original env var
      if (originalApiKey !== undefined) {
        process.env.ANTHROPIC_API_KEY = originalApiKey;
      }
    }
  });

  it('should use API key from environment variable', () => {
    // Save original env var if it exists
    const originalApiKey = process.env.ANTHROPIC_API_KEY;
    const testApiKey = 'test-api-key-from-env';

    try {
      // Set test API key
      process.env.ANTHROPIC_API_KEY = testApiKey;

      // Plugin should initialize without throwing
      const plugin = anthropic({} as PluginOptions);
      assert.ok(plugin);
      assert.strictEqual(plugin.name, 'anthropic');
    } finally {
      // Restore original env var
      if (originalApiKey !== undefined) {
        process.env.ANTHROPIC_API_KEY = originalApiKey;
      } else {
        delete process.env.ANTHROPIC_API_KEY;
      }
    }
  });

  it('should resolve models dynamically via resolve function', async () => {
    const mockClient = createMockAnthropicClient();
    const plugin = anthropic({ [__testClient]: mockClient } as PluginOptions);

    assert.ok(plugin.resolve, 'Plugin should have resolve method');

    // Test resolving a valid model
    const validModel = plugin.resolve!('model', 'anthropic/claude-3-5-haiku');
    assert.ok(validModel, 'Should resolve valid model');
    assert.strictEqual(typeof validModel, 'function');

    // Test resolving an unknown model name - should return a model action
    // (following Google GenAI pattern: accept any model name, let API validate)
    const unknownModel = plugin.resolve!(
      'model',
      'anthropic/unknown-model-xyz'
    );
    assert.ok(unknownModel, 'Should resolve unknown model name');
    assert.strictEqual(
      typeof unknownModel,
      'function',
      'Should return a model action'
    );

    // Test resolving with invalid action type (using 'tool' as invalid for this context)
    const invalidActionType = plugin.resolve!(
      'tool',
      'anthropic/claude-3-5-haiku'
    );
    assert.strictEqual(
      invalidActionType,
      undefined,
      'Should return undefined for invalid action type'
    );
  });

  it('should list available models from API', async () => {
    const mockClient = createMockAnthropicClient({
      modelList: [
        { id: 'claude-3-5-haiku-20241022', display_name: 'Claude 3.5 Haiku' },
        { id: 'claude-3-5-sonnet-20241022', display_name: 'Claude 3.5 Sonnet' },
        { id: 'claude-sonnet-4-20250514', display_name: 'Claude 4 Sonnet' },
      ],
    });

    const plugin = anthropic({ [__testClient]: mockClient } as PluginOptions);
    assert.ok(plugin.list, 'Plugin should have list method');

    const models = await plugin.list!();

    assert.ok(Array.isArray(models), 'Should return an array');
    assert.ok(models.length > 0, 'Should return at least one model');

    // Verify model structure
    for (const model of models) {
      assert.ok(model.name, 'Model should have a name');
      // ActionMetadata has name and other properties, but kind is not required
    }

    // Verify mock was called
    const listStub = mockClient.models.list as any;
    assert.strictEqual(
      listStub.mock.calls.length,
      1,
      'models.list should be called once'
    );
  });

  it('should cache list results on subsequent calls?', async () => {
    const mockClient = createMockAnthropicClient({
      modelList: [
        { id: 'claude-3-5-haiku-20241022', display_name: 'Claude 3.5 Haiku' },
      ],
    });

    const plugin = anthropic({ [__testClient]: mockClient } as PluginOptions);
    assert.ok(plugin.list, 'Plugin should have list method');

    // First call
    const firstResult = await plugin.list!();
    assert.ok(firstResult, 'First call should return results');

    // Second call
    const secondResult = await plugin.list!();
    assert.ok(secondResult, 'Second call should return results');

    // Verify both results are the same (reference equality for cache)
    assert.strictEqual(
      firstResult,
      secondResult,
      'Results should be cached (same reference)'
    );

    // Verify models.list was only called once due to caching
    const listStub = mockClient.models.list as any;
    assert.strictEqual(
      listStub.mock.calls.length,
      1,
      'models.list should only be called once due to caching'
    );
  });
});
