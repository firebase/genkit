import { EmbedderReference, embed } from '@google-genkit/ai/embedders';
import {
  CommonRetrieverOptionsSchema,
  TextDocumentSchema,
  retriever,
  retrieverRef,
} from '@google-genkit/ai/retrievers';
import { PluginProvider, genkitPlugin } from '@google-genkit/common/config';
import { Pinecone, RecordMetadata } from '@pinecone-database/pinecone';
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

const TEXT_KEY = '_content';

export const pineconeRef = (params: {
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

/**
 * Pinecone plugin that provides a pinecone retriever
 */
export function pinecone<EmbedderCustomOptions extends z.ZodTypeAny>(params: {
  indexId: string;
  embedder: EmbedderReference<EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}): PluginProvider {
  const plugin = genkitPlugin(
    'pinecone',
    (params: {
      indexId: string;
      apiKey?: string;
      textKey?: string;
      embedder: EmbedderReference<EmbedderCustomOptions>;
      embedderOptions?: z.infer<EmbedderCustomOptions>;
    }) => ({
      retrievers: [configurePineconeRetriever(params)],
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
  let apiKey;
  const { indexId, embedder, embedderOptions } = {
    ...params,
  };
  if (!params.apiKey) apiKey = process.env.PINECONE_API_KEY;
  if (!apiKey)
    throw new Error(
      'please pass in the API key or set PINECONE_API_KEY environment variable'
    );

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
