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
import { LanguageService, SUPPORTED_LANGUAGES } from './language.service';

// Mock ngx-translate
vi.mock('@ngx-translate/core', () => ({
    TranslateService: vi.fn().mockImplementation(() => ({
        addLangs: vi.fn(),
        setDefaultLang: vi.fn(),
        getBrowserLang: vi.fn().mockReturnValue('en'),
        use: vi.fn(),
    })),
}));

describe('LanguageService', () => {
    let service: LanguageService;
    let mockLocalStorage: Record<string, string>;

    beforeEach(() => {
        // Reset localStorage mock
        mockLocalStorage = {};
        vi.spyOn(localStorage, 'getItem').mockImplementation((key) => mockLocalStorage[key] || null);
        vi.spyOn(localStorage, 'setItem').mockImplementation((key, value) => {
            mockLocalStorage[key] = value;
        });

        // Reset document properties
        document.documentElement.dir = 'ltr';
        document.documentElement.lang = 'en';

        service = new LanguageService();
    });

    describe('SUPPORTED_LANGUAGES', () => {
        it('should have at least 10 languages', () => {
            expect(SUPPORTED_LANGUAGES.length).toBeGreaterThanOrEqual(10);
        });

        it('should have English as first language', () => {
            expect(SUPPORTED_LANGUAGES[0].code).toBe('en');
        });

        it('should have Arabic as RTL', () => {
            const arabic = SUPPORTED_LANGUAGES.find(l => l.code === 'ar');
            expect(arabic).toBeDefined();
            expect(arabic?.direction).toBe('rtl');
        });

        it('should have Indian languages', () => {
            const indianLanguages = ['hi', 'bn', 'te', 'ta', 'mr', 'gu', 'kn'];
            indianLanguages.forEach(code => {
                const lang = SUPPORTED_LANGUAGES.find(l => l.code === code);
                expect(lang).toBeDefined();
                expect(lang?.flag).toBe('🇮🇳');
            });
        });

        it('should have all required properties', () => {
            SUPPORTED_LANGUAGES.forEach(lang => {
                expect(lang.code).toBeDefined();
                expect(lang.name).toBeDefined();
                expect(lang.nativeName).toBeDefined();
                expect(lang.direction).toMatch(/^(ltr|rtl)$/);
                expect(lang.flag).toBeDefined();
            });
        });
    });

    describe('initialization', () => {
        it('should default to system preference', () => {
            expect(service.languagePreference()).toBe('system');
        });

        it('should restore from localStorage if available', () => {
            mockLocalStorage['genkit-chat-language'] = 'es';
            const newService = new LanguageService();
            expect(newService.languagePreference()).toBe('es');
        });
    });

    describe('setLanguagePreference', () => {
        it('should set language preference to a specific language', () => {
            service.setLanguagePreference('fr');
            expect(service.languagePreference()).toBe('fr');
            expect(service.currentLanguage()).toBe('fr');
        });

        it('should persist preference to localStorage', () => {
            service.setLanguagePreference('de');
            expect(localStorage.setItem).toHaveBeenCalledWith('genkit-chat-language', 'de');
        });

        it('should fallback to English for unknown language', () => {
            service.setLanguagePreference('xx');
            expect(service.currentLanguage()).toBe('en');
        });

        it('should set system preference and auto-detect', () => {
            service.setLanguagePreference('system');
            expect(service.languagePreference()).toBe('system');
        });

        it('should update document direction for RTL languages', () => {
            service.setLanguagePreference('ar');
            expect(document.documentElement.dir).toBe('rtl');
        });

        it('should update document lang attribute', () => {
            service.setLanguagePreference('ja');
            expect(document.documentElement.lang).toBe('ja');
        });
    });

    describe('getCurrentLanguage', () => {
        it('should return current language object', () => {
            service.setLanguagePreference('es');
            const lang = service.getCurrentLanguage();
            expect(lang.code).toBe('es');
            expect(lang.name).toBe('Spanish');
            expect(lang.nativeName).toBe('Español');
        });

        it('should return English by default', () => {
            const lang = service.getCurrentLanguage();
            expect(lang.code).toBe('en');
        });
    });

    describe('getLanguage', () => {
        it('should return language by code', () => {
            const lang = service.getLanguage('hi');
            expect(lang).toBeDefined();
            expect(lang?.name).toBe('Hindi');
        });

        it('should return undefined for unknown code', () => {
            const lang = service.getLanguage('xx');
            expect(lang).toBeUndefined();
        });
    });

    describe('getLanguageLabel', () => {
        it('should return native name for specific language', () => {
            service.setLanguagePreference('ja');
            expect(service.getLanguageLabel()).toBe('日本語');
        });

        it('should return System with detected language for system preference', () => {
            service.setLanguagePreference('system');
            expect(service.getLanguageLabel()).toContain('System');
        });
    });
});
