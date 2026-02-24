# Genkit Python — Beta API Design Review

This doc covers the full public API surface being locked at beta: what's importable,
how the client is constructed, the high-traffic method signatures, and the return types
users interact with. Section 5 lists open design questions requiring explicit sign-off.

---

## 1. Import Surface

Every symbol exported at beta. This is exhaustive by design — the list itself is what's
being approved.

### `from genkit import ...` — app developers

```python
from genkit import (
    # Core
    Genkit,
    ActionRunContext,
    GenerateResponse,         # veneer alias of GenerateResponseWrapper
    GenerateResponseChunk,    # veneer alias of GenerateResponseChunkWrapper
    ActionStreamResponse,     # base streaming wrapper — Action.stream()
    FlowStreamResponse,       # flow streaming wrapper — FlowWrapper.stream()
    GenerateStreamResponse,   # generate/prompt streaming wrapper — subclass of FlowStreamResponse
    ExecutablePrompt,
    GenkitError,
    PublicError,         # renamed from UserFacingError — matches Go's NewPublicError

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
    is_dev_environment,

)
```

### `genkit.model`

```python
from genkit.model import (
    GenerateRequest,
    GenerateResponse,        # schema type (NOT the veneer — see §5)
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

### `genkit.retriever`

```python
from genkit.retriever import (
    RetrieverRef,
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
    EmbedderRef,
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

### `genkit.plugin` — all plugin authors

```python
from genkit.plugin import (
    # Base class and framework primitives
    Plugin,
    Action,
    ActionMetadata,
    ActionKind,
    StatusCodes,

    # HTTP / version stamping (for setting x-goog-api-client and user-agent headers)
    GENKIT_CLIENT_HEADER,
    GENKIT_VERSION,

    # Convenience re-exports from domain modules
    # (identical to importing from genkit.model, genkit.retriever, etc.)
    model_action_metadata, model_ref, ModelReference,
    embedder_action_metadata, embedder_ref,
    retriever_action_metadata, retriever_ref,
    indexer_action_metadata, indexer_ref,
    reranker_action_metadata, reranker_ref,
    evaluator_action_metadata, evaluator_ref,
)
```

Note: The domain sub-modules (`genkit.model`, `genkit.retriever`, etc.) are still the canonical
paths for domain-specific types. `genkit.plugin` re-exports the cross-cutting framework primitives
and provides a single entry point for plugin authors who don't want to hunt across multiple paths.

---

## 2. Client Construction

```python
ai = Genkit(
    plugins: list[Plugin] | None = None,
    model: str | None = None,
    prompt_dir: str | Path | None = None,
)
```

- `plugins` — list of initialized plugin instances
- `model` — default model name used when `model=` is omitted from `generate()`
- `prompt_dir` — directory to load `.prompt` files from; defaults to `./prompts` if it exists

---

## 3. Method Signatures

High-traffic paths only — not exhaustive.

### `Genkit`

```python
from typing import Any, overload
C = TypeVar('C', bound=GenerationCommonConfig)
InputT = TypeVar('InputT')
OutputT = TypeVar('OutputT')
# Key invariant: TypeVars are bound ONLY when the caller passes a concrete type[T] argument.
# When a parameter typed type[T] has no default, the overload only matches when explicitly
# provided — that absence-of-default is the mechanism that triggers TypeVar binding.
# Catch-all overloads use dict[str, object] | None = None and return Any-parameterized types.

# generate() has 4 overloads — the (model type) × (output_schema type) cross-product:
#   [1] ModelReference[C] + type[OutputT]  →  GenerateResponse[OutputT]   ← C and OutputT both bound
#   [2] ModelReference[C] + dict/None      →  GenerateResponse[Any]
#   [3] str/None          + type[OutputT]  →  GenerateResponse[OutputT]   ← OutputT bound, C erased
#   [4] str/None          + dict/None      →  GenerateResponse[Any]       ← catch-all
#
# Typed overloads (1, 3): output_schema has NO default — absence of a default is what forces
# the type checker to bind OutputT only when the caller explicitly passes a concrete type.
# Catch-all overloads (2, 4): output_schema: dict[str, object] | None = None covers
# raw JSON Schema dicts, None, and the omitted-entirely case.

# [1] ModelReference[C] + typed schema — both C and OutputT bound:
@overload
async def generate(
    self,
    *,
    model: ModelReference[C],
    config: C | None = None,
    prompt: str | Part | list[Part] | None = None,
    system: str | Part | list[Part] | None = None,
    messages: list[Message] | None = None,
    tools: list[str | Action | ExecutablePrompt] | None = None,
    return_tool_requests: bool | None = None,
    tool_choice: ToolChoice | None = None,
    tool_responses: list[Part] | None = None,
    max_turns: int | None = None,
    context: dict[str, object] | None = None,
    output_schema: type[OutputT],           # no default — binds OutputT
    output_format: str | None = None,
    output_content_type: str | None = None,
    output_instructions: bool | str | None = None,
    output_constrained: bool | None = None,
    use: list[ModelMiddleware] | None = None,
    docs: list[Document] | None = None,
) -> GenerateResponse[OutputT]: ...

# [2] ModelReference[C] + untyped schema:
@overload
async def generate(
    self,
    *,
    model: ModelReference[C],
    config: C | None = None,
    prompt: str | Part | list[Part] | None = None,
    system: str | Part | list[Part] | None = None,
    messages: list[Message] | None = None,
    tools: list[str | Action | ExecutablePrompt] | None = None,
    return_tool_requests: bool | None = None,
    tool_choice: ToolChoice | None = None,
    tool_responses: list[Part] | None = None,
    max_turns: int | None = None,
    context: dict[str, object] | None = None,
    output_schema: dict[str, object] | None = None,
    output_format: str | None = None,
    output_content_type: str | None = None,
    output_instructions: bool | str | None = None,
    output_constrained: bool | None = None,
    use: list[ModelMiddleware] | None = None,
    docs: list[Document] | None = None,
) -> GenerateResponse[Any]: ...

# [3] str model + typed schema — OutputT bound, config falls back to GenerationCommonConfig:
@overload
async def generate(
    self,
    *,
    model: str | None = None,
    config: GenerationCommonConfig | None = None,
    prompt: str | Part | list[Part] | None = None,
    system: str | Part | list[Part] | None = None,
    messages: list[Message] | None = None,
    tools: list[str | Action | ExecutablePrompt] | None = None,
    return_tool_requests: bool | None = None,
    tool_choice: ToolChoice | None = None,
    tool_responses: list[Part] | None = None,
    max_turns: int | None = None,
    context: dict[str, object] | None = None,
    output_schema: type[OutputT],           # no default — binds OutputT
    output_format: str | None = None,
    output_content_type: str | None = None,
    output_instructions: bool | str | None = None,
    output_constrained: bool | None = None,
    use: list[ModelMiddleware] | None = None,
    docs: list[Document] | None = None,
) -> GenerateResponse[OutputT]: ...

# [4] str model + untyped schema — catch-all (dict, None, or omitted):
@overload
async def generate(
    self,
    *,
    model: str | None = None,
    config: GenerationCommonConfig | None = None,
    prompt: str | Part | list[Part] | None = None,
    system: str | Part | list[Part] | None = None,
    messages: list[Message] | None = None,
    tools: list[str | Action | ExecutablePrompt] | None = None,
    return_tool_requests: bool | None = None,
    tool_choice: ToolChoice | None = None,
    tool_responses: list[Part] | None = None,
    max_turns: int | None = None,
    context: dict[str, object] | None = None,
    output_schema: dict[str, object] | None = None,
    output_format: str | None = None,
    output_content_type: str | None = None,
    output_instructions: bool | str | None = None,
    output_constrained: bool | None = None,
    use: list[ModelMiddleware] | None = None,
    docs: list[Document] | None = None,
) -> GenerateResponse[Any]: ...

# generate_stream() has the same 4-overload structure, returning GenerateStreamResponse[T]:

# [1] ModelReference[C] + typed schema:
@overload
def generate_stream(
    self,
    *,
    model: ModelReference[C],
    config: C | None = None,
    prompt: str | Part | list[Part] | None = None,
    system: str | Part | list[Part] | None = None,
    messages: list[Message] | None = None,
    tools: list[str | Action | ExecutablePrompt] | None = None,
    return_tool_requests: bool | None = None,
    tool_choice: ToolChoice | None = None,
    tool_responses: list[Part] | None = None,
    max_turns: int | None = None,
    context: dict[str, object] | None = None,
    output_schema: type[OutputT],           # no default — binds OutputT
    output_format: str | None = None,
    output_content_type: str | None = None,
    output_instructions: bool | str | None = None,
    output_constrained: bool | None = None,
    use: list[ModelMiddleware] | None = None,
    docs: list[Document] | None = None,
    timeout: float | None = None,
) -> GenerateStreamResponse[OutputT]: ...

# [2] ModelReference[C] + untyped schema:
@overload
def generate_stream(
    self,
    *,
    model: ModelReference[C],
    config: C | None = None,
    prompt: str | Part | list[Part] | None = None,
    system: str | Part | list[Part] | None = None,
    messages: list[Message] | None = None,
    tools: list[str | Action | ExecutablePrompt] | None = None,
    return_tool_requests: bool | None = None,
    tool_choice: ToolChoice | None = None,
    tool_responses: list[Part] | None = None,
    max_turns: int | None = None,
    context: dict[str, object] | None = None,
    output_schema: dict[str, object] | None = None,
    output_format: str | None = None,
    output_content_type: str | None = None,
    output_instructions: bool | str | None = None,
    output_constrained: bool | None = None,
    use: list[ModelMiddleware] | None = None,
    docs: list[Document] | None = None,
    timeout: float | None = None,
) -> GenerateStreamResponse[Any]: ...

# [3] str model + typed schema:
@overload
def generate_stream(
    self,
    *,
    model: str | None = None,
    config: GenerationCommonConfig | None = None,
    prompt: str | Part | list[Part] | None = None,
    system: str | Part | list[Part] | None = None,
    messages: list[Message] | None = None,
    tools: list[str | Action | ExecutablePrompt] | None = None,
    return_tool_requests: bool | None = None,
    tool_choice: ToolChoice | None = None,
    tool_responses: list[Part] | None = None,
    max_turns: int | None = None,
    context: dict[str, object] | None = None,
    output_schema: type[OutputT],           # no default — binds OutputT
    output_format: str | None = None,
    output_content_type: str | None = None,
    output_instructions: bool | str | None = None,
    output_constrained: bool | None = None,
    use: list[ModelMiddleware] | None = None,
    docs: list[Document] | None = None,
    timeout: float | None = None,
) -> GenerateStreamResponse[OutputT]: ...

# [4] str model + untyped schema — catch-all:
@overload
def generate_stream(
    self,
    *,
    model: str | None = None,
    config: GenerationCommonConfig | None = None,
    prompt: str | Part | list[Part] | None = None,
    system: str | Part | list[Part] | None = None,
    messages: list[Message] | None = None,
    tools: list[str | Action | ExecutablePrompt] | None = None,
    return_tool_requests: bool | None = None,
    tool_choice: ToolChoice | None = None,
    tool_responses: list[Part] | None = None,
    max_turns: int | None = None,
    context: dict[str, object] | None = None,
    output_schema: dict[str, object] | None = None,
    output_format: str | None = None,
    output_content_type: str | None = None,
    output_instructions: bool | str | None = None,
    output_constrained: bool | None = None,
    use: list[ModelMiddleware] | None = None,
    docs: list[Document] | None = None,
    timeout: float | None = None,
) -> GenerateStreamResponse[Any]: ...

# Retrieval
async def retrieve(
    self,
    retriever: str | RetrieverRef,
    query: str | Document,
    *,
    options: dict[str, object] | None = None,  # plugin-defined schema; shape varies per retriever
) -> list[Document]: ...  # JS parity: wire DocumentData converted to Document veneers

# Embedding
async def embed(
    self,
    embedder: str | EmbedderRef,
    content: str | Document,
    *,
    options: dict[str, object] | None = None,  # plugin-defined schema; shape varies per embedder
) -> list[Embedding]: ...

# Prompt lookup — 4 overloads (InputT × OutputT cross-product):
# [1] Both bound:
@overload
def prompt(
    self,
    name: str,
    variant: str | None = None,
    *,
    input_schema: type[InputT],             # no default — binds InputT
    output_schema: type[OutputT],           # no default — binds OutputT
) -> ExecutablePrompt[InputT, OutputT]: ...

# [2] InputT bound, OutputT untyped — typed input, unstructured output:
@overload
def prompt(
    self,
    name: str,
    variant: str | None = None,
    *,
    input_schema: type[InputT],             # no default — binds InputT
    output_schema: dict[str, object] | None = None,
) -> ExecutablePrompt[InputT, Any]: ...

# [3] OutputT bound, InputT untyped — unstructured input, typed output:
@overload
def prompt(
    self,
    name: str,
    variant: str | None = None,
    *,
    input_schema: dict[str, object] | None = None,
    output_schema: type[OutputT],           # no default — binds OutputT
) -> ExecutablePrompt[Any, OutputT]: ...

# [4] Catch-all — neither bound (dict, None, or omitted):
@overload
def prompt(
    self,
    name: str,
    variant: str | None = None,
    *,
    input_schema: dict[str, object] | None = None,
    output_schema: dict[str, object] | None = None,
) -> ExecutablePrompt[Any, Any]: ...

# Decorators
@ai.flow(name: str | None = None)
async def my_flow(input: InputT) -> OutputT: ...
# Returns: FlowWrapper

@ai.tool(name: str | None = None, description: str | None = None)
def my_tool(input: InputT, ctx: ToolRunContext | None = None) -> OutputT: ...
```

### `ExecutablePrompt` — returned by `ai.prompt()` / `@ai.define_prompt`

```python
# Call like a function
await prompt(input: InputT | None = None) -> GenerateResponse[OutputT]

# Stream
def stream(
    self,
    input: InputT | None = None,
    *,
    timeout: float | None = None,
) -> GenerateStreamResponse[OutputT]

# Render without executing
async def render(
    self,
    input: InputT | dict[str, Any] | None = None,
) -> GenerateActionOptions
```

### `FlowWrapper` — returned by `@ai.flow`

```python
# Call like a function — same signature as the wrapped flow
flow(*args, **kwargs) -> Awaitable[OutputT]

# Stream
def stream(
    self,
    input: InputT | None = None,
    *,
    context: dict[str, object] | None = None,
    telemetry_labels: dict[str, object] | None = None,
    timeout: float | None = None,
) -> FlowStreamResponse[ChunkT, OutputT]
```

### Plugin authoring surface

```python
def define_model(
    self,
    name: str,
    fn: ModelFn,
    *,
    config_schema: type[BaseModel] | dict[str, object] | None = None,
    label: str | None = None,
    supports: Supports | None = None,
    versions: list[str] | None = None,
    stage: Stage | None = None,
) -> Action: ...

def define_embedder(
    self,
    name: str,
    fn: EmbedderFn,
    *,
    config_schema: type[BaseModel] | dict[str, object] | None = None,
    label: str | None = None,
    supports: EmbedderSupports | None = None,
    dimensions: int | None = None,
) -> Action: ...

def define_retriever(
    self,
    name: str,
    fn: RetrieverFn,
    *,
    config_schema: type[BaseModel] | dict[str, object] | None = None,
    label: str | None = None,
    supports: RetrieverSupports | None = None,
) -> Action: ...

# InputT binds through input_schema — all Callables and the return type are typed accordingly
InputT = TypeVar('InputT')

# define_prompt() — 4 overloads (InputT × OutputT cross-product):

# [1] Both bound — typed input, typed output:
@overload
def define_prompt(
    self,
    name: str | None = None,
    *,
    variant: str | None = None,
    model: str | None = None,
    config: GenerationCommonConfig | None = None,
    description: str | None = None,
    input_schema: type[InputT],             # no default — binds InputT
    system: str | Part | list[Part] | Callable[[InputT, dict | None], str | Part | list[Part]] | None = None,
    prompt: str | Part | list[Part] | Callable[[InputT, dict | None], str | Part | list[Part]] | None = None,
    messages: str | list[Message] | Callable[[InputT, dict | None], list[Message]] | None = None,
    docs: list[Document] | Callable[[InputT, dict | None], list[Document]] | None = None,
    output_schema: type[OutputT],           # no default — binds OutputT
    output_format: str | None = None,
    output_content_type: str | None = None,
    output_instructions: bool | str | None = None,
    output_constrained: bool | None = None,
    tools: list[str | Action | ExecutablePrompt] | None = None,
    tool_choice: ToolChoice | None = None,
    return_tool_requests: bool | None = None,
    max_turns: int | None = None,
    use: list[ModelMiddleware] | None = None,
) -> ExecutablePrompt[InputT, OutputT]: ...

# [2] InputT bound, OutputT untyped — typed input, unstructured output:
@overload
def define_prompt(
    self,
    name: str | None = None,
    *,
    variant: str | None = None,
    model: str | None = None,
    config: GenerationCommonConfig | None = None,
    description: str | None = None,
    input_schema: type[InputT],             # no default — binds InputT
    system: str | Part | list[Part] | Callable[[InputT, dict | None], str | Part | list[Part]] | None = None,
    prompt: str | Part | list[Part] | Callable[[InputT, dict | None], str | Part | list[Part]] | None = None,
    messages: str | list[Message] | Callable[[InputT, dict | None], list[Message]] | None = None,
    docs: list[Document] | Callable[[InputT, dict | None], list[Document]] | None = None,
    output_schema: dict[str, object] | None = None,
    output_format: str | None = None,
    output_content_type: str | None = None,
    output_instructions: bool | str | None = None,
    output_constrained: bool | None = None,
    tools: list[str | Action | ExecutablePrompt] | None = None,
    tool_choice: ToolChoice | None = None,
    return_tool_requests: bool | None = None,
    max_turns: int | None = None,
    use: list[ModelMiddleware] | None = None,
) -> ExecutablePrompt[InputT, Any]: ...

# [3] OutputT bound, InputT untyped — unstructured input, typed output:
@overload
def define_prompt(
    self,
    name: str | None = None,
    *,
    variant: str | None = None,
    model: str | None = None,
    config: GenerationCommonConfig | None = None,
    description: str | None = None,
    input_schema: dict[str, object] | None = None,
    system: str | Part | list[Part] | Callable[..., str | Part | list[Part]] | None = None,
    prompt: str | Part | list[Part] | Callable[..., str | Part | list[Part]] | None = None,
    messages: str | list[Message] | Callable[..., list[Message]] | None = None,
    docs: list[Document] | Callable[..., list[Document]] | None = None,
    output_schema: type[OutputT],           # no default — binds OutputT
    output_format: str | None = None,
    output_content_type: str | None = None,
    output_instructions: bool | str | None = None,
    output_constrained: bool | None = None,
    tools: list[str | Action | ExecutablePrompt] | None = None,
    tool_choice: ToolChoice | None = None,
    return_tool_requests: bool | None = None,
    max_turns: int | None = None,
    use: list[ModelMiddleware] | None = None,
) -> ExecutablePrompt[Any, OutputT]: ...

# [4] Catch-all — neither bound (dict, None, or omitted):
@overload
def define_prompt(
    self,
    name: str | None = None,
    *,
    variant: str | None = None,
    model: str | None = None,
    config: GenerationCommonConfig | None = None,
    description: str | None = None,
    input_schema: dict[str, object] | None = None,
    system: str | Part | list[Part] | Callable[..., str | Part | list[Part]] | None = None,
    prompt: str | Part | list[Part] | Callable[..., str | Part | list[Part]] | None = None,
    messages: str | list[Message] | Callable[..., list[Message]] | None = None,
    docs: list[Document] | Callable[..., list[Document]] | None = None,
    output_schema: dict[str, object] | None = None,
    output_format: str | None = None,
    output_content_type: str | None = None,
    output_instructions: bool | str | None = None,
    output_constrained: bool | None = None,
    tools: list[str | Action | ExecutablePrompt] | None = None,
    tool_choice: ToolChoice | None = None,
    return_tool_requests: bool | None = None,
    max_turns: int | None = None,
    use: list[ModelMiddleware] | None = None,
) -> ExecutablePrompt[Any, Any]: ...

# Action — returned by define_model, define_tool, etc.
# Calling streams and returns the base wrapper; FlowWrapper/generate_stream build on top
action.stream(
    input: InputT | None = None,
    *,
    context: dict[str, object] | None = None,
    telemetry_labels: dict[str, object] | None = None,
    timeout: float | None = None,
) -> ActionStreamResponse[ChunkT, OutputT]

# ActionRunContext[ChunkT] — producer interface inside action/flow/tool functions
# Go: StreamCallback[Stream] param (nil = not streaming)
# JS: ActionFnArg<S> / FlowSideChannel<S> — two types; Python unifies into one
ctx.is_streaming              # bool — whether caller requested a stream
ctx.send_chunk(chunk: ChunkT) # type-safe push; no-op if not streaming
ctx.context                   # dict[str, object] — request context

# ToolRunContext(ActionRunContext[object]) — ChunkT is object, not GenerateResponseChunk
# Tools don't own their chunk schema — they borrow the parent generate's callback
# JS ToolAction hardcodes streaming type as z.ZodTypeAny for the same reason
```

---

## 4. Return Type Surfaces

What users get back from calls and interact with.

### `GenerateResponse` — from `generate()`, `await prompt(input)`

```python
response.text          # str — full text of the response
response.output        # OutputT — typed output if output schema was provided
response.message       # MessageWrapper — the final message
response.messages      # list[MessageWrapper] — full conversation history
response.tool_requests # list[ToolRequestPart] — pending tool calls
```

### `MessageWrapper` — accessed via `response.message` / `response.messages`

```python
message.text           # str — text content of the message
message.tool_requests  # list[ToolRequestPart]
message.interrupts     # list[ToolRequestPart] — tool calls requiring user input
```

Note: `MessageWrapper` is not exported for construction. Users construct `Message(role=..., content=[...])` and receive `MessageWrapper` back. See §5.

### `GenerateResponseChunk` — stream chunks from `generate_stream()`

```python
chunk.text             # str — text in this chunk
chunk.output           # object — partial typed output
chunk.accumulated_text # str — all text so far
```

### Streaming wrappers — see [`streaming.md`](streaming.md)

Three wrapper types, one hierarchy (`ActionStreamResponse` → `FlowStreamResponse` → `GenerateStreamResponse`). All expose the same two properties:

```python
result.stream    # AsyncIterable[ChunkT]
result.response  # Awaitable[OutputT]
```

| Type | Returned by | ChunkT | OutputT |
|---|---|---|---|
| `ActionStreamResponse[C, O]` | `action.stream()` | action-defined | action-defined |
| `FlowStreamResponse[C, O]` | `flow.stream()` | flow-defined | flow-defined |
| `GenerateStreamResponse[O]` | `generate_stream()`, `prompt.stream()` | `GenerateResponseChunk` (fixed) | `GenerateResponse[O]` |

### `RetrieverResponse` — from `retrieve()`

```python
response.documents     # list[Document]
```

---

## 5. Design Flags

Open questions requiring explicit sign-off.

### Sync vs async API surface

All `Genkit` methods are `async def`. Users must `await` every call or run inside a flow.
`run_main(coro)` exists as a helper for scripts. There is no sync API.

Options:
1. **Async-only** (current) — clean, but friction for scripts and simple use cases
2. **Sync wrappers** — `ai.generate()` blocks, `ai.generate_stream()` stays async
3. **Two classes** — `Genkit` (async) and `SyncGenkit` (sync), à la `httpx`

Changing this post-beta requires a new class or a deprecation cycle.


### Naming: `GenerateResponse` — veneer vs schema type

`from genkit import GenerateResponse` gives the veneer (wrapper with `.text`, `.output`, etc.).
`from genkit.model import GenerateResponse` gives the raw Pydantic schema type.

Same name, different type, different import path. A file that imports from both gets a collision.
Plugin authors import from `genkit.model`; app developers from `genkit`. In practice no single
file should need both — but it's an implicit contract that could surprise users.

### `config` typing: `GenerationCommonConfig | dict[str, object]`

`generate()`, `generate_stream()`, and `define_prompt()` currently accept:

```python
config: GenerationCommonConfig | dict[str, object] | None = None
```

`config` passes model-specific generation parameters — both common fields (`temperature`, `top_k`)
and provider-specific ones (`safety_settings` for Gemini, `frequency_penalty` for OpenAI).
`GenerationCommonConfig` only covers the common fields; `| dict` is an escape hatch for the rest.
Cost: no IDE autocomplete on model-specific fields, silent typos.

**How JS solves it:** `ModelArgument<CustomOptions>` is generic — when you pass a typed
`ModelAction<GeminiOptions>` or `ModelReference<GeminiOptions>`, TypeScript infers
`config: GeminiOptions` at compile time. String models fall back to untyped (same limitation as
Python today). Go doesn't solve this at all — `ModelRef.config` is typed as `any`.

**Proposed fix: make `ModelReference` generic, add overloads.**

`ModelReference` already exists in Python but its `config` field is `dict[str, object]` — not
generic. The fix:

```python
C = TypeVar('C', bound=GenerationCommonConfig)

# 1. Make ModelReference generic (plugin authors export typed refs):
class ModelReference(BaseModel, Generic[C]):
    name: str
    config: C | None = None
    ...

# Plugin exports:
gemini_flash: ModelReference[GeminiConfig] = ModelReference(name="googleai/gemini-2.0-flash")

# 2. generate() gains two overloads:
@overload
async def generate(self, *, model: ModelReference[C], config: C | None = None, ...) -> GenerateResponse: ...
@overload
async def generate(self, *, model: str | None = None, config: GenerationCommonConfig | None = None, ...) -> GenerateResponse: ...
```

**Result:**
```python
# Typed path — IDE enforces config type, flags wrong plugin config:
await ai.generate(model=gemini_flash, config=GeminiConfig(temperature=0.7, safety_settings=[...]))  # ✅
await ai.generate(model=gemini_flash, config=OpenAIConfig(...))  # ❌ type error

# String path — unchanged, falls back to GenerationCommonConfig:
await ai.generate(model="googleai/gemini-2.0-flash", config=GenerationCommonConfig(temperature=0.7))
```

This achieves full JS parity on the typed path. `ModelReference` already exists — needs to be
made generic and exported from `genkit`. Plugin authors export typed `ModelReference[C]` objects.
`| dict` is dropped entirely.

**Decision needed:** Ship this for beta, or ship `GenerationCommonConfig | None` (subclass
approach, no cross-model safety) and do the generic `ModelReference[C]` post-beta?

### Naming: `Message` vs `MessageWrapper`

Users construct messages with `Message`:
```python
messages=[Message(role="user", content=[...])]
```

But `response.message` returns a `MessageWrapper` — a subclass that adds `.text`, `.tool_requests`,
`.interrupts`. `MessageWrapper` is not exported, so users can't type-annotate it directly.

Options:
1. **Current** — `Message` for construction, `MessageWrapper` silently returned
2. Export `MessageWrapper` under a better name (e.g. `ResponseMessage`)
3. Add `.text` / `.tool_requests` to `Message` directly, eliminate the subclass

---

---

## Appendix: Pre-review action items

Already decided — not for discussion. Listed for completeness.

- Rename `UserFacingError` → `PublicError` (matches Go's `NewPublicError`; intent is "safe to return in HTTP response")
- Remove `reflection_server_spec` from `Genkit.__init__` — server starts automatically via `GENKIT_ENV=dev`, port is auto-selected; expose port override as env var `GENKIT_REFLECTION_PORT` if needed (PR #4812 does the right thing but left the param in)
- Make `ai.registry` private (`ai._registry`); remove direct access from all samples
- Fix `part.root.text` / `part.root.media` ergonomics — Pydantic `RootModel` internals should not surface to users
- Flatten `ExecutablePrompt` `opts: PromptGenerateOptions` TypedDict → flat kwargs (consistent with `generate()`)
- Remove `on_chunk` callback from `generate()` — use `generate_stream()` instead
- Change `generate_stream()` return type from `tuple[AsyncIterator, Future]` to `GenerateStreamResponse` — unifies with `prompt.stream()` which already returns `GenerateStreamResponse`
- Introduce streaming type hierarchy (see `streaming.md`): `ActionStreamResponse[ChunkT, OutputT]` as base, `FlowStreamResponse[ChunkT, OutputT]` subclasses it, `GenerateStreamResponse[OutputT]` subclasses `FlowStreamResponse` with `ChunkT` pinned to `GenerateResponseChunk`
- Fix `Action.stream()` to return `ActionStreamResponse[ChunkT, OutputT]` instead of raw tuple
- Make `ActionRunContext` generic: `ActionRunContext[ChunkT]` so `send_chunk(chunk: ChunkT)` is type-safe — matches Go's `StreamCallback[Stream]` and JS's `ActionFnArg<S>`; currently `send_chunk(chunk: object)` accepts anything. `ToolRunContext` does NOT pin to `GenerateResponseChunk` — JS's `ToolAction` hardcodes the streaming type as `z.ZodTypeAny` (explicitly untyped) because tools borrow the parent generate's callback and don't own their chunk schema; `class ToolRunContext(ActionRunContext[object])` is the correct equivalent
- Fix `FlowWrapper.stream()` to return `FlowStreamResponse[ChunkT, OutputT]` instead of raw tuple; fix `input: object` → `input: InputT`
- Fix `Channel` internals: (1) simplify to `Generic[T]` — the `R` close-result type parameter is unnecessary coupling; (2) fix `_pop()` falsy check `if not r` → `if r is None` — current code incorrectly stops iteration on any falsy chunk value (empty string, `0`, `False`)
- Tighten `Callable[..., Any]` on `define_prompt()` resolver params — current code uses `Callable[..., Any]` everywhere; correct parametrized forms are `Callable[[InputT, dict | None], str | Part | list[Part]]` for `system`/`prompt`, `Callable[[InputT, dict | None], list[Message]]` for `messages`, `Callable[[InputT, dict | None], list[Document]]` for `docs`
- `ai.retrieve()` should return `list[Document]` not `RetrieverResponse` — JS converts wire `DocumentData` to `Document` veneers before returning (`response.documents.map(d => new Document(d))`); Python currently leaks the raw wire type, breaking the retrieve → generate pipeline ergonomics
