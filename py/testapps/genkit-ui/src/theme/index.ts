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
 *     import { LanguageSelectorComponent, ThemeSelectorComponent } from '@aspect/genkit-ui/theme';
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

export { LanguageSelectorComponent, DEFAULT_LANGUAGES } from './language-selector/language-selector.component';
export type { Language } from './language-selector/language-selector.component';

export { ThemeSelectorComponent, THEME_OPTIONS } from './theme-selector/theme-selector.component';
export type { ThemeMode, ThemeOption } from './theme-selector/theme-selector.component';

