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
import { GoogleAICacheManager } from '@google/generative-ai/server';
import { beforeEach, describe, expect, jest, test } from '@jest/globals';
import crypto from 'crypto';
import { GenkitError, ModelReference, z } from 'genkit';
import { logger } from 'genkit/logging';
import { GenerateRequest } from 'genkit/model';
import {
  clearAllCaches,
  extractCacheConfig,
  generateCacheKey,
  getContentForCache,
  lookupContextCache,
  validateContextCacheRequest,
} from '../../src/context-caching/helpers';

// Mocks for logger
jest.mock('genkit/logging', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
  },
}));

// Mock dependencies
const mockCacheManager = {
  list: jest.fn() as jest.Mock<() => Promise<any>>,
  delete: jest.fn() as jest.Mock<() => Promise<void>>,
};

const mockRequest = (overrides: any = {}) => ({
  messages: [],
  tools: [],
  ...overrides, // Ensuring overrides are properly applied
});

const mockModel = (overrides: any = {}) =>
  ({
    info: {
      supports: {
        contextCache: true,
      },
      ...overrides.info,
    },
  }) as ModelReference<z.ZodTypeAny>;

const mockCachedContent: CachedContent = {
  model: 'gemini-1.5-pro-001',
  contents: [
    {
      role: 'user',
      parts: [{ text: 'Hello world' }],
    },
  ],
};

describe('extractCacheConfig', () => {
  test('should return null if no cache metadata is present', () => {
    const request = mockRequest({
      messages: [
        { role: 'user', content: [{ text: 'Hello' }] },
        { role: 'model', content: [{ text: 'How can I help?' }] },
      ],
    });

    const result = extractCacheConfig(request);
    expect(result).toBeNull();
  });

  test('should return cache config with TTL and correct endOfCachedContents', () => {
    const request = mockRequest({
      messages: [
        { role: 'user', content: [{ text: 'Hello' }] },
        {
          role: 'model',
          content: [{ text: 'How can I help?' }],
          metadata: { cache: { ttlSeconds: 3600 } },
        },
      ],
    });

    const result = extractCacheConfig(request);
    expect(result).toEqual({
      cacheConfig: { ttlSeconds: 3600 },
      endOfCachedContents: 1,
    });
  });

  test('should return cache config without TTL and correct endOfCachedContents', () => {
    const request = mockRequest({
      messages: [
        { role: 'user', content: [{ text: 'Hello' }] },
        {
          role: 'model',
          content: [{ text: 'How can I help?' }],
          metadata: { cache: true },
        },
      ],
    });

    const result = extractCacheConfig(request);
    expect(result).toEqual({
      cacheConfig: true,
      endOfCachedContents: 1,
    });
  });

  test('should handle cache config at the first message', () => {
    const request = mockRequest({
      messages: [
        {
          role: 'model',
          content: [{ text: 'Cached response' }],
          metadata: { cache: { ttlSeconds: 7200 } },
        },
        { role: 'user', content: [{ text: 'What is your name?' }] },
      ],
    });

    const result = extractCacheConfig(request);
    expect(result).toEqual({
      cacheConfig: { ttlSeconds: 7200 },
      endOfCachedContents: 0,
    });
  });

  test('should handle cache config at the last message', () => {
    const request = mockRequest({
      messages: [
        { role: 'user', content: [{ text: 'Who are you?' }] },
        {
          role: 'model',
          content: [{ text: 'I am an AI' }],
          metadata: { cache: true },
        },
      ],
    });

    const result = extractCacheConfig(request);
    expect(result).toEqual({
      cacheConfig: true,
      endOfCachedContents: 1,
    });
  });

  test('should return null when metadata exists but no cache field', () => {
    const request = mockRequest({
      messages: [
        {
          role: 'model',
          content: [{ text: 'Response' }],
          metadata: { otherField: 'otherValue' },
        },
        { role: 'user', content: [{ text: 'What is your purpose?' }] },
      ],
    });

    const result = extractCacheConfig(request);
    expect(result).toBeNull();
  });

  test('should correctly parse cacheConfig with ttlSeconds and additional properties', () => {
    const request = mockRequest({
      messages: [
        { role: 'user', content: [{ text: 'Hello' }] },
        {
          role: 'model',
          content: [{ text: 'Response' }],
          metadata: {
            cache: { ttlSeconds: 3600, otherProperty: 'extraValue' },
          },
        },
      ],
    });

    const result = extractCacheConfig(request);
    expect(result).toEqual({
      cacheConfig: { ttlSeconds: 3600, otherProperty: 'extraValue' },
      endOfCachedContents: 1,
    });
  });

  test('should correctly parse cacheConfig as boolean', () => {
    const request = mockRequest({
      messages: [
        { role: 'user', content: [{ text: 'Hello' }] },
        {
          role: 'model',
          content: [{ text: 'Response' }],
          metadata: { cache: true },
        },
      ],
    });

    const result = extractCacheConfig(request);
    expect(result).toEqual({
      cacheConfig: true,
      endOfCachedContents: 1,
    });
  });
});

describe('validateContextCacheRequest', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('should throw error if model version is not provided', () => {
    const request = mockRequest();

    expect(() => {
      validateContextCacheRequest(request, '');
    }).toThrowError(
      new GenkitError({
        status: 'INVALID_ARGUMENT',
        message:
          'Model version is required for context caching, which is only supported in gemini-1.5-flash-001,gemini-1.5-pro-001 models.',
      })
    );
    expect(logger.error).not.toHaveBeenCalled();
  });

  test('should throw error if conflicting features (tools) are present', () => {
    const request = mockRequest({ tools: ['someTool'] });

    expect(() => {
      validateContextCacheRequest(request, 'gemini-1.5-pro-001');
    }).toThrowError(
      new GenkitError({
        status: 'INVALID_ARGUMENT',
        message: 'Context caching cannot be used simultaneously with tools.',
      })
    );
  });

  test('should throw error if conflicting features (codeExecution) are present', () => {
    const request = mockRequest({ config: { codeExecution: true } });

    expect(() => {
      validateContextCacheRequest(request, 'gemini-1.5-pro-001');
    }).toThrowError(
      new GenkitError({
        status: 'INVALID_ARGUMENT',
        message:
          'Context caching cannot be used simultaneously with code execution.',
      })
    );
  });

  test('should return true when context caching is valid', () => {
    const request = mockRequest();

    const result = validateContextCacheRequest(request, 'gemini-1.5-pro-001');
    expect(result).toBe(true);
  });
});

describe('generateCacheKey', () => {
  test('should generate a valid SHA-256 hash for a valid request', () => {
    const result = generateCacheKey(mockCachedContent);
    const expectedHash = crypto
      .createHash('sha256')
      .update(JSON.stringify(mockCachedContent))
      .digest('hex');

    expect(result).toBe(expectedHash);
  });

  test('should handle empty request and generate a hash', () => {
    const emptyRequest: CachedContent = {
      model: '',
      contents: [],
    };
    const result = generateCacheKey(emptyRequest);
    const expectedHash = crypto
      .createHash('sha256')
      .update(JSON.stringify(emptyRequest))
      .digest('hex');

    expect(result).toBe(expectedHash);
  });

  test('should handle deeply nested content', () => {
    const nestedRequest: CachedContent = {
      model: 'gemini-1.5-pro-001',
      contents: [
        {
          role: 'user',
          parts: [{ text: 'Hello world' }, { text: 'How are you?' }],
        },
        {
          role: 'system',
          parts: [{ text: 'I am a chatbot' }],
        },
      ],
    };

    const result = generateCacheKey(nestedRequest);
    const expectedHash = crypto
      .createHash('sha256')
      .update(JSON.stringify(nestedRequest))
      .digest('hex');

    expect(result).toBe(expectedHash);
  });

  test('should produce consistent hashes for the same input', () => {
    const firstHash = generateCacheKey(mockCachedContent);
    const secondHash = generateCacheKey(mockCachedContent);

    expect(firstHash).toBe(secondHash);
  });
});

describe('getContentForCache', () => {
  const mockRequest: GenerateRequest<z.ZodTypeAny> = {
    messages: [
      {
        role: 'user',
        content: [{ text: 'Hello world' }],
      },
      {
        role: 'model',
        content: [{ text: 'I am a chatbot' }],
        // @ts-ignore
        contextCache: true,
      },
      {
        role: 'user',
        content: [{ text: 'Goodbye' }],
      },
    ],
  };

  const mockChatRequest: StartChatParams = {
    history: [
      { role: 'user', parts: [{ text: 'Hello world' }] },
      { role: 'model', parts: [{ text: 'I am a chatbot' }] },
    ],
  };

  test('should throw error if no history is provided', () => {
    expect(() => {
      getContentForCache(mockRequest, { history: [] }, 'gemini-1.5-pro-001', {
        endOfCachedContents: 1,
        cacheConfig: true,
      });
    }).toThrowError('No history provided for context caching');
  });

  test('should throw error if request.messages and chatRequest.history lengths do not match', () => {
    const mismatchedChatRequest: StartChatParams = {
      history: [{ role: 'user', parts: [{ text: 'Hello world' }] }],
    };
    expect(() => {
      getContentForCache(
        mockRequest,
        mismatchedChatRequest,
        'gemini-1.5-pro-001',
        {
          endOfCachedContents: 1,
          cacheConfig: true,
        }
      );
    }).toThrowError(
      new GenkitError({
        status: 'INTERNAL',
        message:
          'Genkit request history and Gemini chat request history length do not match',
      })
    );
  });

  test('should set newHistory to an empty array when endOfCachedContents is the last message', () => {
    const mockRequest: GenerateRequest<z.ZodTypeAny> = {
      messages: [
        {
          role: 'user',
          content: [{ text: 'Hello world' }],
        },
        {
          role: 'model',
          content: [{ text: 'I am a chatbot' }],
          // @ts-ignore
          cache: true,
        },
        {
          role: 'user',
          content: [{ text: 'Goodbye' }],
        },
      ],
    };

    const mockChatRequest: StartChatParams = {
      history: [
        { role: 'user', parts: [{ text: 'Hello world' }] },
        { role: 'model', parts: [{ text: 'I am a chatbot' }] },
      ],
    };

    const { chatRequest } = getContentForCache(
      mockRequest,
      mockChatRequest,
      'gemini-1.5-pro-001',
      {
        endOfCachedContents: 1,
        cacheConfig: true,
      }
    );

    expect(chatRequest.history).toEqual([]);
  });

  test('should split history into cached content and new history', () => {
    const { cachedContent, chatRequest } = getContentForCache(
      mockRequest,
      mockChatRequest,
      'gemini-1.5-pro-001',
      {
        endOfCachedContents: 1,
        cacheConfig: true,
      }
    );
    expect(cachedContent.contents).toHaveLength(2);
    expect(chatRequest.history).toHaveLength(0);
  });
});

describe('lookupContextCache', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('should return the correct cache when found', async () => {
    mockCacheManager.list.mockResolvedValueOnce({
      cachedContents: [{ displayName: 'cacheKey123' }],
    });

    const result = await lookupContextCache(
      mockCacheManager as unknown as GoogleAICacheManager,
      'cacheKey123',
      1
    );

    expect(result).toEqual({ displayName: 'cacheKey123' });
    expect(mockCacheManager.list).toHaveBeenCalled();
  });

  test('should return null if the cache is not found after checking all pages', async () => {
    mockCacheManager.list.mockResolvedValueOnce({
      cachedContents: [],
      nextPageToken: 'nextPage1',
    });

    mockCacheManager.list.mockResolvedValueOnce({
      cachedContents: [],
    });

    const result = await lookupContextCache(
      mockCacheManager as unknown as GoogleAICacheManager,
      'cacheKey123',
      2
    );
    expect(result).toBeNull();
  });

  test('should handle paginated cache listings', async () => {
    mockCacheManager.list
      .mockResolvedValueOnce({
        cachedContents: [],
        nextPageToken: 'nextPage1',
      })
      .mockResolvedValueOnce({
        cachedContents: [{ displayName: 'cacheKey123' }],
      });

    const result = await lookupContextCache(
      mockCacheManager as unknown as GoogleAICacheManager,
      'cacheKey123',
      2
    );

    expect(result).toEqual({ displayName: 'cacheKey123' });
    expect(mockCacheManager.list).toHaveBeenCalledTimes(2);
  });
});

describe('clearAllCaches', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('should clear all caches across multiple pages', async () => {
    mockCacheManager.list
      .mockResolvedValueOnce({
        cachedContents: [{ name: 'cache1' }, { name: 'cache2' }],
        nextPageToken: 'page2',
      })
      .mockResolvedValueOnce({
        cachedContents: [{ name: 'cache3' }],
      });

    await clearAllCaches(mockCacheManager as unknown as GoogleAICacheManager);

    expect(mockCacheManager.delete).toHaveBeenCalledTimes(3); // 3 caches deleted
    expect(logger.info).toHaveBeenCalledWith('Deleted 2 caches on page 1');
    expect(logger.info).toHaveBeenCalledWith('Deleted 1 caches on page 2');
  });

  test('should handle empty pages gracefully', async () => {
    mockCacheManager.list.mockResolvedValueOnce({
      cachedContents: [],
    });

    await clearAllCaches(mockCacheManager as unknown as GoogleAICacheManager);

    expect(mockCacheManager.delete).not.toHaveBeenCalled();
    expect(logger.info).toHaveBeenCalledWith('Deleted 0 caches on page 1');
  });

  test('should log the total number of caches deleted', async () => {
    mockCacheManager.list.mockResolvedValueOnce({
      cachedContents: [{ name: 'cache1' }],
    });

    await clearAllCaches(mockCacheManager as unknown as GoogleAICacheManager);

    expect(logger.info).toHaveBeenCalledWith('Total caches deleted: 1');
  });

  test('should log an error and rethrow when an error occurs during cache clearing', async () => {
    const mockError = new Error('Cache deletion error');
    mockCacheManager.list.mockResolvedValueOnce({
      cachedContents: [{ name: 'cache1' }],
    });
    mockCacheManager.delete.mockRejectedValueOnce(mockError);

    await expect(
      clearAllCaches(mockCacheManager as unknown as GoogleAICacheManager)
    ).rejects.toThrow(
      new GenkitError({
        status: 'INTERNAL',
        message: `Error clearing caches on page 1: ${mockError}`,
      })
    );
  });
});
