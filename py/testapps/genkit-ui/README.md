# @genkit-ai/genkit-ui

Beautiful Angular components for AI-powered applications.

## Features

- **ChatBoxComponent** - Complete chat interface with voice support
- **MessageListComponent** - Message display with markdown rendering
- **ChatInputComponent** - Rich text input with attachments
- **ModelSelectorComponent** - Searchable model dropdown
- **ThemeSelectorComponent** - Light/dark/system theme toggle
- **LanguageSelectorComponent** - Multi-language support with RTL

## Installation

```bash
pnpm add @genkit-ai/genkit-ui
```

## Quick Start

```typescript
import { ChatBoxComponent } from '@genkit-ai/genkit-ui/chat';

@Component({
  imports: [ChatBoxComponent],
  template: `
    <genkit-chat-box
      [messages]="messages"
      [isLoading]="isLoading"
      [selfManagedVoice]="true"
      (send)="onSend($event)" />
  `
})
export class AppComponent {
  messages = [];
  isLoading = false;
  
  onSend(event: SendEvent) {
    // Handle message send
  }
}
```

## Components

### Chat Components

| Component | Selector | Description |
|-----------|----------|-------------|
| `ChatBoxComponent` | `genkit-chat-box` | Complete chat interface |
| `ChatInputComponent` | `genkit-chat-input` | Text input with attachments |
| `MessageListComponent` | `genkit-message-list` | Message display |
| `WelcomeScreenComponent` | `genkit-welcome-screen` | Welcome with quick actions |
| `PromptQueueComponent` | `genkit-prompt-queue` | Queued prompts |
| `ModelSelectorComponent` | `genkit-model-selector` | Model dropdown |

### Theme Components

| Component | Selector | Description |
|-----------|----------|-------------|
| `ThemeSelectorComponent` | `genkit-theme-selector` | Theme toggle |
| `LanguageSelectorComponent` | `genkit-language-selector` | Language picker |

## Storybook

```bash
pnpm run storybook
```

## License

Apache-2.0
