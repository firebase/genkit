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

/**
 * Shared Components - Public API
 *
 * This barrel file exports all self-contained, portable UI components that can
 * be used across Genkit applications or integrated into external applications.
 *
 * Portability Requirements:
 * -------------------------
 * All components exported from this module follow the "Self-Contained Component"
 * pattern, meaning they:
 *
 * 1. Include CSS variable fallbacks (work without global theme)
 * 2. Accept configuration via inputs (not hardcoded services)
 * 3. Emit events via outputs (let parent handle side effects)
 * 4. Have inline styles with fallback values
 * 5. Are fully documented with JSDoc
 *
 * Required Dependencies:
 * ----------------------
 * - @angular/material (Material components)
 * - @ngx-translate/core (Internationalization)
 *
 * Optional:
 * ---------
 * - Material Icons font (for icons)
 * - Custom CSS variables (for theming)
 *
 * Usage Example:
 * --------------
 * ```typescript
 * import { LanguageSelectorComponent, ThemeSelectorComponent } from './shared/components';
 *
 * @Component({
 *   imports: [LanguageSelectorComponent, ThemeSelectorComponent],
 *   template: `
 *     <app-language-selector
 *       [languages]="languages"
 *       [selectedLanguage]="currentLang"
 *       (languageSelected)="onLanguageChange($event)" />
 *
 *     <app-theme-selector
 *       [theme]="currentTheme"
 *       (themeChanged)="onThemeChange($event)" />
 *   `
 * })
 * ```
 */

export type { Language } from './language-selector/language-selector.component';
// Language Selector
export {
  DEFAULT_LANGUAGES,
  LanguageSelectorComponent,
} from './language-selector/language-selector.component';
export type { ThemeMode, ThemeOption } from './theme-selector/theme-selector.component';
// Theme Selector
export { THEME_OPTIONS, ThemeSelectorComponent } from './theme-selector/theme-selector.component';
