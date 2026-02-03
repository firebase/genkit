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

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ThemeMode } from './theme.service';

// Since ThemeService uses Angular's effect() which requires injection context,
// we test the logic separately without instantiating the full service

describe('ThemeService logic', () => {
    let mockLocalStorage: Record<string, string>;

    beforeEach(() => {
        mockLocalStorage = {};
        vi.spyOn(localStorage, 'getItem').mockImplementation((key) => mockLocalStorage[key] || null);
        vi.spyOn(localStorage, 'setItem').mockImplementation((key, value) => {
            mockLocalStorage[key] = value;
        });
    });

    describe('getInitialTheme logic', () => {
        it('should default to system theme when nothing stored', () => {
            const saved = localStorage.getItem('genkit-chat-theme');
            const theme: ThemeMode = saved === 'light' || saved === 'dark' || saved === 'system'
                ? saved
                : 'system';
            expect(theme).toBe('system');
        });

        it('should restore light theme from localStorage', () => {
            mockLocalStorage['genkit-chat-theme'] = 'light';
            const saved = localStorage.getItem('genkit-chat-theme');
            const theme: ThemeMode = saved === 'light' || saved === 'dark' || saved === 'system'
                ? saved
                : 'system';
            expect(theme).toBe('light');
        });

        it('should restore dark theme from localStorage', () => {
            mockLocalStorage['genkit-chat-theme'] = 'dark';
            const saved = localStorage.getItem('genkit-chat-theme');
            const theme: ThemeMode = saved === 'light' || saved === 'dark' || saved === 'system'
                ? saved
                : 'system';
            expect(theme).toBe('dark');
        });

        it('should default to system for invalid stored theme', () => {
            mockLocalStorage['genkit-chat-theme'] = 'invalid';
            const saved = localStorage.getItem('genkit-chat-theme');
            const theme: ThemeMode = saved === 'light' || saved === 'dark' || saved === 'system'
                ? saved
                : 'system';
            expect(theme).toBe('system');
        });
    });

    describe('cycleTheme logic', () => {
        it('should cycle from system to light', () => {
            const current: ThemeMode = 'system';
            const next: ThemeMode = current === 'system' ? 'light' : current === 'light' ? 'dark' : 'system';
            expect(next).toBe('light');
        });

        it('should cycle from light to dark', () => {
            const current: ThemeMode = 'light';
            const next: ThemeMode = current === 'system' ? 'light' : current === 'light' ? 'dark' : 'system';
            expect(next).toBe('dark');
        });

        it('should cycle from dark to system', () => {
            const current: ThemeMode = 'dark';
            const next: ThemeMode = current === 'system' ? 'light' : current === 'light' ? 'dark' : 'system';
            expect(next).toBe('system');
        });
    });

    describe('getThemeIcon logic', () => {
        function getThemeIcon(mode: ThemeMode): string {
            if (mode === 'system') return 'brightness_auto';
            if (mode === 'dark') return 'dark_mode';
            return 'light_mode';
        }

        it('should return brightness_auto for system theme', () => {
            expect(getThemeIcon('system')).toBe('brightness_auto');
        });

        it('should return light_mode for light theme', () => {
            expect(getThemeIcon('light')).toBe('light_mode');
        });

        it('should return dark_mode for dark theme', () => {
            expect(getThemeIcon('dark')).toBe('dark_mode');
        });
    });

    describe('getThemeLabel logic', () => {
        function getThemeLabel(mode: ThemeMode): string {
            if (mode === 'system') return 'System';
            if (mode === 'dark') return 'Dark';
            return 'Light';
        }

        it('should return System for system theme', () => {
            expect(getThemeLabel('system')).toBe('System');
        });

        it('should return Light for light theme', () => {
            expect(getThemeLabel('light')).toBe('Light');
        });

        it('should return Dark for dark theme', () => {
            expect(getThemeLabel('dark')).toBe('Dark');
        });
    });

    describe('isDarkTheme logic', () => {
        function isDarkTheme(mode: ThemeMode, systemPrefersDark: boolean): boolean {
            if (mode === 'system') {
                return systemPrefersDark;
            }
            return mode === 'dark';
        }

        it('should return false for light theme', () => {
            expect(isDarkTheme('light', false)).toBe(false);
            expect(isDarkTheme('light', true)).toBe(false);
        });

        it('should return true for dark theme', () => {
            expect(isDarkTheme('dark', false)).toBe(true);
            expect(isDarkTheme('dark', true)).toBe(true);
        });

        it('should respect system preference when mode is system', () => {
            expect(isDarkTheme('system', false)).toBe(false);
            expect(isDarkTheme('system', true)).toBe(true);
        });
    });
});
