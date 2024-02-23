import { embed } from '@google-genkit/ai/embedders';
import {
  CommonRetrieverOptionsSchema,
  retriever,
  retrieverRef,
  TextDocumentSchema,
} from '@google-genkit/ai/retrievers';
import { ChromaClient, IncludeEnum, Where, WhereDocument } from 'chromadb';
import * as z from 'zod';
export { IncludeEnum };
import { genkitPlugin, PluginProvider } from '@google-genkit/common/config';
import { EmbedderReference } from '@google-genkit/ai/embedders';

const WhereSchema: z.ZodType<Where> = z.any();
const WhereDocumentSchema: z.ZodType<WhereDocument> = z.any();

const ChromaRetrieverOptionsSchema = CommonRetrieverOptionsSchema.extend({
  include: z.array(z.nativeEnum(IncludeEnum)).optional(),
  where: WhereSchema.optional(),
  whereDocument: WhereDocumentSchema.optional(),
});

/**
 * Chroma plugin that provides the Chroma retriever
 */
export function chroma<EmbedderCustomOptions extends z.ZodTypeAny>(params: {
  collectionName: string;
  embedder: EmbedderReference<EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}): PluginProvider {
  const plugin = genkitPlugin(
    'chroma',
    (params: {
      collectionName: string;
      embedder: EmbedderReference<EmbedderCustomOptions>;
      embedderOptions?: z.infer<EmbedderCustomOptions>;
    }) => ({
      retrievers: [chromaDbRetriever(params)],
    })
  );
  return plugin(params);
}

export const chromaRef = (params: {
  collectionName: string;
  displayName?: string;
}) => {
  const displayName = params.displayName ?? params.collectionName;
  return retrieverRef({
    name: `chroma/${params.collectionName}`,
    info: {
      label: `Chroma DB - ${displayName}`,
      names: [displayName],
    },
    configSchema: ChromaRetrieverOptionsSchema.optional(),
  });
};

/**
 * Configures a Chroma vector store retriever.
 */
export function chromaDbRetriever<
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  collectionName: string;
  embedder: EmbedderReference<EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}) {
  const { embedder, collectionName, embedderOptions } = params;
  return retriever(
    {
      provider: 'chroma',
      retrieverId: `chroma/${collectionName}`,
      embedderInfo: embedder.info,
      queryType: z.string(),
      documentType: TextDocumentSchema,
      customOptionsType: ChromaRetrieverOptionsSchema,
    },
    async (input, options) => {
      const client = new ChromaClient();
      const collection = await client.getCollection({
        name: collectionName,
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
}
