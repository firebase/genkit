import { embed } from '@google-genkit/ai/embedders';
import {
  CommonRetrieverOptionsSchema,
  indexerRef,
  retriever,
  retrieverRef,
  TextDocumentSchema,
} from '@google-genkit/ai/retrievers';
import {
  ChromaClient,
  CollectionMetadata,
  IEmbeddingFunction,
  IncludeEnum,
  Metadata,
  Where,
  WhereDocument,
} from 'chromadb';
import * as z from 'zod';
import { genkitPlugin, PluginProvider } from '@google-genkit/common/config';
import { EmbedderReference } from '@google-genkit/ai/embedders';
import { indexer } from '@google-genkit/ai/retrievers';
import { Md5 } from 'ts-md5';

export { IncludeEnum };

const WhereSchema: z.ZodType<Where> = z.any();
const WhereDocumentSchema: z.ZodType<WhereDocument> = z.any();

const ChromaRetrieverOptionsSchema = CommonRetrieverOptionsSchema.extend({
  include: z.array(z.nativeEnum(IncludeEnum)).optional(),
  where: WhereSchema.optional(),
  whereDocument: WhereDocumentSchema.optional(),
});

export const ChromaIndexerOptionsSchema = z.null().optional();

/**
 * Chroma plugin that provides the Chroma retriever and indexer
 */
export function chroma<EmbedderCustomOptions extends z.ZodTypeAny>(params: {
  collectionName: string;
  embedder: EmbedderReference<EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}): PluginProvider {
  const plugin = genkitPlugin(
    'chroma',
    async (params: {
      collectionName: string;
      embedder: EmbedderReference<EmbedderCustomOptions>;
      embedderOptions?: z.infer<EmbedderCustomOptions>;
    }) => ({
      retrievers: [chromaRetriever(params)],
      indexers: [chromaIndexer(params)],
    })
  );
  return plugin(params);
}

export const chromaRetrieverRef = (params: {
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

export const chromaIndexerRef = (params: {
  collectionName: string;
  displayName?: string;
}) => {
  const displayName = params.displayName ?? params.collectionName;
  return indexerRef({
    name: `chroma/${params.collectionName}`,
    info: {
      label: `Chroma DB - ${displayName}`,
      names: [displayName],
    },
    configSchema: ChromaIndexerOptionsSchema.optional(),
  });
};

/**
 * Configures a Chroma vector store retriever.
 */
export function chromaRetriever<
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

/**
 * Configures a Chroma indexer.
 */
export function chromaIndexer<
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  collectionName: string;
  textKey?: string;
  embedder: EmbedderReference<EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}) {
  const { collectionName, embedder, embedderOptions } = {
    ...params,
  };
  const client = new ChromaClient();

  return indexer(
    {
      provider: 'chroma',
      indexerId: `chroma/${params.collectionName}`,
      documentType: TextDocumentSchema,
      customOptionsType: ChromaIndexerOptionsSchema,
    },
    async (docs) => {
      const collection = await client.getCollection({
        name: collectionName,
      });

      const embeddings = await Promise.all(
        docs.map((doc) =>
          embed({
            embedder,
            input: doc.content,
            options: embedderOptions,
          })
        )
      );
      const entries = embeddings.map((value, i) => {
        const metadata: Metadata = {
          ...docs[i].metadata,
        };

        const id = Md5.hashStr(JSON.stringify(docs[i]));
        return {
          id,
          value,
          document: docs[i].content,
          metadata,
        };
      });
      await collection.add({
        ids: entries.map((e) => e.id),
        embeddings: entries.map((e) => e.value),
        metadatas: entries.map((e) => e.metadata),
        documents: entries.map((e) => e.document),
      });
    }
  );
}

/**
 * Helper function for creating Chroma collections.
 */
export async function createChromaCollection<
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  name: string;
  metadata?: CollectionMetadata;
  embedder?: EmbedderReference<EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}) {
  let chromaEmbedder: IEmbeddingFunction | undefined = undefined;
  const embedder = params.embedder;
  if (!!embedder) {
    chromaEmbedder = {
      generate(texts: string[]) {
        return Promise.all(
          texts.map((text) =>
            embed({
              embedder,
              input: text,
              options: params.embedderOptions,
            })
          )
        );
      },
    };
  }
  const client = new ChromaClient();
  return await client.createCollection({
    ...params,
    embeddingFunction: chromaEmbedder,
  });
}

/**
 * Helper function for deleting Chroma collections.
 */
export async function deleteChromaCollection(params: { name: string }) {
  const client = new ChromaClient();
  return await client.deleteCollection({
    ...params,
  });
}
