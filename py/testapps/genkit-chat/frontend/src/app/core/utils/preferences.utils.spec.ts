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
import type { UserPreferences } from '../services/preferences.service';
import {
  addRecentModel,
  clearPreferencesFromStorage,
  getDefaultPreferences,
  getPreferenceWithDefault,
  loadPreferencesFromStorage,
  MAX_RECENT_MODELS,
  PREFERENCES_STORAGE_KEY,
  savePreferencesToStorage,
  updatePreferences,
} from './preferences.utils';

describe('preferences.utils', () => {
  describe('constants', () => {
    it('should have correct storage key', () => {
      expect(PREFERENCES_STORAGE_KEY).toBe('genkit-chat-preferences');
    });

    it('should have max recent models set to 5', () => {
      expect(MAX_RECENT_MODELS).toBe(5);
    });
  });

  describe('getDefaultPreferences', () => {
    it('should return default preferences', () => {
      const defaults = getDefaultPreferences();
      expect(defaults.streamingMode).toBe(true);
      expect(defaults.markdownMode).toBe(true);
      expect(defaults.contentSafetyEnabled).toBe(true);
      expect(defaults.theme).toBe('system');
      expect(defaults.recentModels).toEqual([]);
    });

    it('should return new object each time', () => {
      const d1 = getDefaultPreferences();
      const d2 = getDefaultPreferences();
      expect(d1).not.toBe(d2);
      expect(d1).toEqual(d2);
    });
  });

  describe('addRecentModel', () => {
    it('should add new model to start', () => {
      const result = addRecentModel(['m1', 'm2'], 'm3');
      expect(result[0]).toBe('m3');
      expect(result).toHaveLength(3);
    });

    it('should move existing model to start', () => {
      const result = addRecentModel(['m1', 'm2', 'm3'], 'm2');
      expect(result[0]).toBe('m2');
      expect(result).toHaveLength(3);
      expect(result.filter((m) => m === 'm2')).toHaveLength(1);
    });

    it('should limit to MAX_RECENT_MODELS', () => {
      const existing = ['m1', 'm2', 'm3', 'm4', 'm5'];
      const result = addRecentModel(existing, 'm6');
      expect(result).toHaveLength(5);
      expect(result[0]).toBe('m6');
      expect(result).not.toContain('m5');
    });

    it('should handle empty list', () => {
      const result = addRecentModel([], 'm1');
      expect(result).toEqual(['m1']);
    });
  });

  describe('updatePreferences', () => {
    it('should merge updates with current', () => {
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
  });

  describe('getPreferenceWithDefault', () => {
    it('should return value if defined', () => {
      expect(getPreferenceWithDefault(false, true)).toBe(false);
      expect(getPreferenceWithDefault('dark', 'light')).toBe('dark');
    });

    it('should return default if undefined', () => {
      expect(getPreferenceWithDefault(undefined, true)).toBe(true);
      expect(getPreferenceWithDefault(undefined, 'system')).toBe('system');
    });

    it('should return default if null', () => {
      expect(getPreferenceWithDefault(null, true)).toBe(true);
    });
  });

  describe('loadPreferencesFromStorage', () => {
    beforeEach(() => {
      vi.mocked(localStorage.getItem).mockReset();
    });

    it('should load valid preferences', () => {
      const prefs: UserPreferences = { streamingMode: false };
      vi.mocked(localStorage.getItem).mockReturnValue(JSON.stringify(prefs));
      const result = loadPreferencesFromStorage();
      expect(result?.streamingMode).toBe(false);
    });

    it('should return null for invalid JSON', () => {
      vi.mocked(localStorage.getItem).mockReturnValue('not-json');
      expect(loadPreferencesFromStorage()).toBeNull();
    });

    it('should return null for missing storage', () => {
      vi.mocked(localStorage.getItem).mockReturnValue(null);
      expect(loadPreferencesFromStorage()).toBeNull();
    });
  });

  describe('savePreferencesToStorage', () => {
    beforeEach(() => {
      vi.mocked(localStorage.setItem).mockReset();
    });

    it('should save preferences as JSON', () => {
      const prefs: UserPreferences = { streamingMode: true };
      savePreferencesToStorage(prefs);
      expect(localStorage.setItem).toHaveBeenCalledWith(
        PREFERENCES_STORAGE_KEY,
        JSON.stringify(prefs)
      );
    });

    it('should return true on success', () => {
      const result = savePreferencesToStorage({});
      expect(result).toBe(true);
    });
  });

  describe('clearPreferencesFromStorage', () => {
    beforeEach(() => {
      vi.mocked(localStorage.removeItem).mockReset();
    });

    it('should remove preferences from storage', () => {
      clearPreferencesFromStorage();
      expect(localStorage.removeItem).toHaveBeenCalledWith(PREFERENCES_STORAGE_KEY);
    });
  });
});
