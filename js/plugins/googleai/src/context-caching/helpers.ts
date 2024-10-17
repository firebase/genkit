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

import { CachedContent, Content, StartChatParams } from '@google/generative-ai';
import { GoogleAICacheManager } from '@google/generative-ai/server';
import crypto from 'crypto';
import { GenkitError, z } from 'genkit';
import { logger } from 'genkit/logging';
import { GenerateRequest } from 'genkit/model';

export function generateCacheKey(request: CachedContent): string {
  // Select relevant parts of the request to generate a hash (e.g., messages, config)
  const hashInput = JSON.stringify(request);

  return crypto.createHash('sha256').update(hashInput).digest('hex');
}

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
  if (!chatRequest.history || chatRequest.history.length === 0) {
    throw new Error('No history provided for context caching');
  }

  if (chatRequest.history.length !== request.messages.length - 1) {
    throw new GenkitError({
      status: 'INTERNAL',
      message:
        'Genkit request history and Gemini chat request history length do not match',
    });
  }

  const cachedContent: CachedContent = {
    model: modelVersion,
    contents: [],
  };

  const { endOfCachedContents, cacheConfig } = cacheConfigDetails;

  // We split history into two parts: the part that should be cached and the part that should not
  const slicedHistory = chatRequest.history.slice(0, endOfCachedContents + 1);

  cachedContent.contents = slicedHistory;

  let newHistory: Content[];

  if (endOfCachedContents >= chatRequest.history.length - 1) {
    newHistory = [];
  } else {
    newHistory = chatRequest.history.slice(endOfCachedContents + 1);
  }

  debugger;
  chatRequest.history = newHistory;

  return { cachedContent, chatRequest, cacheConfig };
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

const CONTEXT_CACHE_SUPPORTED_MODELS = [
  'gemini-1.5-flash-001',
  'gemini-1.5-pro-001',
];

export const cacheConfigSchema = z.union([
  z.boolean(),
  z.object({ ttlSeconds: z.number().optional() }).passthrough(),
]);

export type CacheConfig = z.infer<typeof cacheConfigSchema>;

export const cacheConfigDetailsSchema = z.object({
  cacheConfig: cacheConfigSchema,
  endOfCachedContents: z.number(),
});

export type CacheConfigDetails = z.infer<typeof cacheConfigDetailsSchema>;

/**
 * Determines if the user wants to use a cache.
 * Extracts cache config and index of the last cache config from the request if present. Otherwise, returns null.
 * @param request
 * @returns
 */
export const extractCacheConfig = (
  request: GenerateRequest<z.ZodTypeAny>
): {
  cacheConfig: { ttlSeconds?: number } | boolean;
  endOfCachedContents: number;
} | null => {
  const endOfCachedContents = request.messages.findLastIndex(
    (message) => message.metadata && message.metadata.cache
  );

  if (endOfCachedContents === -1) {
    return null;
  }

  const cacheConfig = cacheConfigSchema.parse(
    request.messages[endOfCachedContents].metadata?.cache
  );

  return {
    endOfCachedContents,
    cacheConfig,
  };
};

const INVALID_ARGUMENT_MESSAGES = {
  modelVersion: `Model version is required for context caching, which is only supported in ${CONTEXT_CACHE_SUPPORTED_MODELS.join(',')} models.`,
  tools: 'Context caching cannot be used simultaneously with tools.',
  codeExecution:
    'Context caching cannot be used simultaneously with code execution.',
};

/**
 * Once intent to use cache is established, this fuunction is used to validate the caching request.
 * This stops us making an API call to the cache manager if the request is invalid for some reason.
 * If config for caching is present but conflicting features are present, it will throw a 400 GenkitError.
 * @param request
 * @param model
 * @returns
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

  if (request.tools && request.tools.length > 0) {
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: INVALID_ARGUMENT_MESSAGES.tools,
    });
  }

  if (request.config?.codeExecution) {
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: INVALID_ARGUMENT_MESSAGES.codeExecution,
    });
  }

  // If all checks pass, content should be cached
  return true;
}

/**
 * Utility to clear ALL Caches
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
      const cachedContents = list.cachedContents;

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
      throw new GenkitError({
        status: 'INTERNAL',
        message: `Error clearing caches on page ${currentPage + 1}: ${error}`,
      });
    }
  }

  logger.info(`Total caches deleted: ${totalDeleted}`);
}
