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

const _LOCAL_FILESTORE = '__db_{INDEX_NAME}.json';

interface DbValue {
  doc: TextDocument;
  embedding: Array<number>;
}

function loadFilestore(indexName: string) {
  let existingData = {};
  const indexFileName = _LOCAL_FILESTORE.replace('{INDEX_NAME}', indexName);
  if (fs.existsSync(indexFileName)) {
    existingData = JSON.parse(fs.readFileSync(indexFileName).toString());
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

interface Params<EmbedderCustomOptions extends z.ZodTypeAny> {
  indexName: string;
  embedder: EmbedderReference<EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}

/**
 * Local file-based vectorstore plugin that provides retriever and indexer.
 *
 * NOT INTENDED FOR USE IN PRODUCTION
 */
export function devLocalVectorstore<EmbedderCustomOptions extends z.ZodTypeAny>(
  params: Params<EmbedderCustomOptions>[]
): PluginProvider {
  const plugin = genkitPlugin(
    'devLocalVectorstore',
    async (params: Params<EmbedderCustomOptions>[]) => ({
      retrievers: params.map((p) => configureDevLocalRetriever(p)),
      indexers: params.map((p) => configureDevLocalIndexer(p)),
    })
  );
  return plugin(params);
}

export default devLocalVectorstore;

/**
 * Local file-based vectorstore retriever reference
 */
export function devLocalRetrieverRef(indexName: string) {
  return retrieverRef({
    name: `devLocalVectorstore/${indexName}`,
    info: {
      label: `Local file-based Retriever`,
    },
    configSchema: CommonRetrieverOptionsSchema.optional(),
  });
}

/**
 * Local file-based indexer reference
 */
export function devLocalIndexerRef(indexName: string) {
  return indexerRef({
    name: `devLocalVectorstore/${indexName}`,
    info: {
      label: `Local file-based Indexer`,
      names: ['LFVS'],
    },
    configSchema: z.null().optional(),
  });
}

async function importDocumentsToLocalVectorstore<
  I extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  indexName: string;
  docs: Array<TextDocument>;
  embedder:
    | EmbedderReference<EmbedderCustomOptions>
    | EmbedderAction<I, z.ZodString, EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}) {
  const { docs, embedder, embedderOptions } = { ...params };
  const data = loadFilestore(params.indexName);

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
  fs.writeFileSync(
    _LOCAL_FILESTORE.replace('{INDEX_NAME}', params.indexName),
    JSON.stringify(data)
  );
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
 * Configures a local vectorstore retriever
 */
export function configureDevLocalRetriever<
  I extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  indexName: string;
  embedder:
    | EmbedderReference<EmbedderCustomOptions>
    | EmbedderAction<I, z.ZodString, EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}) {
  const { embedder, embedderOptions } = params;
  const vectorstore = retriever(
    {
      provider: 'devLocalVectorstore',
      retrieverId: `devLocalVectorstore/${params.indexName}`,
      queryType: z.string(),
      documentType: TextDocumentSchema,
      customOptionsType: CommonRetrieverOptionsSchema,
    },
    async (input, options) => {
      const db = loadFilestore(params.indexName);

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
  return vectorstore;
}

/**
 * Configures a local vectorstore indexer.
 */
export function configureDevLocalIndexer<
  I extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  indexName: string;
  embedder:
    | EmbedderReference<EmbedderCustomOptions>
    | EmbedderAction<I, z.ZodString, EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}) {
  const { embedder, embedderOptions } = params;
  const filestore = indexer(
    {
      provider: 'devLocalVectorstore',
      indexerId: `devLocalVectorstore/${params.indexName}`,
      documentType: TextDocumentSchema,
      customOptionsType: z.null().optional(),
    },
    async (docs) => {
      await importDocumentsToLocalVectorstore({
        indexName: params.indexName,
        docs,
        embedder: embedder,
        embedderOptions: embedderOptions,
      });
    }
  );
  return filestore;
}
