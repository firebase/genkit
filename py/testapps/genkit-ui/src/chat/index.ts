/**
 * Chat Components
 * 
 * A complete set of components for building AI chat interfaces.
 * 
 * Component Hierarchy::
 * 
 *     ChatBoxComponent (container - use this for complete chat UI)
 *     ├── MessageListComponent      - Message display with markdown
 *     ├── WelcomeScreenComponent    - Greeting animation, quick actions
 *     ├── PromptQueueComponent      - Queue with drag-and-drop
 *     ├── ChatInputComponent        - Input, attachments, voice, settings
 *     └── ModelSelectorComponent    - Searchable model dropdown
 * 
 * Quick Start::
 * 
 *     // For a complete chat interface:
 *     import { ChatBoxComponent } from '@aspect/genkit-ui/chat';
 *     
 *     @Component({
 *       imports: [ChatBoxComponent],
 *       template: `
 *         <genkit-chat-box
 *           [messages]="messages"
 *           [isLoading]="isLoading"
 *           [selfManagedVoice]="true"
 *           (send)="onSend($event)" />
 *       `
 *     })
 * 
 *     // For individual components:
 *     import { ChatInputComponent, MessageListComponent } from '@aspect/genkit-ui/chat';
 * 
 * @packageDocumentation
 */

// Main container component
export { ChatBoxComponent, DEFAULT_GREETINGS, DEFAULT_QUICK_ACTIONS } from './chat-box/chat-box.component';
export type { ChatSettings } from './chat-box/chat-box.component';

// Individual components
export { MessageListComponent } from './message-list/message-list.component';
export type { Message } from './message-list/message-list.component';

export { WelcomeScreenComponent } from './welcome-screen/welcome-screen.component';
export type { Greeting, QuickAction } from './welcome-screen/welcome-screen.component';

export { PromptQueueComponent } from './prompt-queue/prompt-queue.component';
export type { QueueItem } from './prompt-queue/prompt-queue.component';

export { ChatInputComponent } from './chat-input/chat-input.component';
export type { SendEvent, AttachedFile } from './chat-input/chat-input.component';

export { ModelSelectorComponent } from './model-selector/model-selector.component';
export type { Model, Provider } from './model-selector/model-selector.component';

