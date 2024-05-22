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

import { defineEmbedder, embedderRef } from '@genkit-ai/ai/embedder';
import { EmbedContentRequest, GoogleGenerativeAI } from '@google/generative-ai';
import { string, z } from 'zod';
import { PluginOptions } from './index.js';

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
  title: string().optional(),
});

export type TextEmbeddingGeckoConfig = z.infer<
  typeof TextEmbeddingGeckoConfigSchema
>;

export const textEmbeddingGecko001 = embedderRef({
  name: 'googleai/embedding-001',
  configSchema: TextEmbeddingGeckoConfigSchema,
  info: {
    dimensions: 768,
    label: 'Google Gen AI - Text Embedding Gecko (Legacy)',
    supports: {
      input: ['text'],
    },
  },
});

export const SUPPORTED_MODELS = {
  'embedding-001': textEmbeddingGecko001,
};

export function textEmbeddingGeckoEmbedder(
  name: string,
  options: PluginOptions
) {
  let apiKey =
    options?.apiKey ||
    process.env.GOOGLE_GENAI_API_KEY ||
    process.env.GOOGLE_API_KEY;
  if (!apiKey)
    throw new Error(
      'Please pass in the API key or set either GOOGLE_GENAI_API_KEY or GOOGLE_API_KEY environment variable.\n' +
        'For more details see https://firebase.google.com/docs/genkit/plugins/google-genai'
    );
  const client = new GoogleGenerativeAI(apiKey).getGenerativeModel({
    model: name,
  });
  const embedder = SUPPORTED_MODELS[name];
  return defineEmbedder(
    {
      name: embedder.name,
      configSchema: TextEmbeddingGeckoConfigSchema,
      info: embedder.info!,
    },
    async (input, options) => {
      const embeddings = await Promise.all(
        input.map(async (doc) => {
          const response = await client.embedContent({
            taskType: options?.taskType,
            title: options?.title,
            content: {
              role: '',
              parts: [{ text: doc.text() }],
            },
          } as EmbedContentRequest);
          const values = response.embedding.values;
          return { embedding: values };
        })
      );
      return { embeddings };
    }
  );
}
