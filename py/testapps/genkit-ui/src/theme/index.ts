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
 * Theme Components
 *
 * Self-contained theme and language selection components.
 *
 * Components::
 *
 *     LanguageSelectorComponent - Dropdown for language selection with search
 *     ThemeSelectorComponent    - Toggle or dropdown for theme switching
 *
 * Usage::
 *
 *     import { LanguageSelectorComponent, ThemeSelectorComponent } from '@genkit-ai/genkit-ui/theme';
 *
 *     @Component({
 *       imports: [LanguageSelectorComponent, ThemeSelectorComponent],
 *       template: `
 *         <genkit-language-selector
 *           [selectedLanguage]="currentLang"
 *           (languageSelected)="onLanguageChange($event)" />
 *
 *         <genkit-theme-selector
 *           [theme]="currentTheme"
 *           (themeChanged)="onThemeChange($event)" />
 *       `
 *     })
 *
 * @packageDocumentation
 */

export type { Language } from './language-selector/language-selector.component';
export {
	DEFAULT_LANGUAGES,
	LanguageSelectorComponent,
} from './language-selector/language-selector.component';
export type { ThemeMode, ThemeOption } from './theme-selector/theme-selector.component';
export { THEME_OPTIONS, ThemeSelectorComponent } from './theme-selector/theme-selector.component';
