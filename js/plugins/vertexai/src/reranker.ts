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

import {
  defineReranker,
  RankedDocument,
  RerankerAction,
  rerankerRef,
} from '@genkit-ai/ai/reranker';
import { GoogleAuth } from 'google-auth-library';
import z from 'zod';
import { PluginOptions } from '.';

const DEFAULT_MODEL = 'semantic-ranker-512@latest';

const getRerankEndpoint = (projectId: string, location: string) => {
  return `https://discoveryengine.googleapis.com/v1/projects/${projectId}/locations/${location}/rankingConfigs/default_ranking_config:rank`;
};

// Define the schema for the options used in the Vertex AI reranker
export const VertexAIRerankerOptionsSchema = z.object({
  k: z.number().optional().describe('Number of top documents to rerank'), // Optional: Number of documents to rerank
  model: z.string().optional().describe('Model name for reranking'), // Optional: Model name, defaults to a pre-defined model
  location: z
    .string()
    .optional()
    .describe('Google Cloud location, e.g., "us-central1"'), // Optional: Location of the reranking model
});

// Type alias for the options schema
export type VertexAIRerankerOptions = z.infer<
  typeof VertexAIRerankerOptionsSchema
>;

// Define the structure for each individual reranker configuration
export const VertexRerankerConfigSchema = z.object({
  model: z.string().optional().describe('Model name for reranking'), // Optional: Model name, defaults to a pre-defined model
});

export interface VertexRerankerConfig {
  name?: string;
  model?: string;
}

export interface VertexRerankPluginOptions {
  rerankOptions: VertexRerankerConfig[];
  projectId: string;
  location?: string; // Optional: Location of the reranker service
}

export interface VertexRerankOptions {
  authClient: GoogleAuth;
  pluginOptions?: PluginOptions;
}

/**
 * Creates Vertex AI rerankers.
 *
 * This function returns a list of reranker actions for Vertex AI based on the provided
 * rerank options and configuration.
 *
 * @param {VertexRerankOptions<EmbedderCustomOptions>} params - The parameters for creating the rerankers.
 * @returns {RerankerAction<z.ZodTypeAny>[]} - An array of reranker actions.
 */
export function vertexAiRerankers(
  params: VertexRerankOptions
): RerankerAction<z.ZodTypeAny>[] {
  if (!params.pluginOptions) {
    throw new Error(
      'Plugin options are required to create Vertex AI rerankers'
    );
  }
  const pluginOptions = params.pluginOptions;
  if (!params.pluginOptions.rerankOptions) {
    return [];
  }

  const rerankOptions = params.pluginOptions.rerankOptions;
  const rerankers: RerankerAction<z.ZodTypeAny>[] = [];

  if (!rerankOptions || rerankOptions.length === 0) {
    return rerankers;
  }

  for (const rerankOption of rerankOptions) {
    const reranker = defineReranker(
      {
        name: `vertexai/${rerankOption.name || rerankOption.model}`,
        configSchema: VertexAIRerankerOptionsSchema.optional(),
      },
      async (query, documents, _options) => {
        const auth = new GoogleAuth();
        const client = await auth.getClient();
        const projectId = await auth.getProjectId();

        const response = await client.request({
          method: 'POST',
          url: getRerankEndpoint(
            projectId,
            pluginOptions.location ?? 'us-central1'
          ),
          data: {
            model: rerankOption.model || DEFAULT_MODEL, // Use model from config or default
            query: query.text(),
            records: documents.map((doc, idx) => ({
              id: `${idx}`,
              content: doc.text(),
            })),
          },
        });

        const rankedDocuments: RankedDocument[] = (
          response.data as any
        ).records.map((record: any) => {
          const doc = documents[record.id];
          return new RankedDocument({
            content: doc.content,
            metadata: {
              ...doc.metadata,
              score: record.score,
            },
          });
        });

        return { documents: rankedDocuments };
      }
    );

    rerankers.push(reranker);
  }

  return rerankers;
}

/**
 * Creates a reference to a Vertex AI reranker.
 *
 * @param {Object} params - The parameters for the reranker reference.
 * @param {string} [params.displayName] - An optional display name for the reranker.
 * @returns {Object} - The reranker reference object.
 */
export const vertexAiRerankerRef = (params: {
  name: string;
  displayName?: string;
}) => {
  return rerankerRef({
    name: `vertexai/${name}`,
    info: {
      label: params.displayName ?? `Vertex AI Reranker`,
    },
    configSchema: VertexAIRerankerOptionsSchema.optional(),
  });
};
