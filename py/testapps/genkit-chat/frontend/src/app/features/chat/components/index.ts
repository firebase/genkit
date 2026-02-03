/**
 * Chat Feature Components Index
 * 
 * This module exports all the refactored chat components.
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
 * Usage::
 * 
 *     import { 
 *       MessageListComponent,
 *       WelcomeScreenComponent,
 *       PromptQueueComponent,
 *       ChatInputComponent,
 *       ModelSelectorComponent
 *     } from './components';
 */

export * from './message-list/message-list.component';
export * from './welcome-screen/welcome-screen.component';
export * from './prompt-queue/prompt-queue.component';
export * from './chat-input/chat-input.component';
export * from './model-selector/model-selector.component';
