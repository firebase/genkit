/**
 * @license
 *
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

/**
 * @module /
 */

import {
  embedderRef,
  EmbedderReference,
  Genkit,
  modelRef,
  ModelReference,
  z,
} from 'genkit';
import { GenkitPlugin, genkitPlugin } from 'genkit/plugin';
import { ActionType } from 'genkit/registry';
import { getDerivedParams } from './common/index.js';
import { PluginOptions } from './common/types.js';
import {
  defineVertexAIEmbedder,
  multimodalEmbedding001,
  SUPPORTED_EMBEDDER_MODELS,
  textEmbedding004,
  textEmbedding005,
  textEmbeddingGecko003,
  textEmbeddingGeckoMultilingual001,
  textMultilingualEmbedding002,
  VertexEmbeddingConfig,
  VertexEmbeddingConfigSchema,
} from './embedder.js';
import {
  defineGeminiKnownModel,
  defineGeminiModel,
  gemini,
  gemini10Pro,
  gemini15Flash,
  gemini15Pro,
  gemini20Flash,
  gemini20Flash001,
  gemini20FlashLite,
  gemini20FlashLitePreview0205,
  gemini20ProExp0205,
  gemini25FlashPreview0417,
  gemini25ProExp0325,
  gemini25ProPreview0325,
  GeminiConfigSchema,
  SUPPORTED_GEMINI_MODELS,
  type GeminiConfig,
  type GeminiVersionString,
} from './gemini.js';
import {
  imagen2,
  imagen3,
  imagen3Fast,
  imagenModel,
  SUPPORTED_IMAGEN_MODELS,
} from './imagen.js';
export { type PluginOptions } from './common/types.js';
export {
  gemini,
  gemini10Pro,
  gemini15Flash,
  gemini15Pro,
  gemini20Flash,
  gemini20Flash001,
  gemini20FlashLite,
  gemini20FlashLitePreview0205,
  gemini20ProExp0205,
  gemini25FlashPreview0417,
  gemini25ProExp0325,
  gemini25ProPreview0325,
  GeminiConfigSchema,
  imagen2,
  imagen3,
  imagen3Fast,
  multimodalEmbedding001,
  textEmbedding004,
  textEmbedding005,
  textEmbeddingGecko003,
  textEmbeddingGeckoMultilingual001,
  textMultilingualEmbedding002,
  type GeminiConfig,
  type GeminiVersionString,
};

async function initializer(ai: Genkit, options?: PluginOptions) {
  const { projectId, location, vertexClientFactory, authClient } =
    await getDerivedParams(options);

  Object.keys(SUPPORTED_IMAGEN_MODELS).map((name) =>
    imagenModel(ai, name, authClient, { projectId, location })
  );
  Object.keys(SUPPORTED_GEMINI_MODELS).map((name) =>
    defineGeminiKnownModel(
      ai,
      name,
      vertexClientFactory,
      {
        projectId,
        location,
      },
      options?.experimental_debugTraces
    )
  );
  if (options?.models) {
    for (const modelOrRef of options?.models) {
      const modelName =
        typeof modelOrRef === 'string'
          ? modelOrRef
          : // strip out the `vertexai/` prefix
            modelOrRef.name.split('/')[1];
      const modelRef =
        typeof modelOrRef === 'string' ? gemini(modelOrRef) : modelOrRef;
      defineGeminiModel({
        ai,
        modelName: modelRef.name,
        version: modelName,
        modelInfo: modelRef.info,
        vertexClientFactory,
        options: {
          projectId,
          location,
        },
        debugTraces: options.experimental_debugTraces,
      });
    }
  }

  Object.keys(SUPPORTED_EMBEDDER_MODELS).map((name) =>
    defineVertexAIEmbedder(ai, name, authClient, { projectId, location })
  );
}

async function resolver(
  ai: Genkit,
  actionType: ActionType,
  actionName: string,
  options?: PluginOptions
) {
  // TODO: also support other actions like 'embedder'
  switch (actionType) {
    case 'model':
      await resolveModel(ai, actionName, options);
      break;
    case 'embedder':
      await resolveEmbedder(ai, actionName, options);
      break;
    default:
    // no-op
  }
}

async function resolveModel(
  ai: Genkit,
  actionName: string,
  options?: PluginOptions
) {
  const { projectId, location, vertexClientFactory } =
    await getDerivedParams(options);
  const modelRef = gemini(actionName);
  defineGeminiModel({
    ai,
    modelName: modelRef.name,
    version: actionName,
    modelInfo: modelRef.info,
    vertexClientFactory,
    options: {
      projectId,
      location,
    },
    debugTraces: options?.experimental_debugTraces,
  });
}

async function resolveEmbedder(
  ai: Genkit,
  actionName: string,
  options?: PluginOptions
) {
  const { projectId, location, authClient } = await getDerivedParams(options);

  defineVertexAIEmbedder(ai, actionName, authClient, { projectId, location });
}

/**
 * Add Google Cloud Vertex AI to Genkit. Includes Gemini and Imagen models and text embedder.
 */
function vertexAIPlugin(options?: PluginOptions): GenkitPlugin {
  return genkitPlugin(
    'vertexai',
    async (ai: Genkit) => await initializer(ai, options),
    async (ai: Genkit, actionType: ActionType, actionName: string) =>
      await resolver(ai, actionType, actionName, options)
  );
}

export type VertexAIPlugin = {
  (params?: PluginOptions): GenkitPlugin;
  model(
    name: GeminiVersionString,
    config?: z.infer<typeof GeminiConfigSchema>
  ): ModelReference<typeof GeminiConfigSchema>;
  embedder(
    name: string,
    config?: VertexEmbeddingConfig
  ): EmbedderReference<typeof VertexEmbeddingConfigSchema>;
};

/**
 * Google Cloud Vertex AI plugin for Genkit.
 * Includes Gemini and Imagen models and text embedder.
 */
export const vertexAI = vertexAIPlugin as VertexAIPlugin;
vertexAI.model = (
  name: GeminiVersionString,
  config?: GeminiConfig
): ModelReference<typeof GeminiConfigSchema> => {
  return modelRef({
    name: `vertexai/${name}`,
    config,
    configSchema: GeminiConfigSchema,
  });
};
vertexAI.embedder = (
  name: string,
  config?: VertexEmbeddingConfig
): EmbedderReference<typeof VertexEmbeddingConfigSchema> => {
  return embedderRef({
    name: `vertexai/${name}`,
    config,
    configSchema: VertexEmbeddingConfigSchema,
  });
};

export default vertexAI;
