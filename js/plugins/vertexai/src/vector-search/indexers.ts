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

import { z } from 'genkit';
import { embedMany } from 'genkit/embedder';
import { defineIndexer, IndexerAction, indexerRef } from 'genkit/retriever';
import {
  Datapoint,
  VertexAIVectorIndexerOptionsSchema,
  VertexVectorSearchOptions,
} from './types';
import { upsertDatapoints } from './upsert_datapoints';

/**
 * Creates a reference to a Vertex AI indexer.
 *
 * @param {Object} params - The parameters for the indexer reference.
 * @param {string} params.indexId - The ID of the Vertex AI index.
 * @param {string} [params.displayName] - An optional display name for the indexer.
 * @returns {Object} - The indexer reference object.
 */
export const vertexAiIndexerRef = (params: {
  indexId: string;
  displayName?: string;
}) => {
  return indexerRef({
    name: `vertexai/${params.indexId}`,
    info: {
      label: params.displayName ?? `Vertex AI - ${params.indexId}`,
    },
    configSchema: VertexAIVectorIndexerOptionsSchema.optional(),
  });
};

/**
 * Creates Vertex AI indexers.
 *
 * This function returns a list of indexer actions for Vertex AI based on the provided
 * vector search options and embedder configurations.
 *
 * @param {VertexVectorSearchOptions<EmbedderCustomOptions>} params - The parameters for creating the indexers.
 * @returns {IndexerAction<z.ZodTypeAny>[]} - An array of indexer actions.
 */
export function vertexAiIndexers<EmbedderCustomOptions extends z.ZodTypeAny>(
  params: VertexVectorSearchOptions<EmbedderCustomOptions>
): IndexerAction<z.ZodTypeAny>[] {
  const vectorSearchOptions = params.pluginOptions.vectorSearchOptions;
  const defaultEmbedder = params.defaultEmbedder;
  const indexers: IndexerAction<z.ZodTypeAny>[] = [];

  if (!vectorSearchOptions || vectorSearchOptions.length === 0) {
    return indexers;
  }

  for (const vectorSearchOption of vectorSearchOptions) {
    const { documentIndexer, indexId } = vectorSearchOption;
    const embedder = vectorSearchOption.embedder ?? defaultEmbedder;
    const embedderOptions = vectorSearchOption.embedderOptions;

    const indexer = defineIndexer(
      {
        name: `vertexai/${indexId}`,
        configSchema: VertexAIVectorIndexerOptionsSchema.optional(),
      },
      async (docs, options) => {
        let docIds: string[] = [];

        try {
          docIds = await documentIndexer(docs, options);
        } catch (error) {
          throw new Error(
            `Error storing your document content/metadata: ${error}`
          );
        }

        const embeddings = await embedMany({
          embedder,
          content: docs,
          options: embedderOptions,
        });

        const datapoints = embeddings.map(
          ({ embedding }, i) =>
            new Datapoint({
              datapointId: docIds[i],
              featureVector: embedding,
            })
        );

        try {
          await upsertDatapoints({
            datapoints,
            authClient: params.authClient,
            projectId: params.pluginOptions.projectId!,
            location: params.pluginOptions.location!,
            indexId: indexId,
          });
        } catch (error) {
          throw error;
        }
      }
    );

    indexers.push(indexer);
  }
  return indexers;
}
