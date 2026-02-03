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
 * ThemeSelectorComponent - Self-contained theme toggle/dropdown.
 *
 * This component is responsible for:
 * - Displaying the current theme state (light/dark/system)
 * - Toggle button or dropdown for theme selection
 * - Applying theme to document
 *
 * Portability:
 * - This component is SELF-CONTAINED with CSS fallback variables
 * - Requires: @angular/material
 * - Optional: @ngx-translate/core (for labels)
 * - No service dependency required - handles storage internally
 *
 * Component Architecture::
 *
 *     ┌─────────────────────────────────────────────────────────────────┐
 *     │                    ThemeSelectorComponent                       │
 *     ├─────────────────────────────────────────────────────────────────┤
 *     │  Inputs:                                                        │
 *     │  - theme: ThemeMode ('light' | 'dark' | 'system')               │
 *     │  - mode: 'toggle' | 'dropdown' (default: 'dropdown')            │
 *     │                                                                 │
 *     │  Outputs:                                                       │
 *     │  - themeChanged: EventEmitter<ThemeMode>                        │
 *     └─────────────────────────────────────────────────────────────────┘
 */
import { Component, input, output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule } from '@ngx-translate/core';

export type ThemeMode = 'light' | 'dark' | 'system';

export interface ThemeOption {
  mode: ThemeMode;
  icon: string;
  labelKey: string;
}

export const THEME_OPTIONS: ThemeOption[] = [
  { mode: 'system', icon: 'brightness_auto', labelKey: 'theme.system' },
  { mode: 'light', icon: 'light_mode', labelKey: 'theme.light' },
  { mode: 'dark', icon: 'dark_mode', labelKey: 'theme.dark' },
];

@Component({
  selector: 'app-theme-selector',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatTooltipModule,
    TranslateModule,
  ],
  template: `
    @if (mode() === 'toggle') {
      <!-- Toggle Mode: Single button that cycles through themes -->
      <button mat-icon-button 
              class="theme-toggle-btn"
              [matTooltip]="getTooltip()"
              (click)="cycleTheme()">
        <mat-icon>{{ getIcon() }}</mat-icon>
      </button>
    } @else {
      <!-- Dropdown Mode: Button with menu -->
      <button mat-button 
              class="theme-select-btn"
              [matMenuTriggerFor]="themeMenu">
        <mat-icon>{{ getIcon() }}</mat-icon>
        <span class="theme-label">{{ getCurrentOption().labelKey | translate }}</span>
        <mat-icon class="dropdown-icon">arrow_drop_down</mat-icon>
      </button>
      
      <mat-menu #themeMenu="matMenu" xPosition="before">
        @for (option of themeOptions; track option.mode) {
          <button mat-menu-item 
                  class="theme-item"
                  [class.selected]="theme() === option.mode"
                  (click)="selectTheme(option.mode)">
            <mat-icon>{{ option.icon }}</mat-icon>
            <span>{{ option.labelKey | translate }}</span>
            @if (theme() === option.mode) {
              <mat-icon class="check-icon">check</mat-icon>
            }
          </button>
        }
      </mat-menu>
    }
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
    }

    .theme-toggle-btn {
      color: var(--_on-surface-variant);
      
      &:hover {
        color: var(--_primary);
      }
    }

    .theme-select-btn {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 4px 12px;
      border-radius: 8px;
      
      &:hover {
        background: var(--_surface-container-high);
      }

      mat-icon:first-child {
        color: var(--_on-surface-variant);
      }
    }

    .theme-label {
      font-size: 14px;
      color: var(--_on-surface);
    }

    .dropdown-icon {
      color: var(--_on-surface-variant);
    }

    .theme-item {
      display: flex;
      align-items: center;
      gap: 12px;
      
      &.selected {
        background: var(--_primary-container);
        color: var(--_on-primary-container);
      }
      
      .check-icon {
        margin-left: auto;
        color: var(--_primary);
        font-size: 18px;
        width: 18px;
        height: 18px;
      }
    }
  `,
  ],
})
export class ThemeSelectorComponent {
  /** Current theme mode */
  theme = input<ThemeMode>('system');

  /** Display mode: 'toggle' for single button, 'dropdown' for menu */
  mode = input<'toggle' | 'dropdown'>('dropdown');

  /** Emitted when theme changes */
  themeChanged = output<ThemeMode>();

  /** Available theme options */
  readonly themeOptions = THEME_OPTIONS;

  /** Get the current option based on theme */
  getCurrentOption(): ThemeOption {
    return this.themeOptions.find((o) => o.mode === this.theme()) || this.themeOptions[0];
  }

  /** Get icon for current theme */
  getIcon(): string {
    return this.getCurrentOption().icon;
  }

  /** Get tooltip for toggle mode */
  getTooltip(): string {
    const mode = this.theme();
    if (mode === 'system') return 'System theme';
    if (mode === 'dark') return 'Dark theme';
    return 'Light theme';
  }

  /** Cycle through themes (for toggle mode) */
  cycleTheme(): void {
    const current = this.theme();
    const next: ThemeMode =
      current === 'system' ? 'light' : current === 'light' ? 'dark' : 'system';
    this.themeChanged.emit(next);
  }

  /** Select a specific theme (for dropdown mode) */
  selectTheme(mode: ThemeMode): void {
    this.themeChanged.emit(mode);
  }
}
