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

import { EmbedderReference, ModelReference, z } from 'genkit';
import { GenkitPluginV2, genkitPluginV2 } from 'genkit/plugin';

import * as embedder from './embedder.js';
import * as gemini from './gemini.js';
import * as imagen from './imagen.js';
import * as lyria from './lyria.js';
import * as veo from './veo.js';

import { ActionType } from 'genkit/registry';
import { listModels } from './client.js';
import { VertexPluginOptions } from './types.js';
import { getDerivedOptions } from './utils.js';

export { type EmbeddingConfig } from './embedder.js';
export { type GeminiConfig } from './gemini.js';
export { type ImagenConfig } from './imagen.js';
export { type LyriaConfig } from './lyria.js';
export { type VertexPluginOptions } from './types.js';
export { type VeoConfig } from './veo.js';

async function initializer(pluginOptions?: VertexPluginOptions) {
  const clientOptions = await getDerivedOptions(pluginOptions);

  return [
    ...imagen.defineKnownModels(clientOptions, pluginOptions),
    ...gemini.defineKnownModels(clientOptions, pluginOptions),
    ...embedder.defineKnownModels(clientOptions, pluginOptions),
  ];
}

async function resolver(
  actionType: ActionType,
  actionName: string,
  pluginOptions?: VertexPluginOptions
) {
  const clientOptions = await getDerivedOptions(pluginOptions);
  switch (actionType) {
    case 'model':
      if (imagen.isImagenModelName(actionName)) {
        return imagen.defineModel(actionName, clientOptions, pluginOptions);
      } else {
        return gemini.defineModel(actionName, clientOptions, pluginOptions);
      }
    case 'embedder':
      return embedder.defineEmbedder(actionName, clientOptions, pluginOptions);
    default:
      return undefined;
  }
}

async function listActions(options?: VertexPluginOptions) {
  const clientOptions = await getDerivedOptions(options);
  try {
    const models = await listModels(clientOptions);
    return [
      ...gemini.listActions(models),
      ...imagen.listActions(models),
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
function vertexAIPlugin(options?: VertexPluginOptions): GenkitPluginV2 {
  let listActionsCache;
  return genkitPluginV2({
    name: 'vertexai',
    init: async () => await initializer(options),
    resolve: async (actionType: ActionType, actionName: string) =>
      await resolver(actionType, actionName, options),
    list: async () => {
      if (listActionsCache) return listActionsCache;
      listActionsCache = await listActions(options);
      return listActionsCache;
    },
  });
}

export type VertexAIPlugin = {
  (pluginOptions?: VertexPluginOptions): GenkitPluginV2;
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
    return imagen.createModelRef(name, config);
  }
  if (lyria.isLyriaModelName(name)) {
    return lyria.createModelRef(name, config);
  }
  if (veo.isVeoModelName(name)) {
    return veo.createModelRef(name, config);
  }
  // gemini and unknown model families
  return gemini.createModelRef(name, config);
};
vertexAI.embedder = (
  name: string,
  config?: embedder.EmbeddingConfig
): EmbedderReference<embedder.EmbeddingConfigSchemaType> => {
  return embedder.createEmbedderRef(name, config);
};

export default vertexAI;
