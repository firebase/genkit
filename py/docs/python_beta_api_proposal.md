# Genkit Python — Public API Surface Proposal

This doc defines the public API of the Genkit Python SDK: the set of symbols developers can import, that we commit to keeping stable, and that we document and support. Everything else is internal and can change without notice.

There are two audiences for this SDK:

1. **App developers** — people building AI features with Genkit. They need `Genkit`, decorators, data types, and not much else.
2. **Plugin authors** — people building model providers, vector stores, telemetry exporters, web framework integrations. They need the action system, schema types, and metadata builders.

These audiences have separate entry points.

---

## Methodology

Every import across 30+ samples, 20+ plugins, and the test suite was audited to understand what symbols people actually use. The symbol lists and usage counts below come from that audit. The documentation audit ([DOCUMENTATION_AUDIT.md](./DOCUMENTATION_AUDIT.md)) independently confirmed the import path confusion — the verification agent used internal paths because no public boundary existed.

---

## Type architecture

Before presenting the symbol lists, it helps to understand why there are multiple types for seemingly the same thing. The SDK has three layers of types, each serving a different purpose.

### Layer 1: Schema types (auto-generated)

These are auto-generated from `genkit-schemas.json`, the shared cross-language schema. They're plain Pydantic `BaseModel` classes — data containers with no convenience methods.

```python
# genkit/core/typing.py (auto-generated)
class GenerateResponse(BaseModel):
    candidates: list[Candidate] | None = None
    usage: GenerationUsage | None = None
    request: GenerateRequest | None = None
    ...

class Message(BaseModel):
    role: Role
    content: list[Part]
    metadata: dict[str, Any] | None = None

class Part(RootModel):
    root: TextPart | MediaPart | DataPart | ToolRequestPart | ToolResponsePart | ...

class OutputConfig(BaseModel):
    format: str | None = None
    schema_: dict[str, Any] | None = None
    instructions: str | bool | None = None
    constrained: bool | None = None
```

These are the internal contract between the framework and plugins. A model plugin receives a `GenerateRequest` and returns a `GenerateResponse`. They split into two audiences:

| Audience | Types | Examples |
|----------|-------|---------|
| **Plugin authors** (contract types) | Request/response schemas, config types | `GenerateRequest`, `GenerateResponse`, `OutputConfig`, `ModelInfo` |
| **App developers** (content types) | Things users construct and pass around | `Message`, `Part`, `TextPart`, `Media`, `Document`, `Role` |

Today they all live in `genkit.types` (or `genkit.core.typing` internally), mixed together.

### Layer 2: Veneers (hand-written wrappers)

These extend schema types with convenience methods — `.text`, `.output`, `.tool_requests`. They're what app developers interact with when receiving responses.

```python
# genkit/blocks/model.py (hand-written)
class GenerateResponseWrapper(GenerateResponse):
    @property
    def text(self) -> str: ...
    @property
    def output(self) -> Any: ...
    @property
    def tool_requests(self) -> list[ToolRequestPart]: ...
    @property
    def messages(self) -> list[MessageWrapper]: ...

class MessageWrapper:  # wraps Message, doesn't extend it
    def __init__(self, message: Message): ...
    @property
    def text(self) -> str: ...
    @property
    def tool_requests(self) -> list[ToolRequestPart]: ...
```

Key distinction:
- `GenerateResponseWrapper` **extends** `GenerateResponse` (inheritance). Aliasing it as `GenerateResponse` publicly is safe — construction is compatible.
- `MessageWrapper` **wraps** `Message` (composition). Its constructor takes a `Message` instance, not raw fields. Aliasing it as `Message` would break `Message(role="user", content=[...])`.

Veneers are for app developers receiving responses. Plugin authors constructing responses use the schema types directly.

### Layer 3: Config helpers (hand-written)

Type-carrying wrappers for configuration:

```python
# genkit/blocks/interfaces.py (hand-written)
class Input(Generic[T]):
    """Carries type info for input validation."""
    def __init__(self, schema: type[T]): ...

class Output(Generic[T]):
    """Carries type info for output parsing."""
    def __init__(self, schema: type[T], format: str = "json", ...): ...
```

`Input[T]` and `Output[T]` exist so that `generate()` and `prompt()` can carry generic type information — `ai.generate(output=Output(MyModel))` returns `GenerateResponse[MyModel]` with typed `.output`.

### Where the layers bleed

1. **App developers construct schema types directly.** `Message(role="user", content=[Part(text="hello")])` is a schema type, not a veneer. Content-building types are schema types used by both audiences.

2. **Schema and config types overlap.** `OutputConfig` (schema, Layer 1) and `Output[T]` (config helper, Layer 3) configure the same thing. `generate()` accepts both: `output: OutputConfig | OutputConfigDict | Output[Any] | None`. (This is addressed in [PYTHON_API_REVIEW.md, section 5](./PYTHON_API_REVIEW.md).)

3. **Veneers exported under internal names.** `GenerateResponseWrapper` — the "Wrapper" suffix is an implementation detail that leaked into the public API.

4. **`genkit.types` mixes audiences.** Plugin contract types and app developer types sit in the same module.

The proposal below addresses all four of these problems.

---

## Entry point 1: `from genkit import ...`

The framework entry point for app developers. Veneers, context, and errors. Data types live in `genkit.types` (see below) — this follows the Go SDK pattern where types are a separate package, and matches what Python samples already do in practice.

```python
from genkit import (
    Genkit,
    ActionRunContext,
    GenerateResponse,     # veneer — aliased from GenerateResponseWrapper
    GenkitError,
    UserFacingError,
)
```

**5 symbols.** Tight, intentional, hard to get wrong.

| Symbol | Why it's here |
|--------|--------------|
| `Genkit` | The entry point. Every app starts with this. (48 files) |
| `ActionRunContext` | Context object inside flows and tools. (20 files) |
| `GenerateResponse` | Return type of `ai.generate()` — veneer with `.text`, `.output`, `.tool_requests`. |
| `GenkitError` | Base error class for catching framework errors. |
| `UserFacingError` | Errors safe to surface to HTTP clients. |

### Veneer aliasing

Users should never see "Wrapper" suffixes. The fix:

```python
# genkit/__init__.py
from genkit.blocks.model import GenerateResponseWrapper as GenerateResponse
from genkit.blocks.model import GenerateResponseChunkWrapper as GenerateResponseChunk
```

`GenerateResponseWrapper` uses inheritance, so this alias is safe. `GenerateResponseChunkWrapper` follows the same pattern.

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

| Symbol | Reason |
|--------|--------|
| `tool_response` | Only 3 sample usages. JS/Go use a method on the tool instance. |
| `Plugin` | Users pass plugin instances (`GoogleAI()`), never reference the type. Moved to `genkit.plugin`. |
| `get_logger` | Thin wrapper around `logging.getLogger("genkit")`. Use the stdlib. |
| `GenkitRegistry`, `FlowWrapper`, `SimpleRetrieverOptions` | Internal implementation types. |

### `ToolRunContext` placement

`ToolRunContext` extends `ActionRunContext` with tool-specific features. Both types are kept (for documentation clarity, future-proofing, and runtime `isinstance` checks), but only `ActionRunContext` is exported from the top level. `ToolRunContext` is available from `genkit.types` for type annotations when needed.

---

## Entry point 2: `from genkit.types import ...`

Content types that app developers construct and pass around — the schema types (Layer 1) that users interact with directly.

```python
from genkit.types import (
    # Content
    Part, TextPart, MediaPart, Media,
    DataPart, ToolRequestPart, ToolResponsePart, CustomPart,

    # Messages
    Message, Role,

    # Documents
    Document, DocumentData,

    # Context
    ToolRunContext,

    # Evaluation
    BaseEvalDataPoint,

    # Tool control
    ToolChoice,

    # Generation config
    GenerationCommonConfig,
)
```

This module is focused: things app developers construct and pass to Genkit methods. Plugin contract types (`GenerateRequest`, `OutputConfig`, `ModelInfo`) have been moved to `genkit.plugin` — they don't belong in the app developer's import path.

### No re-exports at the top level

`from genkit import Part, Message` does **not** work. Content types live in `genkit.types` only. This keeps the top-level surface tight and makes it unambiguous where types come from. Samples already use `from genkit.types import ...` — this formalizes the existing pattern.

---

## Entry point 3: `from genkit.plugin import ...`

Everything a plugin author needs to implement a model provider, retriever, embedder, evaluator, or web framework integration.

```python
from genkit.plugin import (
    # Base class
    Plugin,

    # Action system
    Action, ActionRunContext,

    # Schema types (wire format — what plugins receive and return)
    GenerateRequest, GenerateResponse, GenerateResponseChunk,
    Message, OutputConfig, ModelInfo, Supports,

    # Request/response types for other action types
    RetrieverRequest, RetrieverResponse,
    EmbedRequest, EmbedResponse,

    # Metadata builders
    model_metadata, retriever_metadata, embedder_metadata,

    # Telemetry
    TelemetryConfig,
)
```

Note: `GenerateResponse` here is the **schema type** (auto-generated, no convenience methods). In `from genkit import GenerateResponse`, it's the **veneer** (with `.text`, `.output`, etc.). Different classes, different modules, different audiences. This coexistence works without shadowing because the two types never appear in the same import path.

### Cross-language comparison

| Language | App developer imports | Plugin author imports |
|----------|----------------------|---------------------|
| **JS** | `import { genkit, z } from 'genkit'` (unified) | Same package |
| **Go** | `import "github.com/firebase/genkit/go/ai"` (types separate) | Same package, different types |
| **Python (proposed)** | `from genkit import Genkit` + `from genkit.types import Part, Message` | `from genkit.plugin import GenerateRequest, Plugin` |

Python follows the Go pattern — types are a separate import. This matches what samples already do in practice.

---

## Internal modules

Everything under `genkit._core`, `genkit._blocks`, and `genkit._ai` (note underscore prefix) carries no stability guarantee. Today these modules lack the underscore (`genkit.core`, `genkit.blocks`, `genkit.ai`), which is why samples and the documentation agent used internal paths. Renaming them is part of this proposal — the underscore is Python's convention for "private, use at your own risk."

---

## Open design question: `Input[T]` / `Output[T]`

This is the one genuinely open question in the public API surface. It's covered in depth as a design decision in [PYTHON_API_REVIEW.md, section 5](./PYTHON_API_REVIEW.md).

Summary: `Output[T]` carries generic type information for typed responses (`ai.generate(output=Output(MyModel))` → `GenerateResponse[MyModel]`). The alternative is inline kwargs (`output_schema=MyModel`), which loses the generic typing. A tech lead challenged the naming — "Input of what? Output of what?" — arguing the names are too generic.

Three options: inline only, wrapper only, or keep both. Recommendation is wrapper only (consolidate to one `output=` param), with the name open for discussion.
