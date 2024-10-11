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

import { VertexAI } from '@google-cloud/vertexai';
import { genkitPlugin, Plugin, z } from 'genkit';
import { GenerateRequest } from 'genkit/model';
import { IndexerAction, RetrieverAction } from 'genkit/retriever';
import { authenticate } from './common/auth.js';
import { confError, DEFAULT_LOCATION } from './common/global.js';
import { BasePluginOptions } from './common/types.js';
import {
  SUPPORTED_EMBEDDER_MODELS,
  textEmbedding004,
  textEmbeddingGecko,
  textEmbeddingGecko001,
  textEmbeddingGecko002,
  textEmbeddingGecko003,
  textEmbeddingGeckoEmbedder,
  textEmbeddingGeckoMultilingual001,
  textMultilingualEmbedding002,
} from './embedder.js';
import {
  VertexAIEvaluationMetric,
  VertexAIEvaluationMetricType,
  vertexEvaluators,
} from './evaluation.js';
import {
  gemini15Flash,
  gemini15FlashPreview,
  gemini15Pro,
  gemini15ProPreview,
  GeminiConfigSchema,
  geminiModel,
  geminiPro,
  geminiProVision,
  SUPPORTED_GEMINI_MODELS,
} from './gemini.js';
import {
  imagen2,
  imagen3,
  imagen3Fast,
  imagenModel,
  SUPPORTED_IMAGEN_MODELS,
} from './imagen.js';
import { vertexAiRerankers, VertexRerankerConfig } from './reranker.js';
import {
  VectorSearchOptions,
  vertexAiIndexers,
  vertexAiRetrievers,
} from './vector-search';
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
} from './vector-search';

export {
  gemini15Flash,
  gemini15FlashPreview,
  gemini15Pro,
  gemini15ProPreview,
  geminiPro,
  geminiProVision,
  imagen2,
  imagen3,
  imagen3Fast,
  textEmbedding004,
  textEmbeddingGecko,
  textEmbeddingGecko001,
  textEmbeddingGecko002,
  textEmbeddingGecko003,
  textEmbeddingGeckoMultilingual001,
  textMultilingualEmbedding002,
  VertexAIEvaluationMetricType as VertexAIEvaluationMetricType,
};

export interface PluginOptions extends BasePluginOptions {
  /** Configure Vertex AI evaluators */
  evaluation?: {
    metrics: VertexAIEvaluationMetric[];
  };
  /** Configure Vertex AI vector search index options */
  vectorSearchOptions?: VectorSearchOptions<z.ZodTypeAny, any, any>[];
  /** Configure reranker options */
  rerankOptions?: VertexRerankerConfig[];
}

const PLUGIN_NAME = 'vertexai';

/**
 * Add Google Cloud Vertex AI to Genkit. Includes Gemini and Imagen models and text embedder.
 */
export const vertexAI: Plugin<[PluginOptions] | []> = genkitPlugin(
  PLUGIN_NAME,
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

    const vertexClientFactoryCache: Record<string, VertexAI> = {};
    const vertexClientFactory = (
      request: GenerateRequest<typeof GeminiConfigSchema>
    ): VertexAI => {
      const requestLocation = request.config?.location || location;
      if (!vertexClientFactoryCache[requestLocation]) {
        vertexClientFactoryCache[requestLocation] = new VertexAI({
          project: projectId,
          location: requestLocation,
          googleAuthOptions: authOptions,
        });
      }
      return vertexClientFactoryCache[requestLocation];
    };
    const metrics =
      options?.evaluation && options.evaluation.metrics.length > 0
        ? options.evaluation.metrics
        : [];

    const models = [
      ...Object.keys(SUPPORTED_IMAGEN_MODELS).map((name) =>
        imagenModel(name, authClient, { projectId, location })
      ),
      ...Object.keys(SUPPORTED_GEMINI_MODELS).map((name) =>
        geminiModel(name, vertexClientFactory, { projectId, location })
      ),
    ];

    const embedders = Object.keys(SUPPORTED_EMBEDDER_MODELS).map((name) =>
      textEmbeddingGeckoEmbedder(name, authClient, { projectId, location })
    );

    let indexers: IndexerAction<z.ZodTypeAny>[] = [];
    let retrievers: RetrieverAction<z.ZodTypeAny>[] = [];

    if (
      options?.vectorSearchOptions &&
      options.vectorSearchOptions.length > 0
    ) {
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

    const rerankOptions = {
      pluginOptions: options,
      authClient,
      projectId,
    };

    const rerankers = await vertexAiRerankers(rerankOptions);

    return {
      models,
      embedders,
      evaluators: vertexEvaluators(authClient, metrics, projectId, location),
      retrievers,
      indexers,
      rerankers,
    };
  }
);

export default vertexAI;
