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
import { GENKIT_CLIENT_HEADER } from 'genkit';
import { GoogleAuth } from 'google-auth-library';
import { afterEach, beforeEach, describe, it } from 'node:test';
import * as sinon from 'sinon';
import { TextEncoder } from 'util';
import {
  embedContent,
  generateContent,
  generateContentStream,
  getVertexAIUrl,
  imagenPredict,
  listModels,
} from '../../src/vertexai/client';
import {
  ClientOptions,
  Content,
  EmbedContentRequest,
  EmbedContentResponse,
  GenerateContentRequest,
  GenerateContentResponse,
  GenerateContentStreamResult,
  ImagenPredictRequest,
  ImagenPredictResponse,
  Model,
} from '../../src/vertexai/types';

describe('Vertex AI Client', () => {
  let fetchSpy: sinon.SinonStub;
  let authMock: sinon.SinonStubbedInstance<GoogleAuth>;

  const clientOptions: ClientOptions = {
    projectId: 'test-project',
    location: 'us-central1',
    authClient: {} as GoogleAuth, // Will be replaced by mock
  };

  beforeEach(() => {
    fetchSpy = sinon.stub(global, 'fetch');
    authMock = sinon.createStubInstance(GoogleAuth);
    authMock.getAccessToken.resolves('test-token');
    clientOptions.authClient = authMock as unknown as GoogleAuth;
  });

  afterEach(() => {
    sinon.restore();
  });

  function mockFetchResponse(
    body: any,
    ok = true,
    status = 200,
    statusText = 'OK',
    contentType = 'application/json'
  ) {
    const bodyString =
      body === null || body === undefined
        ? ''
        : contentType === 'application/json'
          ? JSON.stringify(body)
          : String(body);
    const response = new Response(bodyString, {
      status: status,
      statusText: statusText,
      headers: { 'Content-Type': contentType },
    });
    fetchSpy.resolves(response);
  }

  describe('getVertexAIUrl', () => {
    const opts: ClientOptions = {
      projectId: 'test-proj',
      location: 'us-east1',
      authClient: {} as any,
    };

    it('should build URL for listModels', () => {
      const url = getVertexAIUrl({
        includeProjectAndLocation: false,
        resourcePath: 'publishers/google/models',
        clientOptions: opts,
      });
      assert.strictEqual(
        url,
        'https://us-east1-aiplatform.googleapis.com/v1beta1/publishers/google/models'
      );
    });

    it('should build URL for generateContent', () => {
      const url = getVertexAIUrl({
        includeProjectAndLocation: true,
        resourcePath: 'publishers/google/models/gemini-2.0-pro',
        resourceMethod: 'generateContent',
        clientOptions: opts,
      });
      assert.strictEqual(
        url,
        'https://us-east1-aiplatform.googleapis.com/v1beta1/projects/test-proj/locations/us-east1/publishers/google/models/gemini-2.0-pro:generateContent'
      );
    });

    it('should build URL for streamGenerateContent', () => {
      const url = getVertexAIUrl({
        includeProjectAndLocation: true,
        resourcePath: 'publishers/google/models/gemini-2.5-flash',
        resourceMethod: 'streamGenerateContent',
        clientOptions: opts,
      });
      assert.strictEqual(
        url,
        'https://us-east1-aiplatform.googleapis.com/v1beta1/projects/test-proj/locations/us-east1/publishers/google/models/gemini-2.5-flash:streamGenerateContent?alt=sse'
      );
    });

    it('should build URL for predict (embedContent)', () => {
      const url = getVertexAIUrl({
        includeProjectAndLocation: true,
        resourcePath: 'publishers/google/models/text-embedding-005',
        resourceMethod: 'predict',
        clientOptions: opts,
      });
      assert.strictEqual(
        url,
        'https://us-east1-aiplatform.googleapis.com/v1beta1/projects/test-proj/locations/us-east1/publishers/google/models/text-embedding-005:predict'
      );
    });

    it('should handle queryParams', () => {
      const url = getVertexAIUrl({
        includeProjectAndLocation: false,
        resourcePath: 'publishers/google/models',
        clientOptions: opts,
        queryParams: 'pageSize=10',
      });
      assert.strictEqual(
        url,
        'https://us-east1-aiplatform.googleapis.com/v1beta1/publishers/google/models?pageSize=10'
      );
    });
  });

  describe('Authentication Error', () => {
    it('should throw a specific error if getToken fails', async () => {
      authMock.getAccessToken.rejects(new Error('Auth failed'));
      await assert.rejects(
        listModels(clientOptions),
        /Unable to authenticate your request/
      );
    });
  });

  describe('listModels', () => {
    it('should return a list of models', async () => {
      const mockModels: Model[] = [
        { name: 'gemini-2.0-pro', launchStage: 'GA' },
        { name: 'gemini-2.5-flash', launchStage: 'GA' },
      ];
      mockFetchResponse({ publisherModels: mockModels });

      const result = await listModels(clientOptions);
      assert.deepStrictEqual(result, mockModels);

      const expectedUrl =
        'https://us-central1-aiplatform.googleapis.com/v1beta1/publishers/google/models';
      sinon.assert.calledOnceWithExactly(fetchSpy, expectedUrl, {
        method: 'GET',
        headers: {
          Authorization: 'Bearer test-token',
          'x-goog-user-project': 'test-project',
          'Content-Type': 'application/json',
          'X-Goog-Api-Client': GENKIT_CLIENT_HEADER,
        },
      });
    });

    it('should throw an error if fetch fails with JSON error', async () => {
      const errorResponse = { error: { message: 'Internal Error' } };
      mockFetchResponse(errorResponse, false, 500, 'Internal Server Error');

      await assert.rejects(
        listModels(clientOptions),
        /Failed to fetch from .* \[500 Internal Server Error\] Internal Error/
      );
    });

    it('should throw an error if fetch fails with non-JSON error', async () => {
      mockFetchResponse(
        '<h1>Gateway Timeout</h1>',
        false,
        504,
        'Gateway Timeout',
        'text/html'
      );

      await assert.rejects(
        listModels(clientOptions),
        /Failed to fetch from .* \[504 Gateway Timeout\] <h1>Gateway Timeout<\/h1>/
      );
    });

    it('should throw an error if fetch fails with empty response body', async () => {
      mockFetchResponse(null, false, 502, 'Bad Gateway');

      await assert.rejects(
        listModels(clientOptions),
        /Failed to fetch from .* \[502 Bad Gateway\] $/
      );
    });

    it('should throw an error on network failure', async () => {
      fetchSpy.rejects(new Error('Network Error'));
      await assert.rejects(
        listModels(clientOptions),
        /Failed to fetch from .* Network Error/
      );
    });
  });

  describe('generateContent', () => {
    const request: GenerateContentRequest = {
      contents: [{ role: 'user', parts: [{ text: 'hello' }] }],
    };
    const model = 'gemini-2.0-pro';

    it('should return GenerateContentResponse', async () => {
      const mockResponse: GenerateContentResponse = {
        candidates: [
          { index: 0, content: { role: 'model', parts: [{ text: 'world' }] } },
        ],
      };
      mockFetchResponse(mockResponse);

      const result = await generateContent(model, request, clientOptions);
      assert.deepStrictEqual(result, mockResponse);

      const expectedUrl =
        'https://us-central1-aiplatform.googleapis.com/v1beta1/projects/test-project/locations/us-central1/publishers/google/models/gemini-2.0-pro:generateContent';
      sinon.assert.calledOnceWithExactly(fetchSpy, expectedUrl, {
        method: 'POST',
        headers: {
          Authorization: 'Bearer test-token',
          'x-goog-user-project': 'test-project',
          'Content-Type': 'application/json',
          'X-Goog-Api-Client': GENKIT_CLIENT_HEADER,
        },
        body: JSON.stringify(request),
      });
    });

    it('should throw on API error with JSON body', async () => {
      const errorResponse = { error: { message: 'Permission denied' } };
      mockFetchResponse(errorResponse, false, 403, 'Forbidden');

      await assert.rejects(
        generateContent(model, request, clientOptions),
        /Failed to fetch from .* \[403 Forbidden\] Permission denied/
      );
    });

    it('should throw on API error with non-JSON body', async () => {
      mockFetchResponse('Forbidden', false, 403, 'Forbidden', 'text/plain');

      await assert.rejects(
        generateContent(model, request, clientOptions),
        /Failed to fetch from .* \[403 Forbidden\] Forbidden/
      );
    });
  });

  describe('embedContent', () => {
    const request: EmbedContentRequest = {
      instances: [{ content: 'test content' }],
      parameters: {},
    };
    const model = 'text-embedding-005';

    it('should return EmbedContentResponse', async () => {
      const mockResponse: EmbedContentResponse = {
        predictions: [
          {
            embeddings: {
              statistics: { truncated: false, token_count: 3 },
              values: [0.1, 0.2, 0.3],
            },
          },
        ],
      };
      mockFetchResponse(mockResponse);

      const result = await embedContent(model, request, clientOptions);
      assert.deepStrictEqual(result, mockResponse);

      const expectedUrl =
        'https://us-central1-aiplatform.googleapis.com/v1beta1/projects/test-project/locations/us-central1/publishers/google/models/text-embedding-005:predict';
      sinon.assert.calledOnceWithExactly(fetchSpy, expectedUrl, {
        method: 'POST',
        headers: {
          Authorization: 'Bearer test-token',
          'x-goog-user-project': 'test-project',
          'Content-Type': 'application/json',
          'X-Goog-Api-Client': GENKIT_CLIENT_HEADER,
        },
        body: JSON.stringify(request),
      });
    });

    it('should throw on API error non-JSON', async () => {
      mockFetchResponse('Not Found', false, 404, 'Not Found', 'text/plain');
      await assert.rejects(
        embedContent(model, request, clientOptions),
        /Failed to fetch from .* \[404 Not Found\] Not Found/
      );
    });
  });

  describe('imagenPredict', () => {
    const request: ImagenPredictRequest = {
      instances: [{ prompt: 'a cat' }],
      parameters: { sampleCount: 1 },
    };
    const model = 'imagen-3.0-generate-002';

    it('should return ImagenPredictResponse', async () => {
      const mockResponse: ImagenPredictResponse = {
        predictions: [{ bytesBase64Encoded: 'abc', mimeType: 'image/png' }],
      };
      mockFetchResponse(mockResponse);

      const result = await imagenPredict(model, request, clientOptions);
      assert.deepStrictEqual(result, mockResponse);

      const expectedUrl =
        'https://us-central1-aiplatform.googleapis.com/v1beta1/projects/test-project/locations/us-central1/publishers/google/models/imagen-3.0-generate-002:predict';
      sinon.assert.calledOnceWithExactly(fetchSpy, expectedUrl, {
        method: 'POST',
        headers: {
          Authorization: 'Bearer test-token',
          'x-goog-user-project': 'test-project',
          'Content-Type': 'application/json',
          'X-Goog-Api-Client': GENKIT_CLIENT_HEADER,
        },
        body: JSON.stringify(request),
      });
    });

    it('should throw on API error non-JSON', async () => {
      mockFetchResponse('Bad Request', false, 400, 'Bad Request', 'text/plain');
      await assert.rejects(
        imagenPredict(model, request, clientOptions),
        /Failed to fetch from .* \[400 Bad Request\] Bad Request/
      );
    });
  });

  describe('generateContentStream', () => {
    function createMockStream(chunks: string[]): Response {
      const stream = new ReadableStream({
        start(controller) {
          for (const chunk of chunks) {
            controller.enqueue(new TextEncoder().encode(chunk));
          }
          controller.close();
        },
      });
      return new Response(stream, {
        headers: { 'Content-Type': 'application/json' },
      });
    }

    it('should process stream and return stream and aggregated response', async () => {
      const request: GenerateContentRequest = {
        contents: [{ role: 'user', parts: [{ text: 'stream' }] }],
      };
      const chunks = [
        'data: {"candidates": [{"index": 0, "content": {"role": "model", "parts": [{"text": "Hello "}]}}]}\n\n',
        'data: {"candidates": [{"index": 0, "content": {"role": "model", "parts": [{"text": "World!"}]}}], "usageMetadata": {"totalTokenCount": 10}}\n\n',
      ];
      fetchSpy.resolves(createMockStream(chunks));

      const result: GenerateContentStreamResult = await generateContentStream(
        'gemini-2.5-flash',
        request,
        clientOptions
      );

      const streamResults: GenerateContentResponse[] = [];
      for await (const item of result.stream) {
        streamResults.push(item);
      }

      assert.deepStrictEqual(streamResults, [
        {
          candidates: [
            {
              index: 0,
              content: {
                role: 'model',
                parts: [{ text: 'Hello ' }],
              } as Content,
            } as any,
          ],
        },
        {
          candidates: [
            {
              index: 0,
              content: {
                role: 'model',
                parts: [{ text: 'World!' }],
              } as Content,
            } as any,
          ],
          usageMetadata: { totalTokenCount: 10 },
        },
      ]);

      const aggregated = await result.response;
      assert.deepStrictEqual(aggregated, {
        candidates: [
          {
            index: 0,
            content: { role: 'model', parts: [{ text: 'Hello World!' }] },
          },
        ],
        usageMetadata: { totalTokenCount: 10 },
      });

      const expectedUrl =
        'https://us-central1-aiplatform.googleapis.com/v1beta1/projects/test-project/locations/us-central1/publishers/google/models/gemini-2.5-flash:streamGenerateContent?alt=sse';
      sinon.assert.calledOnceWithExactly(fetchSpy, expectedUrl, {
        method: 'POST',
        headers: {
          Authorization: 'Bearer test-token',
          'x-goog-user-project': 'test-project',
          'Content-Type': 'application/json',
          'X-Goog-Api-Client': GENKIT_CLIENT_HEADER,
        },
        body: JSON.stringify(request),
      });
    });

    it('should handle stream with malformed JSON', async () => {
      const request: GenerateContentRequest = {
        contents: [{ role: 'user', parts: [{ text: 'stream' }] }],
      };
      const chunks = [
        'data: {"candidates": [{"index": 0, "content": {"role": "model", "parts": [{"text": "Hello "}]}}]}\n\n',
        'data: {"candi dates": []}}}}\n\n', // Malformed
      ];
      fetchSpy.resolves(createMockStream(chunks));

      const result: GenerateContentStreamResult = await generateContentStream(
        'gemini-2.5-flash',
        request,
        clientOptions
      );

      const streamResults: GenerateContentResponse[] = [];
      try {
        for await (const item of result.stream) {
          streamResults.push(item);
        }
        assert.fail('Stream should have thrown an error');
      } catch (e: any) {
        assert.match(
          e.message,
          /Error parsing JSON response from stream chunk/
        );
      }

      try {
        await result.response;
        assert.fail('Response promise should have thrown an error');
      } catch (e: any) {
        assert.match(
          e.message,
          /Error parsing JSON response from stream chunk/
        );
      }
    });

    it('should handle stream error in fetch', async () => {
      const request: GenerateContentRequest = { contents: [] };
      fetchSpy.rejects(new Error('Network failure'));

      await assert.rejects(
        generateContentStream('gemini-2.5-flash', request, clientOptions),
        /Failed to fetch from .* Network failure/
      );
    });

    it('should aggregate parts for multiple candidates', async () => {
      const request: GenerateContentRequest = {
        contents: [{ role: 'user', parts: [{ text: 'stream' }] }],
      };
      const chunks = [
        'data: {"candidates": [{"index": 0, "content": {"role": "model", "parts": [{"text": "C0 A"}]}}, {"index": 1, "content": {"role": "model", "parts": [{"text": "C1 A"}]}}]}\n\n',
        'data: {"candidates": [{"index": 0, "content": {"role": "model", "parts": [{"text": " C0 B"}]}}, {"index": 1, "content": {"role": "model", "parts": [{"text": " C1 B"}]}}]}\n\n',
      ];
      fetchSpy.resolves(createMockStream(chunks));
      const result = await generateContentStream(
        'gemini-2.5-flash',
        request,
        clientOptions
      );
      const aggregated = await result.response;

      assert.strictEqual(aggregated.candidates?.length, 2);
      const sortedCandidates = aggregated.candidates!.sort(
        (a, b) => a.index - b.index
      );

      assert.deepStrictEqual(sortedCandidates[0], {
        index: 0,
        content: { role: 'model', parts: [{ text: 'C0 A C0 B' }] },
      });
      assert.deepStrictEqual(sortedCandidates[1], {
        index: 1,
        content: { role: 'model', parts: [{ text: 'C1 A C1 B' }] },
      });
    });

    it('should aggregate functionCall parts, keeping text first', async () => {
      const request: GenerateContentRequest = {
        contents: [{ role: 'user', parts: [{ text: 'stream' }] }],
      };
      const chunks = [
        'data: {"candidates": [{"index": 0, "content": { "role": "model", "parts": [{"text": "A"}]}}]}\n\n',
        'data: {"candidates": [{"index": 0, "content": { "role": "model", "parts": [{"functionCall": {"name": "tool1", "args": {}}}]}}]}\n\n',
        'data: {"candidates": [{"index": 0, "content": { "role": "model", "parts": [{"text": "B"}]}}]}\n\n',
      ];
      fetchSpy.resolves(createMockStream(chunks));
      const result = await generateContentStream(
        'gemini-2.5-flash',
        request,
        clientOptions
      );
      const aggregated = await result.response;
      assert.deepStrictEqual(aggregated.candidates![0].content.parts, [
        { text: 'AB' },
        { functionCall: { name: 'tool1', args: {} } },
      ]);
    });

    it('should remove empty first text part if other parts exist', async () => {
      const request: GenerateContentRequest = {
        contents: [{ role: 'user', parts: [{ text: 'stream' }] }],
      };
      const chunks = [
        'data: {"candidates": [{"index": 0, "content": { "role": "model", "parts": [{"functionCall": {"name": "tool1", "args": {}}}]}}]}\n\n',
      ];
      fetchSpy.resolves(createMockStream(chunks));
      const result = await generateContentStream(
        'gemini-2.5-flash',
        request,
        clientOptions
      );
      const aggregated = await result.response;
      assert.deepStrictEqual(aggregated.candidates![0].content.parts, [
        { functionCall: { name: 'tool1', args: {} } },
      ]);
    });

    it('should aggregate citation metadata', async () => {
      const request: GenerateContentRequest = {
        contents: [{ role: 'user', parts: [{ text: 'stream' }] }],
      };
      const chunks = [
        'data: {"candidates": [{"index": 0, "content": { "role": "model", "parts": [{"text": "."}] }, "citationMetadata": { "citations": [{"uri": "u1"}]}}]}\n\n',
        'data: {"candidates": [{"index": 0, "content": { "role": "model", "parts": [{"text": "."}] }, "citationMetadata": { "citations": [{"uri": "u2"}]}}]}\n\n',
      ];
      fetchSpy.resolves(createMockStream(chunks));
      const result = await generateContentStream(
        'gemini-2.5-flash',
        request,
        clientOptions
      );
      const aggregated = await result.response;
      assert.deepStrictEqual(aggregated.candidates![0].citationMetadata, {
        citations: [{ uri: 'u1' }, { uri: 'u2' }],
      });
    });

    it('should aggregate grounding metadata', async () => {
      const request: GenerateContentRequest = {
        contents: [{ role: 'user', parts: [{ text: 'stream' }] }],
      };
      const chunks = [
        'data: {"candidates": [{"index": 0, "content": { "role": "model", "parts": [{"text": "."}] }, "groundingMetadata": { "webSearchQueries": ["q1"]}}]}\n\n',
        'data: {"candidates": [{"index": 0, "content": { "role": "model", "parts": [{"text": "."}] }, "groundingMetadata": { "webSearchQueries": ["q2"], "retrievalQueries": ["rq1"], "searchEntryPoint": { "renderedContent": "test" } }}]}\n\n',
        'data: {"candidates": [{"index": 0, "content": { "role": "model", "parts": [{"text": "."}] }, "groundingMetadata": { "groundingChunks": [{"web": {"uri": "u1"}}], "groundingSupports": [{"segment": {"text": "s1"}}]}}]}\n\n',
      ];
      fetchSpy.resolves(createMockStream(chunks));
      const result = await generateContentStream(
        'gemini-2.5-flash',
        request,
        clientOptions
      );
      const aggregated = await result.response;
      assert.deepStrictEqual(aggregated.candidates![0].groundingMetadata, {
        webSearchQueries: ['q1', 'q2'],
        retrievalQueries: ['rq1'],
        groundingChunks: [{ web: { uri: 'u1' } }],
        groundingSupports: [{ segment: { text: 's1' } }],
        searchEntryPoint: { renderedContent: 'test' },
      });
    });
    it('should take last finishReason, finishMessage, and safetyRatings', async () => {
      const request: GenerateContentRequest = {
        contents: [{ role: 'user', parts: [{ text: 'stream' }] }],
      };
      const chunks = [
        'data: {"candidates": [{"index": 0, "content": { "role": "model", "parts": [{"text": "A"}] }, "finishReason": "STOP" }]}\n\n',
        'data: {"candidates": [{"index": 0, "content": { "role": "model", "parts": [{"text": "B"}] }, "finishReason": "MAX_TOKENS", "finishMessage": "Done", "safetyRatings": [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "probability": "LOW"}] }]}\n\n',
      ];
      fetchSpy.resolves(createMockStream(chunks));
      const result = await generateContentStream(
        'gemini-2.5-flash',
        request,
        clientOptions
      );
      const aggregated = await result.response;
      assert.strictEqual(aggregated.candidates![0].finishReason, 'MAX_TOKENS');
      assert.strictEqual(aggregated.candidates![0].finishMessage, 'Done');
      assert.deepStrictEqual(aggregated.candidates![0].safetyRatings, [
        { category: 'HARM_CATEGORY_DANGEROUS_CONTENT', probability: 'LOW' },
      ]);
    });

    it('handles candidates appearing in later chunks', async () => {
      const request: GenerateContentRequest = {
        contents: [{ role: 'user', parts: [{ text: 'stream' }] }],
      };
      const chunks = [
        'data: {"candidates": []}\n\n',
        'data: {"candidates": [{"index": 0, "content": { "role": "model", "parts": [{"text": "A"}]}}]}\n\n',
      ];
      fetchSpy.resolves(createMockStream(chunks));
      const result = await generateContentStream(
        'gemini-2.5-flash',
        request,
        clientOptions
      );
      const aggregated = await result.response;
      assert.deepStrictEqual(aggregated.candidates![0].content.parts, [
        { text: 'A' },
      ]);
    });
  });
});
