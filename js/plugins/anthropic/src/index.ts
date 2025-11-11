/**
 * Original work Copyright 2024 Bloom Labs Inc
 * Modifications Copyright 2025 Google LLC
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
import {
  genkitPluginV2,
  modelActionMetadata,
  type GenkitPluginV2,
} from 'genkit/plugin';

import { ActionMetadata, ModelReference, z } from 'genkit';
import { ModelAction } from 'genkit/model';
import { ActionType } from 'genkit/registry';
import {
  AnthropicConfigSchemaType,
  ClaudeConfig,
  ClaudeModelName,
  GENERIC_CLAUDE_MODEL_INFO,
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
import {
  AnthropicConfigSchema,
  InternalPluginOptions,
  PluginOptions,
  __testClient,
} from './types.js';

export {
  claude35Haiku,
  claude3Haiku,
  claudeHaiku45,
  claudeOpus4,
  claudeOpus41,
  claudeSonnet4,
  claudeSonnet45,
};

function normalizeModelId(modelId: string): string {
  return modelId.replace(/-(?:\d{8}|latest)$/i, '');
}

type ModelMetadataParams = Parameters<typeof modelActionMetadata>[0];

async function list(client: Anthropic): Promise<ActionMetadata[]> {
  const clientModels = (await client.models.list()).data;
  const metadataByName = new Map<string, ModelMetadataParams>();
  const orderedNames: string[] = [];

  for (const modelInfo of clientModels) {
    const modelId = modelInfo.id;
    if (!modelId) {
      continue;
    }

    const normalizedId = normalizeModelId(modelId);
    const ref = KNOWN_CLAUDE_MODELS[normalizedId];

    if (ref) {
      const existing = metadataByName.get(ref.name);
      const baseInfo = existing?.info ?? ref.info;
      const mergedVersions = new Set(
        baseInfo?.versions ?? ref.info?.versions ?? []
      );
      mergedVersions.add(modelId);

      const info = {
        ...baseInfo,
        versions: Array.from(mergedVersions),
      };

      metadataByName.set(ref.name, {
        name: ref.name,
        info,
        configSchema: ref.configSchema,
      });

      if (!existing) {
        orderedNames.push(ref.name);
      }
      continue;
    }

    const fallbackName = `anthropic/${modelId}`;
    const existingFallback = metadataByName.get(fallbackName);
    const fallbackLabel =
      modelInfo.display_name ??
      (normalizedId !== modelId
        ? `Anthropic - ${normalizedId}`
        : `Anthropic - ${modelId}`);

    if (existingFallback) {
      const info = {
        ...existingFallback.info,
        versions: existingFallback.info?.versions
          ? Array.from(
              new Set([...(existingFallback.info.versions ?? []), modelId])
            )
          : [modelId],
      };
      metadataByName.set(fallbackName, {
        ...existingFallback,
        info,
      });
      continue;
    }

    metadataByName.set(fallbackName, {
      name: fallbackName,
      info: {
        ...GENERIC_CLAUDE_MODEL_INFO,
        label: fallbackLabel,
        versions: modelId ? [modelId] : [...GENERIC_CLAUDE_MODEL_INFO.versions],
        supports: {
          ...GENERIC_CLAUDE_MODEL_INFO.supports,
          output: [...GENERIC_CLAUDE_MODEL_INFO.supports.output],
        },
      },
      configSchema: AnthropicConfigSchema,
    });
    orderedNames.push(fallbackName);
  }

  return orderedNames.map((name) =>
    modelActionMetadata(metadataByName.get(name)!)
  );
}

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
  if (options?.cacheSystemPrompt == true) {
    defaultHeaders['anthropic-beta'] = 'prompt-caching-2024-07-31';
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
 * - claude3Haiku: Reference to the Claude 3 Haiku model.
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
      listActionsCache = await list(client);
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
