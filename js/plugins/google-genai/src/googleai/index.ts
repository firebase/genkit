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

export { type EmbeddingConfig } from './embedder.js';
export { type GeminiConfig, type GeminiTtsConfig } from './gemini.js';
export { type ImagenConfig } from './imagen.js';
export { type GoogleAIPluginOptions };

async function initializer(ai: Genkit, options?: GoogleAIPluginOptions) {
  imagen.defineKnownModels(ai, options);
  gemini.defineKnownModels(ai, options);
  embedder.defineKnownModels(ai, options);
}

async function resolver(
  ai: Genkit,
  actionType: ActionType,
  actionName: string,
  options: GoogleAIPluginOptions
) {
  switch (actionType) {
    case 'model':
      if (imagen.isImagenModelName(actionName)) {
        imagen.defineModel(ai, actionName, options);
      } else {
        gemini.defineModel(ai, actionName, options);
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

// All the known model names for intellisense completion
type KnownModels = gemini.KnownModels | imagen.KnownModels;
type KnownEmbedders = embedder.KnownModels;

export type GoogleAIPlugin = {
  (params?: GoogleAIPluginOptions): GenkitPlugin;
  model<T extends string>(
    name: T | KnownModels,
    // Conditional config types based on name type
    // Order matters - the default gemini should be last
    config?: T extends imagen.ImagenModelName
      ? imagen.ImagenConfig
      : T extends gemini.TTSModelName
        ? gemini.GeminiTtsConfig
        : T extends gemini.GemmaModelName
          ? gemini.GemmaConfig
          : gemini.GeminiConfig
  ): // Conditional return types based on name type (same order as above)
  T extends imagen.ImagenModelName
    ? ModelReference<imagen.ImagenConfigSchemaType>
    : T extends gemini.TTSModelName
      ? ModelReference<gemini.GeminiTtsConfigSchemaType>
      : T extends gemini.GemmaModelName
        ? ModelReference<gemini.GemmaConfigSchemaType>
        : ModelReference<gemini.GeminiConfigSchemaType>;

  embedder<T extends string>(
    name: T | KnownEmbedders,
    config?: embedder.EmbeddingConfig
  ): EmbedderReference<embedder.EmbeddingConfigSchemaType>;
};

// Types for readability below
type ModelConfig =
  | imagen.ImagenConfig
  | gemini.GeminiTtsConfig
  | gemini.GemmaConfig
  | gemini.GeminiConfig;
type EmbedderConfig = embedder.EmbeddingConfig;

type ModelConfigSchemaType =
  | imagen.ImagenConfigSchemaType
  | gemini.GeminiTtsConfigSchemaType
  | gemini.GemmaConfigSchemaType
  | gemini.GeminiConfigSchemaType;
type EmbedderConfigSchemaType = embedder.EmbeddingConfigSchemaType;

/**
 * Google Gemini Developer API plugin.
 */
export const googleAI = googleAIPlugin as GoogleAIPlugin;
(googleAI as any).model = (
  name: string,
  config?: ModelConfig
): ModelReference<ModelConfigSchemaType> => {
  if (imagen.isImagenModelName(name)) {
    return imagen.model(name, config);
  }
  // gemini.model handles gemma, tts and default models
  return gemini.model(name, config);
};
googleAI.embedder = (
  name: string,
  config?: EmbedderConfig
): EmbedderReference<EmbedderConfigSchemaType> => {
  return embedder.model(name, config);
};

export default googleAI;
