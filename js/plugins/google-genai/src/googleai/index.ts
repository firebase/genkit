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
  embedderActionMetadata,
  embedderRef,
  EmbedderReference,
  Genkit,
  modelActionMetadata,
  ModelReference,
  z,
} from 'genkit';
import { logger } from 'genkit/logging';
import { modelRef } from 'genkit/model';
import { GenkitPlugin, genkitPlugin } from 'genkit/plugin';
import { ActionType } from 'genkit/registry';
import { listModels } from './client.js';
import {
  defineGoogleAIEmbedder,
  GeminiEmbeddingConfig,
  GoogleAIEmbeddingConfigSchema,
  KNOWN_EMBEDDERS,
} from './embedder.js';
import {
  defineGeminiModel,
  gemini,
  GeminiConfigSchema,
  KNOWN_GEMINI_MODELS,
  type GeminiConfig,
  type GeminiVersionString,
} from './gemini.js';
import { PluginOptions } from './types.js';
import { getApiKeyFromEnvVar } from './utils.js';

export {
  gemini,
  type GeminiConfig,
  type GeminiVersionString,
  type PluginOptions,
};

async function initializer(ai: Genkit, options?: PluginOptions) {
  Object.keys(KNOWN_GEMINI_MODELS).forEach((name) =>
    defineGeminiModel({
      ai,
      name,
      apiKey: options?.apiKey,
      apiVersion: options?.apiVersion,
      baseUrl: options?.baseUrl,
      debugTraces: options?.experimental_debugTraces,
    })
  );

  Object.keys(KNOWN_EMBEDDERS).forEach((name) =>
    defineGoogleAIEmbedder(ai, name, { apiKey: options?.apiKey })
  );
}

async function resolver(
  ai: Genkit,
  actionType: ActionType,
  actionName: string,
  options: PluginOptions
) {
  switch (actionType) {
    case 'model':
      resolveModel(ai, actionName, options);
      break;
    case 'embedder':
      resolveEmbedder(ai, actionName, options);
      break;
    default:
    // no-op
  }
}

function resolveModel(ai: Genkit, actionName: string, options?: PluginOptions) {
  const modelRef = gemini(actionName);
  defineGeminiModel({
    ai,
    name: modelRef.name,
    apiKey: options?.apiKey,
    apiVersion: options?.apiVersion,
    baseUrl: options?.baseUrl,
    info: {
      ...modelRef.info,
      label: `Google AI - ${actionName}`,
    },
    debugTraces: options?.experimental_debugTraces,
  });
}

function resolveEmbedder(
  ai: Genkit,
  actionName: string,
  options: PluginOptions
) {
  defineGoogleAIEmbedder(ai, `googleai/${actionName}`, options);
}

async function listActions(options?: PluginOptions): Promise<ActionMetadata[]> {
  const apiKey = options?.apiKey || getApiKeyFromEnvVar();
  if (!apiKey) {
    // If API key is not configured we don't want to error, just return empty.
    // In practice it will never actually reach this point without the API key,
    // plugin initializer will fail before that.
    logger.error(
      'Pass in the API key or set the GEMINI_API_KEY or GOOGLE_API_KEY environment variable.'
    );
    return [];
  }

  const models = await listModels(apiKey, {
    baseUrl: options?.baseUrl,
    apiVersion: options?.apiVersion,
  });

  return [
    // Models
    ...models
      .filter((m) => m.supportedGenerationMethods.includes('generateContent'))
      // Filter out deprecated
      .filter((m) => !m.description || !m.description.includes('deprecated'))
      .map((m) => {
        const ref = gemini(
          m.name.startsWith('models/')
            ? m.name.substring('models/'.length)
            : m.name
        );

        return modelActionMetadata({
          name: ref.name,
          info: ref.info,
          configSchema: GeminiConfigSchema,
        });
      }),
    // Embedders
    ...models
      .filter((m) => m.supportedGenerationMethods.includes('embedContent'))
      // Filter out deprecated
      .filter((m) => !m.description || !m.description.includes('deprecated'))
      .map((m) => {
        const name =
          'googleai/' +
          (m.name.startsWith('models/')
            ? m.name.substring('models/'.length)
            : m.name);

        return embedderActionMetadata({
          name,
          configSchema: GoogleAIEmbeddingConfigSchema,
          info: {
            dimensions: 768,
            label: `Google Gen AI - ${name}`,
            supports: {
              input: ['text'],
            },
          },
        });
      }),
  ];
}

/**
 * Google Gemini Developer API plugin.
 */
export function googleAIPlugin(options?: PluginOptions): GenkitPlugin {
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
  (params?: PluginOptions): GenkitPlugin;
  model(
    name: GeminiVersionString,
    config?: z.infer<typeof GeminiConfigSchema>
  ): ModelReference<typeof GeminiConfigSchema>;
  embedder(
    name: string,
    config?: GeminiEmbeddingConfig
  ): EmbedderReference<typeof GoogleAIEmbeddingConfigSchema>;
};

/**
 * Google Gemini Developer API plugin.
 */
export const googleAI = googleAIPlugin as GoogleAIPlugin;
googleAI.model = (
  name: GeminiVersionString,
  config?: GeminiConfig
): ModelReference<typeof GeminiConfigSchema> => {
  let modelName = name;
  if (name.startsWith('models/')) {
    modelName = name.substring('models/'.length);
  }
  if (name.startsWith('googleai/')) {
    modelName = name.substring('googleai/'.length);
  }
  return modelRef({
    name: `googleai/${modelName}`,
    config,
    configSchema: GeminiConfigSchema,
  });
};
googleAI.embedder = (
  name: string,
  config?: GeminiEmbeddingConfig
): EmbedderReference<typeof GoogleAIEmbeddingConfigSchema> => {
  let embedderName = name;
  if (name.startsWith('models/')) {
    embedderName = name.substring('models/'.length);
  }
  if (name.startsWith('googleai/')) {
    embedderName = name.substring('googleai/'.length);
  }
  return embedderRef({
    name: `googleai/${embedderName}`,
    config,
    configSchema: GoogleAIEmbeddingConfigSchema,
  });
};

export default googleAI;
