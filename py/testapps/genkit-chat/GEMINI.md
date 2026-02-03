# Genkit Chat - Development Guidelines

This document captures learnings, patterns, and best practices from developing the Genkit Chat application.

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

### TypeScript

- Use strict TypeScript settings (`strict: true` in tsconfig)
- Prefer Angular signals over RxJS for component state
- Use `readonly` for immutable properties
- Prefer interfaces over type aliases for object shapes

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
