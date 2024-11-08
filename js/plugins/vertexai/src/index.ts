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
import {
  SUPPORTED_ANTHROPIC_MODELS,
  anthropicModel,
  claude35Sonnet,
  claude35SonnetV2,
  claude3Haiku,
  claude3Opus,
  claude3Sonnet,
} from './anthropic.js';
import { getDerivedParams } from './common/index.js';
import { PluginOptions } from './common/types.js';
import {
  SUPPORTED_EMBEDDER_MODELS,
  defineVertexAIEmbedder,
  textEmbedding004,
  textEmbeddingGecko003,
  textEmbeddingGeckoMultilingual001,
  textMultilingualEmbedding002,
} from './embedder.js';
import {
  VertexAIEvaluationMetricType,
  vertexEvaluators,
} from './evaluation.js';
import {
  SUPPORTED_GEMINI_MODELS,
  defineGeminiModel,
  gemini10Pro,
  gemini15Flash,
  gemini15Pro,
} from './gemini.js';
import {
  SUPPORTED_IMAGEN_MODELS,
  imagen2,
  imagen3,
  imagen3Fast,
  imagenModel,
} from './imagen.js';
import {
  SUPPORTED_OPENAI_FORMAT_MODELS,
  llama3,
  llama31,
  llama32,
  modelGardenOpenaiCompatibleModel,
} from './model_garden.js';
import { vertexAiRerankers } from './reranker.js';
import { vertexAiIndexers, vertexAiRetrievers } from './vector-search/index.js';
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
} from './vector-search/index.js';
export {
  VertexAIEvaluationMetricType as VertexAIEvaluationMetricType,
  claude35Sonnet,
  claude35SonnetV2,
  claude3Haiku,
  claude3Opus,
  claude3Sonnet,
  gemini10Pro,
  gemini15Flash,
  gemini15Pro,
  imagen2,
  imagen3,
  imagen3Fast,
  llama3,
  llama31,
  llama32,
  textEmbedding004,
  textEmbeddingGecko003,
  textEmbeddingGeckoMultilingual001,
  textMultilingualEmbedding002,
};

/**
 * Add Google Cloud Vertex AI to Genkit. Includes Gemini and Imagen models and text embedder.
 */
export function vertexAI(options?: PluginOptions): GenkitPlugin {
  return genkitPlugin('vertexai', async (ai: Genkit) => {
    const { projectId, location, vertexClientFactory, authClient } =
      await getDerivedParams(options);

    const metrics =
      options?.evaluation && options.evaluation.metrics.length > 0
        ? options.evaluation.metrics
        : [];

    Object.keys(SUPPORTED_IMAGEN_MODELS).map((name) =>
      imagenModel(ai, name, authClient, { projectId, location })
    );
    Object.keys(SUPPORTED_GEMINI_MODELS).map((name) =>
      defineGeminiModel(ai, name, vertexClientFactory, { projectId, location })
    );

    if (options?.modelGardenModels || options?.modelGarden?.models) {
      const mgModels =
        options?.modelGardenModels || options?.modelGarden?.models;
      mgModels!.forEach((m) => {
        const anthropicEntry = Object.entries(SUPPORTED_ANTHROPIC_MODELS).find(
          ([_, value]) => value.name === m.name
        );
        if (anthropicEntry) {
          anthropicModel(ai, anthropicEntry[0], projectId, location);
          return;
        }
        const openaiModel = Object.entries(SUPPORTED_OPENAI_FORMAT_MODELS).find(
          ([_, value]) => value.name === m.name
        );
        if (openaiModel) {
          modelGardenOpenaiCompatibleModel(
            ai,
            openaiModel[0],
            projectId,
            location,
            authClient,
            options.modelGarden?.openAiBaseUrlTemplate
          );
          return;
        }
        throw new Error(`Unsupported model garden model: ${m.name}`);
      });
    }

    const embedders = Object.keys(SUPPORTED_EMBEDDER_MODELS).map((name) =>
      defineVertexAIEmbedder(ai, name, authClient, { projectId, location })
    );

    if (
      options?.vectorSearchOptions &&
      options.vectorSearchOptions.length > 0
    ) {
      const defaultEmbedder = embedders[0];

      vertexAiIndexers(ai, {
        pluginOptions: options,
        authClient,
        defaultEmbedder,
      });

      vertexAiRetrievers(ai, {
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
    await vertexAiRerankers(ai, rerankOptions);
    vertexEvaluators(ai, authClient, metrics, projectId, location);
  });
}

export default vertexAI;
