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
 * ModelSelectorComponent - Model selection dropdown with search.
 *
 * This component is responsible for:
 * - Displaying the currently selected model
 * - Searchable dropdown for model selection
 * - Recent models section
 * - Models grouped by provider
 *
 * Component Architecture::
 *
 *     ┌─────────────────────────────────────────────┐
 *     │          ModelSelectorComponent             │
 *     ├─────────────────────────────────────────────┤
 *     │  Inputs:                                    │
 *     │  - selectedModel: string                    │
 *     │  - providers: Provider[]                    │
 *     │  - recentModels: Model[]                    │
 *     │                                             │
 *     │  Outputs:                                   │
 *     │  - modelSelected: EventEmitter<string>      │
 *     │                                             │
 *     │  Template Sections:                         │
 *     │  ├── Trigger Button (current model)         │
 *     │  └── Dropdown Menu                          │
 *     │      ├── Search Input                       │
 *     │      ├── Recent Models                      │
 *     │      └── Models by Provider                 │
 *     └─────────────────────────────────────────────┘
 */
import { Component, computed, input, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';

export interface Model {
	id: string;
	name: string;
	capabilities?: string[];
	context_window?: number;
}

export interface Provider {
	id: string;
	name: string;
	available: boolean;
	models: Model[];
}

@Component({
	selector: 'genkit-model-selector',
	standalone: true,
	imports: [
		CommonModule,
		FormsModule,
		MatButtonModule,
		MatIconModule,
		MatMenuModule,
		MatDividerModule,
	],
	template: `
    <button mat-button 
            class="model-select-btn"
            [matMenuTriggerFor]="modelMenu"
            (menuOpened)="onMenuOpened()">
      <div class="model-info">
        <span class="model-name">{{ getModelName(selectedModel()) }}</span>
        <span class="provider-name">{{ getProviderName(selectedModel()) }}</span>
      </div>
      <mat-icon class="dropdown-icon">arrow_drop_down</mat-icon>
    </button>
    
    <mat-menu #modelMenu="matMenu" class="model-panel" xPosition="before">
      <!-- Search Input -->
      <div class="model-search" (click)="$event.stopPropagation()">
        <mat-icon>search</mat-icon>
        <input type="text" 
               placeholder="Search models..." 
               [(ngModel)]="searchQuery"
               (keydown)="$event.stopPropagation()">
        @if (searchQuery) {
          <button mat-icon-button class="clear-search" (click)="clearSearch()">
            <mat-icon>close</mat-icon>
          </button>
        }
      </div>
      
      <!-- Recent Models -->
      @if (!searchQuery && recentModels().length > 0) {
        <div class="model-group">
          <div class="group-header">Recent</div>
          @for (model of recentModels(); track model.id) {
            <button mat-menu-item 
                    class="model-item"
                    [class.selected]="selectedModel() === model.id"
                    (click)="selectModel(model.id)">
              <span class="model-name">{{ model.name }}</span>
              <span class="model-badge">{{ getProviderName(model.id) }}</span>
            </button>
          }
        </div>
        <mat-divider></mat-divider>
      }
      
      <!-- Models Grouped by Provider -->
      <div class="model-list">
        @if (searchQuery) {
          <div class="model-group">
            <div class="group-header">Results</div>
            @for (model of filteredModels(); track model.id) {
              <button mat-menu-item 
                      class="model-item"
                      [class.selected]="selectedModel() === model.id"
                      (click)="selectModel(model.id)">
                <span class="model-name">{{ model.name }}</span>
                <span class="model-badge">{{ getProviderName(model.id) }}</span>
              </button>
            } @empty {
              <div class="no-results">No models found</div>
            }
          </div>
        } @else {
          @for (provider of providers(); track provider.id) {
            <div class="model-group">
              <div class="group-header">{{ provider.name }}</div>
              @for (model of provider.models; track model.id) {
                <button mat-menu-item 
                        class="model-item"
                        [class.selected]="selectedModel() === model.id"
                        (click)="selectModel(model.id)">
                  <span class="model-name">{{ model.name }}</span>
                </button>
              }
            </div>
          }
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

    .model-select-btn {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 4px 8px;
      border-radius: 8px;
      min-width: 0;
      max-width: 200px;
      
      &:hover {
        background: var(--_surface-container-high);
      }
    }

    .model-info {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      overflow: hidden;
      
      .model-name {
        font-size: 13px;
        font-weight: 500;
        color: var(--_on-surface);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 150px;
      }
      
      .provider-name {
        font-size: 11px;
        color: var(--_on-surface-variant);
      }
    }

    .dropdown-icon {
      color: var(--_on-surface-variant);
    }

    ::ng-deep .model-panel {
      max-height: 400px;
      min-width: 280px;
    }

    .model-search {
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

    .model-list {
      max-height: 300px;
      overflow-y: auto;
    }

    .model-group {
      padding: 8px 0;
    }

    .group-header {
      padding: 4px 16px 8px;
      font-size: 11px;
      font-weight: 600;
      color: var(--_on-surface-variant);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .model-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      
      &.selected {
        background: var(--_primary-container);
        color: var(--_on-primary-container);
      }
      
      .model-name {
        flex: 1;
        font-size: 14px;
      }
      
      .model-badge {
        font-size: 10px;
        padding: 2px 6px;
        border-radius: 4px;
        background: var(--_surface-container-high);
        color: var(--_on-surface-variant);
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
export class ModelSelectorComponent {
	/** Currently selected model ID */
	selectedModel = input.required<string>();

	/** List of providers with their models */
	providers = input.required<Provider[]>();

	/** Recently used models */
	recentModels = input<Model[]>([]);

	/** Emitted when a model is selected */
	modelSelected = output<string>();

	/** Search query for filtering models */
	searchQuery = '';

	/** Filtered models based on search query */
	filteredModels = computed(() => {
		if (!this.searchQuery) return [];

		const query = this.searchQuery.toLowerCase();
		const allModels: Model[] = [];

		this.providers().forEach((provider) => {
			provider.models.forEach((model) => {
				if (model.name.toLowerCase().includes(query) || model.id.toLowerCase().includes(query)) {
					allModels.push(model);
				}
			});
		});

		return allModels;
	});

	onMenuOpened(): void {
		this.searchQuery = '';
	}

	clearSearch(): void {
		this.searchQuery = '';
	}

	selectModel(modelId: string): void {
		this.modelSelected.emit(modelId);
	}

	getModelName(modelId: string): string {
		for (const provider of this.providers()) {
			const model = provider.models.find((m) => m.id === modelId);
			if (model) return model.name;
		}
		// Fallback: extract name from ID
		const parts = modelId.split('/');
		return parts[parts.length - 1];
	}

	getProviderName(modelId: string): string {
		for (const provider of this.providers()) {
			if (provider.models.some((m) => m.id === modelId)) {
				return provider.name;
			}
		}
		// Fallback: extract provider from ID prefix
		const parts = modelId.split('/');
		if (parts.length > 1) {
			return parts[0].charAt(0).toUpperCase() + parts[0].slice(1);
		}
		return 'Unknown';
	}
}
