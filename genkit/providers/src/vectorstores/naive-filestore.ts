import {
  CommonRetrieverOptionsSchema,
  CommonIndexerOptionsSchema,
  TextDocumentSchema,
  type TextDocument,
  documentStoreFactory,
} from '@google-genkit/ai/retrievers';
import * as z from 'zod';
import { embed, EmbedderAction } from '@google-genkit/ai/embedders';
import { Md5 } from 'ts-md5';
import * as fs from 'fs';
const similarity = require('compute-cosine-similarity');

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

async function importDocumentsToNaiveFilestore<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  docs: Array<TextDocument>;
  embedder: EmbedderAction<I, O, z.ZodString, EmbedderCustomOptions>;
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
  O extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  embedder: EmbedderAction<I, O, z.ZodString, EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
  queryEmbeddings: Array<number>;
  db: Record<string, DbValue>;
  k: number;
}) {
  const scoredDocs: { score: number; doc: TextDocument }[] = [];
  // Very dumb way to check for similar docs.
  for (const [key, value] of Object.entries(params.db)) {
    const thisEmbedding = value.embedding;
    const score = similarity(params.queryEmbeddings, thisEmbedding);
    scoredDocs.push({
      score,
      doc: value.doc,
    });
  }

  scoredDocs.sort((a, b) => (a.score > b.score ? -1 : 1));
  return scoredDocs.slice(0, params.k).map((o) => o.doc);
}

/**
 * Configures a naive filestore datastore.
 */
export function configureNaiveFilestore<
  I extends z.ZodTypeAny,
  O extends z.ZodTypeAny,
  EmbedderCustomOptions extends z.ZodTypeAny
>(params: {
  embedder: EmbedderAction<I, O, z.ZodString, EmbedderCustomOptions>;
  embedderOptions?: z.infer<EmbedderCustomOptions>;
}) {
  const { embedder, embedderOptions } = params;
  const naiveFilestore = documentStoreFactory({
    provider: 'naiveFilestore',
    id: 'singleton',
    inputType: z.string(),
    documentType: TextDocumentSchema,
    retrieverOptionsType: CommonRetrieverOptionsSchema,
    indexerOptionsType: CommonIndexerOptionsSchema.optional(),
    retrieveFn: async (input, options) => {
      const db = loadFilestore();

      const queryEmbeddings = await embed({
        embedder,
        input,
        options: embedderOptions,
      });
      return getClosestDocuments({
        embedder,
        embedderOptions,
        k: options?.k ?? 3,
        queryEmbeddings,
        db,
      });
    },
    indexFn: async (docs) => {
      await importDocumentsToNaiveFilestore({
        docs: docs as TextDocument[],
        embedder: embedder,
        embedderOptions: embedderOptions,
      });
    }
  });
  return naiveFilestore;
}
