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
 * Pure utility functions for theme operations.
 * These functions have no Angular dependencies and are easily testable.
 */

export type Theme = 'light' | 'dark' | 'system';

/**
 * Storage key for theme preference.
 */
export const THEME_STORAGE_KEY = 'genkit-chat-theme';

/**
 * Determine if dark mode should be active.
 */
export function isDarkTheme(theme: Theme, prefersDark: boolean): boolean {
  if (theme === 'system') {
    return prefersDark;
  }
  return theme === 'dark';
}

/**
 * Toggle between light and dark themes.
 */
export function toggleTheme(currentTheme: Theme): Theme {
  return currentTheme === 'dark' ? 'light' : 'dark';
}

/**
 * Get the color-scheme value for CSS.
 */
export function getColorScheme(isDark: boolean): 'light' | 'dark' {
  return isDark ? 'dark' : 'light';
}

/**
 * Load theme from localStorage.
 */
export function loadThemeFromStorage(defaultTheme: Theme = 'system'): Theme {
  if (typeof localStorage === 'undefined') return defaultTheme;

  const stored = localStorage.getItem(THEME_STORAGE_KEY);
  if (stored === 'light' || stored === 'dark' || stored === 'system') {
    return stored;
  }
  return defaultTheme;
}

/**
 * Save theme to localStorage.
 */
export function saveThemeToStorage(theme: Theme): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(THEME_STORAGE_KEY, theme);
}

/**
 * Apply theme classes to the document body.
 */
export function applyThemeToDocument(isDark: boolean): void {
  if (typeof document === 'undefined') return;

  document.body.classList.toggle('dark-theme', isDark);
  document.documentElement.style.colorScheme = getColorScheme(isDark);
}
