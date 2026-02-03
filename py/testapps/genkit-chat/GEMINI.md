# Genkit Chat - Demo Application

See [../GEMINI.md](../GEMINI.md) for shared development guidelines and component documentation.

## Quick Start

```bash
# Start backend
cd backend && uv run fastapi dev

# Start frontend (in another terminal)
cd frontend && pnpm start
```

## Directory Structure

```
genkit-chat/
├── frontend/              # Angular 21 application
│   ├── src/app/
│   │   ├── features/      # Feature modules
│   │   ├── core/          # Services, guards
│   │   └── shared/        # Local shared utilities
│   └── src/assets/i18n/   # Translation files
└── backend/               # Python FastAPI server
    ├── main.py            # Routes, SSE streaming
    └── genkit_setup.py    # Plugin configuration
```

## Using @aspect/genkit-ui Components

This demo uses the shared `@aspect/genkit-ui` library:

```typescript
import { ChatBoxComponent } from '@aspect/genkit-ui/chat';

@Component({
  imports: [ChatBoxComponent],
  template: `
    <genkit-chat-box
      [messages]="messages"
      [isLoading]="isLoading"
      (send)="onSend($event)" />
  `
})
```

See the library README at `../genkit-ui/README.md` for full documentation.
