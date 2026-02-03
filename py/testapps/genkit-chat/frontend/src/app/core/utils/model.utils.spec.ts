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

import { describe, expect, it } from 'vitest';
import type { Model, Provider } from '../services/model.service';
import {
  filterByCapability,
  filterByProvider,
  findModelById,
  flattenModels,
  getDefaultModelId,
  getProviderName,
  groupByProvider,
  hasCapability,
  searchModels,
} from './model.utils';

const mockProviders: Provider[] = [
  {
    id: 'googleai',
    name: 'Google AI',
    models: [
      { id: 'googleai/gemini-pro', name: 'Gemini Pro', capabilities: ['text', 'vision'] },
      { id: 'googleai/gemini-flash', name: 'Gemini Flash', capabilities: ['text'] },
    ],
  },
  {
    id: 'openai',
    name: 'OpenAI',
    models: [{ id: 'openai/gpt-4', name: 'GPT-4', capabilities: ['text', 'code'] }],
  },
];

describe('model.utils', () => {
  describe('flattenModels', () => {
    it('should flatten providers into models with provider info', () => {
      const result = flattenModels(mockProviders);
      expect(result).toHaveLength(3);
      expect(result[0].provider).toBe('Google AI');
      expect(result[0].providerId).toBe('googleai');
    });

    it('should handle empty providers', () => {
      const result = flattenModels([]);
      expect(result).toHaveLength(0);
    });

    it('should handle provider with no models', () => {
      const providers: Provider[] = [{ id: 'empty', name: 'Empty', models: [] }];
      const result = flattenModels(providers);
      expect(result).toHaveLength(0);
    });
  });

  describe('findModelById', () => {
    const models = flattenModels(mockProviders);

    it('should find model by ID', () => {
      const result = findModelById(models, 'googleai/gemini-pro');
      expect(result?.name).toBe('Gemini Pro');
    });

    it('should return undefined for unknown ID', () => {
      const result = findModelById(models, 'unknown');
      expect(result).toBeUndefined();
    });
  });

  describe('getProviderName', () => {
    const models = flattenModels(mockProviders);

    it('should return provider name for model', () => {
      const result = getProviderName(models, 'googleai/gemini-pro');
      expect(result).toBe('Google AI');
    });

    it('should return Unknown for unknown model', () => {
      const result = getProviderName(models, 'unknown');
      expect(result).toBe('Unknown');
    });
  });

  describe('hasCapability', () => {
    const allModels: Model[] = mockProviders.flatMap((p) => p.models);

    it('should return true if model has capability', () => {
      expect(hasCapability(allModels, 'googleai/gemini-pro', 'vision')).toBe(true);
    });

    it('should return false if model lacks capability', () => {
      expect(hasCapability(allModels, 'googleai/gemini-flash', 'vision')).toBe(false);
    });

    it('should return false for unknown model', () => {
      expect(hasCapability(allModels, 'unknown', 'text')).toBe(false);
    });
  });

  describe('filterByProvider', () => {
    const models = flattenModels(mockProviders);

    it('should filter models by provider', () => {
      const result = filterByProvider(models, 'googleai');
      expect(result).toHaveLength(2);
      expect(result.every((m) => m.providerId === 'googleai')).toBe(true);
    });

    it('should return empty for unknown provider', () => {
      const result = filterByProvider(models, 'unknown');
      expect(result).toHaveLength(0);
    });
  });

  describe('filterByCapability', () => {
    const allModels: Model[] = mockProviders.flatMap((p) => p.models);

    it('should filter models with capability', () => {
      const result = filterByCapability(allModels, 'vision');
      expect(result).toHaveLength(1);
      expect(result[0].id).toBe('googleai/gemini-pro');
    });

    it('should return multiple matches', () => {
      const result = filterByCapability(allModels, 'text');
      expect(result.length).toBeGreaterThanOrEqual(2);
    });

    it('should return empty for unknown capability', () => {
      const result = filterByCapability(allModels, 'unknown');
      expect(result).toHaveLength(0);
    });
  });

  describe('searchModels', () => {
    const models = flattenModels(mockProviders);

    it('should search by name', () => {
      const result = searchModels(models, 'Gemini');
      expect(result).toHaveLength(2);
    });

    it('should search by ID', () => {
      const result = searchModels(models, 'gpt-4');
      expect(result).toHaveLength(1);
    });

    it('should search by provider', () => {
      const result = searchModels(models, 'OpenAI');
      expect(result).toHaveLength(1);
    });

    it('should be case insensitive', () => {
      const result = searchModels(models, 'GEMINI');
      expect(result).toHaveLength(2);
    });

    it('should return all for empty query', () => {
      const result = searchModels(models, '');
      expect(result).toHaveLength(3);
    });

    it('should return all for whitespace query', () => {
      const result = searchModels(models, '   ');
      expect(result).toHaveLength(3);
    });
  });

  describe('groupByProvider', () => {
    const models = flattenModels(mockProviders);

    it('should group models by provider', () => {
      const result = groupByProvider(models);
      expect(result.size).toBe(2);
      expect(result.get('googleai')?.length).toBe(2);
      expect(result.get('openai')?.length).toBe(1);
    });

    it('should handle empty array', () => {
      const result = groupByProvider([]);
      expect(result.size).toBe(0);
    });
  });

  describe('getDefaultModelId', () => {
    const models: Model[] = [
      { id: 'model-1', name: 'Model 1' },
      { id: 'model-2', name: 'Model 2' },
    ];

    it('should return first model ID', () => {
      const result = getDefaultModelId(models);
      expect(result).toBe('model-1');
    });

    it('should return fallback for empty array', () => {
      const result = getDefaultModelId([]);
      expect(result).toBe('ollama/llama3.2');
    });

    it('should accept custom fallback', () => {
      const result = getDefaultModelId([], 'custom-fallback');
      expect(result).toBe('custom-fallback');
    });
  });
});
