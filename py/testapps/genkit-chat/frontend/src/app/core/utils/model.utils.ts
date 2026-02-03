// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

/**
 * Pure utility functions for model operations.
 * These functions have no Angular dependencies and are easily testable.
 */

import type { Model, Provider } from '../services/model.service';

/**
 * Model with provider information.
 */
export interface ModelWithProvider extends Model {
  provider: string;
  providerId: string;
}

/**
 * Flatten providers into a list of models with provider info.
 */
export function flattenModels(providers: Provider[]): ModelWithProvider[] {
  return providers.flatMap((p) =>
    p.models.map((m) => ({
      ...m,
      provider: p.name,
      providerId: p.id,
    }))
  );
}

/**
 * Find a model by ID from the flattened list.
 */
export function findModelById(
  models: ModelWithProvider[],
  id: string
): ModelWithProvider | undefined {
  return models.find((m) => m.id === id);
}

/**
 * Get the provider name for a model ID.
 */
export function getProviderName(models: ModelWithProvider[], modelId: string): string {
  const model = findModelById(models, modelId);
  return model?.provider || 'Unknown';
}

/**
 * Check if a model has a specific capability.
 */
export function hasCapability(models: Model[], modelId: string, capability: string): boolean {
  const model = models.find((m) => m.id === modelId);
  return model?.capabilities?.includes(capability) ?? false;
}

/**
 * Filter models by provider.
 */
export function filterByProvider(
  models: ModelWithProvider[],
  providerId: string
): ModelWithProvider[] {
  return models.filter((m) => m.providerId === providerId);
}

/**
 * Filter models by capability.
 */
export function filterByCapability(models: Model[], capability: string): Model[] {
  return models.filter((m) => m.capabilities?.includes(capability));
}

/**
 * Search models by name or ID (case insensitive).
 */
export function searchModels(models: ModelWithProvider[], query: string): ModelWithProvider[] {
  if (!query.trim()) return models;

  const lowerQuery = query.toLowerCase();
  return models.filter(
    (m) =>
      m.name.toLowerCase().includes(lowerQuery) ||
      m.id.toLowerCase().includes(lowerQuery) ||
      m.provider.toLowerCase().includes(lowerQuery)
  );
}

/**
 * Group models by provider.
 */
export function groupByProvider(models: ModelWithProvider[]): Map<string, ModelWithProvider[]> {
  const grouped = new Map<string, ModelWithProvider[]>();

  for (const model of models) {
    const existing = grouped.get(model.providerId) || [];
    grouped.set(model.providerId, [...existing, model]);
  }

  return grouped;
}

/**
 * Get the default model ID.
 */
export function getDefaultModelId(models: Model[], fallback = 'ollama/llama3.2'): string {
  return models[0]?.id || fallback;
}
