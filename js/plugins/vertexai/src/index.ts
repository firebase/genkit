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
import { GenerateRequest, ModelReference } from 'genkit/model';
import { IndexerAction, RetrieverAction } from 'genkit/retriever';
import { GoogleAuth, GoogleAuthOptions } from 'google-auth-library';
import {
  anthropicModel,
  claude35Sonnet,
  claude3Haiku,
  claude3Opus,
  claude3Sonnet,
  SUPPORTED_ANTHROPIC_MODELS,
} from './anthropic.js';
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
import {
  llama3,
  llama31,
  modelGardenOpenaiCompatibleModel,
  SUPPORTED_OPENAI_FORMAT_MODELS,
} from './model_garden.js';
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
  claude35Sonnet,
  claude3Haiku,
  claude3Opus,
  claude3Sonnet,
  gemini15Flash,
  gemini15FlashPreview,
  gemini15Pro,
  gemini15ProPreview,
  geminiPro,
  geminiProVision,
  imagen2,
  imagen3,
  imagen3Fast,
  llama3,
  llama31,
  textEmbedding004,
  textEmbeddingGecko,
  textEmbeddingGecko001,
  textEmbeddingGecko002,
  textEmbeddingGecko003,
  textEmbeddingGeckoMultilingual001,
  textMultilingualEmbedding002,
  VertexAIEvaluationMetricType as VertexAIEvaluationMetricType,
};

export interface PluginOptions {
  /** The Google Cloud project id to call. */
  projectId?: string;
  /** The Google Cloud region to call. */
  location: string;
  /** Provide custom authentication configuration for connecting to Vertex AI. */
  googleAuth?: GoogleAuthOptions;
  /** Configure Vertex AI evaluators */
  evaluation?: {
    metrics: VertexAIEvaluationMetric[];
  };
  /**
   * @deprecated use `modelGarden.models`
   */
  modelGardenModels?: ModelReference<any>[];
  modelGarden?: {
    models: ModelReference<any>[];
    openAiBaseUrlTemplate?: string;
  };
  /** Configure Vertex AI vector search index options */
  vectorSearchOptions?: VectorSearchOptions<z.ZodTypeAny, any, any>[];
  /** Configure reranker options */
  rerankOptions?: VertexRerankerConfig[];
}

const CLOUD_PLATFROM_OAUTH_SCOPE =
  'https://www.googleapis.com/auth/cloud-platform';

/**
 * Add Google Cloud Vertex AI to Genkit. Includes Gemini and Imagen models and text embedder.
 */
export const vertexAI: Plugin<[PluginOptions] | []> = genkitPlugin(
  'vertexai',
  async (options?: PluginOptions) => {
    let authClient;
    let authOptions = options?.googleAuth;

    // Allow customers to pass in cloud credentials from environment variables
    // following: https://github.com/googleapis/google-auth-library-nodejs?tab=readme-ov-file#loading-credentials-from-environment-variables
    if (process.env.GCLOUD_SERVICE_ACCOUNT_CREDS) {
      const serviceAccountCreds = JSON.parse(
        process.env.GCLOUD_SERVICE_ACCOUNT_CREDS
      );
      authOptions = {
        credentials: serviceAccountCreds,
        scopes: [CLOUD_PLATFROM_OAUTH_SCOPE],
      };
      authClient = new GoogleAuth(authOptions);
    } else {
      authClient = new GoogleAuth(
        authOptions ?? { scopes: [CLOUD_PLATFROM_OAUTH_SCOPE] }
      );
    }

    const projectId = options?.projectId || (await authClient.getProjectId());

    const location = options?.location || 'us-central1';
    const confError = (parameter: string, envVariableName: string) => {
      return new Error(
        `VertexAI Plugin is missing the '${parameter}' configuration. Please set the '${envVariableName}' environment variable or explicitly pass '${parameter}' into genkit config.`
      );
    };
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

    if (options?.modelGardenModels || options?.modelGarden?.models) {
      const mgModels =
        options?.modelGardenModels || options?.modelGarden?.models;
      mgModels!.forEach((m) => {
        const anthropicEntry = Object.entries(SUPPORTED_ANTHROPIC_MODELS).find(
          ([_, value]) => value.name === m.name
        );
        if (anthropicEntry) {
          models.push(anthropicModel(anthropicEntry[0], projectId, location));
          return;
        }
        const openaiModel = Object.entries(SUPPORTED_OPENAI_FORMAT_MODELS).find(
          ([_, value]) => value.name === m.name
        );
        if (openaiModel) {
          models.push(
            modelGardenOpenaiCompatibleModel(
              openaiModel[0],
              projectId,
              location,
              authClient,
              options.modelGarden?.openAiBaseUrlTemplate
            )
          );
          return;
        }
        throw new Error(`Unsupported model garden model: ${m.name}`);
      });
    }

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
