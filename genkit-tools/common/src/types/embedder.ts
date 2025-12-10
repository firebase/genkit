/**
 * Copyright 2025 Google LLC
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

import { z } from 'zod';
import { DocumentDataSchema } from './document';

//
// IMPORTANT: Keep this file in sync with genkit/ai/src/embedder.ts!
//

/**
 * A batch (array) of embeddings.
 */
export type EmbeddingBatch = { embedding: number[] }[];

/**
 * EmbeddingSchema includes the embedding and also metadata so you know
 * which of multiple embeddings corresponds to which part of a document.
 */
export const EmbeddingSchema = z.object({
  embedding: z.array(z.number()),
  metadata: z.record(z.string(), z.unknown()).optional(),
});
export type Embedding = z.infer<typeof EmbeddingSchema>;

/**
 * Zod schema of an embed request.
 */
export const EmbedRequestSchema = z.object({
  input: z.array(DocumentDataSchema),
  options: z.any().optional(),
});

/**
 * Zod schema of an embed response.
 */
export const EmbedResponseSchema = z.object({
  embeddings: z.array(EmbeddingSchema),
});
export type EmbedResponse = z.infer<typeof EmbedResponseSchema>;

export const EmbedderSupportsSchema = z.object({
  input: z.array(z.string()).optional(),
  multiturn: z.boolean().optional(),
});
export type EmbedderSupports = z.infer<typeof EmbedderSupportsSchema>;

export const EmbedderInfoSchema = z.object({
  label: z.string().optional(),
  dimensions: z.number().optional(),
  supports: EmbedderSupportsSchema.optional(),
});
export type EmbedderInfo = z.infer<typeof EmbedderInfoSchema>;

export const EmbedderOptionsSchema = z.object({
  label: z.string().optional(),
  dimensions: z.number().optional(),
  supports: EmbedderSupportsSchema.optional(),
  configSchema: z.record(z.any()).optional(),
});
export type EmbedderOptions = z.infer<typeof EmbedderOptionsSchema>;

export const EmbedderRefSchema = z.object({
  name: z.string(),
  info: EmbedderInfoSchema.optional(),
  config: z.any().optional(),
  version: z.string().optional(),
});
export type EmbedderRef = z.infer<typeof EmbedderRefSchema>;
