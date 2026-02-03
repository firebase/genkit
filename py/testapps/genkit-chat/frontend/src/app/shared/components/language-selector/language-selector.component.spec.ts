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

import { describe, expect, it } from 'vitest';

// Local interface to test without Angular dependencies
interface Language {
  code: string;
  name: string;
  nativeName: string;
  direction: 'ltr' | 'rtl';
  flag: string;
}

// Copy DEFAULT_LANGUAGES for testing without Angular imports
const DEFAULT_LANGUAGES: Language[] = [
  { code: 'en', name: 'English', nativeName: 'English', direction: 'ltr', flag: '🇺🇸' },
  { code: 'es', name: 'Spanish', nativeName: 'Español', direction: 'ltr', flag: '🇪🇸' },
  { code: 'de', name: 'German', nativeName: 'Deutsch', direction: 'ltr', flag: '🇩🇪' },
  { code: 'fr', name: 'French', nativeName: 'Français', direction: 'ltr', flag: '🇫🇷' },
  { code: 'ar', name: 'Arabic', nativeName: 'العربية', direction: 'rtl', flag: '🇸🇦' },
  { code: 'zh', name: 'Chinese', nativeName: '中文', direction: 'ltr', flag: '🇨🇳' },
  { code: 'ja', name: 'Japanese', nativeName: '日本語', direction: 'ltr', flag: '🇯🇵' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी', direction: 'ltr', flag: '🇮🇳' },
];

// Helper functions matching component logic
function filterLanguages(languages: Language[], query: string): Language[] {
  const lowerQuery = query.toLowerCase();
  if (!lowerQuery) return languages;

  return languages.filter(
    (lang) =>
      lang.name.toLowerCase().includes(lowerQuery) ||
      lang.nativeName.toLowerCase().includes(lowerQuery) ||
      lang.code.toLowerCase().includes(lowerQuery)
  );
}

function getCurrentLanguage(languages: Language[], code: string): Language | undefined {
  if (code === 'system') return undefined;
  return languages.find((l) => l.code === code);
}

function getDisplayLabel(languages: Language[], code: string): string {
  if (code === 'system') return 'System';
  const lang = languages.find((l) => l.code === code);
  return lang?.nativeName || code;
}

describe('LanguageSelectorComponent logic', () => {
  describe('DEFAULT_LANGUAGES', () => {
    it('should have default languages', () => {
      expect(DEFAULT_LANGUAGES.length).toBeGreaterThan(0);
      expect(DEFAULT_LANGUAGES.length).toBe(8);
    });

    it('should have English as first language', () => {
      expect(DEFAULT_LANGUAGES[0].code).toBe('en');
    });

    it('should include RTL language Arabic', () => {
      const arabic = DEFAULT_LANGUAGES.find((l) => l.code === 'ar');
      expect(arabic).toBeDefined();
      expect(arabic?.direction).toBe('rtl');
    });
  });

  describe('filterLanguages', () => {
    it('should filter languages based on name search', () => {
      const filtered = filterLanguages(DEFAULT_LANGUAGES, 'eng');
      expect(filtered.length).toBe(1);
      expect(filtered[0].code).toBe('en');
    });

    it('should filter languages by native name', () => {
      const filtered = filterLanguages(DEFAULT_LANGUAGES, 'Español');
      expect(filtered.length).toBe(1);
      expect(filtered[0].code).toBe('es');
    });

    it('should filter languages by code', () => {
      const filtered = filterLanguages(DEFAULT_LANGUAGES, 'ja');
      expect(filtered.length).toBe(1);
      expect(filtered[0].code).toBe('ja');
    });

    it('should return all languages when search is empty', () => {
      const filtered = filterLanguages(DEFAULT_LANGUAGES, '');
      expect(filtered.length).toBe(DEFAULT_LANGUAGES.length);
    });

    it('should return empty array when no match', () => {
      const filtered = filterLanguages(DEFAULT_LANGUAGES, 'xyz');
      expect(filtered.length).toBe(0);
    });

    it('should be case insensitive', () => {
      const filtered = filterLanguages(DEFAULT_LANGUAGES, 'FRENCH');
      expect(filtered.length).toBe(1);
      expect(filtered[0].code).toBe('fr');
    });
  });

  describe('getCurrentLanguage', () => {
    it('should get current language by code', () => {
      const lang = getCurrentLanguage(DEFAULT_LANGUAGES, 'ja');
      expect(lang?.code).toBe('ja');
      expect(lang?.name).toBe('Japanese');
    });

    it('should return undefined for system language', () => {
      expect(getCurrentLanguage(DEFAULT_LANGUAGES, 'system')).toBeUndefined();
    });

    it('should return undefined for unknown code', () => {
      expect(getCurrentLanguage(DEFAULT_LANGUAGES, 'unknown')).toBeUndefined();
    });
  });

  describe('getDisplayLabel', () => {
    it('should display correct label for selected language', () => {
      expect(getDisplayLabel(DEFAULT_LANGUAGES, 'fr')).toBe('Français');
    });

    it('should display System for system selection', () => {
      expect(getDisplayLabel(DEFAULT_LANGUAGES, 'system')).toBe('System');
    });

    it('should return code for unknown language', () => {
      expect(getDisplayLabel(DEFAULT_LANGUAGES, 'unknown')).toBe('unknown');
    });

    it('should display native name for Japanese', () => {
      expect(getDisplayLabel(DEFAULT_LANGUAGES, 'ja')).toBe('日本語');
    });

    it('should display native name for Arabic', () => {
      expect(getDisplayLabel(DEFAULT_LANGUAGES, 'ar')).toBe('العربية');
    });
  });
});
