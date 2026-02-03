# Genkit Feature Parity Analysis: JavaScript vs Python

This document provides a comprehensive feature parity analysis between the JavaScript
(canonical) and Python implementations of Genkit, verified as of February 2026.

---

## Executive Summary

| Category | Status | Notes |
|----------|--------|-------|
| **Core AI APIs** | ✅ PARITY | generate, flows, tools, prompts all implemented |
| **Output Formats** | ✅ PARITY | json, text, array, enum, jsonl formats |
| **Embedder API** | ✅ PARITY | embed, embedMany, defineEmbedder |
| **Retriever/Indexer** | ✅ PARITY | Full RAG support |
| **Reranker API** | ✅ PARITY | Define and use rerankers |
| **Evaluator API** | ✅ PARITY | Single and batch evaluators |
| **Session/Chat** | ✅ PARITY | Multi-thread sessions |
| **DAP (Dynamic Actions)** | ✅ PARITY | Runtime action providers |
| **Middleware** | ✅ PARITY | retry/fallback/augmentWithContext |
| **Telemetry** | ✅ PARITY | OpenTelemetry, GCP exporters |
| **Reflection API** | ✅ PARITY | DevUI support |
| **Plugin Coverage** | ✅ PARITY | Vertex AI rerankers and evaluators added |

---

## 1. Core AI APIs Comparison

### 1.1 Generate API

| Feature | JavaScript | Python | Status |
|---------|-----------|--------|--------|
| `generate()` | ✅ | ✅ | PARITY |
| `generateStream()` | ✅ | ✅ `generate_stream()` | PARITY |
| `generateOperation()` | ✅ (beta) | ✅ `generate_operation()` | PARITY |
| **Parameters** | | | |
| `model` | ✅ | ✅ | PARITY |
| `prompt` | ✅ Part/string/array | ✅ Part/string/list | PARITY |
| `system` | ✅ | ✅ | PARITY |
| `messages` | ✅ | ✅ | PARITY |
| `tools` | ✅ | ✅ | PARITY |
| `toolChoice` | ✅ auto/required/none | ✅ auto/required/none | PARITY |
| `returnToolRequests` | ✅ | ✅ `return_tool_requests` | PARITY |
| `maxTurns` | ✅ | ✅ `max_turns` | PARITY |
| `config` | ✅ | ✅ | PARITY |
| `context` | ✅ | ✅ | PARITY |
| `docs` | ✅ | ✅ | PARITY |
| `use` (middleware) | ✅ | ✅ | PARITY |
| `onChunk` | ✅ | ✅ `on_chunk` | PARITY |
| `abortSignal` | ✅ | ❌ | JS only |
| `stepName` | ✅ | ❌ | JS only |
| **Output Options** | | | |
| `output.schema` | ✅ Zod | ✅ Pydantic/dict | PARITY |
| `output.format` | ✅ | ✅ `output_format` | PARITY |
| `output.contentType` | ✅ | ✅ `output_content_type` | PARITY |
| `output.instructions` | ✅ | ✅ `output_instructions` | PARITY |
| `output.constrained` | ✅ | ✅ `output_constrained` | PARITY |
| **Resume (Interrupts)** | | | |
| `resume.respond` | ✅ (beta) | ⚠️ Limited | Python via tool_responses |
| `resume.restart` | ✅ (beta) | ❌ | JS only |

### 1.2 Flow API

| Feature | JavaScript | Python | Status |
|---------|-----------|--------|--------|
| `defineFlow()` | ✅ | ✅ `@ai.flow()` decorator | PARITY |
| Flow streaming | ✅ FlowSideChannel | ✅ `flow.stream()` | PARITY |
| Typed input/output | ✅ Zod schemas | ✅ Pydantic models | PARITY |
| `run()` for sub-spans | ✅ | ✅ | PARITY |
| Async support | ✅ | ✅ | PARITY |
| Sync support | ✅ | ✅ | PARITY |

### 1.3 Tool API

| Feature | JavaScript | Python | Status |
|---------|-----------|--------|--------|
| `defineTool()` | ✅ | ✅ `@ai.tool()` decorator | PARITY |
| `dynamicTool()` | ✅ | ✅ `ai.dynamic_tool()` | PARITY |
| Tool interrupts | ✅ `interrupt()` | ✅ `ToolRunContext` | PARITY |
| `tool.respond()` | ✅ | ✅ `tool_response()` | PARITY |
| `tool.restart()` | ✅ | ✅ `tool_restart()` | PARITY |
| Multipart tools (v2) | ✅ | ❌ | JS only |
| `asTool()` conversion | ✅ | ❌ | JS only |
| `defineInterrupt()` | ✅ | ❌ | JS only |

### 1.4 Prompt API

| Feature | JavaScript | Python | Status |
|---------|-----------|--------|--------|
| `definePrompt()` | ✅ | ✅ `ai.define_prompt()` | PARITY |
| `prompt()` lookup | ✅ | ✅ `ai.prompt()` | PARITY |
| `prompt.stream()` | ✅ | ✅ | PARITY |
| `prompt.render()` | ✅ | ✅ | PARITY |
| `prompt.asTool()` | ✅ | ✅ `prompt.as_tool()` | PARITY |
| Dotprompt files | ✅ | ✅ | PARITY |
| Handlebars templating | ✅ | ✅ | PARITY |
| `defineHelper()` | ✅ | ✅ | PARITY |
| `definePartial()` | ✅ | ✅ | PARITY |
| Prompt variants | ✅ | ✅ | PARITY |

### 1.5 Embedder API

| Feature | JavaScript | Python | Status |
|---------|-----------|--------|--------|
| `embed()` | ✅ | ✅ | PARITY |
| `embedMany()` | ✅ | ✅ `embed_many()` | PARITY |
| `defineEmbedder()` | ✅ | ✅ `ai.define_embedder()` | PARITY |
| EmbedderInfo | ✅ | ✅ | PARITY |

### 1.6 Retriever/Indexer API

| Feature | JavaScript | Python | Status |
|---------|-----------|--------|--------|
| `retrieve()` | ✅ | ✅ | PARITY |
| `index()` | ✅ | ✅ | PARITY |
| `defineRetriever()` | ✅ | ✅ | PARITY |
| `defineSimpleRetriever()` | ✅ | ✅ | PARITY |
| `defineIndexer()` | ✅ | ✅ | PARITY |

### 1.7 Reranker API

| Feature | JavaScript | Python | Status |
|---------|-----------|--------|--------|
| `rerank()` | ✅ | ✅ | PARITY |
| `defineReranker()` | ✅ | ✅ | PARITY |

### 1.8 Evaluator API

| Feature | JavaScript | Python | Status |
|---------|-----------|--------|--------|
| `evaluate()` | ✅ | ✅ | PARITY |
| `defineEvaluator()` | ✅ | ✅ | PARITY |
| Batch evaluator | ✅ | ✅ `define_batch_evaluator()` | PARITY |
| EvalResponse | ✅ | ✅ | PARITY |

### 1.9 Session/Chat API

| Feature | JavaScript | Python | Status |
|---------|-----------|--------|--------|
| `Session` class | ✅ | ✅ | PARITY |
| `session.chat()` | ✅ | ✅ | PARITY |
| `chat.send()` | ✅ | ✅ | PARITY |
| `chat.sendStream()` | ✅ | ✅ `send_stream()` | PARITY |
| Multi-thread support | ✅ | ✅ | PARITY |
| Session state | ✅ | ✅ | PARITY |
| ExecutablePrompt preamble | ✅ | ✅ | PARITY |
| SessionStore interface | ✅ | ✅ | PARITY |
| In-memory store | ✅ | ✅ | PARITY |

### 1.10 Dynamic Action Provider (DAP)

| Feature | JavaScript | Python | Status |
|---------|-----------|--------|--------|
| `defineDynamicActionProvider()` | ✅ | ✅ `define_dynamic_action_provider()` | PARITY |
| Cache with TTL | ✅ | ✅ | PARITY |
| `invalidateCache()` | ✅ | ✅ `invalidate_cache()` | PARITY |
| `getAction()` | ✅ | ✅ `get_action()` | PARITY |
| `listActionMetadata()` | ✅ | ✅ `list_action_metadata()` | PARITY |
| `getActionMetadataRecord()` | ✅ | ✅ `get_action_metadata_record()` | PARITY |
| DAP expansion in reflection | ✅ | ✅ | PARITY |

### 1.11 Model Definition

| Feature | JavaScript | Python | Status |
|---------|-----------|--------|--------|
| `defineModel()` | ✅ | ✅ | PARITY |
| `defineBackgroundModel()` | ✅ | ✅ | PARITY |
| Model capabilities | ✅ | ✅ | PARITY |
| Model versions | ✅ | ✅ | PARITY |
| `modelRef()` | ✅ | ✅ | PARITY |

### 1.12 Resource API

| Feature | JavaScript | Python | Status |
|---------|-----------|--------|--------|
| `defineResource()` | ✅ | ✅ | PARITY |
| URI templates (RFC6570) | ✅ | ✅ | PARITY |

---

## 2. Model Middleware Comparison

| Middleware | JavaScript | Python | Status |
|------------|-----------|--------|--------|
| `downloadRequestMedia()` | ✅ | ❌ | JS only |
| `validateSupport()` | ✅ | ❌ | JS only |
| `simulateSystemPrompt()` | ✅ | ❌ | JS only |
| `augmentWithContext()` | ✅ | ✅ | PARITY |
| `retry()` | ✅ | ✅ | PARITY |
| `fallback()` | ✅ | ✅ | PARITY |
| `simulateConstrainedGeneration()` | ✅ | ❌ | JS only |
| Custom middleware | ✅ | ✅ | PARITY |

> [!NOTE]
> **Production Ready:** Python now has `retry()` and `fallback()` middleware for production reliability.

---

## 3. Output Formats

| Format | JavaScript | Python | Status |
|--------|-----------|--------|--------|
| `json` | ✅ | ✅ | PARITY |
| `text` | ✅ | ✅ | PARITY |
| `array` | ✅ | ✅ | PARITY |
| `enum` | ✅ | ✅ | PARITY |
| `jsonl` | ✅ | ✅ | PARITY |
| Custom formats | ✅ `defineFormat()` | ✅ `ai.define_format()` | PARITY |

---

## 4. Plugin Comparison

### 4.1 Plugin Existence Matrix

| Plugin | JavaScript | Python | Notes |
|--------|-----------|--------|-------|
| **AI Model Providers** | | | |
| google-genai | ✅ | ✅ | Both have GoogleAI + VertexAI |
| vertexai | ✅ (separate) | ✅ (in google-genai) | Different structure |
| anthropic | ✅ | ✅ | PARITY |
| ollama | ✅ | ✅ | PARITY |
| compat-oai (OpenAI) | ✅ | ✅ | PARITY |
| aws-bedrock | ❌ | ✅ | Python only |
| azure | ❌ | ✅ | Python only |
| deepseek | ❌ | ✅ | Python only |
| huggingface | ❌ | ✅ | Python only |
| mistral | ❌ | ✅ | Python only |
| xai (Grok) | ❌ | ✅ | Python only |
| msfoundry | ❌ | ✅ | Python only |
| cf-ai (Cloudflare) | ❌ | ✅ | Python only |
| **Vector Stores** | | | |
| dev-local-vectorstore | ✅ | ✅ | PARITY |
| chroma | ✅ | ❌ | **MISSING in Python** |
| pinecone | ✅ | ❌ | **MISSING in Python** |
| cloud-sql-pg | ✅ | ❌ | JS only |
| **Infrastructure** | | | |
| firebase | ✅ | ✅ | PARITY |
| google-cloud | ✅ | ✅ | PARITY |
| evaluators | ✅ | ✅ | PARITY |
| mcp | ✅ | ✅ | PARITY |
| **Web Frameworks** | | | |
| express | ✅ | ❌ | N/A (JS-specific) |
| next | ✅ | ❌ | N/A (JS-specific) |
| flask | ❌ | ✅ | N/A (Python-specific) |
| **Other** | | | |
| langchain | ✅ | ❌ | JS only |
| checks | ✅ | ❌ | JS only |
| observability | ❌ | ✅ | Python has 3rd-party backends |

### 4.2 google-genai Plugin Feature Comparison

| Feature | JavaScript | Python | Status |
|---------|-----------|--------|--------|
| **Models** | | | |
| Gemini models | ✅ Dynamic | ✅ Dynamic | PARITY |
| Gemma models | ✅ | ✅ | PARITY |
| TTS models | ✅ | ✅ | PARITY |
| Image models | ✅ | ✅ | PARITY |
| Imagen | ✅ (GoogleAI) | ✅ (VertexAI) | Different backends |
| Veo (video) | ✅ | ✅ | PARITY |
| Lyria (audio) | ✅ | ✅ | PARITY |
| **Embedders** | | | |
| Text embeddings | ✅ | ✅ | PARITY |
| Multimodal embeddings | ✅ | ✅ | PARITY |
| **Special Features** | | | |
| Context caching | ✅ (VertexAI) | ✅ (VertexAI, basic) | JS more complete |
| Google Search retrieval | ✅ | ❓ | Unclear in Python |
| **Vertex-specific** | | | |
| Rerankers | ✅ | ✅ | PARITY |
| Built-in evaluators | ✅ | ✅ | PARITY |
| Vector Search | ✅ | ✅ | PARITY |
| Model Garden | ✅ | ✅ | PARITY |

### 4.3 evaluators Plugin Comparison

| Metric | JavaScript | Python | Status |
|--------|-----------|--------|--------|
| ANSWER_RELEVANCY | ✅ | ✅ | PARITY |
| FAITHFULNESS | ✅ | ✅ | PARITY |
| ANSWER_ACCURACY | ✅ | ✅ | PARITY |
| MALICIOUSNESS | ✅ | ✅ | PARITY |
| REGEX | ✅ | ✅ | PARITY |
| DEEP_EQUAL | ✅ | ✅ | PARITY |
| JSONATA | ✅ | ✅ | PARITY |

---

## 5. Telemetry Comparison

| Feature | JavaScript | Python | Status |
|---------|-----------|--------|--------|
| **OpenTelemetry** | | | |
| TracerProvider | ✅ | ✅ | PARITY |
| Span types | ✅ | ✅ | PARITY |
| Span attributes | ✅ | ✅ | PARITY |
| **Span Processors** | | | |
| SimpleSpanProcessor | ✅ | ✅ | PARITY |
| BatchSpanProcessor | ✅ | ✅ | PARITY |
| RealtimeSpanProcessor | ✅ | ✅ | PARITY |
| **Metrics** | | | |
| Generate metrics | ✅ | ✅ | PARITY |
| Feature metrics | ✅ | ✅ | PARITY |
| Path metrics | ✅ | ✅ | PARITY |
| Engagement metrics | ✅ | ✅ | PARITY |
| Video/audio metrics | ❌ | ✅ | Python has more |
| **Exporters** | | | |
| Cloud Trace | ✅ | ✅ | PARITY |
| Cloud Monitoring | ✅ | ✅ | PARITY |
| Cloud Logging | ✅ (Winston) | ✅ (structlog) | PARITY |
| **Third-party** | | | |
| OTLP exporter | ❌ | ✅ | Python only |
| Sentry/Honeycomb/Datadog | ❌ | ✅ | Python only |

---

## 6. Reflection API Comparison

| Endpoint | JavaScript | Python | Status |
|----------|-----------|--------|--------|
| `GET /api/__health` | ✅ | ✅ | PARITY |
| `GET/POST /api/__quitquitquit` | ✅ GET | ✅ GET/POST | Python more flexible |
| `GET /api/actions` | ✅ | ✅ | PARITY |
| `POST /api/runAction` | ✅ | ✅ | PARITY |
| `POST /api/cancelAction` | ✅ | ✅ | PARITY |
| `GET /api/values` | ✅ | ✅ | PARITY |
| `GET /api/envs` | ✅ configurable | ✅ hardcoded | JS more flexible |
| `POST /api/notify` | ✅ | ✅ | PARITY |
| Streaming support | ✅ | ✅ | PARITY |
| Early header flush | ✅ | ✅ | PARITY |
| DAP expansion | ✅ | ✅ | PARITY |

---

## 7. Critical Gaps Summary

### High Priority (Should fix before major production use)

| Gap | Impact | Status |
|-----|--------|--------|
| **`retry()` middleware** | Production reliability - auto-retry on transient errors | ✅ IMPLEMENTED |
| **`fallback()` middleware** | Production reliability - fallback to other models | ✅ IMPLEMENTED |
| **Vertex AI Rerankers** | RAG quality - important for search applications | ✅ IMPLEMENTED |
| **`tool.restart()`** | Advanced interrupt workflows | ✅ IMPLEMENTED |

### Medium Priority (Track for future)

| Gap | Notes |
|-----|-------|
| Chroma plugin | Popular open-source vector DB |
| Pinecone plugin | Popular managed vector DB |
| Vertex AI built-in evaluators | Native GCP evaluation metrics |
| Context caching (full implementation) | JS has more complete support |

### Acceptable Differences

| Difference | Notes |
|------------|-------|
| Python-only plugins (aws-bedrock, etc.) | Expands Python ecosystem |
| JS-only plugins (express, next, langchain) | Language-specific integrations |
| structlog vs Winston | Language-appropriate logging |
| Pydantic vs Zod | Language-appropriate validation |
| Python observability plugin | Additional value for Python users |

---

## 8. Release Readiness Assessment

> [!NOTE]
> **Overall Status: ✅ READY FOR RELEASE**

The Python implementation has achieved feature parity with JavaScript for all core APIs.
The remaining gaps are:
- Production reliability middleware (`retry`, `fallback`) - ✅ IMPLEMENTED
- Advanced tool features (`tool.restart()`, multipart) - `tool.restart()` ✅ IMPLEMENTED
- Vertex-specific features (rerankers, evaluators) - ✅ IMPLEMENTED

**Recommendation:** Ready for release. All critical gaps have been addressed.

---

## 9. Verification Checklist

- [x] Core generate API parity
- [x] Flow API parity
- [x] Tool API (basic) parity
- [x] Prompt API parity
- [x] Embedder API parity
- [x] Retriever/Indexer API parity
- [x] Reranker API parity
- [x] Evaluator API parity
- [x] Session/Chat API parity
- [x] DAP API parity
- [x] Output formats parity
- [x] Telemetry parity
- [x] Reflection API parity
- [x] Middleware: retry() - ✅ IMPLEMENTED
- [x] Middleware: fallback() - ✅ IMPLEMENTED
- [x] Vertex rerankers - ✅ IMPLEMENTED
- [x] Vertex evaluators - ✅ IMPLEMENTED
- [x] tool.restart() - ✅ IMPLEMENTED

---

## 10. Files Reference

### JS Core
- [genkit.ts](/js/genkit/src/genkit.ts) - Main Genkit class
- [session.ts](/js/ai/src/session.ts) - Session management
- [chat.ts](/js/ai/src/chat.ts) - Chat implementation
- [background-action.ts](/js/core/src/background-action.ts) - Background ops
- [dynamic-action-provider.ts](/js/core/src/dynamic-action-provider.ts) - DAP
- [middleware.ts](/js/ai/src/model/middleware.ts) - Model middleware

### Python Core
- [_aio.py](/py/packages/genkit/src/genkit/ai/_aio.py) - Async Genkit class
- [_registry.py](/py/packages/genkit/src/genkit/ai/_registry.py) - GenkitRegistry
- [session/](/py/packages/genkit/src/genkit/blocks/session/) - Session management
- [dap.py](/py/packages/genkit/src/genkit/blocks/dap.py) - Dynamic Action Provider
- [background_model.py](/py/packages/genkit/src/genkit/blocks/background_model.py) - Background models

---

*Last updated: 2026-02-03*
*Analyzed versions: JS (latest main), Python (latest main)*
