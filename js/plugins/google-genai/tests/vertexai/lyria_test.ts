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
import { Genkit } from 'genkit';
import { GenerateRequest } from 'genkit/model';
import { GoogleAuth } from 'google-auth-library';
import { afterEach, beforeEach, describe, it } from 'node:test';
import * as sinon from 'sinon';
import { getGenkitClientHeader } from '../../src/common/utils.js';
import { getVertexAIUrl } from '../../src/vertexai/client.js';
import {
  fromLyriaResponse,
  toLyriaPredictRequest,
} from '../../src/vertexai/converters.js';
import {
  LyriaConfigSchema,
  TEST_ONLY,
  defineModel,
  model,
} from '../../src/vertexai/lyria.js';
import {
  LyriaPredictResponse,
  RegionalClientOptions,
} from '../../src/vertexai/types.js';

const { GENERIC_MODEL, KNOWN_MODELS } = TEST_ONLY;

describe('Vertex AI Lyria', () => {
  let mockGenkit: sinon.SinonStubbedInstance<Genkit>;
  let fetchStub: sinon.SinonStub;
  let authMock: sinon.SinonStubbedInstance<GoogleAuth>;
  let modelActionCallback: (
    request: GenerateRequest<typeof LyriaConfigSchema>,
    options: {
      abortSignal?: AbortSignal;
    }
  ) => Promise<any>;

  const modelName = 'lyria-test-model';

  const defaultRegionalClientOptions: RegionalClientOptions = {
    kind: 'regional',
    projectId: 'test-project',
    location: 'us-central1',
    authClient: {} as any,
  };

  beforeEach(() => {
    mockGenkit = sinon.createStubInstance(Genkit);
    fetchStub = sinon.stub(global, 'fetch');
    authMock = sinon.createStubInstance(GoogleAuth);

    authMock.getAccessToken.resolves('test-token');
    defaultRegionalClientOptions.authClient = authMock as unknown as GoogleAuth;

    mockGenkit.defineModel.callsFake((config: any, func: any) => {
      modelActionCallback = func;
      return { name: config.name } as any;
    });
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

  function getExpectedHeaders(): Record<string, string> {
    return {
      'Content-Type': 'application/json',
      'X-Goog-Api-Client': getGenkitClientHeader(),
      'User-Agent': getGenkitClientHeader(),
      Authorization: 'Bearer test-token',
      'x-goog-user-project': defaultRegionalClientOptions.projectId,
    };
  }

  describe('model()', () => {
    it('should return a ModelReference for a known model', () => {
      const knownModelName = Object.keys(KNOWN_MODELS)[0];
      const ref = model(knownModelName);
      assert.strictEqual(ref.name, `vertexai/${knownModelName}`);
      assert.ok(ref.info?.supports?.media);
      assert.deepStrictEqual(ref.info?.supports?.output, ['media']);
    });

    it('should return a ModelReference for an unknown model using generic info', () => {
      const unknownModelName = 'lyria-unknown-model';
      const ref = model(unknownModelName);
      assert.strictEqual(ref.name, `vertexai/${unknownModelName}`);
      assert.deepStrictEqual(ref.info, GENERIC_MODEL.info);
    });

    it('should apply config to a known model', () => {
      const knownModelName = Object.keys(KNOWN_MODELS)[0];
      const config = { negativePrompt: 'noisy' };
      const ref = model(knownModelName, config);
      assert.strictEqual(ref.name, `vertexai/${knownModelName}`);
      assert.deepStrictEqual(ref.config, config);
    });
  });

  describe('defineModel()', () => {
    beforeEach(() => {
      defineModel(mockGenkit, modelName, defaultRegionalClientOptions);
      sinon.assert.calledOnce(mockGenkit.defineModel);
      const args = mockGenkit.defineModel.lastCall.args[0];
      assert.strictEqual(args.name, `vertexai/${modelName}`);
    });

    const prompt = 'A funky bass line';
    const minimalRequest: GenerateRequest<typeof LyriaConfigSchema> = {
      messages: [{ role: 'user', content: [{ text: prompt }] }],
      config: { sampleCount: 2 },
    };

    const mockPrediction: LyriaPredictResponse = {
      predictions: [
        {
          bytesBase64Encoded: 'base64audio1',
          mimeType: 'audio/wav',
        },
        {
          bytesBase64Encoded: 'base64audio2',
          mimeType: 'audio/wav',
        },
      ],
    };

    it('should call fetch with correct params and return lyria response', async () => {
      mockFetchResponse(mockPrediction);

      const result = await modelActionCallback(minimalRequest, {});

      sinon.assert.calledOnce(fetchStub);
      const fetchArgs = fetchStub.lastCall.args;
      const url = fetchArgs[0];
      const options = fetchArgs[1];

      const expectedUrl = getVertexAIUrl({
        includeProjectAndLocation: true,
        resourcePath: `publishers/google/models/${modelName}`,
        resourceMethod: 'predict',
        clientOptions: defaultRegionalClientOptions,
      });
      assert.strictEqual(url, expectedUrl);
      assert.strictEqual(options.method, 'POST');
      assert.deepStrictEqual(options.headers, getExpectedHeaders());

      const expectedPredictRequest = toLyriaPredictRequest(minimalRequest);
      assert.deepStrictEqual(JSON.parse(options.body), expectedPredictRequest);

      const expectedResponse = fromLyriaResponse(
        mockPrediction,
        minimalRequest
      );
      assert.deepStrictEqual(result, expectedResponse);
      assert.strictEqual(result.candidates?.length, 2);
      assert.strictEqual(
        result.candidates[0].message.content[0].media?.url,
        'data:audio/wav;base64,base64audio1'
      );
    });

    it('should throw if no predictions are returned', async () => {
      mockFetchResponse({ predictions: [] });
      await assert.rejects(
        modelActionCallback(minimalRequest, {}),
        /Model returned no predictions/
      );
    });

    it('should propagate API errors', async () => {
      const errorBody = { error: { message: 'Quota exceeded', code: 429 } };
      mockFetchResponse(errorBody, 429);

      await assert.rejects(
        modelActionCallback(minimalRequest, {}),
        /Error fetching from .*predict.* Quota exceeded/
      );
    });

    it('should pass AbortSignal to fetch', async () => {
      mockFetchResponse(mockPrediction);
      const controller = new AbortController();
      const abortSignal = controller.signal;

      // We need to re-register to pass the clientOptions with the signal
      const clientOptionsWithSignal = {
        ...defaultRegionalClientOptions,
        signal: abortSignal,
      };
      defineModel(mockGenkit, modelName, clientOptionsWithSignal);

      await modelActionCallback(minimalRequest, { abortSignal });

      sinon.assert.calledOnce(fetchStub);
      const fetchOptions = fetchStub.lastCall.args[1];
      assert.ok(fetchOptions.signal, 'Fetch options should have a signal');

      const fetchSignal = fetchOptions.signal;
      const abortSpy = sinon.spy();
      fetchSignal.addEventListener('abort', abortSpy);

      controller.abort();
      sinon.assert.calledOnce(abortSpy);
    });
  });
});
