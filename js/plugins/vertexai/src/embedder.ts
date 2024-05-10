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
  defineEmbedder,
  embedderRef,
  EmbedderReference,
} from '@genkit-ai/ai/embedder';
import { GoogleAuth } from 'google-auth-library';
import { z } from 'zod';
import { PluginOptions } from './index.js';
import { predictModel } from './predict.js';

export const TaskTypeSchema = z.enum([
  'RETRIEVAL_DOCUMENT',
  'RETRIEVAL_QUERY',
  'SEMANTIC_SIMILARITY',
  'CLASSIFICATION',
  'CLUSTERING',
]);
export type TaskType = z.infer<typeof TaskTypeSchema>;

export const TextEmbeddingGeckoConfigSchema = z.object({
  /**
   * The `task_type` parameter is defined as the intended downstream application to help the model
   * produce better quality embeddings.
   **/
  taskType: TaskTypeSchema.optional(),
  title: z.string().optional(),
});
export type TextEmbeddingGeckoConfig = z.infer<
  typeof TextEmbeddingGeckoConfigSchema
>;

export const textEmbeddingGecko003 = embedderRef({
  name: 'vertexai/textembedding-gecko@003',
  configSchema: TextEmbeddingGeckoConfigSchema,
  info: {
    dimensions: 768,
    label: 'Vertex AI - Text Embedding Gecko',
    supports: {
      input: ['text'],
    },
  },
});

export const textEmbeddingGecko002 = embedderRef({
  name: 'vertexai/textembedding-gecko@002',
  configSchema: TextEmbeddingGeckoConfigSchema,
  info: {
    dimensions: 768,
    label: 'Vertex AI - Text Embedding Gecko',
    supports: {
      input: ['text'],
    },
  },
});

export const textEmbeddingGecko001 = embedderRef({
  name: 'vertexai/textembedding-gecko@001',
  configSchema: TextEmbeddingGeckoConfigSchema,
  info: {
    dimensions: 768,
    label: 'Vertex AI - Text Embedding Gecko (Legacy)',
    supports: {
      input: ['text'],
    },
  },
});

/*
// @TODO(huangjeff): Fix multilingual text embedding gecko
// For some reason this model returns 404 but it exists in the reference docs:
// https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-text-embeddings

export const textEmbeddingGeckoMultilingual001 = embedderRef({
  name: 'vertexai/textembedding-gecko-multilingual@001',
  configSchema: TextEmbeddingGeckoConfigSchema,
  info: {
    dimensions: 768,
    label: 'Vertex AI - Multilingual Text Embedding Gecko',
    supports: {
      input: ['text'],
    },
  },
});
*/

export const textEmbeddingGecko = textEmbeddingGecko003;

export const SUPPORTED_EMBEDDER_MODELS: Record<string, EmbedderReference> = {
  'textembedding-gecko@003': textEmbeddingGecko003,
  'textembedding-gecko@002': textEmbeddingGecko002,
  'textembedding-gecko@001': textEmbeddingGecko001,
  //'textembeddding-gecko-multilingual@001': textEmbeddingGeckoMultilingual001,
};

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

export function textEmbeddingGeckoEmbedder(
  name: string,
  client: GoogleAuth,
  options: PluginOptions
) {
  const embedder = SUPPORTED_EMBEDDER_MODELS[name];
  // TODO: Figure out how to allow different versions while still sharing a single implementation.
  const predict = predictModel<EmbeddingInstance, EmbeddingPrediction>(
    client,
    options,
    name
  );
  return defineEmbedder(
    {
      name: embedder.name,
      configSchema: embedder.configSchema,
      info: embedder.info!,
    },
    async (input, options) => {
      const response = await predict(
        input.map((i) => {
          return {
            content: i.text(),
            task_type: options?.taskType,
            title: options?.title,
          };
        })
      );
      return {
        embeddings: response.predictions.map((p) => ({
          embedding: p.embeddings.values,
        })),
      };
    }
  );
}
