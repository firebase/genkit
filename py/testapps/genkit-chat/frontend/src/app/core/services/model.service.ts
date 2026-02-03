/**
 * Copyright 2026 Google LLC
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
 *
 * SPDX-License-Identifier: Apache-2.0
 */

import { HttpClient } from '@angular/common/http';
import { computed, Injectable, inject, signal } from '@angular/core';
import { catchError, of, tap } from 'rxjs';

/**
 * Model information from the backend.
 */
export interface Model {
  id: string;
  name: string;
  capabilities: string[];
  context_window?: number;
}

/**
 * Provider with available models.
 */
export interface Provider {
  id: string;
  name: string;
  available: boolean;
  models: Model[];
}

/**
 * Service for fetching available models from the backend.
 * Falls back to demo models if backend is unavailable.
 */
@Injectable({
  providedIn: 'root',
})
export class ModelService {
  private http = inject(HttpClient);
  private apiUrl = '/api';

  // All providers with their models
  providers = signal<Provider[]>([]);
  isLoading = signal(false);
  error = signal<string | null>(null);

  // Flattened list of all available models
  allModels = computed(() =>
    this.providers().flatMap((p) =>
      p.models.map((m) => ({
        ...m,
        provider: p.name,
        providerId: p.id,
      }))
    )
  );

  // Default model (first available or Ollama local)
  defaultModel = computed(() => this.allModels()[0]?.id || 'ollama/llama3.2');

  // Demo models for when backend is unavailable
  private readonly DEMO_PROVIDERS: Provider[] = [
    {
      id: 'google-genai',
      name: 'Google AI',
      available: true,
      models: [
        {
          id: 'googleai/gemini-3-flash-preview',
          name: 'Gemini 3 Flash Preview',
          capabilities: ['text', 'vision', 'streaming'],
        },
        {
          id: 'googleai/gemini-3-pro-preview',
          name: 'Gemini 3 Pro Preview',
          capabilities: ['text', 'vision', 'streaming'],
        },
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
          id: 'anthropic/claude-opus-4-5',
          name: 'Claude Opus 4.5',
          capabilities: ['text', 'vision', 'streaming'],
        },
        {
          id: 'anthropic/claude-sonnet-4-5',
          name: 'Claude Sonnet 4.5',
          capabilities: ['text', 'vision', 'streaming'],
        },
        {
          id: 'anthropic/claude-haiku-4-5',
          name: 'Claude Haiku 4.5',
          capabilities: ['text', 'vision', 'streaming'],
        },
      ],
    },
    {
      id: 'openai',
      name: 'OpenAI',
      available: true,
      models: [
        { id: 'openai/gpt-4.1', name: 'GPT-4.1', capabilities: ['text', 'vision', 'streaming'] },
        { id: 'openai/gpt-4o', name: 'GPT-4o', capabilities: ['text', 'vision', 'streaming'] },
      ],
    },
  ];

  constructor() {
    // Fetch models on service initialization
    this.fetchModels();
  }

  /**
   * Fetch available models from the backend.
   * Falls back to demo models if backend is unavailable.
   */
  fetchModels(): void {
    this.isLoading.set(true);
    this.error.set(null);

    this.http
      .get<Provider[]>(`${this.apiUrl}/models`)
      .pipe(
        tap((providers) => {
          this.providers.set(providers);
          this.isLoading.set(false);
        }),
        catchError((_err) => {
          this.providers.set(this.DEMO_PROVIDERS);
          this.error.set('Using demo models (backend unavailable)');
          this.isLoading.set(false);
          return of(this.DEMO_PROVIDERS);
        })
      )
      .subscribe();
  }

  /**
   * Get a model by its ID.
   */
  getModel(id: string): Model | undefined {
    return this.allModels().find((m) => m.id === id);
  }

  /**
   * Get the provider name for a model ID.
   */
  getProviderName(modelId: string): string {
    const model = this.allModels().find((m) => m.id === modelId);
    return model?.provider || 'Unknown';
  }

  /**
   * Check if a model supports a capability.
   */
  hasCapability(modelId: string, capability: string): boolean {
    const model = this.getModel(modelId);
    return model?.capabilities?.includes(capability) ?? false;
  }
}
