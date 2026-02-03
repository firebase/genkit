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
 * Pure utility functions for user preferences.
 * These functions have no Angular dependencies and are easily testable.
 */

import type { UserPreferences } from '../services/preferences.service';

/**
 * Storage key for preferences.
 */
export const PREFERENCES_STORAGE_KEY = 'genkit-chat-preferences';

/**
 * Maximum number of recent models to track.
 */
export const MAX_RECENT_MODELS = 5;

/**
 * Get default preferences.
 */
export function getDefaultPreferences(): UserPreferences {
  return {
    streamingMode: true,
    markdownMode: true,
    contentSafetyEnabled: true,
    theme: 'system',
    recentModels: [],
  };
}

/**
 * Add a model to the recent models list.
 */
export function addRecentModel(current: string[], modelId: string): string[] {
  const recent = current.filter((m) => m !== modelId);
  recent.unshift(modelId);
  return recent.slice(0, MAX_RECENT_MODELS);
}

/**
 * Merge preferences with updates.
 */
export function updatePreferences(
  current: UserPreferences,
  updates: Partial<UserPreferences>
): UserPreferences {
  return { ...current, ...updates };
}

/**
 * Get a preference value with a default.
 */
export function getPreferenceWithDefault<T>(value: T | undefined, defaultValue: T): T {
  return value ?? defaultValue;
}

/**
 * Load preferences from localStorage.
 */
export function loadPreferencesFromStorage(): UserPreferences | null {
  if (typeof localStorage === 'undefined') return null;

  try {
    const stored = localStorage.getItem(PREFERENCES_STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored) as UserPreferences;
    }
  } catch {
    // Ignore parse errors
  }
  return null;
}

/**
 * Save preferences to localStorage.
 */
export function savePreferencesToStorage(prefs: UserPreferences): boolean {
  if (typeof localStorage === 'undefined') return false;

  try {
    localStorage.setItem(PREFERENCES_STORAGE_KEY, JSON.stringify(prefs));
    return true;
  } catch {
    return false;
  }
}

/**
 * Clear preferences from localStorage.
 */
export function clearPreferencesFromStorage(): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.removeItem(PREFERENCES_STORAGE_KEY);
}
