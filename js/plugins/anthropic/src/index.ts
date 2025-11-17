/**
 * Copyright 2024 Bloom Labs Inc
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

import Anthropic from '@anthropic-ai/sdk';
import { genkitPluginV2, type GenkitPluginV2 } from 'genkit/plugin';

import { ActionMetadata, ModelReference, z } from 'genkit';
import { ModelAction } from 'genkit/model';
import { ActionType } from 'genkit/registry';
import { listActions } from './list.js';
import {
  AnthropicConfigSchemaType,
  ClaudeConfig,
  ClaudeModelName,
  KNOWN_CLAUDE_MODELS,
  KnownClaudeModels,
  claude35Haiku,
  claude3Haiku,
  claudeHaiku45,
  claudeModel,
  claudeModelReference,
  claudeOpus4,
  claudeOpus41,
  claudeSonnet4,
  claudeSonnet45,
} from './models.js';
import { InternalPluginOptions, PluginOptions, __testClient } from './types.js';

const PROMPT_CACHING_BETA_HEADER_VALUE = 'prompt-caching-2024-07-31';

export {
  claude35Haiku,
  claude3Haiku,
  claudeHaiku45,
  claudeOpus4,
  claudeOpus41,
  claudeSonnet4,
  claudeSonnet45,
};

/**
 * Gets or creates an Anthropic client instance.
 * Supports test client injection for internal testing.
 */
function getAnthropicClient(options?: PluginOptions): Anthropic {
  // Check for test client injection first (internal use only)
  const internalOptions = options as InternalPluginOptions | undefined;
  if (internalOptions?.[__testClient]) {
    return internalOptions[__testClient];
  }

  // Production path: create real client
  const apiKey = options?.apiKey || process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    throw new Error(
      'Please pass in the API key or set the ANTHROPIC_API_KEY environment variable'
    );
  }
  const defaultHeaders: Record<string, string> = {};
  if (options?.cacheSystemPrompt) {
    defaultHeaders['anthropic-beta'] = PROMPT_CACHING_BETA_HEADER_VALUE;
  }
  return new Anthropic({ apiKey, defaultHeaders });
}

/**
 * This module provides an interface to the Anthropic AI models through the Genkit plugin system.
 * It allows users to interact with various Claude models by providing an API key and optional configuration.
 *
 * The main export is the `anthropic` plugin, which can be configured with an API key either directly or through
 * environment variables. It initializes the Anthropic client and makes available the Claude models for use.
 *
 * Exports:
 * - claude35Haiku: Reference to the Claude 3.5 Haiku model.
 * - claude3Haiku: Reference to the Claude 3 Haiku model.
 * - claudeHaiku45: Reference to the Claude Haiku 4.5 model.
 * - claudeOpus4: Reference to the Claude Opus 4 model.
 * - claudeOpus41: Reference to the Claude Opus 4.1 model.
 * - claudeSonnet4: Reference to the Claude Sonnet 4 model.
 * - claudeSonnet45: Reference to the Claude Sonnet 4.5 model.
 * - anthropic: The main plugin function to interact with the Anthropic AI.
 *
 * Usage:
 * To use the Claude models, initialize the anthropic plugin inside `genkit()` and pass the configuration options. If no API key is provided in the options, the environment variable `ANTHROPIC_API_KEY` must be set. If you want to cache the system prompt, set `cacheSystemPrompt` to `true`. **Note:** Prompt caching is in beta and may change. To learn more, see https://docs.anthropic.com/en/docs/prompt-caching.
 *
 * Example:
 * ```
 * import { anthropic } from '@genkit-ai/anthropic';
 * import { genkit } from 'genkit';
 *
 * const ai = genkit({
 *  plugins: [
 *    anthropic({ apiKey: 'your-api-key', cacheSystemPrompt: false })
 *    ... // other plugins
 *  ]
 * });
 * ```
 */
function anthropicPlugin(options?: PluginOptions): GenkitPluginV2 {
  const client = getAnthropicClient(options);
  const defaultApiVersion = options?.apiVersion;

  let listActionsCache: ActionMetadata[] | null = null;

  return genkitPluginV2({
    name: 'anthropic',
    init: async () => {
      const actions: ModelAction[] = [];
      for (const name of Object.keys(KNOWN_CLAUDE_MODELS)) {
        const action = claudeModel({
          name,
          client,
          cacheSystemPrompt: options?.cacheSystemPrompt,
          defaultApiVersion,
        });
        actions.push(action);
      }
      return actions;
    },
    resolve: (actionType: ActionType, name: string) => {
      if (actionType === 'model') {
        // Strip the 'anthropic/' namespace prefix if present
        const modelName = name.startsWith('anthropic/') ? name.slice(10) : name;
        return claudeModel({
          name: modelName,
          client,
          cacheSystemPrompt: options?.cacheSystemPrompt,
          defaultApiVersion,
        });
      }
      return undefined;
    },
    list: async () => {
      if (listActionsCache) return listActionsCache;
      listActionsCache = await listActions(client);
      return listActionsCache;
    },
  });
}

export type AnthropicPlugin = {
  (pluginOptions?: PluginOptions): GenkitPluginV2;
  model(
    name: KnownClaudeModels | (ClaudeModelName & {}),
    config?: ClaudeConfig
  ): ModelReference<AnthropicConfigSchemaType>;
  model(name: string, config?: any): ModelReference<z.ZodTypeAny>;
};

/**
 * Anthropic AI plugin for Genkit.
 * Includes Claude models (3, 3.5, 3.7, and 4 series).
 */
export const anthropic = anthropicPlugin as AnthropicPlugin;
(anthropic as any).model = (
  name: string,
  config?: any
): ModelReference<z.ZodTypeAny> => {
  return claudeModelReference(name, config);
};

export default anthropic;
