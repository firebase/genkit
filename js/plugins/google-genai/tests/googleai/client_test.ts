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
import { afterEach, beforeEach, describe, it } from 'node:test';
import * as sinon from 'sinon';
import { TextEncoder } from 'util';
import {
  FinishReason,
  HarmCategory,
  HarmProbability,
} from '../../src/common/types';
import {
  embedContent,
  generateContent,
  generateContentStream,
  getGoogleAIUrl,
  listModels,
} from '../../src/googleai/client';
import {
  EmbedContentRequest,
  EmbedContentResponse,
  GenerateContentRequest,
  GenerateContentResponse,
  GenerateContentStreamResult,
  Model,
  RequestOptions,
} from '../../src/googleai/types';

describe('Google AI Client', () => {
  let fetchSpy: sinon.SinonStub;
  const apiKey = 'test-api-key';
  const defaultBaseUrl = 'https://generativelanguage.googleapis.com';
  const defaultApiVersion = 'v1beta';

  beforeEach(() => {
    fetchSpy = sinon.stub(global, 'fetch');
  });

  afterEach(() => {
    sinon.restore();
  });

  function mockFetchResponse(
    body: any,
    ok = true,
    status = 200,
    statusText = 'OK'
  ) {
    const response = new Response(JSON.stringify(body), {
      status: ok ? status : status,
      statusText: ok ? statusText : statusText,
      headers: { 'Content-Type': 'application/json' },
    });
    fetchSpy.resolves(response);
  }

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

  describe('getGoogleAIUrl', () => {
    it('should build basic URL', () => {
      const url = getGoogleAIUrl({ resourcePath: 'models' });
      assert.strictEqual(url, `${defaultBaseUrl}/${defaultApiVersion}/models`);
    });

    it('should build URL with resourceMethod', () => {
      const url = getGoogleAIUrl({
        resourcePath: 'models/gemini-2.0-pro',
        resourceMethod: 'generateContent',
      });
      assert.strictEqual(
        url,
        `${defaultBaseUrl}/${defaultApiVersion}/models/gemini-2.0-pro:generateContent`
      );
    });

    it('should build URL with queryParams', () => {
      const url = getGoogleAIUrl({
        resourcePath: 'models',
        queryParams: 'pageSize=10',
      });
      assert.strictEqual(
        url,
        `${defaultBaseUrl}/${defaultApiVersion}/models?pageSize=10`
      );
    });

    it('should add alt=sse for streamGenerateContent', () => {
      const url = getGoogleAIUrl({
        resourcePath: 'models/gemini-2.5-flash',
        resourceMethod: 'streamGenerateContent',
      });
      assert.strictEqual(
        url,
        `${defaultBaseUrl}/${defaultApiVersion}/models/gemini-2.5-flash:streamGenerateContent?alt=sse`
      );
    });

    it('should add alt=sse for streamGenerateContent with other queryParams', () => {
      const url = getGoogleAIUrl({
        resourcePath: 'models/gemini-2.5-flash',
        resourceMethod: 'streamGenerateContent',
        queryParams: 'test=123',
      });
      assert.strictEqual(
        url,
        `${defaultBaseUrl}/${defaultApiVersion}/models/gemini-2.5-flash:streamGenerateContent?test=123&alt=sse`
      );
    });

    it('should use custom apiVersion and baseUrl from RequestOptions', () => {
      const requestOptions: RequestOptions = {
        apiVersion: 'v1',
        baseUrl: 'https://custom.googleapis.com',
      };
      const url = getGoogleAIUrl({ resourcePath: 'models', requestOptions });
      assert.strictEqual(url, 'https://custom.googleapis.com/v1/models');
    });
  });

  describe('listModels', () => {
    it('should return a list of models', async () => {
      const mockModels: Model[] = [
        { name: 'models/gemini-2.0-pro' } as Model,
        { name: 'models/gemini-2.5-flash' } as Model,
      ];
      mockFetchResponse({ models: mockModels });

      const result = await listModels(apiKey);
      assert.deepStrictEqual(result, mockModels);

      const expectedUrl =
        'https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000';
      sinon.assert.calledOnceWithExactly(fetchSpy, expectedUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'x-goog-api-key': apiKey,
          'x-goog-api-client': GENKIT_CLIENT_HEADER,
        },
      });
    });

    it('should throw an error if fetch fails', async () => {
      const errorResponse = { error: { message: 'Internal Error' } };
      mockFetchResponse(errorResponse, false, 500, 'Internal Server Error');

      await assert.rejects(
        listModels(apiKey),
        /Failed to fetch from .* Error fetching from .* \[500 Internal Server Error\] Internal Error/
      );
    });

    it('should include custom headers', async () => {
      mockFetchResponse({ models: [] });
      const requestOptions: RequestOptions = {
        customHeaders: { 'X-Custom-Header': 'test' },
      };
      await listModels(apiKey, requestOptions);

      sinon.assert.calledOnce(fetchSpy);
      const headers = fetchSpy.firstCall.args[1].headers;
      assert.strictEqual(headers['X-Custom-Header'], 'test');
      assert.strictEqual(headers['x-goog-api-key'], apiKey);
    });
  });

  describe('generateContent', () => {
    const model = 'gemini-2.0-pro';
    const request: GenerateContentRequest = {
      contents: [{ role: 'user', parts: [{ text: 'hello' }] }],
    };

    it('should return GenerateContentResponse', async () => {
      const mockResponse: GenerateContentResponse = {
        candidates: [
          { index: 0, content: { role: 'model', parts: [{ text: 'world' }] } },
        ],
      };
      mockFetchResponse(mockResponse);

      const result = await generateContent(apiKey, model, request);
      assert.deepStrictEqual(result, mockResponse);

      const expectedUrl = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;
      sinon.assert.calledOnceWithExactly(fetchSpy, expectedUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-goog-api-key': apiKey,
          'x-goog-api-client': GENKIT_CLIENT_HEADER,
        },
        body: JSON.stringify(request),
      });
    });

    it('should throw on API error', async () => {
      const errorResponse = { error: { message: 'Invalid Request' } };
      mockFetchResponse(errorResponse, false, 400, 'Bad Request');

      await assert.rejects(
        generateContent(apiKey, model, request),
        /Failed to fetch from .* Error fetching from .* \[400 Bad Request\] Invalid Request/
      );
    });
  });

  describe('embedContent', () => {
    const model = 'text-embedding-005'; // Embedding model names differ
    const request: EmbedContentRequest = {
      content: { role: 'user', parts: [{ text: 'test content' }] },
    };

    it('should return EmbedContentResponse', async () => {
      const mockResponse: EmbedContentResponse = {
        embedding: { values: [0.1, 0.2, 0.3] },
      };
      mockFetchResponse(mockResponse);

      const result = await embedContent(apiKey, model, request);
      assert.deepStrictEqual(result, mockResponse);

      const expectedUrl = `https://generativelanguage.googleapis.com/v1beta/embedders/${model}:embedContent`;
      sinon.assert.calledOnceWithExactly(fetchSpy, expectedUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-goog-api-key': apiKey,
          'x-goog-api-client': GENKIT_CLIENT_HEADER,
        },
        body: JSON.stringify(request),
      });
    });
  });

  describe('generateContentStream', () => {
    const model = 'gemini-2.5-flash';
    const defaultRequest: GenerateContentRequest = {
      contents: [{ role: 'user', parts: [{ text: 'stream test' }] }],
    };

    it('should process stream and return stream and aggregated response', async () => {
      const chunks = [
        'data: {"candidates": [{"index": 0, "content": {"role": "model", "parts": [{"text": "Hello "}]}}]}\n\n',
        'data: {"candidates": [{"index": 0, "content": {"role": "model", "parts": [{"text": "World!"}]}}], "usageMetadata": {"totalTokenCount": 10}}\n\n',
      ];
      fetchSpy.resolves(createMockStream(chunks));

      const result: GenerateContentStreamResult = await generateContentStream(
        apiKey,
        model,
        defaultRequest
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
              content: { role: 'model', parts: [{ text: 'Hello ' }] },
            },
          ],
        },
        {
          candidates: [
            {
              index: 0,
              content: { role: 'model', parts: [{ text: 'World!' }] },
            },
          ],
          usageMetadata: { totalTokenCount: 10 },
        },
      ]);

      const aggregated = await result.response;
      assert.deepStrictEqual(aggregated, {
        candidates: [
          {
            index: 0,
            content: {
              role: 'model',
              parts: [{ text: 'Hello ' }, { text: 'World!' }],
            },
          },
        ],
        usageMetadata: { totalTokenCount: 10 },
        promptFeedback: undefined,
      });

      const expectedUrl = `https://generativelanguage.googleapis.com/v1beta/models/${model}:streamGenerateContent?alt=sse`;
      sinon.assert.calledOnceWithExactly(fetchSpy, expectedUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-goog-api-key': apiKey,
          'x-goog-api-client': GENKIT_CLIENT_HEADER,
        },
        body: JSON.stringify(defaultRequest),
      });
    });

    it('should aggregate parts for multiple candidates', async () => {
      const chunks = [
        'data: {"candidates": [{"index": 0, "content": {"role": "model", "parts": [{"text": "C0 A"}]}}, {"index": 1, "content": {"role": "model", "parts": [{"text": "C1 A"}]}}]}\n\n',
        'data: {"candidates": [{"index": 0, "content": {"role": "model", "parts": [{"text": " C0 B"}]}}, {"index": 1, "content": {"role": "model", "parts": [{"text": " C1 B"}]}}]}\n\n',
      ];
      fetchSpy.resolves(createMockStream(chunks));
      const result = await generateContentStream(apiKey, model, defaultRequest);
      const aggregated = await result.response;

      assert.strictEqual(aggregated.candidates?.length, 2);
      const sortedCandidates = aggregated.candidates!.sort(
        (a, b) => a.index - b.index
      );

      assert.deepStrictEqual(sortedCandidates[0], {
        index: 0,
        content: {
          role: 'model',
          parts: [{ text: 'C0 A' }, { text: ' C0 B' }],
        },
      });
      assert.deepStrictEqual(sortedCandidates[1], {
        index: 1,
        content: {
          role: 'model',
          parts: [{ text: 'C1 A' }, { text: ' C1 B' }],
        },
      });
    });

    it('should use latest metadata from chunks for each candidate', async () => {
      const chunks = [
        'data: {"candidates": [{"index": 0, "content": {"role": "model", "parts": [{"text": "A"}]}, "finishReason": "STOP"}, {"index": 1, "content": {"role": "model", "parts": [{"text": "C1 "}]}}]}\n\n',
        'data: {"candidates": [{"index": 0, "content": {"role": "model", "parts": [{"text": "B"}]}, "finishReason": "MAX_TOKENS", "safetyRatings": [{"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "probability": "LOW"}]}, {"index": 1, "content": {"role": "model", "parts": [{"text": "D1"}]}, "finishReason": "STOP" }], "usageMetadata": {"totalTokenCount": 20}}\n\n',
      ];
      fetchSpy.resolves(createMockStream(chunks));
      const result = await generateContentStream(apiKey, model, defaultRequest);
      const aggregated = await result.response;

      assert.strictEqual(aggregated.candidates?.length, 2);
      const sortedCandidates = aggregated.candidates!.sort(
        (a, b) => a.index - b.index
      );

      const cand0 = sortedCandidates[0];
      assert.strictEqual(cand0.index, 0);
      assert.strictEqual(cand0.finishReason, FinishReason.MAX_TOKENS);
      assert.deepStrictEqual(cand0.safetyRatings, [
        {
          category: HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
          probability: HarmProbability.LOW,
        },
      ]);
      assert.deepStrictEqual(cand0.content.parts, [
        { text: 'A' },
        { text: 'B' },
      ]);

      const cand1 = sortedCandidates[1];
      assert.strictEqual(cand1.index, 1);
      assert.strictEqual(cand1.finishReason, FinishReason.STOP);
      assert.strictEqual(cand1.safetyRatings, undefined);
      assert.deepStrictEqual(cand1.content.parts, [
        { text: 'C1 ' },
        { text: 'D1' },
      ]);

      assert.deepStrictEqual(aggregated.usageMetadata, { totalTokenCount: 20 });
    });

    it('should aggregate different part types', async () => {
      const chunks = [
        'data: {"candidates": [{"index": 0, "content": {"role": "model", "parts": [{"text": "Action: "}]}}]}\n\n',
        'data: {"candidates": [{"index": 0, "content": {"role": "model", "parts": [{"functionCall": {"name": "tool_call", "args": {}}}]}}]}\n\n',
      ];
      fetchSpy.resolves(createMockStream(chunks));
      const result = await generateContentStream(apiKey, model, defaultRequest);
      const aggregated = await result.response;
      const cand = aggregated.candidates![0];

      assert.deepStrictEqual(cand, {
        index: 0,
        content: {
          role: 'model',
          parts: [
            { text: 'Action: ' },
            { functionCall: { name: 'tool_call', args: {} } },
          ],
        },
      });
    });

    it('should handle stream with malformed JSON', async () => {
      const chunks = [
        'data: {"candidates": [{"index": 0, "content": {"role": "model", "parts": [{"text": "Hello "}]}}]}\n\n',
        'data: {"candi dates": []}}}}\n\n', // Malformed
      ];
      fetchSpy.resolves(createMockStream(chunks));

      const result: GenerateContentStreamResult = await generateContentStream(
        apiKey,
        model,
        defaultRequest
      );

      const streamResults: GenerateContentResponse[] = [];
      try {
        for await (const item of result.stream) {
          streamResults.push(item);
        }
        assert.fail('Stream should have thrown an error');
      } catch (e: any) {
        assert.match(e.message, /Error parsing JSON response/);
      }

      try {
        await result.response;
        assert.fail('Response promise should have thrown an error');
      } catch (e: any) {
        assert.match(e.message, /Error parsing JSON response/);
      }
    });
  });
});
