/**
 * Copyright 2025 Google LLC
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

import {
  CommonRetrieverOptionsSchema,
  Document,
  indexerRef,
  retrieverRef,
} from 'genkit/retriever';

import { Genkit, z } from 'genkit';
import { GenkitPlugin, genkitPlugin } from 'genkit/plugin';
import { EmbedderArgument } from 'genkit/embedder';
import { BaseIndex, DEFAULT_INDEX_NAME_SUFFIX, DistanceStrategy, ExactNearestNeighbor, QueryOptions } from "./indexes";
import { PostgresEngine } from './engine';


const PostgresRetrieverOptionsSchema = CommonRetrieverOptionsSchema.extend({
  k: z.number().max(1000),
  filter: z.record(z.string(), z.any()).optional(),
});

const PostgresIndexerOptionsSchema = z.object({
});

/**
 * postgresRetrieverRef function creates a retriever for Postgres.
 * @param params The params for the new Postgres retriever
 * @param params.tableName The table name for the postgres retriever
If not specified, the default label will be `Postgres - <tableName>`
 * @returns A reference to a Postgres retriever.
 */
export const postgresRetrieverRef = (params: {
  tableName: string;
}) => {
  return retrieverRef({
    name: `postgres/${params.tableName}`,
    info: {
      label: params.tableName ?? `Postgres - ${params.tableName}`,
    },
    configSchema: PostgresRetrieverOptionsSchema,
  });
};

/**
 * postgresIndexerRef function creates an indexer for Postgres.
 * @param params The params for the new Postgres indexer.
 * @param params.tableName The table name for the Postgres indexer.
If not specified, the default label will be `Postgres - <tableName>`
 * @returns A reference to a Postgres indexer.
 */
export const postgresIndexerRef = (params: {
  tableName: string;
}) => {
  return indexerRef({
    name: `postgres/${params.tableName}`,
    info: {
      label: params.tableName ?? `Postgres - ${params.tableName}`,
    },
    configSchema: PostgresIndexerOptionsSchema.optional(),
  });
};

/**
 * Postgres plugin that provides a Postgres retriever and indexer
 * @param params An array of params to set up Postgres retrievers and indexers
 * @param params.tableName The name of the table
 * @param params.embedder The embedder to use for the indexer and retriever
 * @param params.embedderOptions  Options to customize the embedder
 * @returns The Postgres Genkit plugin
 */
export function postgres<EmbedderCustomOptions extends z.ZodTypeAny>(
  params: {
    tableName: string,
    embedder: EmbedderArgument<EmbedderCustomOptions>;
    embedderOptions?: z.infer<EmbedderCustomOptions>;
    engine: PostgresEngine;
    schemaName?: string;
    contentColumn: string;
    embeddingColumn: string;
    metadataColumns?: string[];
    idColumn: string;
    metadataJsonColumn?: string;
    distanceStrategy: DistanceStrategy;
    indexQueryOptions?: QueryOptions;
  }[]
): GenkitPlugin {
  return genkitPlugin('postgres', async (ai: Genkit) => {
    params.map((i) => configurePostgresRetriever(ai, i));
    params.map((i) => configurePostgresIndexer(ai, i));
  });
}

export default postgres;

/**
 * Configures a Postgres retriever.
 * @param ai A Genkit instance
 * @param params The params for the retriever
 * @param params.tableName The name of the table
 * @param params.embedder The embedder to use for the retriever
 * @param params.embedderOptions  Options to customize the embedder
 * @returns A Postgres retriever
 */
export function configurePostgresRetriever<
  EmbedderCustomOptions extends z.ZodTypeAny,
>(
  ai: Genkit,
  params: {
    tableName: string;
    embedder: EmbedderArgument<EmbedderCustomOptions>;
    embedderOptions?: z.infer<EmbedderCustomOptions>;
    engine: PostgresEngine;
    schemaName?: string;
    contentColumn: string;
    embeddingColumn: string;
    metadataColumns?: string[];
    idColumn: string;
    metadataJsonColumn?: string;
    distanceStrategy: DistanceStrategy;
    indexQueryOptions?: QueryOptions;
  }
) {
  if (!params.engine) {
    throw new Error('Engine is required');
  }

  async function queryCollection(embedding: number[], k?: number | undefined, filter?: string | undefined) {
    k = k ?? 4;
    const operator = params.distanceStrategy.operator;
    const searchFunction = params.distanceStrategy.searchFunction;
    const _filter = filter !== undefined ? `WHERE ${filter}` : "";
    const metadataColNames = params.metadataColumns && params.metadataColumns.length > 0 ? `"${params.metadataColumns.join("\",\"")}"` : "";
    const metadataJsonColName = params.metadataJsonColumn ? `, "${params.metadataJsonColumn}"` : "";

    const query = `SELECT "${params.idColumn}", "${params.contentColumn}", "${params.embeddingColumn}", ${metadataColNames} ${metadataJsonColName}, ${searchFunction}("${params.embeddingColumn}", '[${embedding}]') as distance FROM "${params.schemaName}"."${params.tableName}" ${_filter} ORDER BY "${params.embeddingColumn}" ${operator} '[${embedding}]' LIMIT ${k};;`;

    if (params.indexQueryOptions) {
      await params.engine.pool.raw(`SET LOCAL ${params.indexQueryOptions.to_string()}`);
    }

    const { rows } = await params.engine.pool.raw(query);

    return rows;
  }
    /**
    * Create an index on the vector store table
    * @param {BaseIndex} index
    * @param {string} name Optional
    * @param {boolean} concurrently Optional
    */
    async function applyVectorIndex(index: BaseIndex, name?: string, concurrently: boolean = false): Promise<void> {
      if (index instanceof ExactNearestNeighbor) {
        await dropVectorIndex();
        return;
      }

      const filter = index.partialIndexes ? `WHERE (${index.partialIndexes})` : "";
      const indexOptions = `WITH ${index.indexOptions()}`;
      const funct = index.distanceStrategy.indexFunction;

      if (!name) {
        if (!index.name) {
          index.name = params.tableName + DEFAULT_INDEX_NAME_SUFFIX;
        }
        name = index.name;
      }

      const stmt = `CREATE INDEX ${concurrently ? "CONCURRENTLY" : ""} ${name} ON "${params.schemaName}"."${params.tableName}" USING ${index.indexType} (${params.embeddingColumn} ${funct}) ${indexOptions} ${filter};`

      await params.engine.pool.raw(stmt);
    }

    /**
     * Check if index exists in the table.
     * @param {string} indexName Optional - index name
     */
    async function isValidIndex(indexName?: string): Promise<boolean> {
      const idxName = indexName || (params.tableName + DEFAULT_INDEX_NAME_SUFFIX);
      const stmt = `SELECT tablename, indexname
                          FROM pg_indexes
                          WHERE tablename = '${params.tableName}' AND schemaname = '${params.schemaName}' AND indexname = '${idxName}';`
      const {rows} = await params.engine.pool.raw(stmt);

      return rows.length === 1;
    }

    /**
     * Drop the vector index
     * @param {string} indexName Optional - index name
     */
    async function dropVectorIndex(indexName?: string): Promise<void> {
      const idxName = indexName || (params.tableName + DEFAULT_INDEX_NAME_SUFFIX);
      const query = `DROP INDEX IF EXISTS ${idxName};`;
      await params.engine.pool.raw(query)
    }

    /**
     * Re-index the vector store table
     * @param {string} indexName Optional - index name
     */
    async function reIndex(indexName?: string) {
      const idxName = indexName || (params.tableName + DEFAULT_INDEX_NAME_SUFFIX);
      const query = `REINDEX INDEX ${idxName};`;
      params.engine.pool.raw(query)
    }

  return ai.defineRetriever(
    {
      name: `postgres/${params.tableName}`,
      configSchema: PostgresRetrieverOptionsSchema,
    },
    async (content, options) => {
      console.log(`Retrieving data for table: ${params.tableName}`);
      const queryEmbeddings = await ai.embed({
        embedder: params.embedder ,
        content,
        options: params.embedderOptions,
      });
      const embedding = queryEmbeddings[0].embedding;
      const results = await queryCollection(embedding, options.k, options.filter);
      const documents: Document[] = [];
      for (const row of results) {
        const metadata =
          params.metadataJsonColumn && row[params.metadataJsonColumn]
            ? row[params.metadataJsonColumn]
            : {};
        if(params.metadataColumns){
          for (const col of params.metadataColumns) {
            metadata[col] = row[col];
          }
        }
        documents.push(
          new Document({
            content: row[params.contentColumn],
            metadata: metadata,
          })
        );
      }

      return { documents };
    }
  );
}

/**
 * Configures a Postgres indexer.
 * @param ai A Genkit instance
 * @param params The params for the indexer
 * @param params.tableName The name of the indexer
 * @param params.embedder The embedder to use for the retriever
 * @param params.embedderOptions  Options to customize the embedder
 * @returns A Genkit indexer
 */
export function configurePostgresIndexer<
  EmbedderCustomOptions extends z.ZodTypeAny,
>(
  ai: Genkit,
  params: {
    tableName: string;
    embedder: EmbedderArgument<EmbedderCustomOptions>;
    embedderOptions?: z.infer<EmbedderCustomOptions>;
  }
) {
  return ai.defineIndexer(
    {
      name: `postgres/${params.tableName}`,
      configSchema: PostgresIndexerOptionsSchema.optional(),
    },
    async (documents, options) => {
      // Implement your indexing logic here
      console.log(`Indexing data for table: ${params.tableName}`, documents, options);
      // You'll likely need to interact with your PostgresEngine here
      // to insert embeddings into your table.
    }
  );
}

