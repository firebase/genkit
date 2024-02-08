import { EmbedderAction, embed } from '@google-genkit/ai/embedders';
import {
  CommonRetrieverOptionsSchema,
  documentStoreFactory,
  TextDocumentSchema,
} from '@google-genkit/ai/retrievers';
import * as z from 'zod';
import { Pinecone, RecordMetadata } from '@pinecone-database/pinecone';
import { CreateIndexRequestSpec } from '@pinecone-database/pinecone/dist/pinecone-generated-ts-fetch';
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

/**
 * Configures a Pinecone document store.
 */
export async function configurePinecone<
  I extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  apiKey: string;
  indexId: string;
  textKey?: string;
  createIndexSpec?: CreateIndexRequestSpec; // Maybe just get the request?
  embedder: EmbedderAction<I, z.ZodString, EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}) {
  const { apiKey, indexId, embedder, createIndexSpec, embedderOptions } = {
    ...params,
  };
  const textKey = params.textKey ?? TEXT_KEY;
  const pinecone = new Pinecone({ apiKey });
  let index;
  if (createIndexSpec) {
    index = await pinecone.createIndex({
      name: indexId,
      dimension: embedder.getDimension(),
      spec: createIndexSpec,
      waitUntilReady: true /* always wait till ready*/,
    });
  } else {
    index = pinecone.index(indexId);
  }

  return documentStoreFactory({
    provider: 'pinecone',
    id: params.indexId,
    queryType: z.string(),
    documentType: TextDocumentSchema,
    retrieverOptionsType: PineconeRetrieverOptionsSchema,
    indexerOptionsType: PineconeIndexerOptionsSchema,
    retrieveFn: async (input, options) => {
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
    },
    indexFn: async (docs, options) => {
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
    },
  });
}
