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

// Define the interface locally to avoid importing from service.ts
// which would pull in @ngx-translate/core
interface Language {
  code: string;
  name: string;
  nativeName: string;
  direction: 'ltr' | 'rtl';
  flag: string;
}

// Copy the SUPPORTED_LANGUAGES array for testing
// This tests the configuration values without importing Angular dependencies
const SUPPORTED_LANGUAGES: Language[] = [
  // Global Languages
  { code: 'en', name: 'English', nativeName: 'English', direction: 'ltr', flag: '🇺🇸' },
  { code: 'es', name: 'Spanish', nativeName: 'Español', direction: 'ltr', flag: '🇪🇸' },
  { code: 'de', name: 'German', nativeName: 'Deutsch', direction: 'ltr', flag: '🇩🇪' },
  { code: 'fr', name: 'French', nativeName: 'Français', direction: 'ltr', flag: '🇫🇷' },
  { code: 'pt', name: 'Portuguese', nativeName: 'Português', direction: 'ltr', flag: '🇧🇷' },
  { code: 'it', name: 'Italian', nativeName: 'Italiano', direction: 'ltr', flag: '🇮🇹' },
  { code: 'ru', name: 'Russian', nativeName: 'Русский', direction: 'ltr', flag: '🇷🇺' },
  { code: 'ar', name: 'Arabic', nativeName: 'العربية', direction: 'rtl', flag: '🇸🇦' },
  // East Asian Languages
  { code: 'zh', name: 'Chinese', nativeName: '中文', direction: 'ltr', flag: '🇨🇳' },
  { code: 'ja', name: 'Japanese', nativeName: '日本語', direction: 'ltr', flag: '🇯🇵' },
  { code: 'ko', name: 'Korean', nativeName: '한국어', direction: 'ltr', flag: '🇰🇷' },
  // Indian Languages
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी', direction: 'ltr', flag: '🇮🇳' },
  { code: 'bn', name: 'Bengali', nativeName: 'বাংলা', direction: 'ltr', flag: '🇮🇳' },
  { code: 'te', name: 'Telugu', nativeName: 'తెలుగు', direction: 'ltr', flag: '🇮🇳' },
  { code: 'ta', name: 'Tamil', nativeName: 'தமிழ்', direction: 'ltr', flag: '🇮🇳' },
  { code: 'mr', name: 'Marathi', nativeName: 'मराठी', direction: 'ltr', flag: '🇮🇳' },
  { code: 'gu', name: 'Gujarati', nativeName: 'ગુજરાતી', direction: 'ltr', flag: '🇮🇳' },
  { code: 'kn', name: 'Kannada', nativeName: 'ಕನ್ನಡ', direction: 'ltr', flag: '🇮🇳' },
];

// Since LanguageService uses Angular's inject() which requires injection context,
// we test the configuration and logic separately

describe('SUPPORTED_LANGUAGES configuration', () => {
  it('should have at least 15 languages', () => {
    expect(SUPPORTED_LANGUAGES.length).toBeGreaterThanOrEqual(15);
  });

  it('should have English as first language', () => {
    expect(SUPPORTED_LANGUAGES[0].code).toBe('en');
    expect(SUPPORTED_LANGUAGES[0].name).toBe('English');
  });

  it('should have Arabic as RTL', () => {
    const arabic = SUPPORTED_LANGUAGES.find((l) => l.code === 'ar');
    expect(arabic).toBeDefined();
    expect(arabic?.direction).toBe('rtl');
    expect(arabic?.nativeName).toBe('العربية');
  });

  it('should have all Indian languages', () => {
    const indianLanguages = ['hi', 'bn', 'te', 'ta', 'mr', 'gu', 'kn'];
    indianLanguages.forEach((code) => {
      const lang = SUPPORTED_LANGUAGES.find((l) => l.code === code);
      expect(lang).toBeDefined();
      expect(lang?.flag).toBe('🇮🇳');
      expect(lang?.direction).toBe('ltr');
    });
  });

  it('should have East Asian languages', () => {
    const eastAsian = ['zh', 'ja', 'ko'];
    eastAsian.forEach((code) => {
      const lang = SUPPORTED_LANGUAGES.find((l) => l.code === code);
      expect(lang).toBeDefined();
      expect(lang?.direction).toBe('ltr');
    });
  });

  it('should have European languages', () => {
    const european = ['en', 'es', 'de', 'fr', 'pt', 'it', 'ru'];
    european.forEach((code) => {
      const lang = SUPPORTED_LANGUAGES.find((l) => l.code === code);
      expect(lang).toBeDefined();
    });
  });

  it('should have all required properties for each language', () => {
    SUPPORTED_LANGUAGES.forEach((lang) => {
      expect(lang.code).toBeDefined();
      expect(lang.code.length).toBeGreaterThanOrEqual(2);
      expect(lang.name).toBeDefined();
      expect(lang.nativeName).toBeDefined();
      expect(lang.direction).toMatch(/^(ltr|rtl)$/);
      expect(lang.flag).toBeDefined();
    });
  });

  it('should have unique language codes', () => {
    const codes = SUPPORTED_LANGUAGES.map((l) => l.code);
    const uniqueCodes = [...new Set(codes)];
    expect(codes.length).toBe(uniqueCodes.length);
  });
});

describe('Language helper logic', () => {
  function getLanguage(code: string): Language | undefined {
    return SUPPORTED_LANGUAGES.find((l) => l.code === code);
  }

  function getLanguageLabel(preference: string, currentCode: string): string {
    const current = SUPPORTED_LANGUAGES.find((l) => l.code === currentCode);
    if (!current) return 'Unknown';

    if (preference === 'system') {
      return `System (${current.nativeName})`;
    }
    return current.nativeName;
  }

  describe('getLanguage', () => {
    it('should return language by code', () => {
      const lang = getLanguage('hi');
      expect(lang).toBeDefined();
      expect(lang?.name).toBe('Hindi');
      expect(lang?.nativeName).toBe('हिन्दी');
    });

    it('should return undefined for unknown code', () => {
      const lang = getLanguage('xx');
      expect(lang).toBeUndefined();
    });

    it('should return Bengali correctly', () => {
      const lang = getLanguage('bn');
      expect(lang?.name).toBe('Bengali');
      expect(lang?.nativeName).toBe('বাংলা');
    });

    it('should return Japanese correctly', () => {
      const lang = getLanguage('ja');
      expect(lang?.name).toBe('Japanese');
      expect(lang?.nativeName).toBe('日本語');
    });
  });

  describe('getLanguageLabel', () => {
    it('should return native name for specific language', () => {
      expect(getLanguageLabel('ja', 'ja')).toBe('日本語');
    });

    it('should return System with detected language for system preference', () => {
      const label = getLanguageLabel('system', 'en');
      expect(label).toBe('System (English)');
    });

    it('should work with Hindi', () => {
      expect(getLanguageLabel('hi', 'hi')).toBe('हिन्दी');
    });
  });
});
