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
import { GenkitError, z } from 'genkit';
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

const mockRequest = (overrides: any = {}) => ({
  messages: [],
  tools: [],
  ...overrides, // Ensuring overrides are properly applied
});

const mockCachedContent: CachedContent = {
  model: 'gemini-1.5-pro-001',
  contents: [
    {
      role: 'user',
      parts: [{ text: 'Hello world' }],
    },
  ],
};

let mockCacheManager: {
  list: jest.Mock<
    () => Promise<{
      cachedContents: Partial<CachedContent>[];
      nextPageToken?: string;
    }>
  >;
  delete: jest.Mock<() => Promise<void>>;
};

// Test Suite for extractCacheConfig
describe('extractCacheConfig', () => {
  beforeEach(() => {
    mockCacheManager = {
      list: jest.fn() as jest.Mock<() => Promise<any>>,
      delete: jest.fn() as jest.Mock<() => Promise<void>>,
    };
  });

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

// Test Suite for validateContextCacheRequest
describe('validateContextCacheRequest', () => {
  beforeEach(() => {
    mockCacheManager = {
      list: jest.fn() as jest.Mock<() => Promise<any>>,
      delete: jest.fn() as jest.Mock<() => Promise<void>>,
    };
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

// Test Suite for generateCacheKey
describe('generateCacheKey', () => {
  beforeEach(() => {
    mockCacheManager = {
      list: jest.fn() as jest.Mock<() => Promise<any>>,
      delete: jest.fn() as jest.Mock<() => Promise<void>>,
    };
  });

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

// Test Suite for getContentForCache
describe('getContentForCache', () => {
  let mockRequest: GenerateRequest<z.ZodTypeAny>;
  let mockChatRequest: StartChatParams;

  beforeEach(() => {
    mockCacheManager = {
      list: jest.fn() as jest.Mock<() => Promise<any>>,
      delete: jest.fn() as jest.Mock<() => Promise<void>>,
    };

    mockRequest = {
      messages: [
        {
          role: 'user',
          content: [{ text: 'Hello world' }],
        },
        {
          role: 'model',
          content: [{ text: 'I am a chatbot' }],
          metadata: { cache: true },
        },
        {
          role: 'user',
          content: [{ text: 'Goodbye' }],
        },
      ],
    };
    mockChatRequest = {
      history: [
        { role: 'user', parts: [{ text: 'Hello world' }] },
        { role: 'model', parts: [{ text: 'I am a chatbot' }] },
      ],
    };
  });

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

  test('should correctly split history when endOfCachedContents is not the last message', () => {
    const { cachedContent, chatRequest } = getContentForCache(
      mockRequest,
      mockChatRequest,
      'gemini-1.5-pro-001',
      {
        endOfCachedContents: 0,
        cacheConfig: true,
      }
    );
    expect(cachedContent.contents).toHaveLength(1);
    expect(chatRequest.history).toHaveLength(1);
  });

  test('should correctly split history when endOfCachedContents is the last message', () => {
    const mockRequest: GenerateRequest<z.ZodTypeAny> = {
      messages: [
        { role: 'user', content: [{ text: 'Hello world' }] },
        { role: 'model', content: [{ text: 'I am a chatbot' }] },
        { role: 'user', content: [{ text: 'How are you?' }] },
        {
          role: 'model',
          content: [{ text: 'I am doing well, thank you!' }],
          metadata: { cache: true },
        },
        { role: 'user', content: [{ text: 'Goodbye' }] },
      ],
    };

    const mockChatRequest: StartChatParams = {
      history: [
        { role: 'user', parts: [{ text: 'Hello world' }] },
        { role: 'model', parts: [{ text: 'I am a chatbot' }] },
        { role: 'user', parts: [{ text: 'How are you?' }] },
        { role: 'model', parts: [{ text: 'I am doing well, thank you!' }] },
      ],
    };

    const cacheConfigDetails = {
      endOfCachedContents: 3,
      cacheConfig: true,
    };

    const result = getContentForCache(
      mockRequest,
      mockChatRequest,
      'gemini-1.5-pro-001',
      cacheConfigDetails
    );

    expect(result.cachedContent.contents).toHaveLength(4);
    expect(result.chatRequest.history).toHaveLength(0);

    expect(result.cachedContent.contents).toEqual([
      { role: 'user', parts: [{ text: 'Hello world' }] },
      { role: 'model', parts: [{ text: 'I am a chatbot' }] },
      { role: 'user', parts: [{ text: 'How are you?' }] },
      { role: 'model', parts: [{ text: 'I am doing well, thank you!' }] },
    ]);
  });
});

// Test Suite for lookupContextCache
describe('lookupContextCache', () => {
  beforeEach(() => {
    mockCacheManager = {
      list: jest.fn() as jest.Mock<
        () => Promise<{
          cachedContents: Partial<CachedContent>[];
          nextPageToken?: string;
        }>
      >,
      delete: jest.fn() as jest.Mock<() => Promise<void>>,
    };
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

  test('should stop after reaching the maxPages limit when cache is not found', async () => {
    mockCacheManager.list
      .mockResolvedValueOnce({
        cachedContents: [],
        nextPageToken: 'nextPage1',
      })
      .mockResolvedValueOnce({
        cachedContents: [],
        nextPageToken: 'nextPage2',
      })
      .mockResolvedValueOnce({
        cachedContents: [],
      });

    const maxPages = 2;

    const result = await lookupContextCache(
      mockCacheManager as unknown as GoogleAICacheManager,
      'cacheKey123',
      maxPages
    );

    // Expect null as no matching cache is found
    expect(result).toBeNull();

    // Ensure list was called exactly maxPages times (2 in this case)
    expect(mockCacheManager.list).toHaveBeenCalledTimes(maxPages);

    // Ensure that nextPageToken is passed correctly
    expect(mockCacheManager.list).toHaveBeenNthCalledWith(1, {
      pageSize: undefined,
      pageToken: undefined,
    });
    expect(mockCacheManager.list).toHaveBeenNthCalledWith(2, {
      pageSize: undefined,
      pageToken: 'nextPage1',
    });
  });

  test('should return cache content if found within maxPages limit', async () => {
    mockCacheManager.list
      .mockResolvedValueOnce({
        cachedContents: [],
        nextPageToken: 'nextPage1',
      })
      .mockResolvedValueOnce({
        cachedContents: [{ displayName: 'cacheKey123' }],
      });

    const maxPages = 3;

    const result = await lookupContextCache(
      mockCacheManager as unknown as GoogleAICacheManager,
      'cacheKey123',
      maxPages
    );

    // Expect the matching cache to be found and returned
    expect(result).toEqual({ displayName: 'cacheKey123' });

    // Ensure list was called only twice, as cache was found on the second page
    expect(mockCacheManager.list).toHaveBeenCalledTimes(2);
  });

  test('should stop if maxPages is exceeded, even if there are more pages', async () => {
    mockCacheManager.list
      .mockResolvedValueOnce({
        cachedContents: [],
        nextPageToken: 'nextPage1',
      })
      .mockResolvedValueOnce({
        cachedContents: [],
        nextPageToken: 'nextPage2',
      })
      .mockResolvedValueOnce({
        cachedContents: [{ displayName: 'cacheKey123' }],
      });

    const maxPages = 2;

    const result = await lookupContextCache(
      mockCacheManager as unknown as GoogleAICacheManager,
      'cacheKey123',
      maxPages
    );

    // Expect null as the maxPages limit is reached before finding the cache
    expect(result).toBeNull();

    // Ensure list was called exactly maxPages times
    expect(mockCacheManager.list).toHaveBeenCalledTimes(maxPages);
  });
});

// Test Suite for clearAllCaches
describe('clearAllCaches', () => {
  beforeEach(() => {
    mockCacheManager = {
      list: jest.fn() as jest.Mock<
        () => Promise<{
          cachedContents: Partial<CachedContent>[];
          nextPageToken?: string;
        }>
      >,
      delete: jest.fn() as jest.Mock<() => Promise<void>>,
    };
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
