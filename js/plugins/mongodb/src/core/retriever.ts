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
import { Document, retrieverRef } from 'genkit/retriever';
import { Collection, MongoClient, Document as MongoDocument } from 'mongodb';
import { getCollection } from '../common/connection';
import { retryWithDelay } from '../common/retry';
import {
  BaseDefinition,
  EmbedderOptions,
  HybridSearchOptions,
  RetrieverOptions,
  RetrieverOptionsSchema,
  RetryOptions,
  TextSearchOptions,
  VectorSearchOptions,
  validateRetrieverOptions,
} from '../common/types';

/**
 * Appends two MongoDB aggregation pipelines together.
 *
 * @param pipeline1 - First pipeline array
 * @param pipeline2 - Second pipeline array
 * @returns Combined pipeline array
 */
function appendPipeline(pipeline1?: Array<any>, pipeline2?: Array<any>) {
  const pipeline: Array<any> = [];
  if (pipeline1 && pipeline1.length > 0) {
    pipeline.push(...pipeline1);
  }
  if (pipeline2 && pipeline2.length > 0) {
    pipeline.push(...pipeline2);
  }
  return pipeline;
}

/**
 * Creates a MongoDB text search aggregation stage.
 *
 * @param query - The text query to search for
 * @param options - Text search configuration options
 * @returns MongoDB aggregation stage for text search
 */
function createTextSearchStage(query: string, options: TextSearchOptions): any {
  return {
    $search: { index: options.index, text: { ...options.text, query } },
  };
}

/**
 * Creates a MongoDB vector search aggregation stage.
 *
 * @param queryVector - The vector to search with
 * @param options - Vector search configuration options
 * @returns MongoDB aggregation stage for vector search
 */
function createVectorSearchStage(
  queryVector: number[],
  options: VectorSearchOptions
): any {
  return {
    $vectorSearch: {
      ...options,
      queryVector,
    },
  };
}

/**
 * Creates a MongoDB hybrid search aggregation stage.
 *
 * @param query - The text query to search for
 * @param queryVector - The vector to search with
 * @param options - Hybrid search configuration options
 * @returns MongoDB aggregation stage for hybrid search
 */
function createHybridSearchStage(
  query: string,
  queryVector: number[],
  options: HybridSearchOptions
): any {
  return {
    $rankFusion: {
      input: {
        pipelines: {
          fullTextPipeline: [createTextSearchStage(query, options.search)],
          vectorPipeline: [
            createVectorSearchStage(queryVector, options.vectorSearch),
          ],
        },
      },
      combination: options.combination,
      scoreDetails: options.scoreDetails,
    },
  };
}

/**
 * Executes a MongoDB aggregation pipeline with retry support.
 *
 * @param collection - MongoDB collection
 * @param pipeline - Aggregation pipeline to execute
 * @param retryOptions - Optional retry configuration
 * @returns Array of MongoDB documents
 */
async function executeSearchPipeline(
  collection: Collection,
  pipeline: Array<any>,
  retryOptions?: RetryOptions
): Promise<Array<MongoDocument>> {
  return retryWithDelay(async () => {
    return await collection.aggregate(pipeline).toArray();
  }, retryOptions);
}

/**
 * Converts MongoDB documents to Genkit Document objects.
 *
 * @param results - Array of MongoDB documents
 * @param options - Retriever options for field mapping
 * @returns Array of Genkit Document objects
 */
async function convertResultsToDocuments(
  results: Array<MongoDocument>,
  options: RetrieverOptions
): Promise<Array<Document>> {
  const { dataField, dataTypeField, metadataField } = options;
  return results.map((result) => {
    let data = '';
    if (result[dataField]) {
      data = result[dataField];
    }
    return Document.fromData(
      data,
      result[dataTypeField],
      result[metadataField]
    );
  });
}

/**
 * Generates embeddings for a document using the specified embedder.
 *
 * @param ai - Genkit AI instance
 * @param document - Document to embed
 * @param options - Embedder configuration options
 * @returns Array of embedding values
 */
async function generateEmbeddings(
  ai: Genkit,
  document: Document,
  options: EmbedderOptions
): Promise<Array<number>> {
  const embeddings = await ai.embed({
    embedder: options.embedder,
    options: options.embedderOptions,
    content: document,
  });
  return embeddings[0].embedding;
}

/**
 * Creates a MongoDB aggregation pipeline for search operations.
 *
 * Supports text search, vector search, and hybrid search modes.
 *
 * @param ai - Genkit AI instance
 * @param document - Document to search with
 * @param options - Retriever options defining search type and configuration
 * @returns MongoDB aggregation pipeline
 * @throws {Error} If unknown search options are provided
 */
async function createSearchPipeline(
  ai: Genkit,
  document: Document,
  options: RetrieverOptions
): Promise<Array<any>> {
  try {
    const pipeline: Array<any> = [];

    if ('search' in options) {
      pipeline.push(createTextSearchStage(document.data, options.search));
    } else {
      const embedder: EmbedderOptions = {
        embedder: options.embedder,
        embedderOptions: options.embedderOptions,
      };
      const embedding: Array<number> = await generateEmbeddings(
        ai,
        document,
        embedder
      );

      if ('vectorSearch' in options) {
        pipeline.push(createVectorSearchStage(embedding, options.vectorSearch));
      } else if ('hybridSearch' in options) {
        pipeline.push(
          createHybridSearchStage(
            document.data,
            embedding,
            options.hybridSearch
          )
        );
      } else {
        throw new Error(`Unknown retrieval options provided: ${options}`);
      }
    }

    return appendPipeline(pipeline, options.pipelines);
  } catch (error) {
    throw new Error(
      `Failed to create search pipeline: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Retrieves documents from MongoDB using the specified search strategy.
 *
 * @param ai - Genkit AI instance
 * @param collection - MongoDB collection
 * @param document - Document to search with
 * @param options - Retriever options
 * @param retryOptions - Optional retry configuration
 * @returns Object containing retrieved documents
 * @throws {Error} If retrieval fails
 */
async function retrieve(
  ai: Genkit,
  collection: Collection,
  document: Document,
  options: RetrieverOptions,
  retryOptions?: RetryOptions
) {
  try {
    const pipeline = await createSearchPipeline(ai, document, options);
    const results = await executeSearchPipeline(
      collection,
      pipeline,
      retryOptions
    );
    const documents = await convertResultsToDocuments(results, options);

    return { documents };
  } catch (error) {
    throw new Error(
      `Mongo retrieval failed: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Configures a MongoDB retriever for the Genkit AI framework.
 *
 * @param ai - Genkit AI instance
 * @param client - MongoDB client
 * @param definition - Retriever definition with configuration
 */
function configureRetriever(
  ai: Genkit,
  client: MongoClient,
  definition: BaseDefinition
) {
  return ai.defineRetriever(
    {
      name: `mongodb/${definition.id}`,
      configSchema: RetrieverOptionsSchema,
    },
    async (document: Document, options: RetrieverOptions) => {
      try {
        const parsedOptions = validateRetrieverOptions(options);

        const collection = getCollection(
          client,
          parsedOptions.dbName,
          parsedOptions.collectionName,
          parsedOptions.dbOptions,
          parsedOptions.collectionOptions
        );
        return await retrieve(
          ai,
          collection,
          document,
          parsedOptions,
          definition.retry
        );
      } catch (error) {
        throw new Error(
          `Mongo retrieval failed: ${error instanceof Error ? error.message : 'Unknown error'}`
        );
      }
    }
  );
}

/**
 * Defines a MongoDB retriever for the Genkit AI framework.
 *
 * @param ai - Genkit AI instance
 * @param client - MongoDB client
 * @param definition - Optional retriever definition
 */
export function defineRetriever(
  ai: Genkit,
  client: MongoClient,
  definition?: BaseDefinition
) {
  if (!definition?.id) {
    return;
  }
  configureRetriever(ai, client, definition);
}

/**
 * Creates a reference to a MongoDB retriever.
 *
 * @param id - The retriever identifier
 * @returns A retriever reference that can be used in Genkit operations
 *
 * @example
 * ```typescript
 * const retrieverRef = mongoRetrieverRef('my-retriever');
 * ```
 */
export function mongoRetrieverRef(id: string): ReturnType<typeof retrieverRef> {
  return retrieverRef({
    name: `mongodb/${id}`,
    info: {
      label: `Mongo Retriever - ${id}`,
    },
    configSchema: RetrieverOptionsSchema,
  });
}
