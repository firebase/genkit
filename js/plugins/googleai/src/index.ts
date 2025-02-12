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
  textEmbedding004,
  textEmbeddingGecko001,
  type GeminiConfig,
  type GeminiVersionString,
};

export interface PluginOptions {
  apiKey?: string;
  apiVersion?: string | string[];
  baseUrl?: string;
  models?: (
    | ModelReference</** @ignore */ typeof GeminiConfigSchema>
    | string
  )[];
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
        defineGoogleAIModel(
          ai,
          name,
          options?.apiKey,
          'v1beta',
          options?.baseUrl
        )
      );
    }
    if (apiVersions.includes('v1')) {
      Object.keys(SUPPORTED_V1_MODELS).forEach((name) =>
        defineGoogleAIModel(
          ai,
          name,
          options?.apiKey,
          undefined,
          options?.baseUrl
        )
      );
      Object.keys(SUPPORTED_V15_MODELS).forEach((name) =>
        defineGoogleAIModel(
          ai,
          name,
          options?.apiKey,
          undefined,
          options?.baseUrl
        )
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
        defineGoogleAIModel(
          ai,
          modelName,
          options?.apiKey,
          undefined,
          options?.baseUrl,
          {
            ...modelRef.info,
            label: `Google AI - ${modelName}`,
          }
        );
      }
    }
  });
}

export default googleAI;
