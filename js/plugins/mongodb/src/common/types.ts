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

import { EmbedderArgument, z } from 'genkit';
import { CollectionOptions, DbOptions, MongoClientOptions } from 'mongodb';
import {
  DEFAULT_BATCH_SIZE,
  DEFAULT_DATA_FIELD_NAME,
  DEFAULT_DATA_TYPE_FIELD_NAME,
  DEFAULT_EMBEDDING_FIELD_NAME,
  DEFAULT_METADATA_FIELD_NAME,
  MAX_NUM_CANDIDATES,
} from './constants';

const MONGO_ID_REGEX = /^[0-9a-fA-F]{24}$/;

// Retry

const RetryOptionsSchema = z.object({
  retryAttempts: z.number().int().positive().optional(),
  baseDelay: z.number().int().positive().optional(),
  jitterFactor: z.number().int().positive().optional(),
});

/** Configuration options for retry operations */
export type RetryOptions = z.infer<typeof RetryOptionsSchema>;

// Embedder

/** Custom embedder options type for extensibility */
export type EmbedderCustomOptions = z.ZodTypeAny;

const EmbedderOptionsSchema = z.object({
  embedder: z.custom<EmbedderArgument<EmbedderCustomOptions>>((val) => {
    if (!val) {
      throw new Error('Embedder is required');
    }
    return val;
  }),
  embedderOptions: z.any().optional(),
});

/** Configuration options for embedder operations */
export type EmbedderOptions = z.infer<typeof EmbedderOptionsSchema>;

// Database Collection

const BaseDatabaseCollectionSchema = z.object({
  dbName: z.string().min(1, 'Database name is required'),
  dbOptions: (z.any() as z.ZodType<DbOptions>).optional(),
  collectionName: z.string().min(1, 'Collection name is required'),
  collectionOptions: (z.any() as z.ZodType<CollectionOptions>).optional(),
});

/** Schema for data field configuration */
export const DataFieldSchema = z.object({
  dataField: z
    .string()
    .optional()
    .default(DEFAULT_DATA_FIELD_NAME)
    .describe('The field name to use for the data'),
  metadataField: z
    .string()
    .optional()
    .default(DEFAULT_METADATA_FIELD_NAME)
    .describe('The field name to use for the metadata'),
  dataTypeField: z
    .string()
    .optional()
    .default(DEFAULT_DATA_TYPE_FIELD_NAME)
    .describe('The field name to use for the data type'),
});

// Indexer

/** Schema for MongoDB indexer configuration options */
export const IndexerOptionsSchema = BaseDatabaseCollectionSchema.and(
  EmbedderOptionsSchema
)
  .and(DataFieldSchema)
  .and(
    z.object({
      embeddingField: z
        .string()
        .min(1)
        .optional()
        .default(DEFAULT_EMBEDDING_FIELD_NAME)
        .describe('The field name to use for the embedding'),
      batchSize: z
        .number()
        .int()
        .positive()
        .optional()
        .default(DEFAULT_BATCH_SIZE)
        .describe('The batch size to use for processing documents'),
      skipData: z
        .boolean()
        .optional()
        .default(false)
        .describe('Whether to skip storing document data'),
    })
  );

/** Configuration options for MongoDB indexer operations */
export type IndexerOptions = z.infer<typeof IndexerOptionsSchema>;

/**
 * Validates and normalizes indexer options.
 *
 * @param options - The indexer options to validate
 * @returns Validated and normalized indexer options
 * @throws {Error} If validation fails
 */
export function validateIndexerOptions(
  options: IndexerOptions
): IndexerOptions {
  try {
    return IndexerOptionsSchema.parse(options);
  } catch (validationError) {
    throw new Error(
      `Invalid Mongo indexer options: ${validationError instanceof Error ? validationError.message : 'Validation failed'}`
    );
  }
}

// Text Search

const TextSearchSchema = z
  .object({
    index: z
      .string()
      .min(1, 'Index is required')
      .describe('The index to search'),
    text: z
      .object({
        path: z
          .union([
            z.string().min(1, 'Path is required'),
            z
              .array(z.string().min(1, 'Path is required'))
              .min(1, 'At least one path is required'),
          ])
          .describe(
            'The path(s) to search - can be a single string or array of strings'
          ),
        matchCriteria: z
          .enum(['any', 'all'])
          .optional()
          .describe('The match criteria to use for the search'),
        fuzzy: z
          .object({
            maxEdits: z.number().int().min(1).max(2).optional(),
            prefixLength: z.number().int().min(0).optional(),
            maxExpansions: z.number().int().positive().optional(),
          })
          .optional(),
        score: z
          .any()
          .optional()
          .describe('Score assigned to matching search term results'),
        synonyms: z
          .string()
          .min(1)
          .optional()
          .describe('Synonyms to use for the search'),
      })
      .describe('The text search schema specification')
      .superRefine((data, ctx) => {
        if (data.fuzzy && data.synonyms) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: 'fuzzy and synonyms cannot be used together',
            path: ['fuzzy', 'synonyms'],
          });
        }
      }),
  })
  .describe('The search schema specification for text search');

export type TextSearchOptions = z.infer<typeof TextSearchSchema>;

// Vector Search

const VectorSearchSchema = z
  .object({
    index: z
      .string()
      .min(1, 'Index is required')
      .describe('The index to search'),
    path: z.string().min(1, 'Path is required').describe('The path to search'),
    exact: z.boolean().optional(),
    numCandidates: z
      .number()
      .int()
      .positive()
      .max(MAX_NUM_CANDIDATES)
      .optional(),
    limit: z.number().int().positive().optional(),
    filter: z.record(z.any()).optional(),
  })
  .superRefine((data, ctx) => {
    if (data.exact === false && !data.numCandidates) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'numCandidates required when exact is false',
        path: ['numCandidates'],
      });
    }
    if (data.numCandidates && data.exact === undefined) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'exact required when numCandidates provided',
        path: ['exact'],
      });
    }
    if (data.limit && data.numCandidates && data.limit > data.numCandidates) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'limit cannot exceed numCandidates',
        path: ['limit'],
      });
    }
  })
  .describe('The vector search schema specification');

export type VectorSearchOptions = z.infer<typeof VectorSearchSchema>;

const HybridSearchSchema = z.object({
  search: TextSearchSchema,
  vectorSearch: VectorSearchSchema,
  combination: z
    .object({
      weights: z
        .object({
          vectorPipeline: z.number().positive().max(1).optional().default(0.5),
          fullTextPipeline: z
            .number()
            .positive()
            .max(1)
            .optional()
            .default(0.5),
        })
        .optional()
        .describe('The weights for the vector and full text pipelines'),
    })
    .optional()
    .describe('The combination of the vector and full text pipelines'),
  scoreDetails: z
    .boolean()
    .optional()
    .default(false)
    .describe('Whether to include score details in the results'),
});

export type HybridSearchOptions = z.infer<typeof HybridSearchSchema>;

// Retriever

export const RetrieverOptionsSchema = BaseDatabaseCollectionSchema.and(
  z.union([
    z.object({ search: TextSearchSchema }),
    EmbedderOptionsSchema.and(z.object({ vectorSearch: VectorSearchSchema })),
    EmbedderOptionsSchema.and(z.object({ hybridSearch: HybridSearchSchema })),
  ])
)
  .and(DataFieldSchema)
  .and(
    z.object({
      pipelines: z
        .array(z.any())
        .optional()
        .describe('The aggregation pipeline stages to apply to the search'),
    })
  );

/** Configuration options for MongoDB retriever operations */
export type RetrieverOptions = z.infer<typeof RetrieverOptionsSchema>;

/**
 * Validates and normalizes retriever options.
 *
 * @param options - The retriever options to validate
 * @returns Validated and normalized retriever options
 * @throws {Error} If validation fails
 */
export function validateRetrieverOptions(
  options: RetrieverOptions
): RetrieverOptions {
  try {
    return RetrieverOptionsSchema.parse(options);
  } catch (validationError) {
    throw new Error(
      `Invalid Mongo retriever options: ${validationError instanceof Error ? validationError.message : 'Validation failed'}`
    );
  }
}

// CRUD

/** Input schema for MongoDB create operations */
export const InputCreateSchema = z.object({
  dbName: z
    .string()
    .describe('The name of the database to use')
    .min(1, 'Database name is required'),
  dbOptions: z
    .object({})
    .passthrough()
    .describe('The database options to use')
    .optional(),
  collectionName: z
    .string()
    .describe('The name of the collection to use')
    .min(1, 'Collection name is required'),
  collectionOptions: z
    .object({})
    .passthrough()
    .describe('The collection options to use')
    .optional(),
  document: z.object({}).passthrough().describe('The document data to insert'),
});

/** Input type for MongoDB create operations */
export type InputCreate = z.infer<typeof InputCreateSchema>;

/**
 * Validates and normalizes create operation input.
 *
 * @param input - The create operation input to validate
 * @returns Validated and normalized create operation input
 * @throws {Error} If validation fails
 */
export function validateCreateOptions(input: InputCreate): InputCreate {
  try {
    return InputCreateSchema.parse(input);
  } catch (validationError) {
    throw new Error(
      `Invalid Mongo options: ${validationError instanceof Error ? validationError.message : 'Validation failed'}`
    );
  }
}

/** Output schema for MongoDB create operations */
export const OutputCreateSchema = z.object({
  insertedId: z.string().describe('The ID of the inserted document'),
  success: z.boolean().describe('Whether the operation was successful'),
  message: z.string().describe('Operation result message'),
});

/** Input schema for MongoDB read operations */
export const InputReadSchema = z.object({
  dbName: z
    .string()
    .describe('The name of the database to use')
    .min(1, 'Database name is required'),
  dbOptions: z
    .object({})
    .passthrough()
    .describe('The database options to use')
    .optional(),
  collectionName: z
    .string()
    .describe('The name of the collection to use')
    .min(1, 'Collection name is required'),
  collectionOptions: z
    .object({})
    .passthrough()
    .describe('The collection options to use')
    .optional(),
  id: z.string().regex(MONGO_ID_REGEX).describe('The document ID to retrieve'),
});

/** Input type for MongoDB read operations */
export type InputRead = z.infer<typeof InputReadSchema>;

/**
 * Validates and normalizes read operation input.
 *
 * @param input - The read operation input to validate
 * @returns Validated and normalized read operation input
 * @throws {Error} If validation fails
 */
export function validateReadOptions(input: InputRead): InputRead {
  try {
    return InputReadSchema.parse(input);
  } catch (validationError) {
    throw new Error(
      `Invalid Mongo options: ${validationError instanceof Error ? validationError.message : 'Validation failed'}`
    );
  }
}
export const OutputReadSchema = z.object({
  document: z
    .record(z.any())
    .nullable()
    .describe('The retrieved document or null if not found'),
  success: z.boolean().describe('Whether the operation was successful'),
  message: z.string().describe('Operation result message'),
});

export const InputUpdateSchema = z.object({
  dbName: z
    .string()
    .describe('The name of the database to use')
    .min(1, 'Database name is required'),
  dbOptions: z
    .object({})
    .passthrough()
    .describe('The database options to use')
    .optional(),
  collectionName: z
    .string()
    .describe('The name of the collection to use')
    .min(1, 'Collection name is required'),
  collectionOptions: z
    .object({})
    .passthrough()
    .describe('The collection options to use')
    .optional(),
  id: z.string().regex(MONGO_ID_REGEX).describe('The document ID to update'),
  update: z
    .object({})
    .passthrough()
    .describe(
      'The MongoDB update operations to apply (must use atomic operators like $set, $unset, $inc, etc.)'
    ),
  options: z
    .object({})
    .passthrough()
    .describe('The MongoDB update options to apply')
    .optional(),
});

export type InputUpdate = z.infer<typeof InputUpdateSchema>;

export function validateUpdateOptions(input: InputUpdate): InputUpdate {
  try {
    return InputUpdateSchema.parse(input);
  } catch (validationError) {
    throw new Error(
      `Invalid Mongo options: ${validationError instanceof Error ? validationError.message : 'Validation failed'}`
    );
  }
}
export const OutputUpdateSchema = z.object({
  matchedCount: z
    .number()
    .describe('Number of documents that matched the filter'),
  modifiedCount: z.number().describe('Number of documents that were modified'),
  upsertedId: z
    .string()
    .nullable()
    .describe('ID of the upserted document if upsert was true'),
  success: z.boolean().describe('Whether the operation was successful'),
  message: z.string().describe('Operation result message'),
});

export const InputDeleteSchema = z.object({
  dbName: z
    .string()
    .describe('The name of the database to use')
    .min(1, 'Database name is required'),
  dbOptions: z
    .object({})
    .passthrough()
    .describe('The database options to use')
    .optional(),
  collectionName: z
    .string()
    .describe('The name of the collection to use')
    .min(1, 'Collection name is required'),
  collectionOptions: z
    .object({})
    .passthrough()
    .describe('The collection options to use')
    .optional(),
  id: z.string().regex(MONGO_ID_REGEX).describe('The document ID to delete'),
});

export type InputDelete = z.infer<typeof InputDeleteSchema>;

export function validateDeleteOptions(input: InputDelete): InputDelete {
  try {
    return InputDeleteSchema.parse(input);
  } catch (validationError) {
    throw new Error(
      `Invalid Mongo options: ${validationError instanceof Error ? validationError.message : 'Validation failed'}`
    );
  }
}

export const OutputDeleteSchema = z.object({
  deletedCount: z.number().describe('Number of documents that were deleted'),
  success: z.boolean().describe('Whether the operation was successful'),
  message: z.string().describe('Operation result message'),
});

// Search Index

const SearchIndexDefinitionSchema = z
  .object({
    mappings: z
      .object({
        dynamic: z.boolean().optional(),
        fields: z.object({}).passthrough().optional(),
      })
      .passthrough()
      .superRefine((data, ctx) => {
        if (data.dynamic === false && !data.fields) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: 'fields are required when dynamic is false',
            path: ['fields'],
          });
        }
      }),
  })
  .passthrough()
  .describe('The index definition');

const VectorSearchIndexSchema = z
  .object({
    fields: z
      .array(
        z
          .object({
            type: z
              .enum(['vector', 'filter'])
              .describe(
                'Type of the field to use to index fields for vector search'
              ),
            path: z.string().describe('Name of the field to index'),
            numDimensions: z
              .number()
              .positive()
              .max(8192)
              .describe(
                'Number of vector dimensions that Atlas Vector Search enforces at index-time and query-time'
              ),
            similarity: z
              .enum(['cosine', 'euclidean', 'dotProduct'])
              .describe(
                'Vector similarity function to use to search for top K-nearest neighbors'
              ),
            quantization: z
              .enum(['none', 'scalar', 'binary'])
              .describe(
                'Type of automatic vector quantization for your vectors'
              )
              .optional(),
          })
          .passthrough()
          .superRefine((data, ctx) => {
            if (data.type !== 'vector') {
              if (data.similarity) {
                ctx.addIssue({
                  code: z.ZodIssueCode.custom,
                  message: 'similarity can only be set for vector fields',
                  path: ['similarity'],
                });
              }
              if (data.numDimensions) {
                ctx.addIssue({
                  code: z.ZodIssueCode.custom,
                  message: 'numDimensions can only be set for vector fields',
                  path: ['numDimensions'],
                });
              }
            }
          })
      )
      .min(1, 'At least one vector field is required'),
  })
  .passthrough()
  .describe('The index definition');

export const InputSearchIndexCreateSchema = z.object({
  dbName: z
    .string()
    .describe('The name of the database to use')
    .min(1, 'Database name is required'),
  dbOptions: z
    .object({})
    .passthrough()
    .describe('The database options to use')
    .optional(),
  collectionName: z
    .string()
    .describe('The name of the collection to use')
    .min(1, 'Collection name is required'),
  collectionOptions: z
    .object({})
    .passthrough()
    .describe('The collection options to use')
    .optional(),
  schema: z
    .object({
      name: z.string().describe('Name of the index').optional(),
      type: z.enum(['search', 'vectorSearch']).describe('Type of the index'),
      definition: z.object({}).passthrough(),
    })
    .superRefine((data, ctx) => {
      if (data.type === 'search') {
        try {
          SearchIndexDefinitionSchema.parse(data.definition);
        } catch (error) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `Invalid search index definition: ${error instanceof Error ? error.message : 'Validation failed'}`,
            path: ['definition'],
          });
        }
      } else if (data.type === 'vectorSearch') {
        try {
          VectorSearchIndexSchema.parse(data.definition);
        } catch (error) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: `Invalid vector search index definition: ${error instanceof Error ? error.message : 'Validation failed'}`,
            path: ['definition'],
          });
        }
      }
    })
    .describe('The index schema'),
});

export type InputSearchIndexCreate = z.infer<
  typeof InputSearchIndexCreateSchema
>;

export function validateSearchIndexCreateOptions(
  input: InputSearchIndexCreate
): InputSearchIndexCreate {
  try {
    return InputSearchIndexCreateSchema.parse(input);
  } catch (validationError) {
    throw new Error(
      `Invalid Mongo options: ${validationError instanceof Error ? validationError.message : 'Validation failed'}`
    );
  }
}

export const OutputSearchIndexCreateSchema = z.object({
  indexName: z.string().describe('Name of the created index'),
  success: z.boolean().describe('Whether the operation was successful'),
  message: z.string().describe('Operation result message'),
});

export const InputSearchIndexListSchema = z.object({
  dbName: z
    .string()
    .describe('The name of the database to use')
    .min(1, 'Database name is required'),
  dbOptions: z
    .object({})
    .passthrough()
    .describe('The database options to use')
    .optional(),
  collectionName: z
    .string()
    .describe('The name of the collection to use')
    .min(1, 'Collection name is required'),
  collectionOptions: z
    .object({})
    .passthrough()
    .describe('The collection options to use')
    .optional(),
});

export type InputSearchIndexList = z.infer<typeof InputSearchIndexListSchema>;

export function validateSearchIndexListOptions(
  input: InputSearchIndexList
): InputSearchIndexList {
  try {
    return InputSearchIndexListSchema.parse(input);
  } catch (validationError) {
    throw new Error(
      `Invalid Mongo options: ${validationError instanceof Error ? validationError.message : 'Validation failed'}`
    );
  }
}

export const OutputSearchIndexListSchema = z.object({
  indexes: z.array(z.record(z.any())).describe('Array of index definitions'),
  success: z.boolean().describe('Whether the operation was successful'),
  message: z.string().describe('Operation result message'),
});

export const InputSearchIndexDropSchema = z.object({
  dbName: z
    .string()
    .describe('The name of the database to use')
    .min(1, 'Database name is required'),
  dbOptions: z
    .object({})
    .passthrough()
    .describe('The database options to use')
    .optional(),
  collectionName: z
    .string()
    .describe('The name of the collection to use')
    .min(1, 'Collection name is required'),
  collectionOptions: z
    .object({})
    .passthrough()
    .describe('The collection options to use')
    .optional(),
  indexName: z
    .string()
    .describe('Name of the index to drop')
    .min(1, 'Index name is required'),
});

export type InputSearchIndexDrop = z.infer<typeof InputSearchIndexDropSchema>;

export function validateSearchIndexDropOptions(
  input: InputSearchIndexDrop
): InputSearchIndexDrop {
  try {
    return InputSearchIndexDropSchema.parse(input);
  } catch (validationError) {
    throw new Error(
      `Invalid Mongo options: ${validationError instanceof Error ? validationError.message : 'Validation failed'}`
    );
  }
}

export const OutputSearchIndexDropSchema = z.object({
  success: z.boolean().describe('Whether the operation was successful'),
  message: z.string().describe('Operation result message'),
});

// Connection

const BaseDefinitionSchema = z.object({
  id: z.string().min(1, 'ID is required'),
  retry: RetryOptionsSchema.optional(),
});

/** Base definition for indexer, retriever, crudTools, and searchIndexTools */
export type BaseDefinition = z.infer<typeof BaseDefinitionSchema>;

export const ConnectionSchema = z
  .object({
    url: z.string().url('Invalid  URL'),
    mongoClientOptions: (z.any() as z.ZodType<MongoClientOptions>).optional(),
    indexer: BaseDefinitionSchema.optional(),
    retriever: BaseDefinitionSchema.optional(),
    crudTools: BaseDefinitionSchema.optional(),
    searchIndexTools: BaseDefinitionSchema.optional(),
  })
  .refine(
    (data) => {
      return (
        data.indexer ||
        data.retriever ||
        data.crudTools ||
        data.searchIndexTools
      );
    },
    {
      message:
        'At least one of indexer, retriever, crudTools, or searchIndexTools must be provided',
      path: ['indexer'],
    }
  );

/** Configuration options for MongoDB connection */
export type Connection = z.infer<typeof ConnectionSchema>;

/**
 * Validates and normalizes connection options.
 *
 * @param connection - The connection options to validate
 * @returns Validated and normalized connection options
 * @throws {Error} If validation fails
 */
export function validateConnection(connection: Connection): Connection {
  try {
    return ConnectionSchema.parse(connection);
  } catch (validationError) {
    throw new Error(
      `Invalid Mongo options: ${validationError instanceof Error ? validationError.message : 'Validation failed'}`
    );
  }
}
