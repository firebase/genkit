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
import { GenkitError, ModelReference, z } from 'genkit';
import { logger } from 'genkit/logging';
import { GenerateRequest } from 'genkit/model';
import { toGeminiSystemInstruction } from '../gemini';

export function generateCacheKey(request: CachedContent): string {
  // Select relevant parts of the request to generate a hash (e.g., messages, config)
  const hashInput = JSON.stringify(request);

  return crypto.createHash('sha256').update(hashInput).digest('hex');
}

export function getContentForCache(
  request: GenerateRequest<z.ZodTypeAny>,
  chatRequest: StartChatParams,
  modelVersion: string
): {
  cachedContent: CachedContent;
  chatRequest: StartChatParams;
} {
  if (!chatRequest.history || chatRequest.history.length === 0) {
    throw new Error('No history provided for context caching');
  }

  logger.info('model version', modelVersion);

  const cachedContent: CachedContent = {
    model: modelVersion,
    contents: [],
  };

  const endOfCachedContents = chatRequest.history.findIndex(
    // @ts-ignore
    (message) => message.contextCache
  );

  // We split history into two parts: the part that should be cached and the part that should not
  const slicedHistory = chatRequest.history.slice(0, endOfCachedContents);
  logger.info(
    'last of cached contents',
    JSON.stringify(slicedHistory.map((m) => m.role))
  );
  cachedContent.contents = slicedHistory;

  let newHistory;

  if (endOfCachedContents >= chatRequest.history.length - 1) {
    newHistory = [];
  } else {
    newHistory = chatRequest.history.slice(endOfCachedContents + 1);
  }
  chatRequest.history = newHistory;

  logger.info('new history', JSON.stringify(newHistory.map((m) => m.role)));

  if (request.config?.contextCache?.context) {
    cachedContent.systemInstruction = toGeminiSystemInstruction({
      role: 'system',
      content: [{ text: request.config.contextCache.context }],
    });
  }

  return { cachedContent, chatRequest };
}

/**
 * Lookup context cache by cache key.
 * @param cacheManager
 * @param cacheKey
 * @param maxPages
 * @param pageSize
 * @returns
 */
export async function lookupContextCache(
  cacheManager: GoogleAICacheManager,
  cacheKey: string,
  maxPages = 100, // what should the max pages and page size be?
  pageSize?: number
) {
  let currentPage = 0;
  let pageToken: string | undefined = undefined;

  while (currentPage < maxPages) {
    const listParams = { pageSize, pageToken };

    const list = await cacheManager.list(listParams);

    const cachedContents = list.cachedContents;

    // for (const content of cachedContents) {
    //   await cacheManager.delete(content.name!);
    // }

    const found = cachedContents?.find(
      (content) => content.displayName === cacheKey
    );

    if (found) {
      return found;
    }
    if (list.nextPageToken) {
      pageToken = list.nextPageToken;
    }

    currentPage++;
  }
  return null;
}

/**
 * Function to validate request and model to determine if content should be cached.
 * If config for caching is present but conflicting features are present, it will throw a 400 GenkitError.
 * @param request
 * @param model
 * @returns
 */
export function validateContextCacheRequest(
  request: any,
  model: ModelReference<z.ZodTypeAny>,
  modelVersion: string
): boolean {
  // Check if contextCache is requested in the config
  if (!request.config?.contextCache) {
    logger.info('Context caching is not requested');
    return false;
  }

  if (
    !modelVersion ||
    !['gemini-1.5-flash-001', 'gemini-1.5-pro-001'].includes(modelVersion)
  ) {
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message:
        'Model version is required for context caching, only on 001 models',
    });
  }

  // Check if the model supports contextCache
  // @ts-ignore
  if (!model?.info?.supports?.contextCache) {
    return false;
  }

  // Check for conflicting features
  if (request.config?.systemInstruction) {
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: 'Context caching cannot be used with system instructions',
    });
  }

  if (request.tools && request.tools.length > 0) {
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: 'Context caching cannot be used with tools',
    });
  }

  if (request.config?.codeExecution) {
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: 'Context caching cannot be used with code execution',
    });
  }

  logger.info('Context caching is valid for this request');
  // If all checks pass, content should be cached
  return true;
}

/**
 * Clears ALL
 * @param cacheManager
 * @param maxPages
 * @param pageSize
 */
export async function clearAllCaches(
  cacheManager: GoogleAICacheManager,
  maxPages = 100,
  pageSize = 100
): Promise<void> {
  let currentPage = 0;
  let pageToken: string | undefined = undefined;
  let totalDeleted = 0;

  while (currentPage < maxPages) {
    const listParams = { pageSize, pageToken };

    try {
      const list = await cacheManager.list(listParams);
      const cachedContents = list.cachedContents || [];

      for (const content of cachedContents) {
        if (content.name) {
          await cacheManager.delete(content.name);
          totalDeleted++;
        }
      }

      logger.info(
        `Deleted ${cachedContents.length} caches on page ${currentPage + 1}`
      );

      if (list.nextPageToken) {
        pageToken = list.nextPageToken;
        currentPage++;
      } else {
        break; // No more pages to process
      }
    } catch (error) {
      logger.error(`Error clearing caches on page ${currentPage + 1}:`, error);
      throw error;
    }
  }

  logger.info(`Total caches deleted: ${totalDeleted}`);
}