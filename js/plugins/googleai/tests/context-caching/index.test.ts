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
import { beforeEach, describe, expect, jest, test } from '@jest/globals';
import { GenerateRequest, GenkitError, z } from 'genkit';
import { logger } from 'genkit/logging';
import {
  generateCacheKey,
  getContentForCache,
  lookupContextCache,
} from '../../src/context-caching/helpers';
import { handleContextCache } from '../../src/context-caching/index';

// Mocking GoogleAICacheManager methods
const mockCreate = jest.fn() as jest.Mock<() => Promise<CachedContent | null>>;
const mockList = jest.fn() as jest.Mock<() => Promise<CachedContent[]>>;

jest.mock('@google/generative-ai/server', () => ({
  GoogleAICacheManager: jest.fn().mockImplementation(() => ({
    create: mockCreate,
    list: mockList,
  })),
}));

jest.mock('genkit/logging', () => ({
  logger: {
    debug: jest.fn(),
    error: jest.fn(),
  },
}));

jest.mock('../../src/context-caching/helpers', () => ({
  generateCacheKey: jest.fn(),
  getContentForCache: jest.fn(),
  lookupContextCache: jest.fn(),
}));

describe('handleContextCache', () => {
  const apiKey = 'test-api-key';
  const modelVersion = 'gemini-1.5-pro-001';
  let mockRequest: GenerateRequest<z.ZodTypeAny>;
  let mockChatRequest: StartChatParams;
  let mockCachedContent: CachedContent;

  beforeEach(() => {
    jest.clearAllMocks();

    mockRequest = {
      config: { contextCache: true },
      messages: [
        { role: 'user', content: [{ text: 'Hello world' }] },
        { role: 'model', content: [{ text: 'I am a chatbot' }] },
      ],
    } as GenerateRequest<z.ZodTypeAny>;

    mockChatRequest = {
      history: [
        { role: 'user', parts: [{ text: 'Hello world' }] },
        { role: 'model', parts: [{ text: 'I am a chatbot' }] },
      ],
    };

    mockCachedContent = {
      model: modelVersion,
      contents: [
        { role: 'user', parts: [{ text: 'Hello world' }] },
        { role: 'model', parts: [{ text: 'I am a chatbot' }] },
      ],
      displayName: 'cacheKey123',
      ttlSeconds: 500,
    } as CachedContent;

    (
      getContentForCache as jest.Mock<typeof getContentForCache>
    ).mockReturnValue({
      cachedContent: mockCachedContent,
      chatRequest: mockChatRequest,
    });
    (generateCacheKey as jest.Mock<typeof generateCacheKey>).mockReturnValue(
      'cacheKey123'
    );
    (
      lookupContextCache as jest.Mock<typeof lookupContextCache>
    ).mockResolvedValue(null);
  });

  test('should return cache and transformed chat request if cache is created', async () => {
    mockCreate.mockResolvedValue(mockCachedContent);

    const result = await handleContextCache(
      apiKey,
      mockRequest,
      mockChatRequest,
      modelVersion,
      { endOfCachedContents: 1, cacheConfig: true }
    );

    expect(getContentForCache).toHaveBeenCalledWith(
      mockRequest,
      mockChatRequest,
      modelVersion,
      { endOfCachedContents: 1, cacheConfig: true }
    );
    expect(generateCacheKey).toHaveBeenCalledWith(mockCachedContent);
    expect(lookupContextCache).toHaveBeenCalledWith(
      expect.anything(),
      'cacheKey123'
    );
    expect(mockCreate).toHaveBeenCalledWith(mockCachedContent);
    expect(result.cache).toEqual(mockCachedContent);
    expect(result.newChatRequest).toEqual(mockChatRequest);
  });

  test('should return cache and transformed chat request if cache is found', async () => {
    (
      lookupContextCache as jest.Mock<typeof lookupContextCache>
    ).mockResolvedValueOnce(mockCachedContent);

    const result = await handleContextCache(
      apiKey,
      mockRequest,
      mockChatRequest,
      modelVersion,
      { endOfCachedContents: 1, cacheConfig: true }
    );

    expect(lookupContextCache).toHaveBeenCalledWith(
      expect.anything(),
      'cacheKey123'
    );
    expect(result.cache).toEqual(mockCachedContent);
    expect(result.newChatRequest).toEqual(mockChatRequest);
  });

  test('should throw GenkitError if cache creation fails', async () => {
    mockCreate.mockRejectedValueOnce(new Error('Cache creation failed'));

    await expect(
      handleContextCache(apiKey, mockRequest, mockChatRequest, modelVersion, {
        endOfCachedContents: 1,
        cacheConfig: true,
      })
    ).rejects.toThrowError(
      new GenkitError({
        status: 'INTERNAL',
        message: 'Failed to create cache: Error: Cache creation failed',
      })
    );

    expect(logger.debug).toHaveBeenCalledWith('No cache found, creating one.');
  });

  test('should throw GenkitError if cache lookup and creation both fail', async () => {
    mockCreate.mockResolvedValueOnce(null);

    await expect(
      handleContextCache(apiKey, mockRequest, mockChatRequest, modelVersion, {
        endOfCachedContents: 1,
        cacheConfig: true,
      })
    ).rejects.toThrowError(
      new GenkitError({
        status: 'INTERNAL',
        message: 'Failed to use context cache feature',
      })
    );

    expect(mockCreate).toHaveBeenCalled();
  });
});
