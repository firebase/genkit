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

import type Anthropic from '@anthropic-ai/sdk';
import type {
  GenerateRequest,
  GenerateResponseData,
  ModelReference,
  StreamingCallback,
} from 'genkit';
import { z } from 'genkit';
import type { GenerateResponseChunkData, ModelAction } from 'genkit/model';
import { modelRef } from 'genkit/model';
import { model } from 'genkit/plugin';

import { BetaRunner, Runner } from './runner/index.js';
import { AnthropicConfigSchema, resolveBetaEnabled } from './types.js';

export const claude4Sonnet = modelRef({
  name: 'claude-4-sonnet',
  namespace: 'anthropic',
  info: {
    versions: ['claude-sonnet-4-20250514'],
    label: 'Anthropic - Claude 4 Sonnet',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: AnthropicConfigSchema,
  version: 'claude-sonnet-4-20250514',
});

export const claude3Haiku = modelRef({
  name: 'claude-3-haiku',
  namespace: 'anthropic',
  info: {
    versions: ['claude-3-haiku-20240307'],
    label: 'Anthropic - Claude 3 Haiku',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: AnthropicConfigSchema,
  version: 'claude-3-haiku-20240307',
});

export const claude4Opus = modelRef({
  name: 'claude-4-opus',
  namespace: 'anthropic',
  info: {
    versions: ['claude-opus-4-20250514'],
    label: 'Anthropic - Claude 4 Opus',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: AnthropicConfigSchema,
  version: 'claude-opus-4-20250514',
});

export const claude35Haiku = modelRef({
  name: 'claude-3-5-haiku',
  namespace: 'anthropic',
  info: {
    versions: ['claude-3-5-haiku-20241022', 'claude-3-5-haiku-latest'],
    label: 'Anthropic - Claude 3.5 Haiku',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: AnthropicConfigSchema,
  version: 'claude-3-5-haiku-latest',
});

export const claude45Sonnet = modelRef({
  name: 'claude-4-5-sonnet',
  namespace: 'anthropic',
  info: {
    versions: ['claude-sonnet-4-5-20250929', 'claude-sonnet-4-5-latest'],
    label: 'Anthropic - Claude 4.5 Sonnet',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: AnthropicConfigSchema,
  version: 'claude-sonnet-4-5-latest',
});

export const claude45Haiku = modelRef({
  name: 'claude-4-5-haiku',
  namespace: 'anthropic',
  info: {
    versions: ['claude-haiku-4-5-20251001', 'claude-haiku-4-5-latest'],
    label: 'Anthropic - Claude 4.5 Haiku',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: AnthropicConfigSchema,
  version: 'claude-haiku-4-5-latest',
});

export const claude41Opus = modelRef({
  name: 'claude-4-1-opus',
  namespace: 'anthropic',
  info: {
    versions: ['claude-opus-4-1-20250805', 'claude-opus-4-1-latest'],
    label: 'Anthropic - Claude 4.1 Opus',
    supports: {
      multiturn: true,
      tools: true,
      media: true,
      systemRole: true,
      output: ['text'],
    },
  },
  configSchema: AnthropicConfigSchema,
  version: 'claude-opus-4-1-latest',
});

export const KNOWN_CLAUDE_MODELS: Record<
  string,
  ModelReference<typeof AnthropicConfigSchema>
> = {
  'claude-3-haiku': claude3Haiku,
  'claude-3-5-haiku': claude35Haiku,
  'claude-4-sonnet': claude4Sonnet,
  'claude-4-opus': claude4Opus,
  'claude-4-5-sonnet': claude45Sonnet,
  'claude-4-5-haiku': claude45Haiku,
  'claude-4-1-opus': claude41Opus,
};

export type KnownClaudeModels = keyof typeof KNOWN_CLAUDE_MODELS;
export type ClaudeModelName = string;
export type AnthropicConfigSchemaType = typeof AnthropicConfigSchema;
export type ClaudeConfig = z.infer<typeof AnthropicConfigSchema>;

/**
 * Creates the runner used by Genkit to interact with the Claude model.
 * @param name The name of the Claude model.
 * @param client The Anthropic client instance.
 * @param cacheSystemPrompt Whether to cache the system prompt.
 * @param defaultApiVersion Plugin-wide default API surface.
 * @returns The runner that Genkit will call when the model is invoked.
 */
export function claudeRunner(
  name: string,
  client: Anthropic,
  cacheSystemPrompt?: boolean,
  defaultApiVersion?: 'stable' | 'beta'
) {
  return async (
    request: GenerateRequest<typeof AnthropicConfigSchema>,
    {
      streamingRequested,
      sendChunk,
      abortSignal,
    }: {
      streamingRequested: boolean;
      sendChunk: StreamingCallback<GenerateResponseChunkData>;
      abortSignal: AbortSignal;
    }
  ): Promise<GenerateResponseData> => {
    const isBeta = resolveBetaEnabled(request.config, defaultApiVersion);
    const api = isBeta
      ? new BetaRunner(name, client, cacheSystemPrompt)
      : new Runner(name, client, cacheSystemPrompt);
    return api.run(request, { streamingRequested, sendChunk, abortSignal });
  };
}

/**
 * Generic Claude model info for unknown/unsupported models.
 * Used when a model name is not in SUPPORTED_CLAUDE_MODELS.
 */
const GENERIC_CLAUDE_MODEL_INFO = {
  versions: [],
  label: 'Anthropic - Claude',
  supports: {
    multiturn: true,
    tools: true,
    media: true,
    systemRole: true,
    output: ['text'],
  },
};

/**
 * Creates a model reference for a Claude model.
 * This allows referencing models without initializing the plugin.
 */
export function claudeModelReference(
  name: string,
  config?: z.infer<typeof AnthropicConfigSchema>
): ModelReference<typeof AnthropicConfigSchema> {
  const knownModel = KNOWN_CLAUDE_MODELS[name];
  if (knownModel) {
    return modelRef({
      name: knownModel.name,
      namespace: 'anthropic',
      info: knownModel.info,
      configSchema: knownModel.configSchema,
      config,
    });
  }

  // For unknown models, create a basic reference
  return modelRef({
    name,
    namespace: 'anthropic',
    configSchema: AnthropicConfigSchema,
    config,
  });
}

/**
 * Defines a Claude model with the given name and Anthropic client.
 * Accepts any model name and lets the API validate it. If the model is in SUPPORTED_CLAUDE_MODELS, uses that modelRef
 * for better defaults; otherwise creates a generic model reference.
 */
export function claudeModel(
  name: string,
  client: Anthropic,
  cacheSystemPrompt?: boolean,
  defaultApiVersion?: 'stable' | 'beta'
): ModelAction<typeof AnthropicConfigSchema> {
  // Use supported model ref if available, otherwise create generic model ref
  const modelRef = KNOWN_CLAUDE_MODELS[name];
  const modelInfo = modelRef ? modelRef.info : GENERIC_CLAUDE_MODEL_INFO;

  return model(
    {
      name: `anthropic/${name}`,
      ...modelInfo,
      configSchema: AnthropicConfigSchema,
    },
    claudeRunner(name, client, cacheSystemPrompt, defaultApiVersion)
  );
}
