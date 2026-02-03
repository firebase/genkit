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

import { animate, style, transition, trigger } from '@angular/animations';
import { type CdkDragDrop, DragDropModule } from '@angular/cdk/drag-drop';
import { CommonModule } from '@angular/common';
/**
 * PromptQueueComponent - Queue management with drag-and-drop reordering.
 *
 * This component is responsible for:
 * - Displaying queued prompts waiting to be sent
 * - Drag-and-drop reordering of queue items
 * - Editing queued prompts inline
 * - Queue actions (send now, send all, clear all)
 *
 * Component Architecture::
 *
 *     ┌─────────────────────────────────────────────┐
 *     │           PromptQueueComponent              │
 *     ├─────────────────────────────────────────────┤
 *     │  Inputs:                                    │
 *     │  - queue: QueueItem[]                       │
 *     │                                             │
 *     │  Outputs:                                   │
 *     │  - send: EventEmitter<string>               │
 *     │  - sendAll: EventEmitter<void>              │
 *     │  - remove: EventEmitter<string>             │
 *     │  - clearAll: EventEmitter<void>             │
 *     │  - update: EventEmitter<{id, content}>      │
 *     │  - reorder: EventEmitter<CdkDragDrop>       │
 *     │                                             │
 *     │  Template Sections:                         │
 *     │  ├── Queue Header (count + actions)         │
 *     │  └── Queue Items (draggable list)           │
 *     │      ├── Drag Handle                        │
 *     │      ├── Content (editable)                 │
 *     │      └── Item Actions                       │
 *     └─────────────────────────────────────────────┘
 */
import { Component, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule } from '@ngx-translate/core';

export interface QueueItem {
  id: string;
  content: string;
}

@Component({
  selector: 'app-prompt-queue',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    DragDropModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    TranslateModule,
  ],
  animations: [
    trigger('slideIn', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateY(10px)' }),
        animate('200ms ease-out', style({ opacity: 1, transform: 'translateY(0)' })),
      ]),
      transition(':leave', [
        animate('150ms ease-in', style({ opacity: 0, transform: 'translateY(-10px)' })),
      ]),
    ]),
  ],
  template: `
    <div class="prompt-queue slide-up">
      <div class="queue-header">
        <div class="queue-header-left" (click)="expanded.set(!expanded())">
          <mat-icon class="expand-icon" [class.expanded]="expanded()">expand_more</mat-icon>
          <span class="queue-count">{{ queue().length }} {{ 'queue.queued' | translate }}</span>
        </div>
        <div class="queue-header-actions">
          <button mat-icon-button class="send-all-btn" [matTooltip]="'queue.sendAll' | translate" (click)="sendAll.emit(); $event.stopPropagation()">
            <mat-icon>double_arrow</mat-icon>
          </button>
          <button mat-icon-button class="clear-all-btn" [matTooltip]="'queue.clearAll' | translate" (click)="clearAll.emit(); $event.stopPropagation()">
            <mat-icon>clear_all</mat-icon>
          </button>
        </div>
      </div>
      
      @if (expanded()) {
        <div class="queue-items" cdkDropList (cdkDropListDropped)="onDrop($event)">
          @for (item of queue(); track item.id; let i = $index) {
            <div class="queue-item" cdkDrag @slideIn>
              <mat-icon class="drag-handle" cdkDragHandle>drag_indicator</mat-icon>
              
              @if (editingId() === item.id) {
                <input 
                  class="queue-edit-input" 
                  [(ngModel)]="editingContent"
                  (blur)="saveEdit(item.id)"
                  (keydown.enter)="saveEdit(item.id)"
                  (keydown.escape)="cancelEdit()"
                  #queueEditInput>
              } @else {
                <span class="queue-item-content">{{ item.content }}</span>
              }
              
              <div class="queue-item-actions">
                <button mat-icon-button [matTooltip]="'queue.sendNow' | translate" (click)="send.emit(item.id)">
                  <mat-icon>send</mat-icon>
                </button>
                <button mat-icon-button [matTooltip]="'actions.edit' | translate" (click)="startEdit(item)">
                  <mat-icon>edit</mat-icon>
                </button>
                <button mat-icon-button [matTooltip]="'actions.delete' | translate" (click)="remove.emit(item.id)">
                  <mat-icon>delete</mat-icon>
                </button>
              </div>
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [
    `
    /* CSS Variable Defaults - ensures component works without global theme */
    :host {
      display: block;

      --_primary: var(--primary, #4285f4);
      --_error: var(--error, #ba1a1a);
      --_surface-container: var(--surface-container, #f0f4f9);
      --_surface-container-high: var(--surface-container-high, #e5eaf0);
      --_surface-container-highest: var(--surface-container-highest, #dce0e6);
      --_on-surface: var(--on-surface, #1a1c1e);
      --_on-surface-variant: var(--on-surface-variant, #5f6368);
      --_outline: var(--outline, #74777f);
    }

    .prompt-queue {
      background: var(--_surface-container-high);
      border-radius: 12px;
      padding: 12px 16px;
      margin-bottom: 16px;
    }

    .queue-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .queue-header-left {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      
      &:hover {
        color: var(--_primary);
      }
    }

    .expand-icon {
      transition: transform 0.2s ease;
      
      &.expanded {
        transform: rotate(180deg);
      }
    }

    .queue-count {
      font-size: 14px;
      font-weight: 500;
      color: var(--_on-surface);
    }

    .queue-header-actions {
      display: flex;
      gap: 4px;
      
      button {
        width: 32px;
        height: 32px;
        
        mat-icon {
          font-size: 18px;
          width: 18px;
          height: 18px;
        }
      }
      
      .send-all-btn {
        color: var(--_primary);
      }
      
      .clear-all-btn {
        color: var(--_error);
      }
    }

    .queue-items {
      margin-top: 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .queue-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      background: var(--_surface-container);
      border-radius: 8px;
      cursor: grab;
      
      &:active {
        cursor: grabbing;
      }
    }

    .drag-handle {
      color: var(--_on-surface-variant);
      opacity: 0.6;
      cursor: grab;
      
      &:hover {
        opacity: 1;
      }
    }

    .queue-item-content {
      flex: 1;
      font-size: 14px;
      color: var(--_on-surface);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .queue-edit-input {
      flex: 1;
      background: var(--_surface-container-highest);
      border: 1px solid var(--_outline);
      border-radius: 4px;
      padding: 4px 8px;
      font-size: 14px;
      color: var(--_on-surface);
      
      &:focus {
        outline: none;
        border-color: var(--_primary);
      }
    }

    .queue-item-actions {
      display: flex;
      gap: 4px;
      opacity: 0;
      transition: opacity 0.2s ease;
      
      .queue-item:hover & {
        opacity: 1;
      }
      
      button {
        width: 28px;
        height: 28px;
        
        mat-icon {
          font-size: 16px;
          width: 16px;
          height: 16px;
        }
      }
    }

    /* CDK Drag and Drop styles */
    .cdk-drag-preview {
      box-sizing: border-box;
      border-radius: 8px;
      box-shadow: 0 5px 5px -3px rgba(0, 0, 0, 0.2),
                  0 8px 10px 1px rgba(0, 0, 0, 0.14),
                  0 3px 14px 2px rgba(0, 0, 0, 0.12);
    }

    .cdk-drag-placeholder {
      opacity: 0.3;
    }

    .cdk-drag-animating {
      transition: transform 250ms cubic-bezier(0, 0, 0.2, 1);
    }

    .queue-items.cdk-drop-list-dragging .queue-item:not(.cdk-drag-placeholder) {
      transition: transform 250ms cubic-bezier(0, 0, 0.2, 1);
    }
  `,
  ],
})
export class PromptQueueComponent {
  /** List of queued items */
  queue = input.required<QueueItem[]>();

  /** Emitted when user clicks send on an item */
  send = output<string>();

  /** Emitted when user clicks send all */
  sendAll = output<void>();

  /** Emitted when user clicks remove on an item */
  remove = output<string>();

  /** Emitted when user clicks clear all */
  clearAll = output<void>();

  /** Emitted when a queue item is updated */
  update = output<{ id: string; content: string }>();

  /** Emitted when items are reordered via drag-drop */
  reorder = output<CdkDragDrop<QueueItem[]>>();

  /** Whether the queue is expanded */
  expanded = signal(true);

  /** ID of the item being edited */
  editingId = signal<string | null>(null);

  /** Content being edited */
  editingContent = '';

  onDrop(event: CdkDragDrop<QueueItem[]>): void {
    this.reorder.emit(event);
  }

  startEdit(item: QueueItem): void {
    this.editingId.set(item.id);
    this.editingContent = item.content;
  }

  saveEdit(id: string): void {
    if (this.editingContent.trim()) {
      this.update.emit({ id, content: this.editingContent.trim() });
    }
    this.editingId.set(null);
  }

  cancelEdit(): void {
    this.editingId.set(null);
    this.editingContent = '';
  }
}
