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

import {
  CreateIndexOptions,
  Pinecone,
  PineconeConfiguration,
  RecordMetadata,
} from '@pinecone-database/pinecone';
import { genkitPlugin, PluginProvider, z } from 'genkit';
import { embed, EmbedderArgument } from 'genkit/embedder';
import {
  CommonRetrieverOptionsSchema,
  defineIndexer,
  defineRetriever,
  Document,
  indexerRef,
  retrieverRef,
} from 'genkit/retriever';
import { Md5 } from 'ts-md5';

const SparseVectorSchema = z
  .object({
    indices: z.number().array(),
    values: z.number().array(),
  })
  .refine(
    (input) => {
      return input.indices.length === input.values.length;
    },
    {
      message: 'Indices and values must be of the same length',
    }
  );

const PineconeRetrieverOptionsSchema = CommonRetrieverOptionsSchema.extend({
  k: z.number().max(1000),
  namespace: z.string().optional(),
  filter: z.record(z.string(), z.any()).optional(),
  // includeValues is always false
  // includeMetadata is always true
  sparseVector: SparseVectorSchema.optional(),
});

const PineconeIndexerOptionsSchema = z.object({
  namespace: z.string().optional(),
});

const TEXT_KEY = '_content';

export const pineconeRetrieverRef = (params: {
  indexId: string;
  displayName?: string;
}) => {
  return retrieverRef({
    name: `pinecone/${params.indexId}`,
    info: {
      label: params.displayName ?? `Pinecone - ${params.indexId}`,
    },
    configSchema: PineconeRetrieverOptionsSchema,
  });
};

export const pineconeIndexerRef = (params: {
  indexId: string;
  displayName?: string;
}) => {
  return indexerRef({
    name: `pinecone/${params.indexId}`,
    info: {
      label: params.displayName ?? `Pinecone - ${params.indexId}`,
    },
    configSchema: PineconeIndexerOptionsSchema.optional(),
  });
};

/**
 * Pinecone plugin that provides a pinecone retriever and indexer
 */
export function pinecone<EmbedderCustomOptions extends z.ZodTypeAny>(
  params: {
    clientParams?: PineconeConfiguration;
    indexId: string;
    embedder: EmbedderArgument<EmbedderCustomOptions>;
    embedderOptions?: z.infer<EmbedderCustomOptions>;
  }[]
): PluginProvider {
  const plugin = genkitPlugin(
    'pinecone',
    async (
      params: {
        clientParams?: PineconeConfiguration;
        indexId: string;
        textKey?: string;
        embedder: EmbedderArgument<EmbedderCustomOptions>;
        embedderOptions?: z.infer<EmbedderCustomOptions>;
      }[]
    ) => ({
      retrievers: params.map((i) => configurePineconeRetriever(i)),
      indexers: params.map((i) => configurePineconeIndexer(i)),
    })
  );
  return plugin(params);
}

export default pinecone;

/**
 * Configures a Pinecone retriever.
 */
export function configurePineconeRetriever<
  EmbedderCustomOptions extends z.ZodTypeAny,
>(params: {
  indexId: string;
  clientParams?: PineconeConfiguration;
  textKey?: string;
  embedder: EmbedderArgument<EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}) {
  const { indexId, embedder, embedderOptions } = {
    ...params,
  };
  const pineconeConfig = params.clientParams ?? getDefaultConfig();
  const textKey = params.textKey ?? TEXT_KEY;
  const pinecone = new Pinecone(pineconeConfig);
  const index = pinecone.index(indexId);

  return defineRetriever(
    {
      name: `pinecone/${params.indexId}`,
      configSchema: PineconeRetrieverOptionsSchema,
    },
    async (content, options) => {
      const queryEmbeddings = await embed({
        embedder,
        content,
        options: embedderOptions,
      });
      const scopedIndex = !!options.namespace
        ? index.namespace(options.namespace)
        : index;
      const response = await scopedIndex.query({
        topK: options.k,
        vector: queryEmbeddings,
        includeValues: false,
        includeMetadata: true,
      });
      return {
        documents: response.matches
          .map((m) => m.metadata)
          .filter((m): m is RecordMetadata => !!m)
          .map((m) => {
            const metadata = m;
            const content = metadata[textKey] as string;
            delete metadata[textKey];
            return Document.fromText(content, metadata).toJSON();
          }),
      };
    }
  );
}

/**
 * Configures a Pinecone indexer.
 */
export function configurePineconeIndexer<
  EmbedderCustomOptions extends z.ZodTypeAny,
>(params: {
  indexId: string;
  clientParams?: PineconeConfiguration;
  textKey?: string;
  embedder: EmbedderArgument<EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}) {
  const { indexId, embedder, embedderOptions } = {
    ...params,
  };
  const pineconeConfig = params.clientParams ?? getDefaultConfig();
  const textKey = params.textKey ?? TEXT_KEY;
  const pinecone = new Pinecone(pineconeConfig);
  const index = pinecone.index(indexId);

  return defineIndexer(
    {
      name: `pinecone/${params.indexId}`,
      configSchema: PineconeIndexerOptionsSchema.optional(),
    },
    async (docs, options) => {
      const scopedIndex = !!options?.namespace
        ? index.namespace(options.namespace)
        : index;

      const embeddings = await Promise.all(
        docs.map((doc) =>
          embed({
            embedder,
            content: doc,
            options: embedderOptions,
          })
        )
      );
      await scopedIndex.upsert(
        embeddings.map((value, i) => {
          const metadata: RecordMetadata = {
            ...docs[i].metadata,
          };

          metadata[textKey] = docs[i].text();
          const id = Md5.hashStr(JSON.stringify(docs[i]));
          return {
            id,
            values: value,
            metadata,
          };
        })
      );
    }
  );
}

/**
 * Helper function for creating a Pinecone index.
 */
export async function createPineconeIndex(params: {
  clientParams?: PineconeConfiguration;
  options: CreateIndexOptions;
}) {
  const pineconeConfig = params.clientParams ?? getDefaultConfig();
  const pinecone = new Pinecone(pineconeConfig);
  return await pinecone.createIndex(params.options);
}

/**
 * Helper function to describe a Pinecone index. Use it to check if a newly created index is ready for use.
 */
export async function describePineconeIndex(params: {
  clientParams?: PineconeConfiguration;
  name: string;
}) {
  const pineconeConfig = params.clientParams ?? getDefaultConfig();
  const pinecone = new Pinecone(pineconeConfig);
  return await pinecone.describeIndex(params.name);
}

/**
 * Helper function for deleting Chroma collections.
 */
export async function deletePineconeIndex(params: {
  clientParams?: PineconeConfiguration;
  name: string;
}) {
  const pineconeConfig = params.clientParams ?? getDefaultConfig();
  const pinecone = new Pinecone(pineconeConfig);
  return await pinecone.deleteIndex(params.name);
}

function getDefaultConfig() {
  const maybeApiKey = process.env.PINECONE_API_KEY;
  if (!maybeApiKey)
    throw new Error(
      'Please pass in the API key or set PINECONE_API_KEY environment variable.\n' +
        'For more details see https://firebase.google.com/docs/genkit/plugins/pinecone'
    );
  return { apiKey: maybeApiKey } as PineconeConfiguration;
}
