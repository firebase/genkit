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

import { GenerateRequest, ModelReference } from '@genkit-ai/ai/model';
import { IndexerAction, RetrieverAction } from '@genkit-ai/ai/retriever';
import { Plugin, genkitPlugin } from '@genkit-ai/core';
import { VertexAI } from '@google-cloud/vertexai';
import { embed, GenkitError, genkitPlugin, Plugin, z } from 'genkit';
import { GenerateRequest, ModelReference } from 'genkit/model';
import { IndexerAction, RetrieverAction } from 'genkit/retriever';
import { GoogleAuth, GoogleAuthOptions } from 'google-auth-library';
import { VertexAIEvaluationMetric } from './evaluation.js';
import { GeminiConfigSchema } from './gemini.js';
import { VertexRerankerConfig } from './reranker.js';
import {
  DocumentIndexer,
  DocumentRetriever,
  Neighbor,
  VectorSearchOptions,
} from './vector-search';

let getBigQueryDocumentIndexerExport;
let getBigQueryDocumentRetrieverExport;
let getFirestoreDocumentIndexerExport;
let getFirestoreDocumentRetrieverExport;
let vertexAiIndexerRefExport;
let vertexAiIndexersExport;
let vertexAiRetrieverRefExport;
let vertexAiRetrieversExport;

let claude35SonnetExport;
let claude3HaikuExport;
let claude3OpusExport;
let claude3SonnetExport;
let gemini15FlashExport;
let gemini15FlashPreviewExport;
let gemini15ProExport;
let gemini15ProPreviewExport;
let geminiProExport;
let geminiProVisionExport;
let imagen2Export;
let imagen3Export;
let imagen3FastExport;
let llama3Export;
let llama31Export;
let llama32Export;
let textEmbedding004Export;
let textEmbeddingGeckoExport;
let textEmbeddingGecko001Export;
let textEmbeddingGecko002Export;
let textEmbeddingGecko003Export;
let textEmbeddingGeckoMultilingual001Export;
let textMultilingualEmbedding002Export;
let VertexAIEvaluationMetricTypeExport;

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
  excludeModelGarden?: boolean;
  excludeGemini?: boolean;
  excludeImagen?: boolean;
  excludeEmbedders?: boolean;
  excludeRerankers?: boolean;
  excludeVectorSearch?: boolean;
  excludeEvaluators?: boolean;
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

    authClient = authenticate(authOptions);

    const projectId = options?.projectId || (await authClient.getProjectId());
    const location = options?.location || 'us-central1';
    validate(projectId, location);

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

    const models = await loadModels(projectId, location, options, authClient, vertexClientFactory);
    const embedders = await loadEmbedders(projectId, location, options, authClient);
    const evaluators = await loadEvaluators(projectId, location, options, authClient);
    const { indexers, retrievers } = await loadVectorSearch(projectId, location, options, authClient, embedders);
    const rerankers = await loadRerankers(projectId, location, options, authClient);

    return {
      models,
      embedders,
      evaluators,
      retrievers,
      indexers,
      rerankers,
    };
  }
);

function authenticate(authOptions: GoogleAuthOptions | undefined): GoogleAuth {
  let authClient;

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

  return authClient;
}

function validate(projectId: string, location: string) {
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
}

async function loadModels(
  projectId: string,
  location: string,
  options: PluginOptions | undefined,
  authClient: GoogleAuth,
  vertexClientFactory: any
) {
  const models: any[] = [];

  if (options?.excludeImagen !== true) {
    const {
      imagen2,
      imagen3,
      imagen3Fast,
      imagenModel,
      SUPPORTED_IMAGEN_MODELS,
    } = await import('./imagen.js');

    imagen2Export = imagen2;
    imagen3Export = imagen3;
    imagen3FastExport = imagen3Fast;

    const imagenModels = Object.keys(SUPPORTED_IMAGEN_MODELS).map((name) =>
      imagenModel(name, authClient, { projectId, location })
    );
    models.push(...imagenModels);
  }

  if (options?.excludeGemini !== true) {
    const {
      gemini15Flash,
      gemini15FlashPreview,
      gemini15Pro,
      gemini15ProPreview,
      geminiModel,
      geminiPro,
      geminiProVision,
      SUPPORTED_GEMINI_MODELS,
    } = await import('./gemini.js');

    gemini15FlashExport = gemini15Flash;
    gemini15FlashPreviewExport = gemini15FlashPreview;
    gemini15ProExport = gemini15Pro;
    gemini15ProPreviewExport = gemini15ProPreview;
    geminiProExport = geminiPro;
    geminiProVisionExport = geminiProVision;

    const geminiModels = Object.keys(SUPPORTED_GEMINI_MODELS).map((name) =>
      geminiModel(name, vertexClientFactory, { projectId, location })
    );
    models.push(...geminiModels);
  }

  if (
    options?.excludeModelGarden !== true &&
    (options?.modelGardenModels || options?.modelGarden?.models)
  ) {
    const {
      llama3,
      llama31,
      llama32,
      modelGardenOpenaiCompatibleModel,
      SUPPORTED_OPENAI_FORMAT_MODELS,
    } = await import('./model_garden.js');

    const {
      anthropicModel,
      claude35Sonnet,
      claude3Haiku,
      claude3Opus,
      claude3Sonnet,
      SUPPORTED_ANTHROPIC_MODELS,
    } = await import('./anthropic.js');

    llama3Export = llama3;
    llama31Export = llama31;
    llama32Export = llama32;
    claude35SonnetExport = claude35Sonnet;
    claude3HaikuExport = claude3Haiku;
    claude3OpusExport = claude3Opus;
    claude3SonnetExport = claude3Sonnet;

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

  return models;
}

async function loadEmbedders(
  projectId: string,
  location: string,
  options: PluginOptions | undefined,
  authClient: GoogleAuth,
) {
  let embedders: any[] = [];

  if (options?.excludeEmbedders !== true) {
    const {
      SUPPORTED_EMBEDDER_MODELS,
      textEmbedding004,
      textEmbeddingGecko,
      textEmbeddingGecko001,
      textEmbeddingGecko002,
      textEmbeddingGecko003,
      textEmbeddingGeckoEmbedder,
      textEmbeddingGeckoMultilingual001,
      textMultilingualEmbedding002,
    } = await import('./embedder.js');

    textEmbedding004Export = textEmbedding004;
    textEmbeddingGeckoExport = textEmbeddingGecko;
    textEmbeddingGecko001Export = textEmbeddingGecko001;
    textEmbeddingGecko002Export = textEmbeddingGecko002;
    textEmbeddingGecko003Export = textEmbeddingGecko003;
    textEmbeddingGeckoMultilingual001Export =
      textEmbeddingGeckoMultilingual001;
    textMultilingualEmbedding002Export = textMultilingualEmbedding002;

    embedders.push(
      Object.keys(SUPPORTED_EMBEDDER_MODELS).map((name) =>
        textEmbeddingGeckoEmbedder(name, authClient, { projectId, location })
      )
    );
  }

  return embedders;
}

async function loadEvaluators(projectId: string, location: string, options: PluginOptions | undefined, authClient: GoogleAuth) {
  const metrics =
  options?.evaluation && options.evaluation.metrics.length > 0
    ? options.evaluation.metrics
    : [];
  let evaluators: any = null;

  if (options?.excludeEvaluators && metrics.length > 0) {
    const { vertexEvaluators, VertexAIEvaluationMetricType } = await import(
      './evaluation.js'
    );

    VertexAIEvaluationMetricTypeExport = VertexAIEvaluationMetricType;
    evaluators = vertexEvaluators(authClient, metrics, projectId, location);
  }

  return evaluators;
}

async function loadVectorSearch(
  projectId: string,
  location: string,
  options: PluginOptions | undefined,
  authClient: GoogleAuth,
  embedders: any[]
) {
  let indexers: IndexerAction<z.ZodTypeAny>[] = [];
  let retrievers: RetrieverAction<z.ZodTypeAny>[] = [];

  if (
    options?.excludeVectorSearch !== true &&
    options?.vectorSearchOptions &&
    options.vectorSearchOptions.length > 0
  ) {
    // Embedders are required for vector search
    if (options?.excludeEmbedders !== true) {
      throw new GenkitError({
        status: 'INVALID_ARGUMENT',
        message: "Vector search requires embedders. Please disable the exclusion of embedders."
      })
    }

    const {
      getBigQueryDocumentIndexer,
      getBigQueryDocumentRetriever,
      getFirestoreDocumentIndexer,
      getFirestoreDocumentRetriever,
      vertexAiIndexerRef,
      vertexAiIndexers,
      vertexAiRetrieverRef,
      vertexAiRetrievers,
    } = await import('./vector-search/index.js');

    getBigQueryDocumentIndexerExport = getBigQueryDocumentIndexer;
    getBigQueryDocumentRetrieverExport = getBigQueryDocumentRetriever;
    getFirestoreDocumentIndexerExport = getFirestoreDocumentIndexer;
    getFirestoreDocumentRetrieverExport = getFirestoreDocumentRetriever;
    vertexAiIndexerRefExport = vertexAiIndexerRef;
    vertexAiIndexersExport = vertexAiIndexers;
    vertexAiRetrieverRefExport = vertexAiRetrieverRef;
    vertexAiRetrieversExport = vertexAiRetrievers;

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

  return { indexers, retrievers };
}

async function loadRerankers(projectId: string, location: string, options: PluginOptions | undefined, authClient: GoogleAuth) {
  let rerankers: any = null;

  if (
    options?.excludeRerankers !== true &&
    options?.rerankOptions &&
    options.rerankOptions.length > 0
  ) {
    const { vertexAiRerankers } = await import('./reranker.js');

    const rerankOptions = {
      pluginOptions: options,
      authClient,
      projectId,
    };

    rerankers = await vertexAiRerankers(rerankOptions);
  }

  return rerankers;
}

export {
  claude35SonnetExport as claude35Sonnet,
  claude3HaikuExport as claude3Haiku,
  claude3OpusExport as claude3Opus,
  claude3SonnetExport as claude3Sonnet,
  DocumentIndexer,
  DocumentRetriever,
  gemini15FlashExport as gemini15Flash,
  gemini15FlashPreviewExport as gemini15FlashPreview,
  gemini15ProExport as gemini15Pro,
  gemini15ProPreviewExport as gemini15ProPreview,
  geminiProExport as geminiPro,
  geminiProVisionExport as geminiProVision,
  getBigQueryDocumentIndexerExport as getBigQueryDocumentIndexer,
  getBigQueryDocumentRetrieverExport as getBigQueryDocumentRetriever,
  getFirestoreDocumentIndexerExport as getFirestoreDocumentIndexer,
  getFirestoreDocumentRetrieverExport as getFirestoreDocumentRetriever,
  imagen2Export as imagen2,
  imagen3Export as imagen3,
  imagen3FastExport as imagen3Fast,
  llama3Export as llama3,
  llama31Export as llama31,
  llama32Export as llama32,
  Neighbor,
  textEmbedding004Export as textEmbedding004,
  textEmbeddingGeckoExport as textEmbeddingGecko,
  textEmbeddingGecko001Export as textEmbeddingGecko001,
  textEmbeddingGecko002Export as textEmbeddingGecko002,
  textEmbeddingGecko003Export as textEmbeddingGecko003,
  textEmbeddingGeckoMultilingual001Export as textEmbeddingGeckoMultilingual001,
  textMultilingualEmbedding002Export as textMultilingualEmbedding002,
  VectorSearchOptions,
  VertexAIEvaluationMetricTypeExport as VertexAIEvaluationMetricType,
  vertexAiIndexerRefExport as vertexAiIndexerRef,
  vertexAiIndexersExport as vertexAiIndexers,
  vertexAiRetrieverRefExport as vertexAiRetrieverRef,
  vertexAiRetrieversExport as vertexAiRetrievers,
};

export default vertexAI;
