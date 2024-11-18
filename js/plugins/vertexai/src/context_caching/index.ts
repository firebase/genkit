/**
 * @license
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 */

import { CachedContent, StartChatParams } from '@google-cloud/vertexai';
import {
  ApiClient,
  CachedContents,
} from '@google-cloud/vertexai/build/src/resources';
import { GenerateRequest, GenkitError, z } from 'genkit';
import { logger } from 'genkit/logging';
import type { CacheConfigDetails } from './types.js';
import {
  calculateTTL,
  generateCacheKey,
  getContentForCache,
  lookupContextCache,
} from './utils.js';

/**
 * Handles context caching and transforms the chatRequest for Vertex AI.
 * @param apiKey
 * @param request
 * @param chatRequest
 * @param modelVersion
 * @returns
 */
export async function handleContextCache(
  apiClient: ApiClient,
  request: GenerateRequest<z.ZodTypeAny>,
  chatRequest: StartChatParams,
  modelVersion: string,
  cacheConfigDetails: CacheConfigDetails
): Promise<{ cache: CachedContent; newChatRequest: StartChatParams }> {
  const cachedContentsClient = new CachedContents(apiClient);

  const { cachedContent, chatRequest: newChatRequest } = getContentForCache(
    request,
    chatRequest,
    modelVersion,
    cacheConfigDetails
  );
  cachedContent.model = modelVersion;
  const cacheKey = generateCacheKey(cachedContent);

  cachedContent.displayName = cacheKey;

  let cache;
  try {
    cache = await lookupContextCache(cachedContentsClient, cacheKey);
    logger.debug(`Cache hit: ${cache ? 'true' : 'false'}`);
  } catch (error) {
    logger.debug('No cache found, creating one.');
  }

  if (!cache) {
    try {
      const createParams: CachedContent = {
        ...cachedContent,
        // TODO: make this neater - idk why they chose to stringify the ttl...
        ttl: JSON.stringify(calculateTTL(cacheConfigDetails)) + 's',
      };
      cache = await cachedContentsClient.create(createParams);
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
  // This isn't necessary, but it's nice to have for debugging purposes.
  newChatRequest.cachedContent = cache.name;

  return { cache, newChatRequest };
}
