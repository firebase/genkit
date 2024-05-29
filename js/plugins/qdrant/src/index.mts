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

import { embed, EmbedderArgument } from '@genkit-ai/ai/embedder';
import {
  CommonRetrieverOptionsSchema,
  defineIndexer,
  defineRetriever,
  Document,
  indexerRef,
  retrieverRef,
} from '@genkit-ai/ai/retriever';
import { genkitPlugin, PluginProvider } from '@genkit-ai/core';
import type { QdrantClientParams, Schemas } from '@qdrant/js-client-rest';
import { QdrantClient } from '@qdrant/js-client-rest';
import { v5 as uuidv5 } from 'uuid';
import * as z from 'zod';

const FilterType: z.ZodType<Schemas['Filter']> = z.any();

const QdrantRetrieverOptionsSchema = CommonRetrieverOptionsSchema.extend({
  k: z.number().default(10),
  filter: FilterType.optional(),
});

export const QdrantIndexerOptionsSchema = z.null().optional();

const CONTENT_PAYLOAD_KEY = 'content';
const METADATA_PAYLOAD_KEY = 'metadata';

/**
 * Parameters for the Qdrant plugin.
 */
interface QdrantPluginParams<E extends z.ZodTypeAny = z.ZodTypeAny> {
  /**
   * Parameters for instantiating `QdrantClient`.
   */
  clientParams: QdrantClientParams;
  /**
   * Name of the Qdrant collection.
   */
  collectionName: string;
  /**
   * Embedder to use for the retriever and indexer.
   */
  embedder: EmbedderArgument<E>;
  /**
   * Addtional options for the embedder.
   */
  embedderOptions?: z.infer<E>;
  /**
   * Document content key in the Qdrant payload.
   * Default is 'content'.
   */
  contentPayloadKey?: string;
  /**
   * Document metadata key in the Qdrant payload.
   * Default is 'metadata'.
   */
  metadataPayloadKey?: string;
  /**
   * Additional options when creating a collection.
   */
  collectionCreateOptions?: Schemas['CreateCollection'];
}

/**
 * Qdrant plugin that provides the Qdrant retriever and indexer
 */
export function qdrant<EmbedderCustomOptions extends z.ZodTypeAny>(
  params: QdrantPluginParams<EmbedderCustomOptions>[]
): PluginProvider {
  const plugin = genkitPlugin(
    'qdrant',
    async (params: QdrantPluginParams<EmbedderCustomOptions>[]) => ({
      retrievers: params.map((i) => qdrantRetriever(i)),
      indexers: params.map((i) => qdrantIndexer(i)),
    })
  );
  return plugin(params);
}

export default qdrant;

/**
 * Reference to a Qdrant retriever.
 */
export const qdrantRetrieverRef = (params: {
  collectionName: string;
  displayName?: string;
}) => {
  return retrieverRef({
    name: `qdrant/${params.collectionName}`,
    info: {
      label: params.displayName ?? `Qdrant - ${params.collectionName}`,
    },
    configSchema: QdrantRetrieverOptionsSchema.optional(),
  });
};

/**
 * Reference to a Qdrant indexer.
 */
export const qdrantIndexerRef = (params: {
  collectionName: string;
  displayName?: string;
}) => {
  return indexerRef({
    name: `qdrant/${params.collectionName}`,
    info: {
      label: params.displayName ?? `Qdrant - ${params.collectionName}`,
    },
    configSchema: QdrantIndexerOptionsSchema.optional(),
  });
};

/**
 * Configures a Qdrant vector store retriever.
 */
export function qdrantRetriever<EmbedderCustomOptions extends z.ZodTypeAny>(
  params: QdrantPluginParams<EmbedderCustomOptions>
) {
  const {
    embedder,
    collectionName,
    embedderOptions,
    clientParams,
    contentPayloadKey,
    metadataPayloadKey,
  } = params;

  const client = new QdrantClient(clientParams);

  const contentKey = contentPayloadKey ?? CONTENT_PAYLOAD_KEY;
  const metadataKey = metadataPayloadKey ?? METADATA_PAYLOAD_KEY;

  return defineRetriever(
    {
      name: `qdrant/${collectionName}`,
      configSchema: QdrantRetrieverOptionsSchema,
    },
    async (content, options) => {
      await ensureCollection(params, false);

      const queryEmbeddings = await embed({
        embedder,
        content,
        options: embedderOptions,
      });
      const results = await client.search(collectionName, {
        vector: queryEmbeddings,
        limit: options.k,
        filter: options.filter,
        with_payload: [contentKey, metadataKey],
        with_vector: false,
      });

      const documents = results.map((result) => {
        const content = result.payload?.[contentKey] ?? '';
        const metadata = result.payload?.[metadataKey] ?? {};
        return Document.fromText(content as string, metadata).toJSON();
      });

      return {
        documents,
      };
    }
  );
}

/**
 * Configures a Qdrant indexer.
 */
export function qdrantIndexer<EmbedderCustomOptions extends z.ZodTypeAny>(
  params: QdrantPluginParams<EmbedderCustomOptions>
) {
  const {
    embedder,
    collectionName,
    embedderOptions,
    clientParams,
    contentPayloadKey,
    metadataPayloadKey,
  } = params;

  const client = new QdrantClient(clientParams);

  const contentKey = contentPayloadKey ?? CONTENT_PAYLOAD_KEY;
  const metadataKey = metadataPayloadKey ?? METADATA_PAYLOAD_KEY;

  return defineIndexer(
    {
      name: `qdrant/${params.collectionName}`,
      configSchema: QdrantIndexerOptionsSchema,
    },
    async (docs) => {
      await ensureCollection(params);

      const embeddings = await Promise.all(
        docs.map((doc) =>
          embed({
            embedder,
            content: doc,
            options: embedderOptions,
          })
        )
      );

      await client.upsert(collectionName, {
        points: embeddings.map((embedding, index) => {
          return {
            id: uuidv5(JSON.stringify(docs[index]), uuidv5.URL),
            vector: embedding,
            payload: {
              [contentKey]: docs[index].text(),
              [metadataKey]: docs[index].metadata,
            },
          };
        }),
      });
    }
  );
}

/**
 * Helper function for creating a Qdrant collection.
 * If @param options is not provided, the default options will be used with Cosine similarity.
 */
export async function createQdrantCollection<
  EmbedderCustomOptions extends z.ZodTypeAny,
>(params: QdrantPluginParams<EmbedderCustomOptions>) {
  const { embedder, embedderOptions, clientParams, collectionName } = params;
  const client = new QdrantClient(clientParams);

  let collectionCreateOptions = params.collectionCreateOptions;

  if (!collectionCreateOptions) {
    const embeddings = await embed({
      embedder,
      content: 'SOME_TEXT',
      options: embedderOptions,
    });
    collectionCreateOptions = {
      vectors: {
        size: embeddings.length,
        distance: 'Cosine',
      },
    };
  }

  return await client.createCollection(collectionName, collectionCreateOptions);
}

/**
 * Helper function for deleting Qdrant collections.
 */
export async function deleteQdrantCollection(params: QdrantPluginParams) {
  const client = new QdrantClient(params.clientParams);
  return await client.deleteCollection(params.collectionName);
}

/**
 * Private helper for ensuring that a Qdrant collection exists.
 */
async function ensureCollection(
  params: QdrantPluginParams,
  createCollection = true
) {
  const { clientParams, collectionName } = params;
  const client = new QdrantClient(clientParams);

  if ((await client.collectionExists(collectionName)).exists) {
    return;
  }

  if (createCollection) {
    await createQdrantCollection(params);
  } else {
    throw new Error(
      `Collection ${collectionName} does not exist. Index some documents first.`
    );
  }
}
