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

/**
 * Genkit Chat Feature Components
 *
 * A collection of reusable Angular components for building AI chat interfaces.
 * These components are designed to be portable and can be used in other applications.
 *
 * Component Hierarchy::
 *
 *     ChatComponent (container)
 *     ├── MessageListComponent      - Message display with markdown
 *     ├── WelcomeScreenComponent    - Greeting animation, quick actions
 *     ├── PromptQueueComponent      - Queue with drag-and-drop
 *     ├── ChatInputComponent        - Input, attachments, voice, settings
 *     │   └── [slot: modelSelector]
 *     └── ModelSelectorComponent    - Searchable model dropdown
 *
 * Portability Requirements::
 *
 *     ┌─────────────────────────────────────────────────────────────────┐
 *     │                    REQUIRED IN HOST APP                        │
 *     ├─────────────────────────────────────────────────────────────────┤
 *     │  1. CSS Variables (see _theme.scss)                            │
 *     │     - --primary, --on-primary, --primary-container             │
 *     │     - --surface, --surface-container, --on-surface             │
 *     │     - --error, --error-container, --outline-variant            │
 *     │                                                                 │
 *     │  2. Angular Material                                            │
 *     │     - @angular/material (^18.0.0)                               │
 *     │     - Import a prebuilt theme or define custom                  │
 *     │                                                                 │
 *     │  3. ngx-translate (for i18n)                                    │
 *     │     - @ngx-translate/core                                       │
 *     │     - See en.json for required translation keys                 │
 *     │                                                                 │
 *     │  4. Material Icons Font                                         │
 *     │     - <link href="...fonts.googleapis.com/icon?family=          │
 *     │       Material+Icons" rel="stylesheet">                         │
 *     │                                                                 │
 *     │  5. Optional Services (for full functionality)                  │
 *     │     - SpeechService (Web Speech API wrapper)                    │
 *     │     - ContentSafetyService (TensorFlow toxicity)                │
 *     └─────────────────────────────────────────────────────────────────┘
 *
 * Quick Start::
 *
 *     1. Install dependencies:
 *        npm install @angular/material @ngx-translate/core
 *
 *     2. Import the theme in your styles.scss:
 *        @import '@genkit-chat/components/theme';
 *        // OR copy CSS variables from _theme.scss to your :root
 *
 *     3. Import components in your module:
 *        import { ChatInputComponent, MessageListComponent } from './components';
 *
 *     4. Use in templates:
 *        <app-message-list [messages]="messages" [isLoading]="isLoading" />
 *        <app-chat-input (send)="onSend($event)" />
 *
 * Signal-Based Communication::
 *
 *     The components use signals for decoupled communication. For example,
 *     when a quick action is selected in WelcomeScreenComponent, it emits
 *     the prompt text. The parent can then inject it into ChatInputComponent
 *     using the [injectedText] input:
 *
 *     @Component({
 *       template: `
 *         @if (messages.length === 0) {
 *           <app-welcome-screen
 *             [greetings]="greetings"
 *             [quickActions]="quickActions"
 *             (actionSelected)="injectedPrompt.set($event)" />
 *         }
 *
 *         <app-chat-input
 *           [injectedText]="injectedPrompt()"
 *           (send)="onSend($event)" />
 *       `
 *     })
 *     export class ChatPage {
 *       injectedPrompt = signal<string | null>(null);
 *       // When WelcomeScreen emits, injectedPrompt updates,
 *       // ChatInput effect triggers, sets text, focuses cursor at end
 *     }
 *
 * Example Usage::
 *
 *     @Component({
 *       template: `
 *         <app-message-list
 *           [messages]="chatService.messages()"
 *           [isLoading]="chatService.isLoading()"
 *           [markdownMode]="true"
 *           (copy)="copyToClipboard($event)" />
 *
 *         <app-chat-input
 *           [placeholder]="'Ask me anything...'"
 *           [streamingEnabled]="true"
 *           (send)="sendMessage($event)">
 *           <app-model-selector modelSelector
 *             [selectedModel]="selectedModel"
 *             [providers]="providers"
 *             (modelSelected)="onModelChange($event)" />
 *         </app-chat-input>
 *       `,
 *       imports: [MessageListComponent, ChatInputComponent, ModelSelectorComponent]
 *     })
 *     export class MyChatPage { }
 */

// Re-export types for convenience
export type { AttachedFile, SendEvent } from './chat-input/chat-input.component';
export * from './chat-input/chat-input.component';
// Component exports
export * from './message-list/message-list.component';
export type { Model, Provider } from './model-selector/model-selector.component';
export * from './model-selector/model-selector.component';
export type { QueueItem } from './prompt-queue/prompt-queue.component';
export * from './prompt-queue/prompt-queue.component';
export type { Greeting, QuickAction } from './welcome-screen/welcome-screen.component';
export * from './welcome-screen/welcome-screen.component';
