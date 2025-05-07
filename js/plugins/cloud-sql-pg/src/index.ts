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

import { type Genkit, z } from 'genkit';
import type { EmbedderArgument } from 'genkit/embedder';
import { type GenkitPlugin, genkitPlugin } from 'genkit/plugin';
import type { PostgresEngine } from './engine';
import { DistanceStrategy, type QueryOptions } from './indexes';

const PostgresRetrieverOptionsSchema = CommonRetrieverOptionsSchema.extend({
  k: z.number().max(1000),
  filter: z.string().optional(),
});

const PostgresIndexerOptionsSchema = z.object({});

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
    tableName: string;
    embedder: EmbedderArgument<EmbedderCustomOptions>;
    embedderOptions?: z.infer<EmbedderCustomOptions>;
    engine: PostgresEngine;
    schemaName?: string;
    contentColumn?: string;
    embeddingColumn?: string;
    metadataColumns?: string[];
    ignoreMetaDataColumns?: string[];
    idColumn?: string;
    metadataJsonColumn?: string;
    distanceStrategy?: DistanceStrategy;
    indexQueryOptions?: QueryOptions;
  }[]
): GenkitPlugin {
  return genkitPlugin('postgres', async (ai: Genkit) => {
    params.map(i => configurePostgresRetriever(ai, i));
    params.map(i => configurePostgresIndexer(ai, i));
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
export async function configurePostgresRetriever<
  EmbedderCustomOptions extends z.ZodTypeAny,
>(
  ai: Genkit,
  params: {
    tableName: string;
    embedder: EmbedderArgument<EmbedderCustomOptions>;
    embedderOptions?: z.infer<EmbedderCustomOptions>;
    engine: PostgresEngine;
    schemaName?: string;
    contentColumn?: string;
    embeddingColumn?: string;
    metadataColumns?: string[];
    ignoreMetadataColumns?: string[];
    idColumn?: string;
    metadataJsonColumn?: string;
    distanceStrategy?: DistanceStrategy;
    indexQueryOptions?: QueryOptions;
  }
) {
  const schemaName = params.schemaName ?? 'public';
  const contentColumn = params.contentColumn ?? 'content';
  const embeddingColumn = params.embeddingColumn ?? 'embedding';
  const distanceStrategy =
    params.distanceStrategy ?? DistanceStrategy.COSINE_DISTANCE;
  if (!params.engine) {
    throw new Error('Engine is required');
  }

  async function checkColumns() {
    if (
      params.metadataColumns !== undefined &&
      params.ignoreMetadataColumns !== undefined
    ) {
      throw 'Can not use both metadata_columns and ignore_metadata_columns.';
    }

    const { rows } = await params.engine.pool.raw(
      `SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '${params.tableName}' AND table_schema = '${schemaName}'`
    );
    const columns: { [key: string]: any } = {};

    for (const index in rows) {
      const row = rows[index];
      columns[row['column_name']] = row['data_type'];
    }

    if (params.idColumn && !columns.hasOwnProperty(params.idColumn)) {
      throw `Id column: ${params.idColumn}, does not exist.`;
    }

    if (contentColumn && !columns.hasOwnProperty(contentColumn)) {
      throw `Content column: ${params.contentColumn}, does not exist.`;
    }

    const contentType = contentColumn ? columns[contentColumn] : '';

    if (contentType !== 'text' && !contentType.includes('char')) {
      throw `Content column: ${contentColumn}, is type: ${contentType}. It must be a type of character string.`;
    }

    if (embeddingColumn && !columns.hasOwnProperty(embeddingColumn)) {
      throw `Embedding column: ${embeddingColumn}, does not exist.`;
    }

    if (embeddingColumn && columns[embeddingColumn] !== 'USER-DEFINED') {
      throw `Embedding column: ${embeddingColumn} is not of type Vector.`;
    }

    const metadataJsonColumnToCheck = params.metadataJsonColumn ?? '';
    params.metadataJsonColumn = columns.hasOwnProperty(
      metadataJsonColumnToCheck
    )
      ? params.metadataJsonColumn
      : '';

    if (params.metadataColumns) {
      for (const column of params.metadataColumns) {
        if (column && !columns.hasOwnProperty(column)) {
          throw `Metadata column: ${column}, does not exist.`;
        }
      }
    }

    const allColumns = columns;
    if (
      params.ignoreMetadataColumns !== undefined &&
      params.ignoreMetadataColumns.length > 0
    ) {
      for (const column of params.ignoreMetadataColumns) {
        delete allColumns[column];
      }

      if (params.idColumn) {
        delete allColumns[params.idColumn];
      }
      if (contentColumn) {
        delete allColumns[contentColumn];
      }
      if (embeddingColumn) {
        delete allColumns[embeddingColumn];
      }
      params.metadataColumns = Object.keys(allColumns);
    }
  }

  async function queryCollection(
    embedding: number[],
    k?: number | undefined,
    filter?: string | undefined
  ) {
    k = k ?? 4;
    const operator = distanceStrategy.operator;
    const searchFunction = distanceStrategy.searchFunction;
    const _filter = filter !== undefined ? `WHERE ${filter}` : '';
    const metadataColNames =
      params.metadataColumns && params.metadataColumns.length > 0
        ? `"${params.metadataColumns.join('","')}"`
        : '';
    const metadataJsonColName = params.metadataJsonColumn
      ? `, "${params.metadataJsonColumn}"`
      : '';

    const query = `SELECT "${params.idColumn}", "${contentColumn}", "${embeddingColumn}", ${metadataColNames} ${metadataJsonColName}, ${searchFunction}("${embeddingColumn}", '[${embedding}]') as distance FROM "${schemaName}"."${params.tableName}" ${_filter} ORDER BY "${embeddingColumn}" ${operator} '[${embedding}]' LIMIT ${k};`;

    if (params.indexQueryOptions) {
      await params.engine.pool.raw(
        `SET LOCAL ${params.indexQueryOptions.to_string()}`
      );
    }

    const { rows } = await params.engine.pool.raw(query);

    return rows;
  }

  return ai.defineRetriever(
    {
      name: `postgres/${params.tableName}`,
      configSchema: PostgresRetrieverOptionsSchema,
    },
    async (content, options) => {
      console.log(`Retrieving data for table: ${params.tableName}`);
      checkColumns();
      const queryEmbeddings = await ai.embed({
        embedder: params.embedder,
        content,
        options: params.embedderOptions,
      });
      const embedding = queryEmbeddings[0].embedding;
      const results = await queryCollection(
        embedding,
        options.k,
        options.filter
      );
      const documents: Document[] = [];
      for (const row of results) {
        const metadata =
          params.metadataJsonColumn && row[params.metadataJsonColumn]
            ? row[params.metadataJsonColumn]
            : {};
        if (params.metadataColumns) {
          for (const col of params.metadataColumns) {
            metadata[col] = row[col];
          }
        }
        documents.push(
          new Document({
            content: row[contentColumn],
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
      console.log(
        `Indexing data for table: ${params.tableName}`,
        documents,
        options
      );
      // You'll likely need to interact with your PostgresEngine here
      // to insert embeddings into your table.
    }
  );
}
