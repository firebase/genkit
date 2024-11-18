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
import crypto from 'crypto';
import { GenkitError, MessageData, z } from 'genkit';
import { logger } from 'genkit/logging';
import { GenerateRequest } from 'genkit/model';
import {
  CONTEXT_CACHE_SUPPORTED_MODELS,
  DEFAULT_TTL,
  INVALID_ARGUMENT_MESSAGES,
} from './constants';
import { CacheConfig, CacheConfigDetails, cacheConfigSchema } from './types';

/**
 * Generates a SHA-256 hash to use as a cache key.
 * @param request CachedContent - request object to hash
 * @returns string - the generated cache key
 */
export function generateCacheKey(request: CachedContent): string {
  return crypto
    .createHash('sha256')
    .update(JSON.stringify(request))
    .digest('hex');
}

/**
 * Retrieves the content needed for the cache based on the chat history and config details.
 */
export function getContentForCache(
  request: GenerateRequest<z.ZodTypeAny>,
  chatRequest: StartChatParams,
  modelVersion: string,
  cacheConfigDetails: CacheConfigDetails
): {
  cachedContent: CachedContent;
  chatRequest: StartChatParams;
  cacheConfig?: CacheConfig;
} {
  if (!chatRequest.history?.length) {
    throw new Error('No history provided for context caching');
  }

  validateHistoryLength(request, chatRequest);

  const { endOfCachedContents, cacheConfig } = cacheConfigDetails;
  const cachedContent: CachedContent = {
    model: modelVersion,
    contents: chatRequest.history.slice(0, endOfCachedContents + 1),
  };
  chatRequest.history = chatRequest.history.slice(endOfCachedContents + 1);

  return { cachedContent, chatRequest, cacheConfig };
}

/**
 * Validates that the request and chat request history lengths align.
 * @throws GenkitError if lengths are mismatched
 */
function validateHistoryLength(
  request: GenerateRequest<z.ZodTypeAny>,
  chatRequest: StartChatParams
) {
  if (chatRequest.history?.length !== request.messages.length - 1) {
    throw new GenkitError({
      status: 'INTERNAL',
      message:
        'Genkit request history and Gemini chat request history length do not match',
    });
  }
}

/**
 * Looks up context cache using a cache manager and returns the found item, if any.
 */
export async function lookupContextCache(
  cacheManager: GoogleAICacheManager,
  cacheKey: string,
  maxPages = 100,
  pageSize = 100
) {
  let currentPage = 0;
  let pageToken: string | undefined;

  while (currentPage < maxPages) {
    const { cachedContents, nextPageToken } = await cacheManager.list({
      pageSize,
      pageToken,
    });
    const found = cachedContents?.find(
      (content) => content.displayName === cacheKey
    );

    if (found) return found;
    if (!nextPageToken) break;

    pageToken = nextPageToken;
    currentPage++;
  }
  return null;
}

/**
 * Clears all caches using the cache manager.
 */
export async function clearAllCaches(
  cacheManager: GoogleAICacheManager,
  maxPages = 100,
  pageSize = 100
): Promise<void> {
  let currentPage = 0;
  let pageToken: string | undefined;
  let totalDeleted = 0;

  while (currentPage < maxPages) {
    try {
      const { cachedContents, nextPageToken } = await cacheManager.list({
        pageSize,
        pageToken,
      });
      totalDeleted += await deleteCachedContents(cacheManager, cachedContents);

      if (!nextPageToken) break;
      pageToken = nextPageToken;
      currentPage++;
    } catch (error) {
      throw new GenkitError({
        status: 'INTERNAL',
        message: `Error clearing caches on page ${currentPage + 1}: ${error}`,
      });
    }
  }
  logger.info(`Total caches deleted: ${totalDeleted}`);
}

/**
 * Helper to delete cached contents and return the number of deletions.
 */
async function deleteCachedContents(
  cacheManager: GoogleAICacheManager,
  cachedContents: CachedContent[] = []
): Promise<number> {
  for (const content of cachedContents) {
    if (content.name) await cacheManager.delete(content.name);
  }
  return cachedContents.length;
}

/**
 * Extracts the cache configuration from the request if available.
 */
export const extractCacheConfig = (
  request: GenerateRequest<z.ZodTypeAny>
): {
  cacheConfig: { ttlSeconds?: number } | boolean;
  endOfCachedContents: number;
} | null => {
  const endOfCachedContents = findLastIndex<MessageData>(
    request.messages,
    (message) => !!message.metadata?.cache
  );

  return endOfCachedContents === -1
    ? null
    : {
        endOfCachedContents,
        cacheConfig: cacheConfigSchema.parse(
          request.messages[endOfCachedContents].metadata?.cache
        ),
      };
};

/**
 * Validates context caching request for compatibility with model and request configurations.
 */
export function validateContextCacheRequest(
  request: any,
  modelVersion: string
): boolean {
  if (!modelVersion || !CONTEXT_CACHE_SUPPORTED_MODELS.includes(modelVersion)) {
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: INVALID_ARGUMENT_MESSAGES.modelVersion,
    });
  }
  if (request.tools?.length)
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: INVALID_ARGUMENT_MESSAGES.tools,
    });
  if (request.config?.codeExecution)
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: INVALID_ARGUMENT_MESSAGES.codeExecution,
    });

  return true;
}

/**
 * Polyfill function for Array.prototype.findLastIndex for ES2015 compatibility.
 */
function findLastIndex<T>(
  array: T[],
  callback: (element: T, index: number, array: T[]) => boolean
): number {
  for (let i = array.length - 1; i >= 0; i--) {
    if (callback(array[i], i, array)) return i;
  }
  return -1;
}

/**
 * Calculates the TTL (Time-To-Live) for the cache based on cacheConfigDetails.
 * @param cacheConfig - The caching configuration details.
 * @returns The TTL in seconds.
 */
export function calculateTTL(cacheConfig: CacheConfigDetails): number {
  if (cacheConfig.cacheConfig === true) {
    return DEFAULT_TTL;
  }
  if (cacheConfig.cacheConfig === false) {
    return 0;
  }
  return cacheConfig.cacheConfig.ttlSeconds || DEFAULT_TTL;
}