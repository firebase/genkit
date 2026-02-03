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
import type { Theme } from './theme.utils';
import {
  getColorScheme,
  isDarkTheme,
  loadThemeFromStorage,
  saveThemeToStorage,
  THEME_STORAGE_KEY,
  toggleTheme,
} from './theme.utils';

describe('theme.utils', () => {
  describe('THEME_STORAGE_KEY', () => {
    it('should be defined', () => {
      expect(THEME_STORAGE_KEY).toBe('genkit-chat-theme');
    });
  });

  describe('isDarkTheme', () => {
    it('should return true for dark theme', () => {
      expect(isDarkTheme('dark', false)).toBe(true);
      expect(isDarkTheme('dark', true)).toBe(true);
    });

    it('should return false for light theme', () => {
      expect(isDarkTheme('light', false)).toBe(false);
      expect(isDarkTheme('light', true)).toBe(false);
    });

    it('should follow system preference for system theme', () => {
      expect(isDarkTheme('system', true)).toBe(true);
      expect(isDarkTheme('system', false)).toBe(false);
    });
  });

  describe('toggleTheme', () => {
    it('should toggle dark to light', () => {
      expect(toggleTheme('dark')).toBe('light');
    });

    it('should toggle light to dark', () => {
      expect(toggleTheme('light')).toBe('dark');
    });

    it('should toggle system to dark', () => {
      expect(toggleTheme('system')).toBe('dark');
    });
  });

  describe('getColorScheme', () => {
    it('should return dark for dark mode', () => {
      expect(getColorScheme(true)).toBe('dark');
    });

    it('should return light for light mode', () => {
      expect(getColorScheme(false)).toBe('light');
    });
  });

  describe('loadThemeFromStorage', () => {
    beforeEach(() => {
      vi.mocked(localStorage.getItem).mockReset();
    });

    it('should load light theme from storage', () => {
      vi.mocked(localStorage.getItem).mockReturnValue('light');
      expect(loadThemeFromStorage()).toBe('light');
    });

    it('should load dark theme from storage', () => {
      vi.mocked(localStorage.getItem).mockReturnValue('dark');
      expect(loadThemeFromStorage()).toBe('dark');
    });

    it('should load system theme from storage', () => {
      vi.mocked(localStorage.getItem).mockReturnValue('system');
      expect(loadThemeFromStorage()).toBe('system');
    });

    it('should return default for invalid value', () => {
      vi.mocked(localStorage.getItem).mockReturnValue('invalid');
      expect(loadThemeFromStorage()).toBe('system');
    });

    it('should return default for null', () => {
      vi.mocked(localStorage.getItem).mockReturnValue(null);
      expect(loadThemeFromStorage()).toBe('system');
    });

    it('should accept custom default', () => {
      vi.mocked(localStorage.getItem).mockReturnValue(null);
      expect(loadThemeFromStorage('dark')).toBe('dark');
    });
  });

  describe('saveThemeToStorage', () => {
    beforeEach(() => {
      vi.mocked(localStorage.setItem).mockReset();
    });

    it('should save theme to storage', () => {
      saveThemeToStorage('dark');
      expect(localStorage.setItem).toHaveBeenCalledWith(THEME_STORAGE_KEY, 'dark');
    });

    it('should save all valid themes', () => {
      const themes: Theme[] = ['light', 'dark', 'system'];
      for (const theme of themes) {
        saveThemeToStorage(theme);
        expect(localStorage.setItem).toHaveBeenCalledWith(THEME_STORAGE_KEY, theme);
      }
    });
  });
});
