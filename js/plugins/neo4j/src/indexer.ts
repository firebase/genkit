import * as z from 'zod';
import { Neo4jGraphConfig } from './types';
import { Neo4jVectorStore } from './vector';
import { defineIndexer } from '@genkit-ai/ai/retriever';
import { Document } from '@genkit-ai/ai/retriever';
import { Neo4jIndexerOptionsSchema } from '.';
import { EmbedderArgument } from '@genkit-ai/ai/embedder';

/**
 * Configures a Neo4j indexer.
 */
export function configureNeo4jIndexer(params: {
  neo4jStore: Neo4jVectorStore;
  indexId: string;
}) {
  const { indexId } = {
    ...params,
  };
  const neo4jStore = params.neo4jStore;

  return defineIndexer(
    {
      name: `neo4j/${params.indexId}`,
      configSchema: Neo4jIndexerOptionsSchema
    },
    async (docs: Document[], options) => {
      await neo4jStore.fromDocuments(
        docs, options.vectorConfig);
    }
  );
}

type EmbedderCustomOptions = z.ZodTypeAny;

/**
 * Create a Neo4j Vector index.
 */
export async function createNeo4jVectorIndex(params: {
  clientParams: Neo4jGraphConfig,
  embedder: EmbedderArgument<EmbedderCustomOptions>;
}) {
  const store = await Neo4jVectorStore.create(
    params.clientParams, params.embedder)
  return await store.createIndex();
}

/**
 * List Neo4j Vector Indexes
 */
export async function describeNeo4jVectorIndex(params: {
  clientParams: Neo4jGraphConfig;
}) {
  const store = await Neo4jVectorStore.create(params.clientParams)
  return await store.getIndex();
}

/**
 * Delete Neo4j Vector Index
 */
export async function deleteNeo4jVectorIndex(params: {
  clientParams: Neo4jGraphConfig;
}) {
  const store = await Neo4jVectorStore.create(params.clientParams)
  return await store.deleteIndex();
}
