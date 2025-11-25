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

import type { ModelInfo } from 'genkit/model';
import { BetaRunner, Runner } from './runner/index.js';
import {
  AnthropicBaseConfigSchema,
  AnthropicBaseConfigSchemaType,
  AnthropicConfigSchema,
  AnthropicThinkingConfigSchema,
  resolveBetaEnabled,
  type ClaudeModelParams,
  type ClaudeRunnerParams,
} from './types.js';

// This contains all the Anthropic config schema types
type ConfigSchemaType =
  | AnthropicBaseConfigSchemaType
  | AnthropicThinkingConfigSchemaType;

/**
 * Creates a model reference for a Claude model.
 * Computes the default version from info.versions array and sets it on the modelRef.
 */
function commonRef(
  name: string,
  info?: ModelInfo,
  configSchema: ConfigSchemaType = AnthropicConfigSchema
): ModelReference<ConfigSchemaType> {
  // Compute default version from info.versions array
  let defaultVersion: string | undefined;
  if (info?.versions && info.versions.length > 0) {
    // Prefer version with '-latest' suffix
    const latestVersion = info.versions.find((v) => v.endsWith('-latest'));
    if (latestVersion) {
      defaultVersion = latestVersion;
    } else if (info.versions.includes(name)) {
      // If base name exists in versions array, use it directly
      defaultVersion = name;
    } else {
      // Otherwise use first version
      defaultVersion = info.versions[0];
    }
  }

  return modelRef({
    name: `anthropic/${name}`,
    configSchema,
    version: defaultVersion,
    info: info ?? {
      supports: {
        multiturn: true,
        tools: true,
        media: true,
        systemRole: true,
        output: ['text'],
      },
    },
  });
}

export const KNOWN_CLAUDE_MODELS: Record<
  string,
  ModelReference<
    AnthropicBaseConfigSchemaType | AnthropicThinkingConfigSchemaType
  >
> = {
  'claude-3-haiku': commonRef(
    'claude-3-haiku',
    {
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
    AnthropicBaseConfigSchema
  ),
  'claude-3-5-haiku': commonRef(
    'claude-3-5-haiku',
    {
      versions: ['claude-3-5-haiku-20241022', 'claude-3-5-haiku'],
      label: 'Anthropic - Claude 3.5 Haiku',
      supports: {
        multiturn: true,
        tools: true,
        media: true,
        systemRole: true,
        output: ['text'],
      },
    },
    AnthropicBaseConfigSchema
  ),
  'claude-sonnet-4': commonRef(
    'claude-sonnet-4',
    {
      versions: ['claude-sonnet-4-20250514'],
      label: 'Anthropic - Claude Sonnet 4',
      supports: {
        multiturn: true,
        tools: true,
        media: true,
        systemRole: true,
        output: ['text'],
      },
    },
    AnthropicThinkingConfigSchema
  ),
  'claude-opus-4': commonRef(
    'claude-opus-4',
    {
      versions: ['claude-opus-4-20250514'],
      label: 'Anthropic - Claude Opus 4',
      supports: {
        multiturn: true,
        tools: true,
        media: true,
        systemRole: true,
        output: ['text'],
      },
    },
    AnthropicThinkingConfigSchema
  ),
  'claude-sonnet-4-5': commonRef(
    'claude-sonnet-4-5',
    {
      versions: ['claude-sonnet-4-5-20250929', 'claude-sonnet-4-5'],
      label: 'Anthropic - Claude Sonnet 4.5',
      supports: {
        multiturn: true,
        tools: true,
        media: true,
        systemRole: true,
        output: ['text'],
      },
    },
    AnthropicThinkingConfigSchema
  ),
  'claude-haiku-4-5': commonRef(
    'claude-haiku-4-5',
    {
      versions: ['claude-haiku-4-5-20251001', 'claude-haiku-4-5'],
      label: 'Anthropic - Claude Haiku 4.5',
      supports: {
        multiturn: true,
        tools: true,
        media: true,
        systemRole: true,
        output: ['text'],
      },
    },
    AnthropicThinkingConfigSchema
  ),
  'claude-opus-4-1': commonRef(
    'claude-opus-4-1',
    {
      versions: ['claude-opus-4-1-20250805', 'claude-opus-4-1'],
      label: 'Anthropic - Claude Opus 4.1',
      supports: {
        multiturn: true,
        tools: true,
        media: true,
        systemRole: true,
        output: ['text'],
      },
    },
    AnthropicThinkingConfigSchema
  ),
};

/**
 * Gets the un-prefixed model name from a modelReference.
 */
export function extractVersion(
  model: ModelReference<ConfigSchemaType> | undefined,
  modelName: string
): string {
  if (model?.version) {
    return model.version;
  }
  // Fallback: extract from model name (remove 'anthropic/' prefix if present)
  return modelName.replace(/^anthropic\//, '');
}

/**
 * Generic Claude model info for unknown/unsupported models.
 * Used when a model name is not in KNOWN_CLAUDE_MODELS.
 */
export const GENERIC_CLAUDE_MODEL_INFO = {
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

export type KnownClaudeModels = keyof typeof KNOWN_CLAUDE_MODELS;
export type ClaudeModelName = string;
export type AnthropicConfigSchemaType = typeof AnthropicConfigSchema;
export type AnthropicThinkingConfigSchemaType =
  typeof AnthropicThinkingConfigSchema;
export type ClaudeConfig = z.infer<typeof AnthropicConfigSchema>;

/**
 * Creates the runner used by Genkit to interact with the Claude model.
 * @param params Configuration for the Claude runner.
 * @param configSchema The config schema for this model (used for type inference).
 * @returns The runner that Genkit will call when the model is invoked.
 */
export function claudeRunner<TConfigSchema extends z.ZodTypeAny>(
  params: ClaudeRunnerParams,
  configSchema: TConfigSchema
) {
  const { defaultApiVersion, ...runnerParams } = params;

  if (!runnerParams.client) {
    throw new Error('Anthropic client is required to create a runner');
  }

  let stableRunner: Runner | null = null;
  let betaRunner: BetaRunner | null = null;

  return async (
    request: GenerateRequest<TConfigSchema>,
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
    // Cast to AnthropicConfigSchema for internal runner which expects the full schema
    const normalizedRequest = request as unknown as GenerateRequest<
      typeof AnthropicConfigSchema
    >;
    const isBeta = resolveBetaEnabled(
      normalizedRequest.config,
      defaultApiVersion
    );
    const runner = isBeta
      ? (betaRunner ??= new BetaRunner(runnerParams))
      : (stableRunner ??= new Runner(runnerParams));
    return runner.run(normalizedRequest, {
      streamingRequested,
      sendChunk,
      abortSignal,
    });
  };
}

/**
 * Creates a model reference for a Claude model.
 * This allows referencing models without initializing the plugin.
 */
export function claudeModelReference(
  name: string,
  config?: z.infer<typeof AnthropicConfigSchema>
): ModelReference<z.ZodTypeAny> {
  const knownModel = KNOWN_CLAUDE_MODELS[name];
  if (knownModel) {
    return modelRef({
      name: knownModel.name,
      info: knownModel.info,
      configSchema: knownModel.configSchema,
      version: knownModel.version,
      config,
    });
  }

  // For unknown models, create a basic reference
  return modelRef({
    name: `anthropic/${name}`,
    configSchema: AnthropicConfigSchema,
    config,
  });
}

/**
 * Defines a Claude model with the given name and Anthropic client.
 * Accepts any model name and lets the API validate it. If the model is in KNOWN_CLAUDE_MODELS, uses that modelRef
 * for better defaults; otherwise creates a generic model reference.
 */
export function claudeModel(
  paramsOrName: ClaudeModelParams | string,
  client?: Anthropic,
  cacheSystemPrompt?: boolean,
  defaultApiVersion?: 'stable' | 'beta'
): ModelAction<z.ZodTypeAny> {
  const params =
    typeof paramsOrName === 'string'
      ? {
          name: paramsOrName,
          client:
            client ??
            (() => {
              throw new Error(
                'Anthropic client is required to create a model action'
              );
            })(),
          cacheSystemPrompt,
          defaultApiVersion,
        }
      : paramsOrName;

  const {
    name,
    client: runnerClient,
    cacheSystemPrompt: cachePrompt,
    defaultApiVersion: apiVersion,
  } = params;
  // Use supported model ref if available, otherwise create generic model ref
  const modelRef = KNOWN_CLAUDE_MODELS[name];
  const modelInfo = modelRef ? modelRef.info : GENERIC_CLAUDE_MODEL_INFO;
  const configSchema = modelRef?.configSchema ?? AnthropicConfigSchema;

  return model<
    AnthropicBaseConfigSchemaType | AnthropicThinkingConfigSchemaType
  >(
    {
      name: `anthropic/${name}`,
      ...modelInfo,
      configSchema: configSchema,
    },
    claudeRunner(
      {
        name,
        client: runnerClient,
        cacheSystemPrompt: cachePrompt,
        defaultApiVersion: apiVersion,
      },
      configSchema
    )
  );
}
