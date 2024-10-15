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

import { beforeEach, describe, expect, jest, test } from '@jest/globals';
import { GenkitError, ModelReference, z } from 'genkit';
import { logger } from 'genkit/logging';
import { validateContextCacheRequest } from '../../src/context-caching/helpers';

// Mocks for logger (if you want to test logs)
jest.mock('genkit/logging', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn(),
  },
}));

const mockRequest = (overrides: any = {}) => ({
  config: {
    contextCache: true,
    ...overrides.config,
  },
  tools: overrides.tools || [],
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

describe('validateContextCacheRequest', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('should return false when context caching is not requested', () => {
    const request = mockRequest({ config: { contextCache: false } });
    const model = mockModel();

    const result = validateContextCacheRequest(
      request,
      model,
      'gemini-1.5-pro-001'
    );
    expect(result).toBe(false);
    expect(logger.debug).toHaveBeenCalledWith(
      'Context caching is not requested'
    );
  });

  test('should throw error if model version is not provided', () => {
    const request = mockRequest();
    const model = mockModel();

    expect(() => {
      validateContextCacheRequest(request, model, '');
    }).toThrowError(
      new GenkitError({
        status: 'INVALID_ARGUMENT',
        message:
          'Model version is required for context caching, only on 001 models',
      })
    );
    expect(logger.error).not.toHaveBeenCalled();
  });

  test('should throw error if model version is unsupported', () => {
    const request = mockRequest();
    const model = mockModel();

    expect(() => {
      validateContextCacheRequest(request, model, 'unsupported-version');
    }).toThrowError(
      new GenkitError({
        status: 'INVALID_ARGUMENT',
        message:
          'Model version is required for context caching, only on 001 models',
      })
    );
  });

  test('should return false if model does not support context caching', () => {
    const request = mockRequest();
    const model = mockModel({ info: { supports: { contextCache: false } } });

    const result = validateContextCacheRequest(
      request,
      model,
      'gemini-1.5-pro-001'
    );
    expect(result).toBe(false);
  });

  test('should throw error if conflicting features (systemInstruction) are present', () => {
    const request = mockRequest({ config: { systemInstruction: true } });
    const model = mockModel();

    expect(() => {
      validateContextCacheRequest(request, model, 'gemini-1.5-pro-001');
    }).toThrowError(
      new GenkitError({
        status: 'INVALID_ARGUMENT',
        message: 'Context caching cannot be used with system instructions',
      })
    );
  });

  test('should throw error if conflicting features (tools) are present', () => {
    const request = mockRequest({ tools: ['someTool'] });
    const model = mockModel();

    expect(() => {
      validateContextCacheRequest(request, model, 'gemini-1.5-pro-001');
    }).toThrowError(
      new GenkitError({
        status: 'INVALID_ARGUMENT',
        message: 'Context caching cannot be used with tools',
      })
    );
  });

  test('should throw error if conflicting features (codeExecution) are present', () => {
    const request = mockRequest({ config: { codeExecution: true } });
    const model = mockModel();

    expect(() => {
      validateContextCacheRequest(request, model, 'gemini-1.5-pro-001');
    }).toThrowError(
      new GenkitError({
        status: 'INVALID_ARGUMENT',
        message: 'Context caching cannot be used with code execution',
      })
    );
  });

  test('should return true when context caching is valid', () => {
    const request = mockRequest();
    const model = mockModel();

    const result = validateContextCacheRequest(
      request,
      model,
      'gemini-1.5-pro-001'
    );
    expect(result).toBe(true);
    expect(logger.debug).toHaveBeenCalledWith(
      'Context caching is valid for this request'
    );
  });
});

import { CachedContent } from '@google/generative-ai';
import crypto from 'crypto';
import { generateCacheKey } from '../../src/context-caching/helpers';

// Mock data
const mockCachedContent: CachedContent = {
  model: 'gemini-1.5-pro-001',
  contents: [
    {
      role: 'user',
      parts: [{ text: 'Hello world' }],
    },
  ],
};

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

import { StartChatParams } from '@google/generative-ai';
import { GoogleAICacheManager } from '@google/generative-ai/server';
import { GenerateRequest } from 'genkit/model';
import {
  clearAllCaches,
  getContentForCache,
  lookupContextCache,
} from '../../src/context-caching/helpers';

// Mock logger
jest.mock('genkit/logging', () => ({
  logger: {
    debug: jest.fn(),
    info: jest.fn(),
    error: jest.fn(),
  },
}));

// Mock dependencies
const mockCacheManager = {
  list: jest.fn() as jest.Mock<() => Promise<any>>,
  delete: jest.fn() as jest.Mock<() => Promise<void>>,
};

describe('getContentForCache', () => {
  const mockRequest: GenerateRequest<z.ZodTypeAny> = {
    config: {
      contextCache: true,
    },
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
      { role: 'user', parts: [{ text: 'Goodbye' }] },
    ],
  };

  test('should throw error if no history is provided', () => {
    expect(() => {
      getContentForCache(mockRequest, { history: [] }, 'gemini-1.5-pro-001');
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
        'gemini-1.5-pro-001'
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
      config: {
        contextCache: true,
      },
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
      'gemini-1.5-pro-001'
    );

    expect(chatRequest.history).toEqual([]); // Test that newHistory is set to an empty array
  });

  test('should split history into cached content and new history', () => {
    const { cachedContent, chatRequest } = getContentForCache(
      mockRequest,
      mockChatRequest,
      'gemini-1.5-pro-001'
    );
    expect(cachedContent.contents).toHaveLength(2); // First two messages are cached
    expect(chatRequest.history).toHaveLength(1); // Only the last message remains in history
  });

  test('should add system instructions if provided in the request', () => {
    const requestWithContext = {
      config: {
        contextCache: {
          context: 'System instruction content',
        },
      },
      messages: [
        {
          role: 'user',
          content: [{ text: 'Hello world' }],
        },
        {
          role: 'model',
          content: [{ text: 'I am a chatbot' }],
          contextCache: true,
        },
        {
          role: 'user',
          content: [{ text: 'Goodbye' }],
        },
      ],
    } as GenerateRequest<z.ZodTypeAny>;

    const chatRequestWithHistory: StartChatParams = {
      history: [
        { role: 'user', parts: [{ text: 'Hello world' }] },
        { role: 'system', parts: [{ text: 'I am a chatbot' }] },
        // @ts-ignore
        { role: 'user', parts: [{ text: 'Goodbye' }] },
      ],
    };

    const { cachedContent } = getContentForCache(
      requestWithContext,
      chatRequestWithHistory,
      'gemini-1.5-pro-001'
    );

    expect(cachedContent.systemInstruction).toEqual({
      role: 'user',
      parts: [{ text: 'System instruction content' }],
    });
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
