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
import { Injectable, inject, signal } from '@angular/core';
import { catchError, of } from 'rxjs';
import { PreferencesService } from './preferences.service';

export interface ModelInfo {
  id: string;
  name: string;
  capabilities: string[];
  context_window: number;
  supportsStreaming?: boolean;
}

export interface ProviderInfo {
  id: string;
  name: string;
  available: boolean;
  models: ModelInfo[];
}

export interface ModelsResponse {
  providers: ProviderInfo[];
}

// Default models when backend is unavailable - only latest, non-deprecated models
const DEFAULT_PROVIDERS: ProviderInfo[] = [
  {
    id: 'googleai',
    name: 'Google AI',
    available: true,
    models: [
      {
        id: 'googleai/gemini-3-flash-preview',
        name: 'Gemini 3 Flash Preview',
        capabilities: ['text', 'vision'],
        context_window: 1048576,
      },
      {
        id: 'googleai/gemini-3-pro-preview',
        name: 'Gemini 3 Pro Preview',
        capabilities: ['text', 'vision'],
        context_window: 2097152,
      },
      {
        id: 'googleai/gemini-2.5-flash',
        name: 'Gemini 2.5 Flash',
        capabilities: ['text', 'vision'],
        context_window: 1048576,
      },
      {
        id: 'googleai/gemini-2.5-pro',
        name: 'Gemini 2.5 Pro',
        capabilities: ['text', 'vision'],
        context_window: 1048576,
      },
    ],
  },
  {
    id: 'vertexai',
    name: 'Vertex AI',
    available: true,
    models: [
      {
        id: 'vertexai/gemini-3-flash',
        name: 'Gemini 3 Flash',
        capabilities: ['text', 'vision'],
        context_window: 1048576,
      },
      {
        id: 'vertexai/gemini-3-pro',
        name: 'Gemini 3 Pro',
        capabilities: ['text', 'vision'],
        context_window: 2097152,
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
        capabilities: ['text', 'vision'],
        context_window: 200000,
      },
      {
        id: 'anthropic/claude-sonnet-4-5',
        name: 'Claude Sonnet 4.5',
        capabilities: ['text', 'vision'],
        context_window: 200000,
      },
      {
        id: 'anthropic/claude-haiku-4-5',
        name: 'Claude Haiku 4.5',
        capabilities: ['text', 'vision'],
        context_window: 200000,
      },
    ],
  },
  {
    id: 'openai',
    name: 'OpenAI',
    available: true,
    models: [
      {
        id: 'openai/gpt-4.1',
        name: 'GPT-4.1',
        capabilities: ['text', 'vision'],
        context_window: 1047576,
      },
      {
        id: 'openai/gpt-4.1-mini',
        name: 'GPT-4.1 Mini',
        capabilities: ['text', 'vision'],
        context_window: 1047576,
      },
      {
        id: 'openai/gpt-4.1-nano',
        name: 'GPT-4.1 Nano',
        capabilities: ['text'],
        context_window: 1047576,
      },
      { id: 'openai/o3', name: 'o3', capabilities: ['text', 'reasoning'], context_window: 200000 },
      {
        id: 'openai/o4-mini',
        name: 'o4 Mini',
        capabilities: ['text', 'reasoning'],
        context_window: 200000,
      },
    ],
  },
  {
    id: 'mistral',
    name: 'Mistral AI',
    available: true,
    models: [
      {
        id: 'mistral/mistral-large-latest',
        name: 'Mistral Large',
        capabilities: ['text'],
        context_window: 128000,
      },
      {
        id: 'mistral/mistral-small-latest',
        name: 'Mistral Small',
        capabilities: ['text'],
        context_window: 32000,
      },
      {
        id: 'mistral/codestral-latest',
        name: 'Codestral',
        capabilities: ['text', 'code'],
        context_window: 32000,
      },
    ],
  },
  {
    id: 'cf-ai',
    name: 'Cloudflare AI',
    available: true,
    models: [
      {
        id: 'cf-ai/@cf/meta/llama-3.3-70b-instruct-fp8-fast',
        name: 'Llama 3.3 70B FP8 Fast',
        capabilities: ['text'],
        context_window: 8192,
      },
      {
        id: 'cf-ai/@cf/meta/llama-3.1-8b-instruct',
        name: 'Llama 3.1 8B',
        capabilities: ['text'],
        context_window: 8192,
      },
      {
        id: 'cf-ai/@cf/google/gemma-3-12b-it',
        name: 'Gemma 3 12B (Vision)',
        capabilities: ['text', 'vision'],
        context_window: 8192,
      },
      {
        id: 'cf-ai/@cf/mistral/mistral-small-3.1-24b-instruct',
        name: 'Mistral Small 3.1 24B (Vision)',
        capabilities: ['text', 'vision'],
        context_window: 8192,
      },
      {
        id: 'cf-ai/@cf/deepseek-ai/deepseek-r1-distill-qwen-32b',
        name: 'DeepSeek R1 32B',
        capabilities: ['text', 'reasoning'],
        context_window: 32000,
      },
      {
        id: 'cf-ai/@cf/qwen/qwen2.5-coder-32b-instruct',
        name: 'Qwen 2.5 Coder 32B',
        capabilities: ['text', 'code'],
        context_window: 32000,
      },
    ],
  },
  {
    id: 'ollama',
    name: 'Ollama (Local)',
    available: true,
    models: [
      { id: 'ollama/llama3.2', name: 'Llama 3.2', capabilities: ['text'], context_window: 128000 },
      {
        id: 'ollama/gemma3:4b',
        name: 'Gemma 3 4B',
        capabilities: ['text'],
        context_window: 128000,
      },
      { id: 'ollama/mistral', name: 'Mistral', capabilities: ['text'], context_window: 32768 },
      {
        id: 'ollama/qwen2.5-coder',
        name: 'Qwen 2.5 Coder',
        capabilities: ['text', 'code'],
        context_window: 128000,
      },
    ],
  },
];

const DEFAULT_MODEL = 'ollama/gemma3:4b';

@Injectable({
  providedIn: 'root',
})
export class ModelsService {
  private http = inject(HttpClient);
  private preferencesService = inject(PreferencesService);
  private apiUrl = '/api';
  private readonly MAX_RECENT = 3;

  providers = signal<ProviderInfo[]>(DEFAULT_PROVIDERS);
  // Load selected model from preferences, fallback to default
  selectedModel = signal<string>(this.preferencesService.selectedModel || DEFAULT_MODEL);
  // Load recent models from preferences
  recentModels = signal<string[]>(this.preferencesService.recentModels);
  isLoading = signal(false);
  isBackendConnected = signal(false);

  constructor() {
    this.loadModels();
  }

  loadModels(): void {
    this.isLoading.set(true);
    this.http
      .get<ModelsResponse>(`${this.apiUrl}/models`)
      .pipe(
        catchError((_error) => {
          this.isBackendConnected.set(false);
          return of({ providers: DEFAULT_PROVIDERS });
        })
      )
      .subscribe((response) => {
        if (response.providers.length > 0) {
          this.providers.set(response.providers);
          this.isBackendConnected.set(true);
        }
        this.isLoading.set(false);
      });
  }

  getAllModels(): ModelInfo[] {
    return this.providers().flatMap((p) => p.models);
  }

  /** Get all models sorted lexicographically by name */
  getSortedModels(): ModelInfo[] {
    return this.getAllModels().sort((a, b) => a.name.localeCompare(b.name));
  }

  /** Get models filtered by search query */
  filterModels(query: string): ModelInfo[] {
    const q = query.toLowerCase().trim();
    if (!q) return this.getSortedModels();
    return this.getSortedModels().filter(
      (m) => m.name.toLowerCase().includes(q) || m.id.toLowerCase().includes(q)
    );
  }

  /** Get models for a provider, sorted alphabetically */
  getModelsByProvider(providerId: string): ModelInfo[] {
    const provider = this.providers().find((p) => p.id === providerId);
    return (provider?.models || []).sort((a, b) => a.name.localeCompare(b.name));
  }

  getModelName(modelId: string): string {
    const model = this.getAllModels().find((m) => m.id === modelId);
    return model?.name || modelId.split('/').pop() || modelId;
  }

  getProviderName(modelId: string): string {
    const providerId = modelId.split('/')[0];
    const provider = this.providers().find((p) => p.id === providerId);
    return provider?.name || providerId;
  }

  /** Select a model and add to recent */
  selectModel(modelId: string): void {
    this.selectedModel.set(modelId);
    this.preferencesService.setSelectedModel(modelId);
    this.addToRecent(modelId);
  }

  /** Get recent models as ModelInfo objects */
  getRecentModels(): ModelInfo[] {
    const all = this.getAllModels();
    return this.recentModels()
      .map((id) => all.find((m) => m.id === id))
      .filter((m): m is ModelInfo => m !== undefined);
  }

  private addToRecent(modelId: string): void {
    const recent = this.recentModels().filter((id) => id !== modelId);
    recent.unshift(modelId);
    const updated = recent.slice(0, this.MAX_RECENT);
    this.recentModels.set(updated);
    // PreferencesService handles persistence via setSelectedModel
  }

  /** Check if the selected model supports streaming */
  supportsStreaming(modelId?: string): boolean {
    const id = modelId || this.selectedModel();
    // Ollama models may have unreliable streaming support
    // For now, assume all cloud models support streaming
    if (id.startsWith('ollama/')) {
      return false;
    }
    // Check if model explicitly declares streaming support
    const model = this.getAllModels().find((m) => m.id === id);
    if (model?.supportsStreaming !== undefined) {
      return model.supportsStreaming;
    }
    // Default: all non-Ollama models support streaming
    return true;
  }
}
