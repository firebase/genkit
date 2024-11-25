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
import {
  CachedContentCreateParams,
  GoogleAICacheManager,
} from '@google/generative-ai/server';
import { GenerateRequest, GenkitError, z } from 'genkit';
import { logger } from 'genkit/logging';
import type { CacheConfigDetails } from './types.js';
import {
  calculateTTL,
  generateCacheKey,
  getContentForCache,
  lookupContextCache,
  validateContextCacheRequest,
} from './utils.js';

/**
 * Handles context caching and transforms the chatRequest
 * @param apiKey
 * @param request
 * @param chatRequest
 * @param modelVersion
 * @returns
 */
export async function handleContextCache(
  apiKey: string,
  request: GenerateRequest<z.ZodTypeAny>,
  chatRequest: StartChatParams,
  modelVersion: string,
  cacheConfigDetails: CacheConfigDetails
): Promise<{ cache: CachedContent; newChatRequest: StartChatParams }> {
  const cacheManager = new GoogleAICacheManager(apiKey);

  const { cachedContent, chatRequest: newChatRequest } = getContentForCache(
    request,
    chatRequest,
    modelVersion,
    cacheConfigDetails
  );
  cachedContent.model = modelVersion;
  const cacheKey = generateCacheKey(cachedContent);

  cachedContent.displayName = cacheKey;

  let cache = await lookupContextCache(cacheManager, cacheKey);
  logger.debug(`Cache hit: ${cache ? 'true' : 'false'}`);

  if (!cache) {
    try {
      logger.debug('No cache found, creating one.');
      const createParams: CachedContentCreateParams = {
        ...cachedContent,
        ttlSeconds: calculateTTL(cacheConfigDetails),
      };
      cache = await cacheManager.create(createParams);
      logger.debug(`Created new cache entry with key: ${cacheKey}`);
    } catch (cacheError) {
      logger.error(
        `Failed to create cache with key ${cacheKey}: ${cacheError}`
      );
      throw new GenkitError({
        status: 'INTERNAL',
        message: `Failed to create cache: ${cacheError}`,
      });
    }
  }

  if (!cache) {
    throw new GenkitError({
      status: 'INTERNAL',
      message: 'Failed to use context cache feature',
    });
  }

  return { cache, newChatRequest };
}

/**
 * Handles cache validation, creation, and usage, transforming the chatRequest if necessary.
 * @param apiKey The API key for accessing Google AI Gemini.
 * @param request The generate request passed to the model.
 * @param chatRequest The current chat request configuration.
 * @param modelVersion The version of the model being used.
 * @param cacheConfigDetails Configuration details for caching.
 * @returns A transformed chat request and cache data (if applicable).
 */
export async function handleCacheIfNeeded(
  apiKey: string,
  request: GenerateRequest<z.ZodTypeAny>,
  chatRequest: StartChatParams,
  modelVersion: string,
  cacheConfigDetails: CacheConfigDetails | null
): Promise<{ chatRequest: StartChatParams; cache: CachedContent | null }> {
  // Skip caching if no configuration or if validation fails
  if (
    !cacheConfigDetails ||
    !validateContextCacheRequest(request, modelVersion)
  ) {
    return { chatRequest, cache: null };
  }

  const { cache, newChatRequest } = await handleContextCache(
    apiKey,
    request,
    chatRequest,
    modelVersion,
    cacheConfigDetails
  );
  return { chatRequest: newChatRequest, cache };
}
