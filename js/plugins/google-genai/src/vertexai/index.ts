/**
 * @license
 *
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

/**
 * @module /
 */

import { EmbedderReference, Genkit, ModelReference, z } from 'genkit';
import { GenkitPlugin, genkitPlugin } from 'genkit/plugin';
import { ActionType } from 'genkit/registry';
import { listModels } from './client.js';

import * as embedder from './embedder.js';
import * as gemini from './gemini.js';
import * as imagen from './imagen.js';
import * as lyria from './lyria.js';
import * as veo from './veo.js';

import { VertexPluginOptions } from './types.js';
import { getDerivedOptions } from './utils.js';

export { type EmbeddingConfig } from './embedder.js';
export { type GeminiConfig } from './gemini.js';
export { type ImagenConfig } from './imagen.js';
export { type LyriaConfig } from './lyria.js';
export { type VertexPluginOptions } from './types.js';
export { type VeoConfig } from './veo.js';

async function initializer(ai: Genkit, pluginOptions?: VertexPluginOptions) {
  const clientOptions = await getDerivedOptions(pluginOptions);
  veo.defineKnownModels(ai, clientOptions, pluginOptions);
  imagen.defineKnownModels(ai, clientOptions, pluginOptions);
  lyria.defineKnownModels(ai, clientOptions, pluginOptions);
  gemini.defineKnownModels(ai, clientOptions, pluginOptions);
  embedder.defineKnownModels(ai, clientOptions, pluginOptions);
}

async function resolver(
  ai: Genkit,
  actionType: ActionType,
  actionName: string,
  pluginOptions?: VertexPluginOptions
) {
  const clientOptions = await getDerivedOptions(pluginOptions);
  switch (actionType) {
    case 'model':
      if (lyria.isLyriaModelName(actionName)) {
        lyria.defineModel(ai, actionName, clientOptions, pluginOptions);
      } else if (imagen.isImagenModelName(actionName)) {
        imagen.defineModel(ai, actionName, clientOptions, pluginOptions);
      } else if (veo.isVeoModelName(actionName)) {
        // no-op (not gemini)
      } else {
        gemini.defineModel(ai, actionName, clientOptions, pluginOptions);
      }
      break;
    case 'background-model':
      if (veo.isVeoModelName(actionName)) {
        veo.defineModel(ai, actionName, clientOptions, pluginOptions);
      }
      break;
    case 'embedder':
      embedder.defineEmbedder(ai, actionName, clientOptions, pluginOptions);
      break;
    default:
    // no-op
  }
}

async function listActions(options?: VertexPluginOptions) {
  try {
    const clientOptions = await getDerivedOptions(options);
    const models = await listModels(clientOptions);
    return [
      ...gemini.listActions(models),
      ...imagen.listActions(models),
      ...lyria.listActions(models),
      ...veo.listActions(models),
      // We don't list embedders here
    ];
  } catch (e: unknown) {
    // Errors are already logged in the client code.
    return [];
  }
}

/**
 * Add Google Cloud Vertex AI to Genkit. Includes Gemini and Imagen models and text embedder.
 */
function vertexAIPlugin(options?: VertexPluginOptions): GenkitPlugin {
  let listActionsCache;
  return genkitPlugin(
    'vertexai',
    async (ai: Genkit) => await initializer(ai, options),
    async (ai: Genkit, actionType: ActionType, actionName: string) =>
      await resolver(ai, actionType, actionName, options),
    async () => {
      if (listActionsCache) return listActionsCache;
      listActionsCache = await listActions(options);
      return listActionsCache;
    }
  );
}

export type VertexAIPlugin = {
  (pluginOptions?: VertexPluginOptions): GenkitPlugin;
  model(
    name: gemini.KnownModels | (gemini.GeminiModelName & {}),
    config?: gemini.GeminiConfig
  ): ModelReference<gemini.GeminiConfigSchemaType>;
  model(
    name: imagen.KnownModels | (imagen.ImagenModelName & {}),
    config?: imagen.ImagenConfig
  ): ModelReference<imagen.ImagenConfigSchemaType>;
  model(
    name: lyria.KnownModels | (lyria.LyriaModelName & {}),
    config: lyria.LyriaConfig
  ): ModelReference<lyria.LyriaConfigSchemaType>;
  model(
    name: veo.KnownModels | (veo.VeoModelName & {}),
    config: veo.VeoConfig
  ): ModelReference<veo.VeoConfigSchemaType>;
  model(name: string, config?: any): ModelReference<z.ZodTypeAny>;

  embedder(
    name: string,
    config?: embedder.EmbeddingConfig
  ): EmbedderReference<embedder.EmbeddingConfigSchemaType>;
};

/**
 * Google Cloud Vertex AI plugin for Genkit.
 * Includes Gemini and Imagen models and text embedder.
 */
export const vertexAI = vertexAIPlugin as VertexAIPlugin;
// provide generic implementation for the model function overloads.
(vertexAI as any).model = (
  name: string,
  config?: any
): ModelReference<z.ZodTypeAny> => {
  if (imagen.isImagenModelName(name)) {
    return imagen.model(name, config);
  }
  if (lyria.isLyriaModelName(name)) {
    return lyria.model(name, config);
  }
  if (veo.isVeoModelName(name)) {
    return veo.model(name, config);
  }
  // gemini and unknown model families
  return gemini.model(name, config);
};
vertexAI.embedder = (
  name: string,
  config?: embedder.EmbeddingConfig
): EmbedderReference<embedder.EmbeddingConfigSchemaType> => {
  return embedder.model(name, config);
};

export default vertexAI;
