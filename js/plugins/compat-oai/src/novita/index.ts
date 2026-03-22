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
  GenkitError,
  modelActionMetadata,
  ModelReference,
  z,
} from 'genkit';
import { logger } from 'genkit/logging';
import { type GenkitPluginV2 } from 'genkit/plugin';
import { ActionType } from 'genkit/registry';
import OpenAI from 'openai';
import { openAICompatible, PluginOptions } from '../index.js';
import {
  ChatCompletionCommonConfigSchema,
  defineCompatOpenAIModel,
} from '../model.js';
import {
  novitaModelRef,
  SUPPORTED_NOVITA_MODELS,
} from './novita.js';

export type NovitaPluginOptions = Omit<PluginOptions, 'name' | 'baseURL'>;

function createResolver(pluginOptions: PluginOptions) {
  return async (client: OpenAI, actionType: ActionType, actionName: string) => {
    if (actionType === 'model') {
      const modelRef = novitaModelRef({ name: actionName });
      return defineCompatOpenAIModel({
        name: modelRef.name,
        client,
        pluginOptions,
        modelRef,
      });
    } else {
      logger.warn('Only model actions are supported by the Novita plugin');
      return undefined;
    }
  };
}

const listActions = async (client: OpenAI): Promise<ActionMetadata[]> => {
  return await client.models.list().then((response) =>
    response.data
      .filter((model) => model.object === 'model')
      .map((model: OpenAI.Model) => {
        const modelRef =
          SUPPORTED_NOVITA_MODELS[
            model.id as keyof typeof SUPPORTED_NOVITA_MODELS
          ] ?? novitaModelRef({ name: model.id });
        return modelActionMetadata({
          name: modelRef.name,
          info: modelRef.info,
          configSchema: modelRef.configSchema,
        });
      })
  );
};

export function novitaPlugin(
  options?: NovitaPluginOptions
): GenkitPluginV2 {
  const apiKey = options?.apiKey ?? process.env.NOVITA_API_KEY;
  if (!apiKey) {
    throw new GenkitError({
      status: 'FAILED_PRECONDITION',
      message:
        'Please pass in the API key or set the NOVITA_API_KEY environment variable.',
    });
  }
  const pluginOptions = { name: 'novita', ...options };
  return openAICompatible({
    name: 'novita',
    baseURL: 'https://api.novita.ai/openai',
    apiKey,
    ...options,
    initializer: async (client) => {
      return Object.values(SUPPORTED_NOVITA_MODELS).map((modelRef) =>
        defineCompatOpenAIModel({
          name: modelRef.name,
          client,
          pluginOptions,
          modelRef,
        })
      );
    },
    resolver: createResolver(pluginOptions),
    listActions,
  });
}

export type NovitaPlugin = {
  (params?: NovitaPluginOptions): GenkitPluginV2;
  model(
    name: keyof typeof SUPPORTED_NOVITA_MODELS,
    config?: z.infer<typeof ChatCompletionCommonConfigSchema>
  ): ModelReference<typeof ChatCompletionCommonConfigSchema>;
  model(name: string, config?: any): ModelReference<z.ZodTypeAny>;
};

const model = ((name: string, config?: any): ModelReference<z.ZodTypeAny> => {
  return novitaModelRef({ name, config });
}) as NovitaPlugin['model'];

/**
 * This module provides an interface to Novita AI models through the Genkit
 * plugin system. It allows users to interact with various models by providing
 * an API key and optional configuration.
 *
 * The main export is the `novita` plugin, which can be configured with an API
 * key either directly or through environment variables. It initializes the
 * OpenAI-compatible client and makes available the models for use.
 *
 * Exports:
 * - novita: The main plugin function to interact with Novita AI, via OpenAI
 *   compatible API.
 *
 * Usage: To use the models, initialize the novita plugin inside
 * `configureGenkit` and pass the configuration options. If no API key is
 * provided in the options, the environment variable `NOVITA_API_KEY` must be
 * set.
 *
 * Example:
 * ```
 * import { novita } from '@genkit-ai/compat-oai/novita';
 *
 * export default configureGenkit({
 *  plugins: [
 *    novita()
 *    ... // other plugins
 *  ]
 * });
 * ```
 */
export const novita: NovitaPlugin = Object.assign(novitaPlugin, {
  model,
});

export default novita;
