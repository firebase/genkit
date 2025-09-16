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

import type { Genkit } from 'genkit';
import { genkitPlugin, type GenkitPlugin } from 'genkit/plugin';
import { getDerivedParams } from '../common/index.js';
import type { PluginOptions } from './types.js';
import { vertexAiIndexers, vertexAiRetrievers } from './vector_search/index.js';
export type { PluginOptions } from '../common/types.js';
export {
  getBigQueryDocumentIndexer,
  getBigQueryDocumentRetriever,
  getFirestoreDocumentIndexer,
  getFirestoreDocumentRetriever,
  vertexAiIndexerRef,
  vertexAiIndexers,
  vertexAiRetrieverRef,
  vertexAiRetrievers,
  type DocumentIndexer,
  type DocumentRetriever,
  type Neighbor,
  type VectorSearchOptions,
} from './vector_search/index.js';
/**
 * VertexAI vector search plugin
 *
 * ```ts
 * import { vertexAIVectorSearch } from '@genkit-ai/vertexai/vectorsearch';
 *
 * const ai = genkit({
 *   plugins: [
 *     vertexAI({ ... }),
 *     vertexAIVectorSearch({
        projectId: PROJECT_ID,
        location: LOCATION,
        vectorSearchOptions: [
          {
            publicDomainName: VECTOR_SEARCH_PUBLIC_DOMAIN_NAME,
            indexEndpointId: VECTOR_SEARCH_INDEX_ENDPOINT_ID,
            indexId: VECTOR_SEARCH_INDEX_ID,
            deployedIndexId: VECTOR_SEARCH_DEPLOYED_INDEX_ID,
            documentRetriever: VECTOR_SEARCH_DOCUMENT_RETRIEVER,
            documentIndexer: VECTOR_SEARCH_DOCUMENT_INDEXER,
            embedder: VECTOR_SEARCH_EMBEDDER,
          },
        ],
      }),
 *   ],
 * });
 *
 * const metadata1 = {
 *   restricts: [{
 *     namespace: "colour",
 *     allowList: ["green", "blue, "purple"],
 *     denyList:  ["red", "grey"],
 *   }],
 *   numericRestricts: [
 *   {
 *     namespace: "price",
 *     valueFloat: 4199.99,
 *   },
 *   {
 *     namespace: "weight",
 *     valueDouble: 987.6543,
 *   },
 *   {
 *     namespace: "ports",
 *     valueInt: 3,
 *   },
 * ],
 * }
 * const productDescription1 = "The 'Synapse Slate' seamlessly integrates neural pathways, allowing users to control applications with thought alone. Its holographic display adapts to any environment, projecting interactive interfaces onto any surface."
 * const doc1 = Document.fromText(productDescription1, metadata1);
 *
 * // Index the document along with its restricts and numericRestricts
 * const indexResponse = await ai.index({
 *   indexer: vertexAiIndexerRef({ ... }),
 *   [doc1],
 * });
 *
 *
 * // Later, construct a query using restricts and numeric restricts
 * const queryMetadata = {
 *   restricts: [{
 *     namespace: "colour",
 *     allowList: ["purple"],
 *     denyList: ["red"],
 *   }],
 *   numericRestricts: [{
 *     namespace: "price",
 *     valueFloat: 5000.00,
 *     op: LESS,
 *   }]
 * };
 * const query = "I'm looking for something with a projected display";
 * const queryDoc = new Document(query, queryMetadata);
 *
 * const response = await ai.retrieve({
 *   retriever: vertexAIRetrieverRef({ ... }),
 *   query: queryDocument,
 *   options: { k },
 * });
 *
 * console.log(`response: ${response}`);
 * ```
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
