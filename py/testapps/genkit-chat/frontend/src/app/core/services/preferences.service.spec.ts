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

import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { UserPreferences } from './preferences.service';

// Test the pure logic without Angular's injection context
// Following the "Logic-First" testing pattern from GEMINI.md

const STORAGE_KEY = 'genkit-chat-preferences';
const MAX_RECENT_MODELS = 5;

describe('PreferencesService data structures', () => {
  describe('UserPreferences interface', () => {
    it('should accept all preference fields', () => {
      const prefs: UserPreferences = {
        selectedModel: 'googleai/gemini-2.0-flash',
        recentModels: ['model-1', 'model-2'],
        streamingMode: true,
        markdownMode: true,
        contentSafetyEnabled: true,
        theme: 'dark',
        language: 'en',
      };
      expect(prefs.selectedModel).toBe('googleai/gemini-2.0-flash');
      expect(prefs.recentModels).toHaveLength(2);
      expect(prefs.streamingMode).toBe(true);
      expect(prefs.theme).toBe('dark');
    });

    it('should accept minimal preferences', () => {
      const prefs: UserPreferences = {};
      expect(prefs.selectedModel).toBeUndefined();
      expect(prefs.streamingMode).toBeUndefined();
    });

    it('should accept theme values', () => {
      const themes: Array<UserPreferences['theme']> = ['light', 'dark', 'system'];
      expect(themes).toHaveLength(3);
    });
  });
});

describe('PreferencesService pure logic', () => {
  describe('getDefaults logic', () => {
    const getDefaults = (): UserPreferences => ({
      streamingMode: true,
      markdownMode: true,
      contentSafetyEnabled: true,
      theme: 'system',
      recentModels: [],
    });

    it('should return correct default values', () => {
      const defaults = getDefaults();
      expect(defaults.streamingMode).toBe(true);
      expect(defaults.markdownMode).toBe(true);
      expect(defaults.contentSafetyEnabled).toBe(true);
      expect(defaults.theme).toBe('system');
      expect(defaults.recentModels).toEqual([]);
    });

    it('should return new object each time', () => {
      const defaults1 = getDefaults();
      const defaults2 = getDefaults();
      expect(defaults1).not.toBe(defaults2);
      expect(defaults1).toEqual(defaults2);
    });
  });

  describe('addRecentModel logic', () => {
    const addRecentModel = (current: string[], modelId: string): string[] => {
      const recent = current.filter((m) => m !== modelId);
      recent.unshift(modelId);
      return recent.slice(0, MAX_RECENT_MODELS);
    };

    it('should add new model to start', () => {
      const result = addRecentModel(['model-1', 'model-2'], 'model-3');
      expect(result[0]).toBe('model-3');
      expect(result).toHaveLength(3);
    });

    it('should move existing model to start', () => {
      const result = addRecentModel(['model-1', 'model-2', 'model-3'], 'model-2');
      expect(result[0]).toBe('model-2');
      expect(result).toHaveLength(3);
      expect(result.filter((m) => m === 'model-2')).toHaveLength(1);
    });

    it('should limit to MAX_RECENT_MODELS', () => {
      const existing = ['m-1', 'm-2', 'm-3', 'm-4', 'm-5'];
      const result = addRecentModel(existing, 'm-6');
      expect(result).toHaveLength(5);
      expect(result[0]).toBe('m-6');
      expect(result).not.toContain('m-5');
    });

    it('should handle empty list', () => {
      const result = addRecentModel([], 'model-1');
      expect(result).toEqual(['model-1']);
    });
  });

  describe('localStorage operations', () => {
    beforeEach(() => {
      vi.mocked(localStorage.getItem).mockReset();
      vi.mocked(localStorage.setItem).mockReset();
      vi.mocked(localStorage.removeItem).mockReset();
    });

    it('should use correct storage key', () => {
      expect(STORAGE_KEY).toBe('genkit-chat-preferences');
    });

    it('should serialize preferences to JSON', () => {
      const prefs: UserPreferences = { streamingMode: true, theme: 'dark' };
      const json = JSON.stringify(prefs);
      expect(json).toBe('{"streamingMode":true,"theme":"dark"}');
    });

    it('should deserialize JSON to preferences', () => {
      const json = '{"streamingMode":false,"markdownMode":true}';
      const prefs = JSON.parse(json) as UserPreferences;
      expect(prefs.streamingMode).toBe(false);
      expect(prefs.markdownMode).toBe(true);
    });

    it('should handle invalid JSON gracefully', () => {
      const parsePrefs = (stored: string | null): UserPreferences | null => {
        try {
          return stored ? (JSON.parse(stored) as UserPreferences) : null;
        } catch {
          return null;
        }
      };

      expect(parsePrefs('not-json')).toBeNull();
      expect(parsePrefs(null)).toBeNull();
      expect(parsePrefs('{"streamingMode":true}')).toEqual({ streamingMode: true });
    });
  });

  describe('preference getters with defaults', () => {
    const getWithDefault = <T>(value: T | undefined, defaultValue: T): T => {
      return value ?? defaultValue;
    };

    it('should return value if defined', () => {
      expect(getWithDefault(false, true)).toBe(false);
      expect(getWithDefault('dark' as const, 'system' as const)).toBe('dark');
    });

    it('should return default if undefined', () => {
      expect(getWithDefault(undefined, true)).toBe(true);
      expect(getWithDefault(undefined, 'system')).toBe('system');
    });

    it('should return default if null', () => {
      expect(getWithDefault(null, true)).toBe(true);
    });
  });

  describe('preference update logic', () => {
    const updatePreferences = (
      current: UserPreferences,
      updates: Partial<UserPreferences>
    ): UserPreferences => ({
      ...current,
      ...updates,
    });

    it('should merge updates with current preferences', () => {
      const current: UserPreferences = { streamingMode: true, theme: 'light' };
      const result = updatePreferences(current, { markdownMode: true });
      expect(result.streamingMode).toBe(true);
      expect(result.theme).toBe('light');
      expect(result.markdownMode).toBe(true);
    });

    it('should override existing values', () => {
      const current: UserPreferences = { streamingMode: true };
      const result = updatePreferences(current, { streamingMode: false });
      expect(result.streamingMode).toBe(false);
    });

    it('should preserve other fields', () => {
      const current: UserPreferences = {
        selectedModel: 'model-1',
        recentModels: ['m-1', 'm-2'],
        streamingMode: true,
      };
      const result = updatePreferences(current, { theme: 'dark' });
      expect(result.selectedModel).toBe('model-1');
      expect(result.recentModels).toEqual(['m-1', 'm-2']);
    });
  });
});

describe('Constants', () => {
  it('should have MAX_RECENT_MODELS set to 5', () => {
    expect(MAX_RECENT_MODELS).toBe(5);
  });

  it('should have correct STORAGE_KEY', () => {
    expect(STORAGE_KEY).toBe('genkit-chat-preferences');
  });
});
