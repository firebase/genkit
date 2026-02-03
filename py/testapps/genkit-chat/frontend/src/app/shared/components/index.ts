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

// Language Selector
export { LanguageSelectorComponent, DEFAULT_LANGUAGES } from './language-selector/language-selector.component';
export type { Language } from './language-selector/language-selector.component';

// Theme Selector
export { ThemeSelectorComponent, THEME_OPTIONS } from './theme-selector/theme-selector.component';
export type { ThemeMode, ThemeOption } from './theme-selector/theme-selector.component';
