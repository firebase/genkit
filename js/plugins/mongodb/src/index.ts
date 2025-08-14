/**
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { Genkit } from 'genkit';
import { genkitPlugin, GenkitPlugin } from 'genkit/plugin';
import { closeConnections, getMongoClient } from './common/connection';
import { Connection, validateConnection } from './common/types';
import { defineIndexer } from './core/indexer';
import { defineRetriever } from './core/retriever';
import { defineCRUDTools } from './tools/crud';
import { defineSearchIndexTools } from './tools/search-indexes';

/**
 * Creates a MongoDB plugin for Genkit AI framework.
 *
 * This plugin provides MongoDB integration with text, vector, and hybrid search capabilities,
 * including document indexing, retrieval, CRUD operations, and search index management.
 *
 * @param connections - Array of MongoDB connection configurations
 * @returns A Genkit plugin that can be registered with the AI framework
 * @throws {Error} If no connections are provided or if initialization fails
 */
export function mongodb(connections: Array<Connection>): GenkitPlugin {
  if (!connections || connections.length === 0) {
    throw new Error('At least one Mongo connection must be provided');
  }

  return genkitPlugin('mongodb', async (ai: Genkit) => {
    try {
      for (const connection of connections) {
        const parsedConnection = validateConnection(connection);

        const client = await getMongoClient(
          parsedConnection.url,
          parsedConnection.mongoClientOptions
        );

        defineIndexer(ai, client, parsedConnection.indexer);
        defineRetriever(ai, client, parsedConnection.retriever);
        defineCRUDTools(ai, client, parsedConnection.crudTools);
        defineSearchIndexTools(ai, client, parsedConnection.searchIndexTools);
      }
    } catch (error) {
      await closeConnections();
      throw new Error(
        `Mongo plugin initialization failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    }
  });
}

export type {
  Connection as MongoConnection,
  EmbedderOptions as MongoEmbedderOptions,
  HybridSearchOptions as MongoHybridSearchOptions,
  IndexerOptions as MongoIndexerOptions,
  InputCreate as MongoInputCreate,
  InputDelete as MongoInputDelete,
  InputRead as MongoInputRead,
  InputSearchIndexCreate as MongoInputSearchIndexCreate,
  InputSearchIndexDrop as MongoInputSearchIndexDrop,
  InputSearchIndexList as MongoInputSearchIndexList,
  InputUpdate as MongoInputUpdate,
  RetrieverOptions as MongoRetrieverOptions,
  RetryOptions as MongoRetryOptions,
  TextSearchOptions as MongoTextSearchOptions,
  VectorSearchOptions as MongoVectorSearchOptions,
} from './common/types';

export { mongoIndexerRef } from './core/indexer';
export { mongoRetrieverRef } from './core/retriever';
export { mongoCrudToolsRefArray } from './tools/crud';
export { mongoSearchIndexToolsRefArray } from './tools/search-indexes';

export default mongodb;
