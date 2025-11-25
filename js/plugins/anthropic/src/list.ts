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
import { modelActionMetadata } from 'genkit/plugin';

import { ActionMetadata, ModelReference, z } from 'genkit';
import { GENERIC_CLAUDE_MODEL_INFO, KNOWN_CLAUDE_MODELS } from './models.js';
import { AnthropicConfigSchema } from './types.js';

function normalizeModelId(modelId: string): string {
  // Strip date suffixes (e.g. "-20241001") or "-latest" so lookups hit canonical keys.
  return modelId.replace(/-(?:\d{8}|latest)$/i, '');
}

type ModelMetadataParams = Parameters<typeof modelActionMetadata>[0];

interface MergeKnownModelMetadataParams {
  modelId: string;
  ref: ModelReference<z.ZodTypeAny>;
  metadataByName: Map<string, ModelMetadataParams>;
  orderedNames: string[];
}
/**
 * Integrates metadata for a known Claude model into the aggregated list.
 *
 * It merges version information collected from the Anthropic API onto the
 * canonical model definition while preserving any additional metadata that
 * may already exist in the accumulator.
 */
function mergeKnownModelMetadata({
  modelId,
  ref,
  metadataByName,
  orderedNames,
}: MergeKnownModelMetadataParams): void {
  // Merge onto any prior metadata we have for this named model.
  const existing = metadataByName.get(ref.name);
  const priorInfo = existing?.info ?? ref.info ?? {};
  const priorVersions = Array.isArray(priorInfo.versions)
    ? priorInfo.versions
    : (ref.info?.versions ?? []);

  // Track every concrete model ID surfaced by the API so they appear as selectable versions.
  const versions = new Set<string>(priorVersions);
  versions.add(modelId);

  metadataByName.set(ref.name, {
    name: ref.name,
    info: {
      ...priorInfo,
      versions: Array.from(versions),
    },
    configSchema: ref.configSchema,
  });

  if (!existing) {
    // Preserve the discovery order for determinism.
    orderedNames.push(ref.name);
  }
}

interface MergeFallbackModelMetadataParams {
  modelId: string;
  normalizedId: string;
  displayName?: string;
  metadataByName: Map<string, ModelMetadataParams>;
  orderedNames: string[];
}

/**
 * Creates or updates metadata entries for Anthropic models that are not
 * explicitly enumerated in `KNOWN_CLAUDE_MODELS`.
 *
 * The resulting metadata uses a generic Claude descriptor while capturing
 * the specific model ID returned by the API so it can be surfaced in the
 * Genkit UI.
 */
function mergeFallbackModelMetadata({
  modelId,
  normalizedId,
  displayName,
  metadataByName,
  orderedNames,
}: MergeFallbackModelMetadataParams): void {
  const fallbackName = `anthropic/${modelId}`;
  const existing = metadataByName.get(fallbackName);
  const fallbackLabel =
    displayName ??
    `Anthropic - ${normalizedId !== modelId ? normalizedId : modelId}`;

  if (existing) {
    const priorVersions = existing.info?.versions ?? [];
    const versions = new Set<string>(
      Array.isArray(priorVersions) ? priorVersions : []
    );
    versions.add(modelId);

    metadataByName.set(fallbackName, {
      ...existing,
      info: {
        ...existing.info,
        versions: Array.from(versions),
      },
    });
    return;
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

/**
 * Retrieves available Anthropic models from the API and converts them into Genkit action metadata.
 *
 * This function queries the Anthropic API for the list of available models, matches them against
 * known Claude models, and generates metadata for both known and unknown models. The resulting
 * metadata includes version information and configuration schemas suitable for use in Genkit.
 *
 * @param client - The Anthropic API client instance
 * @returns A promise that resolves to an array of action metadata for all discovered models
 */
export async function listActions(
  client: Anthropic
): Promise<ActionMetadata[]> {
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
      mergeKnownModelMetadata({
        modelId,
        ref,
        metadataByName,
        orderedNames,
      });
      continue;
    }

    // For models we don't explicitly track, synthesize a generic entry that still surfaces the ID.
    mergeFallbackModelMetadata({
      modelId,
      normalizedId,
      displayName: modelInfo.display_name ?? undefined,
      metadataByName,
      orderedNames,
    });
  }

  return orderedNames.map((name) => {
    const metadata = metadataByName.get(name);
    if (!metadata) {
      throw new Error(`Missing metadata for model: ${name}`);
    }
    return modelActionMetadata(metadata);
  });
}
