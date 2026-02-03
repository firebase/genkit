import { Component, inject, signal, effect, ElementRef, ViewChild, OnDestroy, AfterViewInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatMenuModule } from '@angular/material/menu';
import { MatRippleModule } from '@angular/material/core';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDividerModule } from '@angular/material/divider';
import { ChatService, Message } from '../../core/services/chat.service';
import { ModelsService } from '../../core/services/models.service';
import { SpeechService } from '../../core/services/speech.service';
import { ThemeService } from '../../core/services/theme.service';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-chat',
  imports: [
    CommonModule,
    FormsModule,
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
  ],
  template: `
    <div class="chat-container" 
         [class.welcome-mode]="chatService.messages().length === 0"
         [class.has-messages]="chatService.messages().length > 0"
         (dragover)="onDragOver($event)" 
         (dragleave)="onDragLeave($event)"
         (drop)="onDrop($event)">
      
      <!-- Drop Zone Overlay -->
      @if (isDragging()) {
        <div class="drop-zone-overlay">
          <div class="drop-zone-content">
            <mat-icon class="drop-icon">upload_file</mat-icon>
            <p class="drop-title">Drop files here</p>
            <span class="drop-hint">Images, PDFs, or text files</span>
          </div>
        </div>
      }

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
              <div class="message-text">{{ message.content }}</div>
              
              @if (message.isError && message.errorDetails) {
                <button mat-stroked-button class="error-details-btn" (click)="showErrorDetails(message.errorDetails)">
                  <mat-icon>info_outline</mat-icon>
                  View Details
                </button>
              }
              
              @if (message.role === 'assistant') {
                <div class="message-actions">
                  <button mat-icon-button matTooltip="Copy to clipboard" (click)="copyMessage(message.content)">
                    <mat-icon>content_copy</mat-icon>
                  </button>
                  <button mat-icon-button matTooltip="Read aloud" (click)="speakMessage(message.content)">
                    <mat-icon>{{ speechService.isSpeaking() ? 'stop' : 'volume_up' }}</mat-icon>
                  </button>
                  <button mat-icon-button matTooltip="Good response">
                    <mat-icon>thumb_up</mat-icon>
                  </button>
                  <button mat-icon-button matTooltip="Bad response">
                    <mat-icon>thumb_down</mat-icon>
                  </button>
                  <button mat-icon-button [matMenuTriggerFor]="moreMenu" matTooltip="More">
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

      <!-- Attached Files Preview -->
      @if (attachedFiles().length > 0) {
        <div class="attached-files">
          @for (file of attachedFiles(); track file.name) {
            <div class="file-chip">
              @if (file.type.startsWith('image/')) {
                <img [src]="file.preview" alt="preview" class="file-thumb">
              } @else {
                <mat-icon class="file-icon">description</mat-icon>
              }
              <span class="file-name">{{ file.name }}</span>
              <button mat-icon-button class="file-remove" (click)="removeFile(file)" matTooltip="Remove">
                <mat-icon>close</mat-icon>
              </button>
            </div>
          }
        </div>
      }

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
            <p class="welcome-subtitle">How can I help you today?</p>
          </div>
        }
        
        <div class="input-box" [class.focused]="inputFocused">
          <!-- Text Area at top -->
          <textarea class="chat-input" 
                    [(ngModel)]="userMessage" 
                    placeholder="Ask Genkit Chat"
                    (keydown.enter)="onEnterKey($event)"
                    (focus)="inputFocused = true"
                    (blur)="inputFocused = false"
                    [disabled]="chatService.isLoading()"
                    rows="1"
                    #chatTextarea></textarea>
          
          <!-- Bottom Toolbar -->
          <div class="input-toolbar">
            <div class="toolbar-left">
              <!-- Add/Attach Button -->
              <button mat-icon-button 
                      class="toolbar-btn add-btn"
                      matTooltip="Add files"
                      [matMenuTriggerFor]="attachMenu">
                <mat-icon>add</mat-icon>
              </button>
              
              <mat-menu #attachMenu="matMenu" class="attach-menu">
                <button mat-menu-item (click)="anyInput.click()">
                  <mat-icon>upload_file</mat-icon>
                  <span>Upload files</span>
                </button>
                <button mat-menu-item (click)="openGoogleDrive()" 
                        [disabled]="authService.demoMode()"
                        [matTooltip]="authService.demoMode() ? 'Not available in demo mode' : ''">
                  <mat-icon>add_to_drive</mat-icon>
                  <span>Add from Drive</span>
                </button>
                <button mat-menu-item (click)="imageInput.click()">
                  <mat-icon>image</mat-icon>
                  <span>Photos</span>
                </button>
                <mat-divider></mat-divider>
                <button mat-menu-item (click)="audioInput.click()">
                  <mat-icon>audio_file</mat-icon>
                  <span>Audio</span>
                </button>
                <button mat-menu-item (click)="videoInput.click()">
                  <mat-icon>videocam</mat-icon>
                  <span>Video</span>
                </button>
                <button mat-menu-item (click)="pdfInput.click()">
                  <mat-icon>picture_as_pdf</mat-icon>
                  <span>PDF</span>
                </button>
                <button mat-menu-item (click)="textInput.click()">
                  <mat-icon>code</mat-icon>
                  <span>Import code</span>
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
                <mat-icon>tune</mat-icon>
                <span>Tools</span>
              </button>
              
              <!-- Streaming Toggle -->
              <button mat-button 
                      class="toolbar-btn streaming-btn"
                      [class.active]="chatService.streamingMode()"
                      (click)="chatService.toggleStreamingMode()"
                      [matTooltip]="chatService.streamingMode() ? 'Streaming ON - click to disable' : 'Streaming OFF - click to enable'">
                <mat-icon>{{ chatService.streamingMode() ? 'stream' : 'pause_circle' }}</mat-icon>
                <span>Stream</span>
              </button>
            </div>
            
            <div class="toolbar-right">
              <!-- Model Selector -->
              <button mat-button 
                      class="model-select-btn"
                      [matMenuTriggerFor]="modelMenu"
                      (menuOpened)="onModelMenuOpened()">
                <span class="model-label">{{ modelsService.getModelName(modelsService.selectedModel()) }}</span>
                <span class="separator">·</span>
                <span class="provider-label">{{ modelsService.getProviderName(modelsService.selectedModel()) }}</span>
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
              
              <!-- Voice Input -->
              @if (speechService.isSupported()) {
                <button mat-icon-button 
                        class="toolbar-btn mic-btn"
                        [class.recording]="speechService.isListening()"
                        matTooltip="{{ speechService.isListening() ? 'Stop' : 'Voice input' }}"
                        (click)="toggleVoiceInput()">
                  <mat-icon>{{ speechService.isListening() ? 'mic_off' : 'mic' }}</mat-icon>
                </button>
              }
            </div>
          </div>
        </div>
        
        <!-- Quick Actions (below chatbox) -->
        @if (chatService.messages().length === 0) {
          <div class="quick-chips">
            @for (action of quickActions; track action.label) {
              <button mat-stroked-button 
                      class="quick-chip"
                      (click)="useQuickAction(action.prompt)">
                {{ action.label }}
              </button>
            }
          </div>
        }
        
        <p class="disclaimer">
          Genkit Chat may display inaccurate info. Double-check its responses.
        </p>
      </div>
    </div>
  `,
  styles: [`
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

    /* Drop Zone */
    .drop-zone-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(255, 255, 255, 0.98);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      backdrop-filter: blur(4px);
    }

    body.dark-theme .drop-zone-overlay {
      background: rgba(31, 31, 31, 0.98);
    }

    .drop-zone-content {
      text-align: center;
    }

    .drop-icon {
      font-size: 56px;
      width: 56px;
      height: 56px;
      color: var(--gemini-blue);
      margin-bottom: 16px;
    }

    .drop-title {
      font-size: 20px;
      font-weight: 500;
      margin: 0 0 4px;
      color: var(--on-surface);
    }

    .drop-hint {
      font-size: 14px;
      color: var(--on-surface-variant);
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
          filter: invert(1);
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
      padding-bottom: 16px; /* Space before input section */
    }

    .message-row {
      display: flex;
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
    }

    .avatar-logo {
      width: 28px;
      height: auto;
      
      &.dark {
        filter: invert(1);
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
      
      &:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12), 0 8px 24px rgba(0, 0, 0, 0.06);
      }
      
      &.focused {
        border-color: var(--gemini-blue);
        box-shadow: 0 4px 16px rgba(66, 133, 244, 0.15), 0 8px 32px rgba(66, 133, 244, 0.1);
      }
    }
    
    .chat-input {
      width: 100%;
      border: none;
      background: transparent;
      font-size: 16px;
      font-family: inherit;
      color: var(--on-surface);
      outline: none;
      padding: 4px 0;
      resize: none;
      min-height: 24px;
      max-height: 200px;
      line-height: 1.5;
      
      &::placeholder {
        color: var(--on-surface-muted);
      }
      
      &:disabled {
        opacity: 0.7;
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
      gap: 4px;
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
    }
    
    .model-select-btn {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 6px 12px !important;
      font-size: 14px;
      color: var(--on-surface);
      background: transparent;
      border-radius: 8px;
      
      .model-label {
        font-weight: 500;
        white-space: nowrap;
      }
      
      .separator {
        color: #c4c9ce;
        font-weight: 400;
        margin: 0 4px;
      }
      
      .provider-label {
        font-weight: 400;
        color: var(--on-surface-muted);
        white-space: nowrap;
      }
      
      .dropdown-icon {
        font-size: 20px;
        width: 20px;
        height: 20px;
        margin-left: 2px;
        color: var(--on-surface-muted);
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
    
    /* Quick Action Chips */
    .quick-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: center;
      margin-top: 16px;
      padding: 0 16px;
    }
    
    .quick-chip {
      border-radius: 20px !important;
      font-size: 14px;
      padding: 8px 16px !important;
      background: var(--surface) !important;
      border: 1px solid var(--surface-variant) !important;
      color: var(--on-surface) !important;
      
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
      font-size: 15px;
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

    .disclaimer {
      text-align: center;
      font-size: 12px;
      color: var(--on-surface-muted);
      margin: 12px 0 0;
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
  `],
})
export class ChatComponent implements OnDestroy, AfterViewInit {
  chatService = inject(ChatService);
  modelsService = inject(ModelsService);
  speechService = inject(SpeechService);
  themeService = inject(ThemeService);
  authService = inject(AuthService);
  private snackBar = inject(MatSnackBar);

  @ViewChild('messagesContainer') messagesContainer!: ElementRef;
  @ViewChild('chatTextarea') chatTextarea!: ElementRef<HTMLTextAreaElement>;

  userMessage = '';
  inputFocused = false;
  isDragging = signal(false);
  attachedFiles = signal<{ name: string; type: string; preview: string; data: string }[]>([]);

  // Greeting carousel - macOS style with RTL/LTR support (50 languages)
  greetings: { text: string; lang: string; dir?: 'ltr' | 'rtl'; anim?: 'type' | 'slide' }[] = [
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
    { label: 'Create image', prompt: 'Create an image of' },
    { label: 'Write anything', prompt: 'Help me write' },
    { label: 'Help me learn', prompt: 'Explain in simple terms:' },
    { label: 'Create video', prompt: 'Create a video about' },
    { label: 'Stay organized', prompt: 'Help me organize' },
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
      this.showCursor.update(v => !v);
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

  private typeGreeting(greetingText: string, anim: 'type' | 'slide' = 'type', dir: 'ltr' | 'rtl' = 'ltr'): void {
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
      this.sendMessage();
    }
  }

  useQuickAction(prompt: string): void {
    this.userMessage = prompt + ' ';
  }

  sendMessage(): void {
    if (!this.userMessage.trim()) return;

    const message = this.userMessage;
    this.userMessage = '';

    // Keep focus on the input after sending
    setTimeout(() => {
      this.chatTextarea?.nativeElement?.focus();
    }, 0);

    // Use streaming if enabled
    if (this.chatService.streamingMode()) {
      this.chatService.sendStreamMessage(message, this.modelsService.selectedModel());
      return;
    }

    this.chatService.sendMessage(message, this.modelsService.selectedModel())
      .subscribe({
        next: response => {
          this.chatService.addAssistantMessage(response);
          // Refocus after response
          setTimeout(() => {
            this.chatTextarea?.nativeElement?.focus();
          }, 0);
        },
        error: err => {
          this.snackBar.open('Failed to send message. Please try again.', 'Dismiss', {
            duration: 5000,
            panelClass: 'error-snackbar',
          });
          console.error('Chat error:', err);
          // Refocus on error too
          setTimeout(() => {
            this.chatTextarea?.nativeElement?.focus();
          }, 0);
        }
      });
  }

  sendQuickAction(prompt: string): void {
    this.userMessage = prompt;
  }

  openGoogleDrive(): void {
    // TODO: Implement Google Drive picker integration
    this.snackBar.open('Google Drive integration coming soon!', 'Dismiss', { duration: 3000 });
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
      } catch (error) {
        this.snackBar.open('Voice input not available', 'Dismiss', { duration: 3000 });
        console.error('Voice input error:', error);
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
    // Format the error details for display
    let formattedDetails = details;
    try {
      const parsed = JSON.parse(details);
      formattedDetails = JSON.stringify(parsed, null, 2);
    } catch {
      // Keep original if not JSON
    }

    // Open a dialog or snackbar with the error details
    this.snackBar.open('Error details copied to clipboard. Check console for full details.', 'Dismiss', {
      duration: 5000
    });
    navigator.clipboard.writeText(formattedDetails);
    console.error('Error Details:', formattedDetails);
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
    const maxSize = 10 * 1024 * 1024; // 10MB

    files.forEach(file => {
      if (file.size > maxSize) {
        this.snackBar.open(`File "${file.name}" is too large (max 10MB)`, 'Dismiss', { duration: 4000 });
        return;
      }

      const reader = new FileReader();
      reader.onload = () => {
        const dataUrl = reader.result as string;
        this.attachedFiles.update(current => [
          ...current,
          {
            name: file.name,
            type: file.type,
            preview: dataUrl,
            data: dataUrl,
          },
        ]);
      };
      reader.readAsDataURL(file);
    });
  }

  removeFile(file: { name: string }): void {
    this.attachedFiles.update(current =>
      current.filter(f => f.name !== file.name)
    );
  }
}
