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

import { genkitPlugin, Plugin, z } from 'genkit';
import { IndexerAction, RetrieverAction } from 'genkit/retriever';
import { authenticate } from '../common/auth.js';
import { confError, DEFAULT_LOCATION } from '../common/global.js';
import { BasePluginOptions } from '../common/types';
import {
  SUPPORTED_EMBEDDER_MODELS,
  textEmbeddingGeckoEmbedder,
} from '../embedder.js';
import {
  getBigQueryDocumentIndexer,
  getBigQueryDocumentRetriever,
} from './bigquery';
import {
  getFirestoreDocumentIndexer,
  getFirestoreDocumentRetriever,
} from './firestore';
import { vertexAiIndexerRef, vertexAiIndexers } from './indexers';
import { vertexAiRetrieverRef, vertexAiRetrievers } from './retrievers';
import {
  DocumentIndexer,
  DocumentRetriever,
  Neighbor,
  VectorSearchOptions,
  VertexAIVectorIndexerOptions,
  VertexAIVectorIndexerOptionsSchema,
  VertexAIVectorRetrieverOptions,
  VertexAIVectorRetrieverOptionsSchema,
} from './types';

export {
  DocumentIndexer,
  DocumentRetriever,
  getBigQueryDocumentIndexer,
  getBigQueryDocumentRetriever,
  getFirestoreDocumentIndexer,
  getFirestoreDocumentRetriever,
  Neighbor,
  VectorSearchOptions,
  vertexAiIndexerRef,
  vertexAiIndexers,
  vertexAiRetrieverRef,
  vertexAiRetrievers,
  VertexAIVectorIndexerOptions,
  VertexAIVectorIndexerOptionsSchema,
  VertexAIVectorRetrieverOptions,
  VertexAIVectorRetrieverOptionsSchema,
};

export interface PluginOptions extends BasePluginOptions {
  /** Configure Vertex AI vector search index options */
  options?: VectorSearchOptions<z.ZodTypeAny, any, any>[];
}

/**
 *  Plugin for Vertex AI Vector Search
 */
export const vertexAIVectorSearch: Plugin<[PluginOptions] | []> = genkitPlugin(
  'vertexAiVectorSearch',
  async (options?: PluginOptions) => {
    // Authenticate with Google Cloud
    const authOptions = options?.googleAuth;
    const authClient = authenticate(authOptions);

    const projectId = options?.projectId || (await authClient.getProjectId());
    const location = options?.location || DEFAULT_LOCATION;

    if (!location) {
      throw confError('location', 'GCLOUD_LOCATION');
    }
    if (!projectId) {
      throw confError('project', 'GCLOUD_PROJECT');
    }

    const embedders = Object.keys(SUPPORTED_EMBEDDER_MODELS).map((name) =>
      textEmbeddingGeckoEmbedder(name, authClient, { projectId, location })
    );

    let indexers: IndexerAction<z.ZodTypeAny>[] = [];
    let retrievers: RetrieverAction<z.ZodTypeAny>[] = [];

    if (options?.options && options.options.length > 0) {
      const defaultEmbedder = embedders[0];

      indexers = vertexAiIndexers({
        pluginOptions: options,
        authClient,
        defaultEmbedder,
      });

      retrievers = vertexAiRetrievers({
        pluginOptions: options,
        authClient,
        defaultEmbedder,
      });
    }

    return {
      indexers,
      retrievers,
    };
  }
);

export default vertexAIVectorSearch;
