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
import { CommonModule } from '@angular/common';
/**
 * ChatInputComponent - Text area, attachments, voice input, send button.
 *
 * This component is responsible for:
 * - Message text input with auto-resizing
 * - File attachments with drag-and-drop
 * - Voice input via Web Speech API
 * - Content safety highlighting
 * - Send button with animation
 * - Settings dropdown (streaming, markdown, safety)
 *
 * Component Architecture::
 *
 *     ┌─────────────────────────────────────────────────────────────┐
 *     │                    ChatInputComponent                       │
 *     ├─────────────────────────────────────────────────────────────┤
 *     │  Inputs:                                                    │
 *     │  - placeholder: string                                      │
 *     │  - disabled: boolean                                        │
 *     │  - contentFlagged: boolean                                  │
 *     │  - flaggedLabels: string[]                                  │
 *     │  - streamingEnabled: boolean                                │
 *     │  - markdownEnabled: boolean                                 │
 *     │  - safetyEnabled: boolean                                   │
 *     │  - isRecording: boolean                                     │
 *     │  - voiceSupported: boolean                                  │
 *     │                                                             │
 *     │  Outputs:                                                   │
 *     │  - send: EventEmitter<{message, attachments}>               │
 *     │  - inputChange: EventEmitter<string>                        │
 *     │  - toggleVoice: EventEmitter<void>                          │
 *     │  - toggleStreaming: EventEmitter<void>                      │
 *     │  - toggleMarkdown: EventEmitter<void>                       │
 *     │  - toggleSafety: EventEmitter<void>                         │
 *     │  - clearPreferences: EventEmitter<void>                     │
 *     │  - filesSelected: EventEmitter<File[]>                      │
 *     │                                                             │
 *     │  Layout::                                                   │
 *     │  ┌───────────────────────────────────────────────────────┐  │
 *     │  │ Textarea (auto-resize)                                │  │
 *     │  ├───────────────────────────────────────────────────────┤  │
 *     │  │ [+] [Tools] ─────────────── [Model] [⚙] [🎤/Send]    │  │
 *     │  └───────────────────────────────────────────────────────┘  │
 *     │  [Attached Files List]                                      │
 *     └─────────────────────────────────────────────────────────────┘
 */
import {
	type AfterViewInit,
	Component,
	computed,
	type ElementRef,
	effect,
	inject,
	input,
	output,
	signal,
	ViewChild,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

/** Default configuration - can be overridden via inputs */
const DEFAULT_CONFIG = {
	maxAttachments: 10,
	maxFileSizeBytes: 1 * 1024 * 1024, // 1MB
};

/**
 * Get Material Icon name for a given MIME type.
 * Inlined for component portability.
 */
function getMimeTypeIcon(mimeType: string): string {
	if (mimeType.startsWith('image/')) return 'image';
	if (mimeType.startsWith('video/')) return 'videocam';
	if (mimeType.startsWith('audio/')) return 'audio_file';
	if (mimeType === 'application/pdf') return 'picture_as_pdf';
	if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return 'table_chart';
	if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) return 'slideshow';
	if (mimeType.includes('document') || mimeType.includes('word')) return 'description';
	if (mimeType.startsWith('text/')) return 'article';
	if (mimeType.includes('zip') || mimeType.includes('compressed')) return 'folder_zip';
	if (mimeType.includes('json')) return 'data_object';
	return 'insert_drive_file';
}

export interface AttachedFile {
	name: string;
	size: number;
	type: string;
	preview?: string;
	data?: string;
}

export interface SendEvent {
	message: string;
	attachments: AttachedFile[];
}

@Component({
	selector: 'genkit-chat-input',
	standalone: true,
	imports: [
		CommonModule,
		FormsModule,
		MatButtonModule,
		MatIconModule,
		MatMenuModule,
		MatTooltipModule,
		MatDividerModule,
		MatSnackBarModule,
		TranslateModule,
	],
	animations: [
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
    <div class="input-box" 
         [class.focused]="inputFocused()" 
         [class.is-dragging]="isDragging()"
         (click)="focusInput($event)"
         (dragover)="onDragOver($event)" 
         (dragleave)="onDragLeave($event)"
         (drop)="onDrop($event)">
      
      <!-- Drop Zone Overlay -->
      @if (isDragging()) {
        <div class="drop-zone-overlay">
          <mat-icon class="drop-icon">cloud_upload</mat-icon>
          <span class="drop-caption">Drop files to attach</span>
        </div>
      }
      
      <textarea class="chat-input" 
                [class.content-flagged]="contentFlagged()"
                [(ngModel)]="message" 
                [placeholder]="placeholder()"
                [attr.aria-label]="placeholder()"
                (keydown.enter)="onEnterKey($event)"
                (focus)="inputFocused.set(true)"
                (blur)="inputFocused.set(false)"
                (input)="onInputChange()"
                [matTooltip]="contentFlagged() ? 'Content flagged: ' + flaggedLabels().join(', ') : ''"
                rows="1"
                #chatTextarea></textarea>

      @if (message) {
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
          <ng-content select="[modelSelector]"></ng-content>
          
          <!-- Settings Dropdown -->
          <button mat-icon-button 
                  class="toolbar-btn settings-btn"
                  [matMenuTriggerFor]="settingsMenu"
                  [attr.aria-label]="'toolbar.settings' | translate"
                  [matTooltip]="'toolbar.settings' | translate">
            <mat-icon>tune</mat-icon>
          </button>
          <mat-menu #settingsMenu="matMenu" class="settings-menu">
            <!-- Streaming Toggle -->
            <button mat-menu-item (click)="toggleStreaming.emit(); $event.stopPropagation()">
              <mat-icon>{{ streamingEnabled() ? 'stream' : 'pause_circle' }}</mat-icon>
              <span>{{ 'toolbar.stream' | translate }}</span>
              <mat-icon class="toggle-indicator" [class.active]="streamingEnabled()">
                {{ streamingEnabled() ? 'check_circle' : 'radio_button_unchecked' }}
              </mat-icon>
            </button>
            
            <!-- Markdown Toggle -->
            <button mat-menu-item (click)="toggleMarkdown.emit(); $event.stopPropagation()">
              <mat-icon>{{ markdownEnabled() ? 'code' : 'code_off' }}</mat-icon>
              <span>{{ 'toolbar.markdown' | translate }}</span>
              <mat-icon class="toggle-indicator" [class.active]="markdownEnabled()">
                {{ markdownEnabled() ? 'check_circle' : 'radio_button_unchecked' }}
              </mat-icon>
            </button>
            
            <!-- Content Safety Toggle -->
            <button mat-menu-item (click)="toggleSafety.emit(); $event.stopPropagation()">
              <mat-icon>{{ safetyEnabled() ? 'shield' : 'shield_outlined' }}</mat-icon>
              <span>{{ 'toolbar.safe' | translate }}</span>
              <mat-icon class="toggle-indicator" [class.active]="safetyEnabled()">
                {{ safetyEnabled() ? 'check_circle' : 'radio_button_unchecked' }}
              </mat-icon>
            </button>
            
            <mat-divider></mat-divider>
            
            <!-- Clear Preferences -->
            <button mat-menu-item (click)="clearPreferences.emit()">
              <mat-icon>delete_outline</mat-icon>
              <span>{{ 'settings.clearPreferences' | translate }}</span>
            </button>
          </mat-menu>
          
          <!-- Send Button or Voice Input -->
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
            } @else if (voiceSupported()) {
              <button mat-icon-button 
                      class="toolbar-btn mic-btn"
                      @slideButton
                      [class.recording]="isRecording()"
                      [attr.aria-label]="isRecording() ? ('chat.stopRecording' | translate) : ('chat.voiceInput' | translate)"
                      [matTooltip]="isRecording() ? ('chat.stopRecording' | translate) : ('chat.voiceInput' | translate)"
                      (click)="toggleVoice.emit()">
                <mat-icon>{{ isRecording() ? 'mic_off' : 'mic' }}</mat-icon>
              </button>
            }
          </div>
        </div>
      </div>
    </div>
    
    <!-- Attached Files List -->
    @if (attachedFiles().length > 0) {
      <div class="attached-files-container" [class.is-dragging]="isDragging()">
        <div class="attachments-header">
          <span class="attachments-count">{{ attachedFiles().length }} file{{ attachedFiles().length > 1 ? 's' : '' }} attached</span>
          <div class="attachments-actions">
            <button mat-icon-button class="add-more-btn" (click)="anyInput.click()" [attr.aria-label]="'chat.addMoreFiles' | translate" [matTooltip]="'chat.addMoreFiles' | translate">
              <mat-icon>add</mat-icon>
            </button>
            <button mat-icon-button class="clear-all-btn" (click)="clearAllFiles()" [attr.aria-label]="'actions.clearAll' | translate" [matTooltip]="'actions.clearAll' | translate">
              <mat-icon>delete_sweep</mat-icon>
            </button>
          </div>
        </div>
        
        <div class="attached-files-list">
          @for (file of attachedFiles(); track file.name) {
            <div class="file-row">
              <div class="file-icon-wrapper">
                @if (file.type.startsWith('image/')) {
                  <img [src]="file.preview" alt="preview" class="file-thumb-small">
                } @else {
                  <mat-icon class="file-type-icon-small">{{ getFileIcon(file.type) }}</mat-icon>
                }
              </div>
              <span class="file-name-text" [matTooltip]="file.name">{{ file.name }}</span>
              <span class="file-size-text">{{ formatFileSize(file.size) }}</span>
              <button mat-icon-button class="file-remove-btn-small" (click)="removeFile(file)" [attr.aria-label]="('actions.remove' | translate) + ' ' + file.name" [matTooltip]="'actions.remove' | translate">
                <mat-icon>close</mat-icon>
              </button>
            </div>
          }
        </div>
      </div>
    }
  `,
	styles: [
		`
    /* CSS Variable Defaults - ensures component works without global theme */
    :host {
      display: block;
      --_primary: var(--primary, #4285f4);
      --_on-primary: var(--on-primary, #ffffff);
      --_primary-container: var(--primary-container, #d3e3fd);
      --_on-primary-container: var(--on-primary-container, #041e49);
      --_surface-container: var(--surface-container, #f0f4f9);
      --_surface-container-high: var(--surface-container-high, #e5eaf0);
      --_on-surface: var(--on-surface, #1a1c1e);
      --_on-surface-variant: var(--on-surface-variant, #5f6368);
      --_outline-variant: var(--outline-variant, #c4c6d0);
      --_error: var(--error, #ba1a1a);
    }

    .input-box {
      position: relative;
      background: var(--_surface-container);
      border: 1px solid var(--_outline-variant);
      border-radius: 24px;
      padding: 12px 16px;
      transition: all 0.2s ease;
      
      &.focused {
        border-color: var(--_primary);
        box-shadow: 0 0 0 1px var(--_primary);
      }
      
      &.is-dragging {
        border-color: var(--_primary);
        background: var(--_primary-container);
      }
    }

    .drop-zone-overlay {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      background: var(--_primary-container);
      border-radius: 24px;
      z-index: 10;
      
      .drop-icon {
        font-size: 48px;
        width: 48px;
        height: 48px;
        color: var(--_primary);
      }
      
      .drop-caption {
        margin-top: 8px;
        font-size: 14px;
        color: var(--_on-primary-container);
      }
    }

    .chat-input {
      width: 100%;
      background: transparent;
      border: none;
      outline: none;
      font-size: 16px;
      color: var(--_on-surface);
      resize: none;
      font-family: inherit;
      line-height: 1.5;
      max-height: 200px;
      overflow-y: auto;
      
      &::placeholder {
        color: var(--_on-surface-variant);
      }
      
      &.content-flagged {
        text-decoration: underline wavy var(--_error);
        text-decoration-skip-ink: none;
        text-underline-offset: 3px;
      }
    }

    .clear-input-btn {
      position: absolute;
      top: 8px;
      right: 8px;
      width: 24px;
      height: 24px;
      
      mat-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
      }
    }

    .input-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid var(--_outline-variant);
    }

    .toolbar-left, .toolbar-right {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .toolbar-btn {
      color: var(--_on-surface-variant);
      
      &:hover {
        color: var(--_primary);
      }
    }

    .tools-btn {
      font-size: 13px;
      
      mat-icon {
        font-size: 18px;
        margin-right: 4px;
      }
    }

    .action-btn-container {
      overflow: hidden;
    }

    .send-btn {
      color: var(--_primary);
    }

    .mic-btn {
      &.recording {
        color: var(--_error);
        animation: pulse 1s ease-in-out infinite;
      }
    }

    .toggle-indicator {
      margin-left: auto;
      font-size: 18px;
      color: var(--_on-surface-variant);
      
      &.active {
        color: var(--_primary);
      }
    }

    /* Attached files styles */
    .attached-files-container {
      margin-top: 12px;
      padding: 12px;
      background: var(--_surface-container);
      border-radius: 12px;
    }

    .attachments-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }

    .attachments-count {
      font-size: 12px;
      color: var(--_on-surface-variant);
    }

    .attachments-actions {
      display: flex;
      gap: 4px;
      
      button {
        width: 28px;
        height: 28px;
        
        mat-icon {
          font-size: 18px;
        }
      }
    }

    .attached-files-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .file-row {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 8px;
      background: var(--_surface-container-high);
      border-radius: 8px;
    }

    .file-icon-wrapper {
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      
      .file-thumb-small {
        width: 32px;
        height: 32px;
        object-fit: cover;
        border-radius: 4px;
      }
      
      .file-type-icon-small {
        font-size: 24px;
        color: var(--_on-surface-variant);
      }
    }

    .file-name-text {
      flex: 1;
      font-size: 13px;
      color: var(--_on-surface);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .file-size-text {
      font-size: 11px;
      color: var(--_on-surface-variant);
    }

    .file-remove-btn-small {
      width: 24px;
      height: 24px;
      
      mat-icon {
        font-size: 16px;
      }
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
  `,
	],
})
export class ChatInputComponent implements AfterViewInit {
	/** Placeholder text for the input */
	placeholder = input<string>('Type a message...');

	/** Whether the input is disabled */
	disabled = input<boolean>(false);

	/** Whether content is flagged as unsafe */
	contentFlagged = input<boolean>(false);

	/** Labels of flagged content */
	flaggedLabels = input<string[]>([]);

	/** Whether streaming is enabled */
	streamingEnabled = input<boolean>(true);

	/** Whether markdown rendering is enabled */
	markdownEnabled = input<boolean>(true);

	/** Whether content safety is enabled */
	safetyEnabled = input<boolean>(true);

	/** Whether voice is currently recording */
	isRecording = input<boolean>(false);

	/** Whether voice input is supported */
	voiceSupported = input<boolean>(false);

	/**
	 * Signal-based text injection for decoupled communication.
	 * When this value changes, the input text is updated and the input is focused.
	 * Use with a signal from parent component:
	 *
	 * @example
	 * // In parent:
	 * injectedPrompt = signal<string | null>(null);
	 *
	 * // When quick action clicked:
	 * this.injectedPrompt.set('Tell me a joke');
	 *
	 * // In template:
	 * <app-chat-input [injectedText]="injectedPrompt()" />
	 */
	injectedText = input<string | null>(null);

	/** Emitted when user sends a message */
	send = output<SendEvent>();

	/** Emitted when input text changes */
	inputChange = output<string>();

	/** Emitted when voice toggle is clicked */
	toggleVoice = output<void>();

	/** Emitted when streaming toggle is clicked */
	toggleStreaming = output<void>();

	/** Emitted when markdown toggle is clicked */
	toggleMarkdown = output<void>();

	/** Emitted when safety toggle is clicked */
	toggleSafety = output<void>();

	/** Emitted when clear preferences is clicked */
	clearPreferences = output<void>();

	/** Emitted when files are selected */
	filesSelected = output<File[]>();

	/** Services */
	private snackBar = inject(MatSnackBar);
	private translate = inject(TranslateService);

	/** Local state */
	message = '';
	inputFocused = signal(false);
	isDragging = signal(false);
	attachedFiles = signal<AttachedFile[]>([]);

	/** Computed: show send button when there's text */
	showSendButton = computed(() => this.message.trim().length > 0);

	@ViewChild('chatTextarea') private textareaRef!: ElementRef<HTMLTextAreaElement>;

	constructor() {
		// Watch for injected text changes and update input with focus
		effect(() => {
			const text = this.injectedText();
			if (text !== null && text !== undefined) {
				this.message = text;
				this.onInputChange();
				// Focus and move cursor to end after text is set
				setTimeout(() => {
					this.focusInputAtEnd();
				}, 0);
			}
		});
	}

	ngAfterViewInit(): void {
		// Focus the input on init
		setTimeout(() => this.focusInput(), 100);
	}

	focusInput(event?: MouseEvent): void {
		if (event) {
			// Don't focus if clicking on a button
			const target = event.target as HTMLElement;
			if (target.closest('button') || target.closest('mat-menu')) {
				return;
			}
		}
		this.textareaRef?.nativeElement?.focus();
	}

	/**
	 * Focus the input and move cursor to the end of the text.
	 * Used when injecting text to place cursor after the injected content.
	 */
	focusInputAtEnd(): void {
		const textarea = this.textareaRef?.nativeElement;
		if (textarea) {
			textarea.focus();
			const length = textarea.value.length;
			textarea.setSelectionRange(length, length);
		}
	}

	onInputChange(): void {
		this.inputChange.emit(this.message);
	}

	onEnterKey(event: Event): void {
		const keyEvent = event as KeyboardEvent;
		if (!keyEvent.shiftKey) {
			event.preventDefault();
			this.sendMessage();
		}
	}

	sendMessage(): void {
		const trimmedMessage = this.message.trim();
		if (!trimmedMessage && this.attachedFiles().length === 0) return;

		this.send.emit({
			message: trimmedMessage,
			attachments: [...this.attachedFiles()],
		});

		this.message = '';
		this.attachedFiles.set([]);
	}

	clearInput(): void {
		this.message = '';
		this.inputChange.emit('');
	}

	// Drag and drop handlers
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
		if (files && files.length > 0) {
			this.processFiles(Array.from(files));
		}
	}

	onFileSelected(event: Event): void {
		const input = event.target as HTMLInputElement;
		if (input.files && input.files.length > 0) {
			this.processFiles(Array.from(input.files));
			input.value = ''; // Reset for same file selection
		}
	}

	private processFiles(files: File[]): void {
		const currentFiles = this.attachedFiles();

		// Check max attachments
		if (currentFiles.length + files.length > DEFAULT_CONFIG.maxAttachments) {
			this.snackBar.open(
				this.translate.instant('errors.tooManyFiles', { max: DEFAULT_CONFIG.maxAttachments }),
				'OK',
				{ duration: 3000 }
			);
			return;
		}

		for (const file of files) {
			// Check file size
			if (file.size > DEFAULT_CONFIG.maxFileSizeBytes) {
				this.snackBar.open(
					this.translate.instant('errors.fileTooLarge', { name: file.name, size: '1MB' }),
					'OK',
					{ duration: 3000 }
				);
				continue;
			}

			// Create preview for images
			if (file.type.startsWith('image/')) {
				const reader = new FileReader();
				reader.onload = () => {
					this.attachedFiles.update((files) => [
						...files,
						{
							name: file.name,
							size: file.size,
							type: file.type,
							preview: reader.result as string,
							data: reader.result as string,
						},
					]);
				};
				reader.readAsDataURL(file);
			} else {
				this.attachedFiles.update((files) => [
					...files,
					{
						name: file.name,
						size: file.size,
						type: file.type,
					},
				]);
			}
		}
	}

	removeFile(file: AttachedFile): void {
		this.attachedFiles.update((files) => files.filter((f) => f.name !== file.name));
	}

	clearAllFiles(): void {
		this.attachedFiles.set([]);
	}

	getFileIcon(mimeType: string): string {
		return getMimeTypeIcon(mimeType);
	}

	formatFileSize(bytes: number): string {
		if (bytes === 0) return '0 B';
		const k = 1024;
		const sizes = ['B', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return `${Number.parseFloat((bytes / k ** i).toFixed(1))} ${sizes[i]}`;
	}
}
