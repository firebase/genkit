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
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { ChatService, type CompareResponse } from '../../core/services/chat.service';
import { ModelsService } from '../../core/services/models.service';

@Component({
  selector: 'app-compare',
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    MatCheckboxModule,
    MatChipsModule,
  ],
  template: `
    <div class="compare-container">
      <div class="page-header">
        <h1 class="page-title">Compare models</h1>
        <p class="page-desc">Send the same prompt to multiple models and compare responses side by side.</p>
      </div>

      <!-- Model Selection -->
      <section class="section">
        <h2 class="section-title">Select models (2-4)</h2>
        <div class="model-grid">
          @for (provider of modelsService.providers(); track provider.id) {
            <div class="provider-card">
              <div class="provider-header">
                <span class="provider-name">{{ provider.name }}</span>
              </div>
              <div class="model-list">
                @for (model of provider.models; track model.id) {
                  <label class="model-option" [class.selected]="isModelSelected(model.id)">
                    <mat-checkbox 
                      [checked]="isModelSelected(model.id)"
                      (change)="toggleModel(model.id)"
                      [disabled]="!isModelSelected(model.id) && selectedModels().length >= 4">
                    </mat-checkbox>
                    <span class="model-name">{{ model.name }}</span>
                  </label>
                }
              </div>
            </div>
          }
        </div>
      </section>

      <!-- Prompt Input -->
      <section class="section">
        <h2 class="section-title">Enter your prompt</h2>
        <div class="prompt-wrapper">
          <textarea 
            class="prompt-input"
            [(ngModel)]="prompt" 
            rows="4"
            placeholder="E.g., Explain quantum computing in simple terms"></textarea>
        </div>
        
        <button mat-flat-button 
                color="primary"
                class="compare-btn"
                (click)="compare()"
                [disabled]="!prompt.trim() || selectedModels().length < 2 || isLoading()">
          @if (isLoading()) {
            <mat-spinner diameter="20"></mat-spinner>
          } @else {
            <mat-icon>compare_arrows</mat-icon>
          }
          Compare {{ selectedModels().length }} models
        </button>
      </section>

      <!-- Results -->
      @if (results()) {
        <section class="section results-section">
          <h2 class="section-title">Results</h2>
          <div class="results-grid" 
               [class.cols-2]="selectedModels().length === 2" 
               [class.cols-3]="selectedModels().length === 3"
               [class.cols-4]="selectedModels().length >= 4">
            @for (response of results()!.responses; track response.model) {
              <div class="result-card" [class.has-error]="response.error">
                <div class="result-header">
                  <span class="result-model">{{ getModelName(response.model) }}</span>
                  @if (response.latency_ms) {
                    <span class="result-latency">{{ response.latency_ms }}ms</span>
                  }
                </div>
                <div class="result-content">
                  @if (response.error) {
                    <div class="error-state">
                      <mat-icon>error_outline</mat-icon>
                      <span>{{ response.error }}</span>
                    </div>
                  } @else {
                    <p class="result-text">{{ response.response }}</p>
                  }
                </div>
                <div class="result-actions">
                  <button mat-icon-button matTooltip="Copy">
                    <mat-icon>content_copy</mat-icon>
                  </button>
                  <button mat-icon-button matTooltip="Good response">
                    <mat-icon>thumb_up</mat-icon>
                  </button>
                  <button mat-icon-button matTooltip="Bad response">
                    <mat-icon>thumb_down</mat-icon>
                  </button>
                </div>
              </div>
            }
          </div>
        </section>
      }
    </div>
  `,
  styles: [
    `
    :host {
      display: block;
      font-family: 'Google Sans', 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    .compare-container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 24px;
    }

    .page-header {
      margin-bottom: 32px;
    }

    .page-title {
      font-size: 28px;
      font-weight: 400;
      margin: 0 0 8px;
      color: var(--on-surface);
    }

    .page-desc {
      font-size: 14px;
      color: var(--on-surface-variant);
      margin: 0;
    }

    .section {
      margin-bottom: 32px;
    }

    .section-title {
      font-size: 14px;
      font-weight: 500;
      color: var(--on-surface-variant);
      margin: 0 0 16px;
      text-transform: uppercase;
      letter-spacing: 0.02em;
    }

    /* Model Grid */
    .model-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
    }

    .provider-card {
      background: var(--surface-dim);
      border: 1px solid var(--surface-variant);
      border-radius: var(--radius-md);
      overflow: hidden;
    }

    .provider-header {
      padding: 12px 16px;
      background: var(--surface-container);
      border-bottom: 1px solid var(--surface-variant);
    }

    .provider-name {
      font-size: 13px;
      font-weight: 600;
      color: var(--gemini-blue);
      text-transform: uppercase;
      letter-spacing: 0.02em;
    }

    .model-list {
      padding: 8px;
    }

    .model-option {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px;
      border-radius: var(--radius-sm);
      cursor: pointer;
      transition: background var(--transition-fast);
      
      &:hover {
        background: var(--surface-container);
      }
      
      &.selected {
        background: var(--user-bubble-bg);
      }
    }

    .model-name {
      font-size: 14px;
      color: var(--on-surface);
    }

    /* Prompt Input */
    .prompt-wrapper {
      margin-bottom: 16px;
    }

    .prompt-input {
      width: 100%;
      padding: 16px;
      border: 1px solid var(--surface-variant);
      border-radius: var(--radius-md);
      background: var(--surface);
      color: var(--on-surface);
      font-size: 15px;
      font-family: inherit;
      resize: vertical;
      transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
      
      &::placeholder {
        color: var(--on-surface-muted);
      }
      
      &:focus {
        outline: none;
        border-color: var(--gemini-blue);
        box-shadow: 0 0 0 2px rgba(66, 133, 244, 0.2);
      }
    }

    .compare-btn {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 24px;
      font-size: 15px;
      border-radius: var(--radius-full) !important;
      
      mat-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
      }
    }

    /* Results */
    .results-section {
      margin-top: 40px;
    }

    .results-grid {
      display: grid;
      gap: 16px;
      
      &.cols-2 { grid-template-columns: repeat(2, 1fr); }
      &.cols-3 { grid-template-columns: repeat(3, 1fr); }
      &.cols-4 { grid-template-columns: repeat(4, 1fr); }
    }

    @media (max-width: 1024px) {
      .results-grid.cols-3,
      .results-grid.cols-4 {
        grid-template-columns: repeat(2, 1fr);
      }
    }

    @media (max-width: 640px) {
      .results-grid {
        grid-template-columns: 1fr !important;
      }
    }

    .result-card {
      background: var(--surface);
      border: 1px solid var(--surface-variant);
      border-radius: var(--radius-md);
      display: flex;
      flex-direction: column;
      transition: border-color var(--transition-fast);
      
      &:hover {
        border-color: var(--gemini-blue-light);
      }
      
      &.has-error {
        border-color: #ea4335;
      }
    }

    .result-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      border-bottom: 1px solid var(--surface-variant);
    }

    .result-model {
      font-size: 13px;
      font-weight: 600;
      color: var(--on-surface);
    }

    .result-latency {
      font-size: 12px;
      color: var(--on-surface-muted);
      font-family: 'JetBrains Mono', monospace;
    }

    .result-content {
      flex: 1;
      padding: 16px;
    }

    .result-text {
      font-size: 14px;
      line-height: 1.6;
      color: var(--on-surface);
      margin: 0;
      white-space: pre-wrap;
    }

    .error-state {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      color: #ea4335;
      font-size: 13px;
      
      mat-icon {
        flex-shrink: 0;
      }
    }

    .result-actions {
      display: flex;
      gap: 4px;
      padding: 8px 12px;
      border-top: 1px solid var(--surface-variant);
      
      button {
        width: 32px;
        height: 32px;
        
        mat-icon {
          font-size: 18px;
          width: 18px;
          height: 18px;
          color: var(--on-surface-variant);
        }
        
        &:hover mat-icon {
          color: var(--on-surface);
        }
      }
    }
  `,
  ],
})
export class CompareComponent {
  chatService = inject(ChatService);
  modelsService = inject(ModelsService);

  prompt = '';
  selectedModels = signal<string[]>(['googleai/gemini-3-flash-preview']);
  isLoading = signal(false);
  results = signal<CompareResponse | null>(null);

  isModelSelected(modelId: string): boolean {
    return this.selectedModels().includes(modelId);
  }

  toggleModel(modelId: string): void {
    this.selectedModels.update((current) => {
      if (current.includes(modelId)) {
        return current.filter((id) => id !== modelId);
      }
      if (current.length < 4) {
        return [...current, modelId];
      }
      return current;
    });
  }

  getModelName(modelId: string): string {
    const allModels = this.modelsService.getAllModels();
    return allModels.find((m) => m.id === modelId)?.name || modelId;
  }

  compare(): void {
    if (!this.prompt.trim() || this.selectedModels().length < 2) return;

    this.isLoading.set(true);
    this.results.set(null);

    this.chatService.compareModels(this.prompt, this.selectedModels()).subscribe({
      next: (response) => {
        this.results.set(response);
        this.isLoading.set(false);
      },
      error: (_error) => {
        this.isLoading.set(false);
      },
    });
  }
}
