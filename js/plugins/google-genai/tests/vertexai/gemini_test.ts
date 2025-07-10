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
import { Genkit, z } from 'genkit';
import { GenerateRequest, ModelReference } from 'genkit/model';
import { AsyncLocalStorage } from 'node:async_hooks';
import { afterEach, beforeEach, describe, it } from 'node:test';
import * as sinon from 'sinon';
import { FinishReason } from '../../src/common/types';
import {
  GeminiConfigSchema,
  defineModel,
  model,
} from '../../src/vertexai/gemini';
import {
  ClientOptions,
  GenerateContentRequest,
  GenerateContentResponse,
  HarmBlockThreshold,
  HarmCategory,
} from '../../src/vertexai/types';

describe('Vertex AI Gemini', () => {
  let mockGenkit: sinon.SinonStubbedInstance<Genkit>;
  let modelActionCallback: (
    request: GenerateRequest<typeof GeminiConfigSchema>,
    sendChunk?: (chunk: any) => void
  ) => Promise<any>;

  let fetchStub: sinon.SinonStub;
  let mockAsyncStore: sinon.SinonStubbedInstance<AsyncLocalStorage<any>>;

  const defaultClientOptions: ClientOptions = {
    projectId: 'test-project',
    location: 'us-central1',
    authClient: {
      getAccessToken: async () => 'test-token',
    } as any, // Mock auth client
  };

  beforeEach(() => {
    mockGenkit = sinon.createStubInstance(Genkit);
    mockAsyncStore = sinon.createStubInstance(AsyncLocalStorage);

    // Setup mock registry and asyncStore
    mockAsyncStore.getStore.returns(undefined); // Simulate no parent span

    mockAsyncStore.run.callsFake((arg1, arg2, callback) => {
      if (typeof callback === 'function') {
        return callback();
      }
      // Fallback or error if the structure isn't as expected
      throw new Error(
        'AsyncLocalStorage.run mock expected a function as the third argument'
      );
    });

    (mockGenkit as any).registry = {
      lookupAction: () => undefined,
      lookupFlow: () => undefined,
      generateTraceId: () => 'test-trace-id',
      asyncStore: mockAsyncStore, // Provide the mock asyncStore
    };

    fetchStub = sinon.stub(global, 'fetch');

    mockGenkit.defineModel.callsFake((config, func) => {
      modelActionCallback = func;
      return { name: config.name } as any;
    });
  });

  afterEach(() => {
    sinon.restore();
  });

  // Mock fetch for non-streaming responses
  function mockFetchResponse(body: any, status = 200) {
    const response = new Response(JSON.stringify(body), {
      status: status,
      statusText: status === 200 ? 'OK' : 'Error',
      headers: { 'Content-Type': 'application/json' },
    });
    fetchStub.resolves(Promise.resolve(response));
  }

  // Mock fetch for streaming responses (SSE)
  function mockFetchStreamResponse(responses: GenerateContentResponse[]) {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        for (const response of responses) {
          const chunk = `data: ${JSON.stringify(response)}\n\n`;
          controller.enqueue(encoder.encode(chunk));
        }
        controller.close();
      },
    });

    const response = new Response(stream, {
      status: 200,
      statusText: 'OK',
      headers: { 'Content-Type': 'text/event-stream' },
    });
    fetchStub.resolves(Promise.resolve(response));
  }

  const minimalRequest: GenerateRequest<typeof GeminiConfigSchema> = {
    messages: [{ role: 'user', content: [{ text: 'Hello' }] }],
    config: {}, // Add empty config
  };

  const mockCandidate = {
    index: 0,
    content: { role: 'model', parts: [{ text: 'Hi there' }] },
    finishReason: FinishReason.STOP,
  };

  const defaultApiResponse: GenerateContentResponse = {
    candidates: [mockCandidate],
  };

  describe('gemini() function', () => {
    it('returns a ModelReference for a known model string', () => {
      const name = 'gemini-2.0-flash';
      const modelRef: ModelReference<typeof GeminiConfigSchema> = model(name);
      assert.strictEqual(modelRef.name, `vertexai/${name}`);
      assert.ok(modelRef.info?.supports?.multiturn);
      assert.strictEqual(modelRef.configSchema, GeminiConfigSchema);
    });

    it('returns a ModelReference for an unknown model string', () => {
      const name = 'gemini-new-model';
      const modelRef: ModelReference<typeof GeminiConfigSchema> = model(name);
      assert.strictEqual(modelRef.name, `vertexai/${name}`);
      assert.ok(modelRef.info?.supports?.multiturn); // Defaults to generic
      assert.strictEqual(modelRef.configSchema, GeminiConfigSchema);
    });

    it('applies options to the ModelReference', () => {
      const options = { temperature: 0.9, topK: 20 };
      const modelRef: ModelReference<typeof GeminiConfigSchema> = model(
        'gemini-2.0-flash',
        options
      );
      assert.deepStrictEqual(modelRef.config, options);
    });
  });

  describe('defineGeminiModel', () => {
    it('defines a model with the correct name', () => {
      defineModel(mockGenkit, 'gemini-2.0-flash', defaultClientOptions);
      sinon.assert.calledOnce(mockGenkit.defineModel);
      const args = mockGenkit.defineModel.lastCall.args[0];
      assert.strictEqual(args.name, 'vertexai/gemini-2.0-flash');
    });

    it('defines a model with a custom name', () => {
      defineModel(mockGenkit, 'my-custom-gemini', defaultClientOptions);
      const args = mockGenkit.defineModel.lastCall.args[0];
      assert.strictEqual(args.name, 'vertexai/my-custom-gemini');
    });

    describe('Model Action Callback', () => {
      beforeEach(() => {
        defineModel(mockGenkit, 'gemini-2.5-flash', defaultClientOptions);
      });

      it('throws if no messages are provided', async () => {
        await assert.rejects(
          modelActionCallback({ messages: [], config: {} }),
          /No messages provided/
        );
      });

      it('calls fetch for non-streaming requests', async () => {
        mockFetchResponse(defaultApiResponse);
        const result = await modelActionCallback(minimalRequest);

        sinon.assert.calledOnce(fetchStub);
        const fetchArgs = fetchStub.lastCall.args;
        const url = fetchArgs[0];
        const options = fetchArgs[1];

        assert.ok(
          url.includes(
            'us-central1-aiplatform.googleapis.com/v1beta1/projects/test-project/locations/us-central1/publishers/google/models/gemini-2.5-flash:generateContent'
          )
        );
        assert.strictEqual(options.method, 'POST');
        const body = JSON.parse(options.body);
        assert.deepStrictEqual(body.contents, [
          { role: 'user', parts: [{ text: 'Hello' }] },
        ]);

        assert.strictEqual(result.candidates.length, 1);
        assert.strictEqual(
          result.candidates[0].message.content[0].text,
          'Hi there'
        );
      });

      it('calls fetch for streaming requests', async () => {
        mockFetchStreamResponse([defaultApiResponse]);

        const sendChunkSpy = sinon.spy();
        await modelActionCallback(minimalRequest, sendChunkSpy);

        sinon.assert.calledOnce(fetchStub);
        const fetchArgs = fetchStub.lastCall.args;
        const url = fetchArgs[0];
        assert.ok(
          url.includes(
            'us-central1-aiplatform.googleapis.com/v1beta1/projects/test-project/locations/us-central1/publishers/google/models/gemini-2.5-flash:streamGenerateContent'
          )
        );
        assert.ok(url.includes('alt=sse'));

        await new Promise((resolve) => setTimeout(resolve, 10));

        sinon.assert.calledOnce(sendChunkSpy);
        const chunkArg = sendChunkSpy.lastCall.args[0];
        assert.deepStrictEqual(chunkArg, {
          index: 0,
          content: [{ text: 'Hi there' }],
        });
      });

      it('handles system instructions', async () => {
        mockFetchResponse(defaultApiResponse);
        const request: GenerateRequest<typeof GeminiConfigSchema> = {
          messages: [
            { role: 'system', content: [{ text: 'Be concise' }] },
            { role: 'user', content: [{ text: 'Hello' }] },
          ],
          config: {},
        };
        await modelActionCallback(request);

        const apiRequest: GenerateContentRequest = JSON.parse(
          fetchStub.lastCall.args[1].body
        );
        assert.deepStrictEqual(apiRequest.systemInstruction, {
          role: 'user',
          parts: [{ text: 'Be concise' }],
        });
        assert.deepStrictEqual(apiRequest.contents, [
          { role: 'user', parts: [{ text: 'Hello' }] },
        ]);
      });

      it('merges config from request', async () => {
        mockFetchResponse(defaultApiResponse);
        const request: GenerateRequest<typeof GeminiConfigSchema> = {
          ...minimalRequest,
          config: { temperature: 0.1, topP: 0.8, maxOutputTokens: 100 },
        };
        await modelActionCallback(request);

        const apiRequest: GenerateContentRequest = JSON.parse(
          fetchStub.lastCall.args[1].body
        );
        assert.strictEqual(apiRequest.generationConfig?.temperature, 0.1);
        assert.strictEqual(apiRequest.generationConfig?.topP, 0.8);
        assert.strictEqual(apiRequest.generationConfig?.maxOutputTokens, 100);
      });

      it('constructs tools array with functionDeclarations', async () => {
        mockFetchResponse(defaultApiResponse);
        const request: GenerateRequest<typeof GeminiConfigSchema> = {
          ...minimalRequest,
          tools: [
            {
              name: 'myFunc',
              description: 'Does something',
              inputSchema: z.object({ foo: z.string() }),
              outputSchema: z.string(),
            },
          ],
          config: {},
        };
        await modelActionCallback(request);

        const apiRequest: GenerateContentRequest = JSON.parse(
          fetchStub.lastCall.args[1].body
        );
        assert.ok(Array.isArray(apiRequest.tools));
        assert.strictEqual(apiRequest.tools?.length, 1);
        assert.ok(apiRequest.tools?.[0].functionDeclarations);
        assert.strictEqual(
          apiRequest.tools?.[0].functionDeclarations?.length,
          1
        );
        assert.strictEqual(
          apiRequest.tools?.[0].functionDeclarations?.[0].name,
          'myFunc'
        );
      });

      it('handles googleSearchRetrieval tool for gemini-1.5', async () => {
        defineModel(mockGenkit, 'gemini-1.5-pro', defaultClientOptions);
        mockFetchResponse(defaultApiResponse);
        const request: GenerateRequest<typeof GeminiConfigSchema> = {
          ...minimalRequest,
          config: {
            googleSearchRetrieval: {},
          },
        };
        await modelActionCallback(request);
        const apiRequest: GenerateContentRequest = JSON.parse(
          fetchStub.lastCall.args[1].body
        );
        const searchTool = apiRequest.tools?.find(
          (t) => t.googleSearchRetrieval
        );
        assert.ok(searchTool, 'Expected googleSearchRetrieval tool');
        assert.deepStrictEqual(searchTool, { googleSearchRetrieval: {} });
      });

      it('handles googleSearchRetrieval tool for other models (as googleSearch)', async () => {
        mockFetchResponse(defaultApiResponse);
        const request: GenerateRequest<typeof GeminiConfigSchema> = {
          ...minimalRequest,
          config: {
            googleSearchRetrieval: {},
          },
        };
        await modelActionCallback(request);
        const apiRequest: GenerateContentRequest = JSON.parse(
          fetchStub.lastCall.args[1].body
        );
        const searchTool = apiRequest.tools?.find((t) => t.googleSearch);
        assert.ok(searchTool, 'Expected googleSearch tool');
        assert.deepStrictEqual(searchTool, { googleSearch: {} });
      });

      it('handles vertexRetrieval tool', async () => {
        mockFetchResponse(defaultApiResponse);
        const request: GenerateRequest<typeof GeminiConfigSchema> = {
          ...minimalRequest,
          config: {
            vertexRetrieval: {
              datastore: { dataStoreId: 'my-store' },
              disableAttribution: true,
            },
          },
        };
        await modelActionCallback(request);
        const apiRequest: GenerateContentRequest = JSON.parse(
          fetchStub.lastCall.args[1].body
        );
        const retrievalTool = apiRequest.tools?.find((t) => t.retrieval);
        assert.ok(retrievalTool, 'Expected vertexRetrieval tool');
        assert.deepStrictEqual(retrievalTool, {
          retrieval: {
            vertexAiSearch: {
              datastore:
                'projects/test-project/locations/us-central1/collections/default_collection/dataStores/my-store',
            },
            disableAttribution: true,
          },
        });
      });

      it('applies safetySettings', async () => {
        mockFetchResponse(defaultApiResponse);
        const request: GenerateRequest<typeof GeminiConfigSchema> = {
          ...minimalRequest,
          config: {
            safetySettings: [
              {
                category: 'HARM_CATEGORY_HATE_SPEECH',
                threshold: 'BLOCK_ONLY_HIGH',
              },
            ],
          },
        };
        await modelActionCallback(request);
        const apiRequest: GenerateContentRequest = JSON.parse(
          fetchStub.lastCall.args[1].body
        );
        assert.deepStrictEqual(apiRequest.safetySettings, [
          {
            category: HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold: HarmBlockThreshold.BLOCK_ONLY_HIGH,
          },
        ]);
      });

      it('handles JSON output mode', async () => {
        mockFetchResponse(defaultApiResponse);
        const request: GenerateRequest<typeof GeminiConfigSchema> = {
          ...minimalRequest,
          output: { format: 'json' },
          config: {},
        };
        await modelActionCallback(request);
        const apiRequest: GenerateContentRequest = JSON.parse(
          fetchStub.lastCall.args[1].body
        );
        assert.strictEqual(
          apiRequest.generationConfig?.responseMimeType,
          'application/json'
        );
      });

      it('throws if no candidates are returned', async () => {
        mockFetchResponse({ candidates: [] });
        await assert.rejects(
          modelActionCallback(minimalRequest),
          /No valid candidates returned/
        );
      });

      it('handles API call error', async () => {
        fetchStub.rejects(new Error('API Error'));
        await assert.rejects(
          modelActionCallback(minimalRequest),
          /Failed to fetch from https:\/\/us-central1-aiplatform.googleapis.com\/v1beta1\/projects\/test-project\/locations\/us-central1\/publishers\/google\/models\/gemini-2.5-flash:generateContent: API Error/
        );
      });
    });

    describe('Debug Traces', () => {
      it('API call works with debugTraces: true', async () => {
        defineModel(mockGenkit, 'gemini-2.5-flash', defaultClientOptions, {
          location: 'us-central1',
          experimental_debugTraces: true,
        });
        mockFetchResponse(defaultApiResponse);

        await assert.doesNotReject(modelActionCallback(minimalRequest));
        sinon.assert.calledOnce(fetchStub);
      });

      it('API call works without extra logging with debugTraces: false', async () => {
        defineModel(mockGenkit, 'gemini-2.0-flash', defaultClientOptions, {
          location: 'us-central1',
          experimental_debugTraces: false,
        });
        mockFetchResponse(defaultApiResponse);

        await assert.doesNotReject(modelActionCallback(minimalRequest));
        sinon.assert.calledOnce(fetchStub);
      });
    });
  });
});
