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
 * ChatBoxComponent - Self-contained, shareable chat interface.
 *
 * This component provides a complete AI chat experience that can be embedded
 * in any Angular application. It combines all chat sub-components into a
 * single, easy-to-use interface.
 *
 * Features:
 * - Message display with markdown rendering
 * - Welcome screen with greetings and quick actions
 * - Text input with file attachments
 * - Model selector dropdown
 * - Streaming and non-streaming modes
 * - Voice input support (built-in Web Speech API or external)
 * - Content safety checking (optional)
 * - Full i18n support
 * - RTL language support
 * - Dark/light theme support
 *
 * Voice Input Modes:
 * - selfManagedVoice=false (default): Parent provides isRecording, voiceSupported,
 *   and handles toggleVoice output
 * - selfManagedVoice=true: Component manages voice internally using Web Speech API
 *
 * Portability:
 * - This component is SELF-CONTAINED with CSS fallback variables
 * - Requires: @angular/material, @ngx-translate/core
 * - Optional: marked, dompurify (for markdown), Web Speech API (for voice)
 *
 * Component Architecture::
 *
 *     ┌─────────────────────────────────────────────────────────────────┐
 *     │                       ChatBoxComponent                         │
 *     ├─────────────────────────────────────────────────────────────────┤
 *     │  ┌─────────────────────────────────────────────────────────┐   │
 *     │  │  Messages Area                                          │   │
 *     │  │  ├── WelcomeScreen (when empty)                         │   │
 *     │  │  └── MessageList (when has messages)                    │   │
 *     │  └─────────────────────────────────────────────────────────┘   │
 *     │                                                                 │
 *     │  ┌─────────────────────────────────────────────────────────┐   │
 *     │  │  Input Area                                             │   │
 *     │  │  └── ChatInput + ModelSelector                          │   │
 *     │  └─────────────────────────────────────────────────────────┘   │
 *     ├─────────────────────────────────────────────────────────────────┤
 *     │  Inputs:                                                        │
 *     │  - messages: Message[]                                          │
 *     │  - isLoading: boolean                                           │
 *     │  - models: Model[]                                              │
 *     │  - selectedModel: Model                                         │
 *     │  - greetings: Greeting[]                                        │
 *     │  - quickActions: QuickAction[]                                  │
 *     │  - streamingEnabled, markdownEnabled, safetyEnabled             │
 *     │  - avatarUrl, logoUrl                                           │
 *     │  - selfManagedVoice: boolean (enables built-in voice)           │
 *     │                                                                 │
 *     │  Outputs:                                                       │
 *     │  - send: EventEmitter<SendEvent>                                │
 *     │  - modelSelected: EventEmitter<Model>                           │
 *     │  - settingsChanged: EventEmitter<ChatSettings>                  │
 *     └─────────────────────────────────────────────────────────────────┘
 *
 * Usage Example (Self-managed voice)::
 *
 *     <app-chat-box
 *       [messages]="messages"
 *       [isLoading]="isLoading"
 *       [selfManagedVoice]="true"
 *       (send)="onSend($event)" />
 *
 * Usage Example (External voice control)::
 *
 *     <app-chat-box
 *       [messages]="messages"
 *       [isRecording]="speechService.isRecording()"
 *       [voiceSupported]="speechService.isSupported()"
 *       (toggleVoice)="speechService.toggle()"
 *       (send)="onSend($event)" />
 */
import {
	ChangeDetectionStrategy,
	Component,
	computed,
	effect,
	input,
	type OnDestroy,
	output,
	signal,
} from '@angular/core';
import { TranslateModule } from '@ngx-translate/core';
import { ChatInputComponent, type SendEvent } from '../chat-input/chat-input.component';
// Import sub-components
import { type Message, MessageListComponent } from '../message-list/message-list.component';
import {
	type Model,
	ModelSelectorComponent,
	type Provider,
} from '../model-selector/model-selector.component';
import {
	type Greeting,
	type QuickAction,
	WelcomeScreenComponent,
} from '../welcome-screen/welcome-screen.component';

/**
 * Chat settings that can be toggled by user.
 */
export interface ChatSettings {
	streamingEnabled: boolean;
	markdownEnabled: boolean;
	safetyEnabled: boolean;
}

/**
 * Default greetings for the welcome screen.
 */
export const DEFAULT_GREETINGS: Greeting[] = [
	{ text: 'Hello', lang: 'en', dir: 'ltr', anim: 'type' },
	{ text: 'Bonjour', lang: 'fr', dir: 'ltr', anim: 'type' },
	{ text: 'Hola', lang: 'es', dir: 'ltr', anim: 'type' },
	{ text: 'こんにちは', lang: 'ja', dir: 'ltr', anim: 'slide' },
	{ text: 'नमस्ते', lang: 'hi', dir: 'ltr', anim: 'slide' },
	{ text: 'مرحبا', lang: 'ar', dir: 'rtl', anim: 'slide' },
];

/**
 * Default quick actions for the welcome screen.
 */
export const DEFAULT_QUICK_ACTIONS: QuickAction[] = [
	{
		icon: 'lightbulb',
		labelKey: 'chat.actions.explain',
		prompt: 'Explain the concept of ',
		color: 'primary',
	},
	{
		icon: 'code',
		labelKey: 'chat.actions.write_code',
		prompt: 'Write code that ',
		color: 'accent',
	},
	{ icon: 'edit', labelKey: 'chat.actions.help_write', prompt: 'Help me write ', color: 'warn' },
	{
		icon: 'psychology',
		labelKey: 'chat.actions.brainstorm',
		prompt: 'Brainstorm ideas for ',
		color: 'primary',
	},
];

/**
 * Type declarations for Web Speech API (not in all TypeScript libs).
 * These types provide structural compatibility for browser speech recognition.
 */
interface SpeechRecognitionResult {
	readonly length: number;
	readonly isFinal: boolean;
	item(index: number): SpeechRecognitionAlternative;
	[index: number]: SpeechRecognitionAlternative;
}

interface SpeechRecognitionAlternative {
	readonly transcript: string;
	readonly confidence: number;
}

interface SpeechRecognitionResultList {
	readonly length: number;
	item(index: number): SpeechRecognitionResult;
	[index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionEvent extends Event {
	readonly results: SpeechRecognitionResultList;
	readonly resultIndex: number;
}

interface SpeechRecognitionInterface {
	continuous: boolean;
	interimResults: boolean;
	lang: string;
	start(): void;
	stop(): void;
	abort(): void;
	onresult: ((event: SpeechRecognitionEvent) => void) | null;
	onerror: ((event: Event) => void) | null;
	onend: (() => void) | null;
}

interface SpeechRecognitionConstructor {
	new (): SpeechRecognitionInterface;
}

declare global {
	interface Window {
		SpeechRecognition?: SpeechRecognitionConstructor;
		webkitSpeechRecognition?: SpeechRecognitionConstructor;
	}
}

@Component({
	selector: 'genkit-chat-box',
	standalone: true,
	imports: [
		CommonModule,
		TranslateModule,
		MessageListComponent,
		WelcomeScreenComponent,
		ChatInputComponent,
		ModelSelectorComponent,
	],
	changeDetection: ChangeDetectionStrategy.OnPush,
	template: `
    <div class="chat-box" [class.loading]="isLoading()">
      <!-- Messages Area -->
      <div class="messages-area">
        @if (messages().length === 0 && !isLoading()) {
          <genkit-welcome-screen
            [greetings]="greetings()"
            [quickActions]="quickActions()"
            [logoUrl]="logoUrl()"
            (actionSelected)="onQuickAction($event)" />
        } @else {
          <genkit-message-list
            [messages]="messages()"
            [isLoading]="isLoading()"
            [error]="error()"
            [markdownMode]="effectiveMarkdownEnabled()"
            [avatarUrl]="avatarUrl()"
            (copy)="copyMessage.emit($event)"
            (speak)="onSpeak($event)"
            (retry)="retryMessage.emit()"
            (thumbUp)="thumbUp.emit($event)"
            (thumbDown)="thumbDown.emit($event)" />
        }
      </div>
      
      <!-- Input Area -->
      <div class="input-area">
        <genkit-chat-input
          [disabled]="disabled() || isLoading()"
          [placeholder]="placeholder()"
          [streamingEnabled]="effectiveStreamingEnabled()"
          [markdownEnabled]="effectiveMarkdownEnabled()"
          [safetyEnabled]="effectiveSafetyEnabled()"
          [isRecording]="effectiveIsRecording()"
          [voiceSupported]="effectiveVoiceSupported()"
          [contentFlagged]="contentFlagged()"
          [flaggedLabels]="flaggedLabels()"
          [injectedText]="injectedText()"
          (send)="onSend($event)"
          (inputChange)="inputChange.emit($event)"
          (toggleVoice)="onToggleVoice()"
          (toggleStreaming)="onToggleStreaming()"
          (toggleMarkdown)="onToggleMarkdown()"
          (toggleSafety)="onToggleSafety()"
          (filesSelected)="filesSelected.emit($event)">
          
          <!-- Model Selector Slot -->
          @if (showModelSelector() && providers().length > 0) {
            <genkit-model-selector modelSelector
              [selectedModel]="selectedModel()"
              [providers]="providers()"
              [recentModels]="recentModels()"
              (modelSelected)="onModelSelected($event)" />
          }
        </genkit-chat-input>
      </div>
    </div>
  `,
	styles: [
		`
    /* CSS Variable Defaults - ensures component works without global theme */
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
      
      --_surface: var(--surface, #fafafa);
      --_surface-container: var(--surface-container, #f0f4f9);
      --_on-surface: var(--on-surface, #1a1c1e);
      --_outline-variant: var(--outline-variant, #c4c6d0);
    }

    .chat-box {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: var(--_surface);
    }

    .messages-area {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
    }

    .input-area {
      flex-shrink: 0;
      padding: 16px;
      border-top: 1px solid var(--_outline-variant);
      background: var(--_surface-container);
    }

    /* Loading state styling */
    .chat-box.loading {
      .input-area {
        opacity: 0.7;
        pointer-events: none;
      }
    }
  `,
	],
})
export class ChatBoxComponent implements OnDestroy {
	// =====================================================================
	// Message Display Inputs
	// =====================================================================

	/** List of chat messages to display */
	messages = input<Message[]>([]);

	/** Whether the assistant is generating a response */
	isLoading = input<boolean>(false);

	/** Error message to display */
	error = input<string | null>(null);

	/** Avatar URL for assistant messages */
	avatarUrl = input<string>('genkit-logo.png');

	// =====================================================================
	// Welcome Screen Inputs
	// =====================================================================

	/** Greetings to display on welcome screen */
	greetings = input<Greeting[]>(DEFAULT_GREETINGS);

	/** Quick action buttons on welcome screen */
	quickActions = input<QuickAction[]>(DEFAULT_QUICK_ACTIONS);

	/** Logo URL for welcome screen */
	logoUrl = input<string>('genkit-logo.png');

	// =====================================================================
	// Input Configuration
	// =====================================================================

	/** Whether the input is disabled */
	disabled = input<boolean>(false);

	/** Placeholder text for the input */
	placeholder = input<string>('Type a message...');

	/** Whether streaming is enabled */
	streamingEnabled = input<boolean>(true);

	/** Whether markdown rendering is enabled */
	markdownEnabled = input<boolean>(true);

	/** Whether content safety checking is enabled */
	safetyEnabled = input<boolean>(true);

	// =====================================================================
	// Voice Input Configuration
	// =====================================================================

	/**
	 * When true, the component manages voice input internally using Web Speech API.
	 * When false (default), parent provides isRecording/voiceSupported and handles toggleVoice.
	 */
	selfManagedVoice = input<boolean>(false);

	/**
	 * Language for speech recognition (BCP-47 format, e.g., 'en-US').
	 * Only used when selfManagedVoice is true.
	 */
	speechLanguage = input<string>('en-US');

	/** Whether voice is currently recording (external mode) */
	isRecording = input<boolean>(false);

	/** Whether voice input is supported (external mode) */
	voiceSupported = input<boolean>(false);

	// =====================================================================
	// Content Safety
	// =====================================================================

	/** Whether current input content is flagged */
	contentFlagged = input<boolean>(false);

	/** Labels of flagged content */
	flaggedLabels = input<string[]>([]);

	// =====================================================================
	// Model Selection
	// =====================================================================

	/** Whether to show the model selector */
	showModelSelector = input<boolean>(true);

	/** Currently selected model */
	selectedModel = input<Model | null>(null);

	/** Available model providers */
	providers = input<Provider[]>([]);

	/** Recently used models */
	recentModels = input<Model[]>([]);

	// =====================================================================
	// Outputs
	// =====================================================================

	/** Emitted when user sends a message */
	send = output<SendEvent>();

	/** Emitted when input text changes */
	inputChange = output<string>();

	/** Emitted when user selects a model */
	modelSelected = output<Model>();

	/** Emitted when settings change */
	settingsChanged = output<ChatSettings>();

	/** Emitted when voice toggle is clicked (external voice mode only) */
	toggleVoice = output<void>();

	/** Emitted when files are selected */
	filesSelected = output<File[]>();

	/** Emitted when user clicks copy on a message */
	copyMessage = output<string>();

	/** Emitted when user clicks speak on a message */
	speakMessage = output<string>();

	/** Emitted when user clicks retry after error */
	retryMessage = output<void>();

	/** Emitted when user gives thumbs up */
	thumbUp = output<number>();

	/** Emitted when user gives thumbs down */
	thumbDown = output<number>();

	// =====================================================================
	// Internal State
	// =====================================================================

	/** Signal for injected text from quick actions */
	injectedText = signal<string | null>(null);

	/** Internal settings state */
	private _streamingEnabled = signal(true);
	private _markdownEnabled = signal(true);
	private _safetyEnabled = signal(true);

	/** Internal voice state (for self-managed mode) */
	private _internalIsRecording = signal(false);
	private _internalVoiceSupported = signal(false);

	/** Speech recognition instance */
	private recognition: SpeechRecognitionInterface | null = null;

	/** Speech synthesis for speaking messages */
	private synthesis = typeof window !== 'undefined' ? window.speechSynthesis : null;

	/** Effective values combining external and internal state */
	effectiveIsRecording = computed(() =>
		this.selfManagedVoice() ? this._internalIsRecording() : this.isRecording()
	);

	effectiveVoiceSupported = computed(() =>
		this.selfManagedVoice() ? this._internalVoiceSupported() : this.voiceSupported()
	);

	effectiveStreamingEnabled = computed(() => this._streamingEnabled());
	effectiveMarkdownEnabled = computed(() => this._markdownEnabled());
	effectiveSafetyEnabled = computed(() => this._safetyEnabled());

	constructor() {
		// Sync inputs to internal state
		effect(() => {
			this._streamingEnabled.set(this.streamingEnabled());
			this._markdownEnabled.set(this.markdownEnabled());
			this._safetyEnabled.set(this.safetyEnabled());
		});

		// Initialize voice if self-managed
		effect(() => {
			if (this.selfManagedVoice()) {
				this.initVoice();
			}
		});
	}

	ngOnDestroy(): void {
		this.stopRecording();
		if (this.synthesis) {
			this.synthesis.cancel();
		}
	}

	// =====================================================================
	// Voice Management (Self-Managed Mode)
	// =====================================================================

	private initVoice(): void {
		if (typeof window === 'undefined') return;

		const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
		if (SpeechRecognition) {
			this._internalVoiceSupported.set(true);
			this.recognition = new SpeechRecognition();
			this.recognition.continuous = false;
			this.recognition.interimResults = true;
			this.recognition.lang = this.speechLanguage();

			this.recognition.onresult = (event) => {
				const transcript = Array.from(event.results)
					.map((result) => result[0].transcript)
					.join('');

				// Inject the transcribed text
				if (event.results[0].isFinal) {
					this.injectedText.set(transcript);
				}
			};

			this.recognition.onend = () => {
				this._internalIsRecording.set(false);
			};

			this.recognition.onerror = () => {
				this._internalIsRecording.set(false);
			};
		}
	}

	private startRecording(): void {
		if (this.recognition && !this._internalIsRecording()) {
			this.recognition.lang = this.speechLanguage();
			this.recognition.start();
			this._internalIsRecording.set(true);
		}
	}

	private stopRecording(): void {
		if (this.recognition && this._internalIsRecording()) {
			this.recognition.stop();
			this._internalIsRecording.set(false);
		}
	}

	// =====================================================================
	// Event Handlers
	// =====================================================================

	onQuickAction(prompt: string): void {
		this.injectedText.set(prompt);
	}

	onSend(event: SendEvent): void {
		// Clear injected text after send
		this.injectedText.set(null);
		this.send.emit(event);
	}

	onModelSelected(model: Model): void {
		this.modelSelected.emit(model);
	}

	onToggleVoice(): void {
		if (this.selfManagedVoice()) {
			// Self-managed: toggle recording internally
			if (this._internalIsRecording()) {
				this.stopRecording();
			} else {
				this.startRecording();
			}
		} else {
			// External: emit event for parent to handle
			this.toggleVoice.emit();
		}
	}

	/** Speak a message using Speech Synthesis API */
	onSpeak(text: string): void {
		if (this.synthesis) {
			// Cancel any ongoing speech
			this.synthesis.cancel();

			const utterance = new SpeechSynthesisUtterance(text);
			utterance.lang = this.speechLanguage();
			this.synthesis.speak(utterance);
		}
		this.speakMessage.emit(text);
	}

	onToggleStreaming(): void {
		this._streamingEnabled.update((v) => !v);
		this.emitSettings();
	}

	onToggleMarkdown(): void {
		this._markdownEnabled.update((v) => !v);
		this.emitSettings();
	}

	onToggleSafety(): void {
		this._safetyEnabled.update((v) => !v);
		this.emitSettings();
	}

	private emitSettings(): void {
		this.settingsChanged.emit({
			streamingEnabled: this._streamingEnabled(),
			markdownEnabled: this._markdownEnabled(),
			safetyEnabled: this._safetyEnabled(),
		});
	}
}
