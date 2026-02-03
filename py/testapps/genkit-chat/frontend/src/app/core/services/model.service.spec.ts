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
import type { Model, Provider } from './model.service';

// Test the data structures and pure logic without Angular's HttpClient dependency
// Following the "Logic-First" testing pattern from GEMINI.md

describe('ModelService data structures', () => {
  describe('Model interface', () => {
    it('should accept basic model', () => {
      const model: Model = {
        id: 'googleai/gemini-2.0-flash',
        name: 'Gemini 2.0 Flash',
        capabilities: ['text', 'streaming'],
      };
      expect(model.id).toBe('googleai/gemini-2.0-flash');
      expect(model.name).toBe('Gemini 2.0 Flash');
      expect(model.capabilities).toContain('text');
    });

    it('should accept model with context window', () => {
      const model: Model = {
        id: 'openai/gpt-4o',
        name: 'GPT-4o',
        capabilities: ['text', 'vision'],
        context_window: 128000,
      };
      expect(model.context_window).toBe(128000);
    });

    it('should accept model with vision capability', () => {
      const model: Model = {
        id: 'anthropic/claude-sonnet-4',
        name: 'Claude Sonnet 4',
        capabilities: ['text', 'vision', 'streaming'],
      };
      expect(model.capabilities).toContain('vision');
    });
  });

  describe('Provider interface', () => {
    it('should accept provider with models', () => {
      const provider: Provider = {
        id: 'google-genai',
        name: 'Google AI',
        available: true,
        models: [
          { id: 'googleai/gemini-2.0-flash', name: 'Gemini 2.0 Flash', capabilities: ['text'] },
        ],
      };
      expect(provider.id).toBe('google-genai');
      expect(provider.models.length).toBe(1);
    });

    it('should handle unavailable provider', () => {
      const provider: Provider = {
        id: 'ollama',
        name: 'Ollama (Local)',
        available: false,
        models: [],
      };
      expect(provider.available).toBe(false);
      expect(provider.models).toHaveLength(0);
    });
  });
});

describe('ModelService pure logic', () => {
  const mockProviders: Provider[] = [
    {
      id: 'google-genai',
      name: 'Google AI',
      available: true,
      models: [
        {
          id: 'googleai/gemini-2.5-flash',
          name: 'Gemini 2.5 Flash',
          capabilities: ['text', 'vision', 'streaming'],
        },
        {
          id: 'googleai/gemini-2.5-pro',
          name: 'Gemini 2.5 Pro',
          capabilities: ['text', 'vision', 'streaming'],
        },
      ],
    },
    {
      id: 'anthropic',
      name: 'Anthropic',
      available: true,
      models: [
        {
          id: 'anthropic/claude-sonnet-4',
          name: 'Claude Sonnet 4',
          capabilities: ['text', 'vision'],
        },
      ],
    },
    {
      id: 'openai',
      name: 'OpenAI',
      available: true,
      models: [
        { id: 'openai/gpt-4o', name: 'GPT-4o', capabilities: ['text', 'vision', 'streaming'] },
      ],
    },
  ];

  describe('allModels computed logic', () => {
    it('should flatten all models from providers', () => {
      const allModels = mockProviders.flatMap((p) =>
        p.models.map((m) => ({
          ...m,
          provider: p.name,
          providerId: p.id,
        }))
      );

      expect(allModels).toHaveLength(4);
      expect(allModels[0].id).toBe('googleai/gemini-2.5-flash');
      expect(allModels[0].provider).toBe('Google AI');
    });

    it('should include provider info in flattened models', () => {
      const allModels = mockProviders.flatMap((p) =>
        p.models.map((m) => ({
          ...m,
          provider: p.name,
          providerId: p.id,
        }))
      );

      const anthropicModel = allModels.find((m) => m.id === 'anthropic/claude-sonnet-4');
      expect(anthropicModel?.provider).toBe('Anthropic');
      expect(anthropicModel?.providerId).toBe('anthropic');
    });
  });

  describe('defaultModel computed logic', () => {
    it('should return first model id when available', () => {
      const allModels = mockProviders.flatMap((p) => p.models);
      const defaultModel = allModels[0]?.id || 'ollama/llama3.2';
      expect(defaultModel).toBe('googleai/gemini-2.5-flash');
    });

    it('should return fallback when no models available', () => {
      const emptyProviders: Provider[] = [];
      const allModels = emptyProviders.flatMap((p) => p.models);
      const defaultModel = allModels[0]?.id || 'ollama/llama3.2';
      expect(defaultModel).toBe('ollama/llama3.2');
    });
  });

  describe('getModel logic', () => {
    it('should find model by id', () => {
      const allModels = mockProviders.flatMap((p) => p.models);
      const found = allModels.find((m) => m.id === 'openai/gpt-4o');
      expect(found?.name).toBe('GPT-4o');
    });

    it('should return undefined for unknown id', () => {
      const allModels = mockProviders.flatMap((p) => p.models);
      const found = allModels.find((m) => m.id === 'unknown/model');
      expect(found).toBeUndefined();
    });
  });

  describe('getProviderName logic', () => {
    it('should return provider name for model id', () => {
      const allModels = mockProviders.flatMap((p) =>
        p.models.map((m) => ({
          ...m,
          provider: p.name,
        }))
      );
      const model = allModels.find((m) => m.id === 'anthropic/claude-sonnet-4');
      const providerName = model?.provider || 'Unknown';
      expect(providerName).toBe('Anthropic');
    });

    it('should return Unknown for missing model', () => {
      const allModels = mockProviders.flatMap((p) =>
        p.models.map((m) => ({
          ...m,
          provider: p.name,
        }))
      );
      const model = allModels.find((m) => m.id === 'nonexistent');
      const providerName = model?.provider || 'Unknown';
      expect(providerName).toBe('Unknown');
    });
  });

  describe('hasCapability logic', () => {
    it('should return true for existing capability', () => {
      const allModels = mockProviders.flatMap((p) => p.models);
      const model = allModels.find((m) => m.id === 'googleai/gemini-2.5-flash');
      const hasStreaming = model?.capabilities?.includes('streaming') ?? false;
      expect(hasStreaming).toBe(true);
    });

    it('should return false for missing capability', () => {
      const allModels = mockProviders.flatMap((p) => p.models);
      const model = allModels.find((m) => m.id === 'anthropic/claude-sonnet-4');
      const hasStreaming = model?.capabilities?.includes('streaming') ?? false;
      expect(hasStreaming).toBe(false);
    });

    it('should return false for undefined model', () => {
      const allModels = mockProviders.flatMap((p) => p.models);
      const model = allModels.find((m) => m.id === 'nonexistent');
      const hasStreaming = model?.capabilities?.includes('streaming') ?? false;
      expect(hasStreaming).toBe(false);
    });
  });
});

describe('Model filtering and search', () => {
  const allModels = [
    {
      id: 'googleai/gemini-2.5-flash',
      name: 'Gemini 2.5 Flash',
      capabilities: ['text', 'vision'],
      provider: 'Google AI',
    },
    {
      id: 'googleai/gemini-2.5-pro',
      name: 'Gemini 2.5 Pro',
      capabilities: ['text', 'vision'],
      provider: 'Google AI',
    },
    {
      id: 'anthropic/claude-sonnet-4',
      name: 'Claude Sonnet 4',
      capabilities: ['text', 'vision'],
      provider: 'Anthropic',
    },
    {
      id: 'openai/gpt-4o',
      name: 'GPT-4o',
      capabilities: ['text', 'vision', 'audio'],
      provider: 'OpenAI',
    },
  ];

  it('should filter models by provider', () => {
    const googleModels = allModels.filter((m) => m.provider === 'Google AI');
    expect(googleModels).toHaveLength(2);
  });

  it('should filter models by capability', () => {
    const audioModels = allModels.filter((m) => m.capabilities.includes('audio'));
    expect(audioModels).toHaveLength(1);
    expect(audioModels[0].name).toBe('GPT-4o');
  });

  it('should search models by name (case insensitive)', () => {
    const searchTerm = 'gemini';
    const results = allModels.filter((m) =>
      m.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
    expect(results).toHaveLength(2);
  });

  it('should search models by id', () => {
    const searchTerm = 'claude';
    const results = allModels.filter((m) => m.id.includes(searchTerm));
    expect(results).toHaveLength(1);
  });
});
