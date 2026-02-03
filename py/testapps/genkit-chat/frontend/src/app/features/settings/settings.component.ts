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
import { HttpClient } from '@angular/common/http';
import { Component, inject, type OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatOptionModule } from '@angular/material/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSliderModule } from '@angular/material/slider';
import { ThemeService } from '../../core/services/theme.service';

interface ApiKeyInfo {
  configured: boolean;
  preview: string | null;
}

interface ConfigResponse {
  api_keys: {
    GEMINI_API_KEY: ApiKeyInfo;
    ANTHROPIC_API_KEY: ApiKeyInfo;
    OPENAI_API_KEY: ApiKeyInfo;
    OLLAMA_HOST: ApiKeyInfo;
  };
  features: {
    rag_enabled: boolean;
    streaming_enabled: boolean;
    tools_enabled: boolean;
  };
}

@Component({
  selector: 'app-settings',
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatSlideToggleModule,
    MatSliderModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatSelectModule,
    MatFormFieldModule,
    MatOptionModule,
  ],
  template: `
    <div class="settings-container">
      <h1 class="page-title">Settings</h1>

      <!-- API Keys Section -->
      <section class="settings-section">
        <h2 class="section-title">
          <mat-icon>key</mat-icon>
          API Configuration
        </h2>
        <p class="section-desc">API keys are read from environment variables on the backend server.</p>

        @if (loading()) {
          <div class="loading-state">
            <mat-spinner diameter="24"></mat-spinner>
            <span>Loading configuration...</span>
          </div>
        } @else if (config()) {
          <div class="api-keys-list">
            <!-- Google AI -->
            <div class="api-key-item">
              <div class="key-info">
                <div class="key-header">
                  <svg class="provider-icon google" viewBox="0 0 24 24" width="24" height="24">
                    <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                  </svg>
                  <span class="key-name">Google AI</span>
                </div>
                <code class="env-var">GEMINI_API_KEY</code>
              </div>
              <div class="key-status" [class.configured]="config()!.api_keys.GEMINI_API_KEY.configured">
                @if (config()!.api_keys.GEMINI_API_KEY.configured) {
                  <mat-icon class="status-icon success">check_circle</mat-icon>
                  <span class="status-text">{{ config()!.api_keys.GEMINI_API_KEY.preview }}</span>
                } @else {
                  <mat-icon class="status-icon warning">warning</mat-icon>
                  <span class="status-text not-set">Not configured</span>
                }
              </div>
            </div>

            <!-- Anthropic -->
            <div class="api-key-item">
              <div class="key-info">
                <div class="key-header">
                  <svg class="provider-icon anthropic" viewBox="0 0 24 24" width="24" height="24">
                    <path fill="currentColor" d="M17.604 3.332L12.004 20c0-.001-5.605-16.668-5.605-16.668h3.298l2.304 6.855 2.305-6.855h3.298z"/>
                  </svg>
                  <span class="key-name">Anthropic</span>
                </div>
                <code class="env-var">ANTHROPIC_API_KEY</code>
              </div>
              <div class="key-status" [class.configured]="config()!.api_keys.ANTHROPIC_API_KEY.configured">
                @if (config()!.api_keys.ANTHROPIC_API_KEY.configured) {
                  <mat-icon class="status-icon success">check_circle</mat-icon>
                  <span class="status-text">{{ config()!.api_keys.ANTHROPIC_API_KEY.preview }}</span>
                } @else {
                  <mat-icon class="status-icon">radio_button_unchecked</mat-icon>
                  <span class="status-text not-set">Not configured</span>
                }
              </div>
            </div>

            <!-- OpenAI -->
            <div class="api-key-item">
              <div class="key-info">
                <div class="key-header">
                  <svg class="provider-icon openai" viewBox="0 0 24 24" width="24" height="24">
                    <path fill="currentColor" d="M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.516 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.896zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z"/>
                  </svg>
                  <span class="key-name">OpenAI</span>
                </div>
                <code class="env-var">OPENAI_API_KEY</code>
              </div>
              <div class="key-status" [class.configured]="config()!.api_keys.OPENAI_API_KEY.configured">
                @if (config()!.api_keys.OPENAI_API_KEY.configured) {
                  <mat-icon class="status-icon success">check_circle</mat-icon>
                  <span class="status-text">{{ config()!.api_keys.OPENAI_API_KEY.preview }}</span>
                } @else {
                  <mat-icon class="status-icon">radio_button_unchecked</mat-icon>
                  <span class="status-text not-set">Not configured</span>
                }
              </div>
            </div>

            <!-- Ollama -->
            <div class="api-key-item">
              <div class="key-info">
                <div class="key-header">
                  <svg class="provider-icon ollama" viewBox="0 0 24 24" width="24" height="24">
                    <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2"/>
                    <circle cx="12" cy="12" r="4" fill="currentColor"/>
                  </svg>
                  <span class="key-name">Ollama</span>
                </div>
                <code class="env-var">OLLAMA_HOST</code>
              </div>
              <div class="key-status configured">
                <mat-icon class="status-icon success">check_circle</mat-icon>
                <span class="status-text">{{ config()!.api_keys.OLLAMA_HOST.preview }}</span>
              </div>
            </div>
          </div>

          <div class="help-text">
            <mat-icon>info</mat-icon>
            <span>Set environment variables before starting the server. Example: <code>export GEMINI_API_KEY=your-key</code></span>
          </div>
        }
      </section>

      <!-- Appearance Section -->
      <section class="settings-section">
        <h2 class="section-title">
          <mat-icon>palette</mat-icon>
          Appearance
        </h2>
        
        <div class="setting-row">
          <div class="setting-info">
            <span class="setting-label">Theme</span>
            <span class="setting-desc">Choose your preferred color scheme</span>
          </div>
          <mat-form-field appearance="outline" class="theme-select">
            <mat-select [value]="themeService.themeMode()" (selectionChange)="themeService.setTheme($event.value)">
              <mat-option value="system">
                <mat-icon>brightness_auto</mat-icon>
                System
              </mat-option>
              <mat-option value="light">
                <mat-icon>light_mode</mat-icon>
                Light
              </mat-option>
              <mat-option value="dark">
                <mat-icon>dark_mode</mat-icon>
                Dark
              </mat-option>
            </mat-select>
          </mat-form-field>
        </div>
      </section>

      <!-- Generation Defaults Section -->
      <section class="settings-section">
        <h2 class="section-title">
          <mat-icon>tune</mat-icon>
          Generation Defaults
        </h2>
        
        <div class="slider-row">
          <div class="slider-info">
            <span class="setting-label">Temperature</span>
            <span class="slider-value">{{ temperature }}</span>
          </div>
          <mat-slider min="0" max="2" step="0.1" discrete class="full-slider">
            <input matSliderThumb [(ngModel)]="temperature">
          </mat-slider>
          <span class="slider-hint">Lower = more focused, Higher = more creative</span>
        </div>

        <div class="slider-row">
          <div class="slider-info">
            <span class="setting-label">Max output tokens</span>
            <span class="slider-value">{{ maxTokens }}</span>
          </div>
          <mat-slider min="256" max="8192" step="256" discrete class="full-slider">
            <input matSliderThumb [(ngModel)]="maxTokens">
          </mat-slider>
          <span class="slider-hint">Maximum length of generated response</span>
        </div>
      </section>

      <!-- Features Section -->
      @if (config()?.features) {
        <section class="settings-section">
          <h2 class="section-title">
            <mat-icon>extension</mat-icon>
            Features
          </h2>
          
          <div class="features-grid">
            <div class="feature-chip" [class.enabled]="config()!.features.rag_enabled">
              <mat-icon>{{ config()!.features.rag_enabled ? 'check' : 'close' }}</mat-icon>
              <span>RAG / Document Search</span>
            </div>
            <div class="feature-chip" [class.enabled]="config()!.features.streaming_enabled">
              <mat-icon>{{ config()!.features.streaming_enabled ? 'check' : 'close' }}</mat-icon>
              <span>Streaming Responses</span>
            </div>
            <div class="feature-chip" [class.enabled]="config()!.features.tools_enabled">
              <mat-icon>{{ config()!.features.tools_enabled ? 'check' : 'close' }}</mat-icon>
              <span>Tool Calling</span>
            </div>
          </div>
        </section>
      }

      <!-- About Section -->
      <section class="settings-section">
        <h2 class="section-title">
          <mat-icon>info</mat-icon>
          About
        </h2>
        
        <div class="about-content">
          <p><strong>Genkit Chat</strong> v0.1.0</p>
          <p class="about-desc">A multi-model AI chat application demonstrating Genkit Python capabilities.</p>
          
          <div class="tech-stack">
            <a href="https://firebase.google.com/docs/genkit" target="_blank" class="tech-link">
              <mat-icon>auto_awesome</mat-icon>
              Genkit Documentation
            </a>
            <a href="https://github.com/firebase/genkit" target="_blank" class="tech-link">
              <mat-icon>code</mat-icon>
              GitHub Repository
            </a>
          </div>
        </div>
      </section>
    </div>
  `,
  styles: [
    `
    :host {
      display: block;
      font-family: 'Google Sans', 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    .settings-container {
      max-width: 720px;
      margin: 0 auto;
      padding: 24px;
    }

    .page-title {
      font-size: 28px;
      font-weight: 400;
      margin: 0 0 32px;
      color: var(--on-surface);
    }

    .settings-section {
      margin-bottom: 24px;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--surface-variant);
      
      &:last-child {
        border-bottom: none;
        margin-bottom: 0;
        padding-bottom: 0;
      }
    }

    .section-title {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 16px;
      font-weight: 500;
      margin: 0 0 8px;
      color: var(--on-surface);
      
      mat-icon {
        color: var(--gemini-blue);
        font-size: 20px;
        width: 20px;
        height: 20px;
      }
    }

    .section-desc {
      font-size: 14px;
      color: var(--on-surface-variant);
      margin: 0 0 20px;
    }

    .loading-state {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px;
      color: var(--on-surface-variant);
    }

    /* API Keys List */
    .api-keys-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .api-key-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px;
      background: var(--surface-dim);
      border-radius: var(--radius-md);
      border: 1px solid var(--surface-variant);
    }

    .key-info {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .key-header {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .provider-icon {
      width: 24px;
      height: 24px;
      
      &.google { color: #4285f4; }
      &.anthropic { color: #d97706; }
      &.openai { color: #10a37f; }
      &.ollama { color: var(--on-surface-variant); }
    }

    .key-name {
      font-size: 15px;
      font-weight: 500;
      color: var(--on-surface);
    }

    .env-var {
      font-size: 12px;
      color: var(--on-surface-muted);
      background: var(--surface-container);
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
    }

    .key-status {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .status-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
      
      &.success {
        color: #34a853;
      }
      
      &.warning {
        color: #ea8600;
      }
    }

    .status-text {
      font-size: 13px;
      color: var(--on-surface-variant);
      font-family: 'JetBrains Mono', monospace;
      
      &.not-set {
        font-family: inherit;
        font-style: italic;
      }
    }

    .help-text {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      margin-top: 16px;
      padding: 12px;
      background: var(--user-bubble-bg);
      border-radius: var(--radius-sm);
      font-size: 13px;
      color: var(--gemini-blue-dark);
      
      mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        flex-shrink: 0;
      }
      
      code {
        background: rgba(66, 133, 244, 0.1);
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 12px;
      }
    }

    /* Setting Row */
    .setting-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 0;
    }

    .setting-info {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .setting-label {
      font-size: 15px;
      color: var(--on-surface);
    }

    .setting-desc {
      font-size: 13px;
      color: var(--on-surface-variant);
    }

    /* Slider Row */
    .slider-row {
      margin-bottom: 24px;
    }

    .slider-info {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }

    .slider-value {
      font-size: 14px;
      font-weight: 500;
      color: var(--gemini-blue);
      font-family: 'JetBrains Mono', monospace;
    }

    .full-slider {
      width: 100%;
      max-width: 400px;
    }

    .slider-hint {
      font-size: 12px;
      color: var(--on-surface-muted);
      margin-top: 4px;
    }

    .theme-select {
      width: 180px;
      
      .mat-mdc-form-field-subscript-wrapper {
        display: none;
      }
    }

    /* Features Grid */
    .features-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .feature-chip {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 8px 14px;
      background: var(--surface-container);
      border-radius: var(--radius-full);
      font-size: 13px;
      color: var(--on-surface-muted);
      border: 1px solid var(--surface-variant);
      
      mat-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
      }
      
      &.enabled {
        background: var(--user-bubble-bg);
        color: var(--gemini-blue-dark);
        border-color: transparent;
        
        mat-icon {
          color: var(--gemini-blue);
        }
      }
    }

    /* About Section */
    .about-content {
      p {
        margin: 0 0 8px;
        color: var(--on-surface);
      }
      
      .about-desc {
        color: var(--on-surface-variant);
        font-size: 14px;
      }
    }

    .tech-stack {
      display: flex;
      gap: 16px;
      margin-top: 16px;
    }

    .tech-link {
      display: flex;
      align-items: center;
      gap: 6px;
      color: var(--gemini-blue);
      text-decoration: none;
      font-size: 14px;
      
      &:hover {
        text-decoration: underline;
      }
      
      mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
      }
    }
  `,
  ],
})
export class SettingsComponent implements OnInit {
  private http = inject(HttpClient);
  themeService = inject(ThemeService);

  config = signal<ConfigResponse | null>(null);
  loading = signal(true);
  temperature = 0.7;
  maxTokens = 2048;

  ngOnInit(): void {
    this.loadConfig();
  }

  private loadConfig(): void {
    this.http.get<ConfigResponse>('http://localhost:8080/api/config').subscribe({
      next: (data) => {
        this.config.set(data);
        this.loading.set(false);
      },
      error: (_err) => {
        this.loading.set(false);
      },
    });
  }
}
