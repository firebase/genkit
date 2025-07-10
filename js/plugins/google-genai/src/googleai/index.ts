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

import {
  ActionMetadata,
  EmbedderReference,
  Genkit,
  ModelReference,
  z,
} from 'genkit';
import { logger } from 'genkit/logging';
import { GenkitPlugin, genkitPlugin } from 'genkit/plugin';
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

async function initializer(ai: Genkit, options?: GoogleAIPluginOptions) {
  imagen.defineKnownModels(ai, options);
  gemini.defineKnownModels(ai, options);
  embedder.defineKnownModels(ai, options);
  veo.defineKnownModels(ai, options);
}

async function resolver(
  ai: Genkit,
  actionType: ActionType,
  actionName: string,
  options: GoogleAIPluginOptions
) {
  switch (actionType) {
    case 'model':
      if (veo.isVeoModelName(actionName)) {
        // no-op (not gemini)
      } else if (imagen.isImagenModelName(actionName)) {
        imagen.defineModel(ai, actionName, options);
      } else {
        // gemini, tts, gemma, unknown models
        gemini.defineModel(ai, actionName, options);
      }
      break;
    case 'background-model':
      if (veo.isVeoModelName(actionName)) {
        veo.defineModel(ai, actionName, options);
      }
      break;
    case 'embedder':
      embedder.defineEmbedder(ai, actionName, options);
      break;
    default:
    // no-op
  }
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
export function googleAIPlugin(options?: GoogleAIPluginOptions): GenkitPlugin {
  let listActionsCache;
  return genkitPlugin(
    'googleai',
    async (ai: Genkit) => await initializer(ai, options),
    async (ai: Genkit, actionType: ActionType, actionName: string) =>
      await resolver(ai, actionType, actionName, options || {}),
    async () => {
      if (listActionsCache) return listActionsCache;
      listActionsCache = await listActions(options);
      return listActionsCache;
    }
  );
}

export type GoogleAIPlugin = {
  (pluginOptions?: GoogleAIPluginOptions): GenkitPlugin;
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
