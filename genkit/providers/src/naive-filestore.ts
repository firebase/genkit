import {
  EmbedderAction,
  EmbedderReference,
  embed,
} from '@google-genkit/ai/embedders';
import {
  CommonRetrieverOptionsSchema,
  TextDocumentSchema,
  type TextDocument,
  retriever,
  indexer,
  indexerRef,
  retrieverRef,
} from '@google-genkit/ai/retrievers';
import { PluginProvider, genkitPlugin } from '@google-genkit/common/config';
import similarity from 'compute-cosine-similarity';
import * as fs from 'fs';
import { Md5 } from 'ts-md5';
import * as z from 'zod';

const _LOCAL_FILESTORE = '__db.json';

interface DbValue {
  doc: TextDocument;
  embedding: Array<number>;
}

function loadFilestore() {
  let existingData = {};
  if (fs.existsSync(_LOCAL_FILESTORE)) {
    existingData = JSON.parse(fs.readFileSync(_LOCAL_FILESTORE).toString());
  }
  return existingData;
}

function addDocument(
  doc: TextDocument,
  contents: Record<string, DbValue>,
  embedding: Array<number>
) {
  const id = Md5.hashStr(JSON.stringify(doc));
  if (!(id in contents)) {
    // Only inlcude if doc is new
    contents[id] = { doc, embedding };
  } else {
    console.debug(`Skipping ${id} since it is already present`);
  }
}

/**
 * Naive filestore plugin that provides retriever and indexer
 */
export function naiveFilestore<
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  embedder: EmbedderReference<EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}): PluginProvider {
  const plugin = genkitPlugin(
    'naiveFilestore',
    (params: {
      embedder: EmbedderReference<EmbedderCustomOptions>;
      embedderOptions?: z.infer<EmbedderCustomOptions>;
    }) => ({
      retrievers: [configureNaiveFilestoreRetriever(params)],
      indexers: [configureNaiveFilestoreIndexer(params)],
    })
  );
  return plugin(params);
}

/**
 * Naive filestore retriever reference
 */
export const naiveFilestoreRetrieverRef = retrieverRef({
  name: `naiveFilestore/singleton`,
  info: {
    label: `Naive Filestore Retriever`,
    names: ['NFS'],
  },
  configSchema: CommonRetrieverOptionsSchema.optional(),
});

/**
 * Naive filestore indexer reference
 */
export const naiveFilestoreIndexerRef = indexerRef({
  name: `naiveFilestore/singleton`,
  info: {
    label: `Naive Filestore Indexer`,
    names: ['NFS'],
  },
  configSchema: z.null().optional(),
});

async function importDocumentsToNaiveFilestore<
  I extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  docs: Array<TextDocument>;
  embedder:
    | EmbedderReference<EmbedderCustomOptions>
    | EmbedderAction<I, z.ZodString, EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}) {
  const { docs, embedder, embedderOptions } = { ...params };
  const data = loadFilestore();

  await Promise.all(
    docs.map(async (doc) => {
      const embedding = await embed({
        embedder,
        input: doc.content,
        options: embedderOptions,
      });
      addDocument(doc, data, embedding);
    })
  );
  // Update the file
  fs.writeFileSync(_LOCAL_FILESTORE, JSON.stringify(data));
}

async function getClosestDocuments<
  I extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  queryEmbeddings: Array<number>;
  db: Record<string, DbValue>;
  k: number;
}) {
  const scoredDocs: { score: number; doc: TextDocument }[] = [];
  // Very dumb way to check for similar docs.
  for (const [, value] of Object.entries(params.db)) {
    const thisEmbedding = value.embedding;
    const score = similarity(params.queryEmbeddings, thisEmbedding) ?? 0;
    scoredDocs.push({
      score,
      doc: value.doc,
    });
  }

  scoredDocs.sort((a, b) => (a.score > b.score ? -1 : 1));
  return scoredDocs.slice(0, params.k).map((o) => o.doc);
}

/**
 * Configures a naive filestore retriever
 */
export function configureNaiveFilestoreRetriever<
  I extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  embedder:
    | EmbedderReference<EmbedderCustomOptions>
    | EmbedderAction<I, z.ZodString, EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}) {
  const { embedder, embedderOptions } = params;
  const naiveFilestore = retriever(
    {
      provider: 'naiveFilestore',
      retrieverId: 'naiveFilestore/singleton',
      queryType: z.string(),
      documentType: TextDocumentSchema,
      customOptionsType: CommonRetrieverOptionsSchema,
    },
    async (input, options) => {
      const db = loadFilestore();

      const queryEmbeddings = await embed({
        embedder,
        input,
        options: embedderOptions,
      });
      return getClosestDocuments({
        k: options?.k ?? 3,
        queryEmbeddings,
        db,
      });
    }
  );
  return naiveFilestore;
}

/**
 * Configures a naive filestore indexer.
 */
export function configureNaiveFilestoreIndexer<
  I extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  embedder:
    | EmbedderReference<EmbedderCustomOptions>
    | EmbedderAction<I, z.ZodString, EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}) {
  const { embedder, embedderOptions } = params;
  const naiveFilestore = indexer(
    {
      provider: 'naiveFilestore',
      indexerId: 'naiveFilestore/singleton',
      documentType: TextDocumentSchema,
      customOptionsType: z.null().optional(),
    },
    async (docs) => {
      await importDocumentsToNaiveFilestore({
        docs,
        embedder: embedder,
        embedderOptions: embedderOptions,
      });
    }
  );
  return naiveFilestore;
}
