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

import { Genkit, ModelReference } from 'genkit';
import { GenkitPlugin, genkitPlugin } from 'genkit/plugin';
import {
  SUPPORTED_MODELS as EMBEDDER_MODELS,
  defineGoogleAIEmbedder,
  textEmbedding004,
  textEmbeddingGecko001,
} from './embedder.js';
import {
  GeminiConfigSchema,
  SUPPORTED_V15_MODELS,
  SUPPORTED_V1_MODELS,
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
  gemini25ProExp0325,
  type GeminiConfig,
  type GeminiVersionString,
} from './gemini.js';
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
  gemini25ProExp0325,
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

/**
 * Google Gemini Developer API plugin.
 */
export function googleAI(options?: PluginOptions): GenkitPlugin {
  return genkitPlugin('googleai', async (ai: Genkit) => {
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
  });
}

export default googleAI;
