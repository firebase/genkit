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
import {
  Action,
  EmbedderAction,
  genkitPlugin,
  IndexerAction,
  Plugin,
  RerankerAction,
  RetrieverAction,
  z,
} from 'genkit';
import { GenerateRequest, ModelAction, ModelReference } from 'genkit/model';
import { GoogleAuth, GoogleAuthOptions } from 'google-auth-library';
import vertexAiEmbedders from './embedders/index.js';
import { VertexAIEvaluationMetric } from './evaluators/evaluation.js';
import vertexAiEvaluators from './evaluators/index.js';
import { GeminiConfigSchema } from './gemini/gemini.js';
import vertexAiGemini from './gemini/index.js';
import vertexAiImagen from './imagen/index.js';
import vertexAiModelGarden from './modelgarden';
import vertexAiRerankers from './rerankers/index.js';
import { VertexRerankerConfig } from './rerankers/reranker.js';
import vertexAiVectorSearch, { VectorSearchOptions } from './vector-search';

export {
  textEmbedding004,
  textEmbeddingGecko,
  textEmbeddingGecko001,
  textEmbeddingGecko002,
  textEmbeddingGecko003,
  textEmbeddingGeckoEmbedder,
  textEmbeddingGeckoMultilingual001,
  textMultilingualEmbedding002,
} from './embedders';
export { VertexAIEvaluationMetricType } from './evaluators';
export {
  gemini15Flash,
  gemini15FlashPreview,
  gemini15Pro,
  gemini15ProPreview,
  geminiPro,
  geminiProVision,
} from './gemini';
export { imagen2, imagen3, imagen3Fast } from './imagen';
export {
  claude35Sonnet,
  claude3Haiku,
  claude3Opus,
  claude3Sonnet,
  llama3,
  llama31,
  llama32,
} from './modelgarden';
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

    const models = await loadModels(
      projectId,
      location,
      options,
      authClient,
      vertexClientFactory
    );

    const embedders: EmbedderAction[] = [];
    if (options?.excludeEmbedders !== true) {
      const temp = await vertexAiEmbedders(
        projectId,
        location,
        options,
        authClient
      );

      embedders.push(...temp);
    }

    const metrics =
      options?.evaluation && options.evaluation.metrics.length > 0
        ? options.evaluation.metrics
        : [];
    const evaluators: Action[] = [];
    if (options?.excludeEvaluators && metrics.length > 0) {
      const temp = await vertexAiEvaluators(
        projectId,
        location,
        options,
        authClient,
        metrics
      );

      evaluators.push(...temp);
    }

    let indexers: IndexerAction<any>[] = [];
    let retrievers: RetrieverAction<any>[] = [];
    if (
      options?.excludeVectorSearch !== true &&
      options?.vectorSearchOptions &&
      options.vectorSearchOptions.length > 0
    ) {
      const temp = await vertexAiVectorSearch(
        projectId,
        location,
        options,
        authClient,
        embedders
      );

      indexers = temp.indexers;
      retrievers = temp.retrievers;
    }

    const rerankers: RerankerAction[] = [];
    if (
      options?.excludeRerankers !== true &&
      options?.rerankOptions &&
      options.rerankOptions.length > 0
    ) {
      const temp = await vertexAiRerankers(
        projectId,
        location,
        options,
        authClient
      );

      rerankers.push(...temp);
    }

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
  const models: ModelAction<any>[] = [];

  if (options?.excludeGemini !== true) {
    const geminiModels = await vertexAiGemini(
      projectId,
      location,
      options,
      authClient,
      vertexClientFactory
    );
    models.push(...geminiModels);
  }

  if (options?.excludeImagen !== true) {
    const imagenModels = await vertexAiImagen(
      projectId,
      location,
      options,
      authClient
    );
    models.push(...imagenModels);
  }

  if (
    options?.excludeModelGarden !== true &&
    (options?.modelGardenModels || options?.modelGarden?.models)
  ) {
    const modelGardenModels = await vertexAiModelGarden(
      projectId,
      location,
      options,
      authClient
    );
    models.push(...modelGardenModels);
  }

  return models;
}

export default vertexAI;
