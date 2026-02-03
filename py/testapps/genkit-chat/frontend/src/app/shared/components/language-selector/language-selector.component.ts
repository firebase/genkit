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

import { CommonModule } from '@angular/common';
/**
 * LanguageSelectorComponent - Self-contained language dropdown selector.
 *
 * This component is responsible for:
 * - Displaying the currently selected language
 * - Searchable dropdown for language selection
 * - Support for RTL languages
 * - System language auto-detection option
 *
 * Portability:
 * - This component is SELF-CONTAINED with CSS fallback variables
 * - Requires: @angular/material
 * - Optional: @ngx-translate/core (for labels)
 * - Languages are passed as input - no service dependency required
 *
 * Component Architecture::
 *
 *     ┌─────────────────────────────────────────────────────────────────┐
 *     │                    LanguageSelectorComponent                    │
 *     ├─────────────────────────────────────────────────────────────────┤
 *     │  Inputs:                                                        │
 *     │  - languages: Language[]                                        │
 *     │  - selectedLanguage: string (code or 'system')                  │
 *     │  - showSystemOption: boolean (default: true)                    │
 *     │                                                                 │
 *     │  Outputs:                                                       │
 *     │  - languageSelected: EventEmitter<string>                       │
 *     └─────────────────────────────────────────────────────────────────┘
 */
import { Component, computed, input, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { TranslateModule } from '@ngx-translate/core';

/**
 * Language configuration interface.
 * Exported for use by host applications.
 */
export interface Language {
  code: string;
  name: string;
  nativeName: string;
  direction: 'ltr' | 'rtl';
  flag: string;
}

/**
 * Default supported languages.
 * Can be overridden by passing custom languages via input.
 */
export const DEFAULT_LANGUAGES: Language[] = [
  { code: 'en', name: 'English', nativeName: 'English', direction: 'ltr', flag: '🇺🇸' },
  { code: 'es', name: 'Spanish', nativeName: 'Español', direction: 'ltr', flag: '🇪🇸' },
  { code: 'de', name: 'German', nativeName: 'Deutsch', direction: 'ltr', flag: '🇩🇪' },
  { code: 'fr', name: 'French', nativeName: 'Français', direction: 'ltr', flag: '🇫🇷' },
  { code: 'ar', name: 'Arabic', nativeName: 'العربية', direction: 'rtl', flag: '🇸🇦' },
  { code: 'zh', name: 'Chinese', nativeName: '中文', direction: 'ltr', flag: '🇨🇳' },
  { code: 'ja', name: 'Japanese', nativeName: '日本語', direction: 'ltr', flag: '🇯🇵' },
  { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी', direction: 'ltr', flag: '🇮🇳' },
];

@Component({
  selector: 'app-language-selector',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatDividerModule,
    TranslateModule,
  ],
  template: `
    <button mat-button 
            class="language-select-btn"
            [matMenuTriggerFor]="languageMenu"
            (menuOpened)="onMenuOpened()">
      <span class="language-flag">{{ getCurrentLanguage()?.flag || '🌐' }}</span>
      <span class="language-label">{{ getDisplayLabel() }}</span>
      <mat-icon class="dropdown-icon">arrow_drop_down</mat-icon>
    </button>
    
    <mat-menu #languageMenu="matMenu" class="language-panel" xPosition="before">
      <!-- Search Input -->
      <div class="language-search" (click)="$event.stopPropagation()">
        <mat-icon>search</mat-icon>
        <input type="text" 
               [placeholder]="'language.searchLanguages' | translate"
               [(ngModel)]="searchQuery"
               (keydown)="$event.stopPropagation()">
        @if (searchQuery) {
          <button mat-icon-button class="clear-search" (click)="clearSearch()">
            <mat-icon>close</mat-icon>
          </button>
        }
      </div>
      
      <!-- System Option -->
      @if (showSystemOption() && !searchQuery) {
        <button mat-menu-item 
                class="language-item system-item"
                [class.selected]="selectedLanguage() === 'system'"
                (click)="selectLanguage('system')">
          <span class="language-flag">🌐</span>
          <span class="language-name">{{ 'theme.system' | translate }}</span>
          @if (selectedLanguage() === 'system') {
            <mat-icon class="check-icon">check</mat-icon>
          }
        </button>
        <mat-divider></mat-divider>
      }
      
      <!-- Language List -->
      <div class="language-list">
        @for (lang of filteredLanguages(); track lang.code) {
          <button mat-menu-item 
                  class="language-item"
                  [class.selected]="selectedLanguage() === lang.code"
                  [class.rtl]="lang.direction === 'rtl'"
                  (click)="selectLanguage(lang.code)">
            <span class="language-flag">{{ lang.flag }}</span>
            <span class="language-name">{{ lang.nativeName }}</span>
            <span class="language-english">{{ lang.name }}</span>
            @if (selectedLanguage() === lang.code) {
              <mat-icon class="check-icon">check</mat-icon>
            }
          </button>
        } @empty {
          <div class="no-results">{{ 'language.noLanguagesFound' | translate }}</div>
        }
      </div>
    </mat-menu>
  `,
  styles: [
    `
    /* CSS Variable Defaults - ensures component works without global theme */
    :host {
      display: inline-block;

      --_primary: var(--primary, #4285f4);
      --_primary-container: var(--primary-container, #d3e3fd);
      --_on-primary-container: var(--on-primary-container, #041e49);
      --_surface-container-high: var(--surface-container-high, #e5eaf0);
      --_on-surface: var(--on-surface, #1a1c1e);
      --_on-surface-variant: var(--on-surface-variant, #5f6368);
      --_outline-variant: var(--outline-variant, #c4c6d0);
    }

    .language-select-btn {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 4px 12px;
      border-radius: 8px;
      
      &:hover {
        background: var(--_surface-container-high);
      }
    }

    .language-flag {
      font-size: 18px;
    }

    .language-label {
      font-size: 14px;
      color: var(--_on-surface);
    }

    .dropdown-icon {
      color: var(--_on-surface-variant);
    }

    ::ng-deep .language-panel {
      max-height: 400px;
      min-width: 280px;
    }

    .language-search {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      border-bottom: 1px solid var(--_outline-variant);
      
      mat-icon {
        color: var(--_on-surface-variant);
        font-size: 20px;
        width: 20px;
        height: 20px;
      }
      
      input {
        flex: 1;
        background: transparent;
        border: none;
        outline: none;
        font-size: 14px;
        color: var(--_on-surface);
        
        &::placeholder {
          color: var(--_on-surface-variant);
        }
      }
      
      .clear-search {
        width: 24px;
        height: 24px;
        
        mat-icon {
          font-size: 16px;
          width: 16px;
          height: 16px;
        }
      }
    }

    .language-list {
      max-height: 300px;
      overflow-y: auto;
    }

    .language-item {
      display: flex;
      align-items: center;
      gap: 12px;
      
      &.selected {
        background: var(--_primary-container);
        color: var(--_on-primary-container);
      }
      
      &.rtl {
        direction: rtl;
      }
      
      .language-flag {
        font-size: 20px;
      }
      
      .language-name {
        flex: 1;
        font-size: 14px;
      }
      
      .language-english {
        font-size: 12px;
        color: var(--_on-surface-variant);
      }
      
      .check-icon {
        color: var(--_primary);
        font-size: 18px;
        width: 18px;
        height: 18px;
      }
    }

    .system-item {
      .language-name {
        font-style: italic;
      }
    }

    .no-results {
      padding: 16px;
      text-align: center;
      color: var(--_on-surface-variant);
      font-size: 14px;
    }
  `,
  ],
})
export class LanguageSelectorComponent {
  /** List of available languages */
  languages = input<Language[]>(DEFAULT_LANGUAGES);

  /** Currently selected language code (or 'system') */
  selectedLanguage = input<string>('en');

  /** Whether to show the 'System' option */
  showSystemOption = input<boolean>(true);

  /** Emitted when a language is selected */
  languageSelected = output<string>();

  /** Search query for filtering languages */
  searchQuery = '';

  /** Filtered languages based on search */
  filteredLanguages = computed(() => {
    const query = this.searchQuery.toLowerCase();
    if (!query) return this.languages();

    return this.languages().filter(
      (lang) =>
        lang.name.toLowerCase().includes(query) ||
        lang.nativeName.toLowerCase().includes(query) ||
        lang.code.toLowerCase().includes(query)
    );
  });

  onMenuOpened(): void {
    this.searchQuery = '';
  }

  clearSearch(): void {
    this.searchQuery = '';
  }

  selectLanguage(code: string): void {
    this.languageSelected.emit(code);
  }

  getCurrentLanguage(): Language | undefined {
    const code = this.selectedLanguage();
    if (code === 'system') return undefined;
    return this.languages().find((l) => l.code === code);
  }

  getDisplayLabel(): string {
    const code = this.selectedLanguage();
    if (code === 'system') return 'System';
    const lang = this.languages().find((l) => l.code === code);
    return lang?.nativeName || code;
  }
}
