# Genkit Python — Public API Surface Proposal

Stable public symbols — what we document, support, and commit to. Everything else is internal.

Two audiences, separate entry points:

1. **App developers** — `from genkit import ...` for framework objects, content types, errors.
2. **Plugin authors / advanced users** — domain sub-modules (`genkit.model`, `genkit.retriever`, etc.) for request/response schemas, config types, metadata builders.

> **Type architecture detail:** The SDK has schema types (auto-generated Pydantic models from `genkit-schemas.json`) and veneers (hand-written wrappers that add convenience methods like `.text`, `.output`). See [Type Architecture](#type-architecture) appendix at the end of this doc for the full breakdown.

---

## Entry point 1: `from genkit import ...`

The single entry point for app developers. Framework objects, veneers, context, errors, and all content/data types live here. No separate `genkit.types` import needed.

```python
from genkit import (
    # Core
    Genkit,
    ActionRunContext,
    GenerateResponse,      # veneer — aliased from GenerateResponseWrapper
    GenerateResponseChunk, # veneer — aliased from GenerateResponseChunkWrapper (streaming)
    GenkitError,
    UserFacingError,
    Prompt,

    # Content
    Part, TextPart, MediaPart, Media,
    DataPart, ToolRequestPart, ToolResponsePart, CustomPart,
    ReasoningPart,

    # Messages
    Message, Role, Metadata,

    # Documents
    Document, DocumentData, DocumentPart,

    # Context
    ToolRunContext,
    ToolInterruptError,

    # Evaluation
    BaseEvalDataPoint,

    # Tool control
    ToolChoice,

    # Generation config
    GenerationCommonConfig,

    # Plugin authoring (also used by advanced app developers)
    Plugin,
    Action,
    ActionMetadata,
    ActionKind,
    StatusName,
    to_json_schema,
)
```

**~29 symbols.** One import covers both app developers (~22 symbols) and plugin authors (~7 additional). This is normal for Python — OpenAI and Anthropic export far more from their top level.

- `Genkit` — the entry point. Every app starts with this.
- `ActionRunContext` — context object inside flows and tools.
- `GenerateResponse` — return type of `ai.generate()` — veneer with `.text`, `.output`, `.tool_requests`.
- `GenerateResponseChunk` — chunk type from `ai.generate_stream()` — veneer with `.text` (aliased from `GenerateResponseChunkWrapper`).
- `Prompt` — return type of `ai.prompt()`. Core concept, needs to be type-annotatable.
- `GenkitError` — base error class for catching framework errors.
- `UserFacingError` — errors safe to surface to HTTP clients.
- `Part`, `TextPart`, `MediaPart`, `Media`, `DataPart`, `ToolRequestPart`, `ToolResponsePart`, `CustomPart`, `ReasoningPart` — content types developers construct and pass around.
- `Message`, `Role`, `Metadata` — message construction for multi-turn conversations.
- `Document`, `DocumentData`, `DocumentPart` — RAG document types.
- `ToolRunContext` — extended context for tool handlers (extends `ActionRunContext`).
- `ToolInterruptError` — error type for tool interrupts.
- `ToolChoice` — tool selection control for `generate()`.
- `GenerationCommonConfig` — model config (temperature, top_k, etc.).
- `BaseEvalDataPoint` — evaluation data point type.
- `Plugin` — base class for all plugin types (plugin authors).
- `Action` — core action type (plugin authors).
- `ActionMetadata` — action registration metadata (plugin authors).
- `ActionKind` — action type enum: model, retriever, embedder, etc. (plugin authors).
- `StatusName` — error status codes (plugin authors, error handling).
- `to_json_schema` — converts Pydantic models to JSON Schema (plugin authors, 10+ plugins use this during action registration).

### Veneer aliasing

Users should never see "Wrapper" suffixes. The fix:

```python
# genkit/__init__.py
from genkit.blocks.model import GenerateResponseWrapper as GenerateResponse
from genkit.blocks.model import GenerateResponseChunkWrapper as GenerateResponseChunk
```

Both use inheritance (extend the schema type), so these aliases are safe — `isinstance` checks still work.

**`MessageWrapper` is the exception.** It uses composition — its constructor takes a `Message` instance, not raw fields. Aliasing it as `Message` would break `Message(role="user", content=[...])`. So `Message` remains the schema type everywhere. Users interact with `MessageWrapper` via `response.messages` but never construct it directly.

### `ExecutablePrompt` — should it be public?

`ExecutablePrompt` is the class returned by `ai.prompt()`. Today it's not exported — users can't type-annotate a variable that holds a prompt reference.

```python
# Today: no way to annotate this
my_prompt = ai.prompt("greeting")

# Proposed: export as Prompt
from genkit import Prompt
my_prompt: Prompt = ai.prompt("greeting")
```

Recommendation: export it as `Prompt`. It's a core concept, and being unable to type-annotate it is a gap. This would bring the top-level to 6 symbols.

### What was removed

- `tool_response` — only 3 sample usages. JS/Go use a method on the tool instance.
- `Plugin` — users pass plugin instances (`GoogleAI()`), never reference the type. Moved to shared across domains.
- `get_logger` — thin wrapper around `logging.getLogger("genkit")`. Use the stdlib.
- `GenkitRegistry`, `FlowWrapper`, `SimpleRetrieverOptions` — internal implementation types.

### `ToolRunContext` placement

`ToolRunContext` extends `ActionRunContext` with tool-specific features. Both types are kept (for documentation clarity, future-proofing, and runtime `isinstance` checks), but only `ActionRunContext` is exported from the top level. `ToolRunContext` is available from `genkit.types` for type annotations when needed.

---

Types specific to a domain (model, retriever, embedder, etc.) live in domain sub-modules — not in the top-level `genkit` import. These types are used by both plugin authors and advanced app developers (e.g., writing middleware or defining custom models).

---

## Domain sub-modules

Organized by action type, mirroring the JS SDK's `genkit/model`, `genkit/retriever`, etc. Each sub-module contains the wire-format types, metadata builders, helpers, and options for that domain. Both plugin authors and advanced app developers import from here.

### `genkit.model`

Everything related to model implementation and the model wire format.

```python
from genkit.model import (
    # Wire-format types
    GenerateRequest,
    GenerateResponse,       # schema type — NOT the veneer
    GenerateResponseChunk,
    GenerationUsage,
    Candidate,
    OutputConfig,
    FinishReason,
    GenerateActionOptions,
    Error,                  # schema error type (not GenkitError)
    Operation,              # long-running operation type

    # Tool wire-format types (used by model handlers to process tool calls)
    ToolRequest,
    ToolDefinition,
    ToolResponse,

    # Model info and capabilities
    ModelInfo,
    Supports,
    Constrained,
    Stage,

    # Registration and metadata
    model_action_metadata,
    model_ref,
    ModelReference,

    # Background / long-running models (e.g. video generation)
    BackgroundAction,
    lookup_background_action,

    # Helpers
    compute_usage_stats,
    resolve_api_key,             # resolves API key: request config overrides plugin default
    GenerationCommonConfig,

    # Model middleware - WIP
    ModelMiddleware,
    ModelMiddlewareNext,
)
```

Used by: model plugin authors, app developers writing middleware (`GenerateRequest`, `GenerateResponse`, `ModelMiddlewareNext`), app developers defining custom models (`ModelInfo`, `Supports`).

**Notes on helpers:**

- **`resolve_api_key(config, plugin_key)`** — resolves which API key to use: per-request key from `GenerationCommonConfig` overrides the plugin-level default. In JS, this logic lives duplicated in each plugin's `utils.ts` (`calculateApiKey`). Centralizing it in `genkit.model` avoids every plugin re-inventing key resolution for multi-tenancy. The lower-level extraction function (`extract_request_api_key`) stays in `genkit.blocks.model` but is not re-exported to the public API — only the google-genai plugin needs it for the `apiKey: false` ADC edge case.
- **`compute_usage_stats(input, response)`** — renamed from `get_basic_usage_stats`. Counts characters, images, videos, and audio in input/output messages. "Compute" reflects that it does work (not a lookup), and "basic" was dropped (basic compared to what?).
- **`text_from_content`** — removed from public API. Consumers should use the veneer layer instead:
  - **Messages:** `MessageWrapper.text` (available on `response.messages[i].text`)
  - **Responses:** `GenerateResponse.text` (the veneer's `.text` property)
  - **Stream chunks:** `GenerateResponseChunkWrapper.text`
  - **Documents:** `Document.text()` (already exists on the `Document` class)
  - Current consumers: google-genai reranker (should use `Document.text()`), internal middleware (should use `doc.text()`), tests (should use chunk/response veneers).

### `genkit.retriever`

```python
from genkit.retriever import (
    # Wire-format types
    RetrieverRequest,
    RetrieverResponse,

    # Registration and metadata
    retriever_action_metadata,
    create_retriever_ref,
    RetrieverOptions,

    # Indexer support
    IndexerRequest,
    IndexerOptions,
    indexer_action_metadata,
    create_indexer_ref,
)
```

Used by: retriever/indexer plugin authors, app developers using `RetrieverResponse` as a type annotation.

### `genkit.embedder`

```python
from genkit.embedder import (
    # Wire-format types
    EmbedRequest,
    EmbedResponse,
    Embedding,

    # Registration and metadata
    embedder_action_metadata,
    create_embedder_ref,
    EmbedderOptions,
    EmbedderSupports,
)
```

### `genkit.reranker`

```python
from genkit.reranker import (
    reranker_action_metadata,
    create_reranker_ref,
    RankedDocument,
    RerankerRequest,
    RerankerResponse,
    RankedDocumentData,
    RankedDocumentMetadata,
)
```

### `genkit.evaluator`

```python
from genkit.evaluator import (
    # Wire-format types
    EvalRequest,
    EvalResponse,
    EvalFnResponse,
    Score,
    Details,
    BaseEvalDataPoint,
    EvalStatusEnum,

    # Registration and metadata
    evaluator_action_metadata,
    evaluator_ref,
)
```

Used by: evaluator plugin authors and app developers writing custom evaluators (samples show both).

### `genkit.web`

Web framework integration (FastAPI, Flask, custom ASGI apps).

```python
from genkit.web import (
    FlowWrapper,
    ContextProvider,
    RequestData,
    create_flows_asgi_app,
)
```

Used by: fastapi plugin, flask plugin, app developers serving flows over HTTP.

### `genkit.telemetry`

```python
from genkit.telemetry import (
    add_custom_exporter,
    is_dev_environment,
    GENKIT_VERSION,
    GENKIT_CLIENT_HEADER,
    tracer,
)
```

Used by: telemetry plugins (observability, Google Cloud, Firebase, Amazon Bedrock, Cloudflare, Microsoft Foundry).

`AdjustingTraceExporter` and `RedactedSpan` should live in the telemetry *plugin* (e.g., `genkit-google-cloud`), not in core. Both are implementation details of specific telemetry providers — JS and Go also keep these in their cloud plugins, not core.

### Shared across domains (plugin authoring)

These symbols are used by plugin authors across multiple domains. They live in the top-level `from genkit import ...` alongside the app-developer symbols:

```python
from genkit import (
    # (app-developer symbols from Entry point 1 above, plus:)

    # Plugin authoring
    Plugin,             # base class for all plugin types
    Action,             # core action type
    ActionMetadata,     # action registration metadata
    ActionKind,         # action type enum (model, retriever, embedder, etc.)
    StatusName,         # error status codes
    DocumentPart,       # part type within Documents (vs. message Parts)
    to_json_schema,     # converts Pydantic models to JSON Schema
)
```

This brings the total top-level surface to **~29 symbols** (22 app-developer + 7 plugin-authoring). All are stable, documented types — no implementation details.

---

## Internal — resolved decisions

Helpers that were candidates for export. Each has a final verdict.

| Symbol | Consumers | Verdict | Reasoning |
|---|---|---|---|
| `get_logger` | 15+ plugins, 10+ samples | **Drop.** | Structlog wrapper. Neither JS nor Go force a logging library. Use stdlib `logging`. |
| `get_cached_client` | 9 plugins | **Internal (reconsider later).** | Per-event-loop httpx client cache. Solves a real async problem (~100 lines to reimplement). No JS/Go equivalent. Keep internal but may export if third-party plugins need it. |
| `dump_dict` / `dump_json` | 15+ consumers | **Remove.** Fix at source. | Wrappers for `model_dump(exclude_none=True, by_alias=True)`. Fix: emit `GenkitBaseModel` from the code generator that defaults these flags. Then `.model_dump()` just works. See [pydantic/pydantic#10141](https://github.com/pydantic/pydantic/issues/10141). |
| `get_callable_json` | fastapi, flask, core | **Remove.** Add method instead. | Converts exceptions to JSON for HTTP responses. Fix: add `.to_json()` and `.http_status` to `GenkitError` (matches Go's `.ToReflectionError()`). |
| `matches_uri_template` | MCP plugin only | **Internal.** | 15-line regex helper. MCP plugin should own its copy. |

- **`create_reflection_asgi_app`, `RuntimeManager`, `ServerSpec`, `Registry`** — dev-mode reflection server infrastructure. Used by fastapi plugin, multi-server sample, and core `_base_async.py`.

  **The problem:** Genkit needs a dev-mode reflection server (HTTP API on a separate port) so the Genkit Dev UI can introspect the running app. In JS and Go, this is fully automatic — the `Genkit` constructor (JS) or `Init()` (Go) starts the reflection server internally because JS has an ambient event loop and Go has goroutines. The user never touches it.

  Python can't copy this because:
  1. **No event loop at construction time.** `Genkit()` is called synchronously at module level. There's no running `asyncio` event loop yet — you can't start an async HTTP server from a synchronous constructor.
  2. **ASGI server ownership.** In the FastAPI/Flask use case, uvicorn owns the process and the event loop. Genkit is a library inside someone else's ASGI app — it can't spin up a second server on its own.

  When Genkit owns the process (`ai.run_main(coro)`), the reflection server starts automatically (same as JS/Go). The problem is only the "Genkit as a library" path (FastAPI/Flask), where the plugin currently needs four internal imports to wire up the reflection server manually.

  **Fix: add `await ai.start_dev_server()` method on `Genkit`.** One async method that encapsulates all the wiring (creates reflection app from its own registry, binds a port, starts uvicorn, registers with RuntimeManager). The fastapi plugin's lifespan becomes trivial:

  ```python
  cleanup = await ai.start_dev_server()
  yield
  await cleanup()
  ```

  This eliminates `create_reflection_asgi_app`, `RuntimeManager`, `ServerSpec`, and `Registry` from external consumption. All four stay internal. The multi-server sample also uses `ai.start_dev_server()` instead of manually wiring internals.

### `GenerateResponse` naming: veneer vs. schema type

`GenerateResponse` appears in two places:

- **`from genkit import GenerateResponse`** — the **veneer** with `.text`, `.output`, `.tool_requests` (aliased from `GenerateResponseWrapper`). This is what app developers use.
- **`from genkit.model import GenerateResponse`** — the **schema type** (auto-generated wire format). This is what model handlers receive and return.

These are different classes in different modules. No shadowing occurs because a file imports from one or the other, never both. The veneer extends the schema type (inheritance), so they're compatible.

### Cross-language comparison

- **JS** — `import { genkit } from 'genkit'` for common types, `import { ... } from 'genkit/model'` / `'genkit/retriever'` / etc. for domain-specific types.
- **Go** — `import "github.com/firebase/genkit/go/genkit"` for the framework, `import "github.com/firebase/genkit/go/ai"` for all domain types (single package).
- **Python (proposed)** — `from genkit import Genkit, Part, Message` for common types, `from genkit.model import ...` / `from genkit.retriever import ...` / etc. for domain-specific types.

Python follows the JS pattern — common types in the top-level import, domain-specific types in sub-modules organized by action type.

---

## Internal modules

Everything under `genkit._core`, `genkit._blocks`, and `genkit._ai` (note underscore prefix) carries no stability guarantee. Today these modules lack the underscore (`genkit.core`, `genkit.blocks`, `genkit.ai`), which is why samples and the documentation agent used internal paths. Renaming them is part of this proposal — the underscore is Python's convention for "private, use at your own risk."

The domain sub-modules (`genkit.model`, `genkit.retriever`, etc.) are **re-export facades** — they import from the internal modules and re-export a curated public surface. The actual implementation stays in `genkit._blocks` and `genkit._core`. This decouples the public API from internal code organization, so internal refactors don't break users.

---

## Changes from status quo

What plugins and samples currently do that needs to change. This is the migration work.

### Removed from public API

- **`text_from_content`** — standalone function for extracting text from `list[Part]`. Consumers should use veneers instead: `GenerateResponse.text`, `MessageWrapper.text`, `GenerateResponseChunkWrapper.text`, or `Document.text()`. Affected: google-genai reranker, internal middleware, tests.
- **`tool_response`** — only 3 sample usages. JS/Go use a method on the tool instance.
- **`get_logger`** — thin wrapper around `logging.getLogger("genkit")`. Consumers should use stdlib `logging` directly. Affected: 15+ plugins, 10+ samples (trivial change).
- **`GenkitRegistry`** — internal implementation type. Should not be imported by plugins.
- **`SimpleRetrieverOptions`** — internal implementation type.

### Moved to plugins (out of core)

- **`AdjustingTraceExporter`** — base class for trace exporters that adjust spans before export. Currently in `genkit.core.trace.adjusting_exporter`. Should move to the telemetry plugin (e.g., `genkit-google-cloud`). JS and Go both keep this in their cloud plugins, not core.
- **`RedactedSpan`** — span wrapper that redacts `genkit:input`/`genkit:output` attributes. Same file as `AdjustingTraceExporter`. Should move with it. No equivalent in JS/Go core.

### Reorganized (new public paths)

- **`genkit.types` → `genkit`** — all app developer types unified into `from genkit import ...`. No separate `genkit.types` import.
- **`genkit.plugin` → domain sub-modules** — plugin types split by action type: `genkit.model`, `genkit.retriever`, `genkit.embedder`, `genkit.reranker`, `genkit.evaluator`, `genkit.telemetry`. 
- **`Plugin` class** — moved from top-level `genkit` to shared across domains (imported by plugin authors, not app developers).
- **`FlowWrapper`** — moved from internal to a web sub-module export.
- **`ContextProvider`, `RequestData`** — moved from internal to a web sub-module export.
- **`create_flows_asgi_app`** — moved from internal to a web sub-module export.

### Renamed

- **`GenerateResponseWrapper` → `GenerateResponse`** (at the `genkit` top-level) — alias removes the "Wrapper" suffix leak.
- **`genkit.core` → `genkit._core`**, **`genkit.blocks` → `genkit._blocks`**, **`genkit.ai` → `genkit._ai`** — underscore prefix signals internal. This is what breaks all the existing direct imports from plugins/samples.

### Now explicitly internal (plugins must stop importing)

These are things plugins/samples currently import from internal paths. After the rename to `_core`/`_blocks`/`_ai`, these imports break. The public replacements are listed.

- `from genkit.blocks.model import ...` → `from genkit.model import ...`
- `from genkit.blocks.retriever import ...` → `from genkit.retriever import ...`
- `from genkit.blocks.reranker import ...` → `from genkit.reranker import ...`
- `from genkit.blocks.document import Document` → `from genkit import Document`
- `from genkit.core.typing import ...` → `from genkit import ...` (for content types) or `from genkit.model import ...` (for wire-format types)
- `from genkit.core.action import Action, ActionRunContext` → `from genkit import ActionRunContext` or `from genkit.model import Action`
- `from genkit.core.error import GenkitError` → `from genkit import GenkitError`
- `from genkit.core.logging import get_logger` → `import logging; logger = logging.getLogger("genkit")`
- `from genkit.core.http_client import get_cached_client` → stays internal (no public replacement yet; reconsider for export)
- `from genkit.codec import dump_dict, dump_json` → stays internal (no public replacement)
- `from genkit.core.registry import Registry` → stays internal (code smell; use `Genkit` instance)
- `from genkit.core.reflection import create_reflection_asgi_app` → stays internal
- `from genkit.ai._runtime import RuntimeManager` → stays internal
- `from genkit.ai._server import ServerSpec` → stays internal
- `from genkit.blocks.resource import matches_uri_template` → stays internal (MCP plugin should own this)

---

## Appendix

### Type architecture

Two layers of types:

**Schema types (auto-generated).** Auto-generated from `genkit-schemas.json` (shared cross-language schema). Plain Pydantic `BaseModel` classes — data containers with no convenience methods. These are the contract between the framework and plugins. A model plugin receives a `GenerateRequest` and returns a `GenerateResponse`. Content-building types (`Message`, `Part`, `TextPart`, etc.) are also schema types — app developers construct them directly.

**Veneers (hand-written wrappers).** Extend schema types with convenience methods (`.text`, `.output`, `.tool_requests`). `GenerateResponseWrapper` extends `GenerateResponse` via inheritance — aliasing it as `GenerateResponse` publicly is safe. `MessageWrapper` wraps `Message` via composition — its constructor takes a `Message` instance, so aliasing as `Message` would break `Message(role="user", content=[...])`. Users interact with `MessageWrapper` through `response.messages` but never construct it.
