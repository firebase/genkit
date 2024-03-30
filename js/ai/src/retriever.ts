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

import { action, Action } from '@genkit-ai/core';
import { lookupAction, registerAction } from '@genkit-ai/core/registry';
import { setCustomMetadataAttributes } from '@genkit-ai/core/tracing';
import * as z from 'zod';
import { Document, DocumentData, DocumentDataSchema } from './document.js';
import { EmbedderInfo } from './embedder.js';

export { Document, DocumentData, DocumentDataSchema } from './document.js';

type RetrieverFn<RetrieverOptions extends z.ZodTypeAny> = (
  query: Document,
  queryOpts: z.infer<RetrieverOptions>
) => Promise<RetrieverResponse>;

type IndexerFn<IndexerOptions extends z.ZodTypeAny> = (
  docs: Array<Document>,
  indexerOpts: z.infer<IndexerOptions>
) => Promise<void>;

const RetrieverRequestSchema = z.object({
  query: DocumentDataSchema,
  options: z.any().optional(),
});

const RetrieverResponseSchema = z.object({
  documents: z.array(DocumentDataSchema),
  // TODO: stats, etc.
});
type RetrieverResponse = z.infer<typeof RetrieverResponseSchema>;

const IndexerRequestSchema = z.object({
  documents: z.array(DocumentDataSchema),
  options: z.any().optional(),
});

export const RetrieverInfoSchema = z.object({
  label: z.string().optional(),
  /** Supported model capabilities. */
  supports: z
    .object({
      /** Model can process media as part of the prompt (multimodal input). */
      media: z.boolean().optional(),
    })
    .optional(),
});
export type RetrieverInfo = z.infer<typeof RetrieverInfoSchema>;

export type RetrieverAction<CustomOptions extends z.ZodTypeAny = z.ZodTypeAny> =
  Action<
    typeof RetrieverRequestSchema,
    typeof RetrieverResponseSchema,
    { model: RetrieverInfo }
  > & {
    __configSchema?: CustomOptions;
  };

export type IndexerAction<IndexerOptions extends z.ZodTypeAny = z.ZodTypeAny> =
  Action<typeof IndexerRequestSchema, z.ZodVoid> & {
    __configSchema?: IndexerOptions;
  };

function retrieverWithMetadata<
  RetrieverOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  retriever: Action<
    typeof RetrieverRequestSchema,
    typeof RetrieverResponseSchema
  >,
  configSchema?: RetrieverOptions
): RetrieverAction<RetrieverOptions> {
  const withMeta = retriever as RetrieverAction<RetrieverOptions>;
  withMeta.__configSchema = configSchema;
  return withMeta;
}

function indexerWithMetadata<
  IndexerOptions extends z.ZodTypeAny = z.ZodTypeAny,
>(
  indexer: Action<typeof IndexerRequestSchema, z.ZodVoid>,
  configSchema?: IndexerOptions
): IndexerAction<IndexerOptions> {
  const withMeta = indexer as IndexerAction<IndexerOptions>;
  withMeta.__configSchema = configSchema;
  return withMeta;
}

/**
 *  Creates a retriever action for the provided {@link RetrieverFn} implementation.
 */
export function defineRetriever<
  OptionsType extends z.ZodTypeAny = z.ZodTypeAny,
>(
  options: {
    name: string;
    configSchema?: OptionsType;
    info?: RetrieverInfo;
  },
  runner: RetrieverFn<OptionsType>
) {
  const retriever = action(
    {
      name: options.name,
      inputSchema: options.configSchema
        ? RetrieverRequestSchema.extend({
            options: options.configSchema.optional(),
          })
        : RetrieverRequestSchema,
      outputSchema: RetrieverResponseSchema,
      metadata: {
        type: 'retriever',
        info: options.info,
      },
    },
    (i) => {
      setCustomMetadataAttributes({ subtype: 'retriever' });
      return runner(new Document(i.query), i.options);
    }
  );
  const rwm = retrieverWithMetadata(
    retriever as Action<
      typeof RetrieverRequestSchema,
      typeof RetrieverResponseSchema
    >,
    options.configSchema
  );
  registerAction('retriever', rwm.__action.name, rwm);
  return rwm;
}

/**
 *  Creates an indexer action for the provided {@link IndexerFn} implementation.
 */
export function defineIndexer<IndexerOptions extends z.ZodTypeAny>(
  options: {
    name: string;
    embedderInfo?: EmbedderInfo;
    configSchema?: IndexerOptions;
  },
  runner: IndexerFn<IndexerOptions>
) {
  const indexer = action(
    {
      name: options.name,
      inputSchema: options.configSchema
        ? IndexerRequestSchema.extend({
            options: options.configSchema.optional(),
          })
        : IndexerRequestSchema,
      outputSchema: z.void(),
      metadata: {
        type: 'indexer',
        embedderInfo: options.embedderInfo,
      },
    },
    (i) => {
      setCustomMetadataAttributes({ subtype: 'indexer' });
      return runner(
        i.documents.map((dd) => new Document(dd)),
        i.options
      );
    }
  );
  const iwm = indexerWithMetadata(
    indexer as Action<typeof IndexerRequestSchema, z.ZodVoid>,
    options.configSchema
  );
  registerAction('indexer', iwm.__action.name, iwm);
  return iwm;
}

export interface RetrieverParams<
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> {
  retriever: RetrieverArgument<CustomOptions>;
  query: string | DocumentData;
  options?: z.infer<CustomOptions>;
}

export type RetrieverArgument<
  CustomOptions extends z.ZodTypeAny = z.ZodTypeAny,
> = RetrieverAction<CustomOptions> | RetrieverReference<CustomOptions> | string;

/**
 * Retrieves documents from a {@link RetrieverAction} based on the provided query.
 */
export async function retrieve<CustomOptions extends z.ZodTypeAny>(
  params: RetrieverParams<CustomOptions>
): Promise<Array<Document>> {
  let retriever: RetrieverAction<CustomOptions>;
  if (typeof params.retriever === 'string') {
    retriever = await lookupAction(`/retriever/${params.retriever}`);
  } else if (Object.hasOwnProperty.call(params.retriever, 'info')) {
    retriever = await lookupAction(`/retriever/${params.retriever.name}`);
  } else {
    retriever = params.retriever as RetrieverAction<CustomOptions>;
  }
  if (!retriever) {
    throw new Error('Unable to resolve the retriever');
  }
  const response = await retriever({
    query:
      typeof params.query === 'string'
        ? Document.fromText(params.query)
        : params.query,
    options: params.options,
  });

  return response.documents.map((d) => new Document(d));
}

export type IndexerArgument<CustomOptions extends z.ZodTypeAny = z.ZodTypeAny> =
  IndexerReference<CustomOptions> | IndexerAction<CustomOptions> | string;

/**
 * Indexes documents using a {@link IndexerAction} or a {@link DocumentStore}.
 */
export async function index<IndexerOptions extends z.ZodTypeAny>(params: {
  indexer: IndexerArgument<IndexerOptions>;
  documents: Array<DocumentData>;
  options?: z.infer<IndexerOptions>;
}): Promise<void> {
  let indexer: IndexerAction<IndexerOptions>;
  if (typeof params.indexer === 'string') {
    indexer = await lookupAction(`/indexer/${params.indexer}`);
  } else if (Object.hasOwnProperty.call(params.indexer, 'info')) {
    indexer = await lookupAction(`/indexer/${params.indexer.name}`);
  } else {
    indexer = params.indexer as IndexerAction<IndexerOptions>;
  }
  if (!indexer) {
    throw new Error('Unable to utilize the provided indexer');
  }
  return await indexer({
    documents: params.documents,
    options: params.options,
  });
}

export const CommonRetrieverOptionsSchema = z.object({
  k: z.number().describe('Number of documents to retrieve').optional(),
});

export interface RetrieverReference<CustomOptions extends z.ZodTypeAny> {
  name: string;
  configSchema?: CustomOptions;
  info?: RetrieverInfo;
}

/**
 * Helper method to configure a {@link RetrieverReference} to a plugin.
 */
export function retrieverRef<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
>(
  options: RetrieverReference<CustomOptionsSchema>
): RetrieverReference<CustomOptionsSchema> {
  return { ...options };
}

// Reuse the same schema for both indexers and retrievers -- for now.
export const IndexerInfoSchema = RetrieverInfoSchema;
export type IndexerInfo = z.infer<typeof IndexerInfoSchema>;

export interface IndexerReference<CustomOptions extends z.ZodTypeAny> {
  name: string;
  configSchema?: CustomOptions;
  info?: IndexerInfo;
}

/**
 * Helper method to configure a {@link IndexerReference} to a plugin.
 */
export function indexerRef<
  CustomOptionsSchema extends z.ZodTypeAny = z.ZodTypeAny,
>(
  options: IndexerReference<CustomOptionsSchema>
): IndexerReference<CustomOptionsSchema> {
  return { ...options };
}
