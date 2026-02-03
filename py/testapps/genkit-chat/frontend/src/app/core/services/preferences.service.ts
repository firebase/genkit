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

import { effect, Injectable, signal } from '@angular/core';

/**
 * User preferences stored in localStorage.
 */
export interface UserPreferences {
  /** Selected model ID */
  selectedModel?: string;
  /** Recent model IDs (max 5) */
  recentModels?: string[];
  /** Streaming mode enabled */
  streamingMode?: boolean;
  /** Markdown rendering enabled */
  markdownMode?: boolean;
  /** Content safety enabled */
  contentSafetyEnabled?: boolean;
  /** Theme preference */
  theme?: 'light' | 'dark' | 'system';
  /** Language code */
  language?: string;
}

const STORAGE_KEY = 'genkit-chat-preferences';
const MAX_RECENT_MODELS = 5;

/**
 * Service for persisting and retrieving user preferences from localStorage.
 *
 * Key Concepts:
 * ┌─────────────────────┬────────────────────────────────────────────────┐
 * │ Concept             │ Description                                    │
 * ├─────────────────────┼────────────────────────────────────────────────┤
 * │ Preferences         │ User settings that persist across sessions     │
 * │ localStorage        │ Browser storage that persists until cleared    │
 * │ Reactive signals    │ Angular signals for reactive updates           │
 * └─────────────────────┴────────────────────────────────────────────────┘
 */
@Injectable({
  providedIn: 'root',
})
export class PreferencesService {
  /** Current preferences (reactive) */
  preferences = signal<UserPreferences>(this.load());

  constructor() {
    // Auto-save when preferences change
    effect(() => {
      this.save(this.preferences());
    });
  }

  /**
   * Load preferences from localStorage.
   */
  private load(): UserPreferences {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored) as UserPreferences;
      }
    } catch (_e) {}
    return this.getDefaults();
  }

  /**
   * Save preferences to localStorage.
   */
  private save(prefs: UserPreferences): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    } catch (_e) {}
  }

  /**
   * Get default preferences.
   */
  private getDefaults(): UserPreferences {
    return {
      streamingMode: true,
      markdownMode: true,
      contentSafetyEnabled: true,
      theme: 'system',
      recentModels: [],
    };
  }

  // ────────────────────────────────────────────────────────────────
  // Getters
  // ────────────────────────────────────────────────────────────────

  get selectedModel(): string | undefined {
    return this.preferences().selectedModel;
  }

  get recentModels(): string[] {
    return this.preferences().recentModels || [];
  }

  get streamingMode(): boolean {
    return this.preferences().streamingMode ?? true;
  }

  get markdownMode(): boolean {
    return this.preferences().markdownMode ?? true;
  }

  get contentSafetyEnabled(): boolean {
    return this.preferences().contentSafetyEnabled ?? true;
  }

  get theme(): 'light' | 'dark' | 'system' {
    return this.preferences().theme ?? 'system';
  }

  get language(): string | undefined {
    return this.preferences().language;
  }

  // ────────────────────────────────────────────────────────────────
  // Setters (update individual preferences)
  // ────────────────────────────────────────────────────────────────

  setSelectedModel(modelId: string): void {
    this.preferences.update((p) => ({
      ...p,
      selectedModel: modelId,
    }));
    this.addRecentModel(modelId);
  }

  addRecentModel(modelId: string): void {
    this.preferences.update((p) => {
      const recent = (p.recentModels || []).filter((m) => m !== modelId);
      recent.unshift(modelId);
      return {
        ...p,
        recentModels: recent.slice(0, MAX_RECENT_MODELS),
      };
    });
  }

  setStreamingMode(enabled: boolean): void {
    this.preferences.update((p) => ({
      ...p,
      streamingMode: enabled,
    }));
  }

  setMarkdownMode(enabled: boolean): void {
    this.preferences.update((p) => ({
      ...p,
      markdownMode: enabled,
    }));
  }

  setContentSafetyEnabled(enabled: boolean): void {
    this.preferences.update((p) => ({
      ...p,
      contentSafetyEnabled: enabled,
    }));
  }

  setTheme(theme: 'light' | 'dark' | 'system'): void {
    this.preferences.update((p) => ({
      ...p,
      theme,
    }));
  }

  setLanguage(languageCode: string): void {
    this.preferences.update((p) => ({
      ...p,
      language: languageCode,
    }));
  }

  // ────────────────────────────────────────────────────────────────
  // Clear all preferences
  // ────────────────────────────────────────────────────────────────

  /**
   * Clear all stored preferences and reset to defaults.
   */
  clearAll(): void {
    localStorage.removeItem(STORAGE_KEY);
    this.preferences.set(this.getDefaults());
  }

  /**
   * Check if there are any stored preferences.
   */
  hasStoredPreferences(): boolean {
    return localStorage.getItem(STORAGE_KEY) !== null;
  }
}
