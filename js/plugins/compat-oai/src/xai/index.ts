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
  Genkit,
  modelActionMetadata,
  modelRef,
  ModelReference,
  z,
} from 'genkit';
import { logger } from 'genkit/logging';
import { GenkitPlugin } from 'genkit/plugin';
import { ActionType } from 'genkit/registry';
import OpenAI from 'openai';
import {
  defineCompatOpenAIImageModel,
  IMAGE_GENERATION_MODEL_INFO,
  ImageGenerationCommonConfigSchema,
} from '../image.js';
import openAICompatible, { PluginOptions } from '../index.js';
import {
  ChatCompletionCommonConfigSchema,
  defineCompatOpenAIModel,
} from '../model.js';
import { SUPPORTED_IMAGE_MODELS } from './grok-image.js';
import { SUPPORTED_LANGUAGE_MODELS } from './grok.js';

export type XAIPluginOptions = Omit<PluginOptions, 'name' | 'baseURL'>;

const resolver = async (
  ai: Genkit,
  client: OpenAI,
  actionType: ActionType,
  actionName: string
) => {
  if (actionType === 'model') {
    defineCompatOpenAIModel({
      ai,
      name: `xai/${actionName}`,
      client,
    });
  } else {
    logger.warn('Only model actions are supported by the XAI plugin');
  }
};

const listActions = async (client: OpenAI): Promise<ActionMetadata[]> => {
  return await client.models.list().then((response) =>
    response.data
      .filter((model) => model.object === 'model')
      .map((model: OpenAI.Model) => {
        if (model.id.includes('image')) {
          return modelActionMetadata({
            name: `xai/${model.id}`,
            configSchema: ImageGenerationCommonConfigSchema,
            info: IMAGE_GENERATION_MODEL_INFO,
          });
        } else {
          return modelActionMetadata({
            name: `xai/${model.id}`,
            configSchema: ChatCompletionCommonConfigSchema,
            info: SUPPORTED_LANGUAGE_MODELS[model.id]?.info,
          });
        }
      })
  );
};

export function xAIPlugin(options?: XAIPluginOptions): GenkitPlugin {
  return openAICompatible({
    name: 'xai',
    baseURL: 'https://api.x.ai/v1',
    ...options,
    initializer: async (ai, client) => {
      Object.values(SUPPORTED_LANGUAGE_MODELS).forEach((modelRef) =>
        defineCompatOpenAIModel({ ai, name: modelRef.name, client, modelRef })
      );
      Object.values(SUPPORTED_IMAGE_MODELS).forEach((modelRef) =>
        defineCompatOpenAIImageModel({
          ai,
          name: modelRef.name,
          client,
          modelRef,
        })
      );
    },
    resolver,
    listActions,
  });
}

export type XAIPlugin = {
  (params?: XAIPluginOptions): GenkitPlugin;
  model(
    name: keyof typeof SUPPORTED_LANGUAGE_MODELS,
    config?: z.infer<typeof ChatCompletionCommonConfigSchema>
  ): ModelReference<typeof ChatCompletionCommonConfigSchema>;
  model(
    name: keyof typeof SUPPORTED_IMAGE_MODELS,
    config?: z.infer<typeof ImageGenerationCommonConfigSchema>
  ): ModelReference<typeof ImageGenerationCommonConfigSchema>;
  model(name: string, config?: any): ModelReference<z.ZodTypeAny>;
};

const model = ((name: string, config?: any): ModelReference<z.ZodTypeAny> => {
  if (name.includes('image')) {
    return modelRef({
      name: `xai/${name}`,
      config,
      configSchema: ImageGenerationCommonConfigSchema,
    });
  }
  return modelRef({
    name: `xai/${name}`,
    config,
    configSchema: ChatCompletionCommonConfigSchema,
  });
}) as XAIPlugin['model'];

/**
 * This module provides an interface to the XAI models through the Genkit
 * plugin system. It allows users to interact with various models by providing
 * an API key and optional configuration.
 *
 * The main export is the `xai` plugin, which can be configured with an API
 * key either directly or through environment variables. It initializes the
 * OpenAI client and makes available the models for use.
 *
 * Exports:
 * - xAI: The main plugin function to interact with XAI, via OpenAI
 *   compatible API.
 *
 * Usage: To use the models, initialize the xAI plugin inside
 * `configureGenkit` and pass the configuration options. If no API key is
 * provided in the options, the environment variable `OPENAI_API_KEY` must be
 * set.
 *
 * Example:
 * ```
 * import { xAI } from '@genkit-ai/compat-oai/xai';
 *
 * export default configureGenkit({
 *  plugins: [
 *    xAI()
 *    ... // other plugins
 *  ]
 * });
 * ```
 */
export const xAI: XAIPlugin = Object.assign(xAIPlugin, {
  model,
});

export default xAI;
