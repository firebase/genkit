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

import { GenkitError } from '@genkit-ai/core';
import { z } from 'zod';
import { Document, defineRetriever } from './retriever.js';

function itemToDocument<R>(
  item: any,
  options: SimpleRetrieverOptions
): Document {
  if (!item)
    throw new GenkitError({
      status: 'INVALID_ARGUMENT',
      message: `Items returned from simple retriever must be non-null.`,
    });
  if (typeof item === 'string') return Document.fromText(item);
  if (typeof options.content === 'function') {
    const transformed = options.content(item);
    return typeof transformed === 'string'
      ? Document.fromText(transformed)
      : new Document({ content: transformed });
  }
  if (typeof options.content === 'string' && typeof item === 'object')
    return new Document(item[options.content]);
  throw new GenkitError({
    status: 'INVALID_ARGUMENT',
    message: `Cannot convert item to document without content option. Item: ${JSON.stringify(item)}`,
  });
}

function itemToMetadata(
  item: any,
  options: SimpleRetrieverOptions
): Document['metadata'] {
  if (typeof item === 'string') return undefined;
  if (Array.isArray(options.metadata) && typeof item === 'object') {
    const out: Record<string, any> = {};
    options.metadata.forEach((key) => (out[key] = item[key]));
  }
  if (typeof options.metadata === 'function') return options.metadata(item);
  if (!options.metadata && typeof item === 'object') {
    const out = { ...item };
    if (typeof options.content === 'string') delete out[options.content];
    return out;
  }
  throw new GenkitError({
    status: 'INVALID_ARGUMENT',
    message: `Unable to extract metadata from item with supplied options. Item: ${JSON.stringify(item)}`,
  });
}

export interface SimpleRetrieverOptions<
  C extends z.ZodTypeAny = z.ZodTypeAny,
  R = any,
> {
  /** The name of the retriever you're creating. */
  name: string;
  /** A Zod schema containing any configuration info available beyond the query. */
  configSchema?: C;
  /**
   * Specifies how to extract content from the returned items.
   *
   * - If a string, specifies the key of the returned item to extract as content.
   * - If a function, allows you to extract content as text or a document part.
   **/
  content?: string | ((item: R) => Document['content'] | string);
  /**
   * Specifies how to extract metadata from the returned items.
   *
   * - If an array of strings, specifies list of keys to extract from returned objects.
   * - If a function, allows you to use custom behavior to extract metadata from returned items.
   */
  metadata?: string[] | ((item: R) => Document['metadata']);
}

/**
 * defineSimpleRetriever makes it easy to map existing data into documents that
 * can be used for prompt augmentation.
 *
 * @param options Configuration options for the retriever.
 * @param handler A function that queries a datastore and returns items from which to extract documents.
 * @returns A Genkit retriever.
 */
export function defineSimpleRetriever<
  C extends z.ZodTypeAny = z.ZodTypeAny,
  R = any,
>(
  options: SimpleRetrieverOptions<C, R>,
  handler: (query: Document, config: z.infer<C>) => Promise<R[]>
) {
  return defineRetriever(
    {
      name: options.name,
      configSchema: options.configSchema,
    },
    async (query, config) => {
      const result = await handler(query, config);
      return {
        documents: result.map((item) => {
          const doc = itemToDocument(item, options);
          if (typeof item !== 'string')
            doc.metadata = itemToMetadata(item, options);
          return doc;
        }),
      };
    }
  );
}
