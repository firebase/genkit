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

import type { CachedContent, StartChatParams } from '@google-cloud/vertexai';
import assert from 'assert';
import crypto from 'crypto';
import type { GenerateRequest } from 'genkit';
import { describe, it } from 'node:test';
import { DEFAULT_TTL } from '../../src/context-caching/constants.js';
import type { CacheConfigDetails } from '../../src/context-caching/types.js';
import {
  calculateTTL,
  extractCacheConfig,
  generateCacheKey,
  getContentForCache,
  lookupContextCache,
} from '../../src/context-caching/utils.js';

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
});

describe('getContentForCache', () => {
  it('should correctly retrieve cached content and updated chat request', () => {
    const request: GenerateRequest<any> = {
      messages: [
        { role: 'system', content: [{ text: 'System message' }] },
        { role: 'user', content: [{ text: 'Hello!' }] },
      ],
    };
    const chatRequest: StartChatParams = {
      history: [{ role: 'system', parts: [{ text: 'System message' }] }],
    };
    const modelVersion = 'vertexai-gpt';
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
    assert.deepStrictEqual(result.chatRequest.history, []);
    assert.deepStrictEqual(result.cacheConfig, { ttlSeconds: 300 });
  });
});

describe('lookupContextCache', () => {
  it('should return the cached content if found', async () => {
    const mockCacheManager = {
      list: async (pageSize: number, pageToken?: string) => ({
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

  it('should return null if the cached content is not found', async () => {
    const mockCacheManager = {
      list: async (pageSize: number, pageToken?: string) => ({
        cachedContents: [{ displayName: 'key3', data: 'value3' }],
        nextPageToken: undefined,
      }),
    };

    const result = await lookupContextCache(mockCacheManager as any, 'key1');
    assert.strictEqual(result, null);
  });
});

describe('extractCacheConfig', () => {
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
});
