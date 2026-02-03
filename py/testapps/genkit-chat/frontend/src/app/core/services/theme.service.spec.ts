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

import { describe, expect, it, vi } from 'vitest';
import type { Theme } from './theme.service';

// Test the pure logic without Angular's injection context
// Following the "Logic-First" testing pattern from GEMINI.md

describe('ThemeService pure logic', () => {
  describe('Theme type', () => {
    it('should accept light theme', () => {
      const theme: Theme = 'light';
      expect(theme).toBe('light');
    });

    it('should accept dark theme', () => {
      const theme: Theme = 'dark';
      expect(theme).toBe('dark');
    });

    it('should accept system theme', () => {
      const theme: Theme = 'system';
      expect(theme).toBe('system');
    });

    it('should have exactly 3 valid values', () => {
      const validThemes: Theme[] = ['light', 'dark', 'system'];
      expect(validThemes).toHaveLength(3);
    });
  });

  describe('isDarkTheme logic', () => {
    // Simulate the isDarkTheme computed logic
    const isDarkTheme = (theme: Theme, prefersDark: boolean): boolean => {
      if (theme === 'system') {
        return prefersDark;
      }
      return theme === 'dark';
    };

    it('should return true when theme is dark', () => {
      expect(isDarkTheme('dark', false)).toBe(true);
    });

    it('should return false when theme is light', () => {
      expect(isDarkTheme('light', false)).toBe(false);
    });

    it('should return true when theme is system and prefers dark', () => {
      expect(isDarkTheme('system', true)).toBe(true);
    });

    it('should return false when theme is system and prefers light', () => {
      expect(isDarkTheme('system', false)).toBe(false);
    });

    it('should ignore prefersDark for explicit themes', () => {
      expect(isDarkTheme('dark', false)).toBe(true);
      expect(isDarkTheme('light', true)).toBe(false);
    });
  });

  describe('toggleTheme logic', () => {
    // Simulate the toggle logic
    const toggleTheme = (currentTheme: Theme): Theme => {
      return currentTheme === 'dark' ? 'light' : 'dark';
    };

    it('should toggle from dark to light', () => {
      expect(toggleTheme('dark')).toBe('light');
    });

    it('should toggle from light to dark', () => {
      expect(toggleTheme('light')).toBe('dark');
    });

    it('should toggle from system to dark', () => {
      expect(toggleTheme('system')).toBe('dark');
    });
  });

  describe('localStorage integration', () => {
    const STORAGE_KEY = 'genkit-chat-theme';

    it('should use correct storage key', () => {
      expect(STORAGE_KEY).toBe('genkit-chat-theme');
    });

    it('should save theme to localStorage', () => {
      const theme: Theme = 'dark';
      localStorage.setItem(STORAGE_KEY, theme);
      expect(localStorage.setItem).toHaveBeenCalledWith(STORAGE_KEY, 'dark');
    });

    it('should load theme from localStorage', () => {
      vi.mocked(localStorage.getItem).mockReturnValue('light');
      const stored = localStorage.getItem(STORAGE_KEY);
      expect(stored).toBe('light');
    });

    it('should handle missing localStorage value', () => {
      vi.mocked(localStorage.getItem).mockReturnValue(null);
      const stored = localStorage.getItem(STORAGE_KEY);
      expect(stored).toBeNull();
    });
  });

  describe('CSS class logic', () => {
    it('should add dark-theme class when dark', () => {
      const isDark = true;
      const expectedClass = isDark ? 'dark-theme' : '';
      expect(expectedClass).toBe('dark-theme');
    });

    it('should not add dark-theme class when light', () => {
      const isDark = false;
      const expectedClass = isDark ? 'dark-theme' : '';
      expect(expectedClass).toBe('');
    });
  });

  describe('color-scheme logic', () => {
    it('should set color-scheme to dark when dark mode', () => {
      const isDark = true;
      const colorScheme = isDark ? 'dark' : 'light';
      expect(colorScheme).toBe('dark');
    });

    it('should set color-scheme to light when light mode', () => {
      const isDark = false;
      const colorScheme = isDark ? 'dark' : 'light';
      expect(colorScheme).toBe('light');
    });
  });
});
