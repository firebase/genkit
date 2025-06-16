/**
 * Copyright 2024 The Fire Company
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

// import { defineEmbedder, embedderRef } from '@genkit-ai/ai/embedder';

import type { EmbedderReference, Genkit } from 'genkit';
import { z } from 'genkit';
import OpenAI from 'openai';

export const TextEmbeddingConfigSchema = z.object({
  dimensions: z.number().optional(),
  encodingFormat: z.union([z.literal('float'), z.literal('base64')]).optional(),
});
export type TextEmbeddingGeckoConfig = z.infer<
  typeof TextEmbeddingConfigSchema
>;

export function embedderModel(
  ai: Genkit,
  name: string,
  client: OpenAI,
  embedderRef?: EmbedderReference
) {
  return ai.defineEmbedder(
    {
      name,
      configSchema: embedderRef?.configSchema,
      ...embedderRef?.info,
    },
    async (input, options) => {
      const embeddings = await client.embeddings.create({
        model: name,
        input: input.map((d) => d.text),
        dimensions: options?.dimensions,
        encoding_format: options?.encodingFormat,
      });
      return {
        embeddings: embeddings.data.map((d) => ({ embedding: d.embedding })),
      };
    }
  );
}
