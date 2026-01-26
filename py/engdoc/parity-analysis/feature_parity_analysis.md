# Genkit Feature Parity Analysis: JS vs Python

This document analyzes feature gaps and behavioral differences between the JavaScript (canonical) implementation and the Python implementation of Genkit.

---

## Executive Summary

| Category | JS | Python | Gap |
|----------|-----|--------|-----|
| Plugins | 18 | 13 | 5 missing |
| Core API Methods | ~45 | ~35 | 10+ missing |
| Session/Chat | ✅ | ❌ | **Critical Gap** |
| Background Actions | ✅ | ❌ | **Critical Gap** |
| Dynamic Action Provider | ✅ | ❌ | Significant Gap |

---

## 1. Missing Core Features

### 1.1 Session & Chat (Critical Gap)

> [!CAUTION]
> Python lacks stateful conversation management entirely.

**JS has:**
- [Session](/js/ai/src/session.ts) class with:
  - `updateState(data)` - Update session state
  - `updateMessages(thread, messages)` - Manage thread history
  - `chat()` - Create chat sessions with thread support
  - `run(fn)` - Execute within session context
  - `toJSON()` - Serialize session
- [Chat](/js/ai/src/chat.ts) class with:
  - `send(options)` - Send message with history
  - `sendStream(options)` - Streaming with history
  - `messages()` - Get conversation history
  - Thread management (multiple conversations per session)
- `SessionStore` interface for persistence
- `ai.createSession()` and `ai.chat()` veneer methods

**Python has:** Nothing equivalent. No way to maintain conversation history across multiple `generate()` calls without manual message management.

---

### 1.2 Background Actions & Background Models (Critical Gap)

> [!CAUTION]
> Python lacks long-running operation support.

**JS has:**
- [BackgroundAction](/js/core/src/background-action.ts):
  - `start(input, options)` - Start background operation
  - `check(operation)` - Check operation status
  - `cancel(operation)` - Cancel running operation
- `Operation` type with `id`, `done`, `output`, `error`, `metadata`
- `defineBackgroundAction()` - Register background actions
- `defineBackgroundModel()` - Register models that return operations (e.g., video generation)
- [ai.checkOperation()](/js/genkit/src/genkit.ts#L866-L886) - Veneer method

**Python has:** Nothing. Cannot use models like Veo that return operations for later retrieval.

---

### 1.3 Dynamic Action Provider (Significant Gap)

**JS has:**
- [DynamicActionProvider](/js/core/src/dynamic-action-provider.ts):
  - Caching with configurable TTL
  - `invalidateCache()` - Force refresh
  - `getAction(type, name)` - Resolve action dynamically
  - `listActionMetadata(type, name)` - List available actions
  - Used by MCP plugin for dynamic tool discovery

**Python has:** Nothing. The MCP plugin must pre-register all actions.

---

### 1.4 Missing Veneer Methods

| JS Method | Description | Python Status |
|-----------|-------------|---------------|
| `ai.createSession()` | Create stateful session | ❌ Missing |
| `ai.chat()` | Quick chat session | ❌ Missing |
| `ai.currentSession()` | Get active session | ❌ Missing |
| `ai.checkOperation()` | Check background op | ❌ Missing |
| `ai.defineSimpleRetriever()` | Simplified retriever | ❌ Missing |
| `ai.defineBackgroundModel()` | Background model | ❌ Missing |
| `ai.defineDynamicActionProvider()` | DAP registration | ❌ Missing |
| `ai.defineJsonSchema()` | JSON Schema registration | ❌ Missing |
| `ai.dynamicTool()` | Unregistered tools | ❌ Missing |
| `ai.run()` | Named trace step | ❌ Missing |
| `ai.embedMany()` | Bulk embedding | ❌ Missing |
| `ai.index()` | Indexing veneer | ❌ Missing |

---

## 2. Plugin Gaps

### 2.1 Missing Plugins (5)

| JS Plugin | Description | Priority |
|-----------|-------------|----------|
| `@genkit-ai/checks` | Google Checks for safety | Medium |
| `@genkit-ai/chroma` | Chroma vector store | Low |
| `@genkit-ai/cloud-sql-pg` | Cloud SQL PostgreSQL | Medium |
| `@genkit-ai/pinecone` | Pinecone vector store | Medium |
| `@genkit-ai/langchain` | LangChain integration | Low |
| `@genkit-ai/next` | Next.js integration | N/A (Python irrelevant) |
| `@genkit-ai/express` | Express integration | N/A (Flask exists) |
| `@genkit-ai/googleai` | Legacy Google AI | Being deprecated |

### 2.2 Plugin Feature Gaps

#### Vertex AI Plugin

| Feature | JS | Python |
|---------|-----|--------|
| Gemini Models | ✅ | ✅ |
| Imagen Models | ✅ | ✅ (via google-genai) |
| Embedders | ✅ | Limited |
| Rerankers | ✅ | ❌ Missing |
| Context Caching | ✅ | ❌ Missing |
| Vector Search | ✅ | ✅ |
| Evaluation | ✅ | ❌ Missing |
| Model Garden | ✅ | ✅ |

#### Google GenAI Plugin

| Feature | JS | Python |
|---------|-----|--------|
| Gemini Models | ✅ | ✅ |
| Imagen Models | ✅ | ✅ |
| Embedders | ✅ | ✅ |
| Context Caching | ✅ | ❌ Missing |
| Live/Realtime | ✅ | ❌ Missing |

---

## 2.3 Prompt API (`ai.prompt()` / `ai.definePrompt()`)

### JS API

```typescript
// Lookup prompt by name
ai.prompt<I, O, CustomOptions>(name: string, options?: { variant?: string })
  : ExecutablePrompt<I, O, CustomOptions>

// Define prompt with config + template/function
ai.definePrompt({
  name: string,
  model?: string,
  input?: { schema: z.ZodSchema },
  output?: { schema: z.ZodSchema },
  config?: GenerationConfig,
  messages?: string | ((input) => Message[]),  // Template string or function
  tools?: ToolRef[],
}, templateOrFn?)
```

**Key JS Features:**
- Generic type parameters `<I, O, CustomOptions>` for type-safe input/output
- `messages` can be a Dotprompt template string
- Returns `ExecutablePrompt` with `()` call and `.stream()` method
- Automatic `.prompt` file loading from `promptDir`

### Python API

```python
# Lookup prompt by name
await ai.prompt(name: str, variant: str | None = None)
  -> ExecutablePrompt

# Define prompt with explicit kwargs
ai.define_prompt(
    name: str | None = None,
    variant: str | None = None,
    model: str | None = None,
    config: GenerationCommonConfig | dict | None = None,
    description: str | None = None,
    input_schema: type | dict | str | None = None,
    system: str | Part | list[Part] | Callable | None = None,
    prompt: str | Part | list[Part] | Callable | None = None,
    messages: str | list[Message] | Callable | None = None,
    output_format: str | None = None,
    output_content_type: str | None = None,
    output_instructions: bool | str | None = None,
    output_schema: type | dict | str | None = None,
    output_constrained: bool | None = None,
    max_turns: int | None = None,
    return_tool_requests: bool | None = None,
    tools: list[str] | None = None,
    tool_choice: ToolChoice | None = None,
    use: list[ModelMiddleware] | None = None,
    docs: list[DocumentData] | Callable | None = None,
    metadata: dict | None = None,
)
```

**Key Differences:**

| Feature | JS | Python | Notes |
|---------|-----|--------|-------|
| Type generics | ✅ `<I, O, CustomOptions>` | ❌ | No typed input/output |
| Sync lookup | ✅ Sync | ❌ `async` | Python requires `await` |
| Separate `system` param | ❌ | ✅ | Python has dedicated system param |
| Separate `prompt` param | ❌ | ✅ | Python can pass prompt separately |
| `output_*` params | Combined in `output` | ✅ Explicit | More granular in Python |
| `docs` param | ❌ | ✅ | Python has docs for RAG |
| `max_turns` | In config | ✅ Direct | Easier access in Python |
| Template strings | ✅ Dotprompt | ✅ Handlebars | Both support templates |
| `.prompt` file loading | ✅ Auto | ✅ Auto | Both support file loading |

### ExecutablePrompt Comparison

**JS:**
```typescript
const result = await myPrompt({ name: 'value' });
const { stream, response } = await myPrompt.stream({ name: 'value' });
```

**Python:**
```python
result = await my_prompt(name='value')
stream, response = await my_prompt.stream(name='value')
```

> [!NOTE]
> Python's prompt API is **more complete** in some ways (explicit `system`, `docs`, `max_turns`), but lacks the type safety of JS generics.

---

## 2.4 Complete API Surface Comparison

### Method Parity Matrix

| Method | JS | Python | Notes |
|--------|-----|--------|-------|
| **Core Generation** |
| `generate()` | ✅ | ✅ | Both support |
| `generateStream()` | ✅ | ✅ `generate_stream()` | Name differs |
| `checkOperation()` | ✅ | ❌ | Python missing (needed for Veo) |
| **Prompts** |
| `prompt()` | ✅ Sync | ✅ `async` | Python requires await |
| `definePrompt()` | ✅ | ✅ `define_prompt()` | Both support |
| **Flows** |
| `defineFlow()` | ✅ | ✅ `@ai.flow()` decorator | Python uses decorator |
| `run()` | ✅ | ❌ | Step tracing missing in Python |
| `currentContext()` | ✅ | ❌ | Python missing |
| **Tools** |
| `defineTool()` | ✅ | ✅ `@ai.tool()` decorator | Python uses decorator |
| `dynamicTool()` | ✅ | ❌ | Python missing |
| **Models** |
| `defineModel()` | ✅ | ✅ `define_model()` | Both support |
| `defineBackgroundModel()` | ✅ | ❌ | Python missing |
| **RAG** |
| `retrieve()` | ✅ | ✅ | Both support |
| `index()` | ✅ | ✅ | Both support |
| `defineRetriever()` | ✅ | ✅ `define_retriever()` | Both support |
| `defineSimpleRetriever()` | ✅ | ❌ | Python missing |
| `defineIndexer()` | ✅ | ✅ `define_indexer()` | Both support |
| **Embeddings** |
| `embed()` | ✅ | ✅ | Both support |
| `embedMany()` | ✅ | ❌ | Python missing |
| `defineEmbedder()` | ✅ | ✅ `define_embedder()` | Both support |
| **Reranking** |
| `rerank()` | ✅ | ✅ | Both support |
| `defineReranker()` | ✅ | ✅ `define_reranker()` | Both support |
| **Evaluation** |
| `evaluate()` | ✅ | ✅ | Both support |
| `defineEvaluator()` | ✅ | ✅ `define_evaluator()` | Both support |
| — | — | ✅ `define_batch_evaluator()` | Python extra |
| **Schemas** |
| `defineSchema()` | ✅ | ✅ `define_schema()` | Both support |
| `defineJsonSchema()` | ✅ | ❌ | Python missing |
| **Templates** |
| `defineHelper()` | ✅ | ✅ `define_helper()` | Both support |
| `definePartial()` | ✅ | ✅ `define_partial()` | Both support |
| **Dynamic Actions** |
| `defineDynamicActionProvider()` | ✅ | ❌ | Python missing (MCP) |
| **Formats** |
| — | — | ✅ `define_format()` | Python extra |
| **Resources** |
| — | — | ✅ `define_resource()` | Python extra |
| **Session/Chat** |
| `createSession()` | ✅ | ❌ | Python missing |
| `loadSession()` | ✅ | ❌ | Python missing |
| `chat()` | ✅ | ❌ | Python missing |
| **Lifecycle** |
| `configure()` | ✅ | ❌ | Python uses constructor |
| `stopServers()` | ✅ | ❌ | Python missing |
| `run_main()` | ❌ | ✅ | Python extra |

### Critical Missing APIs (Python)

| API | Use Case | Priority |
|-----|----------|----------|
| `checkOperation()` | Poll long-running ops (Veo, Imagen) | P0 |
| `createSession()`/`loadSession()` | Stateful multi-turn | P0 |
| `chat()` | Simple chat interface | P0 |
| `run()` | Step tracing in flows | P1 |
| `dynamicTool()` | Runtime tool creation | P1 |
| `defineBackgroundModel()` | Long-running models | P1 |
| `defineDynamicActionProvider()` | MCP host support | P2 |
| `currentContext()` | Auth/context access | P2 |
| `embedMany()` | Batch embedding | P2 |
| `defineSimpleRetriever()` | Quick retriever setup | P3 |
| `defineJsonSchema()` | Register JSON schemas | P3 |

### Python Extras (Not in JS)

| API | Use Case |
|-----|----------|
| `define_batch_evaluator()` | Evaluate entire dataset at once |
| `define_format()` | Register custom output formats |
| `define_resource()` | Register MCP resources |
| `run_main()` | Dev server entry point |

---

## 2.5 Telemetry and Tracing Comparison

### Tracing Infrastructure

| Feature | JS | Python | Notes |
|---------|-----|--------|-------|
| **OpenTelemetry SDK** | ✅ `@opentelemetry/sdk-node` | ✅ `opentelemetry-sdk` | Both use OTel |
| **TracerProvider** | ✅ | ✅ | Both configure |
| **SimpleSpanProcessor** | ✅ (dev) | ✅ (dev) | Same pattern |
| **BatchSpanProcessor** | ✅ (prod) | ✅ (prod) | Same pattern |
| **RealtimeSpanProcessor** | ✅ | ✅ | Parity achieved |
| **Configurable via env** | ✅ `GENKIT_ENABLE_REALTIME_TELEMETRY` | ✅ | Parity achieved |

### Realtime Tracing

> [!NOTE]
> Both JS and Python now have `RealtimeSpanProcessor` that exports spans on **both start AND end**, enabling live trace visualization during development.

**JS RealtimeSpanProcessor:**
```typescript
class RealtimeSpanProcessor implements SpanProcessor {
  onStart(span: Span): void {
    // Export immediately for real-time updates
    this.exporter.export([span], () => {});
  }
  onEnd(span: ReadableSpan): void {
    // Export completed span
    this.exporter.export([span], () => {});
  }
}
```

**Python:** Equivalent implementation in `genkit.core.trace.realtime_processor`:
```python
class RealtimeSpanProcessor(SpanProcessor):
    def on_start(self, span: Span, parent_context: Context | None = None) -> None:
        # Export immediately for real-time updates
        self._exporter.export([span])

    def on_end(self, span: ReadableSpan) -> None:
        # Export completed span
        self._exporter.export([span])
```

### Span Exporters

| Exporter | JS | Python | Notes |
|----------|-----|--------|-------|
| **TelemetryServerExporter** | ✅ `TraceServerExporter` | ✅ `TelemetryServerSpanExporter` | Both have |
| **GCP Cloud Trace** | ✅ | ✅ | Both via plugins |
| **AdjustingTraceExporter** | ✅ (redacts content) | ✅ | Parity achieved |
| **Custom exporter API** | ✅ | ✅ `add_custom_exporter()` | Both support |

### Telemetry Configuration API

| API | JS | Python | Notes |
|-----|-----|--------|-------|
| `enableTelemetry(config)` | ✅ | ❌ | Python auto-configures |
| `flushTracing()` | ✅ | ✅ `ai.flush_tracing()` | Parity achieved |
| `cleanUpTracing()` | ✅ | ❌ | Python no cleanup |
| `TelemetryConfig` type | ✅ `Partial<NodeSDKConfiguration>` | ❌ | Python untyped |

### Metrics

| Metric | JS (GCP Plugin) | Python (GCP Plugin) |
|--------|----------------|---------------------|
| `genkit/ai/generate/requests` | ✅ | ✅ |
| `genkit/ai/generate/failures` | ✅ | ✅ |
| `genkit/ai/generate/latency` | ✅ | ✅ |
| `genkit/ai/generate/input/tokens` | ✅ | ✅ |
| `genkit/ai/generate/output/tokens` | ✅ | ✅ |
| `genkit/ai/generate/input/characters` | ✅ | ✅ |
| `genkit/ai/generate/output/characters` | ✅ | ✅ |
| `genkit/ai/generate/input/images` | ✅ | ✅ |
| `genkit/ai/generate/output/images` | ✅ | ✅ |
| `genkit/ai/generate/input/videos` | ✅ | ✅ |
| `genkit/ai/generate/output/videos` | ✅ | ✅ |
| `genkit/ai/generate/input/audio` | ✅ | ✅ |
| `genkit/ai/generate/output/audio` | ✅ | ✅ |

> [!NOTE]
> **Metrics parity is good!** Both JS and Python google-cloud plugins record the same AI monitoring metrics.

### GCP Plugin Comparison

| Feature | JS `@genkit-ai/google-cloud` | Python `google-cloud` |
|---------|------------------------------|----------------------|
| **Cloud Trace export** | ✅ | ✅ |
| **Cloud Metrics export** | ✅ | ✅ |
| **Automatic instrumentation** | ✅ (Pino, Winston) | ❌ |
| **Span adjustment/redaction** | ✅ `AdjustingTraceExporter` | ✅ | Parity achieved |
| **Feature markers** | ✅ (marks genkit spans) | ❌ |

### Telemetry Gaps Summary

| Gap | Priority | Status |
|-----|----------|--------|
| ~~**RealtimeSpanProcessor**~~ | ~~P1~~ | ✅ Implemented - live tracing now works |
| ~~**Span redaction**~~ | ~~P2~~ | ✅ Implemented - `AdjustingTraceExporter` |
| ~~**flushTracing() API**~~ | ~~P2~~ | ✅ Implemented - `ai.flush_tracing()` |
| **Logging instrumentation** | P3 | Logs not auto-correlated |
| **enableTelemetry() config** | P3 | Less flexibility |

---

## 3. Model Configuration Not Showing in DevUI

> [!CAUTION]
> **Critical Bug**: Model configuration options don't appear in DevUI for Python Google GenAI models.

### Root Cause

Python's `google.py` has `config_schema` **commented out** when calling `model_action_metadata()`:

```python
# google.py line 484-490
actions_list.append(
    model_action_metadata(
        name=vertexai_name(name),
        info=google_model_info(name).model_dump(),
        # config_schema=GeminiConfigSchema,  # <-- COMMENTED OUT!
    ),
)
```

Compare to JS which **always passes `configSchema`**:

```typescript
// gemini.ts line 547-551
return modelActionMetadata({
  name: ref.name,
  info: ref.info,
  configSchema: ref.configSchema,  // <-- Always included!
});
```

### Impact

- DevUI cannot display model configuration options (temperature, topP, safety settings, etc.)
- Users cannot adjust model parameters through the UI
- Affects both GoogleAI and VertexAI plugins

### Fix Required

1. Uncomment `config_schema=GeminiConfigSchema` in `_resolve_model()` and `list_actions()`
2. Ensure `GeminiConfigSchema` is properly exported and includes all options
3. Verify JSON schema serialization works for Pydantic models

### Files to Fix
- [google.py](/py/plugins/google-genai/src/genkit/plugins/google_genai/google.py#L243) - `list_actions()` 
- [google.py](/py/plugins/google-genai/src/genkit/plugins/google_genai/google.py#L455) - VertexAI `list_actions()`
- [gemini.py](/py/plugins/google-genai/src/genkit/plugins/google_genai/models/gemini.py#L179-L187) - `GeminiConfigSchema` definition

---

## 4. Behavioral Differences

> [!IMPORTANT]
> These are differences in how features behave, not missing features.

### 4.1 Streaming Response Handling

**JS:** Returns `GenerateStreamResponse` with both `stream` (async iterable) and `response` (promise) accessible simultaneously. Stream chunks are also available via `onChunk` callback.

```typescript
const { response, stream } = ai.generateStream({...});
for await (const chunk of stream) {
  console.log(chunk.text);
}
const final = await response;
```

**Python:** Returns GenerateResponseWrapper that requires different access patterns. The `stream` attribute returns an async generator.

```python
response = await ai.generate_stream(...)
async for chunk in response.stream:
    print(chunk.text)
final = await response.response
```

**Action Needed:** Verify streaming API ergonomics match JS patterns.

---

### 4.2 Tool Call Response Handling

**JS:** Tools can return `Part[]` when configured with `multipart: true`, allowing rich responses with multiple content types.

```typescript
ai.defineTool({ multipart: true }, async (input) => {
  return [
    { text: "Analysis:" },
    { media: { url: "data:..." } }
  ];
});
```

**Python:** Tools return a single value that gets wrapped. No explicit multipart support.

**Action Needed:** Add multipart tool support to Python.

---

### 4.3 Output Schema Validation Behavior

**JS:** Uses Zod schemas. When `output.schema` is specified, attempts to parse and validate response. Returns typed `response.output`.

**Python:** Uses Pydantic models. Schema is converted to JSON Schema for the model request, but response parsing may differ.

**Action Needed:** Verify output parsing behavior matches, especially for:
- Partial JSON handling
- Array extraction
- Nested object validation

---

### 4.4 Prompt Resolution Order

**JS:** 
1. Looks in prompt cache (already loaded)
2. Loads from `promptDir` (default: `./prompts`)
3. Checks registered prompts via `definePrompt()`

**Python:**
1. Checks registry for registered prompts
2. Loads from prompt directory if configured

**Action Needed:** Verify prompt loading order and caching behavior.

---

### 4.5 Model Middleware Execution

**JS:** Middleware wraps the generate call with before/after hooks, can modify request and response.

**Python:** Similar structure but async/await patterns differ.

**Action Needed:** Verify middleware execution order and error handling.

---

## 5. Type System Differences

### 5.1 Part Type Construction

**JS:**
```typescript
{ text: "hello" }  // Direct construction
{ media: { url: "..." } }
```

**Python:** (After recent fixes)
```python
Part(root=TextPart(text="hello"))  # Must use root=
Part(root=MediaPart(media=Media(url="...")))
```

**Status:** Being addressed - needs consistent patterns documented.

---

### 5.2 Schema Registration

**JS:**
```typescript
ai.defineSchema('Recipe', RecipeSchema);  // Zod schema
ai.defineJsonSchema('Recipe', {...});     // JSON Schema
```

**Python:**
```python
ai.define_schema('Recipe', Recipe)  # Pydantic model only
```

**Action Needed:** Add `define_json_schema()` to Python.

---

## 6. Testing & Tooling Gaps

| Feature | JS | Python |
|---------|-----|--------|
| Echo Model | ✅ | ✅ |
| Programmable Model | ✅ | ❌ |
| Test Action | ✅ | Limited |
| Trace Viewer | ✅ | ✅ |

---

## 7. Priority Recommendations

### P0 - Critical (Block key use cases)

1. **Model Config Schema Bug** - DevUI cannot show model parameters (commented out in Python)
2. **Session/Chat** - Required for conversational AI applications
3. **Background Actions** - Required for video/image generation models

### P1 - High (Significant functionality gaps)

4. **Context Caching** - Cost optimization for long contexts
5. **Dynamic Action Provider** - MCP and plugin extensibility
6. **Vertex Rerankers** - RAG quality improvement
7. **Vertex Evaluation** - Built-in quality assessment

### P2 - Medium (Completeness)

8. **`defineSimpleRetriever()`** - Developer convenience
9. **`ai.run()`** - Trace step naming
10. **`embedMany()`** - Batch embedding efficiency
11. **Multipart tools** - Rich tool responses

### P3 - Low (Nice to have)

12. **Chroma plugin**
13. **Pinecone plugin**
14. **Cloud SQL plugin**

---

## 8. Files Reference

### JS Core
- [genkit.ts](/js/genkit/src/genkit.ts) - Main Genkit class
- [session.ts](/js/ai/src/session.ts) - Session management
- [chat.ts](/js/ai/src/chat.ts) - Chat implementation
- [background-action.ts](/js/core/src/background-action.ts) - Background ops
- [dynamic-action-provider.ts](/js/core/src/dynamic-action-provider.ts) - DAP

### Python Core
- [_registry.py](/py/packages/genkit/src/genkit/ai/_registry.py) - GenkitRegistry
- [_base_async.py](/py/packages/genkit/src/genkit/ai/_base_async.py) - Genkit base
- [generate.py](/py/packages/genkit/src/genkit/blocks/generate.py) - Generation
- [prompt.py](/py/packages/genkit/src/genkit/blocks/prompt.py) - Prompts
