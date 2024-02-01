import { EmbedderAction, embed } from '@google-genkit/ai/embedders';
import {
  CommonRetrieverOptionsSchema,
  retrieverFactory,
  TextDocumentSchema,
} from '@google-genkit/ai/retrievers';
import * as z from 'zod';
import { Pinecone, RecordMetadata } from '@pinecone-database/pinecone';

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

/**
 * Configures a Pinecone vector store retriever.
 */
export function configurePineconeRetriever<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  apiKey: string;
  indexId: string;
  textKey?: string;
  embedder: EmbedderAction<I, O, z.ZodString, EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}) {
  const { apiKey, indexId, embedder, embedderOptions } = { ...params };
  const textKey = params.textKey ?? TEXT_KEY;
  const pinecone = new Pinecone({ apiKey });
  const index = pinecone.index(indexId);

  return retrieverFactory(
    'pinecone',
    params.indexId,
    z.string(),
    TextDocumentSchema,
    PineconeRetrieverOptionsSchema,
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
