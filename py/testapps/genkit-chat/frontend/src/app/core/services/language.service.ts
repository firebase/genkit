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

import { Injectable, inject, signal } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';

/**
 * Supported language configuration.
 */
export interface Language {
  code: string;
  name: string;
  nativeName: string;
  direction: 'ltr' | 'rtl';
  flag: string;
}

/**
 * Available languages for the application.
 * Includes major global languages and Indian languages.
 */
export const SUPPORTED_LANGUAGES: Language[] = [
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

const STORAGE_KEY = 'genkit-chat-language';

/**
 * Language service for internationalization.
 * Manages language selection and persists preference to localStorage.
 * Supports 'system' as a special value that auto-detects browser language.
 */
@Injectable({
  providedIn: 'root',
})
export class LanguageService {
  private translate = inject(TranslateService);

  /** Current language preference ('system' or a language code) */
  languagePreference = signal<string>('system');

  /** Resolved language code (the actual language being used) */
  currentLanguage = signal<string>('en');

  /** Filter text for language search */
  languageFilter = signal<string>('');

  /** All supported languages sorted lexicographically by English name */
  readonly languages = [...SUPPORTED_LANGUAGES].sort((a, b) => a.name.localeCompare(b.name));

  /** Filtered languages based on search */
  get filteredLanguages(): Language[] {
    const filter = this.languageFilter().toLowerCase();
    if (!filter) return this.languages;
    return this.languages.filter(
      (lang) =>
        lang.name.toLowerCase().includes(filter) ||
        lang.nativeName.toLowerCase().includes(filter) ||
        lang.code.toLowerCase().includes(filter)
    );
  }

  constructor() {
    this.initLanguage();
  }

  /**
   * Initialize language from storage or default to system.
   */
  private initLanguage(): void {
    // Set available languages
    this.translate.addLangs(this.languages.map((l) => l.code));
    this.translate.setDefaultLang('en');

    // Try to restore from storage
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      this.setLanguagePreference(stored);
    } else {
      // Default to system
      this.setLanguagePreference('system');
    }
  }

  /**
   * Set the language preference ('system' or a specific language code).
   */
  setLanguagePreference(preference: string): void {
    this.languagePreference.set(preference);
    localStorage.setItem(STORAGE_KEY, preference);

    let code: string;
    if (preference === 'system') {
      // Auto-detect from browser
      const browserLang = this.translate.getBrowserLang();
      code = browserLang && this.languages.find((l) => l.code === browserLang) ? browserLang : 'en';
    } else {
      code = this.languages.find((l) => l.code === preference) ? preference : 'en';
    }

    this.applyLanguage(code);
  }

  /**
   * Apply a specific language code.
   */
  private applyLanguage(code: string): void {
    const lang = this.languages.find((l) => l.code === code) || this.languages[0];

    this.translate.use(code);
    this.currentLanguage.set(code);

    // Update document direction for RTL languages
    document.documentElement.dir = lang.direction;
    document.documentElement.lang = code;
  }

  /**
   * Get the current language object.
   */
  getCurrentLanguage(): Language {
    return this.languages.find((l) => l.code === this.currentLanguage()) || this.languages[0];
  }

  /**
   * Get language by code.
   */
  getLanguage(code: string): Language | undefined {
    return this.languages.find((l) => l.code === code);
  }

  /**
   * Get display label for current preference.
   */
  getLanguageLabel(): string {
    const pref = this.languagePreference();
    if (pref === 'system') {
      return `System (${this.getCurrentLanguage().nativeName})`;
    }
    return this.getCurrentLanguage().nativeName;
  }
}
