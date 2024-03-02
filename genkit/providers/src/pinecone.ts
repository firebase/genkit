import { EmbedderReference, embed } from '@google-genkit/ai/embedders';
import { indexer, indexerRef } from '@google-genkit/ai/retrievers';
import {
  CommonRetrieverOptionsSchema,
  TextDocumentSchema,
  retriever,
  retrieverRef,
} from '@google-genkit/ai/retrievers';
import { PluginProvider, genkitPlugin } from '@google-genkit/common/config';
import {
  CreateIndexOptions,
  Pinecone,
  RecordMetadata,
} from '@pinecone-database/pinecone';
import { Md5 } from 'ts-md5';
import * as z from 'zod';

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
  const displayName = params.displayName ?? params.indexId;
  return retrieverRef({
    name: `pinecone/${params.indexId}`,
    info: {
      label: `Pinecone - ${displayName}`,
      names: [displayName],
    },
    configSchema: PineconeRetrieverOptionsSchema.optional(),
  });
};

export const pineconeIndexerRef = (params: {
  indexId: string;
  displayName?: string;
}) => {
  const displayName = params.displayName ?? params.indexId;
  return indexerRef({
    name: `pinecone/${params.indexId}`,
    info: {
      label: `Pinecone - ${displayName}`,
      names: [displayName],
    },
    configSchema: PineconeIndexerOptionsSchema.optional(),
  });
};

/**
 * Pinecone plugin that provides a pinecone retriever and indexer
 */
export function pinecone<EmbedderCustomOptions extends z.ZodTypeAny>(
  params: {
    indexId: string;
    embedder: EmbedderReference<EmbedderCustomOptions>;
    embedderOptions?: z.infer<EmbedderCustomOptions>;
  }[]
): PluginProvider {
  const plugin = genkitPlugin(
    'pinecone',
    (
      params: {
        indexId: string;
        apiKey?: string;
        textKey?: string;
        embedder: EmbedderReference<EmbedderCustomOptions>;
        embedderOptions?: z.infer<EmbedderCustomOptions>;
      }[]
    ) => ({
      retrievers: params.map((i) => configurePineconeRetriever(i)),
      indexers: params.map((i) => configurePineconeIndexer(i)),
    })
  );
  return plugin(params);
}

/**
 * Configures a Pinecone retriever.
 */
export function configurePineconeRetriever<
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  indexId: string;
  apiKey?: string;
  textKey?: string;
  embedder: EmbedderReference<EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}) {
  const { indexId, embedder, embedderOptions } = {
    ...params,
  };
  const apiKey = getApiKey(params.apiKey);
  const textKey = params.textKey ?? TEXT_KEY;
  const pinecone = new Pinecone({ apiKey });
  const index = pinecone.index(indexId);

  return retriever(
    {
      provider: 'pinecone',
      retrieverId: `pinecone/${params.indexId}`,
      embedderInfo: embedder.info,
      queryType: z.string(),
      documentType: TextDocumentSchema,
      customOptionsType: PineconeRetrieverOptionsSchema,
    },
    async (input, options) => {
      const queryEmbeddings = await embed({
        embedder,
        input,
        options: embedderOptions,
      });
      const scopedIndex = options.namespace
        ? index.namespace(options.namespace)
        : index;
      const response = await scopedIndex.query({
        topK: options.k,
        vector: queryEmbeddings,
        includeValues: false,
        includeMetadata: true,
      });
      return response.matches
        .map((m) => m.metadata)
        .filter((m): m is RecordMetadata => !!m)
        .map((m) => {
          const metadata = m;
          const content = metadata[textKey] as string;
          delete metadata[textKey];
          return {
            content,
            metadata,
          };
        });
    }
  );
}

/**
 * Configures a Pinecone indexer.
 */
export function configurePineconeIndexer<
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  indexId: string;
  apiKey?: string;
  textKey?: string;
  embedder: EmbedderReference<EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}) {
  const { indexId, embedder, embedderOptions } = {
    ...params,
  };
  const apiKey = getApiKey(params.apiKey);
  const textKey = params.textKey ?? TEXT_KEY;
  const pinecone = new Pinecone({ apiKey });
  const index = pinecone.index(indexId);

  return indexer(
    {
      provider: 'pinecone',
      indexerId: `pinecone/${params.indexId}`,
      documentType: TextDocumentSchema,
      customOptionsType: PineconeIndexerOptionsSchema,
    },
    async (docs, options) => {
      const scopedIndex = options.namespace
        ? index.namespace(options.namespace)
        : index;

      const embeddings = await Promise.all(
        docs.map((doc) =>
          embed({
            embedder,
            input: doc.content,
            options: embedderOptions,
          })
        )
      );
      await scopedIndex.upsert(
        embeddings.map((values, i) => {
          const metadata: RecordMetadata = {
            ...docs[i].metadata,
          };

          metadata[textKey] = docs[i].content;
          const id = Md5.hashStr(JSON.stringify(docs[i]));
          return {
            id,
            values,
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
export async function createPineconeIndex<
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: { apiKey?: string; options: CreateIndexOptions }) {
  const apiKey = getApiKey(params.apiKey);
  const pinecone = new Pinecone({ apiKey });
  return await pinecone.createIndex(params.options);
}

/**
 * Helper function to describe a Pinecone index. Use it to check if a newly created index is ready for use.
 */
export async function describePineconeIndex<
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: { apiKey?: string; name: string }) {
  const apiKey = getApiKey(params.apiKey);
  const pinecone = new Pinecone({ apiKey });
  return await pinecone.describeIndex(params.name);
}

/**
 * Helper function for deleting Chroma collections.
 */
export async function deletePineconeIndex(params: {
  apiKey?: string;
  name: string;
}) {
  const apiKey = getApiKey(params.apiKey);
  const pinecone = new Pinecone({ apiKey });
  return await pinecone.deleteIndex(params.name);
}

function getApiKey(apiKey?: string) {
  let maybeApiKey;
  if (!apiKey) maybeApiKey = process.env.PINECONE_API_KEY;
  if (!maybeApiKey)
    throw new Error(
      'please pass in the API key or set PINECONE_API_KEY environment variable'
    );
  return maybeApiKey;
}
