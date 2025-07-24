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
import { GENKIT_CLIENT_HEADER, Genkit } from 'genkit';
import { GenerateRequest, getBasicUsageStats } from 'genkit/model';
import { GoogleAuth } from 'google-auth-library';
import { afterEach, beforeEach, describe, it } from 'node:test';
import * as sinon from 'sinon';
import { getVertexAIUrl } from '../../src/vertexai/client';
import {
  ImagenConfig,
  ImagenConfigSchema,
  TEST_ONLY,
  defineModel,
  model,
} from '../../src/vertexai/imagen';
import {
  ClientOptions,
  ImagenPredictRequest,
  ImagenPredictResponse,
  ImagenPrediction,
} from '../../src/vertexai/types.js';
import * as utils from '../../src/vertexai/utils';

const { toImagenParameters, fromImagenPrediction } = TEST_ONLY;

// Helper function to escape special characters for use in a RegExp
function escapeRegExp(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); // $& means the whole matched string
}

describe('Vertex AI Imagen', () => {
  describe('KNOWN_IMAGEN_MODELS', () => {
    it('should contain non-zero number of models', () => {
      assert.ok(Object.keys(TEST_ONLY.KNOWN_MODELS).length > 0);
    });
  });

  describe('model()', () => {
    it('should return a ModelReference for a known model', () => {
      const modelName = 'imagen-3.0-generate-002';
      const ref = model(modelName);
      assert.strictEqual(ref.name, `vertexai/${modelName}`);
      assert.ok(ref.info?.supports?.media);
    });

    it('should return a ModelReference for an unknown model using generic info', () => {
      const modelName = 'imagen-unknown-model';
      const ref = model(modelName);
      assert.strictEqual(ref.name, `vertexai/${modelName}`);
      assert.deepStrictEqual(ref.info, TEST_ONLY.GENERIC_MODEL.info);
    });

    it('should apply config to a known model', () => {
      const modelName = 'imagen-3.0-generate-002';
      const config: ImagenConfig = { seed: 123 };
      const ref = model(modelName, config);
      assert.strictEqual(ref.name, `vertexai/${modelName}`);
      assert.deepStrictEqual(ref.config, config);
    });

    it('should apply config to an unknown model', () => {
      const modelName = 'imagen-unknown-model';
      const config: ImagenConfig = { aspectRatio: '16:9' };
      const ref = model(modelName, config);
      assert.strictEqual(ref.name, `vertexai/${modelName}`);
      assert.deepStrictEqual(ref.config, config);
    });

    it('should handle full model path', () => {
      const modelName = 'tunedModels/my-tuned-model';
      const ref = model(modelName);
      assert.strictEqual(ref.name, 'vertexai/tunedModels/my-tuned-model');
    });
  });

  describe('toImagenParameters', () => {
    const baseRequest: GenerateRequest<typeof ImagenConfigSchema> = {
      messages: [],
    };

    it('should set default sampleCount to 1 if candidates is not provided', () => {
      const result = toImagenParameters(baseRequest);
      assert.strictEqual(result.sampleCount, 1);
    });

    it('should use request.candidates for sampleCount', () => {
      const request: GenerateRequest<typeof ImagenConfigSchema> = {
        ...baseRequest,
        candidates: 3,
      };
      const result = toImagenParameters(request);
      assert.strictEqual(result.sampleCount, 3);
    });

    it('should include config parameters', () => {
      const request: GenerateRequest<typeof ImagenConfigSchema> = {
        ...baseRequest,
        config: {
          seed: 12345,
          aspectRatio: '16:9',
          negativePrompt: 'No red colors',
        },
      };
      const result = toImagenParameters(request);
      assert.strictEqual(result.sampleCount, 1);
      assert.strictEqual(result.negativePrompt, 'No red colors');
      assert.strictEqual(result.seed, 12345);
      assert.strictEqual(result.aspectRatio, '16:9');
    });

    it('should omit undefined or null config parameters', () => {
      const request: GenerateRequest<typeof ImagenConfigSchema> = {
        ...baseRequest,
        config: {
          negativePrompt: undefined,
          seed: null as any,
          aspectRatio: '1:1',
        },
      };
      const result = toImagenParameters(request);
      assert.strictEqual(result.sampleCount, 1);
      assert.strictEqual(result.hasOwnProperty('negativePrompt'), false);
      assert.strictEqual(result.hasOwnProperty('seed'), false);
      assert.strictEqual(result.aspectRatio, '1:1');
    });
  });

  describe('fromImagenPrediction', () => {
    it('should convert ImagenPrediction to CandidateData', () => {
      const prediction: ImagenPrediction = {
        bytesBase64Encoded: 'dGVzdGJ5dGVz',
        mimeType: 'image/png',
      };
      const index = 2;
      const result = fromImagenPrediction(prediction, index);

      assert.deepStrictEqual(result, {
        index: 2,
        finishReason: 'stop',
        message: {
          role: 'model',
          content: [
            {
              media: {
                url: 'data:image/png;base64,dGVzdGJ5dGVz',
                contentType: 'image/png',
              },
            },
          ],
        },
      });
    });
  });

  describe('defineImagenModel()', () => {
    let mockAi: sinon.SinonStubbedInstance<Genkit>;
    let fetchStub: sinon.SinonStub;
    const modelName = 'imagen-test-model';
    let authMock: sinon.SinonStubbedInstance<GoogleAuth>;

    const regionalClientOptions: ClientOptions = {
      kind: 'regional',
      projectId: 'test-project',
      location: 'us-central1',
      authClient: {} as any,
    };

    const globalClientOptions: ClientOptions = {
      kind: 'global',
      projectId: 'test-project',
      location: 'global',
      authClient: {} as any,
      apiKey: 'test-api-key',
    };

    beforeEach(() => {
      mockAi = sinon.createStubInstance(Genkit);
      fetchStub = sinon.stub(global, 'fetch');
      authMock = sinon.createStubInstance(GoogleAuth);
      authMock.getAccessToken.resolves('test-token');
      regionalClientOptions.authClient = authMock as unknown as GoogleAuth;
      globalClientOptions.authClient = authMock as unknown as GoogleAuth;
    });

    afterEach(() => {
      sinon.restore();
    });

    function mockFetchResponse(body: any, status = 200) {
      const response = new Response(JSON.stringify(body), {
        status: status,
        statusText: status === 200 ? 'OK' : 'Error',
        headers: { 'Content-Type': 'application/json' },
      });
      fetchStub.resolves(Promise.resolve(response));
    }

    function captureModelRunner(
      clientOptions: ClientOptions
    ): (request: GenerateRequest, options: any) => Promise<any> {
      defineModel(mockAi as any, modelName, clientOptions);
      assert.ok(mockAi.defineModel.calledOnce);
      const callArgs = mockAi.defineModel.firstCall.args;
      assert.strictEqual(callArgs[0].name, `vertexai/${modelName}`);
      assert.strictEqual(callArgs[0].configSchema, ImagenConfigSchema);
      return callArgs[1];
    }

    function getExpectedHeaders(
      clientOptions: ClientOptions
    ): Record<string, string | undefined> {
      const headers: Record<string, string | undefined> = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Client': GENKIT_CLIENT_HEADER,
        'User-Agent': GENKIT_CLIENT_HEADER,
        Authorization: 'Bearer test-token',
        'x-goog-user-project':
          clientOptions.kind != 'express' ? clientOptions.projectId : '',
      };
      if (clientOptions.apiKey) {
        headers['x-goog-api-key'] = clientOptions.apiKey;
      }
      return headers;
    }

    function runTestsForClientOptions(clientOptions: ClientOptions) {
      const expectedUrl = getVertexAIUrl({
        includeProjectAndLocation: true,
        resourcePath: `publishers/google/models/${modelName}`,
        resourceMethod: 'predict',
        clientOptions,
      });

      it(`should define a model and call fetch successfully for ${clientOptions.kind}`, async () => {
        const request: GenerateRequest<typeof ImagenConfigSchema> = {
          messages: [{ role: 'user', content: [{ text: 'A cat' }] }],
          candidates: 2,
          config: { seed: 42 },
        };

        const mockPrediction: ImagenPrediction = {
          bytesBase64Encoded: 'abc',
          mimeType: 'image/png',
        };
        const mockResponse: ImagenPredictResponse = {
          predictions: [mockPrediction, mockPrediction],
        };
        mockFetchResponse(mockResponse);

        const modelRunner = captureModelRunner(clientOptions);
        const result = await modelRunner(request, {});

        sinon.assert.calledOnce(fetchStub);
        const fetchArgs = fetchStub.lastCall.args;
        let actualUrl = fetchArgs[0];
        assert.strictEqual(actualUrl, expectedUrl);
        assert.strictEqual(fetchArgs[1].method, 'POST');
        assert.deepStrictEqual(
          fetchArgs[1].headers,
          getExpectedHeaders(clientOptions)
        );

        const prompt = utils.extractText(request);
        // extractImagenImage and extractImagenMask return undefined,
        // so JSON.stringify will omit these keys.
        const expectedInstance: any = {
          prompt,
        };
        const expectedImagenPredictRequest: ImagenPredictRequest = {
          instances: [expectedInstance],
          parameters: toImagenParameters(request),
        };

        assert.deepStrictEqual(
          JSON.parse(fetchArgs[1].body),
          expectedImagenPredictRequest
        );

        const expectedCandidates = mockResponse.predictions!.map((p, i) =>
          fromImagenPrediction(p, i)
        );
        assert.deepStrictEqual(result.candidates, expectedCandidates);
        assert.deepStrictEqual(result.usage, {
          ...getBasicUsageStats(request.messages, expectedCandidates),
          custom: { generations: 2 },
        });
        assert.deepStrictEqual(result.custom, mockResponse);
      });

      it(`should throw an error if model returns no predictions for ${clientOptions.kind}`, async () => {
        const request: GenerateRequest = {
          messages: [{ role: 'user', content: [{ text: 'A dog' }] }],
        };
        mockFetchResponse({ predictions: [] });

        const modelRunner = captureModelRunner(clientOptions);
        await assert.rejects(
          modelRunner(request, {}),
          /Model returned no predictions/
        );
        sinon.assert.calledOnce(fetchStub);
      });

      it(`should propagate network errors from fetch for ${clientOptions.kind}`, async () => {
        const request: GenerateRequest = {
          messages: [{ role: 'user', content: [{ text: 'A fish' }] }],
        };
        const error = new Error('Network Error');
        fetchStub.rejects(error);

        const modelRunner = captureModelRunner(clientOptions);
        await assert.rejects(
          modelRunner(request, {}),
          new RegExp(
            `^Error: Failed to fetch from ${escapeRegExp(expectedUrl)}: Network Error`
          )
        );
      });

      it(`should handle API error response for ${clientOptions.kind}`, async () => {
        const request: GenerateRequest = {
          messages: [{ role: 'user', content: [{ text: 'A bird' }] }],
        };
        const errorMsg = 'Invalid argument';
        const errorBody = { error: { message: errorMsg, code: 400 } };
        mockFetchResponse(errorBody, 400);

        const modelRunner = captureModelRunner(clientOptions);
        let expectedUrlRegex = escapeRegExp(expectedUrl);
        await assert.rejects(
          modelRunner(request, {}),
          new RegExp(
            `^Error: Failed to fetch from ${expectedUrlRegex}: Error fetching from ${expectedUrlRegex}: \\[400 Error\\] ${errorMsg}`
          )
        );
      });
    }

    describe('with RegionalClientOptions', () => {
      runTestsForClientOptions(regionalClientOptions);
    });

    describe('with GlobalClientOptions', () => {
      runTestsForClientOptions(globalClientOptions);
    });

    // ExpressClientOptions does not support Imagen
    // We have 'does not support' tests elsewhere
  });
});
