# Genkit Testapps - Development Guidelines

This document captures learnings, patterns, and best practices from developing the Genkit test applications.

> **AI Agent Requirement:** This file MUST be kept up to date with learnings at the end of each session and intermittently as significant progress is made. When making architectural decisions, adding new patterns, or solving complex problems, document them here.

---

## Workspace Structure

```
py/testapps/
├── pnpm-workspace.yaml    # PNPM workspace config
├── GEMINI.md              # This file - shared documentation
├── genkit-ui/             # Shared component library (@aspect/genkit-ui)
│   ├── package.json
│   ├── src/
│   │   ├── index.ts       # Main entry point
│   │   ├── chat/          # Chat components
│   │   └── theme/         # Theme components
│   └── .storybook/        # Storybook config
└── genkit-chat/           # Demo chat application
    ├── frontend/          # Angular frontend
    └── backend/           # Python backend
```

---

## Package Manager: pnpm (REQUIRED)

**This workspace uses pnpm, NOT npm.** The `workspace:*` protocol in package.json requires pnpm.

```bash
# Check if pnpm is installed
pnpm --version

# Install pnpm if needed
npm install -g pnpm

# Install dependencies (from testapps/ root)
pnpm install
```

**DO NOT use npm** - it will fail with `Unsupported URL Type "workspace:"` errors.

---

## Google OSS Requirements

Every package or testapp in this workspace MUST include these files for Google OSS compliance:

| File | Description | Required |
|------|-------------|----------|
| `LICENSE` | Apache 2.0 license | ✅ Yes |
| `README.md` | Package/app documentation | ✅ Yes |
| `CONTRIBUTING.md` | Contribution guidelines (can reference parent) | ✅ Yes |
| `CODE_OF_CONDUCT.md` | Code of conduct (can reference parent) | ✅ Yes |

### License Header

All source files must include the Apache 2.0 license header:

```typescript
// Copyright [year] Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0
```

### Checklist for New Packages

When creating a new package or testapp:

- [ ] Add `LICENSE` file (Apache 2.0)
- [ ] Add `README.md` with package description
- [ ] Add `CONTRIBUTING.md` (can reference `../../CONTRIBUTING.md`)
- [ ] Add `CODE_OF_CONDUCT.md` (can reference `../../CODE_OF_CONDUCT.md`)
- [ ] Ensure all source files have license headers
- [ ] Add package to `pnpm-workspace.yaml`

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Genkit Chat Architecture                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Frontend (Angular 19)                                                      │
│  ├── ChatComponent (legacy)  - Legacy monolithic component                  │
│  │   └── Refactored Components (features/chat/components/)                  │
│  │       ├── MessageListComponent    - Message display with markdown        │
│  │       ├── WelcomeScreenComponent  - Greeting animation, quick actions    │
│  │       ├── PromptQueueComponent    - Queue with drag-and-drop             │
│  │       ├── ChatInputComponent      - Input, attachments, voice, settings  │
│  │       └── ModelSelectorComponent  - Searchable model dropdown            │
│  ├── CompareComponent        - Side-by-side model comparison                │
│  ├── Services                                                               │
│  │   ├── ChatService         - Message management, streaming, queue         │
│  │   ├── ModelsService       - Model list, selection, categorization        │
│  │   ├── SpeechService       - Voice input via Web Speech API               │
│  │   ├── ContentSafetyService - Client-side toxicity detection              │
│  │   ├── ThemeService        - Dark/light/system theme management           │
│  │   ├── LanguageService     - i18n with RTL support                        │
│  │   └── AuthService         - Google OAuth with jwt-decode                 │
│  └── Utilities                                                              │
│      ├── SafeMarkdownPipe    - DOMPurify + marked for safe rendering        │
│      └── getMimeTypeIcon     - Semantic file type icons                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  Backend (Python + Robyn/FastAPI)                                           │
│  ├── main.py                 - Routes, SSE streaming, model registry        │
│  ├── genkit_setup.py         - Plugin loading, model discovery              │
│  ├── Genkit Integration      - Flows, tools, prompts                        │
│  └── Multi-provider          - Google AI, Anthropic, OpenAI, Ollama         │
└─────────────────────────────────────────────────────────────────────────────┘
```


## Storybook

The project includes [Storybook](https://storybook.js.org/) for component development and testing in isolation.

### Telemetry

**Disable telemetry by default.** Storybook and other tools may collect anonymous usage data. For privacy and compliance, disable telemetry:

```bash
# Disable Storybook telemetry
npx storybook telemetry --disable

# Or set environment variable
export STORYBOOK_DISABLE_TELEMETRY=1
```

### Running Storybook

```bash
cd frontend

# Start Storybook development server
pnpm run storybook

# Build static Storybook
pnpm run build-storybook
```

Storybook will be available at `http://localhost:6006`.

### Available Component Stories

| Component | Location | Stories |
|-----------|----------|---------|
| **MessageList** | `Chat/MessageList` | Default, Empty, Loading, Error, MarkdownDisabled, LongConversation |
| **WelcomeScreen** | `Chat/WelcomeScreen` | Default, SingleGreeting, RTL, NoQuickActions, ManyQuickActions |
| **PromptQueue** | `Chat/PromptQueue` | Default, Empty, SingleItem, LongQueue, LongContent, WithEmoji |
| **ChatInput** | `Chat/ChatInput` | Default, VoiceRecording, ContentFlagged, Disabled, DarkMode, RTL |
| **ModelSelector** | `Chat/ModelSelector` | Default, SingleProvider, LocalOnly, ManyModels, LongModelNames |

### Writing New Stories

Stories are located alongside components with `.stories.ts` extension:

```
components/
├── message-list/
│   ├── message-list.component.ts
│   └── message-list.stories.ts    # Stories file
└── chat-input/
    ├── chat-input.component.ts
    └── chat-input.stories.ts
```

**Story Template:**

```typescript
import type { Meta, StoryObj } from '@storybook/angular';
import { MyComponent } from './my.component';

const meta: Meta<MyComponent> = {
  title: 'Category/MyComponent',
  component: MyComponent,
  tags: ['autodocs'],
  argTypes: {
    myInput: { description: 'Description', control: 'text' },
    myOutput: { action: 'myOutput' },
  },
};

export default meta;
type Story = StoryObj<MyComponent>;

export const Default: Story = {
  args: {
    myInput: 'Default value',
  },
};

export const AnotherState: Story = {
  args: {
    myInput: 'Different value',
  },
};
```

### Addons

- **@storybook/addon-a11y**: Accessibility testing
- **@storybook/addon-docs**: Auto-generated documentation
- **@storybook/addon-onboarding**: Getting started guide

---

## Coding Standards

### Documentation

- **Add JSDoc comments** to all functions, methods, classes, and interfaces
- **Do not add section marker comments** (e.g., `// ============` banners) - let structure speak for itself
- Keep comments meaningful - explain "why" not "what"

**Example - Good:**
```typescript
/**
 * Checks content for toxicity using TensorFlow.js model.
 * Loads model lazily on first use to reduce initial bundle size.
 * 
 * @param text - The text to analyze for toxic content
 * @returns Promise with safety status and flagged labels
 */
async checkContent(text: string): Promise<ContentCheckResult> {
  // Implementation
}
```

**Example - Bad:**
```typescript
// ============================================
// CONTENT SAFETY METHODS
// ============================================

// Check content
async checkContent(text: string) {
  // check the content here
}
```

### Backend API Documentation

Every Python backend module with HTTP endpoints MUST include:

1. **Endpoint Table in Module Docstring** - List all endpoints with method, path, parameters, and description

2. **Data Flow Diagram in Each Handler** - ASCII diagram showing request processing

**Example - Module Docstring with Endpoint Table:**

```python
"""Chat API Backend Server.

This module provides the HTTP API for the Genkit Chat application.

API Endpoints::

    ┌─────────┬──────────────────────┬────────────────────────────────────────┐
    │ Method  │ Path                 │ Description                            │
    ├─────────┼──────────────────────┼────────────────────────────────────────┤
    │ GET     │ /                    │ Health check, returns server status    │
    │ GET     │ /api/models          │ List available AI models by provider   │
    │ GET     │ /api/stream          │ SSE stream for chat responses          │
    │         │   ?message=<str>     │   - User message (required)            │
    │         │   &model=<str>       │   - Model ID (required)                │
    │         │   &history=<json>    │   - Conversation history (optional)    │
    │ POST    │ /api/chat            │ Non-streaming chat completion          │
    │ GET     │ /api/health          │ Detailed health check with uptime      │
    └─────────┴──────────────────────┴────────────────────────────────────────┘
"""
```

**Example - Handler with Data Flow Diagram:**

```python
@app.get("/api/stream")
async def stream_endpoint(message: str, model: str) -> StreamingResponse:
    """Stream AI responses via Server-Sent Events.

    Data Flow::

        Client Request
             │
             ▼
        ┌─────────────────┐
        │ Parse Parameters│  → Validate message & model
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Get Model Client│  → Look up model from registry
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Generate Stream │  → Call Genkit g.generate_stream()
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ Format as SSE   │  → Yield "data: {...}\\n\\n" chunks
        └────────┬────────┘
                 │
                 ▼
        StreamingResponse ──► Client

    Args:
        message: The user's chat message.
        model: The model ID (e.g., "googleai/gemini-2.0-flash").

    Returns:
        SSE stream with JSON chunks containing response text.
    """
```

### TypeScript

**Strict Typing is Required.** All code MUST pass strict TypeScript checks with zero errors.

- Use strict TypeScript settings (`strict: true` in tsconfig)
- **Never use implicit `any`** - always provide explicit types for:
  - Function parameters: `(v: boolean) => !v` not `(v) => !v`
  - Callback parameters: `.update((files: AttachedFile[]) => ...)` 
  - Arrow function parameters: `.filter((m: Model) => m.id === id)`
  - HTTP response handlers: `next: (response: ApiResponse) => {}`
- Prefer Angular signals over RxJS for component state
- Use `readonly` for immutable properties
- Prefer interfaces over type aliases for object shapes
- Use explicit return types on public methods: `sendMessage(): void`

**Common Patterns:**

```typescript
// Good - explicit types
this.files.update((files: AttachedFile[]) => [...files, newFile]);
this.enabled.update((v: boolean) => !v);
providers.forEach((provider: Provider) => { ... });
models.find((m: Model) => m.id === id);

// Bad - implicit any
this.files.update(files => [...files, newFile]);  // ❌
this.enabled.update(v => !v);  // ❌
providers.forEach(provider => { ... });  // ❌
```

**Documenting Type Loosening and Warning Suppression:**

When strict typing cannot be achieved due to external API limitations (e.g., Web Speech API, third-party libraries), you MUST:

1. **Add a comment explaining why** - Document the specific limitation
2. **Minimize the scope** - Use type assertions only where needed, not broadly
3. **Prefer inline types** - Use inline interface definitions over `any`

**Example - Acceptable Type Loosening:**

```typescript
// Web Speech API types are inconsistent across browsers and not fully 
// standardized in TypeScript libs. Using inline interface to avoid 
// complex type compatibility issues with SpeechRecognitionInterface.
private recognition: {
    continuous: boolean;
    interimResults: boolean;
    lang: string;
    start(): void;
    stop(): void;
    // ... other known properties
} | null = null;

// Type assertion necessary because SpeechRecognitionCtor returns 
// browser-specific interface that doesn't match our local type.
this.recognition = recognition as typeof this.recognition;
```

**Warning Suppression Policy:**

- **Never ignore warnings silently** - Every suppressed warning must have a comment
- **Try to fix first** - Only suppress after confirming no code fix is possible
- **Be specific** - Use `// @ts-expect-error: reason` not blanket `// @ts-ignore`


### SCSS/CSS

- Use CSS custom properties (variables) for theming
- Follow BEM-like naming for component styles
- Keep selectors shallow (max 3 levels)
- Use `var(--token-name)` for colors, not hardcoded values

## UI/UX Patterns

### 1. Input Toolbar Layout

The chat input uses a macOS-inspired design with clear visual hierarchy:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  [Attachments Row - horizontal scroll, macOS-style vertical cards]          │
├─────────────────────────────────────────────────────────────────────────────┤
│  [Textarea - auto-expanding, content safety highlighting]                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  [+] [Tools ▾] [Stream ⚡] [✓ MD] [✓ Safe]  ──  [Model ▾] [Mic/Send →]     │
│  └── Left actions ──────────────────────────── Right actions ──────────────┘
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Debouncing Strategy

| Action | Debounce | Rationale |
|--------|----------|-----------|
| Send button visibility | 150ms (hide only) | Show immediately on type, debounce hide to avoid flicker |
| Content safety check | 500ms | Expensive (TensorFlow.js), run after user stops typing |
| Model search filter | 0ms | Local filtering, instant feedback needed |

### 3. Animation Guidelines

**Slide Transitions (Mic ↔ Send button):**
```typescript
trigger('slideButton', [
  transition(':enter', [
    style({ opacity: 0, transform: 'translateX(10px)' }),
    animate('150ms ease-out', style({ opacity: 1, transform: 'translateX(0)' }))
  ]),
  transition(':leave', [
    animate('100ms ease-in', style({ opacity: 0, transform: 'translateX(-10px)' }))
  ])
])
```

**Key principles:**
- Use `overflow: hidden` on containers to prevent animation overflow
- Enter from right (positive X), exit to left (negative X) for natural flow
- Keep durations short (100-200ms) for responsiveness

### 4. File Attachments (macOS-style)

**Layout:** Vertical cards with icon/thumbnail on top, truncated filename + size below

**Configuration (CHAT_CONFIG):**
```typescript
export const CHAT_CONFIG = {
  maxAttachments: 10,
  maxFileSizeBytes: 1 * 1024 * 1024,  // 1MB
  allowedMimeTypes: ['image/*', 'application/pdf', 'text/*', ...]
};
```

**MIME Type Icons:**
```typescript
function getMimeTypeIcon(mimeType: string): string {
  if (mimeType.startsWith('image/')) return 'image';
  if (mimeType.startsWith('video/')) return 'videocam';
  if (mimeType.startsWith('audio/')) return 'audiotrack';
  if (mimeType === 'application/pdf') return 'picture_as_pdf';
  if (mimeType.includes('spreadsheet') || mimeType.includes('excel')) return 'table_chart';
  if (mimeType.includes('presentation') || mimeType.includes('powerpoint')) return 'slideshow';
  if (mimeType.includes('document') || mimeType.includes('word')) return 'description';
  if (mimeType.startsWith('text/')) return 'article';
  if (mimeType.includes('zip') || mimeType.includes('compressed')) return 'folder_zip';
  return 'insert_drive_file';
}
```

---

## Accessibility (a11y)

### Required ARIA Attributes

Every icon-only button MUST have an `aria-label`:

```html
<!-- Good -->
<button mat-icon-button aria-label="Send message" matTooltip="Send message">
  <mat-icon>send</mat-icon>
</button>

<!-- Bad - missing aria-label -->
<button mat-icon-button matTooltip="Send message">
  <mat-icon>send</mat-icon>
</button>
```

### Accessibility Checklist

When adding new UI components, ensure:

- [ ] All `<button>` with icons have `aria-label`
- [ ] All `<img>` have `alt` attributes
- [ ] All `<input>` and `<textarea>` have `aria-label` or associated `<label>`
- [ ] Interactive elements are keyboard-focusable (tab order)
- [ ] Color contrast meets WCAG AA standards (4.5:1 for text)
- [ ] Focus indicators are visible
- [ ] Dynamic content changes are announced to screen readers
- [ ] RTL languages display correctly

### Dynamic ARIA Labels

For buttons with state-dependent labels:
```html
<button [attr.aria-label]="isRecording ? 'Stop recording' : 'Start voice input'">
```

### Updating Accessibility

When modifying the UI:
1. Run accessibility audit: `pnpm exec playwright test --grep "accessibility"`
2. Test with keyboard navigation (Tab, Enter, Space, Arrow keys)
3. Test with screen reader (VoiceOver on macOS, NVDA on Windows)
4. Verify focus management after actions (e.g., focus returns to input after send)

---

## Internationalization (i18n)

### Supported Languages

| Code | Language | Direction | Status |
|------|----------|-----------|--------|
| en | English | LTR | ✅ Complete |
| es | Spanish | LTR | ✅ Complete |
| de | German | LTR | ✅ Complete |
| fr | French | LTR | ✅ Complete |
| zh | Chinese (Simplified) | LTR | ✅ Complete |
| hi | Hindi | LTR | ✅ Complete |
| ja | Japanese | LTR | ✅ Complete |
| ar | Arabic | RTL | ✅ Complete |
| ko | Korean | LTR | ✅ Complete |

### Adding a New Language

1. **Create translation file:** `src/assets/i18n/{code}.json`
   - Copy `en.json` as template
   - Translate all strings

2. **Register in LanguageService:** `src/app/core/services/language.service.ts`
   ```typescript
   export const SUPPORTED_LANGUAGES: Language[] = [
     // ... existing
     { code: 'ko', name: 'Korean', nativeName: '한국어', direction: 'ltr', flag: '🇰🇷' },
   ];
   ```

3. **Test RTL support** (for Arabic, Hebrew, etc.):
   - Verify layout flips correctly
   - Check text alignment
   - Test model selector chevron position

### Using Translations in Templates

```html
<!-- Simple translation -->
{{ 'chat.placeholder' | translate }}

<!-- With parameters -->
{{ 'errors.fileTooLarge' | translate:{ name: file.name, size: '1MB' } }}
```

### RTL Support

For RTL languages, the app automatically sets `dir="rtl"` on `<html>`. CSS handles layout adjustments:

```scss
[dir="rtl"] {
  .toolbar-left { order: 1; }
  .toolbar-right { order: 0; }
  .model-info { align-items: flex-start; }
}
```

---

## Content Safety

### Client-Side Toxicity Detection

Uses TensorFlow.js `@tensorflow-models/toxicity`:

```typescript
@Injectable({ providedIn: 'root' })
export class ContentSafetyService {
  private model: ToxicityClassifier | null = null;
  enabled = signal(true);
  
  async checkContent(text: string): Promise<{ safe: boolean; labels: string[] }> {
    if (!this.model) {
      this.model = await toxicity.load(0.9);  // 90% threshold
    }
    const predictions = await this.model.classify(text);
    const flagged = predictions.filter(p => p.results[0].match);
    return {
      safe: flagged.length === 0,
      labels: flagged.map(p => p.label)
    };
  }
}
```

### Visual Feedback for Flagged Content

```scss
.chat-input.content-flagged {
  text-decoration: underline wavy var(--error);
  text-decoration-skip-ink: none;
  text-underline-offset: 3px;
  color: var(--error);
}
```

### Testing Content Safety

Unit tests verify the service correctly flags known toxic content:

```typescript
it('should flag toxic content', async () => {
  const result = await service.checkContent('I hate you');
  expect(result.safe).toBeFalse();
  expect(result.labels).toContain('identity_attack');
});

it('should pass safe content', async () => {
  const result = await service.checkContent('Hello, how are you?');
  expect(result.safe).toBeTrue();
});
```

---

## Testing

### Test Structure

```
frontend/
├── src/app/
│   ├── core/services/
│   │   ├── content-safety.service.spec.ts  # Unit tests
│   │   ├── language.service.spec.ts
│   │   └── ...
│   └── features/chat/
│       └── chat.component.spec.ts
├── e2e/
│   ├── chat.spec.ts                        # Playwright E2E tests
│   └── accessibility.spec.ts
```

### Running Tests

```bash
# Frontend unit tests
cd frontend && pnpm test

# E2E tests with Playwright
cd frontend && pnpm exec playwright test

# Backend tests
cd backend && uv run pytest

# Run specific test file
pnpm test -- --include="**/content-safety.service.spec.ts"
```

### Testing Strategy: Logic-First Testing

The genkit-chat frontend uses a **logic-first testing pattern** that extracts pure logic from Angular components and tests it independently. This approach works around Angular's injection context requirements while maximizing test coverage.

**Why Logic-First?**

Angular services using `effect()`, `signal()`, and `inject()` require the Angular injection context, making direct instantiation in Vitest impossible. Instead, we:

1. **Test pure logic** - Extract algorithms, transformations, and business logic into testable functions
2. **Test data structures** - Verify interfaces and type contracts
3. **Test configuration** - Validate constants and settings
4. **Later: Component tests** - Use Angular TestBed for full component integration

**Example - Logic-First Testing:**

```typescript
// Instead of testing the service directly (which needs Angular):
// const service = new ThemeService();  // ❌ NG0203 error

// Test the pure logic:
const isDarkTheme = (theme: Theme, prefersDark: boolean): boolean => {
    if (theme === 'system') return prefersDark;
    return theme === 'dark';
};

it('should return true when theme is dark', () => {
    expect(isDarkTheme('dark', false)).toBe(true);  // ✓
});
```

### Coverage Improvement Plan

Current coverage is ~5.6%. Target is 80%. Here's the phased approach:

| Phase | Coverage Target | Focus |
|-------|-----------------|-------|
| Phase 1 (Done) | 5% | Pure logic tests, config, data structures |
| Phase 2 | 30% | Extract and test utility functions from components |
| Phase 3 | 50% | Add Angular TestBed integration for services |
| Phase 4 | 80% | Component tests with mocked dependencies |

**Files with 100% coverage already:**
- `app/core/config/chat.config.ts` - MIME type icons, config constants

**High-impact files to test next:**
- `app/core/services/chat.service.ts` - Extract queue logic
- `app/core/services/model.service.ts` - Extract filtering logic
- `app/shared/pipes/safe-markdown.pipe.ts` - Extract math substitutions

### Writing Unit Tests

Follow Angular testing conventions:

```typescript
describe('ContentSafetyService', () => {
  let service: ContentSafetyService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(ContentSafetyService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  // Test specific functionality
  it('should toggle enabled state', () => {
    expect(service.enabled()).toBeTrue();
    service.enabled.set(false);
    expect(service.enabled()).toBeFalse();
  });
});
```

### Writing Playwright E2E Tests

```typescript
import { test, expect } from '@playwright/test';

test.describe('Chat functionality', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should send a message and receive response', async ({ page }) => {
    const input = page.locator('textarea[aria-label="Chat message input"]');
    await input.fill('Hello!');
    await page.click('button[aria-label="Send message"]');
    
    // Wait for response
    await expect(page.locator('.message.assistant')).toBeVisible({ timeout: 30000 });
  });

  test('should show content safety warning for toxic input', async ({ page }) => {
    const input = page.locator('textarea[aria-label="Chat message input"]');
    await input.fill('I hate you');
    
    // Wait for debounced safety check
    await page.waitForTimeout(600);
    
    await expect(input).toHaveClass(/content-flagged/);
  });
});
```

### Accessibility Testing with Playwright

```typescript
test('should have no accessibility violations', async ({ page }) => {
  await page.goto('/');
  
  // Check for missing ARIA labels on buttons
  const issues = await page.evaluate(() => {
    const buttons = document.querySelectorAll('button');
    return [...buttons].filter(b => 
      !b.hasAttribute('aria-label') && 
      !b.textContent?.trim()
    ).length;
  });
  
  expect(issues).toBe(0);
});
```

---

## Roadmap Maintenance

### Updating the Roadmap

The project roadmap is maintained in the knowledge base. When completing features:

1. **Mark completed items** with ✅
2. **Add new planned features** as they're identified
3. **Update percentages** for phase completion
4. **Document blockers** if any

### Current Roadmap Status

Track progress in these areas:

| Area | Status | Priority |
|------|--------|----------|
| Core Chat | ✅ Complete | P0 |
| Multi-model Support | ✅ Complete | P0 |
| Streaming Responses | ✅ Complete | P0 |
| File Attachments | ✅ Complete | P1 |
| Voice Input | ✅ Complete | P1 |
| Content Safety | ✅ Complete | P1 |
| Internationalization | 🔄 In Progress | P1 |
| Compare Mode | ✅ Complete | P2 |
| Persistent History | 🔄 Planned | P2 |
| Shareable Chats | 🔄 Planned | P3 |

---

## Performance Optimizations

### 1. Lazy Loading

```typescript
// In app.routes.ts
{
  path: 'compare',
  loadComponent: () => import('./features/compare/compare.component')
    .then(m => m.CompareComponent)
}
```

### 2. Signal-Based Reactivity

Prefer Angular signals for component state:
```typescript
// Reactive state
showSendButton = signal(false);
contentFlagged = signal(false);

// Computed values
messageCount = computed(() => this.chatService.messages().length);
```

### 3. OnPush Change Detection

```typescript
@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  // ...
})
```

---

## Troubleshooting

### Build Warnings

**CommonJS dependency warnings (TensorFlow.js):**
```
▲ [WARNING] Module 'seedrandom' used by '@tensorflow/tfjs-core' is not ESM
```
These are safe to ignore - TensorFlow.js uses CommonJS internally.

### Animation Overflow

If buttons animate outside their container:
```scss
.container {
  overflow: hidden;
  position: relative;
}
```

### Model Selector Alignment

Ensure chevron is on the right:
```scss
.model-select-btn {
  display: flex;
  
  .model-info { order: 0; }
  .dropdown-icon { order: 1; }
}
```

### i18n Translation Not Loading

1. Check translation file exists: `src/assets/i18n/{lang}.json`
2. Verify JSON syntax is valid
3. Check network tab for 404 errors
4. Ensure `TranslateModule` is imported in component

---

## @aspect/genkit-ui Library

The `@aspect/genkit-ui` library is a pnpm workspace package containing reusable Angular components for AI-powered applications. All portable components live in `testapps/genkit-ui/`.

### Library Structure

```
genkit-ui/
├── package.json           # @aspect/genkit-ui
├── tsconfig.json
├── .storybook/            # Storybook configuration
│   ├── main.ts
│   └── preview.ts
└── src/
    ├── index.ts           # Main entry point
    ├── chat/              # Chat components
    │   ├── index.ts       # Chat module exports
    │   ├── chat-box/      # Main container component
    │   ├── chat-input/
    │   ├── message-list/
    │   ├── welcome-screen/
    │   ├── prompt-queue/
    │   └── model-selector/
    └── theme/             # Theme components
        ├── index.ts       # Theme module exports
        ├── styles.css     # Default theme CSS
        ├── language-selector/
        └── theme-selector/
```

### Component Selectors

All library components use the `genkit-` prefix:

| Component | Selector |
|-----------|----------|
| ChatBoxComponent | `genkit-chat-box` |
| ChatInputComponent | `genkit-chat-input` |
| MessageListComponent | `genkit-message-list` |
| WelcomeScreenComponent | `genkit-welcome-screen` |
| PromptQueueComponent | `genkit-prompt-queue` |
| ModelSelectorComponent | `genkit-model-selector` |
| LanguageSelectorComponent | `genkit-language-selector` |
| ThemeSelectorComponent | `genkit-theme-selector` |

### Using the Library

1. **Add as workspace dependency** in `package.json`:
   ```json
   {
     "dependencies": {
       "@aspect/genkit-ui": "workspace:*"
     }
   }
   ```

2. **Import components**:
   ```typescript
   // Import the complete chat box
   import { ChatBoxComponent } from '@aspect/genkit-ui/chat';
   
   // Or import individual components
   import { 
     ChatInputComponent, 
     MessageListComponent,
     Model, 
     Provider 
   } from '@aspect/genkit-ui/chat';
   
   // Theme components
   import { 
     ThemeSelectorComponent, 
     LanguageSelectorComponent 
   } from '@aspect/genkit-ui/theme';
   ```

3. **Use in templates**:
   ```html
   <!-- Complete chat interface with self-managed voice -->
   <genkit-chat-box
     [messages]="messages"
     [isLoading]="isLoading"
     [providers]="providers"
     [selectedModel]="selectedModel"
     [selfManagedVoice]="true"
     (send)="onSend($event)"
     (modelSelected)="onModelChange($event)" />
   
   <!-- Or use individual components -->
   <genkit-message-list [messages]="messages" />
   <genkit-chat-input (send)="onSend($event)" />
   ```

### Running Storybook

```bash
cd testapps/genkit-ui
pnpm install
pnpm run storybook
```

### ChatBoxComponent Features

The `ChatBoxComponent` is the main shareable chat interface:

- **Voice Input Modes:**
  - `selfManagedVoice=true`: Built-in Web Speech API
  - `selfManagedVoice=false`: Parent controls voice via inputs/outputs
  
- **Settings Management:**
  - Streaming toggle
  - Markdown rendering toggle
  - Content safety toggle
  
- **Model Selection:**
  - Searchable dropdown
  - Provider grouping
  - Recent models

---

## Component Portability & Library Extraction

This section documents the architectural patterns that make our components portable and reusable across demo applications. These patterns enable components to be extracted into a shared component library.

### Design Principles

We follow the **Self-Contained Component Pattern** which ensures components work in any Angular application without external dependencies on global styles, services, or configurations.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Self-Contained Component Pattern                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────┐     ┌───────────────────┐     ┌──────────────────┐  │
│  │   CSS Variables   │     │  Input-Based      │     │  Output-Based    │  │
│  │   with Fallbacks  │     │  Configuration    │     │  Side Effects    │  │
│  └─────────┬─────────┘     └─────────┬─────────┘     └────────┬─────────┘  │
│            │                         │                        │            │
│            ▼                         ▼                        ▼            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Portable Component                              │   │
│  │                                                                     │   │
│  │  • Works without global styles                                      │   │
│  │  • Accepts all configuration via inputs                             │   │
│  │  • Emits events instead of calling services directly               │   │
│  │  • Includes inline documentation                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1. CSS Variable Fallback Pattern

Every component defines internal CSS variables with fallback defaults. This ensures the component looks correct even without a global theme.

```scss
// Component styles
:host {
  display: block;

  // Internal variables with fallbacks to global or default values
  --_primary: var(--primary, #4285f4);
  --_on-primary: var(--on-primary, #ffffff);
  --_surface-container: var(--surface-container, #f0f4f9);
  --_on-surface: var(--on-surface, #1a1c1e);
  --_on-surface-variant: var(--on-surface-variant, #5f6368);
  --_error: var(--error, #ba1a1a);
}

// Use internal variables in styles
.button {
  background: var(--_primary);
  color: var(--_on-primary);
}

.container {
  background: var(--_surface-container);
  color: var(--_on-surface);
}
```

**Key Points:**
- Prefix internal variables with `--_` to avoid conflicts
- Use `var(--global, #default)` syntax for fallbacks
- Choose sensible defaults that look good out-of-the-box
- Follow Material Design 3 color token naming

### 2. Input-Based Configuration

Components accept all configuration via `@input()` rather than relying on injected services or global configs.

**Before (Service-Dependent):**
```typescript
// ❌ Bad: Depends on external service
import { LanguageService } from '../../services/language.service';

@Component({ ... })
export class LanguageSelectorComponent {
  private languageService = inject(LanguageService);
  
  get languages() {
    return this.languageService.languages;
  }
}
```

**After (Self-Contained):**
```typescript
// ✅ Good: Configuration via inputs
@Component({ ... })
export class LanguageSelectorComponent {
  /** List of available languages - passed by parent */
  languages = input<Language[]>(DEFAULT_LANGUAGES);
  
  /** Currently selected language code */
  selectedLanguage = input<string>('en');
  
  /** Emits when user selects a language */
  languageSelected = output<string>();
}
```

### 3. Output-Based Side Effects

Components emit events and let parents handle side effects like storage, API calls, or navigation.

**Before:**
```typescript
// ❌ Bad: Component handles side effects directly
selectTheme(mode: ThemeMode) {
  this.themeService.setTheme(mode);
  localStorage.setItem('theme', mode);
  document.body.classList.toggle('dark', mode === 'dark');
}
```

**After:**
```typescript
// ✅ Good: Emit event, let parent handle side effects
themeChanged = output<ThemeMode>();

selectTheme(mode: ThemeMode) {
  this.themeChanged.emit(mode);
}
```

### 4. Configurable Assets

Replace hardcoded asset paths with configurable inputs.

```typescript
// ❌ Bad: Hardcoded path
<img src="genkit-logo.png" alt="Genkit">

// ✅ Good: Configurable via input
avatarUrl = input<string>('genkit-logo.png');
avatarAlt = input<string>('Genkit');

// In template
<img [src]="avatarUrl()" [alt]="avatarAlt()">
```

### 5. Component Documentation Pattern

Every portable component includes comprehensive JSDoc documentation:

```typescript
/**
 * LanguageSelectorComponent - Self-contained language dropdown selector.
 * 
 * This component is responsible for:
 * - Displaying the currently selected language
 * - Searchable dropdown for language selection
 * - Support for RTL languages
 * 
 * Portability:
 * - This component is SELF-CONTAINED with CSS fallback variables
 * - Requires: @angular/material
 * - Optional: @ngx-translate/core
 * 
 * Component Architecture::
 * 
 *     ┌─────────────────────────────────────────────────────────────────┐
 *     │                    LanguageSelectorComponent                    │
 *     ├─────────────────────────────────────────────────────────────────┤
 *     │  Inputs:                                                        │
 *     │  - languages: Language[]                                        │
 *     │  - selectedLanguage: string                                     │
 *     │                                                                 │
 *     │  Outputs:                                                       │
 *     │  - languageSelected: EventEmitter<string>                       │
 *     └─────────────────────────────────────────────────────────────────┘
 */
```

### Portable Components Inventory

| Component | Location | Status |
|-----------|----------|--------|
| **ChatInputComponent** | `features/chat/components/chat-input/` | ✅ Portable |
| **MessageListComponent** | `features/chat/components/message-list/` | ✅ Portable |
| **WelcomeScreenComponent** | `features/chat/components/welcome-screen/` | ✅ Portable |
| **PromptQueueComponent** | `features/chat/components/prompt-queue/` | ✅ Portable |
| **ModelSelectorComponent** | `features/chat/components/model-selector/` | ✅ Portable |
| **LanguageSelectorComponent** | `shared/components/language-selector/` | ✅ Portable |
| **ThemeSelectorComponent** | `shared/components/theme-selector/` | ✅ Portable |

### Library Extraction Preparation

When extracting components to a shared library:

1. **Create a new library project:**
   ```bash
   ng generate library @genkit/ui-components
   ```

2. **Move component folders** to the library's `src/lib/` directory

3. **Update barrel exports** in `public-api.ts`:
   ```typescript
   // public-api.ts
   export * from './lib/language-selector/language-selector.component';
   export * from './lib/theme-selector/theme-selector.component';
   export * from './lib/chat-input/chat-input.component';
   // ...
   ```

4. **Define peer dependencies** in `package.json`:
   ```json
   {
     "name": "@genkit/ui-components",
     "peerDependencies": {
       "@angular/core": "^19.0.0",
       "@angular/material": "^19.0.0",
       "@ngx-translate/core": "^16.0.0"
     }
   }
   ```

5. **Provide a theme SCSS file** for applications that want consistent theming:
   ```scss
   // _theme.scss - exported with the library
   :root {
     --primary: #4285f4;
     --on-primary: #ffffff;
     // ... all design tokens
   }
   ```

### Using Portable Components in Other Apps

```typescript
// In another demo app
import { 
  LanguageSelectorComponent,
  ThemeSelectorComponent,
  ChatInputComponent,
  DEFAULT_LANGUAGES
} from '@genkit/ui-components';

@Component({
  imports: [
    LanguageSelectorComponent,
    ThemeSelectorComponent,
    ChatInputComponent
  ],
  template: `
    <app-language-selector 
      [languages]="languages"
      [selectedLanguage]="currentLang"
      (languageSelected)="onLanguageChange($event)" />
    
    <app-theme-selector 
      [theme]="currentTheme"
      mode="toggle"
      (themeChanged)="onThemeChange($event)" />
    
    <app-chat-input
      [disabled]="false"
      (send)="onSend($event)" />
  `
})
export class MyComponent {
  languages = DEFAULT_LANGUAGES;
  // ...
}
```

---

## Git Commit Guidelines

- Use conventional commits: `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`
- Scope by area: `feat(chat):`, `fix(a11y):`, `docs(i18n):`, `test(safety):`
- Keep messages concise but descriptive
- Reference issues when applicable: `fix(chat): resolve streaming bug (#123)`

### Examples

```
feat(i18n): add Japanese translation
fix(a11y): add missing aria-labels to toolbar buttons
test(safety): add unit tests for toxicity detection
docs: update GEMINI.md with testing guidelines
refactor(chat): debounce content safety checks
```

