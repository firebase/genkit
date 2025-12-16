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
 */
function commonRef(
  name: string,
  configSchema: ConfigSchemaType = AnthropicConfigSchema,
  info?: ModelInfo
): ModelReference<ConfigSchemaType> {
  return modelRef({
    name: `anthropic/${name}`,
    configSchema,
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

/**
 * Maps short model names to their full API model IDs.
 * Claude 3.x models require versioned names (e.g., claude-3-5-haiku-20241022).
 * Claude 4.x models have API aliases that work directly.
 */
const MODEL_VERSION_MAP: Record<string, string> = {
  'claude-3-haiku': 'claude-3-haiku-20240307',
  'claude-3-5-haiku': 'claude-3-5-haiku-20241022',
};

export const KNOWN_CLAUDE_MODELS: Record<
  string,
  ModelReference<
    AnthropicBaseConfigSchemaType | AnthropicThinkingConfigSchemaType
  >
> = {
  'claude-3-haiku': commonRef('claude-3-haiku', AnthropicBaseConfigSchema),
  'claude-3-5-haiku': commonRef('claude-3-5-haiku', AnthropicBaseConfigSchema),
  'claude-sonnet-4': commonRef(
    'claude-sonnet-4',
    AnthropicThinkingConfigSchema
  ),
  'claude-opus-4': commonRef('claude-opus-4', AnthropicThinkingConfigSchema),
  'claude-sonnet-4-5': commonRef(
    'claude-sonnet-4-5',
    AnthropicThinkingConfigSchema
  ),
  'claude-haiku-4-5': commonRef(
    'claude-haiku-4-5',
    AnthropicThinkingConfigSchema
  ),
  'claude-opus-4-5': commonRef(
    'claude-opus-4-5',
    AnthropicThinkingConfigSchema
  ),
  'claude-opus-4-1': commonRef(
    'claude-opus-4-1',
    AnthropicThinkingConfigSchema
  ),
};

/**
 * Gets the API model ID from a model name.
 * Maps short names to full versioned names for Claude 3.x models.
 * Claude 4.x models pass through unchanged as they have API aliases.
 */
export function extractVersion(
  model: ModelReference<ConfigSchemaType> | undefined,
  modelName: string
): string {
  const cleanName = modelName.replace(/^anthropic\//, '');
  return MODEL_VERSION_MAP[cleanName] ?? cleanName;
}

/**
 * Generic Claude model info for unknown/unsupported models.
 * Used when a model name is not in KNOWN_CLAUDE_MODELS.
 */
export const GENERIC_CLAUDE_MODEL_INFO = {
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
 * Strips the 'anthropic/' namespace prefix if present.
 */
function checkModelName(name: string): string {
  return name.startsWith('anthropic/') ? name.slice(10) : name;
}

/**
 * Creates a model reference for a Claude model.
 * This allows referencing models without initializing the plugin.
 */
export function claudeModelReference(
  name: string,
  config: z.infer<typeof AnthropicConfigSchema> = {}
): ModelReference<z.ZodTypeAny> {
  const modelName = checkModelName(name);
  return modelRef({
    name: `anthropic/${modelName}`,
    config: config,
    configSchema: AnthropicConfigSchema,
    info: {
      ...GENERIC_CLAUDE_MODEL_INFO,
    },
  });
}

/**
 * Defines a Claude model with the given name and Anthropic client.
 * Accepts any model name and lets the API validate it. If the model is in KNOWN_CLAUDE_MODELS, uses that modelRef
 * for better defaults; otherwise creates a generic model reference.
 */
export function claudeModel(
  params: ClaudeModelParams
): ModelAction<z.ZodTypeAny> {
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
