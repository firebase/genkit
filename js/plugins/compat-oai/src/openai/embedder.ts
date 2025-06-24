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

import { embedderRef, z } from 'genkit';

export const TextEmbeddingConfigSchema = z.object({
  dimensions: z.number().optional(),
  encodingFormat: z.union([z.literal('float'), z.literal('base64')]).optional(),
});

export type TextEmbeddingGeckoConfig = z.infer<
  typeof TextEmbeddingConfigSchema
>;

export const TextEmbeddingInputSchema = z.string();

export const textEmbedding3Small = embedderRef({
  name: 'openai/text-embedding-3-small',
  configSchema: TextEmbeddingConfigSchema,
  info: {
    dimensions: 1536,
    label: 'Open AI - Text Embedding 3 Small',
    supports: {
      input: ['text'],
    },
  },
});

export const textEmbedding3Large = embedderRef({
  name: 'openai/text-embedding-3-large',
  configSchema: TextEmbeddingConfigSchema,
  info: {
    dimensions: 3072,
    label: 'Open AI - Text Embedding 3 Large',
    supports: {
      input: ['text'],
    },
  },
});

export const textEmbeddingAda002 = embedderRef({
  name: 'openai/text-embedding-ada-002',
  configSchema: TextEmbeddingConfigSchema,
  info: {
    dimensions: 1536,
    label: 'Open AI - Text Embedding ADA 002',
    supports: {
      input: ['text'],
    },
  },
});

export const SUPPORTED_EMBEDDING_MODELS = {
  'text-embedding-3-small': textEmbedding3Small,
  'text-embedding-3-large': textEmbedding3Large,
  'text-embedding-ada-002': textEmbeddingAda002,
};
