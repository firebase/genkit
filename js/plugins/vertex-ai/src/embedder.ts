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

import { defineEmbedder, embedderRef } from '@genkit-ai/ai/embedders';
import { GoogleAuth } from 'google-auth-library';
import { z } from 'zod';
import { PluginOptions } from '.';
import { predictModel } from './predict';

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
  taskType: TaskTypeSchema,
});
export type TextEmbeddingGeckoConfig = z.infer<
  typeof TextEmbeddingGeckoConfigSchema
>;

const TextEmbeddingGeckoInputSchema = z.union([
  z.string(),
  z.object({ title: z.string().optional(), content: z.string() }),
]);

export const textEmbeddingGecko = embedderRef({
  name: 'vertex-ai/textembedding-gecko',
  configSchema: TextEmbeddingGeckoConfigSchema,
  info: {
    dimension: 768,
    label: 'Vertex AI - Text Embedding Gecko',
    names: [
      'vertex-ai/textembedding-gecko-002',
      'vertex-ai/textembedding-gecko-003',
      'vertex-ai/textembedding-gecko-multilingual',
      'vertex-ai/textembedding-gecko-multilingual-001',
    ],
    supports: {
      input: ['text'],
    },
  },
});

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
  client: GoogleAuth,
  options: PluginOptions
) {
  // TODO: Figure out how to allow different versions while still sharing a single implementation.
  const predict = predictModel<EmbeddingInstance, EmbeddingPrediction>(
    client,
    options,
    'textembedding-gecko@003'
  );
  return defineEmbedder(
    {
      info: textEmbeddingGecko.info!,
      customOptionsType: TextEmbeddingGeckoConfigSchema,
      inputType: TextEmbeddingGeckoInputSchema,
      embedderId: textEmbeddingGecko.name,
      provider: 'vertex-ai',
    },
    async (input, options) => {
      const instance: EmbeddingInstance =
        typeof input === 'string' ? { content: input } : input;
      if (options?.taskType) {
        instance.task_type = options.taskType;
      }

      const response = await predict([instance]);
      return response.predictions[0].embeddings.values;
    }
  );
}
