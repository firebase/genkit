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
import { getApiKeyFromEnvVar } from './common.js';
import {
  defineGoogleAIEmbedder,
  SUPPORTED_MODELS as EMBEDDER_MODELS,
  GeminiEmbeddingConfig,
  GeminiEmbeddingConfigSchema,
  textEmbedding004,
  textEmbeddingGecko001,
} from './embedder.js';
import {
  defineGoogleAIModel,
  gemini,
  gemini10Pro,
  gemini15Flash,
  gemini15Flash8b,
  gemini15Pro,
  gemini20Flash,
  gemini20FlashExp,
  gemini20FlashLite,
  gemini20ProExp0205,
  gemini25FlashPreview0417,
  gemini25ProExp0325,
  gemini25ProPreview0325,
  GeminiConfigSchema,
  SUPPORTED_V15_MODELS,
  SUPPORTED_V1_MODELS,
  type GeminiConfig,
  type GeminiVersionString,
} from './gemini.js';
import { listModels } from './list-models.js';
export {
  gemini,
  gemini10Pro,
  gemini15Flash,
  gemini15Flash8b,
  gemini15Pro,
  gemini20Flash,
  gemini20FlashExp,
  gemini20FlashLite,
  gemini20ProExp0205,
  gemini25FlashPreview0417,
  gemini25ProExp0325,
  gemini25ProPreview0325,
  textEmbedding004,
  textEmbeddingGecko001,
  type GeminiConfig,
  type GeminiVersionString,
};

export interface PluginOptions {
  /**
   * Provide the API key to use to authenticate with the Gemini API. By
   * default, an API key must be provided explicitly here or through the
   * `GEMINI_API_KEY` or `GOOGLE_API_KEY` environment variables.
   *
   * If `false` is explicitly passed, the plugin will be configured to
   * expect an `apiKey` option to be provided to the model config at
   * call time.
   **/
  apiKey?: string | false;
  apiVersion?: string | string[];
  baseUrl?: string;
  models?: (
    | ModelReference</** @ignore */ typeof GeminiConfigSchema>
    | string
  )[];
  experimental_debugTraces?: boolean;
}

async function initializer(ai: Genkit, options?: PluginOptions) {
  let apiVersions = ['v1'];

  if (options?.apiVersion) {
    if (Array.isArray(options?.apiVersion)) {
      apiVersions = options?.apiVersion;
    } else {
      apiVersions = [options?.apiVersion];
    }
  }

  if (apiVersions.includes('v1beta')) {
    Object.keys(SUPPORTED_V15_MODELS).forEach((name) =>
      defineGoogleAIModel({
        ai,
        name,
        apiKey: options?.apiKey,
        apiVersion: 'v1beta',
        baseUrl: options?.baseUrl,
        debugTraces: options?.experimental_debugTraces,
      })
    );
  }
  if (apiVersions.includes('v1')) {
    Object.keys(SUPPORTED_V1_MODELS).forEach((name) =>
      defineGoogleAIModel({
        ai,
        name,
        apiKey: options?.apiKey,
        apiVersion: undefined,
        baseUrl: options?.baseUrl,
        debugTraces: options?.experimental_debugTraces,
      })
    );
    Object.keys(SUPPORTED_V15_MODELS).forEach((name) =>
      defineGoogleAIModel({
        ai,
        name,
        apiKey: options?.apiKey,
        apiVersion: undefined,
        baseUrl: options?.baseUrl,
        debugTraces: options?.experimental_debugTraces,
      })
    );
    Object.keys(EMBEDDER_MODELS).forEach((name) =>
      defineGoogleAIEmbedder(ai, name, { apiKey: options?.apiKey })
    );
  }

  if (options?.models) {
    for (const modelOrRef of options?.models) {
      const modelName =
        typeof modelOrRef === 'string'
          ? modelOrRef
          : // strip out the `googleai/` prefix
            modelOrRef.name.split('/')[1];
      const modelRef =
        typeof modelOrRef === 'string' ? gemini(modelOrRef) : modelOrRef;
      defineGoogleAIModel({
        ai,
        name: modelName,
        apiKey: options?.apiKey,
        baseUrl: options?.baseUrl,
        info: {
          ...modelRef.info,
          label: `Google AI - ${modelName}`,
        },
        debugTraces: options?.experimental_debugTraces,
      });
    }
  }
}

async function resolver(
  ai: Genkit,
  actionType: ActionType,
  actionName: string,
  options?: PluginOptions
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
  defineGoogleAIModel({
    ai,
    name: modelRef.name,
    apiKey: options?.apiKey,
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
  options?: PluginOptions
) {
  defineGoogleAIEmbedder(ai, `googleai/${actionName}`, {
    apiKey: options?.apiKey,
  });
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

  const models = await listModels(
    options?.baseUrl || 'https://generativelanguage.googleapis.com',
    apiKey
  );

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
          configSchema: GeminiEmbeddingConfigSchema,
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
      await resolver(ai, actionType, actionName, options),
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
  ): EmbedderReference<typeof GeminiEmbeddingConfigSchema>;
};

/**
 * Google Gemini Developer API plugin.
 */
export const googleAI = googleAIPlugin as GoogleAIPlugin;
googleAI.model = (
  name: GeminiVersionString,
  config?: GeminiConfig
): ModelReference<typeof GeminiConfigSchema> => {
  return modelRef({
    name: `googleai/${name}`,
    config,
    configSchema: GeminiConfigSchema,
  });
};
googleAI.embedder = (
  name: string,
  config?: GeminiEmbeddingConfig
): EmbedderReference<typeof GeminiEmbeddingConfigSchema> => {
  return embedderRef({
    name: `googleai/${name}`,
    config,
    configSchema: GeminiEmbeddingConfigSchema,
  });
};

export default googleAI;
