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
import { DistanceStrategy, QueryOptions } from "./indexes.js";
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
    distanceStrategy: 'cosine' | 'ip' | 'l2';
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
    engine: PostgresEngine;
    schemaName?: string;
    contentColumn: string;
    embeddingColumn: string;
    metadataColumns?: string[];
    idColumn: string;
    metadataJsonColumn?: string;
    distanceStrategy: DistanceStrategy;
    embedder: EmbedderArgument<EmbedderCustomOptions>;
    embedderOptions?: z.infer<EmbedderCustomOptions>;
    indexQueryOptions?: QueryOptions;
  }
) {
  if (!params.engine) {
    throw new Error('Engine is required');
  }

  async function queryCollection(embedding: number[], k?: number | undefined, filter?: string | undefined) {
    const operator = params.distanceStrategy.operator;
    const searchFunction = params.distanceStrategy.searchFunction;
    const metadataColNames = params.metadataColumns && params.metadataColumns.length > 0 ? `"${params.metadataColumns.join("\",\"")}"` : "";
    const metadataJsonColName = params.metadataJsonColumn ? `, "${params.metadataJsonColumn}"` : "";

    const query = `SELECT "${params.idColumn}", "${params.contentColumn}", "${params.embeddingColumn}", ${metadataColNames} ${metadataJsonColName}, ${searchFunction}("${params.embeddingColumn}", '[${embedding}]') as distance FROM "${params.schemaName}"."${params.tableName}" ${_filter} ORDER BY "${params.embeddingColumn}" ${operator} '[${embedding}]';`

    if (params.indexQueryOptions) {
      await params.engine.pool.raw(`SET LOCAL ${params.indexQueryOptions.to_string()}`)
    }

    const {rows} = await params.engine.pool.raw(query);

    return rows;
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
      let documents: Document[] = [];
      const embedding = queryEmbeddings[0].embedding;
      const results = await queryCollection(embedding, options.k, options.filter);
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
        documents.push([
          new Document({
            pageContent: row[params.contentColumn],
            metadata: metadata,
          })
        ]);
      }

      return documents;
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
    }
  );
}

