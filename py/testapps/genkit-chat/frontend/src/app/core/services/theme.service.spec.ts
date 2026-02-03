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
import { ThemeService, ThemeMode } from './theme.service';

describe('ThemeService', () => {
    let service: ThemeService;
    let mockLocalStorage: Record<string, string>;

    beforeEach(() => {
        // Reset localStorage mock
        mockLocalStorage = {};
        vi.spyOn(localStorage, 'getItem').mockImplementation((key) => mockLocalStorage[key] || null);
        vi.spyOn(localStorage, 'setItem').mockImplementation((key, value) => {
            mockLocalStorage[key] = value;
        });

        // Reset document body classes
        document.body.classList.remove('dark-theme');

        service = new ThemeService();
    });

    it('should be created', () => {
        expect(service).toBeDefined();
    });

    describe('initialization', () => {
        it('should default to system theme', () => {
            expect(service.themeMode()).toBe('system');
        });

        it('should restore theme from localStorage', () => {
            mockLocalStorage['genkit-chat-theme'] = 'dark';
            const newService = new ThemeService();
            expect(newService.themeMode()).toBe('dark');
        });

        it('should handle invalid stored theme', () => {
            mockLocalStorage['genkit-chat-theme'] = 'invalid';
            const newService = new ThemeService();
            expect(newService.themeMode()).toBe('system');
        });
    });

    describe('setTheme', () => {
        it('should set theme to light', () => {
            service.setTheme('light');
            expect(service.themeMode()).toBe('light');
        });

        it('should set theme to dark', () => {
            service.setTheme('dark');
            expect(service.themeMode()).toBe('dark');
        });

        it('should set theme to system', () => {
            service.setTheme('light');
            service.setTheme('system');
            expect(service.themeMode()).toBe('system');
        });

        it('should persist theme to localStorage', () => {
            service.setTheme('dark');
            expect(localStorage.setItem).toHaveBeenCalledWith('genkit-chat-theme', 'dark');
        });
    });

    describe('cycleTheme', () => {
        it('should cycle from system to light', () => {
            service.setTheme('system');
            service.cycleTheme();
            expect(service.themeMode()).toBe('light');
        });

        it('should cycle from light to dark', () => {
            service.setTheme('light');
            service.cycleTheme();
            expect(service.themeMode()).toBe('dark');
        });

        it('should cycle from dark to system', () => {
            service.setTheme('dark');
            service.cycleTheme();
            expect(service.themeMode()).toBe('system');
        });
    });

    describe('getThemeIcon', () => {
        it('should return brightness_auto for system theme', () => {
            service.setTheme('system');
            expect(service.getThemeIcon()).toBe('brightness_auto');
        });

        it('should return light_mode for light theme', () => {
            service.setTheme('light');
            expect(service.getThemeIcon()).toBe('light_mode');
        });

        it('should return dark_mode for dark theme', () => {
            service.setTheme('dark');
            expect(service.getThemeIcon()).toBe('dark_mode');
        });
    });

    describe('getThemeLabel', () => {
        it('should return System for system theme', () => {
            service.setTheme('system');
            expect(service.getThemeLabel()).toBe('System');
        });

        it('should return Light for light theme', () => {
            service.setTheme('light');
            expect(service.getThemeLabel()).toBe('Light');
        });

        it('should return Dark for dark theme', () => {
            service.setTheme('dark');
            expect(service.getThemeLabel()).toBe('Dark');
        });
    });

    describe('isDarkTheme', () => {
        it('should return false for light theme', () => {
            service.setTheme('light');
            expect(service.isDarkTheme()).toBe(false);
        });

        it('should return true for dark theme', () => {
            service.setTheme('dark');
            expect(service.isDarkTheme()).toBe(true);
        });

        // System theme depends on matchMedia which is mocked to return false (light)
        it('should respect system preference', () => {
            service.setTheme('system');
            // matchMedia is mocked to return matches: false (light mode)
            expect(service.isDarkTheme()).toBe(false);
        });
    });
});
