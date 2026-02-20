# Genkit Python — Public API Surface Proposal

What's importable, what's not, and where the boundary is.

Two audiences, separate entry points:

1. **Simple Path** — `from genkit import ...`
2. **Advanced Usage** — domain sub-modules (`genkit.model`, `genkit.retriever`, etc.)

---

## 1. Proposed imports

### `from genkit import ...` — app developers

```python
from genkit import (
    # Core
    Genkit,
    ActionRunContext,
    GenerateResponse,       # veneer (aliased from GenerateResponseWrapper)
    GenerateResponseChunk,  # veneer (aliased from GenerateResponseChunkWrapper)
    StreamResponse,         # renamed from GenerateStreamResponse
    ExecutablePrompt,  
    GenkitError,
    UserFacingError,

    # Content types
    Part, TextPart, MediaPart, Media,
    DataPart, ToolRequestPart, ToolResponsePart, CustomPart,
    ReasoningPart,

    # Messages
    Message, Role,

    # Documents
    Document, DocumentData, DocumentPart,

    # Tool context
    ToolRunContext,
    ToolInterruptError,
    ToolChoice,

    # Generation config
    GenerationCommonConfig,

    # Evaluation
    BaseEvalDataPoint,

    # Web framework integration
    RequestData,
    ContextProvider,

    # Constants
    GENKIT_VERSION,
    GENKIT_CLIENT_HEADER,
    is_dev_environment,

    # Plugin authoring (also used by advanced app devs)
    Plugin,
    Action,
    ActionMetadata,
    ActionKind,
    StatusCodes,
)
```

**~34 symbols.** One import covers both app developers (~25) and plugin authors
(~9 additional). Normal for Python — OpenAI and Anthropic export more.

Notes:
- `GenerateResponse` / `GenerateResponseChunk` — aliases that hide the "Wrapper" suffix.
  Both use inheritance, so `isinstance` checks work.
- `Message` is the schema type, not `MessageWrapper`. `MessageWrapper` uses composition
  so aliasing it would break `Message(role="user", content=[...])`. Users get
  `MessageWrapper` via `response.messages` but never construct it.
- `ExecutablePrompt` — exported so users can type-annotate: `my_prompt: ExecutablePrompt = ai.prompt("greeting")`.

### `genkit.model` — model plugin authors

```python
from genkit.model import (
    GenerateRequest,
    GenerateResponse,        # schema type (NOT the veneer)
    GenerateResponseChunk,
    GenerationUsage,
    Candidate,
    OutputConfig,
    FinishReason,
    GenerateActionOptions,
    Error,
    Operation,
    ToolRequest,
    ToolDefinition,
    ToolResponse,
    ModelInfo,
    Supports,
    Constrained,
    Stage,
    model_action_metadata,
    model_ref,
    ModelReference,
    BackgroundAction,
    lookup_background_action,
    compute_usage_stats,
    resolve_api_key,
    GenerationCommonConfig,
    ModelMiddleware,
    ModelMiddlewareNext,
)
```

`GenerateResponse` naming: `from genkit import GenerateResponse` = veneer.
`from genkit.model import GenerateResponse` = schema type. No shadowing — a file
imports from one or the other. Veneer extends schema via inheritance.

### `genkit.retriever`

```python
from genkit.retriever import (
    RetrieverRequest,
    RetrieverResponse,
    retriever_action_metadata,
    retriever_ref,
    IndexerRequest,
    indexer_action_metadata,
    indexer_ref,
)
```

### `genkit.embedder`

```python
from genkit.embedder import (
    EmbedRequest,
    EmbedResponse,
    Embedding,
    embedder_action_metadata,
    embedder_ref,
    EmbedderSupports,
)
```

### `genkit.reranker`

```python
from genkit.reranker import (
    reranker_action_metadata,
    reranker_ref,
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
    EvalRequest,
    EvalResponse,
    EvalFnResponse,
    Score,
    Details,
    BaseEvalDataPoint,
    EvalStatusEnum,
    evaluator_action_metadata,
    evaluator_ref,
)
```

### `genkit.tracing` — telemetry plugin authors

```python
from genkit.tracing import tracer, add_custom_exporter
```

## 2. What we removed from imports (and why)

### Removed from `from genkit import ...`

| Symbol | Why |
|---|---|
| `Input` / `Output` | Type deleted. Replaced by `output_schema` kwarg. Neither JS nor Go needed this. |
| `GenkitRegistry` | Internal implementation type. Plugins use the `Genkit` instance. |
| `FlowWrapper` | Internal. Not needed by app developers. |
| `SimpleRetrieverOptions` | Type deleted. Flatten to kwargs on `define_simple_retriever()`. |
| `PromptGenerateOptions` | Type deleted. 17-field TypedDict that killed IDE autocomplete. |
| `OutputOptions` | Type deleted. Dies with `PromptGenerateOptions`. |
| `ResumeOptions` | No longer top-level. Passed as `resume=` kwarg on prompt methods. |
| `tool_response` | Only 3 sample usages. JS/Go use a method on the tool instance. |
| `GENKIT_CLIENT_HEADER` / `GENKIT_VERSION` | Previously deep internal import (`genkit.core.constants`). Now in top-level `from genkit import ...`. |

### Removed from domain sub-modules

| Symbol | Module | Why |
|---|---|---|
| `RetrieverOptions` | `genkit.retriever` | Type deleted. Flatten to kwargs on `define_retriever()`. |
| `IndexerOptions` | `genkit.retriever` | Type deleted. Flatten to kwargs on `define_indexer()`. |
| `EmbedderOptions` | `genkit.embedder` | Type deleted. Flatten to kwargs on `define_embedder()`. |
| `RerankerOptions` | `genkit.reranker` | Type deleted. Flatten to kwargs on `define_reranker()`. |

### Removed helpers (no longer importable)

| Helper | Why |
|---|---|
| `get_logger` | Structlog wrapper. Use stdlib `logging`. Neither JS nor Go force a logging library. |
| `text_from_content` | Use veneers instead: `response.text`, `message.text`, `doc.text`. |
| `dump_dict` / `dump_json` | Fix at source — `GenkitBaseModel` defaults handle this. See [sdk_design §9](./python_beta_sdk_design.md). |
| `get_callable_json` | Dies with `core/flows.py`. |
| `create_flows_asgi_app` | Cloud Functions pattern — doesn't fit Python where FastAPI/Flask own routing. |

### Internalized (no longer importable)

| Symbol | Why |
|---|---|
| `to_json_schema` | `define_*` accepts types directly — no plugin needs manual conversion. Moves to `core/_internal/_schema.py`. See [sdk_design §10](./python_beta_sdk_design.md). |
| `extract_json` | Zero plugin consumers. Only used internally by `formats/`. Moves to `core/_internal/_extract.py`. |

JS exports both (`genkit/schema`, `genkit/extract`) but no JS plugin imports them either.

### Moved to plugins (out of core SDK)

| Symbol | Destination | Why |
|---|---|---|
| `AdjustingTraceExporter` | telemetry plugin | JS equivalent is in `js/plugins/google-cloud/`, not core. |
| `RealtimeSpanProcessor` | telemetry plugin | Telemetry implementation detail. |
| `RedactedSpan` | telemetry plugin | Only used by `AdjustingTraceExporter`. |

---

## 3. What we added to imports (and why)

### Added to `from genkit import ...`

| Symbol | Why |
|---|---|
| `StreamResponse` | Renamed from `GenerateStreamResponse`. Return type of all streaming APIs. Previously not importable — `generate_stream()` returned a raw tuple. |
| `GenerateResponseChunk` | Veneer alias. Previously not exported from top level. |
| `ToolInterruptError` | User-facing error type for tool interrupts. Previously only importable from internal path. |
| `ToolChoice` | Tool selection control for `generate()`. Previously internal. |
| `StatusCodes` | Error status codes for plugin authors. Previously only in `genkit.core`. |
| `ReasoningPart` | Content type for chain-of-thought. New model capability. |
| `DataPart` / `CustomPart` | Content types that were missing from top-level exports. |

### Added to `genkit.model`

| Symbol | Why |
|---|---|
| `compute_usage_stats` | Renamed from `get_basic_usage_stats`. Centralized — avoids each plugin re-inventing token counting. |
| `resolve_api_key` | Resolves per-request API key vs plugin default. Previously duplicated across plugins. |

---

## 4. Internal design decisions

The following design changes affect the public API indirectly. Full details
(rationale, import DAG, migration plans, open questions) are in
[python_beta_sdk_design.md](./python_beta_sdk_design.md).

**Serialization cleanup (`GenkitBaseModel`)** — Internal base class that
defaults `model_dump()` to `exclude_none=True, by_alias=True`. Eliminates
`dump_dict`/`dump_json` wrappers and fixes 11 inconsistent serialization calls.
See [sdk_design §9](./python_beta_sdk_design.md).

**`define_*` accepts raw Python types** — `define_model`, `define_retriever`,
etc. accept `type | dict | None` directly instead of requiring pre-converted
JSON Schema dicts. `to_json_schema` and `extract_json` move to
`core/_internal/`. See [sdk_design §10](./python_beta_sdk_design.md).

**`ErrorResponse` consolidation** — Replaces 3 error wire format types with a
single internal Pydantic model. See [sdk_design §11](./python_beta_sdk_design.md).

---
