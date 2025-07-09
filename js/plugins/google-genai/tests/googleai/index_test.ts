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
import { afterEach, beforeEach, describe, it, mock } from 'node:test';
import {
  GoogleAIEmbeddingConfigSchema,
  KNOWN_EMBEDDER_MODELS,
} from '../../src/googleai/embedder.js';
import {
  GeminiConfigSchema,
  KNOWN_GEMINI_MODELS,
} from '../../src/googleai/gemini.js';
import { googleAI } from '../../src/googleai/index.js';
import { Model } from '../../src/googleai/types.js';

describe('GoogleAI Plugin', () => {
  let originalEnv: NodeJS.ProcessEnv;
  let fetchMock: any;

  beforeEach(() => {
    originalEnv = { ...process.env };
    // Set a default API key for most tests
    process.env.GOOGLE_API_KEY = 'test-api-key';

    // Mock global.fetch for listActions tests
    fetchMock = mock.method(global, 'fetch');
  });

  afterEach(() => {
    // Restore environment variables
    process.env = originalEnv;
    // Restore mocks
    mock.restoreAll();
  });

  describe('Initializer', () => {
    it('should pre-register flagship Gemini models', async () => {
      const ai = genkit({ plugins: [googleAI()] });
      const model1Name = Object.keys(KNOWN_GEMINI_MODELS)[0];
      const model1Path = `/model/googleai/${model1Name}`;
      const expectedBaseName = `googleai/${model1Name}`;
      const model1 = await ai.registry.lookupAction(model1Path);
      assert.ok(model1, `${model1Name} should be registered at ${model1Path}`);
      assert.strictEqual(model1?.__action.name, expectedBaseName);
    });

    it('should register all known Gemini models', async () => {
      const ai = genkit({ plugins: [googleAI()] });
      for (const modelName in KNOWN_GEMINI_MODELS) {
        const modelPath = `/model/googleai/${modelName}`;
        const expectedBaseName = `googleai/${modelName}`;
        const model = await ai.registry.lookupAction(modelPath);
        assert.ok(model, `${modelName} should be registered at ${modelPath}`);
        assert.strictEqual(model?.__action.name, expectedBaseName);
      }
    });

    it('should pre-register flagship Embedder models', async () => {
      const ai = genkit({ plugins: [googleAI()] });
      const modelKeys = Object.keys(KNOWN_EMBEDDER_MODELS);
      if (modelKeys.length > 0) {
        const model1Name = modelKeys[0];
        const model1Path = `/embedder/googleai/${model1Name}`;
        const expectedBaseName = `googleai/${model1Name}`;
        const model1 = await ai.registry.lookupAction(model1Path);
        assert.ok(
          model1,
          `${model1Name} should be registered at ${model1Path}`
        );
        assert.strictEqual(model1?.__action.name, expectedBaseName);
      }
    });

    it('should register all known Embedder models', async () => {
      const ai = genkit({ plugins: [googleAI()] });
      for (const modelName in KNOWN_EMBEDDER_MODELS) {
        const modelPath = `/embedder/googleai/${modelName}`;
        const expectedBaseName = `googleai/${modelName}`;
        const model = await ai.registry.lookupAction(modelPath);
        assert.ok(model, `${modelName} should be registered at ${modelPath}`);
        assert.strictEqual(model?.__action.name, expectedBaseName);
      }
    });

    it('should throw from initializer if no API key is provided', async () => {
      delete process.env.GOOGLE_API_KEY;
      delete process.env.GEMINI_API_KEY;
      delete process.env.GOOGLE_GENAI_API_KEY;
      const ai = genkit({ plugins: [googleAI({})] });
      const pluginProvider = googleAI()(ai);
      await assert.rejects(async () => {
        await pluginProvider.initializer();
      }, /Please pass in the API key/);
    });

    it('should NOT throw from initializer if apiKey is false', async () => {
      delete process.env.GOOGLE_API_KEY;
      delete process.env.GEMINI_API_KEY;
      delete process.env.GOOGLE_GENAI_API_KEY;
      const ai = genkit({ plugins: [googleAI({ apiKey: false })] });
      const pluginProvider = googleAI({ apiKey: false })(ai);
      await assert.doesNotReject(async () => {
        await pluginProvider.initializer();
      });
    });
  });

  describe('Resolver via lookupAction', () => {
    const testModelName = 'gemini-custom-pro';
    const testModelPath = `/model/googleai/${testModelName}`;
    const testEmbedderName = 'embedding-custom-001';
    const testEmbedderPath = `/embedder/googleai/${testEmbedderName}`;

    it('should register a new Gemini model when looked up', async () => {
      const ai = genkit({ plugins: [googleAI()] });
      const model = await ai.registry.lookupAction(testModelPath);
      assert.ok(model, `${testModelName} should be resolvable and registered`);
      assert.strictEqual(model?.__action.name, `googleai/${testModelName}`);
    });

    it('should register a new Embedder when looked up', async () => {
      const ai = genkit({ plugins: [googleAI()] });
      const embedder = await ai.registry.lookupAction(testEmbedderPath);
      assert.ok(
        embedder,
        `${testEmbedderName} should be resolvable and registered`
      );
      assert.strictEqual(
        embedder?.__action.name,
        `googleai/${testEmbedderName}`
      );
    });
  });

  describe('Helper Functions', () => {
    it('googleAI.model should return a ModelReference with correct schema', () => {
      // genkit() not needed as helper functions don't depend on the instance
      const modelName = 'gemini-2.0-flash';
      const modelRef = googleAI.model(modelName);
      assert.strictEqual(
        modelRef.name,
        `googleai/${modelName}`,
        'Name should be prefixed'
      );
      assert.ok(
        modelRef.info?.supports?.multiturn,
        'Gemini model should support multiturn'
      );
      assert.strictEqual(
        modelRef.configSchema,
        GeminiConfigSchema,
        'Should have GeminiConfigSchema'
      );
    });

    it('googleAI.model should handle names with googleai/ prefix', () => {
      const modelName = 'googleai/gemini-2.0-pro';
      const modelRef = googleAI.model(modelName);
      assert.strictEqual(modelRef.name, modelName);
    });

    it('googleAI.model should handle names with models/ prefix', () => {
      const modelName = 'models/gemini-2.0-pro';
      const modelRef = googleAI.model(modelName);
      assert.strictEqual(modelRef.name, 'googleai/gemini-2.0-pro');
    });

    it('googleAI.embedder should return an EmbedderReference with correct schema', () => {
      const embedderName = 'text-embedding-004';
      const embedderRef = googleAI.embedder(embedderName);
      assert.strictEqual(embedderRef.name, `googleai/${embedderName}`);
      assert.ok(embedderRef.info, 'Should have info');
      assert.strictEqual(
        embedderRef.configSchema,
        GoogleAIEmbeddingConfigSchema,
        'Should have GoogleAIEmbeddingConfigSchema'
      );
    });

    it('googleAI.embedder should handle names with googleai/ prefix', () => {
      const embedderName = 'googleai/text-embedding-custom';
      const embedderRef = googleAI.embedder(embedderName);
      assert.strictEqual(embedderRef.name, embedderName);
    });

    it('googleAI.embedder should handle names with models/ prefix', () => {
      const embedderName = 'models/text-embedding-custom';
      const embedderRef = googleAI.embedder(embedderName);
      assert.strictEqual(embedderRef.name, 'googleai/text-embedding-custom');
    });
  });

  describe('listActions Function', () => {
    const createMockResponse = (models: Array<Partial<Model>>) => {
      const responseBody = { models: models };
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => responseBody,
        text: async () => JSON.stringify(responseBody),
      });
    };

    it('should return an empty array if no models are returned', async () => {
      const ai = genkit({ plugins: [googleAI()] });
      fetchMock.mock.mockImplementation(async () => createMockResponse([]));
      const pluginProvider = googleAI()(ai);
      const actions = await pluginProvider.listActions!();
      assert.deepStrictEqual(actions, [], 'Should return an empty array');
    });

    it('should return metadata for models and embedders', async () => {
      const ai = genkit({ plugins: [googleAI()] });
      const mockModels: Partial<Model>[] = [
        {
          name: 'models/gemini-2.5-pro',
          supportedGenerationMethods: ['generateContent'],
        },
        {
          name: 'models/text-embedding-004',
          supportedGenerationMethods: ['embedContent'],
        },
        {
          name: 'models/other-model',
          supportedGenerationMethods: ['other'],
        },
      ];
      fetchMock.mock.mockImplementation(async () =>
        createMockResponse(mockModels)
      );

      const pluginProvider = googleAI()(ai);
      const actions = await pluginProvider.listActions!();
      const actionNames = actions.map((a) => a.name).sort();
      assert.deepStrictEqual(
        actionNames,
        ['googleai/gemini-2.5-pro', 'googleai/text-embedding-004'].sort()
      );

      const modelAction = actions.find(
        (a) => a.name === 'googleai/gemini-2.5-pro'
      );
      assert.strictEqual(modelAction?.actionType, 'model');

      const embedderAction = actions.find(
        (a) => a.name === 'googleai/text-embedding-004'
      );
      assert.strictEqual(embedderAction?.actionType, 'embedder');
    });

    it('should filter out deprecated models', async () => {
      const ai = genkit({ plugins: [googleAI()] });
      const mockModels = [
        {
          name: 'models/gemini-1.5-flash',
          supportedGenerationMethods: ['generateContent'],
        },
        {
          name: 'models/gemini-pro-deprecated',
          supportedGenerationMethods: ['generateContent'],
          description: 'This model is deprecated.',
        },
        {
          name: 'models/text-embedding-deprecated',
          supportedGenerationMethods: ['embedContent'],
          description: 'deprecated',
        },
      ];
      fetchMock.mock.mockImplementation(async () =>
        createMockResponse(mockModels)
      );
      const pluginProvider = googleAI()(ai);
      const actions = await pluginProvider.listActions!();
      const actionNames = actions.map((a) => a.name);
      assert.deepStrictEqual(actionNames, ['googleai/gemini-1.5-flash']);
    });

    it('should handle fetch errors gracefully', async () => {
      const ai = genkit({ plugins: [googleAI()] });
      fetchMock.mock.mockImplementation(async () => {
        return Promise.resolve({
          ok: false,
          status: 500,
          statusText: 'Internal Error',
          json: async () => ({ error: { message: 'API Error' } }),
        });
      });
      const pluginProvider = googleAI()(ai);
      const actions = await pluginProvider.listActions!();
      assert.deepStrictEqual(
        actions,
        [],
        'Should return empty array on fetch error'
      );
    });

    it('should return empty array if API key is missing for listActions', async () => {
      delete process.env.GOOGLE_API_KEY;
      delete process.env.GEMINI_API_KEY;
      delete process.env.GOOGLE_GENAI_API_KEY;
      const ai = genkit({ plugins: [googleAI({ apiKey: false })] }); // Init with apiKey: false

      const pluginProvider = googleAI({ apiKey: false })(ai);
      const actions = await pluginProvider.listActions!();
      assert.deepStrictEqual(
        actions,
        [],
        'Should return empty array if API key is not found'
      );
      assert.strictEqual(
        fetchMock.mock.callCount(),
        0,
        'Fetch should not be called'
      );
    });

    it('should use listActions cache', async () => {
      const ai = genkit({ plugins: [googleAI()] });
      const mockModels = [
        {
          name: 'models/gemini-1.0-pro',
          supportedGenerationMethods: ['generateContent'],
        },
      ];
      fetchMock.mock.mockImplementation(async () =>
        createMockResponse(mockModels)
      );
      const pluginProvider = googleAI()(ai);
      await pluginProvider.listActions!();
      await pluginProvider.listActions!();
      assert.strictEqual(
        fetchMock.mock.callCount(),
        1,
        'fetch should only be called once'
      );
    });
  });
});
