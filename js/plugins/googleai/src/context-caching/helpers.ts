import { CachedContent, StartChatParams } from '@google/generative-ai';
import { GoogleAICacheManager } from '@google/generative-ai/server';
import { z } from 'genkit';
import { logger } from 'genkit/logging';
import { GenerateRequest } from 'genkit/model';
import { toGeminiSystemInstruction } from '../gemini';

export function getContentForCache(
  request: GenerateRequest<z.ZodTypeAny>,
  chatRequest: StartChatParams,
  model: string
): {
  cachedContent: CachedContent;
  chatRequest: StartChatParams;
} {
  if (!chatRequest.history || chatRequest.history.length === 0) {
    throw new Error('No history provided for context caching');
  }

  const cachedContent: CachedContent = {
    model: model,
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

export async function lookupContextCache(
  cacheManager: GoogleAICacheManager,
  cacheKey,
  maxPages = 3,
  pageSize?: number
) {
  let currentPage = 0;
  let pageToken: string | undefined = undefined;

  while (currentPage < maxPages) {
    const listParams = { pageSize, pageToken };

    const list = await cacheManager.list(listParams);

    if (list.nextPageToken) {
      pageToken = list.nextPageToken;
    } else {
      break;
    }
    const cachedContents = list.cachedContents;

    logger.info('cachedContents', cachedContents);

    const found = cachedContents?.find(
      (content) => content.displayName === cacheKey
    );

    if (found) {
      return found;
    }

    currentPage++;
  }
  return null;
}
