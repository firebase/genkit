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
 * WelcomeScreenComponent - Greeting animation and quick action chips.
 *
 * This component is responsible for:
 * - Animated greeting carousel with typewriter effect
 * - Multi-language greetings with RTL support
 * - Quick action chips for common prompts
 *
 * Portability:
 * - This component is SELF-CONTAINED with CSS fallback variables
 * - Requires: @angular/material, @ngx-translate/core
 * - Logo URL is configurable via input
 *
 * Component Architecture::
 *
 *     ┌─────────────────────────────────────────────────────────────────┐
 *     │                    WelcomeScreenComponent                       │
 *     ├─────────────────────────────────────────────────────────────────┤
 *     │  Inputs:                                                        │
 *     │  - greetings: Greeting[]                                        │
 *     │  - quickActions: QuickAction[]                                  │
 *     │  - logoUrl: string (optional, default: 'genkit-logo.png')       │
 *     │  - logoAlt: string (optional, default: 'Genkit')                │
 *     │                                                                 │
 *     │  Outputs:                                                       │
 *     │  - actionSelected: EventEmitter<string>                         │
 *     └─────────────────────────────────────────────────────────────────┘
 */
import { Component, input, type OnDestroy, type OnInit, output, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { TranslateModule } from '@ngx-translate/core';

export interface Greeting {
  text: string;
  lang: string;
  dir: 'ltr' | 'rtl';
  anim: 'type' | 'slide';
}

export interface QuickAction {
  icon: string;
  labelKey: string;
  prompt: string;
  color: string;
}

@Component({
  selector: 'app-welcome-screen',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule, TranslateModule],
  template: `
    <div class="welcome-header">
      <div class="welcome-logo">
        <img [src]="logoUrl()" [alt]="logoAlt()">
      </div>
      <h1 class="welcome-title" 
          [class.rtl]="currentGreeting().dir === 'rtl'"
          [class.slide-in]="currentGreeting().anim === 'slide'">
        <span class="typewriter-text">{{ typewriterText() }}</span><span class="cursor" [class.visible]="showCursor()">|</span>
      </h1>
      <p class="welcome-subtitle">{{ 'chat.greetingSubtitle' | translate }}</p>
    </div>
    
    <!-- Quick Action Chips -->
    <div class="quick-chips">
      @for (action of quickActions(); track action.labelKey) {
        <button mat-stroked-button 
                class="quick-chip"
                (click)="actionSelected.emit(action.prompt)">
          <mat-icon class="chip-icon" [style.color]="action.color">{{ action.icon }}</mat-icon>
          <span>{{ action.labelKey | translate }}</span>
        </button>
      }
    </div>
  `,
  styles: [
    `
    /* CSS Variable Defaults - ensures component works without global theme */
    :host {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      padding: 24px 16px;

      --_primary: var(--primary, #4285f4);
      --_on-surface: var(--on-surface, #1a1c1e);
      --_on-surface-variant: var(--on-surface-variant, #5f6368);
      --_surface-container-high: var(--surface-container-high, #e5eaf0);
      --_outline-variant: var(--outline-variant, #c4c6d0);
    }

    .welcome-header {
      display: flex;
      flex-direction: column;
      align-items: center;
      margin-bottom: 32px;
    }

    .welcome-logo {
      margin-bottom: 24px;
      
      img {
        height: 56px;
        width: auto;
        border-radius: 12px;
      }
    }

    .welcome-title {
      font-size: 2.5rem;
      font-weight: 400;
      margin: 0 0 8px 0;
      color: var(--_on-surface);
      min-height: 60px;
      display: flex;
      align-items: center;
      justify-content: center;
      
      &.rtl {
        direction: rtl;
      }
      
      .typewriter-text {
        display: inline;
      }
      
      .cursor {
        display: inline-block;
        width: 2px;
        height: 1em;
        background: var(--_primary);
        margin-left: 2px;
        opacity: 0;
        animation: blink 1s step-end infinite;
        
        &.visible {
          opacity: 1;
        }
      }
    }

    .welcome-subtitle {
      font-size: 1.1rem;
      color: var(--_on-surface-variant);
      margin: 0;
    }

    .quick-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      justify-content: center;
      max-width: 600px;
    }

    .quick-chip {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      border-radius: 24px;
      border: 1px solid var(--_outline-variant);
      background: transparent;
      color: var(--_on-surface);
      font-size: 14px;
      letter-spacing: -0.01em;
      transition: all 0.2s ease;
      
      &:hover {
        background: var(--_surface-container-high);
        border-color: var(--_primary);
      }
      
      .chip-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
      }
    }

    @keyframes blink {
      50% { opacity: 0; }
    }
  `,
  ],
})
export class WelcomeScreenComponent implements OnInit, OnDestroy {
  /** List of greetings to cycle through */
  greetings = input.required<Greeting[]>();

  /** Quick action buttons */
  quickActions = input.required<QuickAction[]>();

  /** Logo URL (configurable for portability) */
  logoUrl = input<string>('genkit-logo.png');

  /** Logo alt text */
  logoAlt = input<string>('Genkit');

  /** Emitted when a quick action is selected */
  actionSelected = output<string>();

  /** Current greeting index */
  currentGreetingIndex = signal(0);

  /** Current typewriter text */
  typewriterText = signal('');

  /** Whether to show the cursor */
  showCursor = signal(true);

  private greetingInterval?: ReturnType<typeof setInterval>;
  private typeInterval?: ReturnType<typeof setTimeout>;
  private eraseInterval?: ReturnType<typeof setTimeout>;

  /** Get the current greeting based on index */
  currentGreeting(): Greeting {
    return this.greetings()[this.currentGreetingIndex()];
  }

  ngOnInit(): void {
    this.startGreetingCarousel();
  }

  ngOnDestroy(): void {
    if (this.greetingInterval) clearInterval(this.greetingInterval);
    if (this.typeInterval) clearTimeout(this.typeInterval);
    if (this.eraseInterval) clearTimeout(this.eraseInterval);
  }

  private startGreetingCarousel(): void {
    const greetings = this.greetings();
    if (greetings.length === 0) return;

    // Type the first greeting
    this.typeGreeting(greetings[0].text, greetings[0].anim, greetings[0].dir);

    // Set up interval to cycle through greetings
    this.greetingInterval = setInterval(() => {
      this.eraseGreeting(() => {
        const nextIndex = (this.currentGreetingIndex() + 1) % greetings.length;
        this.currentGreetingIndex.set(nextIndex);
        const nextGreeting = greetings[nextIndex];
        this.typeGreeting(nextGreeting.text, nextGreeting.anim, nextGreeting.dir);
      }, this.currentGreeting().anim);
    }, 4000);
  }

  private typeGreeting(
    greetingText: string,
    anim: 'type' | 'slide' = 'type',
    _dir: 'ltr' | 'rtl' = 'ltr'
  ): void {
    this.showCursor.set(true);

    if (anim === 'slide') {
      // For slide animation, show full text immediately
      this.typewriterText.set(greetingText);
      return;
    }

    // Typewriter effect
    let charIndex = 0;
    const typeNext = () => {
      if (charIndex <= greetingText.length) {
        this.typewriterText.set(greetingText.substring(0, charIndex));
        charIndex++;
        this.typeInterval = setTimeout(typeNext, 50 + Math.random() * 30);
      }
    };
    typeNext();
  }

  private eraseGreeting(callback: () => void, anim: 'type' | 'slide' = 'type'): void {
    if (anim === 'slide') {
      // For slide, just clear and callback
      this.typewriterText.set('');
      callback();
      return;
    }

    // Erase effect
    const currentText = this.typewriterText();
    let charIndex = currentText.length;

    const eraseNext = () => {
      if (charIndex >= 0) {
        this.typewriterText.set(currentText.substring(0, charIndex));
        charIndex--;
        this.eraseInterval = setTimeout(eraseNext, 30);
      } else {
        callback();
      }
    };
    eraseNext();
  }
}
