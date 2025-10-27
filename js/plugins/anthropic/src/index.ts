/**
 * Copyright 2024 Bloom Labs Inc
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

import { genkitPluginV2, model, modelActionMetadata } from 'genkit/plugin';
import Anthropic from '@anthropic-ai/sdk';

import {
  claude4Sonnet,
  claude4Opus,
  claude37Sonnet,
  claude35Sonnet,
  claude3Opus,
  claude3Sonnet,
  claude3Haiku,
  claude35Haiku,
  claudeModel,
  SUPPORTED_CLAUDE_MODELS,
} from './claude.js';
import { ModelAction } from 'genkit/model';
import { ActionType } from 'genkit/registry';
import { ActionMetadata } from 'genkit';

export {
  claude4Sonnet,
  claude4Opus,
  claude37Sonnet,
  claude35Sonnet,
  claude3Opus,
  claude3Sonnet,
  claude3Haiku,
  claude35Haiku,
};

export interface PluginOptions {
  apiKey?: string;
  cacheSystemPrompt?: boolean;
}

async function list(client: Anthropic): Promise<ActionMetadata[]> {
  const clientModels = (await client.models.list()).data;

  return clientModels
    .map((modelInfo) => {
      // Remove the date suffix from the model id
      const normalizedId = modelInfo.id.replace(/-\d{8}$/, '');
      // Get the model reference from the supported models
      const ref = SUPPORTED_CLAUDE_MODELS[normalizedId];
      // Return the model action metadata if the model is supported
      return ref ? modelActionMetadata({
        name: ref.name,
        info: ref.info,
        configSchema: ref.configSchema,
      }) : undefined;
    })
    // Filter out undefined values
    .filter((metadata) => metadata !== undefined);
}

/**
 * This module provides an interface to the Anthropic AI models through the Genkit plugin system.
 * It allows users to interact with various Claude models by providing an API key and optional configuration.
 *
 * The main export is the `anthropic` plugin, which can be configured with an API key either directly or through
 * environment variables. It initializes the Anthropic client and makes available the Claude models for use.
 *
 * Exports:
 * - claude35Sonnet: Reference to the Claude 3.5 Sonnet model.
 * - claude3Haiku: Reference to the Claude 3 Haiku model.
 * - claude3Sonnet: Reference to the Claude 3 Sonnet model.
 * - claude3Opus: Reference to the Claude 3 Opus model.
 * - anthropic: The main plugin function to interact with the Anthropic AI.
 *
 * Usage:
 * To use the Claude models, initialize the anthropic plugin inside `configureGenkit` and pass the configuration options. If no API key is provided in the options, the environment variable `ANTHROPIC_API_KEY` must be set. If you want to cache the system prompt, set `cacheSystemPrompt` to `true`. **Note:** Prompt caching is in beta and may change. To learn more, see https://docs.anthropic.com/en/docs/prompt-caching.
 *
 * Example:
 * ```
 * import anthropic from 'genkitx-anthropic';
 *
 * export default configureGenkit({
 *  plugins: [
 *    anthropic({ apiKey: 'your-api-key', cacheSystemPrompt: false })
 *    ... // other plugins
 *  ]
 * });
 * ```
 */
// TODO: add support for voyage embeddings and tool use (both not documented well in docs.anthropic.com)
export const anthropic = (options?: PluginOptions) => {
  let apiKey = options?.apiKey || process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    throw new Error(
      'Please pass in the API key or set the ANTHROPIC_API_KEY environment variable'
    );
  }
  let defaultHeaders = {};
  if (options?.cacheSystemPrompt == true) {
    defaultHeaders['anthropic-beta'] = 'prompt-caching-2024-07-31';
  }
  const client = new Anthropic({ apiKey, defaultHeaders });

  let listActionsCache: ActionMetadata[] | null = null;

  return genkitPluginV2({
    name: 'anthropic',
    init: async () => {
      const actions: ModelAction[] = [];
      for (const name of Object.keys(SUPPORTED_CLAUDE_MODELS)) {
        const action = claudeModel(name, client, options?.cacheSystemPrompt);
        actions.push(action);
      }
      return actions;
    },
    resolve: (actionType: ActionType, name: string) => {
      if (actionType === 'model') {
        return claudeModel(
          name,
          client
        );
      }
      return undefined;
    },
    list: async () => {
      if (listActionsCache) return listActionsCache;
      listActionsCache = await list(client);
      return listActionsCache;
    }
  });
};

export default anthropic;
