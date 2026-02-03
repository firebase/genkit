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
 * MessageListComponent - Displays chat messages with markdown rendering.
 *
 * This component is responsible for:
 * - Rendering user and assistant messages
 * - Markdown rendering for assistant responses
 * - Message actions (copy, speak, thumbs up/down)
 * - Loading indicator with typing animation
 * - Error message display
 *
 * Component Architecture::
 *
 *     ┌─────────────────────────────────────────────────────────────────┐
 *     │                    MessageListComponent                         │
 *     ├─────────────────────────────────────────────────────────────────┤
 *     │  Inputs:                                                        │
 *     │  - messages: Message[]                                          │
 *     │  - isLoading: boolean                                           │
 *     │  - markdownMode: boolean                                        │
 *     │  - avatarUrl: string (optional, default: 'genkit-logo.png')    │
 *     │  - isSpeaking: boolean (optional, for TTS indicator)           │
 *     │                                                                 │
 *     │  Outputs:                                                       │
 *     │  - copy: EventEmitter<string>                                   │
 *     │  - speak: EventEmitter<string>                                  │
 *     │  - showError: EventEmitter<string>                              │
 *     │  - thumbUp: EventEmitter<Message>                               │
 *     │  - thumbDown: EventEmitter<Message>                             │
 *     └─────────────────────────────────────────────────────────────────┘
 *
 * Portability:
 * - This component is SELF-CONTAINED with CSS fallback variables
 * - Requires: @angular/material, @ngx-translate/core
 * - Optional: SafeMarkdownPipe (for markdown rendering)
 * - Avatar URL is configurable via input
 * - SpeechService replaced with isSpeaking input
 */
import {
  type AfterViewChecked,
  Component,
  type ElementRef,
  input,
  output,
  ViewChild,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule } from '@ngx-translate/core';
import { SafeMarkdownPipe } from '../../../../shared/pipes/safe-markdown.pipe';

/**
 * Message interface - defined locally for portability.
 * Compatible with ChatService.Message.
 */
export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
  model?: string;
  isError?: boolean;
  errorDetails?: string;
}

@Component({
  selector: 'app-message-list',
  standalone: true,
  imports: [
    CommonModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    MatMenuModule,
    MatDividerModule,
    TranslateModule,
    SafeMarkdownPipe,
  ],
  template: `
    <div class="messages-container" #messagesContainer>
      @for (message of messages(); track message.timestamp; let i = $index) {
        <div class="message-row animate-fade-in" 
             [class.user-row]="message.role === 'user'" 
             [class.assistant-row]="message.role === 'assistant'"
             [style.animation-delay]="i * 30 + 'ms'">
          
          <!-- Assistant Avatar -->
          @if (message.role === 'assistant') {
            <div class="message-avatar">
              <img [src]="avatarUrl()" [alt]="avatarAlt()" class="avatar-logo">
            </div>
          }
          
          <div class="message-content" [class.user-message]="message.role === 'user'" [class.error-message]="message.isError">
            @if (message.role === 'assistant' && markdownMode()) {
              <div class="message-text markdown-content" [innerHTML]="message.content | safeMarkdown"></div>
            } @else {
              <div class="message-text">{{ message.content }}</div>
            }
            
            @if (message.isError && message.errorDetails) {
              <button mat-stroked-button class="error-details-btn" (click)="showError.emit(message.errorDetails!)">
                <mat-icon>info_outline</mat-icon>
                View Details
              </button>
            }
            
            @if (message.role === 'assistant') {
              <div class="message-actions">
                <button mat-icon-button [matTooltip]="'actions.copy' | translate" (click)="copy.emit(message.content)">
                  <mat-icon>content_copy</mat-icon>
                </button>
                <button mat-icon-button [matTooltip]="'actions.readAloud' | translate" (click)="speak.emit(message.content)">
                  <mat-icon>{{ isSpeaking() ? 'stop' : 'volume_up' }}</mat-icon>
                </button>
                <button mat-icon-button [matTooltip]="'actions.goodResponse' | translate" (click)="thumbUp.emit(message)">
                  <mat-icon>thumb_up</mat-icon>
                </button>
                <button mat-icon-button [matTooltip]="'actions.badResponse' | translate" (click)="thumbDown.emit(message)">
                  <mat-icon>thumb_down</mat-icon>
                </button>
                <button mat-icon-button [matMenuTriggerFor]="moreMenu" [matTooltip]="'actions.more' | translate">
                  <mat-icon>more_vert</mat-icon>
                </button>
                <mat-menu #moreMenu="matMenu">
                  <button mat-menu-item (click)="copy.emit(message.content)">
                    <mat-icon>content_copy</mat-icon>
                    <span>Copy</span>
                  </button>
                  <button mat-menu-item>
                    <mat-icon>refresh</mat-icon>
                    <span>Regenerate</span>
                  </button>
                  <button mat-menu-item>
                    <mat-icon>share</mat-icon>
                    <span>Share</span>
                  </button>
                  <mat-divider></mat-divider>
                  <button mat-menu-item>
                    <mat-icon>flag</mat-icon>
                    <span>Report issue</span>
                  </button>
                </mat-menu>
              </div>
            }
            
            @if (message.model) {
              <div class="message-model">
                <mat-icon>smart_toy</mat-icon>
                {{ message.model }}
              </div>
            }
          </div>
        </div>
      }

      <!-- Loading State -->
      @if (isLoading()) {
        <div class="message-row assistant-row animate-fade-in">
          <div class="message-avatar">
            <img [src]="avatarUrl()" [alt]="avatarAlt()" class="avatar-logo loading">
          </div>
          <div class="message-content">
            <div class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      }
    </div>
  `,
  styles: [
    `
    /* CSS Variable Defaults - ensures component works without global theme */
    :host {
      display: block;
      flex: 1;
      overflow-y: auto;
      overflow-x: hidden;
      padding: 16px 0;
      scroll-behavior: smooth;

      --_primary: var(--primary, #4285f4);
      --_on-primary: var(--on-primary, #ffffff);
      --_surface-container: var(--surface-container, #f0f4f9);
      --_surface-container-high: var(--surface-container-high, #e5eaf0);
      --_on-surface: var(--on-surface, #1a1c1e);
      --_on-surface-variant: var(--on-surface-variant, #5f6368);
      --_error: var(--error, #ba1a1a);
      --_error-container: var(--error-container, #ffdad6);
      --_on-error-container: var(--on-error-container, #410002);
    }

    .messages-container {
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    .message-row {
      display: flex;
      gap: 16px;
      align-items: flex-start;
      
      &.user-row {
        justify-content: flex-end;
      }
      
      &.assistant-row {
        justify-content: flex-start;
      }
    }

    .message-avatar {
      flex-shrink: 0;
      width: 36px;
      height: 36px;
      
      .avatar-logo {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        object-fit: cover;
        
        &.loading {
          animation: pulse 1.5s ease-in-out infinite;
        }
      }
    }

    .message-content {
      max-width: 75%;
      padding: 12px 16px;
      border-radius: 20px;
      background: var(--_surface-container);
      color: var(--_on-surface);
      line-height: 1.5;
      
      &.user-message {
        background: var(--_primary);
        color: var(--_on-primary);
        border-radius: 20px 20px 4px 20px;
      }
      
      &.error-message {
        background: var(--_error-container);
        color: var(--_on-error-container);
        border: 1px solid var(--_error);
      }
    }

    .message-text {
      word-wrap: break-word;
      overflow-wrap: break-word;
      
      &.markdown-content {
        :deep(pre) {
          background: var(--_surface-container-high);
          padding: 12px;
          border-radius: 8px;
          overflow-x: auto;
        }
        
        :deep(code) {
          font-family: 'Roboto Mono', monospace;
          font-size: 0.9em;
        }
        
        :deep(p:last-child) {
          margin-bottom: 0;
        }
        
        :deep(img) {
          max-width: 100%;
          height: auto;
          border-radius: 12px;
          margin: 0.75em 0;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
          max-height: 500px;
          object-fit: contain;
        }
      }
    }

    .message-actions {
      display: flex;
      gap: 4px;
      margin-top: 8px;
      opacity: 0;
      transition: opacity 0.2s ease;
      
      .message-content:hover & {
        opacity: 1;
      }
      
      button {
        width: 28px;
        height: 28px;
        
        mat-icon {
          font-size: 18px;
          width: 18px;
          height: 18px;
        }
      }
    }

    .message-model {
      display: flex;
      align-items: center;
      gap: 4px;
      margin-top: 8px;
      font-size: 11px;
      color: var(--_on-surface-variant);
      opacity: 0.7;
      
      mat-icon {
        font-size: 14px;
        width: 14px;
        height: 14px;
      }
    }

    .error-details-btn {
      margin-top: 8px;
      font-size: 12px;
      
      mat-icon {
        font-size: 16px;
        margin-right: 4px;
      }
    }

    .typing-indicator {
      display: flex;
      gap: 4px;
      padding: 8px 4px;
      
      span {
        width: 8px;
        height: 8px;
        background: var(--_on-surface-variant);
        border-radius: 50%;
        animation: bounce 1.4s ease-in-out infinite;
        
        &:nth-child(2) { animation-delay: 0.2s; }
        &:nth-child(3) { animation-delay: 0.4s; }
      }
    }

    @keyframes bounce {
      0%, 60%, 100% { transform: translateY(0); }
      30% { transform: translateY(-8px); }
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }

    .animate-fade-in {
      animation: fadeIn 0.3s ease forwards;
      opacity: 0;
    }

    @keyframes fadeIn {
      to { opacity: 1; }
    }
  `,
  ],
})
export class MessageListComponent implements AfterViewChecked {
  /** List of messages to display */
  messages = input.required<Message[]>();

  /** Whether the chat is currently loading a response */
  isLoading = input<boolean>(false);

  /** Whether to render markdown in assistant responses */
  markdownMode = input<boolean>(true);

  /** Avatar URL for assistant messages (configurable for portability) */
  avatarUrl = input<string>('genkit-logo.png');

  /** Alt text for avatar image */
  avatarAlt = input<string>('Assistant');

  /** Whether TTS is currently speaking (replaces SpeechService dependency) */
  isSpeaking = input<boolean>(false);

  /** Error message to display (optional) */
  error = input<string | null>(null);

  /** Emitted when user clicks copy on a message */
  copy = output<string>();

  /** Emitted when user clicks speak on a message */
  speak = output<string>();

  /** Emitted when user clicks to view error details */
  showError = output<string>();

  /** Emitted when user gives thumbs up */
  thumbUp = output<Message>();

  /** Emitted when user gives thumbs down */
  thumbDown = output<Message>();

  @ViewChild('messagesContainer') private messagesContainer!: ElementRef;
  private shouldScrollToBottom = true;

  ngAfterViewChecked(): void {
    if (this.shouldScrollToBottom) {
      this.scrollToBottom();
    }
  }

  private scrollToBottom(): void {
    if (this.messagesContainer?.nativeElement) {
      const container = this.messagesContainer.nativeElement;
      container.scrollTop = container.scrollHeight;
    }
  }
}
