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
  embedderActionMetadata,
  embedderRef,
  modelActionMetadata,
  type ActionMetadata,
  type EmbedderReference,
  type ModelReference,
  type z,
} from 'genkit';
import { logger } from 'genkit/logging';
import { modelRef } from 'genkit/model';
import {
  backgroundModel,
  embedder,
  genkitPluginV2,
  model,
  type GenkitPluginV2,
  type ResolvableAction,
} from 'genkit/plugin';
import type { ActionType } from 'genkit/registry';
import { getApiKeyFromEnvVar } from './common.js';
import {
  SUPPORTED_MODELS as EMBEDDER_MODELS,
  GeminiEmbeddingConfigSchema,
  geminiEmbedding001,
  textEmbedding004,
  textEmbeddingGecko001,
  type GeminiEmbeddingConfig,
} from './embedder.js';
import {
  GeminiConfigSchema,
  SUPPORTED_GEMINI_MODELS,
  createGeminiModel,
  gemini,
  gemini10Pro,
  gemini15Flash,
  gemini15Flash8b,
  gemini15Pro,
  gemini20Flash,
  gemini20FlashExp,
  gemini20FlashLite,
  gemini20ProExp0205,
  gemini25FlashLite,
  gemini25FlashPreview0417,
  gemini25ProExp0325,
  gemini25ProPreview0325,
  type GeminiConfig,
  type GeminiVersionString,
} from './gemini.js';
import {
  GENERIC_IMAGEN_INFO,
  ImagenConfigSchema,
  type KNOWN_IMAGEN_MODELS,
} from './imagen.js';
import { listModels } from './list-models.js';
import { GENERIC_VEO_INFO, KNOWN_VEO_MODELS, VeoConfigSchema } from './veo.js';
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
  gemini25FlashLite,
  gemini25FlashPreview0417,
  gemini25ProExp0325,
  gemini25ProPreview0325,
  geminiEmbedding001,
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

// v2 helper functions that return actions directly
// createGeminiModel is now imported from gemini.ts

function createGeminiEmbedder(
  name: string,
  options: { apiKey?: string | false }
) {
  // For now, return a placeholder - we'll implement this properly
  return embedder(
    {
      name,
      configSchema: GeminiEmbeddingConfigSchema,
      info: {
        dimensions: 768,
        label: `Google Gen AI - ${name}`,
        supports: { input: ['text'] },
      },
    },
    async (request) => {
      // TODO: Implement actual Gemini embedder
      throw new Error('Gemini embedder not yet implemented in v2');
    }
  );
}

async function initializer(options?: PluginOptions) {
  const actions: ResolvableAction[] = [];
  let apiVersions = ['v1'];

  if (options?.apiVersion) {
    if (Array.isArray(options?.apiVersion)) {
      apiVersions = options?.apiVersion;
    } else {
      apiVersions = [options?.apiVersion];
    }
  }

  if (apiVersions.includes('v1beta')) {
    Object.keys(SUPPORTED_GEMINI_MODELS).forEach((name) => {
      const modelAction = createGeminiModel({
        name,
        apiKey: options?.apiKey,
        apiVersion: 'v1beta',
        baseUrl: options?.baseUrl,
      });
      actions.push(modelAction);
    });
  }
  if (apiVersions.includes('v1')) {
    Object.keys(SUPPORTED_GEMINI_MODELS).forEach((name) => {
      const modelAction = createGeminiModel({
        name,
        apiKey: options?.apiKey,
        apiVersion: undefined,
        baseUrl: options?.baseUrl,
      });
      actions.push(modelAction);
    });
    Object.keys(EMBEDDER_MODELS).forEach((name) => {
      const embedderAction = createGeminiEmbedder(name, {
        apiKey: options?.apiKey,
      });
      actions.push(embedderAction);
    });
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
      const modelAction = createGeminiModel({
        name: modelName,
        apiKey: options?.apiKey,
        baseUrl: options?.baseUrl,
        info: {
          ...modelRef.info,
          label: `Google AI - ${modelName}`,
        },
      });
      actions.push(modelAction);
    }
  }

  return actions;
}

async function resolver(
  actionType: ActionType,
  actionName: string,
  options?: PluginOptions
): Promise<ResolvableAction | undefined> {
  if (actionType === 'embedder') {
    return createGeminiEmbedder(actionName, { apiKey: options?.apiKey });
  } else if (actionName.startsWith('veo')) {
    // we do it this way because the request may come in for
    // action type 'model' and action name 'veo-...'. That case should
    // be a noop. It's just the order or model lookup.
    if (actionType === 'background-model') {
      // TODO: Implement Veo background model
      return backgroundModel({
        name: actionName,
        configSchema: VeoConfigSchema,
        label: `Google AI - ${actionName}`,
        async start(request) {
          throw new Error('Veo background model not yet implemented in v2');
        },
        async check(operation) {
          throw new Error('Veo background model not yet implemented in v2');
        },
        async cancel(operation) {
          throw new Error('Veo background model not yet implemented in v2');
        },
      });
    }
  } else if (actionType === 'model') {
    if (actionName.startsWith('imagen')) {
      // TODO: Implement Imagen model
      return model({ name: actionName }, async (request) => {
        throw new Error('Imagen model not yet implemented in v2');
      });
    }
    return createGeminiModel({
      name: actionName,
      apiKey: options?.apiKey,
      baseUrl: options?.baseUrl,
    });
  }
  return undefined;
}

// These v1 functions are no longer needed in v2 - they've been replaced by the resolver function above

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
    // Imagen
    ...models
      .filter(
        (m) =>
          m.supportedGenerationMethods.includes('predict') &&
          m.name.includes('imagen')
      )
      // Filter out deprecated
      .filter((m) => !m.description || !m.description.includes('deprecated'))
      .map((m) => {
        const name = m.name.split('/').at(-1)!;

        return modelActionMetadata({
          name: name,
          info: { ...GENERIC_IMAGEN_INFO },
          configSchema: ImagenConfigSchema,
        });
      }),
    // Veo
    ...models
      .filter(
        (m) =>
          m.supportedGenerationMethods.includes('predictLongRunning') &&
          m.name.includes('veo')
      )
      // Filter out deprecated
      .filter((m) => !m.description || !m.description.includes('deprecated'))
      .map((m) => {
        const name = m.name.split('/').at(-1)!;

        return modelActionMetadata({
          name: name,
          info: { ...GENERIC_VEO_INFO },
          configSchema: VeoConfigSchema,
          background: true,
        });
      }),
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
        const name = m.name.startsWith('models/')
          ? m.name.substring('models/'.length)
          : m.name;

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
export function googleAIPlugin(options?: PluginOptions): GenkitPluginV2 {
  let listActionsCache;
  return genkitPluginV2({
    name: 'googleai',
    async init() {
      return await initializer(options);
    },
    async resolve(actionType: ActionType, actionName: string) {
      return await resolver(actionType, actionName, options);
    },
    async list() {
      if (listActionsCache) return listActionsCache;
      listActionsCache = await listActions(options);
      return listActionsCache;
    },
  });
}

export type GoogleAIPlugin = {
  (params?: PluginOptions): GenkitPluginV2;
  model(
    name: keyof typeof SUPPORTED_GEMINI_MODELS | (`gemini-${string}` & {}),
    config?: z.infer<typeof GeminiConfigSchema>
  ): ModelReference<typeof GeminiConfigSchema>;
  model(
    name: KNOWN_IMAGEN_MODELS | (`imagen${string}` & {}),
    config?: z.infer<typeof ImagenConfigSchema>
  ): ModelReference<typeof ImagenConfigSchema>;
  model(
    name: KNOWN_VEO_MODELS | (`veo${string}` & {}),
    config?: z.infer<typeof VeoConfigSchema>
  ): ModelReference<typeof VeoConfigSchema>;
  model(name: string, config?: any): ModelReference<z.ZodTypeAny>;
  embedder(
    name: string,
    config?: GeminiEmbeddingConfig
  ): EmbedderReference<typeof GeminiEmbeddingConfigSchema>;
};

/**
 * Google Gemini Developer API plugin.
 */
export const googleAI = googleAIPlugin as GoogleAIPlugin;
// provide generic implementation for the model function overloads.
(googleAI as any).model = (
  name: string,
  config?: any
): ModelReference<z.ZodTypeAny> => {
  if (name.startsWith('imagen')) {
    return modelRef({
      name: `googleai/${name}`,
      config,
      configSchema: ImagenConfigSchema,
    });
  }
  if (name.startsWith('veo')) {
    return modelRef({
      name: `googleai/${name}`,
      config,
      configSchema: VeoConfigSchema,
    });
  }
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
