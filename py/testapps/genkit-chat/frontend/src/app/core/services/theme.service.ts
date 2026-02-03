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

import { computed, effect, Injectable, signal } from '@angular/core';

export type ThemeMode = 'light' | 'dark' | 'system';

@Injectable({
  providedIn: 'root',
})
export class ThemeService {
  private readonly THEME_KEY = 'genkit-chat-theme';

  /** The user's selected theme preference (light, dark, or system) */
  themeMode = signal<ThemeMode>(this.getInitialTheme());

  /** Whether the current effective theme is dark (resolves 'system' to actual) */
  isDarkTheme = computed(() => {
    const mode = this.themeMode();
    if (mode === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return mode === 'dark';
  });

  constructor() {
    // Apply theme changes to body
    effect(() => {
      const dark = this.isDarkTheme();
      document.body.classList.toggle('dark-theme', dark);
    });

    // Persist theme preference
    effect(() => {
      const mode = this.themeMode();
      localStorage.setItem(this.THEME_KEY, mode);
    });

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      // This will trigger the isDarkTheme computed to re-evaluate
      if (this.themeMode() === 'system') {
        // Force a re-evaluation by toggling and restoring
        this.themeMode.set('system');
      }
    });
  }

  private getInitialTheme(): ThemeMode {
    const saved = localStorage.getItem(this.THEME_KEY);
    if (saved === 'light' || saved === 'dark' || saved === 'system') {
      return saved;
    }
    return 'system'; // Default to system preference
  }

  /** Cycle through themes: system -> light -> dark -> system */
  cycleTheme(): void {
    const current = this.themeMode();
    const next: ThemeMode =
      current === 'system' ? 'light' : current === 'light' ? 'dark' : 'system';
    this.themeMode.set(next);
  }

  /** Set a specific theme */
  setTheme(mode: ThemeMode): void {
    this.themeMode.set(mode);
  }

  /** Get the icon for the current theme */
  getThemeIcon(): string {
    const mode = this.themeMode();
    if (mode === 'system') return 'brightness_auto';
    if (mode === 'dark') return 'dark_mode';
    return 'light_mode';
  }

  /** Get the label for the current theme */
  getThemeLabel(): string {
    const mode = this.themeMode();
    if (mode === 'system') return 'System';
    if (mode === 'dark') return 'Dark';
    return 'Light';
  }
}
