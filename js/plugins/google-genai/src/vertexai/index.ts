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

import {
  EmbedderReference,
  Genkit,
  ModelReference,
  modelActionMetadata,
  z,
} from 'genkit';
import { GenkitPlugin, genkitPlugin } from 'genkit/plugin';
import { ActionType } from 'genkit/registry';
import { listModels } from './client.js';
import {
  KNOWN_EMBEDDER_MODELS,
  VertexEmbeddingConfig,
  VertexEmbeddingConfigSchema,
  defineVertexAIEmbedder,
  embedder,
} from './embedder.js';
import {
  GeminiConfigSchema,
  KNOWN_GEMINI_MODELS,
  SafetySettingsSchema,
  defineGeminiModel,
  gemini,
  type GeminiConfig,
  type GeminiVersionString,
} from './gemini.js';
import {
  ImagenConfigSchema,
  KNOWN_IMAGEN_MODELS,
  defineImagenModel,
  imagen,
} from './imagen.js';
import { Model, PluginOptions } from './types.js';
import { getDerivedOptions } from './utils.js';
export {
  GeminiConfigSchema,
  ImagenConfigSchema,
  SafetySettingsSchema,
  type GeminiConfig,
  type GeminiVersionString,
  type PluginOptions,
};

async function initializer(ai: Genkit, options?: PluginOptions) {
  const clientOptions = await getDerivedOptions(options);

  Object.keys(KNOWN_IMAGEN_MODELS).map((name) =>
    defineImagenModel(ai, name, clientOptions)
  );

  Object.keys(KNOWN_GEMINI_MODELS).map((name) =>
    defineGeminiModel(
      ai,
      name,
      clientOptions,
      options?.experimental_debugTraces
    )
  );

  Object.keys(KNOWN_EMBEDDER_MODELS).map((name) =>
    defineVertexAIEmbedder(ai, name, clientOptions)
  );
}

async function resolver(
  ai: Genkit,
  actionType: ActionType,
  actionName: string,
  options?: PluginOptions
) {
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
  const clientOptions = await getDerivedOptions(options);

  if (actionName.startsWith('imagen')) {
    defineImagenModel(ai, actionName, clientOptions);
    return;
  }

  defineGeminiModel(
    ai,
    actionName,
    clientOptions,
    options?.experimental_debugTraces
  );
}

async function resolveEmbedder(
  ai: Genkit,
  actionName: string,
  options?: PluginOptions
) {
  const clientOptions = await getDerivedOptions(options);

  defineVertexAIEmbedder(ai, actionName, clientOptions);
}

// Vertex AI list models still returns these and the API does not indicate in any way
// that those models are not served anymore.
const KNOWN_DECOMISSIONED_MODELS = [
  'gemini-pro-vision',
  'gemini-pro',
  'gemini-ultra',
  'gemini-ultra-vision',
];

async function listActions(options?: PluginOptions) {
  const clientOptions = await getDerivedOptions(options);
  try {
    const models = await listModels(clientOptions);
    // Vertex has a lot of models, and no way to figure out the "type" of the model...
    // so, for list actions we only fetch known model "families".
    return [
      // Gemini
      ...models
        .filter(
          (m: Model) =>
            m.name.includes('gemini') &&
            !m.name.includes('embedding') &&
            !KNOWN_DECOMISSIONED_MODELS.includes(m.name.split('/').at(-1)!)
        )
        .map((m: Model) => {
          const ref = gemini(m.name);
          return modelActionMetadata({
            name: ref.name,
            info: ref.info,
            configSchema: ref.configSchema,
          });
        }),
      // Imagen
      ...models
        .filter((m: Model) => m.name.includes('imagen'))
        .map((m: Model) => {
          const ref = imagen(m.name);
          return modelActionMetadata({
            name: ref.name,
            info: ref.info,
            configSchema: ref.configSchema,
          });
        }),
    ];
  } catch (e: unknown) {
    // Errors are already logged in the client code.
    return [];
  }
}

/**
 * Add Google Cloud Vertex AI to Genkit. Includes Gemini and Imagen models and text embedder.
 */
function vertexAIPlugin(options?: PluginOptions): GenkitPlugin {
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
  (params?: PluginOptions): GenkitPlugin;
  model(
    name: keyof typeof KNOWN_GEMINI_MODELS | (`gemini-${string}` & {}),
    config?: z.infer<typeof GeminiConfigSchema>
  ): ModelReference<typeof GeminiConfigSchema>;
  model(
    name: keyof typeof KNOWN_IMAGEN_MODELS | (`imagen${string}` & {}),
    config?: z.infer<typeof ImagenConfigSchema>
  ): ModelReference<typeof ImagenConfigSchema>;
  model(name: string, config?: any): ModelReference<z.ZodTypeAny>;
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
// provide generic implementation for the model function overloads.
(vertexAI as any).model = (
  name: string,
  config?: any
): ModelReference<z.ZodTypeAny> => {
  if (name.startsWith('imagen')) {
    return imagen(name, config);
  }
  return gemini(name, config);
};
vertexAI.embedder = (
  name: string,
  config?: VertexEmbeddingConfig
): EmbedderReference<typeof VertexEmbeddingConfigSchema> => {
  return embedder(name, config);
};

export default vertexAI;
