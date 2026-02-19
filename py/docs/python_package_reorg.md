# Python SDK — Package Reorganization

Proposal to align the Python SDK's internal package structure with Go and JS,
enforce public/internal boundaries, and split oversized files.

Related docs:
- [python_beta_type_design.md](./python_beta_type_design.md) — type audit
- [python_type_audit_checklist.md](./python_type_audit_checklist.md) — checklist
- [python_beta_api_proposal.md](./python_beta_api_proposal.md) — public API surface
- [GENKIT_CLASS_DESIGN.md](../GENKIT_CLASS_DESIGN.md) — Genkit class

---

## Current state

```
genkit/                          7 sub-packages, 73 .py files
├── ai/                          god object + helpers (5 files, 4,500 lines)
├── aio/                         async utilities (4 files)
├── blocks/                      domain types (14 files, 7,800 lines)
│   └── formats/                 output format impls
├── core/                        framework internals (15 files, 5,500 lines)
│   ├── action/                  Action class, context, types
│   └── trace/                   OTel exporters/processors
├── lang/                        deprecation helpers (1 file)
├── types/                       barrel re-export
├── web/                         ASGI server management (8 files)
│   └── manager/
├── __init__.py                  public API barrel
├── codec.py                     JSON serialization helpers
├── model_types.py               GenerationCommonConfig + api_key helpers
└── testing.py                   test doubles
```

### Problems

1. **`blocks/` doesn't exist in Go or JS.** Both put domain types in `ai/`.
   Python's extra layer creates the question "does this go in `ai/` or `blocks/`?"

2. **Orphan packages.** `aio/` (4 files), `lang/` (1 file), `types/` (barrel).
   None earn their existence as top-level packages.

3. **Giant files.** `blocks/prompt.py` (2,446 lines), `ai/_registry.py` (1,680),
   `ai/_aio.py` (1,164). JS/Go equivalents are 600–900 lines.

4. **No boundary enforcement.** Plugins import from `genkit.core.action._action`,
   `genkit.blocks.model`, `genkit.ai._runtime` — deep internal paths. No `__all__`
   on most `__init__.py` files.

5. **Loose root files.** `codec.py` and `model_types.py` are orphans that belong
   in `core/` and `ai/` respectively.

---

## Proposed structure

```
genkit/
├── __init__.py              public API barrel (__all__ defined)
├── ai/                      AI domain types + Genkit class
│   ├── __init__.py          public exports (__all__ defined)
│   ├── prompt.py            ExecutablePrompt + define_prompt (like Go ai/prompt.go)
│   ├── streaming.py         GenerateStreamResponse
│   ├── model.py             GenerateResponseWrapper, ChunkWrapper, MessageWrapper,
│   │                        ModelReference, GenerationCommonConfig, define_model,
│   │                        resolve_api_key, compute_usage_stats
│   ├── document.py          Document, RankedDocument
│   ├── retriever.py         RetrieverRef, RetrieverOptions, define_retriever, etc.
│   ├── embedding.py         Embedder, EmbedderRef, EmbedderOptions, define_embedder
│   ├── reranker.py          RerankerRef, RerankerOptions, define_reranker
│   ├── evaluator.py         EvaluatorRef, define_evaluator
│   ├── tools.py             ToolRunContext, ToolInterruptError, define_tool
│   ├── resource.py          resource actions, define_resource
│   ├── formats/             output format system
│   │   ├── types.py         FormatDef, Formatter, FormatterConfig
│   │   ├── json.py, text.py, jsonl.py, enum.py, array.py
│   ├── _internal/
│   │   ├── _genkit.py       Genkit class body (from ai/_aio.py)
│   │   ├── _genkit_base.py  Genkit __init__, server startup (from ai/_base_async.py)
│   │   ├── _prompt_render.py  dotprompt rendering + PromptCache (split from blocks/prompt.py)
│   │   ├── _generate.py     generate() orchestration, tool loop (from blocks/generate.py)
│   │   ├── _middleware.py    model middleware execution
│   │   └── _messages.py     message construction helpers
│
├── core/                    framework primitives (not AI-specific)
│   ├── __init__.py          public exports (__all__ defined)
│   ├── action.py            Action, ActionRunContext, ActionMetadata (flattened)
│   ├── action_types.py      ActionKind, ActionResponse, ActionMetadataKey
│   ├── error.py             GenkitError, UserFacingError
│   ├── plugin.py            Plugin ABC
│   ├── flow.py              FlowWrapper (generic streaming wrapper)
│   ├── background.py        BackgroundAction (start/check/cancel pattern)
│   ├── dap.py               DynamicActionProvider, DapConfig
│   ├── status_types.py      StatusCodes, Status
│   ├── typing.py            auto-generated schema types (DO NOT EDIT header)
│   ├── _internal/
│   │   ├── _registry.py     Registry class
│   │   ├── _server.py       ServerSpec (reflection API config — moved from ai/)
│   │   ├── _runtime.py      RuntimeManager (.genkit/runtimes/ files — moved from ai/)
│   │   ├── _flows.py        flow registration helpers
│   │   ├── _context.py      RequestData, ContextMetadata
│   │   ├── _tracing.py      tracing setup, span creation
│   │   ├── _trace/          OTel exporters and processors
│   │   │   ├── _default_exporter.py
│   │   │   ├── _adjusting_exporter.py
│   │   │   ├── _realtime_processor.py
│   │   │   └── _types.py    GenkitSpan
│   │   ├── _schema.py       schema utilities, to_json_schema
│   │   ├── _extract.py      JSON extraction from text
│   │   ├── _codec.py        dump_dict, dump_json (from root codec.py)
│   │   ├── _http_client.py  HTTP client helpers
│   │   ├── _environment.py  EnvVar, GenkitEnvironment
│   │   ├── _aio.py          Channel, loop utils (from aio/)
│   │   ├── _logging.py      get_logger
│   │   ├── _constants.py
│   │   └── _deprecations.py (from lang/)
│
├── _web/                    dev server only (all internal)
│   ├── reflection.py        Dev UI reflection API (moved from core/)
│   └── _runtime.py          RuntimeManager — writes .genkit/runtimes/ files
│
│   DELETED: web/manager/ (~1,500 lines, 7 types)
│   ServerManager, ASGIServerAdapter, UvicornAdapter, GranianAdapter,
│   SignalHandler, ServerLifecycle, ServerConfig, AbstractBaseServer,
│   ports.py, info.py — all unused by framework/plugins. Only consumer
│   was one sample (web-multi-server). The reflection server uses raw
│   uvicorn directly (~15 lines in _base_async.py). No abstraction needed.
│
└── testing.py               ProgrammableModel, EchoModel, StaticResponseModel
```

### What changed

| Change | Details |
|---|---|
| **Delete `blocks/`** | All files move into `ai/`. Domain types live where Go/JS put them. |
| **Delete `aio/`** | `Channel` + loop utils → `core/_internal/_aio.py` |
| **Delete `lang/`** | `deprecations.py` → `core/_internal/_deprecations.py` |
| **Delete `types/`** | Barrel re-export removed. `genkit/__init__.py` handles this. |
| **Delete `web/manager/`** | ~1,500 lines of unused multi-server orchestration. Reflection server uses raw uvicorn (~15 lines). |
| **Delete `core/flows.py`** | `create_flows_asgi_app()` — auto-exposes flows as HTTP endpoints. Firebase Cloud Functions pattern that doesn't fit Python (Cloud Functions uses Flask, not ASGI; no `onCallGenkit` for Python). Users should use FastAPI/Flask instead. JS has this (`startFlowServer`) because the Express ecosystem aligns; Python's doesn't. ~370 lines. |
| **Rename `web/` → `_web/`** | Prefix signals "internal, don't import". Now just reflection + runtime. |
| **Move `core/reflection.py` → `_web/`** | It's a Starlette ASGI app, not a core primitive. Breaks `core/` → `web/` cycle. |
| **Move `codec.py`** | → `core/_internal/_codec.py` |
| **Delete `model_types.py`** | `GenerationCommonConfig` → `ai/model.py`. API key helpers renamed to `resolve_api_key` and exposed from `model.py`. `get_basic_usage_stats` renamed to `compute_usage_stats`. |
| **Move `FlowWrapper`** | `ai/_registry.py` → `core/flow.py` (matches Go/JS) |
| **Move `BackgroundAction`** | `blocks/background_model.py` → `core/background.py` (matches Go/JS) |
| **Move `DynamicActionProvider`** | `blocks/dap.py` → `core/dap.py` (matches Go/JS) |
| **Split `prompt.py`** | 2,446 → ~600 (prompt.py) + ~200 (streaming.py) + ~800 (_prompt_render.py) + ~400 (_prompt_cache.py) |
| **Dissolve `ai/_registry.py`** | define_* functions move to their domain files (like Go). `define_model` → `ai/model.py`, `define_retriever` → `ai/retriever.py`, etc. Genkit method stubs stay in `ai/_internal/_genkit.py`. `_registry.py` ceases to exist. |
| **Add `_internal/`** | Pydantic v2 pattern: private implementation behind `_internal/` |
| **Add `__all__`** | Every public `__init__.py` declares its exports |

---

## Cross-language alignment

After the reorg, every audited type lands in the same package as Go and JS.

### `core/` — framework primitives (all three SDKs agree)

| Python type | Go equivalent | JS equivalent |
|---|---|---|
| `Action` | `core/api/action.go` Action | `core/src/action.ts` Action |
| `ActionRunContext` | `core/context.go` ActionContext | `core/src/context.ts` ActionContext |
| `ActionMetadata` | `core/api/action.go` ActionDesc | `core/src/action.ts` ActionMetadata |
| `ActionKind` | `core/api/action.go` ActionType | `core/src/registry.ts` ActionType |
| `GenkitError` | `core/error.go` | `core/src/error.ts` |
| `UserFacingError` | `core/error.go` | `core/src/error.ts` |
| `Plugin` | `core/api/plugin.go` | `core/src/plugin.ts` PluginProvider |
| `StatusCodes` | `core/status_types.go` | `core/src/statusTypes.ts` |
| `FlowWrapper` | `core/flow.go` Flow | `core/src/flow.ts` Flow |
| `BackgroundAction` | `core/background_action.go` | `core/src/background-action.ts` |
| `DynamicActionProvider` | `core/api/plugin.go` DynamicPlugin | `core/src/dynamic-action-provider.ts` |
| `Channel` | N/A (Go built-in) | `core/src/async.ts` |
| `Registry` | `core/api/registry.go` (interface) | `core/src/registry.ts` |

### `ai/` — AI domain types (all three SDKs agree)

| Python type | Go equivalent | JS equivalent |
|---|---|---|
| `Genkit` | `genkit/genkit.go` | `genkit/src/genkit.ts` |
| `ExecutablePrompt` | `ai/prompt.go` Prompt | `ai/src/prompt.ts` |
| `GenerateStreamResponse` | N/A (callback-based) | `ai/src/generate.ts` |
| `GenerateResponseWrapper` | `ai/gen.go` ModelResponse | `ai/src/generate/response.ts` |
| `GenerateResponseChunkWrapper` | `ai/gen.go` ModelResponseChunk | `ai/src/generate/chunk.ts` |
| `MessageWrapper` | `ai/gen.go` Message | `ai/src/message.ts` |
| `Document` | `ai/document.go` | `ai/src/document.ts` |
| `RankedDocument` | `ai/gen.go` RankedDocumentData | `ai/src/reranker.ts` |
| `ToolRunContext` | `ai/tools.go` | `ai/src/tool.ts` |
| `ToolInterruptError` | `ai/tools.go` (unexported) | `ai/src/tool.ts` |
| `ModelReference` | `ai/generate.go` ModelRef | `ai/src/model.ts` |
| `EmbedderRef` | `ai/embedder.go` | `ai/src/embedder.ts` EmbedderReference |
| `RetrieverRef` / `IndexerRef` | `ai/retriever.go` | `ai/src/retriever.ts` |
| `RerankerRef` | N/A | `ai/src/reranker.ts` RerankerReference |
| `EvaluatorRef` | `ai/evaluator.go` | `ai/src/evaluator.ts` |
| `Embedder` | `ai/embedder.go` | `ai/src/embedder.ts` |
| `EmbedderOptions` / `Supports` | `ai/embedder.go` | `ai/src/embedder.ts` |
| `RetrieverOptions` / `IndexerOptions` | `ai/retriever.go` | `ai/src/retriever.ts` |
| `RerankerOptions` | N/A | `ai/src/reranker.ts` |
| `FormatDef` / `Formatter` | `ai/formatter.go` | `ai/src/formats/types.ts` |
| `GenerationCommonConfig` | `ai/gen.go` | `ai/src/model-types.ts` |
| `ActionMetadata` | `core/api/action.go` | `core/src/action.ts` |

Mismatches: **zero.** Every type ends up in the same package as Go and JS.

(`Genkit` is a special case — Go/JS have a separate `genkit/` package, Python uses
the top-level `genkit/__init__.py`. Same role, different mechanism.)

---

## Plugin import paths — before and after

### Model plugin (e.g., google-genai gemini.py)

```python
# Before (6 deep imports):
from genkit.ai import ActionRunContext, GENKIT_CLIENT_HEADER
from genkit.blocks.model import get_basic_usage_stats
from genkit.codec import dump_dict, dump_json
from genkit.core.error import GenkitError, StatusName
from genkit.core.tracing import tracer
from genkit.core.typing import GenerationCommonConfig, Message, ...

# After (2 imports):
from genkit.ai import (
    ActionRunContext, GenkitError, GenerationCommonConfig,
    Message, get_basic_usage_stats, dump_dict, dump_json,
)
from genkit.core import tracer, GENKIT_CLIENT_HEADER
```

### Retriever plugin (e.g., vertex-ai vector_search.py)

```python
# Before (5 deep imports):
from genkit.ai import Genkit
from genkit.blocks.document import Document
from genkit.blocks.retriever import RetrieverOptions, retriever_action_metadata
from genkit.core.action.types import ActionKind
from genkit.core.schema import to_json_schema

# After (1 import):
from genkit.ai import (
    Genkit, Document, RetrieverOptions,
    retriever_action_metadata, ActionKind, to_json_schema,
)
```

### Telemetry plugin (e.g., observability)

```python
# Before (3 deep imports):
from genkit.core.environment import is_dev_environment
from genkit.core.trace.adjusting_exporter import AdjustingTraceExporter
from genkit.core.tracing import add_custom_exporter

# After (1 import):
from genkit.core import is_dev_environment, AdjustingTraceExporter, add_custom_exporter
```

---

## Circular import fix: `core/` → `_web/` cycle

**Problem.** Today `core/` has a hidden dependency on `web/`:

- `core/reflection.py` imports `genkit.web.manager` (it **is** a Starlette ASGI app)
- `core/flows.py` imports `genkit.web.manager` (it **is** a Starlette ASGI app)
- `web/` modules import from `genkit.core.*`

This creates a package-level cycle: `core/ ↔ web/`.

**Root cause.** Both `reflection.py` and `flows.py` are 100% HTTP server
code — Starlette routes, ASGI apps, request/response handling. They ended
up in `core/` by accident, not because they provide core primitives.

**Fix.**

- `core/reflection.py` → move to `_web/reflection.py`
- `core/flows.py` → **delete** (see "What changed" table — Firebase pattern
  that doesn't fit Python; users should use FastAPI/Flask)

```
_web/
├── reflection.py    ← was core/reflection.py
└── _runtime.py      ← RuntimeManager
```

### Additional cross-package violations to fix

**`core/plugin.py` → `blocks/` (becomes `core/` → `ai/` after reorg).**
The `Plugin` base class has two convenience methods — `model(name)` and
`embedder(name)` — that do deferred runtime imports of `ModelReference` and
`EmbedderRef` from `blocks/`. After the reorg, `blocks/` merges into `ai/`,
creating a `core/ → ai/` layering violation.

Fix: move `ModelReference` and `EmbedderRef` into `core/` (they're tiny
types — just a `name: str` wrapper). Or remove the helper methods from
`Plugin` and let plugins construct refs directly.

**`ai/_base_async.py` → `web/manager/_ports.py`.**
Imports `find_free_port_sync` — a 15-line stdlib socket utility. After the
reorg, `web/manager/` is deleted.

Fix: move `find_free_port_sync` to `core/_internal/_ports.py`. It's pure
stdlib (`socket.bind`), no dependencies.

### After all fixes

The dependency graph is strictly one-directional:

```
_web/  →  ai/  →  core/
  └────────────────↗
```

`core/` has zero imports from `_web/` or `ai/`. Clean layering.

---

## Boundary enforcement

### 1. `__all__` on every public `__init__.py`

```python
# genkit/__init__.py
__all__ = [
    'Genkit', 'Document', 'GenkitError', 'UserFacingError',
    'GenerateResponse', 'GenerateStreamResponse',
    'ActionRunContext', 'ToolRunContext', 'Plugin',
    # ... ~50 symbols
]

# genkit/ai/__init__.py
__all__ = [
    'Genkit', 'ExecutablePrompt', 'GenerateStreamResponse',
    'Document', 'RankedDocument', 'ToolRunContext',
    # ... AI domain types + plugin helpers
]

# genkit/core/__init__.py
__all__ = [
    'Action', 'ActionRunContext', 'ActionMetadata', 'ActionKind',
    'GenkitError', 'UserFacingError', 'Plugin', 'FlowWrapper',
    # ... framework types + plugin helpers
]
```

### 2. `import-linter` in CI

```ini
# .importlinter
[importlinter]
root_package = genkit

[importlinter:contract:layers]
name = Package layers
type = layers
layers =
    genkit._web
    genkit.ai
    genkit.core

[importlinter:contract:no-internal-from-plugins]
name = Plugins must not import _internal
type = forbidden
source_modules =
    genkit.plugins
forbidden_modules =
    genkit.ai._internal
    genkit.core._internal
```

### 3. `_internal/` convention

Following Pydantic v2's pattern. Everything in `_internal/` can change without
notice between minor versions. The public modules re-export what's needed.

---

## File size targets

| File | Current | Target | How |
|---|---|---|---|
| `blocks/prompt.py` | 2,446 | ~600 | Split into prompt.py + streaming.py + _prompt_render.py + _prompt_cache.py |
| `ai/_registry.py` | 1,680 | **0 (deleted)** | define_* functions move to domain files (model.py, retriever.py, etc.). Genkit method stubs absorbed into _genkit.py. File ceases to exist. |
| `ai/_aio.py` | 1,164 | ~800 | Rename to _genkit.py, extract server startup to _genkit_base.py |
| `blocks/generate.py` | 1,088 | ~600 | Extract tool loop to _generate.py, keep public generate function |
| `core/typing.py` | 1,066 | 1,066 | Auto-generated, don't touch. Add DO NOT EDIT header. |

Target: no hand-written file over 800 lines. Matches Go/JS norms.

---

## Migration path

This is a **one-time refactor** with no logic changes, no API changes, no behavior
changes. The diff is:

1. Move files
2. Update import paths (find-and-replace across plugins)
3. Add `__all__` to `__init__.py` files
4. Split 3 oversized files

### Order of operations

1. **Add `__all__` to existing `__init__.py` files** — zero-risk, clarifies
   public API immediately. Can land as its own PR.

2. **Merge `blocks/` into `ai/`** — the big structural move. Update all
   import paths. One PR.

3. **Move `FlowWrapper`, `BackgroundAction`, `DynamicActionProvider` to `core/`** —
   small cross-language alignment fix. One PR.

4. **Kill orphans** — delete `aio/`, `lang/`, `types/`, move root files.
   One PR.

5. **Create `_internal/` directories** — move implementation files behind
   the boundary. Update internal imports. One PR.

6. **Rename `web/` → `_web/`, move `core/reflection.py` into `_web/`,
   delete `core/flows.py`** — breaks the `core/ ↔ web/` circular
   dependency and removes the unused flows server. One PR.

7. **Split oversized files** — `prompt.py`, `_registry.py`, `generate.py`.
   One PR each.

8. **Add `import-linter` to CI** — one PR, enforces the new structure going
   forward.

Each step is independently shippable and independently revertible.

---

## What we're NOT doing

- **Not changing the public API.** `from genkit import Genkit` still works.
  All public symbols stay accessible from `genkit.__init__`.

- **Not splitting into multiple PyPI packages.** `genkit` stays as one
  installable package. `ai/` and `core/` are internal organization.

- **Not changing runtime behavior.** This is purely a code organization refactor.

- **Not touching `core/typing.py`.** Auto-generated schema types stay as-is.

- **Not touching plugins' public APIs.** Plugins' `__init__.py` exports
  are unchanged. Only their internal imports from `genkit.*` are updated.
