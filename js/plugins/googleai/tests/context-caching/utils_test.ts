/**
 * Copyright 2024 Google LLC
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

import { CachedContent, StartChatParams } from '@google/generative-ai';
import assert from 'assert';
import crypto from 'crypto';
import { GenerateRequest, GenkitError } from 'genkit';
import { describe, it } from 'node:test';
import {
  CONTEXT_CACHE_SUPPORTED_MODELS,
  DEFAULT_TTL,
  INVALID_ARGUMENT_MESSAGES,
} from '../../src/context-caching/constants.js';
import { CacheConfigDetails } from '../../src/context-caching/types.js';
import {
  calculateTTL,
  extractCacheConfig,
  findLastIndex,
  generateCacheKey,
  getContentForCache,
  lookupContextCache,
  validateContextCacheRequest,
} from '../../src/context-caching/utils';

describe('generateCacheKey', () => {
  it('should generate a SHA-256 hash for a given request object', () => {
    const request: CachedContent = {
      contents: [
        {
          role: 'user',
          parts: [{ text: 'Hello world' }],
        },
      ],
    };
    const expectedHash = crypto
      .createHash('sha256')
      .update(JSON.stringify(request))
      .digest('hex');

    const result = generateCacheKey(request);
    assert.strictEqual(
      result,
      expectedHash,
      'Generated hash does not match expected hash'
    );
  });

  it('should handle an empty `contents` array as input', () => {
    const request: CachedContent = {
      contents: [],
    };
    const expectedHash = crypto
      .createHash('sha256')
      .update(JSON.stringify(request))
      .digest('hex');

    const result = generateCacheKey(request);
    assert.strictEqual(
      result,
      expectedHash,
      'Generated hash does not match expected hash for empty `contents` array'
    );
  });

  it('should generate different hashes for different objects', () => {
    const request1: CachedContent = {
      contents: [
        {
          role: 'user',
          parts: [{ text: 'First message' }],
        },
      ],
    };
    const request2: CachedContent = {
      contents: [
        {
          role: 'user',
          parts: [{ text: 'Second message' }],
        },
      ],
    };

    const hash1 = generateCacheKey(request1);
    const hash2 = generateCacheKey(request2);

    assert.notStrictEqual(
      hash1,
      hash2,
      'Hashes for different objects should not match'
    );
  });

  it('should be consistent for the same input', () => {
    const request: CachedContent = {
      contents: [
        {
          role: 'user',
          parts: [{ text: 'Consistent message' }],
        },
      ],
    };
    const hash1 = generateCacheKey(request);
    const hash2 = generateCacheKey(request);
    assert.strictEqual(hash1, hash2, 'Hashes for the same object should match');
  });

  it('should handle nested parts correctly', () => {
    const request: CachedContent = {
      contents: [
        {
          role: 'user',
          parts: [
            { text: 'Outer part', inlineData: undefined },
            {
              text: 'Nested part',
              functionCall: undefined,
            },
          ],
        },
      ],
    };
    const expectedHash = crypto
      .createHash('sha256')
      .update(JSON.stringify(request))
      .digest('hex');

    const result = generateCacheKey(request);
    assert.strictEqual(
      result,
      expectedHash,
      'Generated hash does not match expected hash for nested parts'
    );
  });

  it('should include optional properties if provided', () => {
    const request: CachedContent = {
      contents: [
        {
          role: 'assistant',
          parts: [{ text: 'Hello from the assistant' }],
        },
      ],
      model: 'gpt-4',
      displayName: 'test-cache',
    };
    const expectedHash = crypto
      .createHash('sha256')
      .update(JSON.stringify(request))
      .digest('hex');

    const result = generateCacheKey(request);
    assert.strictEqual(
      result,
      expectedHash,
      'Generated hash does not match expected hash with optional properties'
    );
  });
  it('should handle malformed input gracefully', () => {
    const request: any = {}; // Malformed input
    const result = generateCacheKey(request);
    assert.ok(result, 'Should return a valid hash even for malformed input');
  });
});

describe('getContentForCache', () => {
  it('should correctly retrieve cached content and updated chat request', () => {
    const request: GenerateRequest<any> = {
      messages: [
        { role: 'system', content: [{ text: 'System message' }] },
        { role: 'user', content: [{ text: 'Hello!' }] },
        { role: 'model', content: [{ text: 'Response' }] }, // Added an assistant response
      ],
    };
    const chatRequest: StartChatParams = {
      history: [
        { role: 'system', parts: [{ text: 'System message' }] },
        { role: 'user', parts: [{ text: 'User message' }] },
      ],
    };
    const modelVersion = 'gpt-4';
    const cacheConfigDetails: CacheConfigDetails = {
      endOfCachedContents: 0,
      cacheConfig: { ttlSeconds: 300 },
    };

    const result = getContentForCache(
      request,
      chatRequest,
      modelVersion,
      cacheConfigDetails
    );

    assert.deepStrictEqual(result.cachedContent, {
      model: modelVersion,
      contents: [{ role: 'system', parts: [{ text: 'System message' }] }],
    });
    assert.deepStrictEqual(result.chatRequest.history, [
      { role: 'user', parts: [{ text: 'User message' }] },
    ]);
    assert.deepStrictEqual(result.cacheConfig, { ttlSeconds: 300 });
  });

  it('should work correctly with no cacheConfigDetails', () => {
    const request: GenerateRequest<any> = {
      messages: [
        { role: 'system', content: [{ text: 'System message' }] },
        { role: 'user', content: [{ text: 'Hello!' }] },
      ],
    };
    const chatRequest: StartChatParams = {
      history: [{ role: 'system', parts: [{ text: 'System message' }] }],
    };
    const modelVersion = 'gpt-4';
    const cacheConfigDetails: CacheConfigDetails = {
      endOfCachedContents: 0,
      cacheConfig: true,
    };

    const result = getContentForCache(
      request,
      chatRequest,
      modelVersion,
      cacheConfigDetails
    );

    assert.deepStrictEqual(result.cachedContent, {
      model: modelVersion,
      contents: [{ role: 'system', parts: [{ text: 'System message' }] }],
    });
    assert.deepStrictEqual(result.chatRequest.history, []);
    assert.strictEqual(result.cacheConfig, true);
  });

  it('should throw an error if modelVersion is missing', () => {
    const request: GenerateRequest<any> = {
      messages: [{ role: 'user', content: [{ text: 'Hello!' }] }],
    };
    const chatRequest: StartChatParams = {
      history: [{ role: 'user', parts: [{ text: 'Hello!' }] }],
    };
    const cacheConfigDetails: CacheConfigDetails = {
      endOfCachedContents: 0,
      cacheConfig: true,
    };

    assert.throws(
      () => {
        getContentForCache(request, chatRequest, '', cacheConfigDetails);
      },
      (error: any) =>
        error instanceof Error &&
        error.message === 'No model version provided for context caching',
      'Expected an error about missing model version'
    );
  });

  it('should throw an error if endOfCachedContents exceeds history length', () => {
    const request: GenerateRequest<any> = {
      messages: [{ role: 'user', content: [{ text: 'Hello!' }] }],
    };
    const chatRequest: StartChatParams = {
      history: [{ role: 'user', parts: [{ text: 'Hello!' }] }],
    };
    const modelVersion = 'gpt-4';
    const cacheConfigDetails: CacheConfigDetails = {
      endOfCachedContents: 5, // Exceeds history length
      cacheConfig: true,
    };

    assert.throws(
      () => {
        getContentForCache(
          request,
          chatRequest,
          modelVersion,
          cacheConfigDetails
        );
      },
      (error: any) =>
        error instanceof Error &&
        error.message ===
          'INTERNAL: Genkit request history and Gemini chat request history length do not match',
      'Expected error for out-of-bounds endOfCachedContents'
    );
  });
});

describe('findLastIndex', () => {
  it('should return the index of the last element that satisfies the callback', () => {
    const array = [1, 2, 3, 4, 5, 6];
    const result = findLastIndex(array, (element) => element % 2 === 0);
    assert.strictEqual(result, 5, 'Last even number is at index 5');
  });

  it('should return -1 if no elements satisfy the callback', () => {
    const array = [1, 3, 5, 7];
    const result = findLastIndex(array, (element) => element % 2 === 0);
    assert.strictEqual(result, -1, 'No even numbers, so result is -1');
  });

  it('should handle an empty array and return -1', () => {
    const array: number[] = [];
    const result = findLastIndex(array, () => true);
    assert.strictEqual(result, -1, 'Empty array should return -1');
  });

  it('should return the index of the last element matching a complex condition', () => {
    const array = [
      { id: 1, value: 10 },
      { id: 2, value: 15 },
      { id: 3, value: 10 },
      { id: 4, value: 20 },
    ];
    const result = findLastIndex(array, (element) => element.value === 10);
    assert.strictEqual(result, 2, 'Last object with value 10 is at index 2');
  });

  it('should return the index of the last element when multiple match', () => {
    const array = [1, 2, 3, 4, 5, 6];
    const result = findLastIndex(array, (element) => element > 2);
    assert.strictEqual(result, 5, 'Last element greater than 2 is at index 5');
  });

  it('should pass the correct arguments to the callback', () => {
    const array = [1, 2, 3];
    const indices: number[] = [];
    const result = findLastIndex(array, (element, index) => {
      indices.push(index); // Collect indices in reverse order
      return false; // Ensure all elements are checked
    });
    assert.deepStrictEqual(
      indices,
      [2, 1, 0],
      'Callback should check indices in reverse order'
    );
    assert.strictEqual(result, -1, 'No matching element, result should be -1');
  });

  it('should handle an array with one element', () => {
    const array = [42];
    const result = findLastIndex(array, (element) => element === 42);
    assert.strictEqual(
      result,
      0,
      'Single matching element should return index 0'
    );
  });

  it('should handle an array with all elements matching the condition', () => {
    const array = [5, 5, 5, 5];
    const result = findLastIndex(array, (element) => element === 5);
    assert.strictEqual(
      result,
      3,
      'Last element matching condition is at index 3'
    );
  });
});

describe('lookupContextCache', () => {
  it('should return the cached content if found on the first page', async () => {
    const mockCacheManager = {
      list: async ({
        pageSize,
        pageToken,
      }: {
        pageSize: number;
        pageToken?: string;
      }) => ({
        cachedContents: [
          { displayName: 'key1', data: 'value1' },
          { displayName: 'key2', data: 'value2' },
        ],
        nextPageToken: undefined,
      }),
    };

    const result = await lookupContextCache(mockCacheManager as any, 'key1');
    assert.deepStrictEqual(result, { displayName: 'key1', data: 'value1' });
  });

  it('should return the cached content if found on subsequent pages', async () => {
    const mockCacheManager = {
      list: async ({
        pageSize,
        pageToken,
      }: {
        pageSize: number;
        pageToken?: string;
      }) => {
        if (!pageToken) {
          return {
            cachedContents: [{ displayName: 'key1', data: 'value1' }],
            nextPageToken: 'page2',
          };
        }
        if (pageToken === 'page2') {
          return {
            cachedContents: [{ displayName: 'key2', data: 'value2' }],
            nextPageToken: undefined,
          };
        }
        return { cachedContents: [], nextPageToken: undefined };
      },
    };

    const result = await lookupContextCache(mockCacheManager as any, 'key2');
    assert.deepStrictEqual(result, { displayName: 'key2', data: 'value2' });
  });

  it('should return null if the cached content is not found', async () => {
    const mockCacheManager = {
      list: async ({
        pageSize,
        pageToken,
      }: {
        pageSize: number;
        pageToken?: string;
      }) => ({
        cachedContents: [
          { displayName: 'key1', data: 'value1' },
          { displayName: 'key3', data: 'value3' },
        ],
        nextPageToken: undefined,
      }),
    };

    const result = await lookupContextCache(
      mockCacheManager as any,
      'nonexistent-key'
    );
    assert.strictEqual(result, null);
  });

  it('should respect the maxPages limit and return null if not found', async () => {
    const mockCacheManager = {
      list: async ({
        pageSize,
        pageToken,
      }: {
        pageSize: number;
        pageToken?: string;
      }) => ({
        cachedContents: [{ displayName: `key${pageToken}` }],
        nextPageToken:
          pageToken === 'page99'
            ? undefined
            : `page${parseInt(pageToken || '1') + 1}`,
      }),
    };

    const result = await lookupContextCache(
      mockCacheManager as any,
      'key100',
      50
    ); // Limit to 50 pages
    assert.strictEqual(result, null);
  });

  it('should handle an empty response gracefully', async () => {
    const mockCacheManager = {
      list: async ({
        pageSize,
        pageToken,
      }: {
        pageSize: number;
        pageToken?: string;
      }) => ({
        cachedContents: [],
        nextPageToken: undefined,
      }),
    };

    const result = await lookupContextCache(mockCacheManager as any, 'key1');
    assert.strictEqual(result, null);
  });

  it('should stop searching if no nextPageToken is provided', async () => {
    const mockCacheManager = {
      list: async ({
        pageSize,
        pageToken,
      }: {
        pageSize: number;
        pageToken?: string;
      }) => ({
        cachedContents: [{ displayName: 'key1', data: 'value1' }],
        nextPageToken: undefined,
      }),
    };

    const result = await lookupContextCache(mockCacheManager as any, 'key2');
    assert.strictEqual(result, null);
  });

  it('should throw a GenkitError with the correct status and message on a network error', async () => {
    const mockCacheManager = {
      list: async () => {
        throw new Error('Network Error');
      },
    };

    try {
      await lookupContextCache(mockCacheManager as any, 'key1');
      assert.fail('Expected lookupContextCache to throw a GenkitError');
    } catch (error) {
      assert.ok(
        error instanceof GenkitError,
        'Error should be an instance of GenkitError'
      );
      assert.strictEqual(
        error.status,
        'INTERNAL',
        'Error status should be "INTERNAL"'
      );
      assert.strictEqual(
        error.message,
        'INTERNAL: Error looking up context cache: Network Error',
        'Error message should contain the network error details'
      );
    }
  });

  it('should throw a GenkitError with "Unknown Network Error" if error message is missing', async () => {
    const mockCacheManager = {
      list: async () => {
        throw {}; // Simulate an unknown error object
      },
    };

    try {
      await lookupContextCache(mockCacheManager as any, 'key1');
      assert.fail('Expected lookupContextCache to throw a GenkitError');
    } catch (error) {
      assert.ok(
        error instanceof GenkitError,
        'Error should be an instance of GenkitError'
      );
      assert.strictEqual(
        error.status,
        'INTERNAL',
        'Error status should be "INTERNAL"'
      );
      assert.strictEqual(
        error.message,
        'INTERNAL: Error looking up context cache: Unknown Network Error',
        'Error message should indicate an unknown network error'
      );
    }
  });
});

describe('validateContextCacheRequest', () => {
  it('should throw an error for empty modelVersion', () => {
    const request: GenerateRequest<any> = {
      messages: [],
      config: {},
    };
    assert.throws(
      () => validateContextCacheRequest(request, ''),
      (error: any) =>
        error instanceof GenkitError &&
        error.status === 'INVALID_ARGUMENT' &&
        error.message ===
          'INVALID_ARGUMENT: ' + INVALID_ARGUMENT_MESSAGES.modelVersion
    );
  });

  it('should return true for valid model and request', () => {
    const request: GenerateRequest<any> = {
      messages: [],
      config: {},
    };
    const modelVersion = 'supported-model';
    CONTEXT_CACHE_SUPPORTED_MODELS.push(modelVersion);

    const result = validateContextCacheRequest(request, modelVersion);
    assert.strictEqual(result, true);
  });

  it('should throw an error for unsupported model version', () => {
    const request: GenerateRequest<any> = {
      messages: [],
      config: {},
    };

    const unsupportedModelVersion = 'unsupported-model';

    // Reset and populate the supported models list
    CONTEXT_CACHE_SUPPORTED_MODELS.length = 0;
    CONTEXT_CACHE_SUPPORTED_MODELS.push(
      'gemini-1.5-flash-001',
      'gemini-1.5-pro-001'
    );

    assert.throws(
      () => validateContextCacheRequest(request, unsupportedModelVersion),
      (error: any) => {
        if (!(error instanceof GenkitError)) {
          console.error('Error is not an instance of GenkitError:', error);
          return false;
        }

        // Updated expected message with "INVALID_ARGUMENT:" prefix
        const expectedMessage =
          'INVALID_ARGUMENT: Model version is required for context caching, supported only in gemini-1.5-flash-001,gemini-1.5-pro-001 models.';
        return (
          error.status === 'INVALID_ARGUMENT' &&
          error.message === expectedMessage
        );
      },
      'Expected GenkitError with INVALID_ARGUMENT status and correct message'
    );
  });

  it('should throw an error if tools are present in the request', () => {
    const request: GenerateRequest<any> = {
      messages: [],
      tools: [{ name: 'test-tool', description: 'Test tool' }],
    };
    const modelVersion = 'supported-model';
    CONTEXT_CACHE_SUPPORTED_MODELS.push(modelVersion);

    assert.throws(
      () => validateContextCacheRequest(request, modelVersion),
      (error: any) => {
        if (!(error instanceof GenkitError)) {
          console.error('Error is not an instance of GenkitError:', error);
          return false;
        }

        // Add "INVALID_ARGUMENT:" prefix to the expected message
        const expectedMessage =
          'INVALID_ARGUMENT: Context caching cannot be used simultaneously with tools.';
        return (
          error.status === 'INVALID_ARGUMENT' &&
          error.message === expectedMessage
        );
      },
      'Expected GenkitError with INVALID_ARGUMENT status and correct message'
    );
  });

  it('should throw an error if code execution is enabled in the request', () => {
    const request: GenerateRequest<any> = {
      messages: [],
      config: { codeExecution: true },
    };
    const modelVersion = 'supported-model';
    CONTEXT_CACHE_SUPPORTED_MODELS.push(modelVersion);

    assert.throws(
      () => validateContextCacheRequest(request, modelVersion),
      (error: any) => {
        if (!(error instanceof GenkitError)) {
          console.error('Error is not an instance of GenkitError:', error);
          return false;
        }

        // Add "INVALID_ARGUMENT:" prefix to the expected message
        const expectedMessage =
          'INVALID_ARGUMENT: Context caching cannot be used simultaneously with code execution.';
        return (
          error.status === 'INVALID_ARGUMENT' &&
          error.message === expectedMessage
        );
      },
      'Expected GenkitError with INVALID_ARGUMENT status and correct message'
    );
  });
});

describe('extractCacheConfig', () => {
  it('should return null if no metadata.cache is present', () => {
    const request: GenerateRequest<any> = {
      messages: [{ metadata: {}, role: 'user', content: [{ text: 'Hello!' }] }],
    };
    const result = extractCacheConfig(request);
    assert.strictEqual(result, null);
  });

  it('should correctly extract cache config when metadata.cache is present', () => {
    const request: GenerateRequest<any> = {
      messages: [
        {
          metadata: { cache: { ttlSeconds: 300 } },
          role: 'user',
          content: [{ text: 'Hello!' }],
        },
        { metadata: {}, role: 'model', content: [{ text: 'Response' }] },
      ],
    };
    const result = extractCacheConfig(request);
    assert.deepStrictEqual(result, {
      endOfCachedContents: 0,
      cacheConfig: { ttlSeconds: 300 },
    });
  });

  it('should handle invalid metadata.cache structures gracefully', () => {
    const request: GenerateRequest<any> = {
      messages: [
        {
          metadata: { cache: 'invalid' },
          role: 'user',
          content: [{ text: 'Hello!' }],
        },
      ],
    };
    assert.throws(() => extractCacheConfig(request));
  });
});

describe('calculateTTL', () => {
  it('should return the default TTL when cacheConfig is true', () => {
    const cacheConfigDetails: CacheConfigDetails = {
      cacheConfig: true,
      endOfCachedContents: 0,
    };
    const result = calculateTTL(cacheConfigDetails);
    assert.strictEqual(result, DEFAULT_TTL);
  });

  it('should return 0 when cacheConfig is false', () => {
    const cacheConfigDetails: CacheConfigDetails = {
      cacheConfig: false,
      endOfCachedContents: 0,
    };
    const result = calculateTTL(cacheConfigDetails);
    assert.strictEqual(result, 0);
  });

  it('should return the specified ttlSeconds value when present', () => {
    const cacheConfigDetails: CacheConfigDetails = {
      cacheConfig: { ttlSeconds: 500 },
      endOfCachedContents: 0,
    };
    const result = calculateTTL(cacheConfigDetails);
    assert.strictEqual(result, 500);
  });

  it('should return the default TTL when ttlSeconds is missing', () => {
    const cacheConfigDetails: CacheConfigDetails = {
      cacheConfig: {},
      endOfCachedContents: 0,
    };
    const result = calculateTTL(cacheConfigDetails);
    assert.strictEqual(result, DEFAULT_TTL);
  });
});
