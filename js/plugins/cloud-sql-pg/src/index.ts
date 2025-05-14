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

import { Genkit, z } from 'genkit';
import { GenkitPlugin, genkitPlugin } from 'genkit/plugin';
import { EmbedderArgument, Embedding } from 'genkit/embedder';
import {
  CommonRetrieverOptionsSchema,
  Document,
  indexerRef,
  retrieverRef,
} from 'genkit/retriever';

import { v4 as uuidv4 } from 'uuid';
import { PostgresEngine, Column } from './engine';
import { DistanceStrategy, type QueryOptions } from './indexes';

const PostgresRetrieverOptionsSchema = CommonRetrieverOptionsSchema.extend({
  k: z.number().max(1000),
  filter: z.string().optional(),
});

const PostgresIndexerOptionsSchema = z.object({
  batchSize: z.number().default(100),
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
 * @param params.embedderOptions Options to customize the embedder
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
    ignoreMetadataColumns?: string[];
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
 * @param params.engine The engine to use for the indexer
 * @param params.embedder The embedder to use for the retriever
 * @param params.embedderOptions  Options to customize the embedder
 * @param params.metadataColumns The metadata columns to use for the indexer
 * @param params.idColumn The id column to use for the indexer
 * @param params.metadataJsonColumn The metadata json column to use for the indexer
 * @param params.contentColumn The content column to use for the indexer
 * @param params.embeddingColumn The embedding column to use for the indexer
 * @param params.schemaName The schema name to use for the indexer
 * @param params.chunkSize The chunk size to use for the indexer
 * @returns Add documents to vector store
 */
export function configurePostgresIndexer<
  EmbedderCustomOptions extends z.ZodTypeAny,
>(
  ai: Genkit,
  params: {
    tableName: string;
    engine: PostgresEngine;
    schemaName?: string;
    contentColumn?: string;
    embeddingColumn?: string;
    metadataColumns?: string[];
    ignoreMetadataColumns?: string[];
    idColumn?: string;
    metadataJsonColumn?: string;
    embedder: EmbedderArgument<EmbedderCustomOptions>;
    embedderOptions?: z.infer<EmbedderCustomOptions>;
  }
) {
  if (!params.engine) {
    throw new Error('Engine is required');
  }

  if (params.metadataColumns && params.ignoreMetadataColumns) {
    throw new Error('Cannot use both metadataColumns and ignoreMetadataColumns');
  }

  const {
    tableName,
    engine,
    schemaName,
    contentColumn,
    embeddingColumn,
    metadataColumns,
    ignoreMetadataColumns,
    idColumn,
    metadataJsonColumn,
    embedder,
    embedderOptions
  } = params;

  const defaultSchemaName = schemaName ?? 'public';
  const defaultContentColumn = contentColumn ?? 'content';
  const defaultEmbeddingColumn = embeddingColumn ?? 'embedding';
  const defaultIdColumn = idColumn ?? 'id';
  const defaultMetadataJsonColumn = metadataJsonColumn ?? 'metadata';

  // Store the final metadata columns at the module level
  let finalMetadataColumns: string[] = metadataColumns || [];

  async function ensureTableExists() {
    // Get existing columns and their types if table exists
    const { rows } = await engine.pool.raw(
      `SELECT column_name, data_type, is_nullable 
       FROM information_schema.columns 
       WHERE table_name = '${tableName}' AND table_schema = '${defaultSchemaName}'`
    );
    
    if (rows.length === 0) {
      throw new Error(`Table ${defaultSchemaName}.${tableName} does not exist. Please create it using initVectorstoreTable first.`);
    }

    const existingColumns = rows.map(row => row.column_name);
    const requiredColumns = [
      defaultIdColumn,
      defaultContentColumn,
      defaultEmbeddingColumn
    ];

    const missingColumns = requiredColumns.filter(col => !existingColumns.includes(col));
    if (missingColumns.length > 0) {
      throw new Error(`Missing required columns: ${missingColumns.join(', ')}`);
    }

    const columnTypes = rows.reduce((acc, row) => {
      acc[row.column_name] = row.data_type;
      return acc;
    }, {} as Record<string, string>);


    if (columnTypes[defaultContentColumn] !== 'text') {
      throw new Error(`Content column must be of type 'text', found '${columnTypes[defaultContentColumn]}'`);
    }


    if (columnTypes[defaultEmbeddingColumn] !== 'USER-DEFINED') {
      throw new Error(`Embedding column must be of type 'vector', found '${columnTypes[defaultEmbeddingColumn]}'`);
    }

    const idColumnType = columnTypes[defaultIdColumn];
    if (!idColumnType || !['text', 'character varying', 'varchar', 'uuid'].includes(idColumnType)) {
      throw new Error(`ID column must be a string type (text, varchar, or uuid), found '${idColumnType}'`);
    }

    if (ignoreMetadataColumns && ignoreMetadataColumns.length > 0) {
      finalMetadataColumns = existingColumns.filter(col => 
        !ignoreMetadataColumns.includes(col) && 
        !requiredColumns.includes(col) &&
        col !== defaultMetadataJsonColumn
      );
    }
  }

  async function generateEmbeddings(documents: Document[], options?: { batchSize?: number }): Promise<IndexedDocument[]> {
    const CHUNK_SIZE = options?.batchSize || 100;
    const results: IndexedDocument[] = [];
    
    for (let i = 0; i < documents.length; i += CHUNK_SIZE) {
      const chunk = documents.slice(i, i + CHUNK_SIZE);
      try {
        // Single batch call for all documents in the chunk
        const batchEmbeddings = await ai.embedMany({
          embedder,
          content: chunk,
          options: embedderOptions
        });
        
        const chunkResults = chunk.map((doc, index) => ({
          id: doc.metadata?.[defaultIdColumn] as string || uuidv4(),
          content: typeof doc.content === 'string' ? doc.content : JSON.stringify(doc.content),
          embedding: JSON.stringify(batchEmbeddings[index].embedding),
          metadata: doc.metadata || {}
        }));
        
        results.push(...chunkResults);
      } catch (error) {
        throw new Error('Embedding failed');
      }
    }
    
    return results;
  }

  return ai.defineIndexer(
    {
      name: `postgres/${params.tableName}`,
      configSchema: PostgresIndexerOptionsSchema.optional(),
    },

    async (docs, options) => {
      await ensureTableExists();
      
      try {
        const vectors = await generateEmbeddings(docs, options);
        const batchSize = options?.batchSize || 100;

        for (let i = 0; i < vectors.length; i += batchSize) {
          const batch = vectors.slice(i, i + batchSize);
          
          const insertData = batch.map(doc => {
            const metadata = doc.metadata || {};
            return {
              [defaultIdColumn]: doc.id,
              [defaultContentColumn]: doc.content,
              [defaultEmbeddingColumn]: doc.embedding,
              ...(defaultMetadataJsonColumn && { [defaultMetadataJsonColumn]: metadata }),
              ...Object.fromEntries(
                finalMetadataColumns
                  .filter(col => metadata[col] !== undefined)
                  .map(col => [col, metadata[col]])
              )
            };
          });

          const table = defaultSchemaName 
            ? engine.pool.withSchema(defaultSchemaName).table(tableName)
            : engine.pool.table(tableName);

          await table.insert(insertData);
        }
      } catch (error) {
        throw error;
      }
    }
  );
}

interface IndexedDocument {
  id: string;
  content: string;
  embedding: string;
  metadata: Record<string, unknown>;
}
