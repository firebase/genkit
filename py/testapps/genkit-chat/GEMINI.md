# Genkit Chat - Development Guidelines

This document captures learnings, patterns, and best practices from developing the Genkit Chat application.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Genkit Chat Architecture                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  Frontend (Angular 19)                                                      │
│  ├── ChatComponent       - Main chat interface with input/messages          │
│  ├── CompareComponent    - Side-by-side model comparison                    │
│  ├── Services                                                               │
│  │   ├── ChatService     - Message management, streaming, queue             │
│  │   ├── ModelsService   - Model list, selection, categorization            │
│  │   ├── SpeechService   - Voice input via Web Speech API                   │
│  │   ├── ContentSafetyService - Client-side toxicity detection              │
│  │   ├── ThemeService    - Dark/light/system theme management               │
│  │   └── AuthService     - Demo mode user management                        │
│  └── Utilities                                                              │
│      ├── SafeMarkdownPipe - DOMPurify + marked for safe rendering           │
│      └── getMimeTypeIcon  - Semantic file type icons                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  Backend (Python + Robyn)                                                   │
│  ├── main.py             - Routes, SSE streaming, model registry            │
│  ├── Genkit Integration  - Flows, tools, prompts                            │
│  └── Multi-provider      - Google AI, Vertex AI, Ollama                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

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

### Checklist

- [ ] All `<button>` with icons have `aria-label`
- [ ] All `<img>` have `alt` attributes
- [ ] All `<input>` and `<textarea>` have `aria-label` or associated `<label>`
- [ ] Interactive elements are keyboard-focusable (tab order)
- [ ] Color contrast meets WCAG AA standards
- [ ] Focus indicators are visible

### Dynamic ARIA Labels

For buttons with state-dependent labels:
```html
<button [attr.aria-label]="isRecording ? 'Stop recording' : 'Start voice input'">
```

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

## Internationalization (i18n)

### Supported Languages

| Code | Language | Direction |
|------|----------|-----------|
| en-US | English (US) | LTR |
| en-GB | English (UK) | LTR |
| es | Spanish | LTR |
| de | German | LTR |
| fr | French | LTR |
| zh | Chinese (Simplified) | LTR |
| hi | Hindi | LTR |
| ar | Arabic | RTL |
| ja | Japanese | LTR |
| ko | Korean | LTR |

### Implementation with ngx-translate

1. **Install dependencies:**
   ```bash
   pnpm add @ngx-translate/core @ngx-translate/http-loader
   ```

2. **Create translation files:** `src/assets/i18n/{lang}.json`

3. **Service setup:**
   ```typescript
   export function HttpLoaderFactory(http: HttpClient) {
     return new TranslateHttpLoader(http, './assets/i18n/', '.json');
   }
   ```

4. **Usage in templates:**
   ```html
   {{ 'chat.placeholder' | translate }}
   ```

5. **Language selector in sidebar:**
   ```html
   <button mat-list-item [matMenuTriggerFor]="langMenu">
     <mat-icon>language</mat-icon>
     <span>{{ currentLang }}</span>
   </button>
   ```

### RTL Support

For RTL languages (Arabic, Hebrew):
```scss
[dir="rtl"] {
  .toolbar-left { order: 1; }
  .toolbar-right { order: 0; }
  .model-info { align-items: flex-start; }
}
```

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

## Testing

### Running Tests

```bash
# Frontend unit tests
cd frontend && pnpm test

# E2E tests with Playwright
cd frontend && pnpm exec playwright test

# Backend tests
cd backend && uv run pytest
```

### Accessibility Testing

```javascript
// In Playwright test
test('accessibility audit', async ({ page }) => {
  await page.goto('/');
  
  // Check for missing ARIA labels
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

## Common Patterns

### 1. Tooltip + ARIA Label Combo

```html
<button mat-icon-button 
        aria-label="Add files"
        matTooltip="Add files">
  <mat-icon>add</mat-icon>
</button>
```

### 2. Conditional Disabled State

```html
<button [disabled]="!canSend()"
        [attr.aria-disabled]="!canSend()">
  Send
</button>
```

### 3. Focus Management

```typescript
ngAfterViewInit() {
  // Auto-focus chat input
  this.chatTextarea.nativeElement.focus();
}

sendMessage() {
  // Restore focus after sending
  this.chatTextarea.nativeElement.focus();
}
```

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

## Git Commit Guidelines

- Use conventional commits: `feat:`, `fix:`, `docs:`, `style:`, `refactor:`
- Scope by area: `feat(chat):`, `fix(a11y):`, `docs(i18n):`
- Keep messages concise but descriptive
