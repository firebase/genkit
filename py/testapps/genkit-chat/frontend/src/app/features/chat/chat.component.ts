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
import { type CdkDragDrop, DragDropModule, moveItemInArray } from '@angular/cdk/drag-drop';
import { CommonModule } from '@angular/common';
import {
  type AfterViewInit,
  Component,
  type ElementRef,
  effect,
  inject,
  type OnDestroy,
  signal,
  ViewChild,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatRippleModule } from '@angular/material/core';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule } from '@ngx-translate/core';
import { CHAT_CONFIG, getMimeTypeIcon } from '../../core/config/chat.config';
import { AuthService } from '../../core/services/auth.service';
import { ChatService } from '../../core/services/chat.service';
import { ContentSafetyService } from '../../core/services/content-safety.service';
import { ModelsService } from '../../core/services/models.service';
import { PreferencesService } from '../../core/services/preferences.service';
import { SpeechService } from '../../core/services/speech.service';
import { ThemeService } from '../../core/services/theme.service';
import { ErrorDetailsDialogComponent } from '../../shared/error-details-dialog/error-details-dialog.component';
import { SafeMarkdownPipe } from '../../shared/pipes/safe-markdown.pipe';

/**
 * Main chat interface component for Genkit Chat.
 *
 * This is the legacy monolithic component. For new development, prefer using
 * the refactored components from `./components/`:
 *
 * Component Architecture::
 *
 *     ChatComponent (this file - legacy container)
 *     │
 *     └── Refactored Components (./components/)
 *         ├── MessageListComponent      - Message display with markdown
 *         ├── WelcomeScreenComponent    - Greeting animation, quick actions
 *         ├── PromptQueueComponent      - Queue with drag-and-drop
 *         ├── ChatInputComponent        - Input, attachments, voice, settings
 *         │   └── [slot: modelSelector]
 *         └── ModelSelectorComponent    - Searchable model dropdown
 *
 * Migration Path:
 * 1. Import components from './components'
 * 2. Replace template sections with component usages
 * 3. Wire up inputs/outputs to existing services
 * 4. Remove redundant code from this file
 *
 * Example using new components::
 *
 *     <!-- Message list -->
 *     <app-message-list
 *       [messages]="chatService.messages()"
 *       [isLoading]="chatService.isLoading()"
 *       [markdownMode]="chatService.markdownMode()"
 *       (copy)="copyMessage($event)"
 *       (speak)="speakMessage($event)" />
 *
 *     <!-- Welcome screen (when no messages) -->
 *     @if (chatService.messages().length === 0) {
 *       <app-welcome-screen
 *         [greetings]="greetings"
 *         [quickActions]="quickActions"
 *         (actionSelected)="useQuickAction($event)" />
 *     }
 *
 *     <!-- Input area -->
 *     <app-chat-input
 *       [streamingEnabled]="chatService.streamingMode()"
 *       [markdownEnabled]="chatService.markdownMode()"
 *       [safetyEnabled]="contentSafetyService.enabled()"
 *       (send)="handleSend($event)">
 *       <app-model-selector modelSelector
 *         [selectedModel]="modelsService.selectedModel()"
 *         [providers]="modelsService.providers()"
 *         (modelSelected)="modelsService.setSelectedModel($event)" />
 *     </app-chat-input>
 *
 * @see ./components/index.ts for all available components
 */
@Component({
  selector: 'app-chat',
  imports: [
    CommonModule,
    FormsModule,
    DragDropModule,
    MatCardModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatTooltipModule,
    MatMenuModule,
    MatRippleModule,
    MatSnackBarModule,
    MatDividerModule,
    MatDialogModule,
    SafeMarkdownPipe,
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
    // Slide animation for mic/send button transition - slide left
    trigger('slideButton', [
      transition(':enter', [
        style({ opacity: 0, transform: 'translateX(10px)' }),
        animate('150ms ease-out', style({ opacity: 1, transform: 'translateX(0)' })),
      ]),
      transition(':leave', [
        animate('100ms ease-in', style({ opacity: 0, transform: 'translateX(-10px)' })),
      ]),
    ]),
  ],
  template: `
    <div class="chat-container"
         [class.welcome-mode]="chatService.messages().length === 0"
         [class.has-messages]="chatService.messages().length > 0"
         (dragover)="onDragOver($event)"
         (dragleave)="onDragLeave($event)"
         (drop)="onDrop($event)">

      <!-- Drag zone covers entire container to detect drags, but overlay shows in input box -->

      <!-- Messages -->
      <div class="messages-container" #messagesContainer>
        @for (message of chatService.messages(); track message.timestamp; let i = $index) {
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
              @if (message.role === 'assistant' && chatService.markdownMode()) {
                <div class="message-text markdown-content" [innerHTML]="message.content | safeMarkdown"></div>
              } @else {
                <div class="message-text">{{ message.content }}</div>
              }

              @if (message.isError && message.errorDetails) {
                <button mat-stroked-button class="error-details-btn" (click)="showErrorDetails(message.errorDetails)">
                  <mat-icon>info_outline</mat-icon>
                  View Details
                </button>
              }

              @if (message.role === 'assistant') {
                <div class="message-actions">
                  <button mat-icon-button [matTooltip]="'actions.copy' | translate" (click)="copyMessage(message.content)">
                    <mat-icon>content_copy</mat-icon>
                  </button>
                  <button mat-icon-button [matTooltip]="'actions.readAloud' | translate" (click)="speakMessage(message.content)">
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
                    <button mat-menu-item (click)="copyMessage(message.content)">
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
        @if (chatService.isLoading()) {
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

      <!-- Input Section - Gemini Style -->
      <div class="input-section">
        <!-- Welcome Content (above chatbox) - hides when responses start streaming -->
        @if (chatService.messages().length === 0) {
          <div class="welcome-header">
            <div class="welcome-logo">
              <img src="genkit-logo.png" alt="Genkit">
            </div>
            <h1 class="welcome-title"
                [class.rtl]="greetings[currentGreetingIndex()].dir === 'rtl'"
                [class.slide-in]="greetings[currentGreetingIndex()].anim === 'slide'">
              <span class="typewriter-text">{{ typewriterText() }}</span><span class="cursor" [class.visible]="showCursor()">|</span>
            </h1>
            <p class="welcome-subtitle">{{ 'chat.greetingSubtitle' | translate }}</p>
          </div>

          <!-- Quick Action Chips (between greeting and chatbox) -->
          <div class="quick-chips">
            @for (action of quickActions; track action.labelKey) {
              <button mat-stroked-button
                      class="quick-chip"
                      (click)="useQuickAction(action.prompt)">
                <mat-icon class="chip-icon" [style.color]="action.color">{{ action.icon }}</mat-icon>
                <span>{{ action.labelKey | translate }}</span>
              </button>
            }
          </div>
        }

        <!-- Prompt Queue (shows when loading and has queued items) -->
        @if (chatService.isLoading() && chatService.promptQueue().length > 0) {
          <div class="prompt-queue slide-up">
            <div class="queue-header">
              <div class="queue-header-left" (click)="queueExpanded = !queueExpanded">
                <mat-icon class="expand-icon" [class.expanded]="queueExpanded">expand_more</mat-icon>
                <span class="queue-count">{{ chatService.promptQueue().length }} {{ 'queue.queued' | translate }}</span>
              </div>
              <div class="queue-header-actions">
                <button mat-icon-button class="send-all-btn" [matTooltip]="'queue.sendAll' | translate" (click)="chatService.sendAllFromQueue(); $event.stopPropagation()">
                  <mat-icon>double_arrow</mat-icon>
                </button>
                <button mat-icon-button class="clear-all-btn" [matTooltip]="'queue.clearAll' | translate" (click)="chatService.clearQueue(); $event.stopPropagation()">
                  <mat-icon>clear_all</mat-icon>
                </button>
              </div>
            </div>
            @if (queueExpanded) {
              <div class="queue-items" cdkDropList (cdkDropListDropped)="onQueueDrop($event)">
                @for (item of chatService.promptQueue(); track item.id; let i = $index) {
                  <div class="queue-item" cdkDrag @slideIn>
                    <mat-icon class="drag-handle" cdkDragHandle>drag_indicator</mat-icon>
                    @if (editingQueueId === item.id) {
                      <input
                        class="queue-edit-input"
                        [(ngModel)]="editingQueueContent"
                        (blur)="saveQueueEdit(item.id)"
                        (keydown.enter)="saveQueueEdit(item.id)"
                        (keydown.escape)="cancelQueueEdit()"
                        #queueEditInput>
                    } @else {
                      <span class="queue-item-content">{{ item.content }}</span>
                    }
                    <div class="queue-item-actions">
                      <button mat-icon-button [matTooltip]="'queue.sendNow' | translate" (click)="chatService.sendFromQueue(item.id)">
                        <mat-icon>send</mat-icon>
                      </button>
                      <button mat-icon-button [matTooltip]="'actions.edit' | translate" (click)="startEditQueue(item)">
                        <mat-icon>edit</mat-icon>
                      </button>
                      <button mat-icon-button [matTooltip]="'actions.delete' | translate" (click)="chatService.removeFromQueue(item.id)">
                        <mat-icon>delete</mat-icon>
                      </button>
                    </div>
                  </div>
                }
              </div>
            }
          </div>
        }

        <div class="input-box" [class.focused]="inputFocused" [class.pulse-send]="isPulsing" [class.is-dragging]="isDragging()" (click)="focusInput($event)">
          <!-- Drop Zone Overlay (inside input box) -->
          @if (isDragging()) {
            <div class="drop-zone-overlay">
              <mat-icon class="drop-icon">cloud_upload</mat-icon>
              <span class="drop-caption">Drop files to attach</span>
            </div>
          }

          <textarea class="chat-input"
                    [class.content-flagged]="contentFlagged()"
                    [(ngModel)]="userMessage"
                    [placeholder]="'chat.placeholder' | translate"
                    [attr.aria-label]="'chat.placeholder' | translate"
                    (keydown.enter)="onEnterKey($event)"
                    (focus)="inputFocused = true"
                    (blur)="inputFocused = false"
                    (input)="onInputChange()"
                    [matTooltip]="contentFlagged() ? 'Content flagged: ' + flaggedLabels().join(', ') : ''"
                    [matTooltipClass]="'flagged-content-tooltip'"
                    rows="1"
                    #chatTextarea></textarea>

          @if (userMessage) {
            <button mat-icon-button class="clear-input-btn" (click)="clearInput()" [attr.aria-label]="'chat.clearInput' | translate" [matTooltip]="'chat.clearInput' | translate">
              <mat-icon>close</mat-icon>
            </button>
          }

          <!-- Bottom Toolbar -->
          <div class="input-toolbar">
            <div class="toolbar-left">
              <!-- Add/Attach Button -->
              <button mat-icon-button
                      class="toolbar-btn add-btn"
                      [attr.aria-label]="'chat.addFiles' | translate"
                      [matTooltip]="'chat.addFiles' | translate"
                      [matMenuTriggerFor]="attachMenu">
                <mat-icon>add</mat-icon>
              </button>

              <mat-menu #attachMenu="matMenu" class="attach-menu">
                <button mat-menu-item (click)="anyInput.click()">
                  <mat-icon>upload_file</mat-icon>
                  <span>{{ 'chat.uploadFiles' | translate }}</span>
                </button>
                <button mat-menu-item (click)="openGoogleDrive()"
                        [disabled]="authService.demoMode()"
                        [matTooltip]="authService.demoMode() ? ('nav.demoUser' | translate) : ''">
                  <mat-icon>add_to_drive</mat-icon>
                  <span>{{ 'chat.googleDrive' | translate }}</span>
                </button>
                <button mat-menu-item (click)="imageInput.click()">
                  <mat-icon>image</mat-icon>
                  <span>{{ 'attach.photos' | translate }}</span>
                </button>
                <mat-divider></mat-divider>
                <button mat-menu-item (click)="audioInput.click()">
                  <mat-icon>audio_file</mat-icon>
                  <span>{{ 'attach.audio' | translate }}</span>
                </button>
                <button mat-menu-item (click)="videoInput.click()">
                  <mat-icon>videocam</mat-icon>
                  <span>{{ 'attach.video' | translate }}</span>
                </button>
                <button mat-menu-item (click)="pdfInput.click()">
                  <mat-icon>picture_as_pdf</mat-icon>
                  <span>{{ 'attach.pdf' | translate }}</span>
                </button>
                <button mat-menu-item (click)="textInput.click()">
                  <mat-icon>code</mat-icon>
                  <span>{{ 'attach.code' | translate }}</span>
                </button>
              </mat-menu>

              <!-- Hidden file inputs -->
              <input #imageInput type="file" hidden (change)="onFileSelected($event)" multiple accept="image/*">
              <input #videoInput type="file" hidden (change)="onFileSelected($event)" multiple accept="video/*">
              <input #audioInput type="file" hidden (change)="onFileSelected($event)" multiple accept="audio/*">
              <input #pdfInput type="file" hidden (change)="onFileSelected($event)" multiple accept=".pdf">
              <input #textInput type="file" hidden (change)="onFileSelected($event)" multiple accept=".txt,.md,.json,.csv,.xml,.yaml,.yml,.py,.ts,.js,.go,.rs,.java">
              <input #anyInput type="file" hidden (change)="onFileSelected($event)" multiple>

              <!-- Tools Button -->
              <button mat-button class="toolbar-btn tools-btn">
                <mat-icon>handyman</mat-icon>
                <span>{{ 'toolbar.tools' | translate }}</span>
              </button>

            </div>

            <div class="toolbar-right">
              <!-- Model Selector -->
              <button mat-button
                      class="model-select-btn"
                      [matMenuTriggerFor]="modelMenu"
                      (menuOpened)="onModelMenuOpened()">
                <div class="model-info">
                  <span class="model-name">{{ modelsService.getModelName(modelsService.selectedModel()) }}</span>
                  <span class="provider-name">{{ modelsService.getProviderName(modelsService.selectedModel()) }}</span>
                </div>
                <mat-icon class="dropdown-icon">arrow_drop_down</mat-icon>
              </button>

              <mat-menu #modelMenu="matMenu" class="model-panel" xPosition="before">
                <!-- Search Input -->
                <div class="model-search" (click)="$event.stopPropagation()">
                  <mat-icon>search</mat-icon>
                  <input type="text"
                         placeholder="Search models..."
                         [(ngModel)]="modelSearchQuery"
                         (input)="filterModels()"
                         (keydown)="$event.stopPropagation()">
                  @if (modelSearchQuery) {
                    <button mat-icon-button class="clear-search" (click)="clearModelSearch()">
                      <mat-icon>close</mat-icon>
                    </button>
                  }
                </div>

                <!-- Recent Models -->
                @if (!modelSearchQuery && modelsService.getRecentModels().length > 0) {
                  <div class="model-group">
                    <div class="group-header">Recent</div>
                    @for (model of modelsService.getRecentModels(); track model.id) {
                      <button mat-menu-item
                              class="model-item"
                              [class.selected]="modelsService.selectedModel() === model.id"
                              (click)="selectModel(model.id)">
                        <span class="model-name">{{ model.name }}</span>
                        <span class="model-badge">{{ modelsService.getProviderName(model.id) }}</span>
                      </button>
                    }
                  </div>
                  <mat-divider></mat-divider>
                }

                <!-- Models Grouped by Provider -->
                <div class="model-list">
                  @if (modelSearchQuery) {
                    <div class="model-group">
                      <div class="group-header">Results</div>
                      @for (model of filteredModels(); track model.id) {
                        <button mat-menu-item
                                class="model-item"
                                [class.selected]="modelsService.selectedModel() === model.id"
                                (click)="selectModel(model.id)">
                          <span class="model-name">{{ model.name }}</span>
                          <span class="model-badge">{{ modelsService.getProviderName(model.id) }}</span>
                        </button>
                      } @empty {
                        <div class="no-results">No models found</div>
                      }
                    </div>
                  } @else {
                    @for (provider of modelsService.providers(); track provider.id) {
                      <div class="model-group">
                        <div class="group-header">{{ provider.name }}</div>
                        @for (model of modelsService.getModelsByProvider(provider.id); track model.id) {
                          <button mat-menu-item
                                  class="model-item"
                                  [class.selected]="modelsService.selectedModel() === model.id"
                                  (click)="selectModel(model.id)">
                            <span class="model-name">{{ model.name }}</span>
                          </button>
                        }
                      </div>
                    }
                  }
                </div>
              </mat-menu>

              <!-- Settings Dropdown (icon only) - between model selector and mic -->
              <button mat-icon-button
                      class="toolbar-btn settings-btn"
                      [matMenuTriggerFor]="settingsMenu"
                      [attr.aria-label]="'toolbar.settings' | translate"
                      [matTooltip]="'toolbar.settings' | translate">
                <mat-icon>tune</mat-icon>
              </button>
              <mat-menu #settingsMenu="matMenu" class="settings-menu">
                <!-- Streaming Toggle -->
                <button mat-menu-item
                        [disabled]="!modelsService.supportsStreaming()"
                        (click)="toggleStreaming(); $event.stopPropagation()">
                  <mat-icon>{{ chatService.streamingMode() && modelsService.supportsStreaming() ? 'stream' : 'pause_circle' }}</mat-icon>
                  <span>{{ 'toolbar.stream' | translate }}</span>
                  <mat-icon class="toggle-indicator"
                            [class.active]="chatService.streamingMode() && modelsService.supportsStreaming()">
                    {{ chatService.streamingMode() && modelsService.supportsStreaming() ? 'check_circle' : 'radio_button_unchecked' }}
                  </mat-icon>
                </button>

                <!-- Markdown Toggle -->
                <button mat-menu-item (click)="chatService.toggleMarkdownMode(); $event.stopPropagation()">
                  <mat-icon>{{ chatService.markdownMode() ? 'code' : 'code_off' }}</mat-icon>
                  <span>{{ 'toolbar.markdown' | translate }}</span>
                  <mat-icon class="toggle-indicator" [class.active]="chatService.markdownMode()">
                    {{ chatService.markdownMode() ? 'check_circle' : 'radio_button_unchecked' }}
                  </mat-icon>
                </button>

                <!-- Content Safety Toggle -->
                <button mat-menu-item (click)="contentSafetyService.toggle(); $event.stopPropagation()">
                  <mat-icon>{{ contentSafetyService.enabled() ? 'shield' : 'shield_outlined' }}</mat-icon>
                  <span>{{ 'toolbar.safe' | translate }}</span>
                  <mat-icon class="toggle-indicator"
                            [class.active]="contentSafetyService.enabled()"
                            [class.loading]="contentSafetyService.loading()">
                    {{ contentSafetyService.enabled() ? 'check_circle' : 'radio_button_unchecked' }}
                  </mat-icon>
                </button>

                <mat-divider></mat-divider>

                <!-- Clear Preferences -->
                <button mat-menu-item (click)="clearPreferences()">
                  <mat-icon>delete_outline</mat-icon>
                  <span>{{ 'settings.clearPreferences' | translate }}</span>
                </button>
              </mat-menu>

              <!-- Send Button (when text is entered) or Voice Input -->
              <div class="action-btn-container">
                @if (showSendButton()) {
                  <button mat-icon-button
                          class="toolbar-btn send-btn"
                          @slideButton
                          [attr.aria-label]="'chat.sendMessage' | translate"
                          [matTooltip]="'chat.sendMessage' | translate"
                          (click)="sendMessage()">
                    <mat-icon>send</mat-icon>
                  </button>
                } @else if (speechService.isSupported()) {
                  <button mat-icon-button
                          class="toolbar-btn mic-btn"
                          @slideButton
                          [class.recording]="speechService.isListening()"
                          [attr.aria-label]="speechService.isListening() ? ('chat.stopRecording' | translate) : ('chat.voiceInput' | translate)"
                          [matTooltip]="speechService.isListening() ? ('chat.stopRecording' | translate) : ('chat.voiceInput' | translate)"
                          (click)="toggleVoiceInput()">
                    <mat-icon>{{ speechService.isListening() ? 'mic_off' : 'mic' }}</mat-icon>
                  </button>
                }
              </div>
            </div>
          </div>
        </div>

        <!-- Attached Files List (below chatbox) - also acts as dropzone -->
        @if (attachedFiles().length > 0) {
          <div class="attached-files-container"
               (dragover)="onDragOver($event)"
               (dragleave)="onDragLeave($event)"
               (drop)="onDrop($event)"
               [class.is-dragging]="isDragging()">
            <!-- Header toolbar -->
            <div class="attachments-header">
              <span class="attachments-count">{{ attachedFiles().length }} file{{ attachedFiles().length > 1 ? 's' : '' }} attached</span>
              <div class="attachments-actions">
                <button mat-icon-button
                        class="add-more-btn"
                        (click)="anyInput.click()"
                        [attr.aria-label]="'chat.addMoreFiles' | translate"
                        [matTooltip]="'chat.addMoreFiles' | translate">
                  <mat-icon>add</mat-icon>
                </button>
                <button mat-icon-button
                        class="clear-all-btn"
                        (click)="clearAllFiles()"
                        [attr.aria-label]="'actions.clearAll' | translate"
                        [matTooltip]="'actions.clearAll' | translate">
                  <mat-icon>delete_sweep</mat-icon>
                </button>
              </div>
            </div>

            <!-- File list -->
            <div class="attached-files-list">
              @for (file of attachedFiles(); track file.name) {
                <div class="file-row">
                  <!-- Icon or Thumbnail -->
                  <div class="file-icon-wrapper">
                    @if (file.type.startsWith('image/')) {
                      <img [src]="file.preview" alt="preview" class="file-thumb-small">
                    } @else {
                      <mat-icon class="file-type-icon-small">{{ getFileIcon(file.type) }}</mat-icon>
                    }
                  </div>

                  <!-- File name (truncated with tooltip for full name) -->
                  <span class="file-name-text" [matTooltip]="file.name">{{ file.name }}</span>

                  <!-- File size -->
                  <span class="file-size-text">{{ formatFileSize(file.size) }}</span>

                  <!-- Remove button -->
                  <button mat-icon-button
                          class="file-remove-btn-small"
                          (click)="removeFile(file)"
                          [attr.aria-label]="('actions.remove' | translate) + ' ' + file.name"
                          [matTooltip]="'actions.remove' | translate">
                    <mat-icon>close</mat-icon>
                  </button>
                </div>
              }
            </div>

            <!-- Drop overlay for adding more files -->
            @if (isDragging()) {
              <div class="attachments-drop-overlay">
                <mat-icon>add_circle</mat-icon>
                <span>Drop to add more files</span>
              </div>
            }
          </div>
        }

      </div>
    </div>
  `,
  styles: [
    `
    :host {
      display: block;
      width: 100%;
      height: 100%;
      overflow: hidden;
      font-family: 'Google Sans', 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }

    .chat-container {
      display: flex;
      flex-direction: column;
      height: 100%;
      max-width: 860px;
      margin: 0 auto;
      padding: 0 24px;
      position: relative;
      overflow: hidden;
    }

    /* When in welcome mode (no messages), center content */
    .chat-container.welcome-mode {
      justify-content: center;
    }

    /* When has messages, use flex layout for scroll */
    .chat-container.has-messages {
      justify-content: flex-start;
    }

    /* Welcome Section */
    .welcome-section {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px 16px;
      text-align: center;
    }

    .welcome-logo {
      margin-bottom: 24px;

      img {
        height: 56px;
        width: auto;
        border-radius: 12px;

        &.dark {
          /* filter: invert(1); removed */
        }
      }
    }

    .welcome-title {
      font-size: 40px;
      font-weight: 400;
      margin: 0 0 8px;
      color: var(--on-surface);
    }

    .welcome-subtitle {
      font-size: 16px;
      color: var(--on-surface-variant);
      margin: 0 0 40px;
    }

    .suggestions-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
      width: 100%;
      max-width: 500px;
    }

    @media (max-width: 500px) {
      .suggestions-grid {
        grid-template-columns: 1fr;
      }
    }

    .suggestion-card {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 16px;
      background: var(--surface);
      border: 1px solid var(--surface-variant);
      border-radius: var(--radius-md);
      cursor: pointer;
      text-align: left;
      transition: all var(--transition-fast);
      font-family: inherit;

      &:hover {
        background: var(--surface-dim);
        border-color: var(--gemini-blue-light);
      }

      &:active {
        transform: scale(0.98);
      }
    }

    .suggestion-icon {
      color: var(--gemini-blue);
      font-size: 20px;
      width: 20px;
      height: 20px;
    }

    .suggestion-text {
      flex: 1;
      font-size: 14px;
      color: var(--on-surface);
      line-height: 1.4;
    }

    /* Messages */
    .messages-container {
      flex: 1;
      min-height: 0; /* Critical for flexbox scrolling */
      overflow-y: auto;
      padding: 24px 0;
      padding-bottom: 120px; /* Large space before input section + queue */
    }

    .message-row {
      display: flex;
      align-items: flex-start;
      gap: 16px;
      padding: 16px 0;

      &.user-row {
        justify-content: flex-end;
      }
    }

    .message-avatar {
      flex-shrink: 0;
      width: 28px;
      height: 28px;
      width: 28px;
      height: 28px;
      margin-top: 0; /* Align with first line text baseline */
    }

    .avatar-logo {
      width: 28px;
      height: auto;

      &.dark {
        /* filter: invert(1); removed */
      }

      &.loading {
        animation: pulse 1.2s ease-in-out infinite;
      }
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }

    .message-content {
      flex: 1;
      max-width: 720px;
    }

    .user-message {
      background: var(--user-bubble-bg);
      padding: 12px 16px;
      border-radius: 20px;
      max-width: fit-content;
      margin-left: auto;
    }

    .message-text {
      font-size: 15px;
      line-height: 1.7;
      color: var(--on-surface);
      white-space: pre-wrap;
      word-break: break-word;
    }

    /* Markdown content styling */
    .markdown-content {
      white-space: normal;

      p {
        margin: 0 0 0.75em;
        &:last-child {
          margin-bottom: 0;
        }
      }

      h1, h2, h3, h4, h5, h6 {
        margin: 1em 0 0.5em;
        font-weight: 600;
        line-height: 1.3;
        &:first-child {
          margin-top: 0;
        }
      }

      h1 { font-size: 1.4em; }
      h2 { font-size: 1.25em; }
      h3 { font-size: 1.1em; }
      h4, h5, h6 { font-size: 1em; }

      code {
        font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Mono', monospace;
        font-size: 0.85em;
        padding: 2px 6px;
        background: var(--surface-variant);
        border-radius: 4px;
      }

      pre {
        margin: 0.75em 0;
        padding: 12px 16px;
        background: var(--surface-variant);
        border-radius: 8px;
        overflow-x: auto;

        code {
          padding: 0;
          background: none;
          font-size: 0.85em;
        }
      }

      ul, ol {
        margin: 0.5em 0;
        padding-left: 1.5em;
      }

      li {
        margin: 0.25em 0;
      }

      blockquote {
        margin: 0.75em 0;
        padding: 8px 16px;
        border-left: 3px solid var(--gemini-blue);
        background: var(--surface-variant);
        font-style: italic;
      }

      a {
        color: var(--gemini-blue);
        text-decoration: none;
        &:hover {
          text-decoration: underline;
        }
      }

      table {
        border-collapse: collapse;
        margin: 0.75em 0;
        width: 100%;
      }

      th, td {
        padding: 8px 12px;
        border: 1px solid var(--outline);
        text-align: left;
      }

      th {
        background: var(--surface-variant);
        font-weight: 600;
      }

      hr {
        border: none;
        border-top: 1px solid var(--outline);
        margin: 1em 0;
      }

      img {
        max-width: 100%;
        height: auto;
        border-radius: 12px;
        margin: 0.75em 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        cursor: zoom-in;
        transition: transform 0.2s ease, box-shadow 0.2s ease;

        &:hover {
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
        }

        /* Limit max height for very tall images */
        max-height: 500px;
        object-fit: contain;
      }

      /* Mermaid diagram styling */
      .mermaid-diagram {
        margin: 1em 0;
        padding: 16px;
        background: var(--surface-variant);
        border-radius: 12px;
        overflow-x: auto;

        svg {
          max-width: 100%;
          height: auto;
        }
      }

      .mermaid-error {
        padding: 12px 16px;
        background: rgba(217, 48, 37, 0.1);
        border: 1px solid rgba(217, 48, 37, 0.3);
        border-radius: 8px;
        color: #d93025;
        font-family: monospace;
        font-size: 0.9em;
      }

      /* Math equation styling */
      .math-inline {
        font-family: 'Cambria Math', 'Times New Roman', serif;
        font-style: italic;
        padding: 0 2px;
      }

      .math-display {
        display: block;
        text-align: center;
        font-family: 'Cambria Math', 'Times New Roman', serif;
        font-size: 1.2em;
        margin: 1em 0;
        padding: 16px;
        background: var(--surface-variant);
        border-radius: 8px;
      }

      .math-frac {
        display: inline-flex;
        flex-direction: column;
        align-items: center;
        vertical-align: middle;
        margin: 0 4px;

        .math-num {
          border-bottom: 1px solid currentColor;
          padding-bottom: 2px;
        }

        .math-denom {
          padding-top: 2px;
        }
      }
    }

    .user-message .message-text {
      color: var(--user-bubble-text);
    }

    /* Error message styling */
    .error-message {
      .message-text {
        color: #d93025;
      }
    }

    .error-details-btn {
      margin-top: 8px;
      font-size: 12px;
      color: #d93025;
      border-color: #d93025;
      padding: 4px 12px;
      height: auto;
      line-height: 1.4;

      mat-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
        margin-right: 4px;
      }

      &:hover {
        background: rgba(217, 48, 37, 0.08);
      }
    }

    .message-actions {
      display: flex;
      gap: 2px;
      margin-top: 8px;
      opacity: 0;
      transition: opacity var(--transition-fast);

      .message-row:hover & {
        opacity: 1;
      }

      button {
        width: 32px;
        height: 32px;

        mat-icon {
          font-size: 18px;
          width: 18px;
          height: 18px;
          color: var(--on-surface-muted);
        }

        &:hover mat-icon {
          color: var(--on-surface);
        }
      }
    }

    .message-model {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      color: var(--on-surface-muted);
      margin-top: 8px;

      mat-icon {
        font-size: 14px;
        width: 14px;
        height: 14px;
      }
    }

    /* Typing Indicator */
    .typing-indicator {
      display: flex;
      gap: 4px;
      padding: 8px 0;

      span {
        width: 8px;
        height: 8px;
        background: var(--on-surface-muted);
        border-radius: 50%;
        animation: bounce 1.4s infinite ease-in-out;

        &:nth-child(1) { animation-delay: -0.32s; }
        &:nth-child(2) { animation-delay: -0.16s; }
      }
    }

    @keyframes bounce {
      0%, 80%, 100% {
        transform: scale(0.8);
        opacity: 0.5;
      }
      40% {
        transform: scale(1);
        opacity: 1;
      }
    }

    /* Attached Files */
    .attached-files {
      display: flex;
      gap: 8px;
      padding: 12px 0;
      flex-wrap: wrap;
    }

    .file-chip {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      background: var(--surface-container);
      border: 1px solid var(--surface-variant);
      border-radius: var(--radius-full);
    }

    .file-thumb {
      width: 24px;
      height: 24px;
      border-radius: 4px;
      object-fit: cover;
    }

    .file-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
      color: var(--on-surface-variant);
    }

    .file-name {
      font-size: 13px;
      color: var(--on-surface);
      max-width: 150px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .file-remove {
      width: 24px !important;
      height: 24px !important;
      margin: -4px -4px -4px 0;

      mat-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
      }
    }

    /* Prompt Queue */
    .prompt-queue {
      width: 90%;
      max-width: 740px;
      margin: 0 auto 0; /* No bottom margin - chatbox overlays */
      background: var(--surface-container);
      border-radius: var(--radius-lg) var(--radius-lg) 0 0; /* Rounded top only */
      border: 1px solid var(--surface-variant);
      border-bottom: none; /* Remove bottom border - hidden by chatbox */
      overflow: hidden;
      box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.08), 0 -2px 8px rgba(0, 0, 0, 0.04);
      position: relative;
      z-index: 1; /* Below chatbox */

      &.slide-up {
        animation: slideUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      }
    }

    @keyframes slideUp {
      from {
        opacity: 0;
        transform: translateY(20px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .queue-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 12px 8px 16px;
      transition: background 0.2s;
    }

    .queue-header-left {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      flex: 1;

      &:hover {
        opacity: 0.8;
      }
    }

    .queue-header-actions {
      display: flex;
      align-items: center;
      gap: 2px;
    }

    .send-all-btn,
    .clear-all-btn {
      width: 24px !important;
      height: 24px !important;
      display: flex !important;
      align-items: center !important;
      justify-content: center !important;
      padding: 0 !important;

      mat-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
        color: var(--on-surface-variant);
        display: flex;
        align-items: center;
        justify-content: center;
      }
    }

    .send-all-btn:hover mat-icon {
      color: var(--gemini-blue);
    }

    .clear-all-btn:hover mat-icon {
      color: var(--error);
    }

    .expand-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
      color: var(--on-surface-variant);
      transition: transform 0.2s;

      &.expanded {
        transform: rotate(180deg);
      }
    }

    .queue-count {
      font-size: 12px;
      font-weight: 500;
      color: var(--on-surface-variant);
    }

    .queue-items {
      border-top: 1px solid var(--surface-variant);
      max-height: 150px;
      overflow-y: auto;
    }

    .queue-item {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border-bottom: 1px solid var(--surface-variant);
      background: var(--surface-container);
      transition: box-shadow 0.2s, transform 0.2s;

      &:last-child {
        border-bottom: none;
      }

      &.cdk-drag-preview {
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        border-radius: var(--radius-md);
      }

      &.cdk-drag-placeholder {
        opacity: 0.4;
      }

      &.cdk-drag-animating {
        transition: transform 250ms cubic-bezier(0, 0, 0.2, 1);
      }
    }

    .drag-handle {
      cursor: grab;
      color: var(--on-surface-variant);
      font-size: 16px;
      width: 16px;
      height: 16px;
      flex-shrink: 0;

      &:active {
        cursor: grabbing;
      }
    }

    .cdk-drop-list-dragging .queue-item:not(.cdk-drag-placeholder) {
      transition: transform 250ms cubic-bezier(0, 0, 0.2, 1);
    }

    .queue-item-content {
      flex: 1;
      font-size: 12px;
      color: var(--on-surface);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .queue-edit-input {
      flex: 1;
      padding: 6px 10px;
      font-size: 14px;
      border: 1px solid var(--gemini-blue);
      border-radius: var(--radius-md);
      background: var(--surface);
      color: var(--on-surface);
      outline: none;

      &:focus {
        box-shadow: 0 0 0 2px rgba(66, 133, 244, 0.2);
      }
    }

    .queue-item-actions {
      display: flex;
      align-items: center;
      gap: 2px;
      flex-shrink: 0;

      button {
        width: 32px !important;
        height: 32px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 0 !important;

        mat-icon {
          font-size: 18px;
          width: 18px;
          height: 18px;
          color: var(--on-surface-variant);
          display: flex;
          align-items: center;
          justify-content: center;
        }

        &:hover mat-icon {
          color: var(--on-surface);
        }

        &:disabled mat-icon {
          color: var(--outline);
        }
      }
    }

    /* Input Section */
    .input-section {
      flex-shrink: 0; /* Don't shrink - stay at bottom */
      padding: 16px 24px 24px;
      width: 100%;
      max-width: 820px;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      align-items: center;
      transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
      background: var(--surface-dim);
    }

    /* Welcome header above chatbox */
    .welcome-header {
      text-align: center;
      margin-bottom: 32px;
      animation: fadeIn 0.3s ease-out;

      .welcome-logo {
        margin-bottom: 24px;

        img {
          height: 56px;
          width: auto;
          border-radius: 12px;
        }
      }

      .welcome-title {
        font-size: 52px;
        font-weight: 400;
        margin: 0 0 8px;
        color: var(--on-surface);
        display: inline-flex;
        align-items: center;

        &.rtl {
          direction: rtl;
          .typewriter-text {
            direction: rtl;
            unicode-bidi: bidi-override;
          }
        }

        &.slide-in {
          .typewriter-text {
            animation: slideInFade 0.5s ease-out;
          }
        }

        .typewriter-text {
          display: inline;
        }

        .cursor {
          opacity: 0;
          font-weight: 300;
          color: #9aa0a6;
          margin-left: 2px;

          &.visible {
            opacity: 1;
          }
        }
      }

      .welcome-subtitle {
        font-size: 20px;
        color: var(--on-surface-variant);
        margin: 0;
      }
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @keyframes slideInFade {
      from {
        opacity: 0;
        transform: translateY(15px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    @keyframes slideUpType {
      0% {
        opacity: 0;
        transform: translateY(20px);
        clip-path: inset(0 100% 0 0);
      }
      50% {
        opacity: 1;
        transform: translateY(0);
        clip-path: inset(0 50% 0 0);
      }
      100% {
        opacity: 1;
        transform: translateY(0);
        clip-path: inset(0 0 0 0);
      }
    }

    /* Centered welcome state - vertically centered */
    .chat-container.welcome-mode {
      justify-content: center;
      align-items: center;

      .messages-container {
        display: none;
      }

      .input-section {
        position: absolute;
        top: 50%;
        left: 0;
        right: 0;
        margin: 0 auto;
        transform: translateY(-50%);
        max-width: 820px;
        width: calc(100% - 48px);
      }
    }

    /* After typing starts - slide down to bottom */
    .chat-container.has-messages {
      justify-content: flex-start;

      .messages-container {
        display: block;
        flex: 1;
      }

      .input-section {
        position: absolute;
        bottom: 24px;
        top: auto;
        left: 0;
        right: 0;
        margin: 0 auto;
        transform: translateY(0);
      }
    }

    .input-box {
      display: flex;
      flex-direction: column;
      background: var(--surface);
      border: 1px solid transparent;
      border-radius: 28px;
      padding: 16px 20px;
      transition: all var(--transition-fast);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08), 0 4px 16px rgba(0, 0, 0, 0.04);
      width: 100%;
      position: relative;
      z-index: 2; /* Above queue */

      &:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12), 0 8px 24px rgba(0, 0, 0, 0.06);
      }

      &.focused {
        border-color: var(--gemini-blue);
        box-shadow: 0 4px 16px rgba(66, 133, 244, 0.15), 0 8px 32px rgba(66, 133, 244, 0.1);
      }

      &.pulse-send {
        animation: sendPulse 0.4s cubic-bezier(0.4, 0, 0.2, 1);
      }

      &.is-dragging {
        border: 2px dashed var(--gemini-blue);
        background: rgba(66, 133, 244, 0.05);
        box-shadow: 0 4px 16px rgba(66, 133, 244, 0.2), 0 8px 32px rgba(66, 133, 244, 0.15);
      }
    }

    body.dark-theme .input-box.is-dragging {
      background: rgba(138, 180, 248, 0.08);
    }

    /* Drop Zone Overlay - absolutely positioned within input-box */
    .drop-zone-overlay {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(255, 255, 255, 0.95);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 8px;
      z-index: 10;
      border-radius: 28px;
      pointer-events: none;
    }

    body.dark-theme .drop-zone-overlay {
      background: rgba(31, 31, 31, 0.95);
    }

    .drop-icon {
      font-size: 40px;
      width: 40px;
      height: 40px;
      color: var(--gemini-blue);
      animation: dropBounce 0.8s ease infinite;
    }

    @keyframes dropBounce {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-6px); }
    }

    .drop-caption {
      font-size: 14px;
      font-weight: 500;
      color: var(--gemini-blue);
    }

    @keyframes sendPulse {
      0% {
        box-shadow: 0 4px 16px rgba(66, 133, 244, 0.15), 0 8px 32px rgba(66, 133, 244, 0.1);
      }
      50% {
        box-shadow: 0 6px 24px rgba(66, 133, 244, 0.4), 0 12px 48px rgba(66, 133, 244, 0.25);
      }
      100% {
        box-shadow: 0 4px 16px rgba(66, 133, 244, 0.15), 0 8px 32px rgba(66, 133, 244, 0.1);
      }
    }

    .chat-input {
      width: 100%;
      border: none;
      background: transparent;
      font-size: 18px;
      font-family: inherit;
      color: var(--on-surface);
      outline: none;
      padding: 4px 0;
      resize: none;
      min-height: 24px;
      max-height: 200px;
      line-height: 1.5;
      padding-right: 40px; /* Space for clear button */

      &::placeholder {
        color: var(--on-surface-muted);
      }

      &:disabled {
        opacity: 0.7;
      }

      /* Squiggly red underline for flagged content */
      &.content-flagged {
        text-decoration: underline wavy var(--error);
        text-decoration-skip-ink: none;
        text-underline-offset: 3px;
        color: var(--error);

        /* Fallback for browsers that don't support wavy */
        @supports not (text-decoration-style: wavy) {
          text-decoration: underline;
          text-decoration-color: var(--error);
        }
      }
    }

    /* Tooltip styling for flagged content */
    ::ng-deep .flagged-content-tooltip {
      background: var(--error) !important;
      color: white !important;
      font-weight: 500;
    }

    /* Attached Files Container (wrapper with header and dropzone capability) */
    .attached-files-container {
      margin: -8px auto 0;
      width: 85%;
      max-width: 700px;
      background: var(--surface-container);
      border-radius: 0 0 var(--radius-md) var(--radius-md);
      border: 1px solid var(--outline-variant);
      border-top: none;
      box-shadow: inset 0 3px 8px rgba(0, 0, 0, 0.12), inset 0 1px 4px rgba(0, 0, 0, 0.15);
      position: relative;
      overflow: hidden;
      transition: border-color 0.2s, box-shadow 0.2s;

      &.is-dragging {
        border-color: var(--gemini-blue);
        box-shadow: inset 0 3px 8px rgba(0, 0, 0, 0.12), inset 0 1px 4px rgba(0, 0, 0, 0.15), 0 0 0 2px var(--gemini-blue-light);
      }
    }

    /* Attachments header toolbar */
    .attachments-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 12px 6px 16px;
      border-bottom: 1px solid rgba(0, 0, 0, 0.05);
      box-shadow: inset 0 3px 8px rgba(0, 0, 0, 0.12), inset 0 1px 4px rgba(0, 0, 0, 0.15);
      background: var(--surface-container);
    }

    .attachments-count {
      font-size: 12px;
      font-weight: 500;
      color: var(--on-surface-variant);
    }

    .attachments-actions {
      display: flex;
      align-items: center;
      gap: 2px;
    }

    .add-more-btn,
    .clear-all-btn {
      width: 28px !important;
      height: 28px !important;
      padding: 0 !important;

      .mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        color: var(--on-surface-variant);
      }

      &:hover .mat-icon {
        color: var(--on-surface);
      }
    }

    .clear-all-btn:hover .mat-icon {
      color: var(--error) !important;
    }

    /* Drop overlay for attachments container */
    .attachments-drop-overlay {
      position: absolute;
      inset: 0;
      background: rgba(var(--gemini-blue-rgb, 66, 133, 244), 0.1);
      backdrop-filter: blur(2px);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 8px;
      z-index: 10;

      mat-icon {
        font-size: 32px;
        width: 32px;
        height: 32px;
        color: var(--gemini-blue);
      }

      span {
        font-size: 13px;
        font-weight: 500;
        color: var(--gemini-blue);
      }
    }

    /* Attached Files List (scrollable file list) */
    .attached-files-list {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 8px 16px 12px 16px;
      max-height: 180px; /* Height for 3 items without scroll */
      overflow-x: hidden;
      overflow-y: auto;
      scrollbar-width: thin;

      &::-webkit-scrollbar {
        width: 4px;
      }

      &::-webkit-scrollbar-track {
        background: transparent;
      }

      &::-webkit-scrollbar-thumb {
        background: transparent;
        border-radius: 2px;
      }

      &:hover::-webkit-scrollbar-thumb {
        background: var(--outline-variant);
      }
    }

    /* File row - horizontal layout */
    .file-row {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 4px;
      border-radius: 6px;
      transition: background var(--transition-fast);

      &:not(:last-child) {
        border-bottom: 1px solid var(--outline-variant);
        padding-bottom: 8px;
        margin-bottom: 4px;
      }

      &:hover {
        background: rgba(255, 255, 255, 0.5);

        .file-remove-btn-small {
          opacity: 1;
        }
      }
    }

    /* File icon wrapper */
    .file-icon-wrapper {
      width: 28px;
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .file-thumb-small {
      width: 28px;
      height: 28px;
      object-fit: cover;
      border-radius: 4px;
    }

    .file-type-icon-small {
      font-size: 22px;
      width: 22px;
      height: 22px;
      color: var(--gemini-blue);
    }

    /* File name text */
    .file-name-text {
      flex: 1;
      font-size: 13px;
      font-weight: 500;
      color: var(--on-surface);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* File size text */
    .file-size-text {
      font-size: 11px;
      color: var(--on-surface-muted);
      flex-shrink: 0;
    }

    /* Remove button - small circular */
    .file-remove-btn-small {
      width: 24px !important;
      height: 24px !important;
      padding: 0 !important;
      opacity: 0.6;
      transition: opacity var(--transition-fast);
      flex-shrink: 0;
      display: flex !important;
      align-items: center;
      justify-content: center;

      .mat-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
        color: var(--on-surface-variant);
        display: flex;
        align-items: center;
        justify-content: center;
      }

      &:hover {
        opacity: 1;

        .mat-icon {
          color: var(--error);
        }
      }
    }

    .input-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 8px;
      padding-top: 8px;
    }

    .toolbar-left,
    .toolbar-right {
      display: flex;
      align-items: center;
      gap: 2px;
    }

    .toolbar-btn {
      color: var(--on-surface-variant);

      &:hover {
        color: var(--on-surface);
        background: var(--surface-container);
      }
    }

    .add-btn {
      background: var(--surface-container);
      border-radius: 50%;
    }

    .tools-btn {
      font-size: 14px;
      padding: 4px 12px !important;
      min-width: auto;

      mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        margin-right: 4px;
      }

      span {
        font-weight: 500;
      }
    }

    .streaming-btn {
      font-size: 14px;
      padding: 4px 12px !important;
      min-width: auto;
      transition: all var(--transition-fast);

      mat-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        margin-right: 4px;
      }

      span {
        font-weight: 500;
      }

      &.active {
        background: var(--user-bubble-bg);
        color: var(--gemini-blue);

        mat-icon {
          color: var(--gemini-blue);
        }
      }

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;

        &:hover {
          background: transparent;
        }
      }
    }

    /* Settings dropdown button */
    .settings-btn {
      width: 36px !important;
      height: 36px !important;
      padding: 0 !important;

      mat-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
      }
    }

    /* Toggle indicators in settings menu */
    ::ng-deep .settings-menu {
      .mat-mdc-menu-item {
        display: flex;
        align-items: center;
        gap: 8px;

        .toggle-indicator {
          margin-left: auto;
          font-size: 18px;
          width: 18px;
          height: 18px;
          color: var(--on-surface-muted);

          &.active {
            color: #34a853;
          }

          &.loading {
            animation: pulse 1.5s infinite;
          }
        }
      }
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }

    .model-select-btn {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 4px 8px 4px 12px !important;
      font-size: 14px;
      color: var(--on-surface);
      background: transparent;
      border-radius: 8px;
      min-width: auto;

      .model-info {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        line-height: 1.2;
        order: 0;
      }

      .model-name {
        font-weight: 500;
        font-size: 13px;
        white-space: nowrap;
      }

      .provider-name {
        font-weight: 400;
        font-size: 10px;
        color: var(--on-surface-muted);
        white-space: nowrap;
        opacity: 0.7;
      }

      .dropdown-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        color: var(--on-surface-muted);
        order: 1;
        margin-left: 2px;
      }

      &:hover {
        background: var(--surface-container);
      }
    }

    .mic-btn {
      &.recording {
        color: #ea4335 !important;
        animation: pulse 1s infinite;
      }
    }

    /* Action button container for send/mic transition */
    .action-btn-container {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      overflow: hidden;
      position: relative;
      margin-top: -4px;
    }

    .send-btn {
      color: var(--gemini-blue) !important;

      &:hover {
        background: rgba(66, 133, 244, 0.1) !important;
      }
    }

    /* Quick Action Chips */
    .quick-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: center;
      margin: 24px 0;
      padding: 0 16px;
    }

    .quick-chip {
      display: inline-flex !important;
      align-items: center;
      gap: 6px;
      border-radius: 20px !important;
      font-size: 14px;
      letter-spacing: -0.01em;
      padding: 8px 14px !important;
      background: var(--surface) !important;
      border: 1px solid var(--surface-variant) !important;
      color: var(--on-surface) !important;

      .chip-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
      }

      &:hover {
        background: var(--surface-container) !important;
        border-color: var(--on-surface-muted) !important;
      }
    }

    .disclaimer {
      margin: 16px 0 0;
      font-size: 12px;
      color: var(--on-surface-muted);
      text-align: center;
    }

    .input-wrapper {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 8px 12px;
      background: var(--surface-container);
      border: 1px solid var(--surface-variant);
      border-radius: var(--radius-full);
      transition: all var(--transition-fast);

      &:hover {
        border-color: var(--on-surface-muted);
      }

      &.focused {
        background: var(--surface);
        border-color: var(--gemini-blue);
        box-shadow: 0 0 0 3px rgba(66, 133, 244, 0.15);
      }
    }

    .input-action {
      color: var(--on-surface-variant);
      flex-shrink: 0;

      &:hover {
        color: var(--on-surface);
      }

      &.recording {
        color: #ea4335 !important;
        animation: pulse 1s infinite;
      }
    }

    .chat-input {
      flex: 1;
      min-width: 0;
      border: none;
      background: transparent;
      font-size: 18px;
      font-family: inherit;
      color: var(--on-surface);
      outline: none;
      padding: 8px;

      &::placeholder {
        color: var(--on-surface-muted);
      }

      &:disabled {
        opacity: 0.7;
      }
    }

    .model-select-container {
      flex-shrink: 0;
    }

    .model-select-trigger {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 4px 8px !important;
      min-width: 160px;
      max-width: 200px;
      background: var(--surface) !important;
      border: 1px solid var(--surface-variant);
      border-radius: var(--radius-sm) !important;
      font-size: 13px;
      height: 32px;

      .selected-model {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex: 1;
        text-align: left;
      }

      .dropdown-arrow {
        font-size: 18px;
        width: 18px;
        height: 18px;
        margin: 0 -4px 0 0;
        color: var(--on-surface-muted);
      }

      &:hover {
        background: var(--surface-container) !important;
        border-color: var(--gemini-blue);
      }
    }

    .send-btn {
      color: var(--on-surface-muted);
      flex-shrink: 0;
      transition: all var(--transition-fast);

      &.active {
        color: var(--gemini-blue);

        &:hover {
          background: var(--user-bubble-bg);
        }
      }

      &:disabled {
        opacity: 0.4;
      }
    }



    /* Animations */
    .animate-fade-in {
      animation: fadeIn 0.2s ease-out forwards;
    }

    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(8px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .clear-input-btn {
      position: absolute;
      top: 20px;
      right: 20px;
      width: 32px !important;
      height: 32px !important;
      padding: 0 !important;
      display: flex !important;
      align-items: center;
      justify-content: center;

      mat-icon {
        font-size: 22px;
        width: 22px;
        height: 22px;
        color: var(--on-surface-muted);
        display: flex;
        align-items: center;
        justify-content: center;
      }

      &:hover mat-icon {
        color: var(--on-surface);
      }
    }
  `,
  ],
})
export class ChatComponent implements OnDestroy, AfterViewInit {
  chatService = inject(ChatService);
  modelsService = inject(ModelsService);
  speechService = inject(SpeechService);
  themeService = inject(ThemeService);
  authService = inject(AuthService);
  contentSafetyService = inject(ContentSafetyService);
  preferencesService = inject(PreferencesService);
  private snackBar = inject(MatSnackBar);
  private dialog = inject(MatDialog);

  @ViewChild('messagesContainer') messagesContainer!: ElementRef;
  @ViewChild('chatTextarea') chatTextarea!: ElementRef<HTMLTextAreaElement>;

  userMessage = '';
  inputFocused = false;
  isDragging = signal(false);
  attachedFiles = signal<
    {
      name: string;
      type: string;
      size: number;
      preview: string;
      data: string;
    }[]
  >([]);

  // Debounced send button visibility to smooth animation
  showSendButton = signal(false);
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;
  private safetyDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  // Content safety - tracks flagged content for highlighting
  contentFlagged = signal(false);
  flaggedLabels = signal<string[]>([]);

  // Attachment limits from config
  maxAttachments = CHAT_CONFIG.maxAttachments;
  maxFileSizeBytes = CHAT_CONFIG.maxFileSizeBytes;

  // Queue editing state
  queueExpanded = true;
  editingQueueId: string | null = null;
  editingQueueContent = '';

  // Animation state
  isPulsing = false;

  // Greeting carousel - macOS style with RTL/LTR support (50 languages)
  greetings: {
    text: string;
    lang: string;
    dir?: 'ltr' | 'rtl';
    anim?: 'type' | 'slide';
  }[] = [
    { text: 'Hello', lang: 'English', dir: 'ltr', anim: 'type' },
    { text: 'Hola', lang: 'Spanish', dir: 'ltr', anim: 'type' },
    { text: 'Bonjour', lang: 'French', dir: 'ltr', anim: 'type' },
    { text: '你好', lang: 'Chinese', dir: 'ltr', anim: 'slide' },
    { text: 'こんにちは', lang: 'Japanese', dir: 'ltr', anim: 'slide' },
    { text: '안녕하세요', lang: 'Korean', dir: 'ltr', anim: 'slide' },
    { text: 'مرحبا', lang: 'Arabic', dir: 'rtl', anim: 'type' },
    { text: 'שלום', lang: 'Hebrew', dir: 'rtl', anim: 'type' },
    { text: 'سلام', lang: 'Persian', dir: 'rtl', anim: 'type' },
    { text: 'نمستے', lang: 'Urdu', dir: 'rtl', anim: 'type' },
    { text: 'नमस्ते', lang: 'Hindi', dir: 'ltr', anim: 'slide' },
    { text: 'Ciao', lang: 'Italian', dir: 'ltr', anim: 'type' },
    { text: 'Olá', lang: 'Portuguese', dir: 'ltr', anim: 'type' },
    { text: 'Привет', lang: 'Russian', dir: 'ltr', anim: 'type' },
    { text: 'Hallo', lang: 'German', dir: 'ltr', anim: 'type' },
    { text: 'Merhaba', lang: 'Turkish', dir: 'ltr', anim: 'type' },
    { text: 'Xin chào', lang: 'Vietnamese', dir: 'ltr', anim: 'type' },
    { text: 'สวัสดี', lang: 'Thai', dir: 'ltr', anim: 'slide' },
    { text: 'Γεια σου', lang: 'Greek', dir: 'ltr', anim: 'type' },
    { text: 'Cześć', lang: 'Polish', dir: 'ltr', anim: 'type' },
    { text: 'Hoi', lang: 'Dutch', dir: 'ltr', anim: 'type' },
    { text: 'Hej', lang: 'Swedish', dir: 'ltr', anim: 'type' },
    { text: 'Halo', lang: 'Indonesian', dir: 'ltr', anim: 'type' },
    { text: 'Habari', lang: 'Swahili', dir: 'ltr', anim: 'type' },
    { text: 'Привіт', lang: 'Ukrainian', dir: 'ltr', anim: 'type' },
    { text: 'Ahoj', lang: 'Czech', dir: 'ltr', anim: 'type' },
    { text: 'Kumusta', lang: 'Filipino', dir: 'ltr', anim: 'type' },
    { text: 'স্বাগতম', lang: 'Bengali', dir: 'ltr', anim: 'slide' },
    { text: 'வணக்கம்', lang: 'Tamil', dir: 'ltr', anim: 'slide' },
    { text: 'Selamat', lang: 'Malay', dir: 'ltr', anim: 'type' },
    { text: 'Hei', lang: 'Norwegian', dir: 'ltr', anim: 'type' },
    { text: 'Hej', lang: 'Danish', dir: 'ltr', anim: 'type' },
    { text: 'Moi', lang: 'Finnish', dir: 'ltr', anim: 'type' },
    { text: 'Szia', lang: 'Hungarian', dir: 'ltr', anim: 'type' },
    { text: 'Salut', lang: 'Romanian', dir: 'ltr', anim: 'type' },
    { text: 'Hola', lang: 'Catalan', dir: 'ltr', anim: 'type' },
    { text: 'Ahoj', lang: 'Slovak', dir: 'ltr', anim: 'type' },
    { text: 'Bok', lang: 'Croatian', dir: 'ltr', anim: 'type' },
    { text: 'Здраво', lang: 'Serbian', dir: 'ltr', anim: 'type' },
    { text: 'Živjo', lang: 'Slovenian', dir: 'ltr', anim: 'type' },
    { text: 'Sveiki', lang: 'Latvian', dir: 'ltr', anim: 'type' },
    { text: 'Labas', lang: 'Lithuanian', dir: 'ltr', anim: 'type' },
    { text: 'Tere', lang: 'Estonian', dir: 'ltr', anim: 'type' },
    { text: 'Halló', lang: 'Icelandic', dir: 'ltr', anim: 'type' },
    { text: 'Helo', lang: 'Welsh', dir: 'ltr', anim: 'type' },
    { text: 'Dia dhuit', lang: 'Irish', dir: 'ltr', anim: 'type' },
    { text: 'Halò', lang: 'Scottish Gaelic', dir: 'ltr', anim: 'type' },
    { text: 'Kia ora', lang: 'Māori', dir: 'ltr', anim: 'type' },
    { text: 'Aloha', lang: 'Hawaiian', dir: 'ltr', anim: 'type' },
    { text: 'Talofa', lang: 'Samoan', dir: 'ltr', anim: 'type' },
  ];
  currentGreetingIndex = signal(0);
  greetingFading = signal(false);
  typewriterText = signal('');
  showCursor = signal(true);
  private greetingInterval: ReturnType<typeof setInterval> | null = null;
  private typewriterTimeout: ReturnType<typeof setTimeout> | null = null;
  private cursorInterval: ReturnType<typeof setInterval> | null = null;

  // Model selector
  modelSearchQuery = '';
  filteredModels = signal(this.modelsService.getSortedModels());

  quickActions = [
    {
      labelKey: 'quickActions.createImage',
      prompt: 'Create an image of',
      icon: 'image',
      color: '#EA4335',
    },
    {
      labelKey: 'quickActions.writeAnything',
      prompt: 'Write a poem about',
      icon: 'edit_note',
      color: '#4285F4',
    },
    {
      labelKey: 'quickActions.helpMeLearn',
      prompt: 'Explain in simple terms:',
      icon: 'school',
      color: '#34A853',
    },
    {
      labelKey: 'quickActions.createVideo',
      prompt: 'Create a video about',
      icon: 'videocam',
      color: '#FBBC04',
    },
  ];

  constructor() {
    // Start greeting carousel
    this.startGreetingCarousel();

    // Track previous message count to detect when chat is cleared
    let prevMessageCount = 0;

    effect(() => {
      const messages = this.chatService.messages();

      // When messages are cleared (new chat), focus the input
      if (prevMessageCount > 0 && messages.length === 0) {
        this.focusChatInput();
      }
      prevMessageCount = messages.length;

      if (messages.length > 0 && this.messagesContainer) {
        setTimeout(() => {
          this.messagesContainer.nativeElement.scrollTop =
            this.messagesContainer.nativeElement.scrollHeight;
        }, 100);
      }
    });

    // Update filtered models when providers change
    effect(() => {
      this.modelsService.providers();
      this.filteredModels.set(this.modelsService.getSortedModels());
    });
  }

  ngOnDestroy(): void {
    if (this.greetingInterval) {
      clearInterval(this.greetingInterval);
    }
    if (this.typewriterTimeout) {
      clearTimeout(this.typewriterTimeout);
    }
    if (this.cursorInterval) {
      clearInterval(this.cursorInterval);
    }
  }

  ngAfterViewInit(): void {
    // Focus chat input when welcome screen is shown (initial load)
    this.focusChatInput();
  }

  /** Focus the chat textarea input */
  focusChatInput(): void {
    // Use setTimeout to ensure the element is ready
    setTimeout(() => {
      if (this.chatTextarea?.nativeElement) {
        this.chatTextarea.nativeElement.focus();
      }
    }, 100);
  }

  private startGreetingCarousel(): void {
    // Start cursor blinking
    this.cursorInterval = setInterval(() => {
      this.showCursor.update((v) => !v);
    }, 530);

    // Type the first greeting
    const first = this.greetings[0];
    this.typeGreeting(first.text, first.anim || 'type', first.dir || 'ltr');

    // Schedule carousel
    this.greetingInterval = setInterval(() => {
      const current = this.greetings[this.currentGreetingIndex()];

      // Erase current text
      this.eraseGreeting(() => {
        // Move to next greeting
        const nextIndex = (this.currentGreetingIndex() + 1) % this.greetings.length;
        this.currentGreetingIndex.set(nextIndex);

        const next = this.greetings[nextIndex];
        // Type new greeting
        this.typeGreeting(next.text, next.anim || 'type', next.dir || 'ltr');
      }, current.anim || 'type');
    }, 8000);
  }

  private typeGreeting(
    greetingText: string,
    anim: 'type' | 'slide' = 'type',
    dir: 'ltr' | 'rtl' = 'ltr'
  ): void {
    // Build the full text including user's name (no comma, looks cooler)
    const userName = this.authService.user()?.given_name;
    const text = userName ? `${greetingText} ${userName}` : greetingText;

    if (anim === 'slide') {
      // For slide animation, show full text immediately
      this.typewriterText.set(text);
      return;
    }

    // Typewriter animation
    let charIndex = 0;
    this.typewriterText.set('');

    const typeNext = () => {
      if (charIndex < text.length) {
        if (dir === 'rtl') {
          // For RTL, build from right side
          this.typewriterText.set(text.substring(text.length - charIndex - 1));
        } else {
          // For LTR, build from left side
          this.typewriterText.set(text.substring(0, charIndex + 1));
        }
        charIndex++;
        this.typewriterTimeout = setTimeout(typeNext, 80);
      }
    };

    typeNext();
  }

  private eraseGreeting(callback: () => void, anim: 'type' | 'slide' = 'type'): void {
    if (anim === 'slide') {
      // For slide animation, clear immediately
      this.typewriterText.set('');
      callback();
      return;
    }

    const currentText = this.typewriterText();
    let charIndex = currentText.length;

    const eraseNext = () => {
      if (charIndex > 0) {
        charIndex--;
        this.typewriterText.set(currentText.substring(0, charIndex));
        this.typewriterTimeout = setTimeout(eraseNext, 40);
      } else {
        callback();
      }
    };

    eraseNext();
  }

  onModelMenuOpened(): void {
    this.modelSearchQuery = '';
    this.filteredModels.set(this.modelsService.getSortedModels());
  }

  filterModels(): void {
    this.filteredModels.set(this.modelsService.filterModels(this.modelSearchQuery));
  }

  clearModelSearch(): void {
    this.modelSearchQuery = '';
    this.filteredModels.set(this.modelsService.getSortedModels());
  }

  selectModel(modelId: string): void {
    this.modelsService.selectModel(modelId);
  }

  getShortModelName(): string {
    const name = this.modelsService.getModelName(this.modelsService.selectedModel());
    // Extract just the model variant (e.g., "Flash" from "Gemini 2.0 Flash")
    const parts = name.split(' ');
    return parts[parts.length - 1] || name;
  }

  onEnterKey(event: Event): void {
    const keyEvent = event as KeyboardEvent;
    if (!keyEvent.shiftKey) {
      keyEvent.preventDefault();

      // Trigger pulse animation
      this.isPulsing = true;
      setTimeout(() => {
        this.isPulsing = false;
      }, 400);

      this.sendMessage();
      // Ensure focus stays on input after Angular's change detection
      setTimeout(() => this.chatTextarea?.nativeElement?.focus(), 0);
    }
  }

  focusInput(event: MouseEvent): void {
    // Focus the textarea when clicking anywhere in the input box
    // Ignore clicks on buttons, menus, and other interactive elements
    const target = event.target as HTMLElement;
    const isInteractive = target.closest('button, mat-icon, .mat-mdc-menu-trigger, input, select');
    if (!isInteractive) {
      this.chatTextarea?.nativeElement?.focus();
    }
  }

  useQuickAction(prompt: string): void {
    this.userMessage = `${prompt} `;
    // Focus the textarea and move cursor to end after Angular updates the DOM
    setTimeout(() => {
      const textarea = this.chatTextarea?.nativeElement;
      if (textarea) {
        textarea.focus();
        // Move cursor to end of text
        const length = textarea.value.length;
        textarea.setSelectionRange(length, length);
      }
    }, 0);
  }

  /**
   * Clear content flagging when user edits their message.
   * Also debounce the send button visibility for smooth animation.
   * Real-time content safety is debounced (500ms) to avoid excessive API calls.
   */
  onInputChange(): void {
    // Clear content flagging when user edits
    if (this.contentFlagged()) {
      this.contentFlagged.set(false);
      this.flaggedLabels.set([]);
    }

    // Debounce send button visibility (150ms)
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    const hasText = !!this.userMessage.trim();

    // If switching to send button, show immediately
    // If switching to mic button, debounce to avoid flicker
    if (hasText && !this.showSendButton()) {
      this.showSendButton.set(true);
    } else if (!hasText && this.showSendButton()) {
      this.debounceTimer = setTimeout(() => {
        if (!this.userMessage.trim()) {
          this.showSendButton.set(false);
        }
      }, 150);
    }

    // Debounced real-time content safety check (500ms after user stops typing)
    if (this.safetyDebounceTimer) {
      clearTimeout(this.safetyDebounceTimer);
    }

    if (hasText && this.contentSafetyService.enabled()) {
      this.safetyDebounceTimer = setTimeout(async () => {
        const message = this.userMessage.trim();
        if (message) {
          const safetyResult = await this.contentSafetyService.checkContent(message);
          // Only flag if user hasn't cleared the input
          if (this.userMessage.trim() === message && !safetyResult.safe) {
            this.contentFlagged.set(true);
            this.flaggedLabels.set(safetyResult.labels);
          }
        }
      }, 500);
    }
  }

  async sendMessage(): Promise<void> {
    if (!this.userMessage.trim()) return;

    const message = this.userMessage;
    this.userMessage = '';

    // TODO(#file-attachments): Include attachedFiles in the message payload.
    // The UI allows attaching files (stored in this.attachedFiles signal), but they
    // are not currently sent to the backend. To complete this feature:
    // 1. Update chatService.sendMessage() and sendStreamMessage() to accept attachments
    // 2. Update the backend API to handle multimodal input (text + images)
    // 3. Clear attachedFiles after successful send
    // 4. Handle attachment display in the chat history
    // See: https://github.com/firebase/genkit/issues/XXXX

    // Reset send button state (will animate to mic)
    this.showSendButton.set(false);

    // Always keep focus on the input
    this.chatTextarea?.nativeElement?.focus();

    // Check content safety if enabled
    if (this.contentSafetyService.enabled()) {
      const safetyResult = await this.contentSafetyService.checkContent(message);
      if (!safetyResult.safe) {
        // Mark content as flagged for visual highlighting
        this.contentFlagged.set(true);
        this.flaggedLabels.set(safetyResult.labels);

        this.snackBar.open(
          `Message blocked: ${safetyResult.message || 'Potentially harmful content detected'}`,
          'Dismiss',
          { duration: 5000, panelClass: 'warning-snackbar' }
        );
        // Restore the message so user can edit it
        this.userMessage = message;
        return;
      }
      // Clear any previous flagging
      this.contentFlagged.set(false);
      this.flaggedLabels.set([]);
    }

    // If model is busy, queue the prompt
    if (this.chatService.isLoading()) {
      this.chatService.addToQueue(message, this.modelsService.selectedModel());
      return;
    }

    // Use streaming if enabled
    if (this.chatService.streamingMode() && this.modelsService.supportsStreaming()) {
      this.chatService.sendStreamMessage(message, this.modelsService.selectedModel(), () => {
        this.chatTextarea?.nativeElement?.focus();
      });
      return;
    }

    this.chatService.sendMessage(message, this.modelsService.selectedModel()).subscribe({
      next: (response) => {
        this.chatService.addAssistantMessage(response);
      },
      error: (_err) => {
        this.snackBar.open('Failed to send message. Please try again.', 'Dismiss', {
          duration: 5000,
          panelClass: 'error-snackbar',
        });
      },
    });
  }

  clearInput(): void {
    this.userMessage = '';
    this.onInputChange();
    this.chatTextarea?.nativeElement?.focus();
  }

  sendQuickAction(prompt: string): void {
    this.userMessage = prompt;
  }

  // Queue editing methods
  startEditQueue(item: { id: string; content: string }): void {
    this.editingQueueId = item.id;
    this.editingQueueContent = item.content;
  }

  saveQueueEdit(id: string): void {
    if (this.editingQueueContent.trim()) {
      this.chatService.updateQueuedPrompt(id, this.editingQueueContent);
    }
    this.cancelQueueEdit();
  }

  cancelQueueEdit(): void {
    this.editingQueueId = null;
    this.editingQueueContent = '';
  }

  onQueueDrop(event: CdkDragDrop<unknown[]>): void {
    const queue = [...this.chatService.promptQueue()];
    moveItemInArray(queue, event.previousIndex, event.currentIndex);
    this.chatService.promptQueue.set(queue);
  }
  openGoogleDrive(): void {
    // TODO: Implement Google Drive picker integration
    this.snackBar.open('Google Drive integration coming soon!', 'Dismiss', {
      duration: 3000,
    });
  }

  async toggleVoiceInput(): Promise<void> {
    if (this.speechService.isListening()) {
      this.speechService.stopListening();
    } else {
      try {
        const transcript = await this.speechService.startListening();
        if (transcript) {
          this.userMessage = transcript;
        }
      } catch (_error) {
        this.snackBar.open('Voice input not available', 'Dismiss', {
          duration: 3000,
        });
      }
    }
  }

  speakMessage(text: string): void {
    if (this.speechService.isSpeaking()) {
      this.speechService.stopSpeaking();
    } else {
      this.speechService.speak(text);
    }
  }

  copyMessage(text: string): void {
    navigator.clipboard.writeText(text).then(() => {
      this.snackBar.open('Copied to clipboard', '', { duration: 2000 });
    });
  }

  showErrorDetails(details: string): void {
    this.dialog.open(ErrorDetailsDialogComponent, {
      data: { errorDetails: details },
      width: '600px',
      maxHeight: '80vh',
    });
  }

  toggleStreaming(): void {
    if (this.modelsService.supportsStreaming()) {
      this.chatService.toggleStreamingMode();
    }
  }

  getStreamingTooltip(): string {
    if (!this.modelsService.supportsStreaming()) {
      return 'Streaming not supported for this model';
    }
    return this.chatService.streamingMode()
      ? 'Streaming ON - click to disable'
      : 'Streaming OFF - click to enable';
  }

  getSafetyTooltip(): string {
    if (this.contentSafetyService.loading()) {
      return 'Loading toxicity detection model...';
    }
    if (this.contentSafetyService.enabled()) {
      return this.contentSafetyService.modelReady()
        ? 'Content Safety ON - toxic content will be blocked'
        : 'Content Safety ON - model loading on first use';
    }
    return 'Content Safety OFF - no client-side filtering';
  }

  clearPreferences(): void {
    this.preferencesService.clearAll();
    this.snackBar
      .open('Preferences cleared. Refresh to apply defaults.', 'Refresh', {
        duration: 5000,
      })
      .onAction()
      .subscribe(() => {
        window.location.reload();
      });
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging.set(false);

    const files = event.dataTransfer?.files;
    if (files) {
      this.processFiles(Array.from(files));
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files) {
      this.processFiles(Array.from(input.files));
    }
    input.value = ''; // Reset for same file selection
  }

  private processFiles(files: File[]): void {
    const currentCount = this.attachedFiles().length;
    const remaining = this.maxAttachments - currentCount;

    if (remaining <= 0) {
      this.snackBar.open(`Maximum ${this.maxAttachments} attachments allowed`, 'Dismiss', {
        duration: 4000,
      });
      return;
    }

    // Only process up to the remaining slots
    const filesToProcess = files.slice(0, remaining);

    if (files.length > remaining) {
      this.snackBar.open(`Only ${remaining} more file(s) can be attached`, 'Dismiss', {
        duration: 4000,
      });
    }

    filesToProcess.forEach((file) => {
      if (file.size > this.maxFileSizeBytes) {
        const maxSizeMB = (this.maxFileSizeBytes / (1024 * 1024)).toFixed(0);
        this.snackBar.open(`File "${file.name}" is too large (max ${maxSizeMB}MB)`, 'Dismiss', {
          duration: 4000,
        });
        return;
      }

      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = reader.result as string;
        this.attachedFiles.update((current) => [
          ...current,
          {
            name: file.name,
            type: file.type || 'application/octet-stream',
            size: file.size,
            preview: dataUrl,
            data: dataUrl,
          },
        ]);
      };
      reader.readAsDataURL(file);
    });
  }

  removeFile(file: { name: string }): void {
    this.attachedFiles.update((current) => current.filter((f) => f.name !== file.name));
  }

  /**
   * Clear all attached files.
   */
  clearAllFiles(): void {
    this.attachedFiles.set([]);
  }

  /**
   * Get Material Icon name for a MIME type.
   */
  getFileIcon(mimeType: string): string {
    return getMimeTypeIcon(mimeType);
  }

  /**
   * Format file size to human-readable string.
   */
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';

    const units = ['B', 'KB', 'MB', 'GB'];
    const base = 1024;
    const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(base)), units.length - 1);
    const value = bytes / base ** exponent;

    // Show 1 decimal place for KB and above, none for bytes
    return exponent === 0
      ? `${value} ${units[exponent]}`
      : `${value.toFixed(1)} ${units[exponent]}`;
  }
}
