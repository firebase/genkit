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

import { Genkit, z } from 'genkit';
import { EmbedderReference, embedderRef } from 'genkit/embedder';
import { GoogleAuth } from 'google-auth-library';
import { PluginOptions } from './common/types.js';
import { PredictClient, predictModel } from './predict.js';

export const TaskTypeSchema = z.enum([
  'RETRIEVAL_DOCUMENT',
  'RETRIEVAL_QUERY',
  'SEMANTIC_SIMILARITY',
  'CLASSIFICATION',
  'CLUSTERING',
]);

export type TaskType = z.infer<typeof TaskTypeSchema>;

export const VertexEmbeddingConfigSchema = z.object({
  /**
   * The `task_type` parameter is defined as the intended downstream application to help the model
   * produce better quality embeddings.
   **/
  taskType: TaskTypeSchema.optional(),
  title: z.string().optional(),
  location: z.string().optional(),
  version: z.string().optional(),
  /**
   * The `dimensions` parameter allows you to specify the dimensionality of the embedding output.
   * By default, the model generates embeddings with 768 dimensions. Models such as
   * `text-embedding-004`, `text-embedding-005`, and `text-multilingual-embedding-002`
   * allow the output dimensionality to be adjusted between 1 and 768.
   * By selecting a smaller output dimensionality, users can save memory and storage space, leading to more efficient computations.
   **/
  dimensions: z.number().min(1).max(768).optional(),
});

export type VertexEmbeddingConfig = z.infer<typeof VertexEmbeddingConfigSchema>;

function commonRef(
  name: string,
  input?: ('text' | 'image')[]
): EmbedderReference<typeof VertexEmbeddingConfigSchema> {
  return embedderRef({
    name: `vertexai/${name}`,
    configSchema: VertexEmbeddingConfigSchema,
    info: {
      dimensions: 768,
      label: `Vertex AI - ${name}`,
      supports: {
        input: input ?? ['text'],
      },
    },
  });
}

export const textEmbeddingGecko003 = commonRef('textembedding-gecko@003');
export const textEmbedding004 = commonRef('text-embedding-004');
export const textEmbedding005 = commonRef('text-embedding-005');
export const textEmbeddingGeckoMultilingual001 = commonRef(
  'textembedding-gecko-multilingual@001'
);
export const textMultilingualEmbedding002 = commonRef(
  'text-multilingual-embedding-002'
);

export const SUPPORTED_EMBEDDER_MODELS: Record<string, EmbedderReference> = {
  'textembedding-gecko@003': textEmbeddingGecko003,
  'text-embedding-004': textEmbedding004,
  'text-embedding-005': textEmbedding005,
  'textembedding-gecko-multilingual@001': textEmbeddingGeckoMultilingual001,
  'text-multilingual-embedding-002': textMultilingualEmbedding002,
  // TODO: add support for multimodal embeddings
  // 'multimodalembedding@001': commonRef('multimodalembedding@001', [
  //   'image',
  //   'text',
  // ]),
};

const customDimensionsSupportedModelNames = [
  textEmbedding004.name,
  textEmbedding005.name,
  textMultilingualEmbedding002.name,
];

interface EmbeddingInstance {
  task_type?: TaskType;
  content: string;
  title?: string;
}
interface EmbeddingPrediction {
  embeddings: {
    statistics: {
      truncated: boolean;
      token_count: number;
    };
    values: number[];
  };
}

export function defineVertexAIEmbedder(
  ai: Genkit,
  name: string,
  client: GoogleAuth,
  options: PluginOptions
) {
  const embedder = SUPPORTED_EMBEDDER_MODELS[name];
  const predictClients: Record<
    string,
    PredictClient<EmbeddingInstance, EmbeddingPrediction>
  > = {};
  const predictClientFactory = (
    config: VertexEmbeddingConfig
  ): PredictClient<EmbeddingInstance, EmbeddingPrediction> => {
    const requestLocation = config?.location || options.location;
    if (!predictClients[requestLocation]) {
      // TODO: Figure out how to allow different versions while still sharing a single implementation.
      predictClients[requestLocation] = predictModel<
        EmbeddingInstance,
        EmbeddingPrediction
      >(
        client,
        {
          ...options,
          location: requestLocation,
        },
        name
      );
    }
    return predictClients[requestLocation];
  };

  return ai.defineEmbedder(
    {
      name: embedder.name,
      configSchema: embedder.configSchema,
      info: embedder.info!,
    },
    async (input, options) => {
      const dimensions =
        customDimensionsSupportedModelNames.includes(embedder.name) &&
        options?.dimensions
          ? options.dimensions
          : undefined;
      const predictClient = predictClientFactory(options);
      const response = await predictClient(
        input.map((i) => {
          return {
            content: i.text,
            task_type: options?.taskType,
            title: options?.title,
          };
        }),
        dimensions ? { outputDimensionality: dimensions } : {}
      );
      return {
        embeddings: response.predictions.map((p) => ({
          embedding: p.embeddings.values,
        })),
      };
    }
  );
}
