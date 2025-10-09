/**
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

import { ActionMetadata, EmbedderReference, ModelReference, z } from 'genkit';
import { logger } from 'genkit/logging';
import {
  GenkitPluginV2,
  ResolvableAction,
  genkitPluginV2,
} from 'genkit/plugin';
import { ActionType } from 'genkit/registry';
import { extractErrMsg } from '../common/utils.js';
import { listModels } from './client.js';
import { GoogleAIPluginOptions } from './types.js';
import { calculateApiKey } from './utils.js';

// These are namespaced because they all intentionally have
// functions of the same name with the same arguments.
// (All exports from these files are used here)
import * as embedder from './embedder.js';
import * as gemini from './gemini.js';
import * as imagen from './imagen.js';
import * as veo from './veo.js';

export { type EmbeddingConfig } from './embedder.js';
export { type GeminiConfig, type GeminiTtsConfig } from './gemini.js';
export { type ImagenConfig } from './imagen.js';
export { type GoogleAIPluginOptions };

async function initializer(options?: GoogleAIPluginOptions) {
  return [
    ...imagen.listKnownModels(options),
    ...gemini.listKnownModels(options),
    ...embedder.listKnownModels(options),
    ...veo.listKnownModels(options),
  ];
}

async function resolver(
  actionType: ActionType,
  actionName: string,
  options: GoogleAIPluginOptions
): Promise<ResolvableAction | undefined> {
  switch (actionType) {
    case 'model':
      if (veo.isVeoModelName(actionName)) {
        return undefined;
      } else if (imagen.isImagenModelName(actionName)) {
        return await imagen.defineModel(actionName, options);
      } else {
        // gemini, tts, gemma, unknown models
        return await gemini.defineModel(actionName, options);
      }
      break;
    case 'background-model':
      if (veo.isVeoModelName(actionName)) {
        return await veo.defineModel(actionName, options);
      }
      break;
    case 'embedder':
      return await embedder.defineEmbedder(actionName, options);
      break;
  }
  return undefined;
}

async function listActions(
  options?: GoogleAIPluginOptions
): Promise<ActionMetadata[]> {
  try {
    const apiKey = calculateApiKey(options?.apiKey, undefined);
    const allModels = await listModels(apiKey, {
      baseUrl: options?.baseUrl,
      apiVersion: options?.apiVersion,
    });

    return [
      ...gemini.listActions(allModels),
      ...imagen.listActions(allModels),
      ...veo.listActions(allModels),
      ...embedder.listActions(allModels),
    ];
  } catch (e: unknown) {
    logger.error(extractErrMsg(e));
    return [];
  }
}

/**
 * Google Gemini Developer API plugin.
 */
export function googleAIPlugin(
  options?: GoogleAIPluginOptions
): GenkitPluginV2 {
  let listActionsCache;
  return genkitPluginV2({
    name: 'googleai',
    init: async () => await initializer(options),
    resolve: async (actionType: ActionType, actionName: string) =>
      await resolver(actionType, actionName, options || {}),
    list: async () => {
      if (listActionsCache) return listActionsCache;
      listActionsCache = await listActions(options);
      return listActionsCache;
    },
  });
}

export type GoogleAIPlugin = {
  (pluginOptions?: GoogleAIPluginOptions): GenkitPluginV2;
  model(
    name: gemini.KnownGemmaModels | (gemini.GemmaModelName & {}),
    config: gemini.GemmaConfig
  ): ModelReference<gemini.GemmaConfigSchemaType>;
  model(
    name: gemini.KnownTtsModels | (gemini.TTSModelName & {}),
    config: gemini.GeminiTtsConfig
  ): ModelReference<gemini.GeminiTtsConfigSchemaType>;
  model(
    name: gemini.KnownGeminiModels | (gemini.GeminiModelName & {}),
    config?: gemini.GeminiConfig
  ): ModelReference<gemini.GeminiConfigSchemaType>;
  model(
    name: imagen.KnownModels | (imagen.ImagenModelName & {}),
    config?: imagen.ImagenConfig
  ): ModelReference<imagen.ImagenConfigSchemaType>;
  model(
    name: veo.KnownModels | (veo.VeoModelName & {}),
    config?: veo.VeoConfig
  ): ModelReference<veo.VeoConfigSchemaType>;
  model(name: string, config?: any): ModelReference<z.ZodTypeAny>;

  embedder(
    name: string,
    config?: embedder.EmbeddingConfig
  ): EmbedderReference<embedder.EmbeddingConfigSchemaType>;
};

/**
 * Google Gemini Developer API plugin.
 */
export const googleAI = googleAIPlugin as GoogleAIPlugin;
(googleAI as any).model = (
  name: string,
  config?: any
): ModelReference<z.ZodTypeAny> => {
  if (veo.isVeoModelName(name)) {
    return veo.model(name, config);
  }
  if (imagen.isImagenModelName(name)) {
    return imagen.model(name, config);
  }
  // gemma, tts, gemini and unknown model families.
  return gemini.model(name, config);
};
googleAI.embedder = (
  name: string,
  config?: embedder.EmbeddingConfig
): EmbedderReference<embedder.EmbeddingConfigSchemaType> => {
  return embedder.model(name, config);
};

export default googleAI;
