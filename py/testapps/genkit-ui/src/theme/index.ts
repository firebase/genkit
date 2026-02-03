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

export { LanguageSelectorComponent, Language, DEFAULT_LANGUAGES } from './language-selector/language-selector.component';
export { ThemeSelectorComponent, ThemeMode, ThemeOption, THEME_OPTIONS } from './theme-selector/theme-selector.component';
