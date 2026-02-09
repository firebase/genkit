# Genkit Feature Parity Audit — JS / Go / Python

> Generated: 2025-02-08. Updated: 2026-02-08. Baseline: `firebase/genkit` JS implementation, with explicit JS vs Go vs Python parity tracking.
> Last verified: 2026-02-08 against genkit-ai org (14 repos) and BloomLabsInc/genkit-plugins.

## 1. Plugin Parity Matrix

### 1a. Plugin Coverage (In-Tree)

| Plugin Category | Plugin | JS | Go | Python | Notes |
|----------------|--------|:--:|:--:|:------:|-------|
| **Model Providers** | | | | | |
| Google GenAI | `google-genai` / `googlegenai` | ✅ | ✅ | ✅ | Primary provider |
| Google AI (legacy) | `googleai` | ✅ | — | — | JS legacy plugin |
| Vertex AI | `vertexai` / `vertex-ai` | ✅ | ✅ | ✅ | Name alias only |
| Anthropic | `anthropic` | ✅ | ✅ | ✅ | |
| Ollama | `ollama` | ✅ | ✅ | ✅ | |
| OpenAI-compatible | `compat-oai` / `compat_oai` | ✅ | ✅ | ✅ | Shim layer |
| Amazon Bedrock | `amazon-bedrock` | — | — | ✅ | Python-only (in-tree) |
| Cloudflare Workers AI | `cloudflare-workers-ai` | — | — | ✅ | Python-only |
| DeepSeek | `deepseek` | — | — | ✅ | Python-only |
| HuggingFace | `huggingface` | — | — | ✅ | Python-only |
| Microsoft Foundry | `microsoft-foundry` | — | — | ✅ | Python-only |
| Mistral | `mistral` | — | — | ✅ | Python-only |
| xAI (Grok) | `xai` | — | — | ✅ | Python-only |
| **Vector Stores** | | | | | |
| Dev Local Vectorstore | `dev-local-vectorstore` / `localvec` | ✅ | ✅ | ✅ | |
| Pinecone | `pinecone` | ✅ | ✅ | ❌ | Missing in Python |
| Chroma | `chroma` | ✅ | — | ❌ | JS-only in-tree |
| Cloud SQL (PostgreSQL) | `cloud-sql-pg` | ✅ | — | ❌ | JS-only in-tree |
| AlloyDB | `alloydb` | — | ✅ | — | Go-only |
| PostgreSQL | `postgresql` | — | ✅ | — | Go-only |
| Weaviate | `weaviate` | — | ✅ | — | Go-only |
| **Evaluation** | | | | | |
| Evaluators | `evaluators` | ✅ | ✅ | ✅ | |
| Checks (AI Safety) | `checks` | ✅ | — | ✅ | |
| **Observability** | | | | | |
| Google Cloud telemetry | `google-cloud` / `googlecloud` | ✅ | ✅ | ✅ | |
| Observability (OTLP backends) | `observability` | — | — | ✅ | Python-only |
| **Platform** | | | | | |
| Firebase | `firebase` | ✅ | ✅ | ✅ | |
| MCP | `mcp` | ✅ | ✅ | ✅ | |
| **Web Framework / Serving** | | | | | |
| Express | `express` | ✅ | — | — | JS-only |
| Next.js | `next` | ✅ | — | — | JS-only |
| Flask | `flask` | — | — | ✅ | Python-only |
| Server plugin | `server` | — | ✅ | — | Go-only |
| **Other** | | | | | |
| LangChain | `langchain` | ✅ | — | — | JS-only |
| Internal helpers | `internal` | — | ✅ | — | Go internal |

### 1b. Coverage Metrics

| Metric | JS | Go | Python |
|--------|:--:|:--:|:------:|
| Total in-tree plugins | 18 | 16 | 20 |
| Shared (JS+Go+Python) | 11 | 11 | 11 |
| Model provider plugins | 6 | 4 | 12 |
| Vector store plugins | 4 | 4 | 1 |
| Unique to this SDK | 7 | 5 | 9 |

### 1c. Plugin Gap Table (Parity Focus)

| Gap Group | JS Canonical Plugins | Go Status | Python Status | Priority | Status |
|-----------|----------------------|-----------|---------------|----------|:------:|
| Vector stores | `pinecone`, `chroma`, `cloud-sql-pg` | `pinecone` ✅, others ❌ | all 3 missing | High | ❌ |
| Web framework adapters | `express`, `next` | n/a (framework-specific) | n/a (framework-specific) | Info | ⚠️ |
| Integration ecosystem | `langchain` | missing | missing | Medium | ❌ |
| Legacy compatibility | `googleai` | n/a | missing | Low | ⚠️ |

### 1d. External Ecosystem Plugins (genkit-ai org + community)

| Plugin | Org/Source | SDK | Python Equivalent | Status |
|--------|-----------|-----|-------------------|:------:|
| AWS Bedrock JS | `genkit-ai/aws-bedrock-js-plugin` | JS | `amazon-bedrock` (in-tree) | ✅ |
| AWS Bedrock Go | `genkit-ai/aws-bedrock-go-plugin` | Go | `amazon-bedrock` (in-tree) | ✅ |
| Azure Foundry JS | `genkit-ai/azure-foundry-js-plugin` | JS | `microsoft-foundry` (in-tree) | ✅ |
| Azure Foundry Go | `genkit-ai/azure-foundry-go-plugin` | Go | `microsoft-foundry` (in-tree) | ✅ |
| OpenTelemetry Go | `genkit-ai/opentelemetry-go-plugin` | Go | `google-cloud` + `observability` (in-tree) | ✅ |
| `genkitx-openai` | `BloomLabsInc/genkit-plugins` | JS | `compat-oai` (in-tree) | ✅ |
| `genkitx-anthropic` | `BloomLabsInc/genkit-plugins` | JS | `anthropic` (in-tree) | ✅ |
| `genkitx-mistral` | `BloomLabsInc/genkit-plugins` | JS | `mistral` (in-tree) | ✅ |
| `genkitx-groq` | `BloomLabsInc/genkit-plugins` | JS | ❌ Not available | ❌ |
| `genkitx-cohere` | `BloomLabsInc/genkit-plugins` | JS | ❌ Not available | ❌ |
| `genkitx-azure-openai` | `BloomLabsInc/genkit-plugins` | JS | `microsoft-foundry` (partial) | ⚠️ |
| `genkitx-convex` | `BloomLabsInc/genkit-plugins` | JS | ❌ Not available | ❌ |
| `genkitx-hnsw` | `BloomLabsInc/genkit-plugins` | JS | ❌ Not available | ❌ |
| `genkitx-milvus` | `BloomLabsInc/genkit-plugins` | JS | ❌ Not available | ❌ |
| `genkitx-graph` | `BloomLabsInc/genkit-plugins` | JS | ❌ Not available | ❌ |

---

## 2. Sample Parity Matrix

### 2a. Sample Counts

| Sample Set | JS | Go | Python | Notes |
|------------|:--:|:--:|:------:|-------|
| Canonical internal sample/testapp set | 32 (`js/testapps`) | 37 (`go/samples`) | 37 runnable (`py/samples`, excluding `shared`, `sample-test`) | Primary parity baseline |
| Public showcase samples | 9 (`samples/js-*`) | — | — | Public docs/demo set |
| Total directories under samples root | — | 37 | 39 | Python includes utility dirs (`shared`, `sample-test`) |

### 2b. Sample Area Parity (JS vs Go vs Python)

| Area | JS | Go | Python | Status |
|------|:--:|:--:|:------:|:------:|
| Provider demos | ✅ | ✅ | ✅ | ✅ |
| Core framework patterns (flows/tools/prompts/evals) | ✅ | ✅ | ✅ | ✅ |
| MCP sample coverage | ✅ | ✅ | ⚠️ | ⚠️ |
| Web framework integration samples | ✅ (Express/Next/Firebase functions) | ⚠️ (server plugin + samples) | ✅ (Flask/ASGI variants) | ⚠️ surface differs |
| Durable/streaming advanced demos | ✅ | ✅ | ⚠️ | ⚠️ partial equivalence |

---

## 3. OSS Compliance Audit — Python

### 3a. Required Files per Package Type

Per Google OSS guidelines:

| File | Publishable Package | Sample | Notes |
|------|:-------------------:|:------:|-------|
| `LICENSE` | **Required** | **Required** | Apache 2.0 |
| `README.md` | **Required** | **Required** | |
| `pyproject.toml` | **Required** | **Required** | |
| `CHANGELOG.md` | **Required** | Optional | Per release_check |
| `py.typed` | **Required** | N/A | PEP 561 marker |
| `run.sh` | N/A | **Required** | Sample runner |
| `tests/` | **Required** | Optional | |

### 3b. Plugin Compliance

| Plugin | LICENSE | README | pyproject | CHANGELOG | py.typed | tests/ | Status |
|--------|:------:|:------:|:---------:|:---------:|:--------:|:------:|:------:|
| amazon-bedrock | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (2) | ⚠️ |
| anthropic | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (3) | ⚠️ |
| checks | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (1) | ⚠️ |
| cloudflare-workers-ai | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (1) | ⚠️ |
| compat-oai | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (7) | ⚠️ |
| deepseek | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (3) | ⚠️ |
| dev-local-vectorstore | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (4) | ⚠️ |
| evaluators | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (2) | ⚠️ |
| firebase | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (2) | ⚠️ |
| flask | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (1) | ⚠️ |
| google-cloud | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (2) | ⚠️ |
| google-genai | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (3) | ⚠️ |
| huggingface | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (2) | ⚠️ |
| mcp | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (5) | ⚠️ |
| microsoft-foundry | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (3) | ⚠️ |
| mistral | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (3) | ⚠️ |
| observability | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (2) | ⚠️ |
| ollama | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (4) | ⚠️ |
| vertex-ai | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (4) | ⚠️ |
| xai | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ (2) | ⚠️ |

**Legend**: ✅ = present, ❌ = missing, ⚠️ = mostly OK (only CHANGELOG missing)

### 3c. Missing Files Summary

| Issue | Count | Affected |
|-------|:-----:|----------|
| Missing `py.typed` | ~~9~~ **0** | All fixed ✅ |
| Missing `CHANGELOG.md` | 21 | ALL plugins + core package |
| Missing sample `LICENSE` | ~~1~~ **0** | `provider-checks-hello` fixed ✅ |

### 3d. Core Package (`packages/genkit`)

| Item | Status |
|------|:------:|
| LICENSE | ✅ |
| README.md | ✅ |
| pyproject.toml | ✅ |
| CHANGELOG.md | ❌ |
| py.typed | ✅ |
| tests/ | ✅ (44 test files) |

### 3e. Sample Compliance

All 37 samples have: `README.md` ✅, `run.sh` ✅, `pyproject.toml` ✅
All samples except `provider-checks-hello` had `LICENSE` ✅ (now fixed).

---

## 4. Test Coverage Summary

| Component | Test Files | Notes |
|-----------|:----------:|-------|
| **Core** (`packages/genkit`) | 44 | Comprehensive |
| **compat-oai** | 7 | Best-covered plugin |
| **google-genai** | 7 | Best-covered plugin |
| **mcp** | 5 | Well-covered |
| **dev-local-vectorstore** | 4 | Good |
| **ollama** | 4 | Good |
| **vertex-ai** | 4 | Good |
| **amazon-bedrock** | 3 | Good |
| **anthropic** | 3 | Good |
| **cloudflare-workers-ai** | 3 | Good |
| **deepseek** | 3 | Good |
| **evaluators** | 3 | Good |
| **firebase** | 3 | Good |
| **flask** | 3 | Good |
| **google-cloud** | 3 | Good |
| **huggingface** | 3 | Good |
| **microsoft-foundry** | 3 | Good |
| **mistral** | 3 | Good |
| **observability** | 3 | Good |
| **xai** | 3 | Good |
| **Total (plugins)** | 70 | All plugins ≥ 3 |
| **Total (workspace)** | 136 | Including core + samples |

---

## 5. Core Framework Parity — Module-Level API Comparison

### 5a. Define / Registration APIs

| API | JS (`Genkit` class) | Go (`genkit` pkg) | Python (`Genkit` / `GenkitRegistry`) | Status |
|-----|:---:|:---:|:---:|:---:|
| `defineFlow` | ✅ | ✅ `DefineFlow` | ✅ `.flow()` decorator | ✅ |
| `defineStreamingFlow` | ✅ (via options) | ✅ `DefineStreamingFlow` | ✅ (via streaming param) | ✅ |
| `defineTool` | ✅ | ✅ `DefineTool` | ✅ `.tool()` decorator | ✅ |
| `defineToolWithInputSchema` | — | ✅ `DefineToolWithInputSchema` | — | Go-only |
| `defineTool({multipart: true})` | ✅ | ✅ `DefineMultipartTool` | ❌ | ❌ Python missing (G18) |
| `defineModel` | ✅ | ✅ `DefineModel` | ✅ `define_model` | ✅ |
| `defineBackgroundModel` | ✅ | ✅ `DefineBackgroundModel` | ✅ `define_background_model` | ✅ |
| `definePrompt` | ✅ | ✅ `DefinePrompt` | ✅ `define_prompt` | ✅ |
| `defineDataPrompt` | — | ✅ `DefineDataPrompt` | — | Go-only |
| `defineEmbedder` | ✅ | ✅ `DefineEmbedder` | ✅ `define_embedder` | ✅ |
| `defineRetriever` | ✅ | ✅ `DefineRetriever` | ✅ `define_retriever` | ✅ |
| `defineSimpleRetriever` | ✅ | — | ✅ `define_simple_retriever` | ✅ |
| `defineIndexer` | ✅ | ❌ | ✅ `define_indexer` | ❌ Go missing |
| `defineReranker` | ✅ | ❌ | ✅ `define_reranker` | ❌ Go missing |
| `defineEvaluator` | ✅ | ✅ `DefineEvaluator` | ✅ `define_evaluator` | ✅ |
| `defineBatchEvaluator` | — | ✅ `DefineBatchEvaluator` | ✅ `define_batch_evaluator` | ✅ |
| `defineSchema` | ✅ | ✅ `DefineSchema` | ✅ `define_schema` | ✅ |
| `defineJsonSchema` | ✅ | — | ✅ `define_json_schema` | ✅ |
| `defineHelper` (Handlebars) | ✅ | ✅ `DefineHelper` | ✅ `define_helper` | ✅ |
| `definePartial` (Handlebars) | ✅ | ✅ `DefinePartial` | ✅ `define_partial` | ✅ |
| `defineFormat` | ✅ | ✅ `DefineFormat` | ✅ `define_format` | ✅ |
| `defineResource` | ✅ (beta) | ✅ `DefineResource` | ✅ `define_resource` | ✅ |
| `defineDynamicActionProvider` | ✅ | ❌ | ✅ `define_dynamic_action_provider` | ❌ Go missing |
| `defineInterrupt` | ✅ (beta) | ⚠️ (tool interrupt primitives, no direct define API) | ✅ (via tool interrupts) | ⚠️ |

### 5b. Invoke / Runtime APIs

| API | JS | Go | Python | Status |
|-----|:---:|:---:|:---:|:---:|
| `generate` | ✅ | ✅ `Generate` | ✅ `generate` | ✅ |
| `generateStream` | ✅ | ✅ `GenerateStream` | ✅ `generate_stream` | ✅ |
| `generateText` (convenience) | — | ✅ `GenerateText` | ✅ (via `generate`) | Go-only helper |
| `generateData` (typed output) | — | ✅ `GenerateData` | ✅ (via `generate`) | Go-only helper |
| `generateDataStream` | — | ✅ `GenerateDataStream` | ✅ (via `generate_stream`) | Go-only helper |
| `generateOperation` (background) | ✅ | ✅ `GenerateOperation` | ✅ `generate_operation` | ✅ |
| `embed` | ✅ | ✅ `Embed` | ✅ `embed` | ✅ |
| `embedMany` | ✅ | — | ✅ `embed_many` | ✅ |
| `retrieve` | ✅ | ✅ `Retrieve` | ✅ `retrieve` | ✅ |
| `rerank` | ✅ | ❌ | ✅ `rerank` | ❌ Go missing |
| `evaluate` | ✅ | ✅ `Evaluate` | ✅ `evaluate` | ✅ |
| `prompt` (load prompt) | ✅ | — | ✅ `prompt` | ✅ |
| `run` (named step) | ✅ | ✅ `Run` | ✅ `run` | ✅ |
| `chat` | ✅ (beta) | ❌ (session primitives only) | ✅ `Chat` class | ❌ Go missing high-level API |
| `createSession` | ✅ (beta) | ❌ (session package only) | ✅ `Session` class | ❌ Go missing high-level API |

### 5c. Client (Remote Invocation)

| API | JS | Go | Python | Status |
|-----|:---:|:---:|:---:|:---:|
| `runFlow` (remote HTTP) | ✅ (beta/client) | — | — | ❌ Python missing |
| `streamFlow` (remote SSE) | ✅ (beta/client) | — | — | ❌ Python missing |

Note: These are client-side helpers for invoking deployed flows over HTTP.
Python users typically use `httpx` or `requests` directly.

### 5d. Core Infrastructure

| Module | JS | Go | Python | Status |
|--------|:---:|:---:|:---:|:---:|
| Action system | `core/action.ts` | `core/action.go` | `core/action/` | ✅ |
| Registry | `core/registry.ts` | `core/core.go` | `core/registry.py` | ✅ |
| Reflection server | `core/reflection.ts` | `genkit/reflection.go` | `core/reflection.py` | ✅ |
| Tracing / telemetry | `core/tracing/` | `core/tracing/` | `core/trace/` | ✅ |
| Realtime span processor | `tracing/realtime-span-processor.ts` | — | `core/trace/realtime_processor.py` | ✅ |
| Schema / JSON schema | `core/schema.ts` | — | `core/schema.py` | ✅ |
| Error types | `core/error.ts` | `core/error.go` | `core/error.py` | ✅ |
| Status types | `core/statusTypes.ts` | `core/status_types.go` | `core/status_types.py` | ✅ |
| Context | `core/context.ts` | `core/context.go` | `core/context.py` | ✅ |
| Logging | `core/logging.ts` | `core/logger/` | `core/logging.py` | ✅ |
| Plugin system | `core/plugin.ts` | `core/api/plugin.go` | `core/_plugins.py` | ✅ |
| Streaming | `core/streaming.ts` | via Go iterators | `aio/channel.py` | ✅ |
| Background actions | `core/background-action.ts` | `core/background_action.go` | `blocks/background_model.py` | ✅ |
| Dynamic action providers | `core/dynamic-action-provider.ts` | — | `blocks/dap.py` | ✅ |
| Async context | `core/async-context.ts` | via Go context | `aio/` | ✅ |
| Config | `core/config.ts` | — | `core/environment.py` | ✅ |
| Web / server manager | — | `genkit/servers.go` | `web/manager/` | ✅ |
| HTTP client utils | — | — | `core/http_client.py` (cached) | Python-only |

### 5e. AI Blocks (Building Blocks)

| Block | JS (`ai/`) | Go (`ai/`) | Python (`blocks/`) | Status |
|-------|:---:|:---:|:---:|:---:|
| Generate | `generate/` | `generate.go` | `generate.py` | ✅ |
| Model | `model.ts` | — (in ai pkg) | `model.py` | ✅ |
| Middleware | `model/middleware.ts` | `model_middleware.go` | `middleware.py` | ✅ |
| Tool | `tool.ts` | `tools.go` | `tools.py` | ✅ |
| Prompt | `prompt.ts` | `prompt.go` | `prompt.py` | ✅ |
| Document | `document.ts` | `document.go` | `document.py` | ✅ |
| Embedder | `embedder.ts` | `embedder.go` | `embedding.py` | ✅ |
| Evaluator | `evaluator.ts` | `evaluator.go` | `evaluator.py` | ✅ |
| Retriever | `retriever.ts` | `retriever.go` | `retriever.py` | ✅ |
| Reranker | `reranker.ts` | — | `reranker.py` | ✅ |
| Resource | `resource.ts` | `resource.go` | `resource.py` | ✅ |
| Session / Chat | `session.ts` + `chat.ts` | — | `session/` (5 files) | ✅ |
| Message | `message.ts` | — | `messages.py` | ✅ |
| Extract (output parsing) | `extract.ts` | — | `extract.py` (in core) | ✅ |
| Check operation | `check-operation.ts` | — | In `background_model.py` | ✅ |
| Background model | — | `background_model.go` | `background_model.py` | ✅ |

### 5f. Output Formats

| Format | JS | Go | Python | Status |
|--------|:---:|:---:|:---:|:---:|
| JSON | ✅ | ✅ | ✅ | ✅ |
| JSONL | ✅ | ✅ | ✅ | ✅ |
| Array | ✅ | ✅ | ✅ | ✅ |
| Enum | ✅ | ✅ | ✅ | ✅ |
| Text | ✅ | ✅ | ✅ | ✅ |

### 5g. Cross-SDK Gaps vs JS Canonical API/Behavior

| Feature | JS | Go | Python | Gap Owner | Priority |
|---------|:--:|:--:|:------:|-----------|:--------:|
| `runFlow` / `streamFlow` client | ✅ (beta/client) | ❌ | ❌ | Go + Python | P2 |
| `defineTool({multipart: true})` | ✅ | ✅ | ❌ | Python | P1 |
| Model API V2 (`apiVersion: 'v2'`) | ✅ | ❌ | ❌ | Go + Python | P1 |
| `defineDynamicActionProvider` | ✅ | ❌ | ✅ | Go | P2 |
| `defineIndexer` | ✅ | ❌ | ✅ | Go | P2 |
| `defineReranker` | ✅ | ❌ | ✅ | Go | P2 |
| `rerank` runtime API | ✅ | ❌ | ✅ | Go | P2 |
| `chat` / `createSession` high-level APIs | ✅ | ❌ | ✅ | Go | P2 |
| Built-in model middleware: `retry` | ✅ | ❌ | ❌ | Go + Python | P1 |
| Built-in model middleware: `fallback` | ✅ | ❌ | ❌ | Go + Python | P1 |
| Built-in model middleware: `simulateConstrainedGeneration` | ✅ | ❌ | ❌ | Go + Python | P1 |
| Built-in model middleware: `downloadRequestMedia` | ✅ | ✅ | ❌ | Python | P2 |
| Built-in model middleware: `validateSupport` | ✅ | ✅ | ❌ | Python | P2 |
| Built-in model middleware: `simulateSystemPrompt` | ✅ | ✅ | ❌ | Python | P2 |
| `Genkit({context: ...})` default ctx | ✅ | ❌ | ❌ | Go + Python | P3 |
| `Genkit({clientHeader: ...})` | ✅ | ❌ | ❌ | Go + Python | P3 |
| `Genkit({name: ...})` display name | ✅ | ❌ | ❌ | Go + Python | P3 |
| Pinecone vector store plugin | ✅ | ✅ | ❌ | Python | P2 |
| ChromaDB vector store plugin | ✅ | — | ❌ | Go + Python | P3 |
| Cloud SQL PG vector store plugin | ✅ | — | ❌ | Go + Python | P3 |
| LangChain integration plugin | ✅ | — | ❌ | Go + Python | P3 |
| **Community Ecosystem** (BloomLabs etc.) | | | | | |
| Groq provider (`genkitx-groq`) | ✅ (community) | — | ❌ | Python | P3 |
| Cohere provider (`genkitx-cohere`) | ✅ (community) | — | ❌ | Python | P3 |
| Azure OpenAI (`genkitx-azure-openai`) | ✅ (community) | — | ✅ `microsoft-foundry` (superset) | Python | ✅ |
| Convex vector store (`genkitx-convex`) | ✅ (community) | — | ❌ | Python | P3 |
| HNSW vector store (`genkitx-hnsw`) | ✅ (community) | — | ❌ | Python | P3 |
| Milvus vector store (`genkitx-milvus`) | ✅ (community) | — | ❌ | Python | P3 |
| Graph workflows (`genkitx-graph`) | ✅ (community) | — | ❌ | Python | P3 |

### 5h. Python-Only Features

| Feature | Notes |
|---------|-------|
| 8 unique model providers | Bedrock, Cloudflare Workers AI, DeepSeek, HuggingFace, MS Foundry, Mistral, xAI, Observability |
| Flask plugin | Python web framework integration |
| ASGI/gRPC production sample | `web-endpoints-hello` — production-ready template with security, resilience, multi-server |
| `check_consistency` tooling | Automated 25-check workspace hygiene script |
| `release_check` tooling | Automated 15-check pre-release validation |
| Per-event-loop HTTP client caching | `get_cached_client()` — WeakKeyDictionary-based async HTTP client management |
| Multi-framework web support | Flask, FastAPI, Litestar, Quart adapters with framework-agnostic ASGI middleware |

### 5i. Go-Only Features (Not in JS or Python)

| Feature | Notes |
|---------|-------|
| `DefineDataPrompt` | Strongly-typed prompt with inferred input/output schemas |
| `GenerateText` | Convenience — direct string output from generation |
| `GenerateData` / `GenerateDataStream` | Convenience — structured typed output from generation |
| `DefineToolWithInputSchema` | Custom JSON schema input for tools |
| `LookupDataPrompt` | Typed prompt lookup |
| `WithPromptFS` | Embedded filesystem support for Go `embed.FS` |
| `LoadPromptFromSource` | Load prompt from raw string content |
| `CalculateInputOutputUsage` | Public middleware for counting input/output characters and media |
| `validateVersion` | Model version validation middleware |
| AlloyDB / PostgreSQL / Weaviate | Go-only vector stores |

---

## 6. Community & External Ecosystem (Validated 2026-02-08)

### 6a. `github.com/genkit-ai` org — Full Repository Inventory

| Metric | Value | Status |
|--------|-------|:------:|
| Public repos visible | 14 | ✅ |
| Primary content type | Docs / samples / SDK collateral + community plugins | ✅ |
| Direct repo-level replacement for JS in-tree plugin gaps | AWS Bedrock, Azure Foundry (both Go and JS) | ✅ |

| Repository | Type | Language | Parity Relevance |
|------------|------|----------|------------------|
| `genkit-dart` | SDK | Dart | Out-of-scope (separate SDK) |
| `docsite` | Documentation | MDX | Reference for API docs |
| `aws-bedrock-js-plugin` | Plugin | TypeScript | Python in-tree `amazon-bedrock` covers this ✅ |
| `aws-bedrock-go-plugin` | Plugin | Go | Python in-tree `amazon-bedrock` covers this ✅ |
| `azure-foundry-js-plugin` | Plugin | TypeScript | Python in-tree `microsoft-foundry` covers this ✅ |
| `azure-foundry-go-plugin` | Plugin | Go | Python in-tree `microsoft-foundry` covers this ✅ |
| `opentelemetry-go-plugin` | Plugin | Go | Python in-tree `google-cloud` + `observability` covers this ✅ |
| `skills` | AI Prompts | — | Supplemental |
| `repo-workflows` | CI | TypeScript | Infrastructure only |
| `genkit-python-samples` | Samples | TypeScript | Supplemental Python samples |
| `genkit-java` | SDK (unofficial) | Java | Out-of-scope (WIP separate SDK) |
| `samples` | Samples | Mixed | Supplemental sample source |
| `genkit-by-example` | Tutorials | Mixed | Supplemental tutorial source |
| `genkit-notebooklm` | App | — | Demo/showcase project |

### 6b. `BloomLabsInc/genkit-plugins` (npm `genkitx-*`)

Full plugin list from the repository README (10 plugins, 33 contributors, 54 releases):

**Model / Embedding Plugins:**

| Plugin | Category | Python Parity | Status |
|--------|----------|---------------|:------:|
| `genkitx-openai` | Provider (OpenAI) | Covered via `compat-oai` | ✅ |
| `genkitx-anthropic` | Provider (Anthropic) | Covered via `anthropic` | ✅ |
| `genkitx-mistral` | Provider (Mistral) | Covered via `mistral` | ✅ |
| `genkitx-groq` | Provider (Groq) | ❌ Not available | ❌ |
| `genkitx-cohere` | Provider (Cohere) | ❌ Not available | ❌ |
| `genkitx-azure-openai` | Provider (Azure OpenAI) | `microsoft-foundry` (partial) | ⚠️ |

**Vector Store Plugins:**

| Plugin | Category | Python Parity | Status |
|--------|----------|---------------|:------:|
| `genkitx-convex` | Vector store (Convex) | ❌ Not available | ❌ |
| `genkitx-hnsw` | Vector store (HNSW) | ❌ Not available | ❌ |
| `genkitx-milvus` | Vector store (Milvus) | ❌ Not available | ❌ |

**Other Plugins:**

| Plugin | Category | Python Parity | Status |
|--------|----------|---------------|:------:|
| `genkitx-graph` | Graph workflows | ❌ Not available | ❌ |

### 6c. External-Ecosystem Takeaways

| External Category | Current Python Coverage | Gap Level |
|-------------------|-------------------------|:---------:|
| Community model providers (6) | 3 of 6 covered | ⚠️ |
| Community vector stores (3) | 0 of 3 covered | ❌ |
| Community other plugins (1) | 0 of 1 covered | ❌ |
| genkit-ai org plugins (5) | All covered via in-tree equivalents | ✅ |
| Priority relative to JS-canonical parity | Secondary | ⚠️ |

**Note on community provider gaps**: The missing community providers (`genkitx-groq`, `genkitx-cohere`) could potentially be addressed via `compat-oai` since both Groq and Cohere offer OpenAI-compatible API endpoints. However, dedicated plugins would provide optimal model capability declarations and embedder support.

---

## 7. Action Items

### Parity Contract (Explicit)

| Rule | Requirement | Status |
|------|-------------|:------:|
| API parity | Go and Python should match canonical JS API capabilities (language-idiomatic surface allowed) | ⚠️ |
| Behavior parity | Language-idiomatic APIs are acceptable only when runtime semantics remain equivalent | ⚠️ |
| Gap handling | Any JS divergence is parity debt, not enhancement work | ✅ |

### P0 — Completed Foundations

| Item | Scope | Status |
|------|-------|:------:|
| Add missing `py.typed` to 9 plugins | PEP 561 compliance | ✅ |
| Add `LICENSE` to `provider-checks-hello` sample | OSS compliance | ✅ |
| Verify all plugins pass `bin/lint` and `py/bin/check_consistency` | Quality gate | ✅ |
| Add Google OSS file checks (CONTRIBUTING.md, LICENSE) to `py/bin/check_consistency` | Compliance automation | ✅ |

### 7a. Python Roadmap (JS-Canonical Parity)

| Gap ID | SDK | Work Item | Reference | Status |
|--------|-----|-----------|-----------|:------:|
| G1 | Python | `define_model(use=[...])` — model-level middleware | §8b.1 | ✅ Done (PR #4516) |
| G2 | Python | Action-level middleware storage | §8b.1 | ✅ Done (PR #4516) |
| G5 | Python | `X-Genkit-Span-Id` response header | §8c.4 | ✅ Done (PR #4511, merged) |
| G6 | Python | `on_trace_start` pass `span_id` | §8c.3 | ✅ Done (PR #4511, merged) |
| G11 | Python | Add `CHANGELOG.md` to plugins + core | §3c | ✅ Done (PR #4507 + #4508, merged) |
| G3 | Python | `simulate_constrained_generation` middleware | §8b.3, §8f | 🔄 PR #4510 open |
| G12 | Python | `retry` middleware | §8f | 🔄 PR #4510 open |
| G13 | Python | `fallback` middleware | §8f | 🔄 PR #4510 open |
| G14 | Python | `validate_support` middleware | §8f | 🔄 PR #4510 open |
| G15 | Python | `download_request_media` middleware | §8f | 🔄 PR #4510 open |
| G16 | Python | `simulate_system_prompt` middleware | §8f | 🔄 PR #4510 open |
| G18 | Python | Multipart tool support (`tool.v2`) | §8h | 🔄 PR #4513 open |
| G20 | Python | `Genkit(context=...)` constructor | §8j | 🔄 PR #4512 open |
| G21 | Python | `Genkit(clientHeader=...)` constructor | §8j | 🔄 PR #4512 open |
| G22 | Python | `Genkit(name=...)` constructor | §8j | 🔄 PR #4512 open |
| G38 | Python | `get_model_middleware()` auto-wiring | §8f.1 | ⬜ |
| G19 | Python | Model API V2 (`defineModel({apiVersion: 'v2'})`) | §8i | ⬜ |
| G4 | Python | Move `augment_with_context` to define-model time | §8b.2 | ⬜ |
| G7 | Python | Wire DAP action discovery into `/api/actions` | §8a, §8c.5 | ⏳ Deferred |
| G9 | Python | Add Pinecone vector store plugin | §5g | ⬜ |
| G10 | Python | Add ChromaDB vector store plugin | §5g | ⬜ |
| G30 | Python | Add Cloud SQL PG vector store parity | §5g | ⬜ |
| G31 | Python | Add dedicated Python MCP parity sample | §2b/§9 | ⏳ Deferred |
| G8 | Python | Implement `genkit.client` (`run_flow` / `stream_flow`) | §5c/§9 | ⏳ Deferred |
| G17 | Python | Add built-in `api_key()` context provider | §8g | ⬜ |
| G33 | Python | Consider LangChain integration parity | §1c/§9 | ⬜ |
| G34 | Python | Track BloomLabs vector stores (Convex, HNSW, Milvus) | §6b/§9 | ⬜ |
| G35 | Python | Add Groq provider (or document compat-oai usage) | §1d/§6b | ⬜ |
| G36 | Python | Add Cohere provider (or document compat-oai usage) | §1d/§6b | ⬜ |
| G37 | Python | Track BloomLabs graph workflows plugin | §1d/§6b | ⬜ |

### 7b. Go Roadmap (JS-Canonical Parity) — Deferred

> **Note**: Go parity work is deferred to a future effort. Current focus is exclusively on Python SDK parity.

| Gap ID | SDK | Work Item | Reference | Status |
|--------|-----|-----------|-------|:------:|
| G23 | Go | Add `defineDynamicActionProvider` parity | §5a/§5g | ⬜ |
| G24 | Go | Add `defineIndexer` parity | §5a/§5g | ⬜ |
| G25 | Go | Add `defineReranker` parity + runtime `rerank` API | §5a/§5b/§5g | ⬜ |
| G26 | Go | Add high-level `chat` / `createSession` API parity | §5b/§5g | ⬜ |
| G27 | Go | Add model middleware parity: `retry`, `fallback`, `simulateConstrainedGeneration` | §5g | ⬜ |
| G28 | Go | Add Model API V2 parity semantics | §5g | ⬜ |
| G29 | Go | Add constructor parity for context/client header/display name | §5g | ⬜ |
| G8 | Go | Implement `genkit.client` (`runFlow` / `streamFlow`) helpers | §5c/§9 | ⬜ |
| G30 | Go | Add Cloud SQL PG vector store parity | §5g | ⬜ |
| G32 | Go | Close web-serving behavior parity gaps (framework-agnostic) | §2b/§9 | ⬜ |
| G33 | Go | Consider LangChain integration parity | §1c/§9 | ⬜ |
| G34 | Go | Track BloomLabs vector stores | §6b/§9 | ⬜ |

---

## 8. Deep Dive Feature Comparison (JS vs Go vs Python)

> Updated: 2026-02-08. Line-level tracing against JS canonical implementation.

### Middleware Taxonomy — What Kinds Exist and When to Use Each

Genkit has **four distinct middleware layers**, each operating at a different level
of the request lifecycle. They are not interchangeable.

```
                        ┌──────────────────────────────┐
                        │        User Request          │
                        └──────────┬───────────────────┘
                                   │
                        ┌──────────▼───────────────────┐
   Layer 1              │   ASGI / HTTP Middleware      │  Security, CORS, rate limiting
   (Framework)          │   (Starlette, FastAPI, etc.)  │  Runs on EVERY HTTP request
                        └──────────┬───────────────────┘
                                   │
                        ┌──────────▼───────────────────┐
   Layer 2              │   Context Providers           │  Auth, API key extraction
   (Action)             │   (ContextProvider functions) │  Runs before EVERY action
                        └──────────┬───────────────────┘
                                   │
                        ┌──────────▼───────────────────┐
   Layer 3              │   Action Middleware           │  Generic action wrapping
   (Core)               │   (Action.use in JS core)    │  Runs around any action type
                        └──────────┬───────────────────┘
                                   │
                        ┌──────────▼───────────────────┐
   Layer 4              │   Model Middleware            │  Model-specific transforms
   (AI)                 │   (ModelMiddleware functions) │  Runs only on model calls
                        └──────────┬───────────────────┘
                                   │
                        ┌──────────▼───────────────────┐
                        │     Model Runner (LLM API)   │
                        └──────────────────────────────┘
```

#### Layer 1: ASGI / HTTP Middleware (Framework-Level)

**What**: Standard web middleware applied to the HTTP server.
**When**: Security headers, CORS, rate limiting, request logging, body size limits, compression.
**Scope**: Runs on **every HTTP request** — not Genkit-specific.
**Where**: Applied via Starlette/FastAPI/Litestar middleware stacks.

```python
# Example: Starlette CORS middleware
from starlette.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"])
```

**Not for**: Model request/response transforms, auth context injection.

#### Layer 2: Context Providers (Action-Level Auth)

**What**: Functions that extract auth/context data from the incoming HTTP request
and make it available to all actions via `current_context()`.
**When**: API key validation, JWT parsing, user session extraction.
**Scope**: Runs **before every action** execution, receiving the raw HTTP request.
**Where**: Registered via `Genkit(context=...)` or the `api_key()` helper.

```python
# Example: API key context provider
ai = Genkit(context=api_key(policy=lambda ctx, req: validate_key(ctx.key)))
```

**Key difference from middleware**: Context providers **parse and validate**
but don't wrap the action execution. They run once, before the action, and
their output is available via `current_context()` throughout the action's
lifecycle.

**Not for**: Modifying model requests/responses.

#### Layer 3: Action Middleware (Core-Level, JS Only)

**What**: Generic middleware that wraps any action (model, flow, tool, etc.) at
the `core/action.ts` level.
**When**: Tracing, logging, metrics collection, generic retry logic.
**Scope**: Runs around **any action type**, not specific to models.
**Where**: Applied via `defineAction({ use: [...] })` in JS.

```typescript
// JS only — not yet exposed as a user-facing API in Python
const action = defineAction({
  use: [tracingMiddleware, metricsMiddleware],
  fn: async (input) => { ... }
});
```

**Status**: JS has this as `SimpleMiddleware` / `MiddlewareWithOptions` in
`core/action.ts`. Python has the underlying `Action(middleware=...)` storage
(PR #4516) but this layer is primarily used internally by the framework
to wire model middleware — it's not a user-facing API.

**Not for**: Model-specific request transforms (use Model Middleware instead).

#### Layer 4: Model Middleware (AI-Level) ← Primary User-Facing Middleware

**What**: Functions that intercept and transform model `GenerateRequest`s and
`GenerateResponse`s in a chain around the model runner.
**When**: Safety guardrails, retry, fallback, constrained generation, system
prompt simulation, media downloading, request validation, caching.
**Scope**: Runs **only on model calls** (via `generate()` or `prompt.generate()`).

Model middleware can be applied at **two levels**:

| Level | API | When Applied | Typical Use |
|-------|-----|:------------:|-------------|
| **Call-time** | `generate(use=[mw])` | Per `generate()` call | Safety checks, per-request retry |
| **Model-level** | `define_model(use=[mw])` | Every call to this model | Always-on guardrails, validation |
| **Auto-wired** | `getModelMiddleware()` (JS) | At model definition time | Context augmentation, constrained generation simulation |

**Execution order**: call-time → model-level → auto-wired → model runner

```python
# Call-time middleware (per-request)
response = await ai.generate(
    model='googleai/gemini-2.0-flash',
    prompt='Hello',
    use=[checks_middleware(...), retry()],  # ← per this call only
)

# Model-level middleware (baked into the model)
ai.define_model(
    name='custom/safe-model',
    fn=my_model_fn,
    use=[validate_support(), simulate_system_prompt()],  # ← every call
)
```

#### Built-in Model Middleware Functions

| Middleware | Category | Purpose | When to Use | Status |
|-----------|:--------:|---------|-------------|:------:|
| `augment_with_context()` | **Transform** | Inject retrieved documents into user message | Models without native context support | ✅ Python |
| `simulate_constrained_generation()` | **Transform** | Inject JSON schema instructions for structured output | Models without native constrained output | 🔄 PR #4510 |
| `simulate_system_prompt()` | **Transform** | Convert system messages to user/model turns | Models without native system prompt | 🔄 PR #4510 |
| `download_request_media()` | **Transform** | Download URL media → base64 data URIs | Models requiring inline media | 🔄 PR #4510 |
| `validate_support()` | **Guard** | Check request vs model capabilities | All models — catches unsupported features early | 🔄 PR #4510 |
| `retry()` | **Resilience** | Exponential backoff with jitter | Production deployments with transient errors | 🔄 PR #4510 |
| `fallback()` | **Resilience** | Try alternative models on failure | Multi-model production setups | 🔄 PR #4510 |
| `checks_middleware()` | **Safety** | AI safety guardrails via Google Checks API | Content moderation | 🔄 PR #4504 (plugin) |

#### Decision Guide: Which Middleware Layer?

| Need | Use |
|------|-----|
| CORS, rate limiting, security headers | **Layer 1** (ASGI) |
| API key validation, user auth | **Layer 2** (Context Provider) |
| Transform model requests/responses | **Layer 4** (Model Middleware) |
| Block unsafe content | **Layer 4** (Model Middleware — `checks_middleware`) |
| Retry on transient errors | **Layer 4** (Model Middleware — `retry()`) |
| Fall back to alternative model | **Layer 4** (Model Middleware — `fallback()`) |
| Always-on model guardrails | **Layer 4** (Model Middleware — `define_model(use=[...])`) |
| Per-request safety check | **Layer 4** (Model Middleware — `generate(use=[...])`) |

### 8a. Dynamic Action Providers (DAP)

**Status**: ⚠️ Partial in Python

| Capability | JS Implementation | Python Implementation | Notes |
|------------|-------------------|-----------------------|-------|
| Definition | `ai.defineDynamicActionProvider` | `genkit.blocks.dap.define_dynamic_action_provider` | Parity ✅ |
| Resolution | `Registry.resolveAction` queries DAPs | `Registry.resolve_action` queries DAPs (fallback) | Parity ✅ |
| Discovery | `Registry.listResolvableActions` queries DAPs | **MISSING** | **Critical Gap**: Python's reflection API (`handle_list_actions`) only lists *registered* actions and *plugin* actions. It does NOT query DAPs for their actions. This means MCP tools will not appear in the Dev UI list in Python. |
| Metadata | `dap.listActions()` | `dap.get_action_metadata_record()` exists but is **unused** | The method exists in `dap.py` but is not wired into `reflection.py`. |

### 8b. Model Middleware — Architecture Deep Dive

**Status**: ❌ Multiple Gaps — Python vs JS

#### 8b.1 Two-Layer Middleware Architecture (JS) vs Single-Layer (Python)

JS has **two independent middleware dispatch layers**. Python has **one**.

**JS Architecture** (`js/ai/src/model.ts` + `js/core/src/action.ts` + `js/ai/src/generate/action.ts`):

```
User calls ai.generate({ use: [callTimeMiddleware] })
    │
    ▼
generate/action.ts dispatch() — call-time middleware chain
    │  index 0: callTimeMiddleware(req, next)
    │  index N: end of chain → model(req, actionOpts)
    │                              │
    │                              ▼
    │                action.ts actionWithMiddleware() — model-level middleware chain
    │                    │  index 0: augmentWithContext (if model !supports.context)
    │                    │  index 1: simulateConstrainedGeneration wrapper
    │                    │  index 2+: user-supplied middleware from defineModel({use: [...]})
    │                    │  end of chain → action.run(req, opts) → model runner fn
    │                    ▼
    │                actual model implementation (e.g., Google AI SDK call)
    ▼
GenerateResponse
```

**Python Architecture** (`py/.../blocks/generate.py`):

```
User calls genkit.generate(use=[callTimeMiddleware])
    │
    ▼
generate.py dispatch() — single middleware chain
    │  index 0: callTimeMiddleware(req, ctx, next)
    │  index N: augment_with_context() (appended at call time, conditional)
    │  end of chain → model.arun(input=req, ...) → directly to model runner fn
    │                                                (NO action-level middleware)
    ▼
GenerateResponse
```

**Key difference**: In JS, `model(req, actionOpts)` at the end of the call-time chain invokes the action **which is already wrapped** with model-level middleware via `actionWithMiddleware()`. In Python, `model.arun()` calls the model runner **directly** with no additional middleware layer.

| Aspect | JS Behavior | Python Behavior | Gap |
|--------|-------------|-----------------|-----|
| `defineModel({use: [mw]})` | ✅ Accepted. `mw` is baked into the action via `actionWithMiddleware()` at registration time. | ❌ `define_model(use=[...])` not supported. Parameter doesn't exist. | **Missing feature** |
| Model-level middleware storage | Stored in `ActionParams.use`, applied by `actionWithMiddleware()` wrapping `action.run()`. | No storage mechanism. `Action` class has no `middleware` attribute. | **Missing infrastructure** |
| Call-time middleware (`generate(use=[...])`) | ✅ Dispatched in `generate/action.ts:dispatch()`. Call-time runs FIRST, then model-level runs inside the action call. | ✅ Dispatched in `generate.py:dispatch()`. Single-layer only. | Partial parity (single layer works) |
| Execution order | call-time[0] → ... → call-time[N] → model-level[0] → ... → model-level[M] → runner | call-time[0] → ... → call-time[N] → runner | **Different order semantics** |

**JS References**:
- `js/ai/src/model.ts:161-186` — `modelActionOptions()` calls `getModelMiddleware()` and passes result as `ActionParams.use`
- `js/ai/src/model.ts:337-358` — `getModelMiddleware()` builds the model-level middleware array
- `js/core/src/action.ts:248-301` — `actionWithMiddleware()` wraps an action with middleware
- `js/core/src/action.ts:476-477` — `action()` calls `actionWithMiddleware()` when `config.use` is set
- `js/ai/src/generate/action.ts:335-358` — `dispatch()` chains call-time middleware, then calls `model(req, actionOpts)` which enters the action-level chain

**Python References**:
- `py/.../ai/_registry.py:define_model()` — No `use` parameter
- `py/.../blocks/generate.py:215-248` — `dispatch()` — single-layer, calls `model.arun()` directly
- `py/.../core/action/_action.py:Action.__init__()` — No middleware storage

#### 8b.2 `augmentWithContext` — Placement Difference

| Aspect | JS | Python | Gap |
|--------|-----|--------|-----|
| Where added | At **define-model time**, inside `getModelMiddleware()`. Added to the action-level middleware chain. | At **generate-call time**, inside `generate_action()`. Added to the call-time middleware chain. | **Behavioral difference** |
| Condition | Always added if `!options.supports.context` (regardless of whether request has docs). | Only added if `raw_request.docs` exists AND model doesn't support context. | **Stricter condition in Python** |
| Middleware layer | Model-level (runs after call-time middleware). | Call-time (runs at the same level as user middleware). | **Different layer** |

**JS** (`js/ai/src/model.ts:342-343`):
```js
const middleware: ModelMiddlewareArgument[] = options.use || [];
if (!options?.supports?.context) middleware.push(augmentWithContext());
// ↑ Always added at define time, unconditionally
```

**Python** (`py/.../blocks/generate.py:199-213`):
```python
if not middleware:
    middleware = []
# ...
if raw_request.docs and not supports_context:
    middleware.append(augment_with_context())
# ↑ Only added at call time, only when docs are present
```

**Impact**: In JS, calling `augmentWithContext()` is always part of the model's middleware chain, ready to process any future request with docs. In Python, it's only added when the *current* request has docs. This is a minor difference in practice but a behavioral divergence.

#### 8b.3 `simulateConstrainedGeneration` — Missing in Python

| Aspect | JS | Python | Gap |
|--------|-----|--------|-----|
| Existence | ✅ `js/ai/src/model/middleware.ts:466-497` | ❌ Does not exist | **Missing middleware** |
| Purpose | For models that don't natively support constrained output, injects format instructions into the prompt and clears the `constrained`, `format`, `contentType`, and `schema` from `output`. | Not implemented. Models that don't support constrained output may produce malformed responses. | **Functional gap** |
| Application | Always added at define-model time via `getModelMiddleware()`, wrapped in a conditional check based on `supports.constrained`. | N/A | |

**JS** (`js/ai/src/model.ts:344-355`):
```js
const constrainedSimulator = simulateConstrainedGeneration();
middleware.push((req, next) => {
  if (
    !options?.supports?.constrained ||
    options?.supports?.constrained === 'none' ||
    (options?.supports?.constrained === 'no-tools' &&
      (req.tools?.length ?? 0) > 0)
  ) {
    return constrainedSimulator(req, next);
  }
  return next(req);
});
```

**Impact**: Models that declare `supports.constrained = 'none'` or `'no-tools'` in JS get automatic schema instruction injection. In Python, the model must handle this itself or the output may not conform to the requested schema.

#### 8b.4 Middleware Type Signatures

| Aspect | JS | Python | Gap |
|--------|-----|--------|-----|
| Simple form | `SimpleMiddleware<I, O>`: `(req, next) => Promise<O>` (2 args) | N/A | Not applicable |
| With options form | `MiddlewareWithOptions<I, O, S>`: `(req, options, next) => Promise<O>` (3 args) | N/A | Not applicable |
| Model middleware | `ModelMiddleware` = `SimpleMiddleware<GenerateRequest, GenerateResponse>` | `ModelMiddleware` = `(req, ctx, next) => GenerateResponse` (always 3-arg) | **Different signatures** |
| Discriminator | JS checks `currentMiddleware.length` (2 vs 3) to pick the form. | Python always uses 3-arg form `(req: GenerateRequest, ctx: ActionRunContext, next: ModelMiddlewareNext)`. | Python is simpler but can't support the simple 2-arg form. |
| `ActionRunOptions` vs `ActionRunContext` | JS passes `ActionRunOptions` (has `onChunk`, `context`, `abortSignal`). | Python passes `ActionRunContext` (has `send_chunk`, `context`, `is_streaming`). | **Semantically equivalent but structurally different** — not a gap per se, just a naming difference. |

**Verdict**: Python's single 3-arg signature is cleaner. The JS 2-arg form is mainly for backward compatibility. No action needed here — the Python approach is fine.

### 8c. Reflection Server — Wire Protocol Comparison

**Status**: ✅ Mostly Aligned, with Minor Gaps

Both JS and Python use the **same core protocol**: Newline-delimited JSON (NDJSON) over `text/plain` for streaming, `application/json` for non-streaming. Neither uses SSE. However, there are several header-level and callback-shape differences.

#### 8c.1 Streaming Response Wire Format

| Aspect | JS (`js/core/src/reflection.ts:260-301`) | Python (`py/.../core/reflection.py:362-471`) | Gap |
|--------|-----|--------|-----|
| Chunk format | `JSON.stringify(chunk) + '\n'` | `dump_json(chunk) + '\n'` | ✅ Identical |
| Final message | `JSON.stringify({result, telemetry: {traceId}})` (no trailing newline) | `json.dumps({result, telemetry: {traceId}})` (no trailing newline) | ✅ Identical |
| Error in stream | `JSON.stringify({error: {code, message, details: {stack}}})` | `json.dumps(get_reflection_json(e).model_dump(by_alias=True))` | ✅ Functionally equivalent |
| Content-Type | `text/plain` | `text/plain` (via `media_type='text/plain'`) | ✅ Identical |
| Transfer-Encoding | Explicit `Transfer-Encoding: chunked` | Explicit `Transfer-Encoding: chunked` in headers dict | ✅ Identical |

#### 8c.2 Non-Streaming Response Wire Format

| Aspect | JS (`js/core/src/reflection.ts:304-321`) | Python (`py/.../core/reflection.py:473-560`) | Gap |
|--------|-----|--------|-----|
| Response body | `JSON.stringify({result, telemetry: {traceId}})` | `json.dumps({result, telemetry: {traceId}})` | ✅ Identical |
| Content-Type | `application/json` | `application/json` (via `media_type='application/json'`) | ✅ Identical |
| Transfer-Encoding | Explicit `Transfer-Encoding: chunked` (for early header flushing) | Implicit via Starlette `StreamingResponse` | ⚠️ **Minor**: JS explicitly sets it; Python relies on Starlette. Functionally equivalent but not explicit. |

#### 8c.3 Response Headers

| Header | JS | Python | Gap |
|--------|-----|--------|-----|
| `X-Genkit-Trace-Id` | ✅ Set in `onTraceStart` callback. Both streaming and non-streaming. | ✅ Set when trace ID is available. Both streaming and non-streaming. | ✅ Identical |
| **`X-Genkit-Span-Id`** | ✅ Set in `onTraceStart` callback (`reflection.ts:247`). | ❌ **Not sent**. Only listed in CORS `expose_headers`. | **Gap**: Python never sends this header. |
| `X-Genkit-Version` / `x-genkit-version` | ✅ Set as `X-Genkit-Version` in `onTraceStart` callback AND as `x-genkit-version` in non-streaming list endpoints. | ✅ Set as `x-genkit-version` in all responses. | ✅ Functionally equivalent (case-insensitive HTTP headers). |
| CORS `expose_headers` | Not explicitly shown (uses express CORS). | `['X-Genkit-Trace-Id', 'X-Genkit-Span-Id', 'x-genkit-version']` | ✅ Python is more explicit. |

#### 8c.4 `onTraceStart` Callback Shape

| Aspect | JS | Python | Gap |
|--------|-----|--------|-----|
| Callback arguments | `({traceId, spanId})` — receives **both** trace ID and span ID as a destructured object. | `(tid: str)` — receives **only** trace ID as a string. | **Gap**: Python cannot send `X-Genkit-Span-Id` because it doesn't receive the span ID. |

**JS** (`js/core/src/reflection.ts:234-258`):
```js
const onTraceStartCallback = ({ traceId: tid, spanId }) => {
  traceId = tid;
  response.setHeader('X-Genkit-Trace-Id', tid);
  response.setHeader('X-Genkit-Span-Id', spanId);  // ← Python can't do this
  response.setHeader('X-Genkit-Version', GENKIT_VERSION);
  // ...
  response.flushHeaders();
};
```

**Python** (`py/.../core/reflection.py:395-399`):
```python
def wrapped_on_trace_start(tid: str) -> None:
    nonlocal run_trace_id
    run_trace_id = tid
    on_trace_start(tid)
    trace_id_event.set()
```

**Fix required**: Update `on_trace_start` callback signature throughout the Python action system to pass both `trace_id` and `span_id`, then include `X-Genkit-Span-Id` in reflection response headers.

#### 8c.5 Action Discovery Endpoint (`GET /api/actions`)

| Aspect | JS | Python | Gap |
|--------|-----|--------|-----|
| Method | `registry.listResolvableActions()` — includes registered + plugin-advertised + **DAP-expanded** actions. | `_list_registered_actions(registry)` + `registry.list_actions()` — includes registered + plugin-advertised but **NOT DAP-expanded**. | **Gap**: See §8a. MCP tools from DAPs don't appear. |
| Response shape | `{key, name, description, metadata, inputSchema?, outputSchema?}` | `{key, name, type, description, inputSchema, outputSchema, metadata}` | ⚠️ Python includes `type` field (action kind); JS does not include it in the response but has `actionType` in `ActionMetadata`. Minor difference — not a functional gap. |

### 8d. Flow Invocation Client

**Status**: ❌ Missing in Python

| Feature | JS | Python | Notes |
|---------|----|--------|-------|
| `runFlow` (HTTP) | Client-side helper to invoke deployed flows | **Missing** | Python developers must craft HTTP requests manually using `requests` or `httpx`. |
| `streamFlow` (SSE) | Client-side helper to stream deployed flows | **Missing** | |

**Recommendation**: Implement `genkit.client` module with `run_flow` and `stream_flow` helpers that encapsulate the API protocol (JSON input, streaming response handling).

### 8e. Runtime Architecture

**Status**: ✅ Good Parity

| Feature | JS | Python | Notes |
|---------|----|--------|-------|
| Async Context | `AsyncLocalStorage` | `contextvars` | Both SDKs correctly handle async context propagation for traces. |
| HTTP Client | `fetch` (native) | `httpx` (with caching) | Python implements a `get_cached_client` pattern to optimize connection reuse in async environments. |
| Web Frameworks | Express/Next.js (middleware) | Starlette (ASGI) | Python uses a framework-agnostic ASGI approach (Starlette) which is excellent. Adapters for Flask/FastAPI exist. |

### 8f. Model Middleware — Full Coverage Comparison

**Status**: ❌ Major Gap — Python has 1 of 7 JS middleware functions

JS provides **7** built-in model middleware functions in `js/ai/src/model/middleware.ts`.
Python has **1** (`augment_with_context` in `blocks/middleware.py`).

| Middleware | JS | Python | Gap | Description |
|-----------|:--:|:------:|:---:|-------------|
| `augmentWithContext` | ✅ | ✅ `augment_with_context` | ⚠️ Placement differs (see §8b.2) | Injects documents into user message as context |
| `simulateConstrainedGeneration` | ✅ | ❌ | **G3** | Injects JSON schema instructions for models without native constrained output |
| `retry` | ✅ | ❌ | **G12** | Exponential backoff retry with configurable statuses, jitter, and callbacks |
| `fallback` | ✅ | ❌ | **G13** | Falls back to alternative models on specific error statuses |
| `validateSupport` | ✅ | ❌ | **G14** | Validates request against model capabilities (media, tools, multiturn) |
| `downloadRequestMedia` | ✅ | ❌ | **G15** | Downloads HTTP media URLs and converts to data URIs for inlining |
| `simulateSystemPrompt` | ✅ | ❌ | **G16** | Converts system messages into user/model message pairs for models without system prompt support |

#### G12: `retry` Middleware

**JS** (`js/ai/src/model/middleware.ts:337-383`):
```ts
export function retry(options: RetryOptions = {}): ModelMiddleware {
  // maxRetries (default: 3), exponential backoff with jitter
  // Retries on: UNAVAILABLE, DEADLINE_EXCEEDED, RESOURCE_EXHAUSTED, ABORTED, INTERNAL
  // Configurable: initialDelayMs, maxDelayMs, backoffFactor, noJitter, onError callback
}
```

**Impact**: Without this, Python users must implement their own retry logic around `generate()` calls. This is especially important for production deployments where transient errors are common.

#### G13: `fallback` Middleware

**JS** (`js/ai/src/model/middleware.ts:420-451`):
```ts
export function fallback(ai: HasRegistry, options: FallbackOptions): ModelMiddleware {
  // Falls back to alternative models on error
  // Tries each model in order until one succeeds
  // Configurable statuses and onError callback
}
```

**Impact**: Model fallback is a critical production feature. Without it, Python users must manually implement try/catch chains with model resolution.

#### G14: `validateSupport` Middleware

**JS** (`js/ai/src/model/middleware.ts:100-135`):
```ts
export function validateSupport(options: {
  name: string;
  supports?: ModelInfo['supports'];
}): ModelMiddleware {
  // Validates: media support, tool use, multiturn messages
  // Throws descriptive error with model name and request details
}
```

**Impact**: Without this, models silently receive requests with features they don't support, leading to confusing errors or incorrect behavior.

#### G15: `downloadRequestMedia` Middleware

**JS** (`js/ai/src/model/middleware.ts:35-95`):
```ts
export function downloadRequestMedia(options?: {
  maxBytes?: number;
  filter?: (part: MediaPart) => boolean;
}): ModelMiddleware {
  // Downloads http(s) media URLs and converts to data URIs
  // Useful for models that don't support URL-based media
}
```

**Impact**: Models that require base64-encoded media (rather than URLs) need this. Python users must handle media download and encoding manually.

#### G16: `simulateSystemPrompt` Middleware

**JS** (`js/ai/src/model/middleware.ts:151-174`):
```ts
export function simulateSystemPrompt(options?: {
  preface: string;
  acknowledgement: string;
}): ModelMiddleware {
  // Converts system messages into user/model turn pairs
  // For models that don't natively support system prompts
}
```

**Impact**: Models without native system prompt support (e.g., some older or fine-tuned models) get automatic simulation in JS but not in Python.

### 8g. Context Providers — Built-in Helpers

**Status**: ⚠️ Minor Gap

| Feature | JS | Python | Gap |
|---------|:--:|:------:|:---:|
| `ContextProvider` type | ✅ `core/context.ts` | ✅ `core/context.py` | ✅ Parity |
| `RequestData` type | ✅ `{method, headers, input}` | ⚠️ `{request, metadata}` | **Shape differs** (see below) |
| `apiKey()` helper | ✅ Built-in context provider | ❌ Not implemented | **G17** |
| `runWithContext()` | ✅ | ✅ (via action context propagation) | ✅ |
| `getContext()` | ✅ | ✅ `current_context()` | ✅ |

#### `RequestData` Shape Difference

**JS** (`core/context.ts:61-65`):
```ts
export interface RequestData<T = any> {
  method: 'GET' | 'PUT' | 'POST' | 'DELETE' | 'OPTIONS' | 'QUERY';
  headers: Record<string, string>;
  input: T;
}
```

**Python** (`core/context.py:36-45`):
```python
@dataclass
class RequestData(Generic[T]):
    request: T
    metadata: ContextMetadata | None = None
```

The Python `RequestData` is simpler — it wraps the raw request object and optional metadata (currently just `trace_id`). The JS version carries parsed HTTP method and headers, enabling more sophisticated context providers like `apiKey()`. This is a deliberate design difference (Python relies on the web framework's own request object), but it means `apiKey()` can't be ported directly without adjusting the `RequestData` shape or accepting the framework's request type.

#### G17: `apiKey()` Context Provider

**JS** (`core/context.ts:89-118`):
```ts
export function apiKey(
  valueOrPolicy?: ((context: ApiKeyContext) => void | Promise<void>) | string
): ContextProvider<ApiKeyContext> {
  // Extracts API key from Authorization header
  // Validates against expected value or custom policy
  // Returns UserFacingError for auth failures
}
```

**Impact**: Low. Python web frameworks (Flask, FastAPI, Starlette) have their own mature authentication middleware. This is more of a convenience gap than a functional one.

### 8h. Multipart Tool Support

**Status**: ❌ Missing in Python

| Feature | JS | Python | Gap |
|---------|:--:|:------:|:---:|
| `defineTool({multipart: true})` | ✅ Supported. Creates a `MultipartToolAction` of type `tool.v2`. | ❌ Not supported. `define_tool` has no `multipart` parameter. | **G18** |
| `MultipartToolAction` type | ✅ `tool.ts:107-122` — Action with `tool.v2` type, returns `{output?, content?}`. | ❌ Does not exist. | **G18** |
| `MultipartToolResponse` type | ✅ `parts.ts` — Schema with `output` and `content` fields. | ⚠️ Type exists in `typing.py:933` but unused in tool definition. | Partial |
| Auto-registration of `tool.v2` | ✅ Non-multipart tools are also registered as `tool.v2` with wrapped output. | ❌ No dual registration. | **G18** |

**JS** (`js/ai/src/tool.ts:306-335`):
```ts
export function defineTool(registry, config, fn) {
  const a = tool(config, fn);
  registry.registerAction(config.multipart ? 'tool.v2' : 'tool', a);
  if (!config.multipart) {
    // Non-multipart tools also get a v2 registration
    registry.registerAction('tool.v2', basicToolV2(config, fn));
  }
  return a;
}
```

**Impact**: Medium. Multipart tools allow returning both structured output AND rich content parts (media, text, etc.) from a single tool invocation. This is important for tools that produce images, audio, or other media alongside data.

### 8i. Model API V2 (New Streaming Interface)

**Status**: ❌ Missing in Python

| Feature | JS | Python | Gap |
|---------|:--:|:------:|:---:|
| `defineModel({apiVersion: 'v2'})` | ✅ New model runner signature: `(request, options: ActionFnArg) => Promise<response>` | ❌ Python uses the v1 pattern with separate `streaming_callback`. | **G19** |
| `ActionFnArg` | ✅ Unified options object with `onChunk`, `context`, `abortSignal`, `registry`. | ❌ Python passes `streaming_callback` as a separate parameter. | **G19** |

**JS** (`js/genkit/src/genkit.ts:301-309`):
```ts
defineModel<CustomOptionsSchema>(options: {
    apiVersion: 'v2';
  } & DefineModelOptions<CustomOptionsSchema>,
  runner: (
    request: GenerateRequest<CustomOptionsSchema>,
    options: ActionFnArg<GenerateResponseChunkData>
  ) => Promise<GenerateResponseData>
): ModelAction<CustomOptionsSchema>;
```

**Impact**: Medium. The V2 interface is cleaner and extensible (new fields can be added to `ActionFnArg` without breaking changes). The V1 interface with a positional `streamingCallback` parameter is still supported in JS for backward compatibility. Python's approach is functionally equivalent but doesn't benefit from the unified options pattern.

### 8j. Genkit Constructor Parameters

**Status**: ⚠️ Minor Gaps

| Parameter | JS (`GenkitOptions`) | Python (`Genkit.__init__`) | Gap |
|-----------|:---:|:---:|:---:|
| `plugins` | ✅ | ✅ | ✅ Parity |
| `model` | ✅ (default model) | ✅ | ✅ Parity |
| `promptDir` | ✅ | ✅ `prompt_dir` | ✅ Parity |
| `context` | ✅ Sets `registry.context` for default action context. | ❌ Not supported. | **G20** |
| `clientHeader` | ✅ Appends to `x-goog-api-client` header via `setClientHeader()`. | ❌ Not supported. `GENKIT_CLIENT_HEADER` is a constant. | **G21** |
| `name` | ✅ Display name shown in Dev UI. Passed to `ReflectionServer`. | ❌ Not supported. | **G22** |

**JS** (`js/genkit/src/genkit.ts:159-172`):
```ts
export interface GenkitOptions {
  plugins?: (GenkitPlugin | GenkitPluginV2)[];
  promptDir?: string;
  model?: ModelArgument<any>;
  context?: ActionContext;      // ← Python missing (G20)
  name?: string;                // ← Python missing (G22)
  clientHeader?: string;        // ← Python missing (G21)
}
```

**Impact**: Low-Medium.
- `context` (G20): Useful for setting default auth/metadata for all actions. Python users can set context per-call.
- `clientHeader` (G21): Used for attribution tracking. The constant `GENKIT_CLIENT_HEADER` covers the base case; the parameter allows customization (e.g., adding Firebase plugin version info).
- `name` (G22): Purely cosmetic — shown in the Dev UI sidebar. Used to distinguish multiple Genkit instances.

### 8k. Go API/Behavior Deep-Dive vs JS Canonical

**Status**: ⚠️ Partial parity with targeted API gaps

| Capability | JS | Go | Gap ID | Notes |
|------------|----|----|:------:|------|
| Dynamic action provider API | `defineDynamicActionProvider` ✅ | ❌ | G23 | No equivalent public API in `go/genkit` |
| Indexer definition API | `defineIndexer` ✅ | ❌ | G24 | No generic `DefineIndexer` API |
| Reranker definition/runtime | `defineReranker` + `rerank` ✅ | ❌ | G25 | Reranker types exist, but no public define/runtime APIs |
| High-level chat/session API | `chat` / `createSession` ✅ | ❌ (session primitives only) | G26 | Go has `core/x/session`, not JS-equivalent high-level API |
| Built-in model middleware parity | 7 built-ins ✅ | 4 built-ins (`simulateSystemPrompt`, `augmentWithContext`, `validateSupport`, `DownloadRequestMedia`) | G27 | Missing `retry`, `fallback`, `simulateConstrainedGeneration` |
| Model API V2 parity semantics | `apiVersion: 'v2'` ✅ | ❌ | G28 | No explicit v2 model runner interface |
| Constructor option parity | `context`, `name`, `clientHeader` ✅ | ❌ | G29 | Go has `WithDefaultModel`, `WithPromptDir`, `WithPlugins`, but not these JS options |
| Remote flow client helpers | `runFlow` / `streamFlow` ✅ | ❌ | G8 | No first-party equivalent helper package |

**Go-specific parity strengths**:
- Multipart tools are first-class (`DefineMultipartTool`) ✅
- Data prompt APIs are first-class (`DefineDataPrompt`) ✅
- Strong typed generate helpers (`GenerateText`, `GenerateData`, `GenerateDataStream`) ✅

**Go-only middleware** (not present in JS or Python — Go-specific additions):
- `addAutomaticTelemetry()` — OTel instrumentation automatically added to all models
- `validateVersion()` — Validates requested model version against supported versions list
- `CalculateInputOutputUsage()` — Public utility to compute character/media counts for usage tracking

**Go-only Lookup/Load APIs**:
- `LoadPromptDirFromFS()` — Supports Go `embed.FS` for embedded prompt files
- `LoadPromptFromSource()` — Loads a prompt from raw string content (not a file path)
- `LookupDataPrompt()` — Typed lookup for data prompts
- `LookupPlugin()` — Retrieves a registered plugin by name (not in Python)
- `NewResource()` — Creates an unregistered resource (Python has `dynamic_resource()` equivalent)
- `FindMatchingResource()` — Finds resource matching a URI pattern (Python has `find_matching_resource()` equivalent)
- `ListResources()` — Lists all registered resources

---

## 9. Gap Summary — Prioritized Fix List

### 9a. Consolidated Gap Register (Implementation-Ready)

| Gap ID | SDK | Gap | Priority | Primary Files to Touch | Fast Validation |
|--------|-----|-----|:--------:|------------------------|-----------------|
| G1 | Python | `define_model(use=[...])` ~~missing~~ **done** | P1 | `py/packages/genkit/src/genkit/ai/_registry.py` | ✅ PR #4516 |
| G2 | Python | Action-level middleware storage ~~missing~~ **done** | P1 | `py/packages/genkit/src/genkit/core/action/_action.py` | ✅ PR #4516 |
| G3 | Python | `simulate_constrained_generation` ~~missing~~ **in PR** | P1 | `py/packages/genkit/src/genkit/blocks/middleware.py` | 🔄 PR #4510 |
| G4 | Python | `augment_with_context` lifecycle mismatch | P2 | `py/packages/genkit/src/genkit/blocks/generate.py`, `.../blocks/model.py` | ⬜ depends on G38 |
| G5 | Python | `X-Genkit-Span-Id` header ~~missing~~ **done** | P1 | `py/packages/genkit/src/genkit/core/reflection.py` | ✅ PR #4511 (merged) |
| G6 | Python | `on_trace_start` ~~lacks~~ **now passes** `span_id` | P1 | `py/packages/genkit/src/genkit/core/action/_action.py`, `.../core/reflection.py` | ✅ PR #4511 (merged) |
| G7 | Python | DAP discovery missing from `/api/actions` | P1 | `py/packages/genkit/src/genkit/core/reflection.py`, `.../core/registry.py` | ⏳ Deferred |
| G8 | Go + Python (separate impls) | no `runFlow`/`streamFlow` client helpers | P2 | Go: new `go/genkit/client` package; Python: new `py/packages/genkit/src/genkit/client` | ⏳ Deferred |
| G9 | Python | Pinecone plugin parity | P2 | new plugin under `py/plugins/pinecone` | ⬜ |
| G10 | Python | Chroma plugin parity | P2 | new plugin under `py/plugins/chroma` | ⬜ |
| G11 | Python | ~~missing~~ plugin/core `CHANGELOG.md` **done** | P3 | all `py/plugins/*`, `py/packages/genkit` | ✅ PR #4507 + #4508 (merged) |
| G12 | Python | `retry` middleware ~~missing~~ **in PR** | P1 | `py/packages/genkit/src/genkit/blocks/middleware.py` | 🔄 PR #4510 |
| G13 | Python | `fallback` middleware ~~missing~~ **in PR** | P1 | `py/packages/genkit/src/genkit/blocks/middleware.py` | 🔄 PR #4510 |
| G14 | Python | `validate_support` middleware ~~missing~~ **in PR** | P2 | `py/packages/genkit/src/genkit/blocks/middleware.py` | 🔄 PR #4510 |
| G15 | Python | `download_request_media` middleware ~~missing~~ **in PR** | P2 | `py/packages/genkit/src/genkit/blocks/middleware.py` | 🔄 PR #4510 |
| G16 | Python | `simulate_system_prompt` ~~missing~~ **in PR** | P2 | `py/packages/genkit/src/genkit/blocks/middleware.py` | 🔄 PR #4510 |
| G17 | Python | `api_key()` context provider missing | P3 | `py/packages/genkit/src/genkit/core/context.py` | ⬜ |
| G18 | Python | multipart tool (`tool.v2`) ~~missing~~ **in PR** | P1 | `py/packages/genkit/src/genkit/blocks/tools.py`, `.../blocks/generate.py` | 🔄 PR #4513 |
| G19 | Python | Model API V2 runner interface missing | P1 | `py/packages/genkit/src/genkit/ai/_registry.py`, `.../blocks/model.py` | ⬜ |
| G20 | Python | `Genkit(context=...)` ~~missing~~ **in PR** | P2 | `py/packages/genkit/src/genkit/ai/_aio.py` | 🔄 PR #4512 |
| G21 | Python | `Genkit(clientHeader=...)` ~~missing~~ **in PR** | P2 | `py/packages/genkit/src/genkit/ai/_aio.py`, `.../core/http_client.py` | 🔄 PR #4512 |
| G22 | Python | `Genkit(name=...)` ~~missing~~ **in PR** | P2 | `py/packages/genkit/src/genkit/ai/_aio.py`, `.../core/reflection.py` | 🔄 PR #4512 |
| G38 | Python | `get_model_middleware()` auto-wiring (new) | P1 | `py/packages/genkit/src/genkit/ai/_registry.py` | ⬜ depends on G1 ✅ |
| G23 | Go | `defineDynamicActionProvider` parity missing | P2 | `go/genkit/genkit.go`, `go/core/registry.go` | DAP action discovery + resolve test |
| G24 | Go | `defineIndexer` parity missing | P2 | `go/genkit/genkit.go`, `go/ai` indexing action | indexer registration + invoke test |
| G25 | Go | `defineReranker` + `rerank` runtime missing | P1 | `go/genkit/genkit.go`, `go/ai` reranker block | reranker registration + scoring call |
| G26 | Go | high-level `chat` / `createSession` missing | P2 | `go/genkit` wrapper over `core/x/session` | multi-turn stateful chat parity tests |
| G27 | Go | middleware parity (`retry`, `fallback`, constrained simulation) | P1 | `go/ai/model_middleware.go`, `go/ai/generate.go` | middleware behavior parity suite |
| G28 | Go | model API v2 parity semantics missing | P1 | `go/ai/generate.go`, `go/genkit/genkit.go` | v2 runner signature compatibility tests |
| G29 | Go | constructor parity (`context`,`clientHeader`,`name`) missing | P2 | `go/genkit/genkit.go` options | option propagation tests |
| G30 | Go + Python (separate impls) | Cloud SQL PG vector store parity missing | P2 | Go/Python plugin packages | vector store CRUD/retrieval sample |
| G31 | Python | no dedicated MCP parity sample | P2 | `py/samples/provider-mcp-*` (new) | sample runs + tools listed in reflection |
| G32 | Go + Python (separate impls) | web-serving endpoint behavior parity coverage missing | P3 | web adapter tests + docs | endpoint semantics parity matrix passes |
| G33 | Go + Python (separate impls) | LangChain integration parity missing | P3 | plugin scaffolding | minimal chain invocation sample |
| G34 | Go + Python (separate impls) | BloomLabs vector stores missing (Convex, HNSW, Milvus) | P3 | plugin scaffolding (`convex`,`hnsw`,`milvus`) | basic ingest/query smoke tests |
| G35 | Python | Groq provider parity missing (or compat-oai doc) | P3 | new plugin or `compat-oai` usage guide | basic model call test |
| G36 | Python | Cohere provider parity missing (or compat-oai doc) | P3 | new plugin or `compat-oai` usage guide | basic model call + embed test |
| G37 | Python | Graph workflows plugin parity missing | P3 | new plugin under `py/plugins/graph` | basic graph workflow test |

### 9b. Dependency Matrix

| Depends On | Unblocks | Why | Status |
|------------|----------|-----|:------:|
| G2 | G1, G3, G4, G12, G13, G14, G16 | Python model middleware architecture must exist before feature middleware parity | ✅ G2 done |
| G1 | G38 | Auto-wiring needs define_model(use=) to exist | ✅ G1 done |
| G38 | G3, G4, G14, G15, G16 | Auto-wired middleware needs the wiring helper | ⬜ |
| G6 | G5 | Need span ID in callback before header emission | ✅ Both done |
| G7, G23 | G31 | MCP parity sample quality depends on DAP discoverability in tooling | ⏳ |
| G25 | G27, G28 | Go reranker/model API work shares core generation extension points |
| G29 | G8 | constructor/client header parity helps consistent remote invocation behavior |

### 9c. Fast-Close Implementation Bundles

| Bundle | Scope | Gaps | Deliverable | Exit Tests |
|--------|-------|------|-------------|------------|
| B1 | Python middleware foundation | G2, G1, G3, G12, G13, G14, G16 | full model middleware parity layer | middleware parity test suite green |
| B2 | Python reflection/protocol parity | G6, G5, G7 | trace/span headers + DAP discovery | reflection integration tests green |
| B3 | Python advanced model/tool parity | G18, G19, G4 | multipart + v2 model + ordering parity | tool.v2 + v2 runner tests green |
| B4 | Go API parity layer | G23, G24, G25, G26, G28, G29 | missing high-level APIs added | public API compile + behavior tests |
| B5 | Cross-SDK client/plugin parity | G8, G9, G10, G30, G31 | client helpers + plugin/sample parity | cross-SDK parity smoke suite green |
| B6 | Ecosystem/compliance | G11, G17, G32, G33, G34, G35, G36, G37 | docs/compliance + secondary plugins | consistency + sample smoke checks green |

### 9d. Prioritized Execution Order (All 3 SDKs)

1. B1: Python middleware foundation (highest behavior delta).
2. B2: Python reflection/protocol parity (Dev UI and observability correctness).
3. B4: Go API parity layer (largest JS-vs-Go surface gaps).
4. B3: Python advanced model/tool parity.
5. B5: cross-SDK client + plugin/sample parity.
6. B6: ecosystem/compliance.

### 9e. Cross-SDK Summary

| SDK | P1 Gaps | P2 Gaps | P3 Gaps | Critical Themes |
|-----|:-------:|:-------:|:-------:|-----------------|
| Python | 10 | 12 | 8 | middleware parity, multipart/v2 model parity, reflection parity, community ecosystem |
| Go | 3 | 6 | 3 | missing high-level APIs (DAP/indexer/reranker/chat), middleware and v2 parity |

| Overall Metric | Value |
|----------------|-------|
| Total tracked gaps (G1–G37) | 37 |
| P1 (release-blocking parity) | 13 |
| P2 (major parity) | 16 |
| P3 (follow-up parity) | 8 |

---

## 10. Implementation Roadmap (Python SDK Focus)

> Generated: 2026-02-08. Based on reverse topological sort of the dependency graph across all tracked Python gaps (G1–G37).

### 10a. Dependency Graph

The following directed acyclic graph (DAG) captures all prerequisite relationships between Python gaps. An edge `A → B` means **A must be completed before B can begin**.

```
Legend:  ───► = "is prerequisite for"
        (Pn) = priority level

FOUNDATION LAYER (no prerequisites)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  G2 (P1) Action middleware storage
    ├───► G1  (P1) define_model(use=[...])
    ├───► G12 (P1) retry middleware
    ├───► G13 (P1) fallback middleware
    ├───► G15 (P2) download_request_media middleware
    └───► G19 (P1) Model API V2 runner interface

  G1 (P1) define_model(use=[...])         [depends on G2]
    ├───► G3  (P1) simulate_constrained_generation
    ├───► G4  (P2) augment_with_context lifecycle fix
    ├───► G14 (P2) validate_support middleware
    └───► G16 (P2) simulate_system_prompt middleware

  G6 (P1) on_trace_start span_id
    └───► G5  (P1) X-Genkit-Span-Id header

  G7 (P1) DAP discovery in /api/actions
    └───► G31 (P2) MCP parity sample

  G21 (P2) Genkit(clientHeader=...)
    └───► G8  (P2) genkit.client module (run_flow/stream_flow)

INDEPENDENT NODES (no prerequisites, unblock nothing)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  G9  (P2) Pinecone plugin          G18 (P1) Multipart tool (tool.v2)
  G10 (P2) ChromaDB plugin          G20 (P2) Genkit(context=...)
  G11 (P3) CHANGELOG.md             G22 (P2) Genkit(name=...)
  G17 (P3) api_key() context        G30 (P2) Cloud SQL PG plugin
  G35 (P3) Groq provider            G36 (P3) Cohere provider
  G33 (P3) LangChain integration    G34 (P3) BloomLabs vector stores
  G37 (P3) Graph workflows
```

### 10b. Topological Sort — Dependency Levels

Reverse topological sort of the gap DAG yields the following dependency levels. Each level contains gaps whose prerequisites are all satisfied by prior levels. **Work within each level can be fully parallelized.**

| Level | Gaps | Prerequisites | Theme |
|:-----:|------|:--------------|-------|
| **L0** | G2, G6, G7, G18, G20, G21, G22, G9, G10, G11, G17, G30, G35, G36, G33, G34, G37 | *None* | Foundation + all independent work |
| **L1** | G1, G5, G12, G13, G15, G19, G31, G8 | G2, G6, G7, G21 | Middleware arch + protocol + client |
| **L2** | G3, G4, G14, G16 | G1 | Feature middleware requiring define-model-time wiring |

**Critical path** (longest chain): `G2 → G1 → G3` (3 levels deep, governs minimum calendar time for full P1 closure).

### 10c. Phased Roadmap

#### Phase 0 — Quick Wins (No Core Framework Changes Required)

> **Start immediately.** All items are independent of each other and of core framework work. Can run in parallel with all subsequent phases.

| ID | Work Item | Effort | Type |
|----|-----------|:------:|------|
| **QW-1** | **Test coverage uplift** for all "Minimum" and "Adequate" plugins (see §10f) | M | Testing |
| **QW-2** | **Verify all existing samples run** — execute every `py/samples/*/run.sh`, fix any breakage | M | Validation |
| **QW-3** | G11: Add `CHANGELOG.md` to all 20 plugins + core package (21 files) | XS | Compliance |
| **QW-4** | G22: Add `name` parameter to `Genkit()` constructor — pass to `ReflectionServer` display name | XS | Feature |
| **QW-5** | G17: Implement `api_key()` context provider in `core/context.py` | S | Feature |
| **QW-6** | G35: Groq provider — thin `compat-oai` wrapper + usage documentation | S | Plugin |
| **QW-7** | G36: Cohere provider — thin `compat-oai` wrapper + embedder support + docs | S | Plugin |

**Effort key**: XS = < 1 day, S = 1–2 days, M = 3–5 days, L = 1–2 weeks, XL = 2+ weeks.

**Why these are quick wins**: None of them touch the core action system, middleware dispatcher, or reflection server. Provider wrappers for Groq/Cohere reuse the existing `compat-oai` infrastructure. CHANGELOGs and constructor params are additive, zero-risk changes. Sample verification catches regressions early and requires no framework changes.

---

#### Phase 1 — Core Infrastructure Foundation

> **Prerequisite for Phases 2 and 3.** This is the highest-leverage work — it unblocks 11 downstream gaps.

| ID | Gap | Work Item | Files to Touch | Effort | Unblocks |
|----|-----|-----------|----------------|:------:|----------|
| **P1.1** | **G2** | Add `middleware` storage to `Action` class; implement `action_with_middleware()` wrapper that chains model-level middleware around `action.run()` | `core/action/_action.py` | L | G1, G12, G13, G15, G19 |
| **P1.2** | **G6** | Update `on_trace_start` callback signature to `(trace_id: str, span_id: str)` throughout action system | `core/action/_action.py`, `core/reflection.py`, `core/trace/` | S | G5 |
| **P1.3** | **G18** | Add multipart tool support: `define_tool(multipart=True)`, `MultipartToolAction` type `tool.v2`, dual registration for non-multipart tools | `blocks/tools.py`, `blocks/generate.py` | M | — |
| **P1.4** | **G20** | Add `context` parameter to `Genkit()` that sets `registry.context` for default action context | `ai/_aio.py` | XS | — |
| **P1.5** | **G21** | Add `clientHeader` parameter to `Genkit()` that appends to `GENKIT_CLIENT_HEADER` via `set_client_header()` | `ai/_aio.py`, `core/http_client.py` | XS | G8 |

**Exit criteria**: All unit tests green for action middleware dispatch, span_id propagation, tool.v2 registration, and constructor parameter propagation.

---

#### Phase 2 — Middleware Architecture & Protocol Parity

> **Depends on Phase 1** (specifically G2 for middleware gaps, G6 for span header). All items within this phase can be parallelized.

| ID | Gap | Work Item | Files to Touch | Effort | Unblocks |
|----|-----|-----------|----------------|:------:|----------|
| **P2.1** | **G1** | Add `use` parameter to `define_model()`; pass middleware list to `Action` via `action_with_middleware()` from Phase 1 | `ai/_registry.py`, `blocks/model.py` | M | G3, G4, G14, G16 |
| **P2.2** | **G5** | Emit `X-Genkit-Span-Id` response header in reflection server using span_id from updated callback | `core/reflection.py` | XS | — |
| **P2.3** | **G12** | Implement `retry()` middleware: exponential backoff with jitter, configurable statuses (UNAVAILABLE, DEADLINE_EXCEEDED, RESOURCE_EXHAUSTED, ABORTED, INTERNAL), `max_retries`, `initial_delay_ms`, `max_delay_ms`, `backoff_factor`, `on_error` callback | `blocks/middleware.py` | M | — |
| **P2.4** | **G13** | Implement `fallback()` middleware: ordered model list, configurable error statuses, `on_error` callback, model resolution via registry | `blocks/middleware.py` | M | — |
| **P2.5** | **G15** | Implement `download_request_media()` middleware: download `http(s)` media URLs → data URIs, `max_bytes` limit, `filter` predicate | `blocks/middleware.py` | S | — |
| **P2.6** | **G19** | Add Model API V2: `define_model(api_version='v2')` with unified `ActionFnArg` options object (`on_chunk`, `context`, `abort_signal`, `registry`); maintain backward-compatible v1 path | `ai/_registry.py`, `blocks/model.py` | L | — |

**Exit criteria**: Full middleware parity test suite green — retry with mock flaky model, fallback chain invocation, media download roundtrip, v2 runner signature tests. Reflection server returns `X-Genkit-Span-Id` in all action run responses.

---

#### Phase 3 — Feature Middleware Parity

> **Depends on Phase 2** (specifically G1: `define_model(use=[...])`). These middleware functions are applied at **define-model time** as part of the model's built-in middleware chain.

| ID | Gap | Work Item | Files to Touch | Effort | Unblocks |
|----|-----|-----------|----------------|:------:|----------|
| **P3.1** | **G3** | Implement `simulate_constrained_generation()` middleware: inject JSON schema instructions into prompt for models with `supports.constrained = 'none'` or `'no-tools'`; clear `constrained`, `format`, `content_type`, `schema` from output config | `blocks/middleware.py` | M | — |
| **P3.2** | **G4** | Move `augment_with_context()` from call-time to define-model time: add unconditionally (when `supports.context` is false) to model middleware chain via `get_model_middleware()`, remove conditional addition from `generate.py` | `blocks/middleware.py`, `blocks/model.py`, `blocks/generate.py` | S | — |
| **P3.3** | **G14** | Implement `validate_support()` middleware: validate request against model `supports` declaration (media, tools, multiturn, system prompt); throw descriptive `GenkitError` with model name and unsupported feature details | `blocks/middleware.py` | S | — |
| **P3.4** | **G16** | Implement `simulate_system_prompt()` middleware: convert system messages into user/model turn pairs with configurable preface and acknowledgement strings | `blocks/middleware.py` | S | — |

**Exit criteria**: Every middleware has dedicated unit tests verifying: (a) correct request transformation, (b) passthrough when condition not met, (c) matching JS behavior for edge cases. Model middleware ordering test confirms: `validate_support → download_request_media → simulate_system_prompt → augment_with_context → simulate_constrained_generation → [user middleware] → runner`.

---

#### Phase 4 — Integration & Client Parity

> **Depends on**: G21 (Phase 1) for client helpers.

| ID | Gap | Work Item | Files to Touch | Effort | Unblocks |
|----|-----|-----------|----------------|:------:|----------|
| **P4.1** | **G8** | Implement `genkit.client` module with `run_flow()` (HTTP POST + JSON response) and `stream_flow()` (HTTP POST + NDJSON streaming response) helpers; use `httpx` with configurable `client_header` | New `client/` module | M | — |

**Exit criteria**: `run_flow` and `stream_flow` can invoke a deployed genkit flow endpoint over HTTP with correct headers and response parsing.

---

#### Phase 5 — Deferred & Ecosystem Parity

> **Deprioritized items.** Vector store plugins, DAP discovery, and community ecosystem work are deferred to focus on core framework 1:1 parity and existing plugin quality first.

| ID | Gap | Work Item | Effort | Notes |
|----|-----|-----------|:------:|-------|
| **P5.1** | G7 | DAP discovery in `/api/actions` — wire `get_action_metadata_record()` into reflection `handle_list_actions` | S | Deferred; unblocks G31 |
| **P5.2** | G31 | Dedicated MCP parity sample — depends on G7 DAP discovery | S | Deferred |
| **P5.3** | G9 | Pinecone vector store plugin (new `py/plugins/pinecone`) | M | Deferred |
| **P5.4** | G10 | ChromaDB vector store plugin (new `py/plugins/chroma`) | M | Deferred |
| **P5.5** | G30 | Cloud SQL PG vector store plugin (new `py/plugins/cloud-sql-pg`) | M | Deferred |
| **P5.6** | G33 | LangChain integration plugin | L | Evaluate if LangChain Python integration adds value given Python's existing rich plugin ecosystem |
| **P5.7** | G34 | BloomLabs vector stores (Convex, HNSW, Milvus) | L per store | Community-driven; consider as `compat-oai`-style shims or documentation-only |
| **P5.8** | G37 | Graph workflows plugin | L | Port `genkitx-graph` concepts; evaluate against native Python workflow libraries |

**Exit criteria**: Each plugin has README, tests, sample, and passes `check_consistency`.

---

### 10d. Dependency Graph — Visual Summary

```
  PHASE 0 (parallel)                PHASE 1              PHASE 2            PHASE 3          PHASE 4
  ════════════════                  ═══════              ═══════            ═══════          ═══════

  ┌──────────────────────┐
  │ QW: G11,G17,G22      │
  │ G35,G36              │     ┌────────┐       ┌────────┐       ┌────────┐
  │ G9,G10,G30           │     │  G2    │──────►│  G1    │──────►│  G3    │
  │ Test Coverage Uplift │     │  (P1)  │  ┌───►│  (P1)  │──┬──►│  (P1)  │
  └──────────────────────┘     └───┬────┘  │    └────────┘  │   ├────────┤
          │ (runs in parallel      │       │                ├──►│  G4    │
          │  with all phases)      ├───────┼──────────┐     │   │  (P2)  │
          ▼                        │       │          │     │   ├────────┤
                                   │       │          ▼     ├──►│  G14   │
                              ┌────┼───┐   │    ┌────────┐  │   │  (P2)  │
                              │    │   │   │    │  G12   │  │   ├────────┤
                              │    ▼   │   │    │  (P1)  │  └──►│  G16   │
                              │ ┌──────┤   │    ├────────┤      │  (P2)  │
                              │ │ G15  │   │    │  G13   │      └────────┘
                              │ │ (P2) │   │    │  (P1)  │
                              │ └──────┘   │    ├────────┤
                              │            │    │  G19   │
                              │            │    │  (P1)  │
                              │            │    └────────┘
     ┌────────┐          ┌────┴───┐   ┌────┴───┐
     │  G21   │─────────►│  G8    │   │  G5    │
     │  (P2)  │          │  (P2)  │   │  (P1)  │
     └────────┘          └────────┘   └────────┘
                                           ▲
     ┌────────┐                       ┌────┴───┐
     │  G7    │                       │  G6    │
     │  (P1)  │          ┌────────┐   │  (P1)  │
     └────┬───┘          │  G31   │   └────────┘
          └─────────────►│  (P2)  │
                         └────────┘

     ┌────────┐
     │  G18   │  (independent, Phase 1)
     │  (P1)  │
     └────────┘

     ┌────────┐  ┌────────┐
     │  G20   │  │  G22   │  (independent, Phase 0–1)
     │  (P2)  │  │  (P2)  │
     └────────┘  └────────┘
```

### 10e. Critical Path Analysis

| Path | Chain Length | Calendar Estimate | Covers |
|------|:-----------:|:-----------------:|--------|
| **G2 → G1 → G3** | 3 levels | ~4–5 weeks | Core middleware → define-model → constrained generation |
| **G2 → G1 → G14** | 3 levels | ~4–5 weeks | Core middleware → define-model → validate support |
| **G2 → G1 → G16** | 3 levels | ~4–5 weeks | Core middleware → define-model → system prompt simulation |
| **G2 → G12** | 2 levels | ~3 weeks | Core middleware → retry |
| **G2 → G13** | 2 levels | ~3 weeks | Core middleware → fallback |
| **G6 → G5** | 2 levels | ~1 week | Span callback → span header |
| **G21 → G8** | 2 levels | ~2 weeks | Client header → client module |
| ~~G7 → G31~~ | 2 levels | ~2 weeks | *(Deferred — DAP discovery → MCP sample)* |

**Bottleneck**: G2 (Action middleware storage) is the single highest-leverage item. It unblocks 5 direct dependents and 4 transitive dependents. **Prioritize G2 above all other work.**

### 10f. Test Coverage Uplift Plan

> Goal: Raise all plugins from "Minimum" (1 test file) or "Adequate" (2 files) to **comprehensive** coverage (4+ test files, 400+ lines total).

#### Target Test Dimensions per Plugin Type

**Model provider plugins** should test:

| Dimension | Test File | What to Verify |
|-----------|-----------|----------------|
| Plugin init | `plugin_init_test.py` | Model/embedder registration, capability declarations, config validation |
| Request transform | `request_transform_test.py` | Genkit `GenerateRequest` → provider API format (messages, tools, config, media) |
| Response transform | `response_transform_test.py` | Provider API response → Genkit `GenerateResponse` (content, usage, finish reason) |
| Streaming | `streaming_test.py` | Streaming chunk handling, partial response assembly, backpressure |
| Error handling | `error_handling_test.py` | API errors, rate limits, auth failures, timeout, malformed responses |
| Tool calls | `tool_calls_test.py` | Tool call request/response roundtrip (if model supports tools) |
| Multi-turn | `multiturn_test.py` | Conversation history formatting, role mapping |

**Vector store plugins** should test:

| Dimension | Test File | What to Verify |
|-----------|-----------|----------------|
| Plugin init | `plugin_init_test.py` | Retriever/indexer registration, client configuration |
| Indexing | `indexing_test.py` | Document ingestion, embedding generation, upsert |
| Retrieval | `retrieval_test.py` | Query → results, similarity scoring, top-k, metadata filtering |
| Error handling | `error_handling_test.py` | Connection failures, missing collections, invalid queries |

**Framework/utility plugins** should test:

| Dimension | Test File | What to Verify |
|-----------|-----------|----------------|
| Plugin init | `plugin_init_test.py` | Middleware registration, configuration |
| Request lifecycle | `lifecycle_test.py` | Request → processing → response pipeline |
| Error handling | `error_handling_test.py` | Framework errors, validation failures |
| Integration | `integration_test.py` | End-to-end with mock services |

#### Per-Plugin Uplift Targets

| Plugin | Current | Target | New Tests Needed | Priority |
|--------|:-------:|:------:|:----------------:|:--------:|
| **dev-local-vectorstore** | 1 file, 32 lines | 4 files, 300+ lines | indexing, retrieval, error handling, concurrent access | High |
| **firebase** | 1 file, 43 lines | 4 files, 400+ lines | auth integration, Firestore ops, telemetry, error handling | High |
| **evaluators** | 1 file, 65 lines | 4 files, 300+ lines | evaluator execution, scoring, batch evaluation, custom metrics | High |
| **flask** | 1 file, 88 lines | 4 files, 400+ lines | route registration, request/response lifecycle, streaming, error handling | Medium |
| **observability** | 1 file, 128 lines | 4 files, 400+ lines | span export, metric collection, OTLP format, error traces | Medium |
| **google-cloud** | 1 file, 341 lines | 4 files, 600+ lines | trace export, log correlation, metric upload, auth/config | Medium |
| **microsoft-foundry** | 1 file, 309 lines | 4 files, 500+ lines | request/response transform, streaming, error handling, tool calls | Medium |
| **checks** | 1 file, 333 lines | 3 files, 500+ lines | policy evaluation, safety scoring, error handling | Medium |
| **cloudflare-workers-ai** | 1 file, 496 lines | 3 files, 600+ lines | streaming, error handling, model-specific features | Low |
| **amazon-bedrock** | 2 files, 1190 lines | 4 files, 1400+ lines | streaming, tool calls, multi-turn | Low |
| **deepseek** | 2 files, 374 lines | 4 files, 600+ lines | streaming, error handling, tool calls | Medium |
| **huggingface** | 2 files, 450 lines | 4 files, 600+ lines | streaming, error handling, model variants | Medium |
| **xai** | 2 files, 481 lines | 4 files, 600+ lines | streaming, error handling, tool calls | Medium |

### 10g. Execution Timeline

```
Week   1    2    3    4    5    6    7    8    9   10   11   12
      ──── ──── ──── ──── ──── ──── ──── ──── ──── ──── ──── ────
P0    ████████████████████████████████████████████████████████████  Quick wins + test uplift + sample verification (continuous)
P1    ████████████████                                             G2, G6, G18, G20, G21
P2              ████████████████                                   G1, G5, G12, G13, G15, G19
P3                        ████████████                             G3, G4, G14, G16
P4                                    ████████                     G8
P5                                              ████████████████── G7, G31, G9, G10, G30, G33, G34, G37 (deferred)

Milestone     ▲ P1 infra    ▲ Middleware     ▲ Full P1    ▲ Client
              complete      parity          closure     parity
              (week 3)      (week 5)        (week 7)    (week 9)
```

### 10h. PR Breakdown

> **Key rule**: Changes to core framework (`py/packages/genkit/`) MUST be sent as separate PRs from plugin (`py/plugins/`) and sample (`py/samples/`) changes. This keeps reviews focused, reduces blast radius, and allows independent rollback.
>
> **Process**: All PRs are created in **draft mode**. Default reviewers: **@zarinn3pal**, **@mengqinshen**, **@huangjeff5**.

#### PR Scope Categories

| Category | Path Prefix | Rule |
|----------|-------------|------|
| **Core** | `py/packages/genkit/src/genkit/` | One logical change per PR. Never mixed with plugin/sample code. |
| **Plugin** | `py/plugins/<name>/` | One plugin per PR. Tests ship with the code they cover. |
| **Sample** | `py/samples/` | Sample fixes can be batched. New samples get their own PR. |
| **Compliance** | Cross-cutting (CHANGELOG, LICENSE, etc.) | Can span multiple directories in a single PR. |

#### Phase 0 — Quick Win PRs

| PR | Scope | Gaps | Contents | Status |
|----|:-----:|------|----------|:------:|
| **PR-0a** → **#4507 + #4508** | Compliance | G11 | Add `CHANGELOG.md` to all 20 plugins + core package (21 files) | ✅ Merged |
| **PR-0b** | Sample | — | Run all `py/samples/*/run.sh`, fix any broken samples | ✅ Done (via #4488, #4503) |
| **PR-0c** → included in **#4512** | Core | G22 | `Genkit(name=...)` constructor param → `ReflectionServer` display name | 🔄 PR open |
| **PR-0d** | Core | G17 | `api_key()` context provider in `core/context.py` + tests | ⬜ Not started |
| **PR-0e** | Plugin | G35 | Groq provider — thin `compat-oai` wrapper plugin + tests + docs | ⬜ Not started |
| **PR-0f** | Plugin | G36 | Cohere provider — thin `compat-oai` wrapper plugin + tests + docs | ⬜ Not started |
| **PR-0g** → **#4509** | Plugin | — | Test coverage uplift across all 19 plugins | ✅ Merged |

*Phase 0 mostly complete — only G17, G35, G36 remain.*

#### Phase 1 — Core Infrastructure PRs

| PR | Scope | Gaps | Contents | Status |
|----|:-----:|------|----------|:------:|
| **PR-1a** → **#4516** | Core | G2, G1 | `Action(middleware=...)`, `register_action(middleware=...)`, `define_model(use=[...])`, `dispatch()` chains model-level MW after call-time MW, 3 tests + sample | 🔄 PR open |
| **PR-1b** → **#4511** | Core | G6, G5 | `on_trace_start(trace_id, span_id)` + `X-Genkit-Span-Id` response header | ✅ Merged |
| **PR-1c** → **#4513** | Core | G18 | Multipart tool support: `@ai.tool(multipart=True)`, `tool.v2` action kind, dual registration, 6 tests + sample | 🔄 PR open |
| **PR-1d** → **#4512** | Core | G20, G21, G22 | `Genkit(context=..., name=..., client_header=...)`, runtime file name field, 12 tests | 🔄 PR open |

*PR-1b is merged. PR-1a, PR-1c, PR-1d are in review.*

#### Phase 2 — Middleware Functions PR

| PR | Scope | Gaps | Contents | Status |
|----|:-----:|------|----------|:------:|
| **PR-2a** → **#4510** | Core | G3, G12, G13, G14, G15, G16 | All 6 middleware functions (`retry`, `fallback`, `validate_support`, `download_request_media`, `simulate_system_prompt`, `simulate_constrained_generation`) + extracted utilities + 38 tests | 🔄 PR open |
| **PR-2b** | Core | G38 | `get_model_middleware()` auto-wiring — inject middleware at define-model time based on `ModelInfo.supports`, matching JS `getModelMiddleware()` | ⬜ Not started |
| **PR-2c** | Core | G19 | Model API V2 runner interface — `define_model(api_version='v2')`, `ActionFnArg` options object, backward compat, tests | ⬜ Not started |

#### Phase 3 — Remaining Core Parity

| PR | Scope | Gaps | Contents | Depends On |
|----|:-----:|------|----------|:----------:|
| **PR-3a** | Core | G4 | Move `augment_with_context()` from generate-time to define-model time via G38 auto-wiring | PR-2b (G38) |
| **PR-3b** | Core | G8 | New `genkit.client` module — `run_flow()`, `stream_flow()` helpers, `httpx`-based, tests | PR-1d |

#### Other Open PRs (Bug Fixes & New Features)

| PR | Scope | Description | Status |
|----|:-----:|-------------|:------:|
| **#4514** | Core | `Transfer-Encoding: chunked` on standard action responses | 🔄 PR open |
| **#4504** | Plugin | Google Checks AI Safety plugin + sample | 🔄 PR open |
| **#4495** | Core | Prevent infinite recursion in `create_prompt_from_file()` | 🔄 PR open |
| **#4494** | Core | `dropped_*` property overrides on `RedactedSpan` | 🔄 PR open |
| **#4401** | Core | Reflection API v2 (WebSocket + JSON-RPC 2.0) | 🔄 PR open |

#### PR Dependency Chain (Actual PRs)

```
MERGED
══════
#4511 (G5+G6: span_id + header) ────── ✅ Done
#4507 + #4508 (G11: CHANGELOG.md) ───── ✅ Done
#4509 (plugin test coverage) ────────── ✅ Done

INDEPENDENT (merge in any order)
════════════════════════════════
#4494 (RedactedSpan fix)         ─── no file conflicts
#4504 (Checks plugin)            ─── new plugin, no conflicts
#4510 (MW functions)             ─── blocks/middleware.py only
#4495 (Prompt recursion fix)     ─── core/registry.py overlap
#4514 (Transfer-Encoding fix)    ─── core/reflection.py overlap

LAYER 2 (after Layer 1)
═══════════════════════
#4401 (Reflection v2)            ─── rebase onto #4514
#4513 (Multipart tools)          ─── independent of #4401

LAYER 3 (last)
══════════════
#4512 (Constructor parity)       ─── rebase onto #4401 + #4495
#4516 (MW storage + sample)      ─── rebase onto #4513 + #4495 + #4512
```

#### PR Summary

| Phase | PRs | Status |
|:-----:|:---:|:------:|
| 0 | 7 planned | 4 merged, 3 not started |
| 1 | 4 (#4511, #4512, #4513, #4516) | 1 merged, 3 open |
| 2 | 3 (#4510, +2 not started) | 1 open, 2 not started |
| 3 | 2 (not started) | ⬜ |
| Other fixes | 3 (#4401, #4494, #4495) | All open |
| Plugin | 1 (#4504 Checks) | Open |

#### Immediate PR Manifest — Original Branch Split (Completed)

> The original `yesudeep/feat/checks-plugin` branch was split into 5 PRs as planned.
> All have been sent — A, B, C merged; D (#4504) open; E (sample bundled with D).

| PR | Branch | Status |
|----|--------|:------:|
| **A** | `yesudeep/chore/py-typed-compliance` | ✅ Merged (part of #4488) |
| **B** | `yesudeep/chore/check-consistency-updates` | ✅ Merged (part of #4488) |
| **C** | `yesudeep/docs/parity-audit` | ✅ Merged (#4505) |
| **D** | `yesudeep/feat/checks-plugin` | 🔄 PR #4504 open |
| **E** | (bundled with D) | 🔄 Included in #4504 |

### 10i. Summary Metrics

| Metric | Value |
|--------|-------|
| Total Python gaps | 31 (G1–G22, G30–G31, G33–G38) |
| **Done (merged to main)** | **5** — G5, G6, G11 (+ plugin test coverage) |
| **In review (PRs open)** | **14** — G1, G2, G3, G12–G16, G18, G20–G22 |
| **Not started** | **12** — G4, G7–G10, G17, G19, G30–G31, G33–G38 |
| Deferred | 5 items (G7, G8, G31, G33–G37) |
| Open PRs | 9 (#4401, #4494, #4495, #4504, #4510, #4512, #4513, #4514, #4516) |
| Critical path remaining | G38 → G4 (auto-wiring → context lifecycle) |
| Plugins needing test uplift | ~~13~~ improved via PR #4509 (merged) |
