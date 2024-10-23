import * as z from 'zod';
import { Neo4jGraphConfig } from './types';
import { Neo4jVectorStore } from './vector';
import { EmbedderArgument } from '@genkit-ai/ai/embedder';
import { defineIndexer } from '@genkit-ai/ai/retriever';
import { Document } from '@genkit-ai/ai/retriever';

/**
 * Configures a Neo4j indexer.
 */
export function configureNeo4jIndexer<EmbedderOptions extends z.ZodTypeAny>(params: {
  clientParams: Neo4jGraphConfig;
  indexName: string;
  embedder: EmbedderArgument<EmbedderOptions>;
  embedderOptions?: z.infer<EmbedderOptions>;
}) {
  const { indexName, embedder, embedderOptions } = {
    ...params,
  };
  const neo4jConfig = params.clientParams;

  return defineIndexer(
    {
      name: `neo4j/${params.indexName}`,
    },
    async (docs: Document[]) => {
      await Neo4jVectorStore.fromDocuments(
        docs, embedder, embedderOptions, neo4jConfig);
    }
  );
}

/**
 * Create a Neo4j Vector index.
 */
export async function createNeo4jVectorIndex(params: {
  clientParams: Neo4jGraphConfig;
}) {
  return await Neo4jVectorStore.createIndex(params.clientParams);
}

/**
 * List Neo4j Vector Indexes
 */
export async function describeNeo4jVectorIndex(params: {
  clientParams: Neo4jGraphConfig;
}) {
  return await Neo4jVectorStore.getIndex(params.clientParams);
}

/**
 * Delete Neo4j Vector Index
 */
export async function deleteNeo4jVectorIndex(params: {
  clientParams: Neo4jGraphConfig;
}) {
  return await Neo4jVectorStore.deleteIndex(params.clientParams);
}