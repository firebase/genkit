# Genkit Feature Parity Audit — JS / Go / Python

> Generated: 2025-02-08. Updated: 2026-02-13. Baseline: `firebase/genkit` JS implementation, with explicit JS vs Go vs Python parity tracking.
> Last verified: 2026-02-13 against genkit-ai org (14 repos) and BloomLabsInc/genkit-plugins.

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
| Cohere | `cohere` | — | — | ✅ | Python-only |
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
| FastAPI | `fastapi` | — | — | ✅ | Python-only |
| Server plugin | `server` | — | ✅ | — | Go-only |
| **Other** | | | | | |
| LangChain | `langchain` | ✅ | — | — | JS-only |
| Internal helpers | `internal` | — | ✅ | — | Go internal |

### 1b. Coverage Metrics

| Metric | JS | Go | Python |
|--------|:--:|:--:|:------:|
| Total in-tree plugins | 18 | 16 | 22 |
| Shared (JS+Go+Python) | 11 | 11 | 11 |
| Model provider plugins | 6 | 4 | 13 |
| Vector store plugins | 4 | 4 | 1 |
| Unique to this SDK | 7 | 5 | 11 |

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
| `genkitx-cohere` | `BloomLabsInc/genkit-plugins` | JS | ✅ `cohere` (in-tree) | ✅ |
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
| Canonical internal sample/testapp set | 32 (`js/testapps`) | 37 (`go/samples`) | 39 runnable (`py/samples`, excluding `shared`, `sample-test`) | Primary parity baseline |
| Public showcase samples | 9 (`samples/js-*`) | — | — | Public docs/demo set |
| Total directories under samples root | — | 37 | 41 | Python includes utility dirs (`shared`, `sample-test`) |

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
| amazon-bedrock | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (4) | ✅ |
| anthropic | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (3) | ✅ |
| checks | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (1) | ✅ |
| cloudflare-workers-ai | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (4) | ✅ |
| compat-oai | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (7) | ✅ |
| deepseek | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (3) | ✅ |
| dev-local-vectorstore | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (4) | ✅ |
| evaluators | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (3) | ✅ |
| firebase | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (3) | ✅ |
| flask | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (3) | ✅ |
| google-cloud | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (3) | ✅ |
| google-genai | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (9) | ✅ |
| huggingface | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (3) | ✅ |
| mcp | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (5) | ✅ |
| microsoft-foundry | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (4) | ✅ |
| mistral | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (4) | ✅ |
| observability | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (3) | ✅ |
| ollama | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (5) | ✅ |
| vertex-ai | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (4) | ✅ |
| xai | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (4) | ✅ |
| cohere | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (5) | ✅ |
| fastapi | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ (0) | ⚠️ |

**Legend**: ✅ = present, ❌ = missing, ⚠️ = mostly OK

### 3c. Missing Files Summary

| Issue | Count | Affected |
|-------|:-----:|----------|
| Missing `py.typed` | ~~9~~ **0** | All fixed ✅ |
| Missing `CHANGELOG.md` | ~~21~~ **0** | All fixed ✅ (G11) |
| Missing sample `LICENSE` | ~~1~~ **0** | `provider-checks-hello` fixed ✅ |
| Missing tests | 1 | `fastapi` plugin (0 test files) |

### 3d. Core Package (`packages/genkit`)

| Item | Status |
|------|:------:|
| LICENSE | ✅ |
| README.md | ✅ |
| pyproject.toml | ✅ |
| CHANGELOG.md | ✅ |
| py.typed | ✅ |
| tests/ | ✅ (44 test files) |

### 3e. Sample Compliance

All 39 samples have: `README.md` ✅, `run.sh` ✅, `pyproject.toml` ✅, `LICENSE` ✅.

---

## 4. Test Coverage Summary

| Component | Test Files | Notes |
|-----------|:----------:|-------|
| **Core** (`packages/genkit`) | 44 | Comprehensive |
| **google-genai** | 9 | Best-covered plugin |
| **compat-oai** | 7 | Well-covered |
| **cohere** | 5 | Well-covered |
| **mcp** | 5 | Well-covered |
| **ollama** | 5 | Well-covered |
| **amazon-bedrock** | 4 | Good |
| **cloudflare-workers-ai** | 4 | Good |
| **dev-local-vectorstore** | 4 | Good |
| **microsoft-foundry** | 4 | Good |
| **mistral** | 4 | Good |
| **vertex-ai** | 4 | Good |
| **xai** | 4 | Good |
| **anthropic** | 3 | Good |
| **deepseek** | 3 | Good |
| **evaluators** | 3 | Good |
| **firebase** | 3 | Good |
| **flask** | 3 | Good |
| **google-cloud** | 3 | Good |
| **huggingface** | 3 | Good |
| **observability** | 3 | Good |
| **checks** | 1 | Minimal |
| **fastapi** | 0 | ❌ No tests |
| **Total (plugins)** | 84 | 20 of 22 plugins have tests |
| **Total (workspace)** | 128+ | Including core + samples |

---

## 5. Core Framework Parity — Module-Level API Comparison

### 5a. Define / Registration APIs

| API | JS (`Genkit` class) | Go (`genkit` pkg) | Python (`Genkit` / `GenkitRegistry`) | Status |
|-----|:---:|:---:|:---:|:---:|
| `defineFlow` | ✅ | ✅ `DefineFlow` | ✅ `.flow()` decorator | ✅ |
| `defineStreamingFlow` | ✅ (via options) | ✅ `DefineStreamingFlow` | ✅ (via streaming param) | ✅ |
| `defineTool` | ✅ | ✅ `DefineTool` | ✅ `.tool()` decorator | ✅ |
| `defineToolWithInputSchema` | — | ✅ `DefineToolWithInputSchema` | — | Go-only |
| `defineTool({multipart: true})` | ✅ | ✅ `DefineMultipartTool` | ✅ `.tool(multipart=True)` | ✅ (PR #4513) |
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
| `defineTool({multipart: true})` | ✅ | ✅ | ✅ | — | ✅ Done (PR #4513) |
| ~~Model API V2 (`apiVersion: 'v2'`)~~ | ~~✅~~ | ~~❌~~ | ~~❌~~ | ~~Go + Python~~ | ~~Superseded by Middleware V2 + Bidi~~ |
| **Generate Middleware V2** (3-tier: `generate`/`model`/`tool` hooks) | 🔄 RFC | 🔄 RFC | ❌ | All SDKs | P0 |
| **`defineBidiAction`** | 🔄 | 🔄 RFC | ❌ | Go + Python | P1 |
| **`defineBidiFlow`** | 🔄 | 🔄 RFC | ❌ | Go + Python | P1 |
| **`defineBidiModel`** / `generateBidi` | 🔄 | 🔄 RFC | ❌ | Go + Python | P1 |
| **`defineAgent`** (replaces Chat API) | 🔄 RFC | 🔄 RFC | ❌ | Go + Python | P1 |
| **Plugin V2** (plugins provide middleware) | ✅ | ❌ | ❌ | Go + Python | P2 |
| **Reflection API V2** (WebSocket + JSON-RPC 2.0) | 🔄 | 🔄 | 🔄 (draft) | All SDKs | P1 |
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
| Cohere provider (`genkitx-cohere`) | ✅ (community) | — | ✅ `cohere` (in-tree) | Python | ✅ |
| Azure OpenAI (`genkitx-azure-openai`) | ✅ (community) | — | ✅ `microsoft-foundry` (superset) | Python | ✅ |
| Convex vector store (`genkitx-convex`) | ✅ (community) | — | ❌ | Python | P3 |
| HNSW vector store (`genkitx-hnsw`) | ✅ (community) | — | ❌ | Python | P3 |
| Milvus vector store (`genkitx-milvus`) | ✅ (community) | — | ❌ | Python | P3 |
| Graph workflows (`genkitx-graph`) | ✅ (community) | — | ❌ | Python | P3 |

### 5h. Python-Only Features

| Feature | Notes |
|---------|-------|
| 9 unique model providers | Bedrock, Cloudflare Workers AI, Cohere, DeepSeek, HuggingFace, MS Foundry, Mistral, xAI, Observability |
| Flask + FastAPI plugins | Python web framework integrations |
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
| `genkitx-cohere` | Provider (Cohere) | ✅ `cohere` (in-tree) | ✅ |
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
| Community model providers (6) | 4 of 6 covered | ⚠️ |
| Community vector stores (3) | 0 of 3 covered | ❌ |
| Community other plugins (1) | 0 of 1 covered | ❌ |
| genkit-ai org plugins (5) | All covered via in-tree equivalents | ✅ |
| Priority relative to JS-canonical parity | Secondary | ⚠️ |

**Note on community provider gaps**: The missing community provider `genkitx-groq` could potentially be addressed via `compat-oai` since Groq offers an OpenAI-compatible API endpoint. However, a dedicated plugin would provide optimal model capability declarations and embedder support. Cohere is now covered by the in-tree `cohere` plugin ([#4518](https://github.com/firebase/genkit/pull/4518)).

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

> Updated: 2026-02-13. Status legend: ⬜ = not started, 🔄 = PR open, ✅ = merged, ⏳ = deferred, ⏸️ = paused (blocked on upstream), ~~struck~~ = superseded.

| Gap ID | SDK | Work Item | Reference | Status | PR |
|--------|-----|-----------|-----------|:------:|:---|
| **G38** | Python | **Generate-level middleware V2** — 3-tier hooks (`generate`/`model`/`tool`), `define_middleware`, registry | §8l | ⬜ Blocked | Upstream: JS [#4515](https://github.com/firebase/genkit/pull/4515), Go [#4422](https://github.com/firebase/genkit/pull/4422) |
| G2 → G1 | Python | Add `middleware` storage to `Action`, then add `use=` to `define_model` | §8b.1 | ⏸️ Superseded | [#4516](https://github.com/firebase/genkit/pull/4516) — open but superseded, pending G38 |
| G7 | Python | Wire DAP action discovery into `GET /api/actions` | §8a, §8c.5 | ⬜ Reverted | [#4459](https://github.com/firebase/genkit/pull/4459) merged then reverted by [#4469](https://github.com/firebase/genkit/pull/4469) — needs re-land |
| G6 → G5 | Python | Pass `span_id` in `on_trace_start`, send `X-Genkit-Span-Id` | §8c.3, §8c.4 | ✅ Done | [#4511](https://github.com/firebase/genkit/pull/4511) |
| G3 | Python | Implement `simulate_constrained_generation` middleware | §8b.3, §8f | ⏸️ Paused | [#4510](https://github.com/firebase/genkit/pull/4510) (closed) — needs new PR after G38 |
| G12 | Python | Implement `retry` middleware | §8f | ⏸️ Paused | [#4510](https://github.com/firebase/genkit/pull/4510) (closed) — needs new PR after G38 |
| G13 | Python | Implement `fallback` middleware | §8f | ⏸️ Paused | [#4510](https://github.com/firebase/genkit/pull/4510) (closed) — needs new PR after G38 |
| G14 | Python | Implement `validate_support` middleware | §8f | ⏸️ Paused | [#4510](https://github.com/firebase/genkit/pull/4510) (closed) — needs new PR after G38 |
| G15 | Python | Implement `download_request_media` middleware | §8f | ⏸️ Paused | [#4510](https://github.com/firebase/genkit/pull/4510) (closed) — needs new PR after G38 |
| G16 | Python | Implement `simulate_system_prompt` middleware | §8f | ⏸️ Paused | [#4510](https://github.com/firebase/genkit/pull/4510) (closed) — needs new PR after G38 |
| G18 | Python | Add multipart tool support (`defineTool({multipart: true})`) | §8h | 🔄 | [#4513](https://github.com/firebase/genkit/pull/4513) |
| ~~G19~~ | ~~Python~~ | ~~Add Model API V2 (`defineModel({apiVersion: 'v2'})`)~~ | ~~§8i~~ | ~~Superseded~~ | Replaced by G38 (middleware V2) + G41 (bidi models) |
| G20 | Python | Add `context` parameter to `Genkit()` constructor | §8j | 🔄 | [#4512](https://github.com/firebase/genkit/pull/4512) |
| G21 | Python | Add `clientHeader` parameter to `Genkit()` constructor | §8j | 🔄 | [#4512](https://github.com/firebase/genkit/pull/4512) |
| G22 | Python | Add `name` parameter to `Genkit()` constructor | §8j | 🔄 | [#4512](https://github.com/firebase/genkit/pull/4512) |
| G4 | Python | Move `augment_with_context` to define-model time | §8b.2 | ⏸️ Paused | [#4510](https://github.com/firebase/genkit/pull/4510) (closed) — logic valid, needs new PR after G38 |
| **G39** | Python | **Bidirectional Action** primitive (`define_bidi_action`) | §8m | ⬜ Blocked | Upstream: JS [#4288](https://github.com/firebase/genkit/pull/4288) |
| **G40** | Python | **Bidirectional Flow** primitive (`define_bidi_flow`) | §8m | ⬜ Blocked | Upstream: JS [#4288](https://github.com/firebase/genkit/pull/4288) |
| **G41** | Python | **Bidirectional Model** (`define_bidi_model`, `generate_bidi`) for real-time LLM APIs | §8m | ⬜ Blocked | Upstream: JS [#4210](https://github.com/firebase/genkit/pull/4210) |
| **G42** | Python | **Agent primitive** (`define_agent`) with session stores, replacing Chat API | §8n | ⬜ Blocked | Upstream: JS [#4212](https://github.com/firebase/genkit/pull/4212) |
| **G43** | Python | **Plugin V2 architecture** — plugins provide middleware arrays (`GenkitPluginV2`) | §8o | ⬜ | Upstream: JS [#4132](https://github.com/firebase/genkit/pull/4132) (merged) |
| **G44** | Python | **Reflection API V2** — WebSocket + JSON-RPC 2.0 | §8p | 🔄 | [#4401](https://github.com/firebase/genkit/pull/4401) (draft) |
| G9 | Python | Add Pinecone vector store plugin | §5g | ⏳ Deferred | — |
| G10 | Python | Add ChromaDB vector store plugin | §5g | ⏳ Deferred | — |
| G30 | Python | Add Cloud SQL PG vector store parity | §5g | ⏳ Deferred | — |
| G31 | Python | Add dedicated Python MCP parity sample | §2b/§9 | 🔄 | [#4248](https://github.com/firebase/genkit/pull/4248) |
| G8 | Python | Implement `genkit.client` (`run_flow` / `stream_flow`) | §5c/§9 | ⏳ Deferred | — |
| G17 | Python | Add built-in `api_key()` context provider | §8g | ⬜ | [#4521](https://github.com/firebase/genkit/pull/4521) (closed) — needs new PR |
| G11 | Python | Add `CHANGELOG.md` to plugins + core | §3c | ✅ Done | [#4507](https://github.com/firebase/genkit/pull/4507), [#4508](https://github.com/firebase/genkit/pull/4508) |
| G33 | Python | Consider LangChain integration parity | §1c/§9 | ⏳ Deferred | — |
| G34 | Python | Track BloomLabs vector stores (Convex, HNSW, Milvus) | §6b/§9 | ⏳ Deferred | — |
| G35 | Python | Add Groq provider (or document compat-oai usage) | §1d/§6b | ⬜ | — |
| G36 | Python | Add Cohere provider (or document compat-oai usage) | §1d/§6b | ✅ Done | [#4518](https://github.com/firebase/genkit/pull/4518) |
| G37 | Python | Track BloomLabs graph workflows plugin | §1d/§6b | ⏳ Deferred | — |

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
| **`X-Genkit-Span-Id`** | ✅ Set in `onTraceStart` callback (`reflection.ts:247`). | ✅ Set in `wrapped_on_trace_start` callback. Both streaming and non-streaming. | ✅ Fixed by [#4511](https://github.com/firebase/genkit/pull/4511) |
| `X-Genkit-Version` / `x-genkit-version` | ✅ Set as `X-Genkit-Version` in `onTraceStart` callback AND as `x-genkit-version` in non-streaming list endpoints. | ✅ Set as `x-genkit-version` in all responses. | ✅ Functionally equivalent (case-insensitive HTTP headers). |
| CORS `expose_headers` | Not explicitly shown (uses express CORS). | `['X-Genkit-Trace-Id', 'X-Genkit-Span-Id', 'x-genkit-version']` | ✅ Python is more explicit. |

#### 8c.4 `onTraceStart` Callback Shape

| Aspect | JS | Python | Gap |
|--------|-----|--------|-----|
| Callback arguments | `({traceId, spanId})` — receives **both** trace ID and span ID as a destructured object. | `(tid: str, sid: str)` — receives **both** trace ID and span ID. | ✅ Fixed by [#4511](https://github.com/firebase/genkit/pull/4511) |

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

**Python** (`py/.../core/reflection.py`):
```python
def wrapped_on_trace_start(tid: str, sid: str) -> None:
    nonlocal run_trace_id, run_span_id
    run_trace_id = tid
    run_span_id = sid
    on_trace_start(tid, sid)
    trace_id_event.set()
```

**Fixed**: `on_trace_start` now receives both `trace_id` and `span_id`, and `X-Genkit-Span-Id` is included in reflection response headers ([#4511](https://github.com/firebase/genkit/pull/4511)).

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
| `defineTool({multipart: true})` | ✅ Supported. Creates a `MultipartToolAction` of type `tool.v2`. | ✅ `.tool(multipart=True)` registers as `tool.v2` with metadata `tool.multipart=True`. | ✅ PR #4513 |
| `MultipartToolAction` type | ✅ `tool.ts:107-122` — Action with `tool.v2` type, returns `{output?, content?}`. | ✅ Registered under `ActionKind.TOOL_V2` with appropriate metadata. | ✅ PR #4513 |
| `MultipartToolResponse` type | ✅ `parts.ts` — Schema with `output` and `content` fields. | ✅ Multipart tool functions return `{output?, content?}` dict. | ✅ PR #4513 |
| Auto-registration of `tool.v2` | ✅ Non-multipart tools are also registered as `tool.v2` with wrapped output. | ✅ Non-multipart tools register both `tool` and `tool.v2` (v2 wraps output in `{output: result}`). | ✅ PR #4513 |

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

### 8l. Generate Middleware V2 — 3-Tier Hook Architecture (Active RFC)

> **JS RFC**: [#4515](https://github.com/firebase/genkit/pull/4515) (`@pavelgj`). **Go RFC**: [#4422](https://github.com/firebase/genkit/pull/4422) (`@apascal07`). **Go impl**: [#4464](https://github.com/firebase/genkit/pull/4464).
> **JS registered middleware**: [#3906](https://github.com/firebase/genkit/pull/3906) (`@pavelgj`).
> **Status**: Active development. The old `ModelMiddleware` type is being deprecated.

The middleware system is being redesigned from a single model-wrapping function to a 3-tier hook system:

| Hook | Scope | Called When |
|------|-------|------------|
| `generate` | Wraps entire generation including tool loop | Each `ai.generate()` call iteration |
| `model` | Wraps individual model API call | Each model invocation |
| `tool` | Wraps individual tool execution | Each tool call |

**JS API** (`generateMiddleware`):

```typescript
export const myMiddleware = generateMiddleware(
  { name: 'myMiddleware', configSchema: z.object({...}) },
  (config) => ({
    async generate(options, ctx, next) { return next(options, ctx); },
    async model(request, ctx, next) { return next(request, ctx); },
    async tool(request, ctx, next) { return next(request, ctx); },
    tools: [/* additional tools to inject */],
  })
);

// Usage: generate({..., use: [myMiddleware({verbose: true})]})
// Registry: ai.defineMiddleware('name', myMiddleware)
// Plugin: plugins: [myMiddleware.plugin()]
```

**Go API** (`Middleware` interface):

```go
type Middleware interface {
    Name() string
    New() Middleware  // per-invocation state
    Generate(ctx, *GenerateState, GenerateNext) (*ModelResponse, error)
    Model(ctx, *ModelState, ModelNext) (*ModelResponse, error)
    Tool(ctx, *ToolState, ToolNext) (*ToolResponse, error)
}
```

**Key design differences from old `ModelMiddleware`:**

| Aspect | Old (`ModelMiddleware`) | New (Middleware V2) |
|--------|------------------------|---------------------|
| Hooks | Model-call only | `generate` + `model` + `tool` |
| State | Stateless function | Per-invocation state (`New()`) |
| Registration | Anonymous function | Named, registerable, referenceable by string |
| Attachment | `define_model(use=[...])` only | `generate(use=[...])` + `define_model(use=[...])` + plugin |
| Config | None | Typed config schema (JSON Schema for Dev UI) |
| Tool injection | Not possible | `tools` field in middleware def |
| Reflection | Not visible | Listed in `/api/values?type=middleware` |

**Impact on Python gaps**: G1, G2, G3, G12–G16 must target this new architecture. Old `ModelMiddleware`-based implementations (#4510, #4516) are **paused** until the JS/Go canonical implementations land.

### 8m. Bidirectional Streaming Primitives (Active RFC)

> **JS RFC**: [#4210](https://github.com/firebase/genkit/pull/4210) (`@pavelgj`). **JS impl**: [#4288](https://github.com/firebase/genkit/pull/4288).
> **Go RFC**: [#4184](https://github.com/firebase/genkit/pull/4184) (`@apascal07`). **Go impl**: [#4387](https://github.com/firebase/genkit/pull/4387).
> **Status**: Active development in JS and Go. Python has no bidi work yet.

Adds three new primitives for bidirectional streaming:

| Primitive | Purpose | Init | Input Stream | Output Stream | Final Output |
|-----------|---------|------|-------------|---------------|-------------|
| `defineBidiAction` | Core bidi primitive | Setup context | `AsyncIterable<In>` | `AsyncIterable<Stream>` | `Output` |
| `defineBidiFlow` | Bidi action + observability | Setup context | `AsyncIterable<In>` | `AsyncIterable<Stream>` | `Output` |
| `defineBidiModel` | Specialized for real-time LLM APIs | `ModelRequest` (config, tools, system prompt) | `ModelRequest` (messages) | `ModelResponseChunk` | `ModelResponse` |

**JS usage pattern:**

```typescript
const session = await ai.generateBidi({
  model: myRealtimeModel,
  config: { temperature: 0.7 },
  system: 'You are a helpful assistant',
});
session.send('Hello!');
for await (const chunk of session.stream) { console.log(chunk.content); }
```

**`BidiConnection` / `BidiStreamingResponse`:**

```typescript
interface BidiStreamingResponse<O, S, I> {
  stream: AsyncGenerator<S>;  // Output stream
  output: Promise<O>;         // Final result
  send(chunk: I): void;       // Push input
  close(): void;              // End input stream
}
```

**Python implications**: Will need async generator-based implementation with `asyncio` channels. The `init` pattern maps well to Python's existing `GenerateRequest` types.

### 8n. Agent Primitive (Active RFC)

> **JS RFC**: [#4212](https://github.com/firebase/genkit/pull/4212) (`@pavelgj`).
> **Go RFC**: In [#4184](https://github.com/firebase/genkit/pull/4184) (`@apascal07`). **Go impl**: [#4462](https://github.com/firebase/genkit/pull/4462).
> **Status**: RFC stage. The JS RFC explicitly states *"`defineAgent` would replace the current Chat API."*

`defineAgent` is a high-level abstraction built on top of Bidi Flows for stateful multi-turn agents:

| Feature | Chat API (current) | Agent Primitive (new) |
|---------|-------------------|-----------------------|
| State management | Client-side history | Client-managed or server-managed (via `SessionStore`) |
| Streaming | Output only | Bidirectional (input + output) |
| Interrupts | Tool interrupts | Full human-in-the-loop with turn semantics |
| Session persistence | None built-in | Pluggable `SessionStore` (Postgres, Firestore, etc.) |
| Snapshots | None | Session snapshots for rollback |

**JS API:**

```typescript
const myAgent = ai.defineAgent(
  { name: 'myAgent', store: postgresSessionStore({...}) },
  async function* ({ inputStream, init, sendChunk }) {
    let messages = init?.messages ?? [];
    for await (const input of inputStream) {
      const response = await ai.generate({ messages: [...messages, input], model: ... });
      messages = response.messages;
    }
    return { sessionId: init?.sessionId, messages };
  }
);
```

**Python implications**: Will replace or extend the existing `Chat`/`Session` classes in `blocks/session/`. Needs async generator support and pluggable session store abstraction.

### 8o. Plugin V2 Architecture (JS Merged)

> **JS impl**: [#4132](https://github.com/firebase/genkit/pull/4132) (`@huangjeff5`, merged 2026-01-22).
> **Plugin migrations**: [#3541](https://github.com/firebase/genkit/pull/3541) (checks), [#3547](https://github.com/firebase/genkit/pull/3547) (ollama), [#3749](https://github.com/firebase/genkit/pull/3749) (googleai).
> **Status**: JS core merged. Plugin migrations in progress. Python + Go not started.

Plugin V2 adds a `version: 'v2'` field and a `generateMiddleware` method to the plugin interface, enabling plugins to provide middleware:

```typescript
interface GenkitPluginV2 {
  name: string;
  version: 'v2';
  model: (registry: Registry) => void;
  generateMiddleware?: () => GenerateMiddleware[];
}
```

**Key changes from Plugin V1:**
- Plugins can register middleware globally (not just models/embedders)
- `resolve()` pattern for deferred action creation (e.g., `ollama().model('phi3.5')`)
- Middleware plugins can be composed: `plugins: [myLogger.plugin(), retryPlugin()]`

**Python implications**: The current plugin system (`core/_plugins.py`) does not support middleware registration. Will need a V2 plugin interface once G38 (Middleware V2) lands.

### 8p. Reflection API V2 — WebSocket + JSON-RPC 2.0 (Active RFC)

> **RFC**: [#4211](https://github.com/firebase/genkit/pull/4211) (`@pavelgj`).
> **JS+CLI impl**: [#4295](https://github.com/firebase/genkit/pull/4295) (behind `--experimental-reflection-v2`).
> **Go impl**: [#4300](https://github.com/firebase/genkit/pull/4300) (draft).
> **Python impl**: [#4401](https://github.com/firebase/genkit/pull/4401) (draft).

Replaces the HTTP REST-based reflection server with WebSocket + JSON-RPC 2.0 for:
- Bidirectional streaming support (required for bidi actions/flows in Dev UI)
- Lower latency action invocation
- Server-push notifications (action progress, trace events)
- Multiplexed connections

**Python implications**: The existing `core/reflection.py` HTTP server needs a WebSocket transport layer. The Python draft (#4401) is already tracking this work.

---

## 9. Gap Summary — Prioritized Fix List

### 9a. Consolidated Gap Register (Implementation-Ready)

| Gap ID | SDK | Gap | Priority | Primary Files to Touch | Fast Validation |
|--------|-----|-----|:--------:|------------------------|-----------------|
| G1 | Python | `define_model(use=[...])` missing | P1 | `py/packages/genkit/src/genkit/ai/_registry.py` | unit: model registration accepts and stores `use` |
| G2 | Python | Action-level middleware storage missing | P1 | `py/packages/genkit/src/genkit/core/action/_action.py` | unit: middleware chain wraps action execution |
| G3 | Python | `simulate_constrained_generation` missing | P1 | `py/packages/genkit/src/genkit/blocks/middleware.py` | unit: constrained request on unsupported model rewrites prompt |
| G4 | Python | `augment_with_context` lifecycle mismatch | P2 | `py/packages/genkit/src/genkit/blocks/generate.py`, `.../blocks/model.py` | parity test: same middleware ordering as JS |
| G5 | Python | `X-Genkit-Span-Id` header missing | P1 | `py/packages/genkit/src/genkit/core/reflection.py` | integration: reflection response exposes span header |
| G6 | Python | `on_trace_start` lacks `span_id` | P1 | `py/packages/genkit/src/genkit/core/action/_action.py`, `.../core/reflection.py` | unit: callback receives trace+span |
| G7 | Python | DAP discovery missing from `/api/actions` | P1 | `py/packages/genkit/src/genkit/core/reflection.py`, `.../core/registry.py` | integration: DAP tools visible in action listing |
| G8 | Go + Python (separate impls) | no `runFlow`/`streamFlow` client helpers | P2 | Go: new `go/genkit/client` package; Python: new `py/packages/genkit/src/genkit/client` | e2e: invoke deployed flow HTTP+stream helper |
| G9 | Python | Pinecone plugin parity | P2 | new plugin under `py/plugins/pinecone` | plugin sample + retrieval roundtrip |
| G10 | Python | Chroma plugin parity | P2 | new plugin under `py/plugins/chroma` | plugin sample + retrieval roundtrip |
| G11 | Python | missing plugin/core `CHANGELOG.md` | P3 | all `py/plugins/*`, `py/packages/genkit` | consistency check passes |
| G12 | Python | `retry` middleware missing | P1 | `py/packages/genkit/src/genkit/blocks/middleware.py` | flaky-model retry test with backoff |
| G13 | Python | `fallback` middleware missing | P1 | `py/packages/genkit/src/genkit/blocks/middleware.py` | fallback model invoked on configured status |
| G14 | Python | `validate_support` middleware missing | P2 | `py/packages/genkit/src/genkit/blocks/middleware.py` | unsupported media/tools throws deterministic error |
| G15 | Python | `download_request_media` middleware missing | P2 | `py/packages/genkit/src/genkit/blocks/middleware.py` | URL media transformed to data URI |
| G16 | Python | `simulate_system_prompt` missing | P2 | `py/packages/genkit/src/genkit/blocks/middleware.py` | system message rewritten for unsupported model |
| G17 | Python | `api_key()` context provider missing | P3 | `py/packages/genkit/src/genkit/core/context.py` | auth header extraction + policy callback tests |
| G18 | Python | ~~multipart tool (`tool.v2`) missing~~ | P1 | `ai/_registry.py`, `core/action/types.py`, `blocks/generate.py` | ✅ **Done** (PR #4513) |
| G19 | Python | Model API V2 runner interface missing | P1 | `py/packages/genkit/src/genkit/ai/_registry.py`, `.../blocks/model.py` | v2 model receives unified options struct |
| G20 | Python | ~~`Genkit(context=...)` missing~~ | P2 | `ai/_aio.py`, `core/registry.py` | ✅ **Done** (PR #4512) |
| G21 | Python | ~~`Genkit(clientHeader=...)` missing~~ | P2 | `ai/_aio.py`, `core/constants.py` | ✅ **Done** (PR #4512) |
| G22 | Python | ~~`Genkit(name=...)` missing~~ | P2 | `ai/_aio.py`, `ai/_runtime.py`, `core/registry.py` | ✅ **Done** (PR #4512) |
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
| **G38** | **All SDKs** | **Generate Middleware V2** — 3-tier hooks (`generate`/`model`/`tool`), `define_middleware`, middleware registry, per-invocation state, config schema, tool injection | **P0** | `py/packages/genkit/src/genkit/blocks/middleware.py`, `core/action/`, `ai/_registry.py` | middleware V2 interface + 3-hook dispatch + registry lookup + config validation tests |
| **G39** | **Go + Python** | **Bidirectional Action** primitive (`define_bidi_action`) — core bidi streaming with `init`, `input_stream`, `output_stream` | **P1** | `py/packages/genkit/src/genkit/core/action/` (new bidi action type) | bidi action send/receive/close lifecycle tests |
| **G40** | **Go + Python** | **Bidirectional Flow** primitive (`define_bidi_flow`) — bidi action with observability/tracing | **P1** | `py/packages/genkit/src/genkit/blocks/` (new bidi flow module) | bidi flow tracing + streaming roundtrip tests |
| **G41** | **Go + Python** | **Bidirectional Model** (`define_bidi_model`, `generate_bidi`) — specialized bidi for real-time LLM APIs (Gemini Live, OpenAI Realtime) | **P1** | `py/packages/genkit/src/genkit/blocks/model.py`, `ai/_registry.py` | bidi model init + streaming conversation tests |
| **G42** | **Go + Python** | **Agent primitive** (`define_agent`) — stateful multi-turn agent with session stores, replaces Chat API | **P1** | `py/packages/genkit/src/genkit/blocks/` (new agent module, replaces/extends `session/`) | agent creation + session persistence + turn semantics tests |
| **G43** | **Go + Python** | **Plugin V2 architecture** — plugins provide `generate_middleware` arrays (`GenkitPluginV2`) | **P2** | `py/packages/genkit/src/genkit/core/_plugins.py` | plugin V2 middleware registration + resolution tests |
| **G44** | **All SDKs** | **Reflection API V2** — WebSocket + JSON-RPC 2.0, replacing HTTP REST reflection server | **P1** | `py/packages/genkit/src/genkit/core/reflection.py`, `web/manager/` | WebSocket connection + JSON-RPC dispatch + bidi action streaming tests |

### 9b. Python Gap Status Tracker (Updated 2026-02-09)

> Status legend: ⬜ = not started, 🔄 = PR open, ✅ = merged, ⏳ = deferred, ⏸️ = paused (blocked on upstream RFC), ~~struck~~ = superseded.

| Gap | Status | PR | Notes |
|-----|:------:|:---|-------|
| **G38** | ⬜ Blocked | Upstream: JS [#4515](https://github.com/firebase/genkit/pull/4515), Go [#4422](https://github.com/firebase/genkit/pull/4422) | **Middleware V2** (3-tier hooks) — waiting on JS/Go to land first |
| G1 | ⏸️ | [#4516](https://github.com/firebase/genkit/pull/4516) | `define_model(use=[...])` — **paused**, architecture changing (blocked on G38) |
| G2 | ⏸️ | [#4516](https://github.com/firebase/genkit/pull/4516) | Action middleware storage — **paused** (blocked on G38) |
| G3 | ⏸️ | [#4510](https://github.com/firebase/genkit/pull/4510) | `simulate_constrained_generation` — **paused** (blocked on G38) |
| G4 | 🔄 | [#4510](https://github.com/firebase/genkit/pull/4510) | `augment_with_context` lifecycle — logic valid, needs G38 interface |
| G5 | ✅ | [#4511](https://github.com/firebase/genkit/pull/4511) | `X-Genkit-Span-Id` header — merged 2026-02-09 |
| G6 | ✅ | [#4511](https://github.com/firebase/genkit/pull/4511) | `on_trace_start` span_id — merged 2026-02-09 |
| G7 | ✅ | [#4459](https://github.com/firebase/genkit/pull/4459) | DAP discovery — merged 2026-02-06 |
| G8 | ⏳ | — | `genkit.client` — deferred |
| G9 | ⏳ | — | Pinecone — deferred |
| G10 | ⏳ | — | ChromaDB — deferred |
| G11 | ✅ | [#4507](https://github.com/firebase/genkit/pull/4507), [#4508](https://github.com/firebase/genkit/pull/4508) | CHANGELOGs — merged 2026-02-09 |
| G12 | ⏸️ | [#4510](https://github.com/firebase/genkit/pull/4510) | `retry` middleware — **paused** (blocked on G38) |
| G13 | ⏸️ | [#4510](https://github.com/firebase/genkit/pull/4510) | `fallback` middleware — **paused** (blocked on G38) |
| G14 | ⏸️ | [#4510](https://github.com/firebase/genkit/pull/4510) | `validate_support` — **paused** (blocked on G38) |
| G15 | ⏸️ | [#4510](https://github.com/firebase/genkit/pull/4510) | `download_request_media` — **paused** (blocked on G38) |
| G16 | ⏸️ | [#4510](https://github.com/firebase/genkit/pull/4510) | `simulate_system_prompt` — **paused** (blocked on G38) |
| G17 | 🔄 | [#4521](https://github.com/firebase/genkit/pull/4521) | `api_key()` context — draft |
| G18 | 🔄 | [#4513](https://github.com/firebase/genkit/pull/4513) | multipart tool (tool.v2) — open |
| ~~G19~~ | ~~Superseded~~ | — | ~~Model API V2~~ — replaced by G38 (middleware V2) + G41 (bidi models) |
| G20 | 🔄 | [#4512](https://github.com/firebase/genkit/pull/4512) | `Genkit(context=...)` — open |
| G21 | 🔄 | [#4512](https://github.com/firebase/genkit/pull/4512) | `Genkit(client_header=...)` — open |
| G22 | 🔄 | [#4512](https://github.com/firebase/genkit/pull/4512) | `Genkit(name=...)` — open |
| G30 | ⏳ | — | Cloud SQL PG — deferred |
| G31 | 🔄 | [#4248](https://github.com/firebase/genkit/pull/4248) | MCP sample v2 — open |
| G33 | ⏳ | — | LangChain — deferred |
| G34 | ⏳ | — | BloomLabs vector stores — deferred |
| G35 | ⬜ | — | Groq provider — not started |
| G36 | ✅ | [#4518](https://github.com/firebase/genkit/pull/4518) | Cohere provider — merged 2026-02-09 |
| G37 | ⏳ | — | Graph workflows — deferred |
| **G39** | ⬜ Blocked | Upstream: JS [#4288](https://github.com/firebase/genkit/pull/4288) | **Bidi Action** — waiting on JS to land |
| **G40** | ⬜ Blocked | Upstream: JS [#4288](https://github.com/firebase/genkit/pull/4288) | **Bidi Flow** — waiting on JS to land |
| **G41** | ⬜ Blocked | Upstream: JS [#4210](https://github.com/firebase/genkit/pull/4210) | **Bidi Model** — waiting on JS to land |
| **G42** | ⬜ Blocked | Upstream: JS [#4212](https://github.com/firebase/genkit/pull/4212) | **Agent primitive** — waiting on JS RFC |
| **G43** | ⬜ | Upstream: JS [#4132](https://github.com/firebase/genkit/pull/4132) (merged) | **Plugin V2** — JS landed, Python design needed |
| **G44** | 🔄 | [#4401](https://github.com/firebase/genkit/pull/4401) (draft) | **Reflection API V2** — Python draft open |

**Progress**: 5 merged, 6 in review, 8 paused (middleware V2 blocked), 1 superseded, 6 blocked on upstream RFCs, 2 not started, 8 deferred. (Go gaps G23–G29, G32 tracked in §7b.)

### 9c. Dependency Matrix

| Depends On | Unblocks | Why |
|------------|----------|-----|
| **G38** | G2, G1, G3, G4, G12, G13, G14, G15, G16, G43 | **Middleware V2 architecture** must land in JS/Go before Python can implement any middleware |
| G2 | G1, G3, G4, G12, G13, G14, G16 | Python model middleware architecture must exist before feature middleware parity |
| G6 | G5 | Need span ID in callback before header emission |
| G7, G23 | G31 | MCP parity sample quality depends on DAP discoverability in tooling |
| **G39** | G40, G41 | Bidi Action is the core primitive; Flow and Model build on it |
| **G41** | G42 | Agent primitive is built on top of Bidi Flow/Model |
| **G44** | Bidi Dev UI support | WebSocket reflection needed for bidi streaming in Dev UI |
| G25 | G27, G28 | Go reranker/model API work shares core generation extension points |
| G29 | G8 | constructor/client header parity helps consistent remote invocation behavior |

### 9d. Fast-Close Implementation Bundles

| Bundle | Scope | Gaps | Deliverable | Exit Tests |
|--------|-------|------|-------------|------------|
| B1 | Python middleware foundation | G2, G1, G3, G12, G13, G14, G16 | full model middleware parity layer | middleware parity test suite green |
| B2 | Python reflection/protocol parity | G6, G5, G7 | trace/span headers + DAP discovery | reflection integration tests green |
| B3 | Python advanced model/tool parity | G18, G19, G4 | multipart + v2 model + ordering parity | tool.v2 + v2 runner tests green |
| B4 | Go API parity layer | G23, G24, G25, G26, G28, G29 | missing high-level APIs added | public API compile + behavior tests |
| B5 | Cross-SDK client/plugin parity | G8, G9, G10, G30, G31 | client helpers + plugin/sample parity | cross-SDK parity smoke suite green |
| B6 | Ecosystem/compliance | G11, G17, G32, G33, G34, G35, G36, G37 | docs/compliance + secondary plugins | consistency + sample smoke checks green |

### 9e. Prioritized Execution Order (All 3 SDKs)

1. B1: Python middleware foundation (highest behavior delta).
2. B2: Python reflection/protocol parity (Dev UI and observability correctness).
3. B4: Go API parity layer (largest JS-vs-Go surface gaps).
4. B3: Python advanced model/tool parity.
5. B5: cross-SDK client + plugin/sample parity.
6. B6: ecosystem/compliance.

### 9f. Cross-SDK Summary

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

> Generated: 2026-02-08. Updated: 2026-02-09. Based on reverse topological sort of the dependency graph across all tracked Python gaps (G1–G44).
>
> **2026-02-09 update**: Five major cross-SDK redesigns (Middleware V2, Bidi, Agent, Plugin V2, Reflection V2) have been identified as active RFCs. The roadmap has been restructured: middleware gaps G1–G3, G12–G16 are **paused** pending upstream Middleware V2 (#4515, #4422); G19 is **superseded**; new gaps G38–G44 added.

### 10a. Dependency Graph

The following directed acyclic graph (DAG) captures all prerequisite relationships between Python gaps. An edge `A → B` means **A must be completed before B can begin**.

```
Legend:  ───► = "is prerequisite for"
        (Pn) = priority level
        [PAUSED] = blocked on upstream RFC
        [DONE] = merged
        [SUPERSEDED] = replaced by new gap

UPSTREAM BLOCKERS (waiting on JS/Go RFCs to land)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  G38 (P0) Generate Middleware V2 (3-tier hooks)     [BLOCKED on JS #4515, Go #4422]
    ├───► G2  (P1) Action middleware storage          [PAUSED]
    ├───► G43 (P2) Plugin V2 architecture
    └───► (transitively) G1, G3, G4, G12-G16

  G39 (P1) Bidirectional Action                      [BLOCKED on JS #4288]
    ├───► G40 (P1) Bidirectional Flow
    └───► G41 (P1) Bidirectional Model

  G41 (P1) Bidirectional Model                       [BLOCKED on JS #4210]
    └───► G42 (P1) Agent primitive (replaces Chat API)

  G44 (P1) Reflection API V2 (WebSocket)             [draft PR #4401]

MIDDLEWARE CHAIN (all PAUSED pending G38)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  G2 (P1) Action middleware storage                  [PAUSED]
    ├───► G1  (P1) define_model(use=[...])           [PAUSED]
    ├───► G12 (P1) retry middleware                   [PAUSED]
    ├───► G13 (P1) fallback middleware                [PAUSED]
    └───► G15 (P2) download_request_media             [PAUSED]

  G1 (P1) define_model(use=[...])                    [PAUSED]
    ├───► G3  (P1) simulate_constrained_generation    [PAUSED]
    ├───► G4  (P2) augment_with_context lifecycle fix
    ├───► G14 (P2) validate_support middleware         [PAUSED]
    └───► G16 (P2) simulate_system_prompt              [PAUSED]

COMPLETED
━━━━━━━━━

  G6 (P1) on_trace_start span_id                     [DONE #4511]
    └───► G5  (P1) X-Genkit-Span-Id header            [DONE #4511]

  G7 (P1) DAP discovery in /api/actions               [DONE #4459]
    └───► G31 (P2) MCP parity sample

  G11 (P3) CHANGELOG.md                               [DONE #4507, #4508]
  G36 (P3) Cohere provider                             [DONE #4518]

SUPERSEDED
━━━━━━━━━━
  G19 (P1) Model API V2                               [SUPERSEDED by G38 + G41]

ACTIVE (unblocked, can proceed now)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  G21 (P2) Genkit(clientHeader=...)
    └───► G8  (P2) genkit.client module (run_flow/stream_flow)

  G18 (P1) Multipart tool (tool.v2)     G20 (P2) Genkit(context=...)
  G22 (P2) Genkit(name=...)             G17 (P3) api_key() context
  G35 (P3) Groq provider

DEFERRED
━━━━━━━━
  G9  (P2) Pinecone plugin              G10 (P2) ChromaDB plugin
  G30 (P2) Cloud SQL PG plugin          G33 (P3) LangChain integration
  G34 (P3) BloomLabs vector stores      G37 (P3) Graph workflows
  G8  (P2) genkit.client                 (deferred)
```

### 10b. Topological Sort — Dependency Levels

Reverse topological sort of the gap DAG yields the following dependency levels. Each level contains gaps whose prerequisites are all satisfied by prior levels. **Work within each level can be fully parallelized.**

| Level | Gaps | Prerequisites | Theme | Status |
|:-----:|------|:--------------|-------|:------:|
| **L-1** | **G38**, **G39**, **G44** | *Upstream JS/Go RFCs* | Upstream blockers — must land in JS/Go first | ⏸️ Blocked |
| **L0** | G2, G18, G20, G21, G22, G17, G35, G40, G41, G43 | G38 (for G2, G43); G39 (for G40, G41); *none* for others | Foundation + all independent work | Mixed |
| **L1** | G1, G12, G13, G15, G42, G8 | G2, G21, G41 | Middleware arch + client + agent | ⏸️ (middleware) |
| **L2** | G3, G4, G14, G16 | G1 | Feature middleware requiring define-model-time wiring | ⏸️ |

**Critical path** (longest chain): `G38 → G2 → G1 → G3` (4 levels deep, governs minimum calendar time for full P1 closure). **G38 is an external dependency on upstream JS/Go RFC work.**

**Completed items** (removed from active levels): G5, G6, G7, G11, G19 (superseded), G36.
**Deferred**: G8, G9, G10, G30, G33, G34, G37.

### 10c. Phased Roadmap

#### Phase 0 — Quick Wins (No Core Framework Changes Required)

> **Start immediately.** All items are independent of each other and of core framework work. Can run in parallel with all subsequent phases.

| ID | Work Item | Effort | Type | Status |
|----|-----------|:------:|------|:------:|
| **QW-1** | **Test coverage uplift** for all "Minimum" and "Adequate" plugins (see §10f) | M | Testing | 🔄 [#4509](https://github.com/firebase/genkit/pull/4509) (merged), ongoing |
| **QW-2** | **Verify all existing samples run** — execute every `py/samples/*/run.sh`, fix any breakage | M | Validation | 🔄 |
| ~~**QW-3**~~ | ~~G11: Add `CHANGELOG.md` to all 20 plugins + core package (21 files)~~ | ~~XS~~ | ~~Compliance~~ | ✅ [#4507](https://github.com/firebase/genkit/pull/4507), [#4508](https://github.com/firebase/genkit/pull/4508) |
| **QW-4** | G22: Add `name` parameter to `Genkit()` constructor — pass to `ReflectionServer` display name | XS | Feature | 🔄 [#4512](https://github.com/firebase/genkit/pull/4512) |
| **QW-5** | G17: Implement `api_key()` context provider in `core/context.py` | S | Feature | 🔄 [#4521](https://github.com/firebase/genkit/pull/4521) (draft) |
| **QW-6** | G35: Groq provider — thin `compat-oai` wrapper + usage documentation | S | Plugin | ⬜ |
| ~~**QW-7**~~ | ~~G36: Cohere provider — thin `compat-oai` wrapper + embedder support + docs~~ | ~~S~~ | ~~Plugin~~ | ✅ [#4518](https://github.com/firebase/genkit/pull/4518) |

**Effort key**: XS = < 1 day, S = 1–2 days, M = 3–5 days, L = 1–2 weeks, XL = 2+ weeks.

**Why these are quick wins**: None of them touch the core action system, middleware dispatcher, or reflection server. Provider wrappers for Groq/Cohere reuse the existing `compat-oai` infrastructure. CHANGELOGs and constructor params are additive, zero-risk changes. Sample verification catches regressions early and requires no framework changes.

---

#### Phase 1 — Unblocked Core Work (No Upstream Dependencies)

> **Start now.** These items have no upstream RFC blockers and are unrelated to the middleware V2 redesign.

| ID | Gap | Work Item | Files to Touch | Effort | Unblocks | Status |
|----|-----|-----------|----------------|:------:|----------|:------:|
| ~~**P1.2**~~ | ~~**G6**~~ | ~~Update `on_trace_start` callback signature~~ | ~~`core/action/`, `core/reflection.py`~~ | ~~S~~ | ~~G5~~ | ✅ [#4511](https://github.com/firebase/genkit/pull/4511) |
| **P1.3** | **G18** | Add multipart tool support: `define_tool(multipart=True)`, `MultipartToolAction` type `tool.v2`, dual registration for non-multipart tools | `blocks/tools.py`, `blocks/generate.py` | M | — | 🔄 [#4513](https://github.com/firebase/genkit/pull/4513) |
| **P1.4** | **G20** | Add `context` parameter to `Genkit()` that sets `registry.context` for default action context | `ai/_aio.py` | XS | — | 🔄 [#4512](https://github.com/firebase/genkit/pull/4512) |
| **P1.5** | **G21** | Add `clientHeader` parameter to `Genkit()` that appends to `GENKIT_CLIENT_HEADER` via `set_client_header()` | `ai/_aio.py`, `core/http_client.py` | XS | G8 | 🔄 [#4512](https://github.com/firebase/genkit/pull/4512) |

**Exit criteria**: All unit tests green for tool.v2 registration and constructor parameter propagation.

---

#### Phase 2 — Middleware V2 Architecture (PAUSED — Blocked on Upstream RFCs)

> **PAUSED.** Blocked on upstream JS Middleware V2 ([#4515](https://github.com/firebase/genkit/pull/4515)) and Go Middleware V2 ([#4422](https://github.com/firebase/genkit/pull/4422)) landing. PRs [#4510](https://github.com/firebase/genkit/pull/4510) and [#4516](https://github.com/firebase/genkit/pull/4516) are paused.
>
> When upstream lands, these items will need to be redesigned to target the new 3-tier middleware architecture (see §8l). The **core middleware logic** (retry backoff, fallback chain, constraint simulation, etc.) remains valid — only the **wrapping interface** changes from `ModelMiddleware` function to `GenerateMiddlewareDef` with `generate`/`model`/`tool` hooks.

| ID | Gap | Work Item | Effort | Status |
|----|-----|-----------|:------:|:------:|
| **P2.0** | **G38** | Implement Middleware V2 architecture: 3-tier hooks, `define_middleware()`, middleware registry, per-invocation state, config schema | XL | ⏸️ Blocked on upstream |
| **P2.1** | **G2 → G1** | Adapt `Action` middleware storage and `define_model(use=[...])` to new V2 interface | L | ⏸️ [#4516](https://github.com/firebase/genkit/pull/4516) paused |
| **P2.3** | **G12** | Reimplement `retry()` as V2 middleware with `model` hook | M | ⏸️ [#4510](https://github.com/firebase/genkit/pull/4510) paused |
| **P2.4** | **G13** | Reimplement `fallback()` as V2 middleware with `model` hook | M | ⏸️ [#4510](https://github.com/firebase/genkit/pull/4510) paused |
| **P2.5** | **G15** | Reimplement `download_request_media()` as V2 middleware with `model` hook | S | ⏸️ [#4510](https://github.com/firebase/genkit/pull/4510) paused |

---

#### Phase 3 — Feature Middleware Parity (PAUSED — Depends on Phase 2)

> **PAUSED.** Depends on Phase 2 (G38 + G1). These middleware functions will use the `model` hook in the new V2 architecture.

| ID | Gap | Work Item | Effort | Status |
|----|-----|-----------|:------:|:------:|
| **P3.1** | **G3** | Reimplement `simulate_constrained_generation()` as V2 middleware | M | ⏸️ |
| **P3.2** | **G4** | Move `augment_with_context()` to define-model-time V2 middleware chain | S | ⏸️ |
| **P3.3** | **G14** | Reimplement `validate_support()` as V2 middleware | S | ⏸️ |
| **P3.4** | **G16** | Reimplement `simulate_system_prompt()` as V2 middleware | S | ⏸️ |
| **P3.5** | **G43** | Plugin V2 architecture — plugins provide `generate_middleware` arrays | M | ⏸️ |

---

#### Phase 4 — Bidirectional Streaming & Agent (BLOCKED — Awaiting Upstream)

> **BLOCKED.** Depends on JS Bidi Actions ([#4288](https://github.com/firebase/genkit/pull/4288)) and Agent RFC ([#4212](https://github.com/firebase/genkit/pull/4212)) landing.

| ID | Gap | Work Item | Effort | Status |
|----|-----|-----------|:------:|:------:|
| **P4.1** | **G39** | Implement `define_bidi_action` — core bidi action with `init`, async input/output streams | L | ⬜ Blocked |
| **P4.2** | **G40** | Implement `define_bidi_flow` — bidi action with observability/tracing wrappers | M | ⬜ Blocked |
| **P4.3** | **G41** | Implement `define_bidi_model` + `generate_bidi` — specialized bidi for real-time LLM APIs | L | ⬜ Blocked |
| **P4.4** | **G42** | Implement `define_agent` — stateful agent with session stores, replaces Chat API | XL | ⬜ Blocked |
| **P4.5** | **G44** | Implement Reflection API V2 — WebSocket + JSON-RPC 2.0 transport | L | 🔄 [#4401](https://github.com/firebase/genkit/pull/4401) (draft) |

---

#### Phase 5 — Integration & Client Parity

> **Depends on**: G21 (Phase 1) for client helpers.

| ID | Gap | Work Item | Files to Touch | Effort | Unblocks |
|----|-----|-----------|----------------|:------:|----------|
| **P5.1** | **G8** | Implement `genkit.client` module with `run_flow()` (HTTP POST + JSON response) and `stream_flow()` (HTTP POST + NDJSON streaming response) helpers; use `httpx` with configurable `client_header` | New `client/` module | M | — |

**Exit criteria**: `run_flow` and `stream_flow` can invoke a deployed genkit flow endpoint over HTTP with correct headers and response parsing.

---

#### Phase 6 — Deferred & Ecosystem Parity

> **Deprioritized items.** Vector store plugins and community ecosystem work are deferred to focus on core framework 1:1 parity and existing plugin quality first.

| ID | Gap | Work Item | Effort | Notes |
|----|-----|-----------|:------:|-------|
| **P6.1** | G9 | Pinecone vector store plugin (new `py/plugins/pinecone`) | M | Deferred |
| **P6.2** | G10 | ChromaDB vector store plugin (new `py/plugins/chroma`) | M | Deferred |
| **P6.3** | G30 | Cloud SQL PG vector store plugin (new `py/plugins/cloud-sql-pg`) | M | Deferred |
| **P6.4** | G33 | LangChain integration plugin | L | Evaluate if LangChain Python integration adds value given Python's existing rich plugin ecosystem |
| **P6.5** | G34 | BloomLabs vector stores (Convex, HNSW, Milvus) | L per store | Community-driven; consider as `compat-oai`-style shims or documentation-only |
| **P6.6** | G37 | Graph workflows plugin | L | Port `genkitx-graph` concepts; evaluate against native Python workflow libraries |

**Exit criteria**: Each plugin has README, tests, sample, and passes `check_consistency`.

---

### 10d. Dependency Graph — Visual Summary

```
  UPSTREAM BLOCKERS                PHASE 0 (parallel)           PHASE 1 (active)
  ═════════════════                ════════════════              ════════════════

  ┌─────────────────┐         ┌──────────────────────┐
  │  G38 (P0)       │         │ QW: G11✅,G17,G22    │     ┌────────┐  ┌────────┐
  │  Middleware V2   │─ ─ ─ ─►│ G35, G36✅            │     │  G18   │  │  G20   │
  │  [JS #4515]     │  waits  │ Test Coverage Uplift │     │  (P1)  │  │  (P2)  │
  │  [Go #4422]     │         └──────────────────────┘     │ tool.v2│  │ ctx    │
  └────────┬────────┘              (runs in parallel)      └────────┘  └────────┘
           │
           │ unblocks                                       ┌────────┐  ┌────────┐
           ▼                                                │  G21   │  │  G22   │
  ┌────────────────┐                                        │  (P2)  │  │  (P2)  │
  │  G2 → G1       │─────────► PHASE 2+3 (middleware)      │ header │  │ name   │
  │  [PAUSED]      │           all middleware items         └────┬───┘  └────────┘
  │  #4516 paused  │           #4510 paused                      │
  └────────────────┘                                             ▼
                                                            ┌────────┐
  ┌─────────────────┐                                       │  G8    │
  │  G39 (P1)       │                                       │  (P2)  │
  │  Bidi Action    │─────────► G40 (Bidi Flow)             │ client │
  │  [JS #4288]     │────────►  G41 (Bidi Model) ──► G42   └────────┘
  └─────────────────┘                                (Agent)

  ┌─────────────────┐        COMPLETED
  │  G44 (P1)       │        ═════════
  │  Reflection V2  │        G5✅, G6✅ (#4511)
  │  [Py #4401]     │        G7✅ (#4459)
  └─────────────────┘        G11✅ (#4507,#4508)
                              G36✅ (#4518)
                              G19 ──► SUPERSEDED (by G38+G41)
```

### 10e. Critical Path Analysis

| Path | Chain Length | Calendar Estimate | Covers | Status |
|------|:-----------:|:-----------------:|--------|:------:|
| **G38 → G2 → G1 → G3** | 4 levels | Unknown (depends on upstream) | Middleware V2 → storage → define-model → constrained gen | ⏸️ Blocked |
| **G38 → G2 → G1 → G14** | 4 levels | Unknown | Middleware V2 → storage → define-model → validate support | ⏸️ Blocked |
| **G38 → G2 → G12** | 3 levels | Unknown | Middleware V2 → storage → retry | ⏸️ Blocked |
| **G39 → G41 → G42** | 3 levels | Unknown (depends on upstream) | Bidi Action → Bidi Model → Agent | ⬜ Blocked |
| ~~G6 → G5~~ | ~~2 levels~~ | — | ~~Span callback → span header~~ | ✅ Done |
| **G21 → G8** | 2 levels | ~2 weeks | Client header → client module | 🔄 Active |

**Bottleneck shift**: The bottleneck has moved from G2 (internal) to **G38** (external dependency on upstream JS/Go Middleware V2 RFCs). Until JS [#4515](https://github.com/firebase/genkit/pull/4515) and Go [#4422](https://github.com/firebase/genkit/pull/4422) land, 8 Python middleware gaps remain blocked.

**Actionable now**: Phase 0 quick wins, Phase 1 unblocked items (G18, G20, G21, G22), test coverage uplift, sample verification.

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

> **Updated 2026-02-09**: Timeline restructured due to upstream Middleware V2 and Bidi RFC blockers.

```
Week   1    2    3    4    5    ?    ?    ?    ?    ?    ?    ?
      ──── ──── ──── ──── ──── ──── ──── ──── ──── ──── ──── ────
P0    ████████████████████████████████████████████████████████████  Quick wins + test uplift (continuous)
P1    ████████████████                                             G18, G20, G21, G22 (unblocked)
                         ╔═══════════════════════════════════════
                         ║ WAITING ON UPSTREAM RFCs
                         ║ G38: JS #4515 (Middleware V2)
                         ║ G39: JS #4288 (Bidi Actions)
                         ║ G42: JS #4212 (Agent Primitive)
                         ╚═══════════════════════════════════════
P2                             ████████████████                    G38→G2→G1, G12, G13, G15 (after upstream)
P3                                       ████████████              G3, G4, G14, G16, G43 (after P2)
P4                                                 ████████████── G39-G42, G44 (Bidi + Agent + Reflection V2)
P5                                                       ████     G8 (client)
P6                                                           ──── Deferred ecosystem

Milestone     ▲ P1 done       ▲ Upstream    ▲ Middleware  ▲ Bidi+Agent
              (week 3)        lands (?)     parity (?)   parity (?)
```

**Note**: Phases 2–4 timelines depend on when upstream JS/Go RFCs land. Phase 0 and Phase 1 work continues in parallel.

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

| PR | Scope | Gaps | Contents | Depends On |
|----|:-----:|------|----------|:----------:|
| **PR-0a** | Compliance | G11 | Add `CHANGELOG.md` to all 20 plugins + core package (21 files) | — |
| **PR-0b** | Sample | — | Run all `py/samples/*/run.sh`, fix any broken samples | — |
| **PR-0c** | Core | G22 | `Genkit(name=...)` constructor param → `ReflectionServer` display name | — |
| **PR-0d** | Core | G17 | `api_key()` context provider in `core/context.py` + tests | — |
| **PR-0e** | Plugin | G35 | Groq provider — thin `compat-oai` wrapper plugin + tests + docs | — |
| **PR-0f** | Plugin | G36 | Cohere provider — thin `compat-oai` wrapper plugin + tests + docs | — |
| **PR-0g.1–0g.13** | Plugin | — | Test coverage uplift — **one PR per plugin** (see §10f for per-plugin targets): dev-local-vectorstore, firebase, evaluators, flask, observability, google-cloud, microsoft-foundry, checks, cloudflare-workers-ai, amazon-bedrock, deepseek, huggingface, xai | — |

*All Phase 0 PRs are independent and can be sent in parallel.*

#### Phase 1 — Core Infrastructure PRs

| PR | Scope | Gaps | Contents | Depends On |
|----|:-----:|------|----------|:----------:|
| **PR-1a** | Core | G2 | Add `middleware` list to `Action.__init__()`, implement `action_with_middleware()` dispatch wrapper, unit tests for middleware chaining | — |
| **PR-1b** | Core | G6 | Update `on_trace_start` callback signature to `(trace_id, span_id)` across action system + tracing, update all call sites | — |
| **PR-1c** | Core | G18 | ~~Multipart tool support: `define_tool(multipart=True)`, `tool.v2` action type, dual registration for non-multipart tools, unit tests~~ | ✅ PR #4513 |
| **PR-1d** | Core | G20, G21, G22 | ~~`Genkit(context=..., client_header=..., name=...)` constructor params~~ | ✅ PR #4512 |

*PR-1a is the critical-path item. Land it first to unblock Phase 2.*

#### Phase 2 — Middleware Architecture PRs

| PR | Scope | Gaps | Contents | Depends On |
|----|:-----:|------|----------|:----------:|
| **PR-2a** | Core | G1 | Add `use` param to `define_model()`, wire to `action_with_middleware()`, build `get_model_middleware()` helper, tests | PR-1a |
| **PR-2b** | Core | G5 | Emit `X-Genkit-Span-Id` response header in reflection server (small, ~20 lines) | PR-1b |
| **PR-2c** | Core | G12 | `retry()` middleware — exponential backoff, jitter, configurable statuses, `on_error` callback, dedicated test suite | PR-1a |
| **PR-2d** | Core | G13 | `fallback()` middleware — ordered model list, error status config, `on_error` callback, dedicated test suite | PR-1a |
| **PR-2e** | Core | G15 | `download_request_media()` middleware — URL→data URI conversion, `max_bytes`, `filter`, tests | PR-1a |
| **PR-2f** | Core | G19 | Model API V2 runner interface — `define_model(api_version='v2')`, `ActionFnArg` options object, backward compat, tests | PR-1a |

*PR-2c, PR-2d, PR-2e can be sent in parallel once PR-1a lands. PR-2a must also land before Phase 3.*

#### Phase 3 — Feature Middleware PRs

| PR | Scope | Gaps | Contents | Depends On |
|----|:-----:|------|----------|:----------:|
| **PR-3a** | Core | G3 | `simulate_constrained_generation()` — schema instruction injection, output config clearing, tests | PR-2a |
| **PR-3b** | Core | G4 | `augment_with_context()` lifecycle fix — move from call-time to define-model time, update `generate.py`, tests | PR-2a |
| **PR-3c** | Core | G14 | `validate_support()` — request vs model capability validation, descriptive errors, tests | PR-2a |
| **PR-3d** | Core | G16 | `simulate_system_prompt()` — system→user/model turn conversion, configurable preface/ack, tests | PR-2a |

*All four PRs are independent of each other and can be sent in parallel once PR-2a lands.*

#### Phase 4 — Integration PR

| PR | Scope | Gaps | Contents | Depends On |
|----|:-----:|------|----------|:----------:|
| **PR-4a** | Core | G8 | New `genkit.client` module — `run_flow()`, `stream_flow()` helpers, `httpx`-based, tests | PR-1d |

#### PR Dependency Chain (Critical Path)

```
PR-0* ──────────────────────────────────────────── (all parallel, no deps)

PR-1a (G2: Action middleware) ─────► PR-2a (G1: define_model use=) ─────► PR-3a (G3)
                               ├───► PR-2c (G12: retry)                ├─► PR-3b (G4)
                               ├───► PR-2d (G13: fallback)             ├─► PR-3c (G14)
                               ├───► PR-2e (G15: download media)       └─► PR-3d (G16)
                               └───► PR-2f (G19: Model API V2)

PR-1b (G6: span_id callback) ─────► PR-2b (G5: span header)

PR-1c (G18: multipart tools) ────── (no downstream deps)

PR-1d (G20+G21: constructor) ─────► PR-4a (G8: client module)
```

#### PR Summary

| Phase | PRs | Core | Plugin | Sample/Compliance |
|:-----:|:---:|:----:|:------:|:-----------------:|
| 0 | ~16 | 2 | 2 + 13 test uplift | 2 |
| 1 | 4 | 4 | — | — |
| 2 | 6 | 6 | — | — |
| 3 | 4 | 4 | — | — |
| 4 | 1 | 1 | — | — |
| **Total** | **~31** | **17** | **~15** | **2** |

#### Immediate PR Manifest — Current Branch Split

The current `yesudeep/feat/checks-plugin` branch bundles 32 changed files spanning 6 concerns. Per the scope rules above, it must be split into the following 5 PRs before merging:

| PR | Branch | Scope | Files | Commit Message | Depends On |
|----|--------|:-----:|:-----:|----------------|:----------:|
| **A** | `yesudeep/chore/py-typed-compliance` | Compliance | 9 `py.typed` files (cloudflare-workers-ai, deepseek, dev-local-vectorstore, huggingface, mcp, microsoft-foundry, mistral, observability, xai) | `chore(py/plugins): add missing py.typed PEP 561 markers to 9 plugins` | — |
| **B** | `yesudeep/chore/check-consistency-updates` | Tooling | `py/bin/check_consistency` (adds checks 19, 20, 21) | `feat(py/bin): add sample LICENSE, Google OSS files, and CHANGELOG checks to check_consistency` | — |
| **C** | `yesudeep/docs/parity-audit` | Docs | `py/PARITY_AUDIT.md`, `py/GEMINI.md` | `docs(py): add feature parity audit with implementation roadmap` | — |
| **D** | `yesudeep/feat/checks-plugin` | Plugin | `py/plugins/checks/` (13 files), `py/pyproject.toml` (plugin registration + pyright tweak), `py/uv.lock` | `feat(py/checks): add Google Checks AI Safety plugin` | — |
| **E** | `yesudeep/feat/checks-sample` | Sample | `py/samples/provider-checks-hello/` (5 files), `py/pyproject.toml` (sample registration) | `feat(py/samples): add provider-checks-hello sample` | **D** |

**Dependency**: A, B, C, D are independent and can merge in any order. E depends on D (sample imports the plugin).

**`py/pyproject.toml` handling**: This file is touched by both D and E. PR-D gets the plugin workspace registration lines + pyright format tweak. PR-E gets only the sample workspace registration line. Each PR applies its own partial edit.

### 10i. Summary Metrics

| Metric | Value |
|--------|-------|
| Total Python gaps | **36** (G1–G22, G30–G31, G33–G44, minus G19 superseded) |
| **Completed** | **5** — G5, G6, G7, G11, G36 |
| **In review (PRs open)** | **6** — G4, G17, G18, G20, G21, G22 |
| **Paused (blocked on upstream Middleware V2)** | **8** — G1, G2, G3, G12, G13, G14, G15, G16 |
| **Blocked on upstream RFCs (new)** | **6** — G38, G39, G40, G41, G42, G43 |
| **Reflection V2 (draft)** | **1** — G44 |
| **Superseded** | **1** — G19 (replaced by G38 + G41) |
| **Not started** | **1** — G35 |
| **Deferred** | **8** — G8, G9, G10, G30, G33, G34, G37, G31 |
| Phase 0 quick wins | 5 active items (2 done) |
| Phase 1 (unblocked) | 4 items (G18, G20, G21, G22) — **actionable now** |
| Phases 2–3 (middleware) | 13 items — **paused**, awaiting upstream G38 |
| Phase 4 (bidi + agent) | 5 items — **blocked**, awaiting upstream G39–G42, G44 |
| Phase 5 (integration) | 1 item (G8) |
| Phase 6 (deferred) | 6 items (vector stores, ecosystem) |
| Critical path length | **4 dependency levels** (G38 → G2 → G1 → G3) |
| External blockers | JS [#4515](https://github.com/firebase/genkit/pull/4515), [#4288](https://github.com/firebase/genkit/pull/4288), [#4212](https://github.com/firebase/genkit/pull/4212); Go [#4422](https://github.com/firebase/genkit/pull/4422) |
| Estimated calendar time to P1 closure | **Depends on upstream** — Phase 1 items completable in ~2–3 weeks |
| Plugins needing test uplift | 13 of 20 |
| New test files needed (est.) | ~40–50 across all plugins |

---

## 11. Cross-SDK Issue Tracker Analysis

> **Purpose**: Catalogue real-world issues reported against JS, Go, and Python SDKs on
> GitHub to (a) identify problems that already affect or could affect the Python SDK,
> (b) avoid repeating the same mistakes, and (c) prioritize fixes. Each row records
> the original issue, its category, a Python-applicability verdict, and the
> recommended action.
>
> **Methodology**: Issues were collected from
> [firebase/genkit/issues](https://github.com/firebase/genkit/issues) using
> keyword searches (error, streaming, telemetry, schema, install, etc.) and
> by examining the most upvoted / most recent open issues as of 2026-02-09.

### 11a. Category Legend

| Category | Icon | Description |
|----------|:----:|-------------|
| **Bug — Runtime** | 🐛 | Incorrect behavior at runtime (data corruption, crashes, wrong output) |
| **Bug — Schema / Output** | 📐 | JSON Schema generation, structured output, or validation failures |
| **Streaming** | 🌊 | Streaming-specific bugs or missing features |
| **Telemetry / Observability** | 📡 | Tracing, logging, OTel integration issues |
| **DevX / Documentation** | 📖 | Confusing docs, outdated examples, developer friction |
| **Installation / Dependency** | 📦 | Build failures, version pinning, incompatible transitive deps |
| **Plugin Interop** | 🔌 | Plugin-specific bugs or missing capabilities |
| **Error Handling** | ⚠️ | Poor error messages, silent failures, missing error types |
| **Security** | 🔒 | Leaked data, credential handling |
| **Feature Request** | 💡 | Frequently-requested features that improve production readiness |

### 11b. Python-Applicability Verdicts

| Verdict | Meaning |
|---------|---------|
| ✅ **Confirmed** | The issue already exists in the Python SDK (verified in code) |
| ⚠️ **Likely** | The Python SDK has similar architecture; the same bug class is probable |
| 🔍 **Investigate** | Needs code audit to confirm; the pattern exists but may differ |
| 🛡️ **Protected** | Python's design already prevents this class of bug |
| ➖ **N/A** | Language or runtime-specific; does not apply to Python |

### 11c. Bug — Runtime Issues

| # | Issue | SDK | Summary | Python Verdict | Action / Notes |
|---|-------|:---:|---------|:--------------:|----------------|
| 1 | [#3839](https://github.com/firebase/genkit/issues/3839) | Go | **LookupPrompt caches input and reuses stale values** — prompt template not re-rendered on subsequent calls with different input. Silent data corruption (no runtime error). | 🔍 Investigate | Python's Dotprompt uses Handlebars rendering per-call, but audit `prompt.py` to verify template text is never mutated in place. |
| 2 | [#4264](https://github.com/firebase/genkit/issues/4264) | Go | **Prompt renders incorrect input after initial execution or when used concurrently** — `templateText` appears fragmented and pre-rendered on second run. Duplicate of #3839 class. | 🔍 Investigate | Same class as #3839. Verify Python prompt compilation creates a fresh template each time. |
| 3 | [#4492](https://github.com/firebase/genkit/issues/4492) | **PY** | **Tools with only `ToolRunContext` crash with `PydanticSchemaGenerationError`** — defining a tool with `ctx: ToolRunContext` as the sole parameter causes schema generation to fail at import time; even if bypassed, wrong value dispatched at runtime. | ✅ **Confirmed** | Two bugs: (A) `_registry.py` line 557–561 treats 1-arg `ToolRunContext`-only tool as data input, (B) schema builder tries `TypeAdapter(ToolRunContext)`. Fix: detect context-only signature and skip schema generation. |
| 4 | [#4117](https://github.com/firebase/genkit/issues/4117) | **PY** | **Backend log timestamp leaked into generated text** — `multipart_tool_calling` flow returns text prefixed with `"011-25 15:58:15.908000 +0000 UTC"`. | 🔍 Investigate | Likely model-side artifact (gemini-3-pro-preview), but audit Python's tool response concatenation in `generate.py` to ensure no log contamination in message assembly. |
| 5 | [#4279](https://github.com/firebase/genkit/issues/4279) | JS | **`compat-oai` raw response is always empty** — `response.raw` returns `{}` despite data being present in traces. | ⚠️ Likely | Python `compat-oai` plugin should be audited — check if `raw` field is populated in `GenerateResponse`. The JS bug is in response construction; Python may have the same omission. |

### 11d. Bug — Schema / Output Issues

| # | Issue | SDK | Summary | Python Verdict | Action / Notes |
|---|-------|:---:|---------|:--------------:|----------------|
| 6 | [#4119](https://github.com/firebase/genkit/issues/4119) | Go | **`InferJSONSchema` produces invalid schema for repeated struct types** — `{additionalProperties: true}` without `type` field causes Gemini API rejection. | 🛡️ Protected | Python uses Pydantic's `TypeAdapter.json_schema()` which handles repeated types correctly via `$defs`/`$ref`. No action needed. |
| 7 | [#4110](https://github.com/firebase/genkit/issues/4110) | JS | **Schema regression from v1.22 → v1.23** — `$ref` in output schema not resolved before API call, causing `400 Bad Request`. Discriminated unions with `z.discriminatedUnion` broke between versions. | ⚠️ Likely | Python's `gen.go`-based schema sanitizer and Pydantic schema generation should be audited. Verify `$ref` is resolved before sending to Gemini API. Also test discriminated unions via `Literal` + `Union`. |
| 8 | [#2758](https://github.com/firebase/genkit/issues/2758) | JS | **Zod integration pitfalls** — `nullable()`, `describe()`, `literal()` rejected by Gemini; structured output randomly missing properties. | ⚠️ Likely | Python equivalent: Pydantic `Optional`, `Field(description=...)`, `Literal`. Verify these are correctly translated in schema for `google-genai` plugin. Create test cases for edge cases. |
| 9 | [#4350](https://github.com/firebase/genkit/issues/4350) | **PY** | **No handling for malformed JSON in `extract.py`** — `TODO` at line 42. | ✅ **Confirmed** | `extract.py:42` has `# TODO(#4350)`. Implement robust JSON parsing with fallback/repair for model responses that contain markdown fences or trailing commas. |

### 11e. Streaming Issues

| # | Issue | SDK | Summary | Python Verdict | Action / Notes |
|---|-------|:---:|---------|:--------------:|----------------|
| 10 | [#3851](https://github.com/firebase/genkit/issues/3851) | Go | **Streaming with tools causes message loss** — final response only includes tool response, ignoring reasoning/previous model messages. | 🔍 Investigate | Audit Python's streaming + tool-calling path in `generate.py`. Verify message history is correctly accumulated across tool call turns during streaming. |
| 11 | [#4036](https://github.com/firebase/genkit/issues/4036) | JS | **Anthropic: `input_json_delta` not supported for streaming tool calls** — server tools stream deltas that aren't parsed. | 🔍 Investigate | If Python's Anthropic plugin supports streaming tool calls, verify delta parsing. Currently likely N/A since Anthropic plugin may not stream tool args. |
| 12 | [#3938](https://github.com/firebase/genkit/issues/3938) | JS | **MCP tool inputs never exposed in `streamResponse.toolRequest`** — streaming responses don't surface tool request arguments. | 🔍 Investigate | Audit Python MCP plugin streaming path. |

### 11f. Telemetry / Observability Issues

| # | Issue | SDK | Summary | Python Verdict | Action / Notes |
|---|-------|:---:|---------|:--------------:|----------------|
| 13 | [#2904](https://github.com/firebase/genkit/issues/2904) | JS | **Telemetry doesn't work with Sentry or Elastic APM** — no traces exported when using third-party APM alongside Genkit telemetry. | 🔍 Investigate | Python's OTel integration should be tested with Sentry and Elastic APM Python SDKs. The `web-endpoints-hello` sample already supports Sentry (`sentry_init.py`), but verify trace propagation when both Genkit tracing and Sentry coexist. |
| 14 | [#2278](https://github.com/firebase/genkit/issues/2278) | JS | **Telemetry not exported when flow called from Cloud Function** — traces appear in Dev UI but not in Firebase Console when invoked from a Cloud Function. | ⚠️ Likely | Verify Python SDK flushes traces before the cloud function process exits. Short-lived serverless environments (Cloud Functions, Lambda) may terminate before async OTel export completes. Add `force_flush()` on shutdown. |
| 15 | — | All | **`X-Genkit-Span-Id` header missing in Python reflection server** (documented in §8c.3) | ✅ **Confirmed** | Python's `onTraceStart` callback receives only `tid: str`, not `spanId`. Add `spanId` to callback signature and emit `X-Genkit-Span-Id` response header. |

### 11g. DevX / Documentation Issues

| # | Issue | SDK | Summary | Python Verdict | Action / Notes |
|---|-------|:---:|---------|:--------------:|----------------|
| 16 | [#4501](https://github.com/firebase/genkit/issues/4501) | Go | **Documentation is outdated — `ai.Retrieve` doesn't work** — RAG Go examples on genkit.dev use deprecated APIs. | ⚠️ Likely | Python docs should be audited for accuracy. Ensure all code examples in README files and docstrings compile and run against the current SDK version. |
| 17 | [#3810](https://github.com/firebase/genkit/issues/3810) | JS | **Ollama plugin docs claim structured output support but it doesn't work** — developers waste time trying to use `output: { schema }` with Ollama. | ⚠️ Likely | Python Ollama plugin should document what is and isn't supported (structured output, tool calling, streaming). Add `supports` metadata to model definition. |
| 18 | [#3915](https://github.com/firebase/genkit/issues/3915) | JS | **Gemini "free tier" quota errors on first request** — docs say "generous free tier" but users hit immediate `429` quota errors. `limit: 0` for free tier in some regions. | ⚠️ Likely | Python getting-started docs/samples should mention quota limitations and add retry/backoff guidance. The `web-endpoints-hello` sample handles this via circuit breaker, but simpler samples need a note. |
| 19 | [#2758](https://github.com/firebase/genkit/issues/2758) | JS | **Schema definition pitfalls not documented** — `nullable()`, `describe()`, `literal()` silently fail or get rejected. | ⚠️ Likely | Document which Pydantic field types/options are fully supported by each provider (Gemini, Vertex, Anthropic, OpenAI). Add a "Schema Compatibility" section to Python plugin docs. |

### 11h. Installation / Dependency Issues

| # | Issue | SDK | Summary | Python Verdict | Action / Notes |
|---|-------|:---:|---------|:--------------:|----------------|
| 20 | [#2771](https://github.com/firebase/genkit/issues/2771) | Go | **Genkit v0.5.1 won't build with OTel SDK v1.35.0** — `instrumentation.Library` deprecated in favor of `instrumentation.Scope`, causing compile failure. | 🔍 Investigate | Python pins OTel versions in `pyproject.toml`. Run `uv pip check` and verify no version conflicts with latest `opentelemetry-sdk`. Add lower-bound checks in CI. |
| 21 | — | All | **CLI installation has wrong architecture for darwin-x64** — reported for the `genkit` CLI binary. | ➖ N/A | Python SDK doesn't ship native binaries. However, ensure `setup.sh` in samples detects architecture correctly when installing the genkit CLI. |
| 22 | — | All | **CI/CD interrupted by cookie/analytics prompt** — CLI tooling shows interactive prompts in headless environments. | ⚠️ Likely | Python's `genkit start` may show similar prompts. Ensure `--non-interactive` or `CI=true` suppresses all prompts. Test in CI matrix. |

### 11i. Plugin Interop Issues

| # | Issue | SDK | Summary | Python Verdict | Action / Notes |
|---|-------|:---:|---------|:--------------:|----------------|
| 23 | [#4490](https://github.com/firebase/genkit/issues/4490) | Go | **Cannot use moondream:v2 with Ollama plugin** — models are statically defined; any model not in the hardcoded list fails with "model not found". | 🔍 Investigate | Verify Python Ollama plugin allows arbitrary model names. If models are statically listed, add a pass-through for unknown model names. |
| 24 | [#3651](https://github.com/firebase/genkit/issues/3651) | JS | **Vertex AI plugin uses wrong URL for `location: 'global'`** — constructs `https://global-aiplatform.googleapis.com` (404) instead of `https://aiplatform.googleapis.com`. | 🔍 Investigate | Check Python `vertex-ai` plugin for the same URL construction pattern. The Google `genai` Python SDK may handle this correctly, but verify. |
| 25 | [#4299](https://github.com/firebase/genkit/issues/4299) | Go | **MCP client silently swallows initialization errors** — `NewGenkitMCPClient` returns `nil` error on misconfigured `BaseURL`; user only discovers failure on first tool call. | 🔍 Investigate | Audit Python MCP plugin's `__init__` / connection setup. Ensure initialization errors (bad URL, connection refused, auth failure) are raised immediately, not deferred. |

### 11j. Error Handling Issues

| # | Issue | SDK | Summary | Python Verdict | Action / Notes |
|---|-------|:---:|---------|:--------------:|----------------|
| 26 | [#4336](https://github.com/firebase/genkit/issues/4336) | **PY** | **`GenerationBlockedError` should extend `GenkitError`** — `TODO` at `generate.py:1034`. Currently a bare exception, making it hard to catch in a typed error hierarchy. | ✅ **Confirmed** | Implement the error hierarchy. `GenerationBlockedError(GenkitError)` enables structured error handling and consistent HTTP status code mapping. |
| 27 | [#4347](https://github.com/firebase/genkit/issues/4347) | **PY** | **Tool arguments not validated against schema** — `TODO` at `tools.py:212`. Models can pass invalid args and the tool receives garbage. | ✅ **Confirmed** | Implement Pydantic validation before dispatching to tool function. Return structured error to model on validation failure (enables retry). |
| 28 | [#4365](https://github.com/firebase/genkit/issues/4365) | **PY** | **MCP tool args not validated against schema** — similar to #4347 but for MCP-sourced tools. | ✅ **Confirmed** | Same fix pattern as #4347. |

### 11k. Security Issues

| # | Issue | SDK | Summary | Python Verdict | Action / Notes |
|---|-------|:---:|---------|:--------------:|----------------|
| 29 | [#4117](https://github.com/firebase/genkit/issues/4117) | **PY** | **Backend log timestamp leaked into generated text** — internal timestamps appear in model output. If log messages contain secrets (API keys, user data), this is a data leak vector. | 🔍 Investigate | Audit log formatters and verify structured logging (`log_config.py`) never injects into model message assembly. The `web-endpoints-hello` sample's secret masking processor is best practice. |

### 11l. Feature Requests (Production Readiness)

| # | Issue | SDK | Summary | Python Verdict | Action / Notes |
|---|-------|:---:|---------|:--------------:|----------------|
| 30 | [#1598](https://github.com/firebase/genkit/issues/1598) | JS | **Allow changing API key per-request in `generate()`** — multi-tenant apps need per-customer API keys. Currently must create separate Genkit instances. | 💡 Design | Python should support per-request auth override. Consider `ai.generate(config=ModelConfig(api_key="..."))` or a context-based approach. This is critical for SaaS/multi-tenant deployments. |
| 31 | [#663](https://github.com/firebase/genkit/issues/663) | JS | **Support tool calling for models without native support** — simulate tool calling via prompt injection for Ollama/local models. | 💡 Design | This maps to the missing `simulateConstrainedGeneration` middleware (Gap G3 in §8f). When implemented, it would also cover simulated tool calling. |
| 32 | [#4468](https://github.com/firebase/genkit/issues/4468) | All | **RFC: Agents** — first-class agent support with multi-turn planning, memory, and tool orchestration. | 💡 Track | Monitor RFC progress. Python implementation should follow the same API surface as JS. |
| 33 | [#4467](https://github.com/firebase/genkit/issues/4467) | All | **RFC: Session flows** — stateful multi-turn conversations with persistent context. | 💡 Track | Monitor RFC progress. Python's async-first design is well-suited for session management. |
| 34 | [#4466](https://github.com/firebase/genkit/issues/4466) | All | **RFC: Middleware V2** — redesign of the middleware system for composability and layering. | 💡 Track | Directly addresses Python's single-layer middleware gap (§8b). Wait for RFC to stabilize before implementing. |

### 11m. Priority Matrix — Python Actions from Issue Tracker

| Priority | Issue(s) | Category | Action | Effort |
|:--------:|----------|----------|--------|:------:|
| **P0** | #4492 | 🐛 Bug | Fix context-only tool crash + dispatch | S |
| **P0** | #4350 | 📐 Schema | Implement malformed JSON handling in `extract.py` | M |
| **P0** | #4347, #4365 | ⚠️ Error | Validate tool args against schema | M |
| **P0** | #4336 | ⚠️ Error | `GenerationBlockedError` → extend `GenkitError` | S |
| **P1** | #4279 analog | 🔌 Plugin | Audit `compat-oai` raw response population | S |
| **P1** | #3851 analog | 🌊 Stream | Audit streaming + tool-calling message accumulation | M |
| **P1** | §8c.3 | 📡 Telemetry | Add `X-Genkit-Span-Id` header to reflection server | S |
| **P1** | #2278 analog | 📡 Telemetry | Add `force_flush()` for serverless environments | S |
| **P2** | #4490 analog | 🔌 Plugin | Verify Ollama plugin allows arbitrary model names | S |
| **P2** | #3651 analog | 🔌 Plugin | Audit Vertex AI `global` location URL construction | S |
| **P2** | #4299 analog | 🔌 Plugin | Audit MCP client init error surfacing | S |
| **P2** | #3810 analog | 📖 DevX | Document plugin capability matrices (structured output, tools, streaming) | M |
| **P2** | #4110 analog | 📐 Schema | Test discriminated unions / `$ref` resolution with Gemini API | M |
| **P2** | #1598 | 💡 Feature | Design per-request API key override | L |
| **P3** | #3839 analog | 🐛 Bug | Audit prompt template mutation safety | S |
| **P3** | #4117 | 🔒 Security | Audit log/model output isolation | S |
| **P3** | RFCs | 💡 Feature | Track Agent, Session, Middleware V2 RFCs | — |

**Effort**: S = small (< 1 day), M = medium (1–3 days), L = large (3+ days)

### 11n. Summary

| Metric | Count |
|--------|:-----:|
| Total issues analyzed | 34 |
| ✅ Confirmed in Python | 5 (#4492, #4350, #4347, #4365, #4336 + §8c.3 span header) |
| ⚠️ Likely applicable | 9 |
| 🔍 Needs investigation | 12 |
| 🛡️ Already protected | 1 |
| ➖ Not applicable | 2 |
| 💡 Feature requests to track | 5 |
| **P0 actions (immediate)** | **4 work items** |
| **P1 actions (next sprint)** | **4 work items** |
| **P2 actions (planned)** | **7 work items** |
| **P3 actions (backlog)** | **3 work items** |

---

## 12. Fixability Assessment — "⚠️ Likely" Issues in Python

> Each of the 9 "⚠️ Likely applicable" issues from §11 was verified against the
> Python SDK source. Below is the code-level verdict and recommended action.

### 12a. Fixable in Python Code (5 of 9)

| # | Issue | Category | Code Location | Verdict | Fix |
|---|-------|----------|---------------|---------|-----|
| 5 | [#4279](https://github.com/firebase/genkit/issues/4279) — `compat-oai` raw response empty | 🔌 Plugin | `compat-oai/models/*.py` — no `custom=` field set on `GenerateResponseData` | **Fixable** | Populate `custom` field with the raw API response dict in all compat-oai model response constructors. |
| 7 | [#4110](https://github.com/firebase/genkit/issues/4110) — Schema `$ref` regression | 📐 Schema | `google-genai/models/gemini.py:1090–1119` — `_convert_schema_property()` resolves `$ref` via `$defs` | **Already handled** ✅ but needs test coverage | Add test cases for `Literal` + `Union` discriminated unions, recursive schemas, and deeply nested `$ref`. |
| 8 | [#2758](https://github.com/firebase/genkit/issues/2758) — Pydantic schema pitfalls | 📐 Schema | `google-genai/models/gemini.py` schema conversion | **Fixable** | Write provider-specific schema compat tests for `Optional`, `Field(description=...)`, `Literal`, nested unions. |
| 14 | [#2278](https://github.com/firebase/genkit/issues/2278) — Telemetry not exported in serverless | 📡 Telemetry | `genkit/core/trace/` — `force_flush()` exists but not auto-called on exit | **Fixable** | Add `atexit` handler or document `ai.close()` / `force_flush()` requirement for serverless. |
| 22 | CI/CD interactive prompt | 📦 Install | `genkit start` CLI tooling | **Fixable** | Verify `CI=true` suppresses prompts; add `GENKIT_NONINTERACTIVE=1` support if needed. |

### 12b. Documentation / Audit Only (3 of 9)

| # | Issue | Category | Verdict | Action |
|---|-------|----------|---------|--------|
| 16 | [#4501](https://github.com/firebase/genkit/issues/4501) — Outdated docs | 📖 DevX | **Docs audit** | Run all README/docstring examples against current SDK; fix failures. |
| 17 | [#3810](https://github.com/firebase/genkit/issues/3810) — Ollama structured output misleading | 📖 DevX | **🛡️ Already protected** — Python Ollama plugin allows arbitrary models via `resolve()` fallback and declares `'output': ['text', 'json'], 'constrained': 'all'` | Document which Ollama models reliably produce JSON mode output. |
| 18 | [#3915](https://github.com/firebase/genkit/issues/3915) — Gemini quota errors | 📖 DevX | **Docs task** | Add quota/rate-limit notes to getting-started samples. |

### 12c. Already Protected (1 of 9)

| # | Issue | Category | Verdict |
|---|-------|----------|---------|
| 19 | [#2758](https://github.com/firebase/genkit/issues/2758) (dup) — Schema pitfalls undocumented | 📖 DevX | Same as #8 — code fix is schema testing; doc fix is compatibility matrix. |

---

## 13. Dependency Graph & Reverse Topological Sort Roadmap

### 13a. Dependency Graph

Each node is a work item. An arrow A → B means "B depends on A" (A must land first).

```
                    ┌───────────────────────────────────────────────────────────┐
                    │              DEPENDENCY GRAPH                             │
                    │              (arrows = "must land before")               │
                    └───────────────────────────────────────────────────────────┘

  ╔══════════════════════════════════════════════════════════════════╗
  ║  LAYER 0 — No dependencies (all independent, can run parallel) ║
  ╚══════════════════════════════════════════════════════════════════╝

  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
  │ W1: Error        │  │ W2: Context-only │  │ W3: Malformed    │
  │ hierarchy        │  │ tool crash       │  │ JSON handling    │
  │ #4336 + #4346    │  │ #4492            │  │ #4350            │
  │ generate.py      │  │ _registry.py     │  │ extract.py       │
  │ tools.py         │  │                  │  │                  │
  └────────┬─────────┘  └──────────────────┘  └──────────────────┘
           │
           │ (establishes GenkitError base)
           ▼
  ╔══════════════════════════════════════════════════════════════════╗
  ║  LAYER 1 — Depends on W1 (error hierarchy)                     ║
  ╚══════════════════════════════════════════════════════════════════╝

  ┌──────────────────┐
  │ W4: Tool arg     │
  │ validation       │
  │ #4347 + #4365    │
  │ tools.py         │
  │ (uses GenkitError│
  │  for validation  │
  │  errors)         │
  └────────┬─────────┘
           │
           │ (validation relies on error types + schema infra)
           ▼
  ╔══════════════════════════════════════════════════════════════════╗
  ║  LAYER 2 — Depends on W4 (validation infrastructure)           ║
  ╚══════════════════════════════════════════════════════════════════╝

  ┌──────────────────┐  ┌──────────────────┐
  │ W5: compat-oai   │  │ W6: Streaming +  │
  │ raw response     │  │ tools message    │
  │ #4279 analog     │  │ accumulation     │
  │ compat-oai/*.py  │  │ #3851 analog     │
  │                  │  │ generate.py      │
  └──────────────────┘  └──────────────────┘

  ╔══════════════════════════════════════════════════════════════════╗
  ║  LAYER 2 (parallel) — No core deps, can run alongside W4      ║
  ╚══════════════════════════════════════════════════════════════════╝

  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
  │ W7: Span-Id      │  │ W8: force_flush  │  │ W9: Schema       │
  │ header           │  │ serverless       │  │ compat tests     │
  │ §8c.3            │  │ #2278 analog     │  │ #4110 + #2758    │
  │ reflection API   │  │ trace/*.py       │  │ google-genai     │
  └──────────────────┘  └──────────────────┘  └──────────────────┘

  ╔══════════════════════════════════════════════════════════════════╗
  ║  LAYER 3 — Depends on W9 (schema compat tests)                 ║
  ╚══════════════════════════════════════════════════════════════════╝

  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
  │ W10: Plugin      │  │ W11: Vertex AI   │  │ W12: MCP init    │
  │ capability docs  │  │ global URL       │  │ error surfacing  │
  │ #3810 analog     │  │ #3651 analog     │  │ #4299 analog     │
  │ README files     │  │ vertex-ai plugin │  │ mcp plugin       │
  └──────────────────┘  └──────────────────┘  └──────────────────┘

  ╔══════════════════════════════════════════════════════════════════╗
  ║  LAYER 4 — Feature design (long-term)                          ║
  ╚══════════════════════════════════════════════════════════════════╝

  ┌──────────────────┐  ┌──────────────────┐
  │ W13: Per-request │  │ W14: RFC         │
  │ API key override │  │ tracking         │
  │ #1598            │  │ Agents/Sessions/ │
  │ genkit core      │  │ Middleware V2    │
  └──────────────────┘  └──────────────────┘
```

### 13b. File Conflict Matrix

Work items touching the same file must be ordered or merged into one PR:

| File | Work Items | Conflict? | Resolution |
|------|:---------:|:---------:|------------|
| `blocks/generate.py` | W1, W6 | ⚠️ Yes | W1 lands first (error class at EOF), then W6 (message accumulation in body) |
| `blocks/tools.py` | W1, W4 | ⚠️ Yes | W1 lands first (`ToolInterruptError` base class), then W4 (validation) |
| `ai/_registry.py` | W2 | — | No conflicts |
| `core/extract.py` | W3 | — | No conflicts |
| `compat-oai/models/*.py` | W5 | — | No conflicts |
| `core/trace/*.py` | W8 | — | No conflicts |
| `google-genai/models/gemini.py` | W9 | — | No conflicts |

### 13c. Reverse Topological Sort — Execution Order

Items are listed in **dependency-safe order** (leaves first). Items at the same
layer can execute in parallel.

```
Sprint 1 (P0 — immediate, ~3 days)
──────────────────────────────────
  [parallel]
  ├── PR-A: W1 — Error hierarchy (#4336 + #4346)
  ├── PR-B: W2 — Context-only tool crash (#4492)
  └── PR-C: W3 — Malformed JSON handling (#4350)

  [sequential after PR-A]
  └── PR-D: W4 — Tool arg validation (#4347 + #4365)

Sprint 2 (P1 — next sprint, ~4 days)
─────────────────────────────────────
  [parallel]
  ├── PR-E: W5 — compat-oai raw response (#4279 analog)
  ├── PR-F: W6 — Streaming + tools message audit (#3851 analog)
  ├── PR-G: W7 — X-Genkit-Span-Id header (§8c.3)
  └── PR-H: W8 — force_flush for serverless (#2278 analog)

Sprint 3 (P2 — planned, ~5 days)
──────────────────────────────────
  [parallel]
  ├── PR-I: W9  — Schema compat tests (#4110 + #2758)
  ├── PR-J: W11 — Vertex AI global URL audit (#3651 analog)
  └── PR-K: W12 — MCP init error surfacing (#4299 analog)

  [after PR-I]
  └── PR-L: W10 — Plugin capability docs (#3810 analog)

Sprint 4+ (P3/backlog)
─────────────────────
  PR-M: W13 — Per-request API key override (design RFC)
  PR-N: W14 — Track Agent/Session/Middleware V2 RFCs
```

### 13d. PR Manifest with Regression Tests

| PR | Branch | Work Items | Files Changed | Regression Tests Required | Commit Message |
|----|--------|:----------:|:-------------:|---------------------------|----------------|
| **A** | `yesudeep/fix/error-hierarchy` | W1 | `generate.py`, `tools.py` | `test_generation_response_error_is_genkit_error`, `test_tool_interrupt_error_is_genkit_error`, `test_generation_blocked_error_http_status` | `fix(py/core): make GenerationResponseError and ToolInterruptError extend GenkitError` |
| **B** | `yesudeep/fix/context-only-tool` | W2 | `_registry.py` | `test_tool_with_only_context_param`, `test_tool_with_context_and_input`, `test_tool_with_no_params`, `test_tool_schema_skips_context_type` | `fix(py/core): handle tools with only ToolRunContext parameter` |
| **C** | `yesudeep/fix/malformed-json` | W3 | `extract.py` | `test_extract_json_markdown_fences`, `test_extract_json_trailing_comma`, `test_extract_json_bare_string`, `test_parse_partial_json_incomplete`, `test_extract_json_with_code_block` | `fix(py/core): handle malformed JSON in extract.py` |
| **D** | `yesudeep/fix/tool-validation` | W4 | `tools.py`, `generate.py` | `test_tool_validates_input_schema`, `test_tool_validation_error_message`, `test_mcp_tool_validates_input`, `test_tool_validation_allows_valid_input` | `fix(py/core): validate tool arguments against schema before dispatch` |
| **E** | `yesudeep/fix/compat-oai-raw` | W5 | `compat-oai/models/*.py` | `test_chat_response_has_raw_data`, `test_image_response_has_raw_data`, `test_audio_response_has_raw_data` | `fix(py/compat-oai): populate custom/raw field on GenerateResponseData` |
| **F** | `yesudeep/audit/streaming-tools` | W6 | `generate.py` (audit) | `test_streaming_tool_calls_preserve_messages`, `test_streaming_multi_turn_history` | `fix(py/core): preserve message history during streaming tool calls` |
| **G** | `yesudeep/fix/span-id-header` | W7 | `web/manager/*.py` | `test_reflection_response_has_span_id_header` | `fix(py/core): add X-Genkit-Span-Id header to reflection server` |
| **H** | `yesudeep/fix/serverless-flush` | W8 | `ai/_aio.py`, `core/trace/*.py` | `test_force_flush_called_on_close`, `test_atexit_handler_registered` | `fix(py/core): ensure trace flush in serverless environments` |
| **I** | `yesudeep/test/schema-compat` | W9 | `tests/` (new test files) | `test_discriminated_union_schema`, `test_recursive_schema_ref`, `test_optional_field_schema`, `test_literal_field_schema`, `test_nested_ref_resolution` | `test(py/google-genai): add schema compatibility tests for Pydantic edge cases` |
| **J** | `yesudeep/audit/vertex-global-url` | W11 | `vertex-ai/` (audit) | `test_global_location_url_construction` | `fix(py/vertex-ai): audit global location URL construction` |
| **K** | `yesudeep/fix/mcp-init-errors` | W12 | `mcp/` plugin | `test_mcp_init_bad_url_raises`, `test_mcp_init_connection_refused_raises` | `fix(py/mcp): surface initialization errors immediately` |
| **L** | `yesudeep/docs/plugin-capabilities` | W10 | `README.md` files | — (docs only) | `docs(py/plugins): add capability matrices for structured output, tools, streaming` |

### 13e. Regression Test Specifications

Each test below targets a specific bug to prevent regressions.

#### PR-A: Error Hierarchy Tests

```python
# tests/genkit/blocks/generate_error_test.py
def test_generation_response_error_is_genkit_error():
    """GenerationResponseError must be a subclass of GenkitError."""
    assert issubclass(GenerationResponseError, GenkitError)

def test_generation_response_error_has_status():
    """GenerationResponseError must have a status field for HTTP mapping."""
    err = GenerationResponseError(response=mock_response, message="blocked",
                                   status="FAILED_PRECONDITION", details={})
    assert err.status == "FAILED_PRECONDITION"

# tests/genkit/blocks/tools_error_test.py
def test_tool_interrupt_error_is_genkit_error():
    """ToolInterruptError must be a subclass of GenkitError."""
    assert issubclass(ToolInterruptError, GenkitError)
```

#### PR-B: Context-Only Tool Tests

```python
# tests/genkit/ai/tool_context_test.py
def test_tool_with_only_context_param():
    """A tool with only ToolRunContext must not crash at registration."""
    @ai.tool()
    def my_tool(ctx: ToolRunContext) -> str:
        return "ok"
    # Should not raise PydanticSchemaGenerationError
    assert my_tool is not None

def test_tool_with_no_params():
    """A tool with no params must register and execute."""
    @ai.tool()
    def no_params_tool() -> str:
        return "hello"
    assert no_params_tool is not None

def test_tool_schema_skips_context_type():
    """Schema generation must skip ToolRunContext, not try to build schema for it."""
    @ai.tool()
    def ctx_tool(ctx: ToolRunContext) -> str:
        return "ok"
    action = ai.registry.lookup_action(ActionKind.TOOL, "ctx_tool")
    assert action.input_schema is None or "ToolRunContext" not in str(action.input_schema)
```

#### PR-C: Malformed JSON Tests

```python
# tests/genkit/core/extract_malformed_test.py
def test_extract_json_markdown_fences():
    """JSON wrapped in ```json ... ``` fences must be extracted."""
    text = '```json\n{"key": "value"}\n```'
    assert extract_json(text) == {"key": "value"}

def test_extract_json_with_code_block():
    """JSON inside a markdown code block with extra text must be extracted."""
    text = 'Here is the result:\n```json\n{"name": "test"}\n```\nDone.'
    assert extract_json(text) == {"name": "test"}

def test_extract_json_trailing_comma():
    """JSON with trailing comma must be parsed (json5 handles this)."""
    text = '{"key": "value",}'
    result = extract_json(text)
    assert result == {"key": "value"}
```

#### PR-D: Tool Validation Tests

```python
# tests/genkit/blocks/tool_validation_test.py
def test_tool_validates_input_schema():
    """Invalid tool arguments must raise a validation error, not crash the tool."""
    @ai.tool()
    def typed_tool(input: MyModel) -> str:
        return input.name
    # Passing invalid input should raise structured error
    with pytest.raises(GenkitError) as exc_info:
        await typed_tool.action.arun({"invalid_field": 123})
    assert "validation" in str(exc_info.value).lower()

def test_tool_validation_allows_valid_input():
    """Valid tool arguments must pass validation and execute normally."""
    @ai.tool()
    def typed_tool(input: MyModel) -> str:
        return input.name
    result = await typed_tool.action.arun({"name": "test"})
    assert result.response == "test"
```

---

## 14. Model Conformance Roadmap

> Source: Cross-runtime model conformance testing framework from KI
> `genkit_model_conformance`. The Python SDK follows a phased approach to ensure
> all model provider plugins exhibit identical behavior to the JS canonical
> implementation.

### 14a. Architecture

```
                 py/bin/test-model-conformance
                           |
                           v
               genkit dev:test-model --from-file spec.yaml
                           |
                    discovers runtime
                           |
                           v
                  Reflection Server (:3100)
                           |
                    /api/runAction
                           |
                           v
               Plugin: GoogleAI / Anthropic / etc.
                           ^
                           |
                  conformance_entry.py
```

### 14b. Phased Execution Plan

| Phase | Target | Status | Key Tasks |
|:-----:|--------|:------:|-----------|
| **0** | Foundations | ✅ Done | Imagen support under `googleai/` prefix; directory tree setup |
| **1** | Specs & Entry Points | ✅ Done | Symlink JS specs; create `conformance_entry.py` per plugin; YAML specs for anthropic/compat-oai |
| **2** | Orchestration | ✅ Done | `py/bin/test-model-conformance` script; `uv run --project` integration |
| **3** | Validation | ✅ Done | Discovery across 11 providers verified; multimodal parity (PR #4477) |
| **4** | Remaining Gaps | 📋 Planned | xAI image gen, MS Foundry multimodal, Ollama metadata, final google-genai pass |

### 14c. Plugin Parity Matrix

| Plugin | JS Name | Python Name | Parity | Key Gap |
|--------|---------|-------------|:------:|---------|
| **Anthropic** | `@genkit-ai/anthropic` | `genkit-plugin-anthropic` | ✅ Full + superset | `output_config.effort` minor |
| **Google GenAI** | `@genkit-ai/google-genai` | `genkit-plugin-google-genai` | ✅ Full | — |
| **Vertex AI** | `@genkit-ai/vertexai` | `genkit-plugin-vertex-ai` | ✅ Full | — |
| **OpenAI** | `@genkit-ai/compat-oai/openai` | `genkit-plugin-compat-oai` | ⚠️ Minor | Embeddings, GPT-5 refs, `gpt-image-1` ext config |
| **xAI** | `@genkit-ai/compat-oai/xai` | `genkit-plugin-xai` | ⚠️ Medium | `grok-2-image-1212`, `deferred`, `webSearchOptions`, `reasoningEffort` |
| **DeepSeek** | `@genkit-ai/compat-oai/deepseek` | `genkit-plugin-deepseek` | ✅ Superset | Python has V3, R1 |
| **Ollama** | `@genkit-ai/ollama` | `genkit-plugin-ollama` | ⚠️ Metadata | Missing `media`, `toolChoice` flags |
| **Amazon Bedrock** | External | `genkit-plugin-amazon-bedrock` | 🟢 Superset | — |
| **Microsoft Foundry** | External | `genkit-plugin-microsoft-foundry` | ⚠️ Missing | DALL-E, TTS, Whisper not ported |
| **Mistral** | N/A | `genkit-plugin-mistral` | 🟢 Python-only | — |
| **Hugging Face** | N/A | `genkit-plugin-huggingface` | 🟢 Python-only | — |
| **Cloudflare** | N/A | `genkit-plugin-cloudflare-workers-ai` | 🟢 Python-only | — |
| **Cohere** | N/A | `genkit-plugin-cohere` | 🟢 Python-only | — |

### 14d. Conformance Priority Actions

| Priority | Action | Plugin | Effort |
|:--------:|--------|--------|:------:|
| P1 | Add `media` and `toolChoice` metadata flags | Ollama | S |
| P1 | Add embeddings support | compat-oai | M |
| P2 | Add `grok-2-image-1212` image generation | xAI | M |
| P2 | Add `gpt-image-1` extended config | compat-oai | S |
| P2 | Add `deferred`, `webSearchOptions`, `reasoningEffort` | xAI | S |
| P3 | Add DALL-E/TTS/Whisper | Microsoft Foundry | M |
| P3 | Add GPT-5 model refs | compat-oai | S |
| P4 | Add `output_config.effort` for opus-4-5 | Anthropic | S |

### 14e. Sample Coverage Audit

| Sample | Basic | Stream | Tools | Struct | Vision | Embed | Code | Reason | TTS/STT | Cache | PDF | RAG |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **amazon-bedrock** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **anthropic** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |
| **cloudflare** | ❌ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **compat-oai** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **deepseek** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **google-genai** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **huggingface** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **ms-foundry** | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **mistral** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **ollama** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **xai** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

### 14f. JS-Only Plugins Not Yet in Python

| Plugin | Purpose | Python Priority |
|--------|---------|:---------------:|
| **Chroma** | Vector store (ChromaDB) | Medium |
| **Pinecone** | Vector store (Pinecone) | Medium |
| **Cloud SQL PG** | Vector store (PostgreSQL) | Low |
| **LangChain** | LangChain integration | Low |
| **Checks** | Safety/content evaluation | ✅ Merged (#4504) |

### 14g. Conformance PR Mapping

| Phase | PR | Description | Status |
|:-----:|---:|-------------|:------:|
| P0 | #4472 | Imagen support under `googleai/` prefix | ✅ Merged |
| P0 | #4474 | Model conformance testing plan | ✅ Merged |
| P0/P1/P2 | #4473 | Conformance test infrastructure | ✅ Merged |
| P2+ | #4476 | Specs for remaining 8 providers | ✅ Merged |
| P3 | #4477 | compat-oai multimodal (image, TTS, STT) | ✅ Merged |
| Core | #4401 | Reflection API v2 (WebSocket + JSON-RPC 2.0) | 🔄 Active |
| P4 | — | xAI image generation | 📋 Planned |
| P4 | — | Microsoft Foundry multimodal | 📋 Planned |
| P4 | — | Ollama metadata parity | 📋 Planned |

---

## 15. Combined Roadmap — All Streams

> This section unifies the parity gaps (§7–10), issue tracker fixes (§11–13),
> and model conformance work (§14) into a single prioritized roadmap.

### 15a. Sprint Plan

| Sprint | Timeline | Work Items | PRs | Dependencies |
|:------:|:--------:|:-----------|:---:|:------------:|
| **S1** | Week 1 | W1 (error hierarchy), W2 (context-only tool), W3 (malformed JSON) | A, B, C | None |
| **S1** | Week 1 | W4 (tool validation) — after PR-A lands | D | A |
| **S2** | Week 2 | W5 (compat-oai raw), W6 (streaming audit), W7 (span-id), W8 (force_flush) | E, F, G, H | None |
| **S2** | Week 2 | Ollama metadata flags (conformance P1) | — | None |
| **S3** | Week 3 | W9 (schema compat tests), W11 (vertex URL), W12 (MCP init errors) | I, J, K | None |
| **S3** | Week 3 | W10 (plugin capability docs) — after PR-I | L | I |
| **S3** | Week 3 | compat-oai embeddings (conformance P1) | — | None |
| **S4+** | Week 4+ | Per-request API key design, xAI image gen, MS Foundry multimodal | M, — | RFC |
| **S4+** | Week 4+ | Track Agent/Session/Middleware V2 RFCs | N | External |

### 15b. PR Status (as of 2026-02-11)

#### Recently Merged (since 2026-02-09)

| PR | Title | Merged | Relates To |
|---:|-------|:------:|:----------:|
| #4519 | fix(py/core): `arun_raw` None input validation | 2026-02-09 | OSS compliance |
| #4522 | docs(py): architecture diagrams, concepts table | 2026-02-09 | Documentation |
| #4524 | fix(py): CI license check failures, lint | 2026-02-09 | Tooling |
| #4504 | feat(py/checks): Google Checks AI Safety plugin | 2026-02-09 | Plugin — Checks |
| #4541 | fix(py): uv.lock out of sync | 2026-02-10 | Workspace |
| #4544 | docs(py): release roadmap and orchestration | 2026-02-10 | Release tooling |
| #4547 | fix(py/samples): endpoints sample resilience | 2026-02-10 | Sample — web-endpoints |
| #4548 | feat(py/tools): releasekit — release orchestration | 2026-02-10 | Release tooling |
| #4550 | feat(py/tools): releasekit phase 1 — workspace + graph | 2026-02-10 | Release tooling |
| #4555 | feat(py/tools): releasekit phase 2 — versioning, bump, pin | 2026-02-10 | Release tooling |
| #4556 | feat(releasekit): phase 3 publish MVP | 2026-02-10 | Release tooling |
| #4558 | feat(releasekit): phase 4 Rich Live progress table | 2026-02-10 | Release tooling |
| #4561 | fix(py/plugins/flask): remove cyclical dependency | 2026-02-11 | Plugin — Flask |
| #4563 | feat(releasekit): comprehensive check command | 2026-02-11 | Release tooling |
| #4564 | feat(releasekit): checksum verification + preflight | 2026-02-11 | Release tooling |
| #4565 | feat(releasekit): dependency-triggered scheduler | 2026-02-11 | Release tooling |
| #4569 | feat(releasekit): dynamic scheduler add/remove | 2026-02-11 | Release tooling |
| #4570 | feat(releasekit): tags, changelog, release notes | 2026-02-11 | Release tooling |
| #4571 | fix(py): add missing LICENSE to samples | 2026-02-11 | OSS compliance |
| #4572 | feat(releasekit): Phase 6 UX polish | 2026-02-11 | Release tooling |
| #4574 | feat(releasekit): async refactoring + test suite | 2026-02-11 | Release tooling |
| #4575 | docs(releasekit): adopt release-please model | 2026-02-11 | Release tooling |
| #4577 | feat(releasekit): Forge protocol, transitive propagation | 2026-02-11 | Release tooling |

#### Closed (Superseded)

| PR | Title | Status | Notes |
|---:|-------|:------:|:------|
| #4510 | feat(py): model middleware parity | ❌ Closed | Superseded by new approach |
| #4516 | feat(py): model-level middleware support | ❌ Closed | Superseded |
| #4521 | feat(py/core): api_key() context provider | ❌ Closed | Superseded |

#### Currently Open

| PR | Title | Status | Relates To |
|---:|-------|:------:|:----------:|
| #4401 | feat(py): Reflection API v2 (WebSocket + JSON-RPC) | 🔄 Active | Conformance core |
| #4512 | feat(py/genkit): Genkit constructor parity | 🔄 Open | §14e samples |
| #4513 | feat(py/genkit): multipart tool support | 🔄 Open | Gap G18 |
| #4517 | docs(py): PARITY_AUDIT.md update | 🔄 Open | This document |
| #4538 | fix(py/ai): dotprompt input.default for DevUI | 🔄 Open | Dotprompt |
| #4549 | fix(py/core): guard RealtimeSpanProcessor export | 🔄 Open | Telemetry |
| #4578 | fix(js): duplicate sample project names | 🔄 Open | Cross-SDK |
| #4584 | fix(py/genkit): framework classifiers, Changelog URL | 🔄 Open | Release prep |
| #4585 | docs(releasekit): README, roadmap, CHANGELOG | 🔄 Open | Release tooling docs |
| #4586 | ci(releasekit): migrate publish_python.yml | 🔄 Open | CI automation |
| #4587 | feat(releasekit): log view keyboard shortcut | 🔄 Open | Release tooling UX |

### 15c. Summary Metrics

| Metric | Value |
|--------|:-----:|
| Total work items (issue tracker) | 14 (W1–W14) |
| Total work items (conformance) | 8 (P1–P4) |
| Total work items (parity gaps §7) | 30 (G1–G37) |
| **Combined unique actions** | **~45** |
| PRs merged (total since §15 inception) | **31** |
| PRs currently open | **11** |
| PRs closed (superseded) | **3** |
| PRs in Sprint 1 (P0) | 4 (A, B, C, D) |
| PRs in Sprint 2 (P1) | 4 (E, F, G, H) |
| PRs in Sprint 3 (P2) | 4 (I, J, K, L) |
| Estimated weeks to P0 closure | 1 week |
| Estimated weeks to P1 closure | 2 weeks |
| Estimated weeks to P2 closure | 3 weeks |
| Regression tests required | ~35 new test functions across 12 PRs |
| **New: releasekit (release tooling)** | **14 PRs merged, 3 PRs open** |

---

## 16. Sample Flow Test Plan — Optimal Error Detection Order

> **Goal**: Execute sample flows in an order that maximizes early bug detection.
> The strategy: exercise **core framework features first** (where bugs affect
> all providers), then test **the cheapest provider** (Google GenAI free tier),
> then progressively test more specialized providers.

### 16a. Execution Order Rationale

```
                    ┌─────────────────────────────────────────────────────┐
                    │          ERROR DETECTION PRIORITY PYRAMID           │
                    │                                                     │
                    │  Layer 1 (Core Framework)    ← Bugs here affect    │
                    │  ┌─────────────────────┐       ALL providers       │
                    │  │ Tools, Streaming,    │                           │
                    │  │ Structured Output,   │   Test FIRST             │
                    │  │ Interrupts, Formats  │                           │
                    │  └─────────────────────┘                           │
                    │                                                     │
                    │  Layer 2 (Cheapest Provider) ← Free tier = fast,   │
                    │  ┌─────────────────────┐       cheap validation    │
                    │  │ Google GenAI         │                           │
                    │  │ (Gemini free tier)   │   Test SECOND            │
                    │  └─────────────────────┘                           │
                    │                                                     │
                    │  Layer 3 (Multi-Provider)    ← Same features,      │
                    │  ┌──────────────────────────┐  different plugins   │
                    │  │ Anthropic, OpenAI, Ollama,│                     │
                    │  │ Mistral, DeepSeek, xAI   │ Test THIRD           │
                    │  └──────────────────────────┘                     │
                    │                                                     │
                    │  Layer 4 (Specialized)       ← Unique features    │
                    │  ┌──────────────────────────┐                     │
                    │  │ Vertex AI, Bedrock, Cloud │                     │
                    │  │ infra, evals, RAG, media  │ Test FOURTH         │
                    │  └──────────────────────────┘                     │
                    │                                                     │
                    │  Layer 5 (Web Infra)         ← Deployment, not    │
                    │  ┌──────────────────────────┐  model logic         │
                    │  │ Flask, ASGI, multi-server,│                     │
                    │  │ gRPC endpoints            │ Test LAST           │
                    │  └──────────────────────────┘                     │
                    └─────────────────────────────────────────────────────┘
```

### 16b. Ordered Test Execution Plan

Each row below is a sample to test. Column "Features Exercised" lists the
core Genkit capabilities each sample validates. The order is designed so that
the **first failure** reveals the **most impactful bug**.

**Usage**: `py/bin/test_sample_flows <sample-name>` or `py/bin/run_sample <sample-name>`

---

#### Phase 1: Core Framework (no external API keys needed for some)

These samples exercise core Genkit framework features. A bug here affects
every downstream provider.

| # | Sample | Env Vars | Flows | Tools | Features Exercised |
|:-:|--------|----------|:-----:|:-----:|:-------------------|
| 1 | `framework-tool-interrupts` | `GEMINI_API_KEY` | 1 | 1 | **Tool interrupts** (human-in-the-loop), `ctx.interrupt()`, `tool_response()`, resume flow — directly validates W1 (error hierarchy) and W4 (tool validation) |
| 2 | `framework-context-demo` | `GEMINI_API_KEY` | 4 | 3 | **Context providers**, auth propagation, `ToolRunContext` usage — directly validates W2 (context-only tool crash) |
| 3 | `framework-dynamic-tools-demo` | `GEMINI_API_KEY` | 3 | 2 | **Dynamic tool registration**, DAP action discovery — validates registry internals |
| 4 | `framework-format-demo` | `GEMINI_API_KEY` | ~5 | 0 | **Output formats** (JSON, text, custom), structured output, format injection — validates W3 (malformed JSON) |
| 5 | `framework-prompt-demo` | `GEMINI_API_KEY` | ~3 | 0 | **Dotprompt** templates, system prompts, prompt files — validates prompt parsing |
| 6 | `framework-middleware-demo` | `GEMINI_API_KEY` | ~3 | 0 | **Action middleware**, model middleware, context middleware — validates middleware chain |
| 7 | `framework-realtime-tracing-demo` | `GEMINI_API_KEY` | ~3 | 0 | **OpenTelemetry** traces, spans, real-time trace streaming — validates W7 (span-id) and W8 (force_flush) |
| 8 | `framework-restaurant-demo` | `GEMINI_API_KEY` | ~3 | 0 | **Sessions**, multi-turn chat, state management — validates session/chat infrastructure |
| 9 | `framework-evaluator-demo` | `GEMINI_API_KEY` | N/A | N/A | **Evaluators**, custom scorers — validates evaluation infrastructure |

#### Phase 2: Google GenAI (free tier — cheapest to test)

The highest flow coverage with zero cost. This is the primary provider for
the Python SDK.

| # | Sample | Env Vars | Flows | Tools | Features Exercised |
|:-:|--------|----------|:-----:|:-----:|:-------------------|
| 10 | `provider-google-genai-hello` | `GEMINI_API_KEY` | 24 | 7 | **Complete feature set**: basic, streaming, tools, structured output, vision, embeddings, code gen, multi-turn, system prompt, temperature config — exercises the most code paths |
| 11 | `provider-google-genai-code-execution` | `GEMINI_API_KEY` | ~2 | 0 | **Code execution** sandbox — exercises config forwarding |
| 12 | `provider-google-genai-context-caching` | `GEMINI_API_KEY` | ~2 | 0 | **Context caching** — exercises cache config and token optimization |
| 13 | `provider-google-genai-media-models-demo` | `GEMINI_API_KEY` | 13 | 1 | **Imagen + Veo** image/video generation — exercises multimodal output |
| 14 | `provider-google-genai-vertexai-hello` | `GOOGLE_CLOUD_PROJECT` | 15 | 3 | **Vertex AI** variant — same features but with Vertex credentials |
| 15 | `provider-google-genai-vertexai-image` | `GOOGLE_CLOUD_PROJECT` | 1 | 0 | **Vertex AI Imagen** — specialized image generation |

#### Phase 3: Multi-Provider (validate cross-provider parity)

Each provider should behave identically for basic/streaming/tools/structured.
A failure here that doesn't appear in Phase 2 isolates a **plugin-specific bug**.

| # | Sample | Env Vars | Flows | Tools | Features Exercised | Unique Tests |
|:-:|--------|----------|:-----:|:-----:|:-------------------|:-------------|
| 16 | `provider-ollama-hello` | (local Ollama) | 14 | 1 | Basic, stream, tools, struct, vision, embed, RAG | **RAG flow** (unique to Ollama), local-only model, arbitrary model resolution |
| 17 | `provider-anthropic-hello` | `ANTHROPIC_API_KEY` | 15 | 1 | Basic, stream, tools, struct, vision, code, reasoning | **Prompt caching**, PDF support, extended thinking |
| 18 | `provider-compat-oai-hello` | `OPENAI_API_KEY` | 19 | 3 | Basic, stream, tools, struct, code, **TTS/STT** | **Audio** (TTS, STT), image generation — validates W5 (raw response) |
| 19 | `provider-deepseek-hello` | `DEEPSEEK_API_KEY` | 12 | 1 | Basic, stream, tools, struct, code, reasoning | **Deep reasoning** (V3/R1) |
| 20 | `provider-mistral-hello` | `MISTRAL_API_KEY` | 18 | 1 | Basic, stream, tools, struct, vision, embed, code, reasoning | **Mistral-specific** `codestral` model |
| 21 | `provider-xai-hello` | `XAI_API_KEY` | 13 | 0 | Basic, stream, tools, struct, code | Grok models, native gRPC SDK |
| 22 | `provider-huggingface-hello` | `HF_TOKEN` | 15 | 1 | Basic, stream, tools, struct, code | **HF Inference API**, multiple model architectures |
| 23 | `provider-microsoft-foundry-hello` | `AZURE_OPENAI_*` | 13 | 1 | Basic, stream, tools, vision, code | **Azure endpoints** — validates W12 (MCP/init errors) |
| 24 | `provider-cohere-hello` | `COHERE_API_KEY` | 15 | 1 | Basic, stream, tools, struct, code | **Cohere** rerank, embeddings (if present) |
| 25 | `provider-cloudflare-workers-ai-hello` | `CLOUDFLARE_*` | ~5 | 0 | Stream, tools, vision, embed, code | **Cloudflare Workers AI** — edge inference |

#### Phase 4: Specialized Infrastructure

These test provider-specific infrastructure (vector search, evals, RAG).

| # | Sample | Env Vars | Flows | Features Exercised |
|:-:|--------|----------|:-----:|:-------------------|
| 26 | `dev-local-vectorstore-hello` | `GOOGLE_CLOUD_PROJECT` | 2 | **Local vector store**, document indexing, retrieval |
| 27 | `provider-vertex-ai-model-garden` | `GOOGLE_CLOUD_PROJECT` | 11 | **Model Garden** (Llama, Claude on Vertex), cross-model tool calling |
| 28 | `provider-vertex-ai-rerank-eval` | `GOOGLE_CLOUD_PROJECT` | 7 | **Reranking**, evaluation flows, quality scoring |
| 29 | `provider-vertex-ai-vector-search-firestore` | `GOOGLE_CLOUD_PROJECT` | 1 | **Firestore vector search** integration |
| 30 | `provider-vertex-ai-vector-search-bigquery` | `GOOGLE_CLOUD_PROJECT` | 2 | **BigQuery vector search** integration |
| 31 | `provider-firestore-retriever` | `GOOGLE_CLOUD_PROJECT` | ~2 | **Firestore retriever** plugin |
| 32 | `provider-observability-hello` | `GEMINI_API_KEY` | 1 | **Custom observability** plugin |

#### Phase 5: Web Framework Integration

These test deployment infrastructure, not model logic. Bugs here are
isolated to serving layer.

| # | Sample | Env Vars | Flows | Features Exercised |
|:-:|--------|----------|:-----:|:-------------------|
| 33 | `web-flask-hello` | `GEMINI_API_KEY` | 1 | **Flask** integration, context providers, `genkit_flask_handler` |
| 34 | `web-short-n-long` | `GEMINI_API_KEY` | 14 | **ASGI deployment** (`create_flows_asgi_app`), tools, interrupts, embeddings, image gen, system prompts, multi-turn, streaming |
| 35 | `web-endpoints-hello` | `GEMINI_API_KEY` | 8 | **Production ASGI** (FastAPI/Litestar/Quart), gRPC, rate limiting, circuit breaker, security headers, caching |
| 36 | `web-multi-server` | `GEMINI_API_KEY` | 1 | **Multi-server** architecture, `ServerManager`, multiple ASGI apps |

### 16c. Feature Coverage Matrix by Phase

| Feature | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 |
|---------|:-------:|:-------:|:-------:|:-------:|:-------:|
| `@ai.flow()` basic | ✅ | ✅ | ✅ | ✅ | ✅ |
| `@ai.tool()` basic | ✅ | ✅ | ✅ | — | ✅ |
| Streaming | ✅ | ✅ | ✅ | — | ✅ |
| Structured output | ✅ | ✅ | ✅ | — | ✅ |
| Tool interrupts | ✅ | — | — | — | ✅ |
| `ToolRunContext` | ✅ | — | — | — | — |
| Context providers | ✅ | — | — | — | ✅ |
| Dynamic tools (DAP) | ✅ | — | — | — | — |
| Dotprompt | ✅ | — | — | — | — |
| Middleware | ✅ | — | — | — | — |
| OpenTelemetry | ✅ | — | — | — | ✅ |
| Sessions | ✅ | — | — | — | — |
| Evaluators | ✅ | — | — | ✅ | — |
| Vision/multimodal | — | ✅ | ✅ | — | — |
| Embeddings | — | ✅ | ✅ | ✅ | ✅ |
| Code execution | — | ✅ | ✅ | — | — |
| TTS/STT audio | — | — | ✅ | — | — |
| Image generation | — | ✅ | ✅ | — | ✅ |
| RAG/retrieval | — | — | ✅ | ✅ | — |
| Reranking | — | — | — | ✅ | — |
| Vector search | — | — | — | ✅ | — |
| Multi-turn chat | ✅ | ✅ | — | — | ✅ |
| System prompts | ✅ | ✅ | — | — | ✅ |
| ASGI deployment | — | — | — | — | ✅ |
| Flask deployment | — | — | — | — | ✅ |
| gRPC endpoints | — | — | — | — | ✅ |
| Rate limiting | — | — | — | — | ✅ |
| Circuit breaker | — | — | — | — | ✅ |

### 16d. Quick-Start Commands

```bash
# Run all Phase 1 (core framework) — no API cost, fastest
for s in framework-tool-interrupts framework-context-demo \
         framework-dynamic-tools-demo framework-format-demo \
         framework-prompt-demo framework-middleware-demo; do
    py/bin/test_sample_flows "$s"
done

# Run Phase 2 (Google GenAI) — free tier
for s in provider-google-genai-hello \
         provider-google-genai-code-execution \
         provider-google-genai-media-models-demo; do
    py/bin/test_sample_flows "$s"
done

# Run ALL phases (full regression)
py/bin/test_sample_flows  # interactive mode with fzf
```

### 16e. Expected Bug Detection by Phase

| Phase | Estimated Bug Yield | Bugs Caught |
|:-----:|:-------------------:|-------------|
| **1** | ~60% of total | W1 (error hierarchy), W2 (context-only tool), W3 (malformed JSON), W4 (tool validation), W7 (span-id), W8 (force_flush), session bugs, middleware bugs |
| **2** | ~15% of total | Schema regression (W9), config forwarding, multimodal output, generation request construction |
| **3** | ~15% of total | Plugin-specific: W5 (compat-oai raw response), provider schema handling, streaming parity, tool name escaping |
| **4** | ~5% of total | Vector search, retrieval, reranking, eval infrastructure |
| **5** | ~5% of total | ASGI/Flask serving, security middleware, gRPC, rate limiting |

### 16f. Environment Variable Quick Reference

| Env Var | Used By | How to Get |
|---------|---------|------------|
| `GEMINI_API_KEY` | All `framework-*`, `provider-google-genai-*`, all `web-*` | [Google AI Studio](https://aistudio.google.com/apikey) (free) |
| `GOOGLE_CLOUD_PROJECT` | `provider-google-genai-vertexai-*`, `provider-vertex-ai-*`, `dev-local-*`, `provider-firestore-*` | [Google Cloud Console](https://console.cloud.google.com) |
| `ANTHROPIC_API_KEY` | `provider-anthropic-hello` | [Anthropic Console](https://console.anthropic.com) |
| `OPENAI_API_KEY` | `provider-compat-oai-hello` | [OpenAI Platform](https://platform.openai.com/api-keys) |
| `DEEPSEEK_API_KEY` | `provider-deepseek-hello` | [DeepSeek Platform](https://platform.deepseek.com) |
| `MISTRAL_API_KEY` | `provider-mistral-hello` | [Mistral Console](https://console.mistral.ai) |
| `XAI_API_KEY` | `provider-xai-hello` | [xAI Console](https://console.x.ai) |
| `HF_TOKEN` | `provider-huggingface-hello` | [Hugging Face](https://huggingface.co/settings/tokens) |
| `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_ENDPOINT` | `provider-microsoft-foundry-hello` | [Azure Portal](https://portal.azure.com) |
| `COHERE_API_KEY` | `provider-cohere-hello` | [Cohere Dashboard](https://dashboard.cohere.com) |
| `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` | `provider-cloudflare-workers-ai-hello` | [Cloudflare Dashboard](https://dash.cloudflare.com) |
| (none — local Ollama) | `provider-ollama-hello` | `ollama serve` locally |
