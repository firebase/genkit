import {
  CommonRetrieverOptionsSchema,
  retrieverFactory,
  TextDocumentSchema,
} from '@google-genkit/ai/retrievers';
import * as z from 'zod';
import { ChromaClient, IncludeEnum, Where, WhereDocument } from 'chromadb';
import { embed, EmbedderAction } from '@google-genkit/ai/embedders';
export { IncludeEnum };

const WhereSchema: z.ZodType<Where> = z.any();
const WhereDocumentSchema: z.ZodType<WhereDocument> = z.any();

const ChromaRetrieverOptionsSchema = CommonRetrieverOptionsSchema.extend({
  include: z.array(z.nativeEnum(IncludeEnum)).optional(),
  where: WhereSchema.optional(),
  whereDocument: WhereDocumentSchema.optional(),
}).optional();

/**
 * Configures a Chroma vector store retriever.
 */
export function configureChromaRetriever<
  I extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  collectionName: string;
  embedder: EmbedderAction<I, z.ZodString, EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}) {
  const { embedder, collectionName, embedderOptions } = params;
  const chromaRetriever = retrieverFactory(
    {
      provider: 'chroma',
      retrieverId: collectionName,
      queryType: z.string(),
      documentType: TextDocumentSchema,
      customOptionsType: ChromaRetrieverOptionsSchema,
    },
    async (input, options) => {
      const client = new ChromaClient();
      const collection = await client.getOrCreateCollection({
        name: collectionName,
        metadata: {
          description: 'My test collection',
        },
      });

      const queryEmbeddings = await embed({
        embedder,
        input,
        options: embedderOptions,
      });
      const results = await collection.query({
        nResults: options?.k,
        include: options?.include,
        where: options?.where,
        whereDocument: options?.whereDocument,
        queryEmbeddings,
      });

      const documents = results.documents[0];
      const metadatas = results.metadatas[0];

      const combined = documents
        .map((d, i) => {
          if (d !== null) {
            return {
              document: d,
              metadata: metadatas[i] ?? undefined,
            };
          }
          return undefined;
        })
        .filter(
          (r): r is { document: string; metadata: Record<string, any> } => !!r
        );

      return combined.map((result) => {
        return {
          content: result.document,
          metadata: result.metadata,
        };
      });
    }
  );
  return chromaRetriever;
}
