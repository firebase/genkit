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
import { GenkitPlugin, genkitPlugin } from 'genkit/plugin';
import { getDerivedParams } from '../common/index.js';
import { PluginOptions } from './types.js';
import { vertexAiIndexers, vertexAiRetrievers } from './vector_search/index.js';
export { PluginOptions } from '../common/types.js';
export {
  DocumentIndexer,
  DocumentRetriever,
  Neighbor,
  VectorSearchOptions,
  getBigQueryDocumentIndexer,
  getBigQueryDocumentRetriever,
  getFirestoreDocumentIndexer,
  getFirestoreDocumentRetriever,
  vertexAiIndexerRef,
  vertexAiIndexers,
  vertexAiRetrieverRef,
  vertexAiRetrievers,
} from './vector_search/index.js';
/**
 * Add Google Cloud Vertex AI to Genkit. Includes Gemini and Imagen models and text embedder.
 */
export function vertexAIVectorSearch(options?: PluginOptions): GenkitPlugin {
  return genkitPlugin('vertexAIVectorSearch', async (ai: Genkit) => {
    const { authClient } = await getDerivedParams(options);

    if (
      options?.vectorSearchOptions &&
      options.vectorSearchOptions.length > 0
    ) {
      vertexAiIndexers(ai, {
        pluginOptions: options,
        authClient,
        defaultEmbedder: options.embedder,
      });

      vertexAiRetrievers(ai, {
        pluginOptions: options,
        authClient,
        defaultEmbedder: options.embedder,
      });
    }
  });
}
