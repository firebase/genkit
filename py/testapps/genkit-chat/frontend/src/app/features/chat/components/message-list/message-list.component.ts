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
 *     ┌─────────────────────────────────────────────┐
 *     │           MessageListComponent              │
 *     ├─────────────────────────────────────────────┤
 *     │  Inputs:                                    │
 *     │  - messages: Message[]                      │
 *     │  - isLoading: boolean                       │
 *     │  - markdownMode: boolean                    │
 *     │                                             │
 *     │  Outputs:                                   │
 *     │  - copy: EventEmitter<string>               │
 *     │  - speak: EventEmitter<string>              │
 *     │  - showError: EventEmitter<string>          │
 *     │                                             │
 *     │  Template Sections:                         │
 *     │  ├── Message Loop (user/assistant rows)    │
 *     │  │   ├── Avatar                             │
 *     │  │   ├── Content (markdown or plain text)  │
 *     │  │   └── Actions (copy, speak, feedback)   │
 *     │  └── Loading State (typing indicator)       │
 *     └─────────────────────────────────────────────┘
 */
import { Component, input, output, inject, ElementRef, AfterViewChecked, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { TranslateModule } from '@ngx-translate/core';
import { Message } from '../../../../core/services/chat.service';
import { SpeechService } from '../../../../core/services/speech.service';
import { SafeMarkdownPipe } from '../../../../shared/pipes/safe-markdown.pipe';

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
              <img src="genkit-logo.png" alt="Genkit" class="avatar-logo">
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
                  <mat-icon>{{ speechService.isSpeaking() ? 'stop' : 'volume_up' }}</mat-icon>
                </button>
                <button mat-icon-button [matTooltip]="'actions.goodResponse' | translate">
                  <mat-icon>thumb_up</mat-icon>
                </button>
                <button mat-icon-button [matTooltip]="'actions.badResponse' | translate">
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
            <img src="genkit-logo.png" alt="Genkit" class="avatar-logo loading">
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
    styles: [`
    :host {
      display: block;
      flex: 1;
      overflow-y: auto;
      overflow-x: hidden;
      padding: 16px 0;
      scroll-behavior: smooth;
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
      background: var(--surface-container);
      color: var(--on-surface);
      line-height: 1.5;
      
      &.user-message {
        background: var(--primary);
        color: var(--on-primary);
        border-radius: 20px 20px 4px 20px;
      }
      
      &.error-message {
        background: var(--error-container);
        color: var(--on-error-container);
        border: 1px solid var(--error);
      }
    }

    .message-text {
      word-wrap: break-word;
      overflow-wrap: break-word;
      
      &.markdown-content {
        :deep(pre) {
          background: var(--surface-container-high);
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
      color: var(--on-surface-variant);
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
        background: var(--on-surface-variant);
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
  `]
})
export class MessageListComponent implements AfterViewChecked {
    /** List of messages to display */
    messages = input.required<Message[]>();

    /** Whether the chat is currently loading a response */
    isLoading = input<boolean>(false);

    /** Whether to render markdown in assistant responses */
    markdownMode = input<boolean>(true);

    /** Emitted when user clicks copy on a message */
    copy = output<string>();

    /** Emitted when user clicks speak on a message */
    speak = output<string>();

    /** Emitted when user clicks to view error details */
    showError = output<string>();

    /** Speech service for TTS state */
    speechService = inject(SpeechService);

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
