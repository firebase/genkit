# Genkit Python SDK — API Design Review

## 1. Background

The Python SDK launched to match JS and Go feature timelines. It achieved feature parity, but the API surface was never designed independently. Patterns were ported from JS rather than designed natively for Python. 

The Python SDK is public but hasn't cut a stable release. The JS SDK went through a similar cleanup between v0.5 and v1.0, and the migration cost grew with each release. Python is earlier in that curve and changes are still cheap.

In this doc, we're laying out some guiding principles for designing the API so we have more consistency and standardization for adding new framework features going forward.

## 2. Principles

### Pythonic API conventions

The JS SDK uses options objects, camelCase, and callback patterns. "Pythonic" means a set of concrete conventions:

**Zero-to-one positional arguments.** Every public method allows at most one positional arg — the "obvious" one (e.g., `input` for a prompt call). Everything else is keyword-only via the `*` marker. This prevents positional abuse and makes call sites self-documenting:

```python
# Bad: what are these arguments?
ai.generate("gemini", "Hi", None, None, ["search"])

# Good: every argument is named
ai.generate(model="gemini", prompt="Hi", tools=["search"])
```

**Kwargs over options dicts.** JS groups parameters into an options object. Python has first-class keyword arguments. Dict-based configuration loses autocomplete, type checking, and discoverability. This applies to `generate()`, `prompt()`, and every public method.

**Flat imports, intentional boundaries.** Python has no access modifiers — any module is importable, and there's no way to enforce "private." This makes API boundary design a deliberate choice, not a language feature. We define three public entry points (`genkit`, `genkit.types`, `genkit.plugin`) and treat everything else as internal with no stability guarantee. Internal modules should be underscore-prefixed (`genkit._core`, `genkit._blocks`) to signal this — today they lack the underscore, which is why samples accidentally depend on them. The mechanics of this boundary are covered in section 4.

## 3. Initial Audit

While working on updated docs, we identified several friction points in the developer experience. 

For many of these friction points, there was a clear Pythonic standard to follow — keyword-only arguments on all methods, sequence protocol on `RetrieverResponse`, convenience properties like `response.media`, veneer aliasing (`GenerateResponseWrapper` → `GenerateResponse`), and cleanup of internal utilities from the public surface. More details here: [python_beta_sdk_audit.md](./py/docs/python_beta_sdk_audit.md)

The remaining sections in this doc are open questions that need some discussion to resolve.

## 4. Public API surface & type architecture

Today there is no formal public/internal boundary. The documentation audit found samples importing from `genkit.core.action`, `genkit.blocks.model`, and `genkit.ai` — all internal paths that happen to work. This means any internal module rename or refactor is a breaking change for external developers, even if the public API hasn't changed. App developers and plugin authors share a single `genkit.types` module, which means app developers are exposed to plugin contract types they'll never use — and plugin authors have to sift through content types to find the schema types they need. Wrapper classes are exported under internal names like `GenerateResponseWrapper`, so the implementation detail of "this is a wrapper around an auto-generated type" leaks into every type hint and docstring.

We propose formalizing three entry points, separated by audience:

- **`from genkit import ...`** — App developers. 5-6 symbols: `Genkit`, `ActionRunContext`, `GenerateResponse` (veneer), `GenkitError`, `UserFacingError`,  `Prompt`.
- **`from genkit.types import ...`** — App developers (data types). Content types: `Part`, `Message`, `Document`, `Role`, `ToolChoice`, `GenerationCommonConfig`, etc.
- **`from genkit.plugin import ...`** — Plugin authors. Plugin contract: `Plugin`, `GenerateRequest`, `GenerateResponse` (schema), `OutputConfig`, `ModelInfo`, metadata builders, etc.

Internal modules (`genkit.core`, `genkit.blocks`, `genkit.ai`) would be renamed with underscore prefixes (`genkit._core`, `genkit._blocks`) to signal "private, no stability guarantee" — the standard Python convention.

The full proposal — including the type architecture (auto-generated schema types vs hand-written veneers vs config helpers), symbol lists, rationale for each inclusion/exclusion, and the `MessageWrapper` aliasing problem — is in [python_beta_api_proposal.md](./python_beta_api_proposal.md).


^^^ Upon discussion, we got more details on aliasing. App developers may need access to the wire format for unit testing. They are more likely to need that actually vs. the veneer (which I think is handled internally). Also I remember Pavel said something about flow vs. generate. One returns veneer vs. other returns the wire format. He said app developer may need to use one or the other.

^^^ Upon dicsussion, no clear reason to separate from genkit import vs from genkit.types import

^^^ Audit what's exposed via __all__ in all the packages (there are some random helpers for example)

^^^ Consider internal code organization as well, what goes in blocks? core? web? types? Internal code organization is somewhat generic/sprawling/unopinionated 

## 5. Output configuration

The `generate()` method currently accepts output configuration multiple ways:

```python
# Way 1: Inline kwargs
await ai.generate(prompt="...", output_format="json", output_content_type="application/json",
                  output_instructions="Return valid JSON", output_constrained=True)

# Way 2: Config helper with generics
await ai.generate(prompt="...", output=Output(schema=MyModel))
```

**Flat kwargs vs. wrapper object.** We considered both approaches:

A **wrapper object** (`output=OutputConfig(Recipe)` or `output=Recipe`) bundles the schema with secondary options (format, constrained, instructions) into one param, reducing `generate()`'s parameter count. But it introduces a new type developers have to learn and import.

**Flat kwargs** (`output_schema=Recipe`) is the more Pythonic approach. Python functions embrace explicit parameters with defaults — `requests.get()` has 15+ kwargs, `json.dumps()` has 8, `subprocess.run()` has 12. No config objects. The secondary output params (`output_format`, `output_constrained`, `output_content_type`, `output_instructions`) stay as kwargs with sensible defaults — `output_format` auto-defaults to `'json'` when a schema is set, the rest default to `None` and are rarely used. The common case is just:

```python
response = await ai.generate(prompt="...", output_schema=Recipe)
response.output.name  # typed as str — IDE autocomplete works
```

No new types, no imports beyond the Pydantic model, and the 95% case is one kwarg.

**Recommendation.** Flat kwargs. Remove the `output` param. Keep `output_schema`, `output_format`, `output_constrained`, `output_content_type`, and `output_instructions` as individual keyword-only params. Use `@overload` so `output_schema: type[T]` parameterizes the return type. The wire-format `OutputConfig` remains an internal/plugin type — plugin authors use it when implementing model plugins to read output configuration from the `GenerateRequest`, but app developers never see it.

`output_schema` accepts three forms: a Pydantic model class (`type[T]` — the common case, gives typed returns), a raw JSON schema dict (`dict` — for dynamic schemas, returns `Any`), or a registered schema name (`str`, looked up from registry at runtime, returns `Any`). Only the Pydantic class form carries the generic type. 

**The same applies to `input_schema`.** With flat kwargs and overloads, `input_schema: type[T]` carries the generic directly — `Input[T]` can be removed:

```python
prompt = ai.define_prompt(
    name='recipe',
    input_schema=RecipeInput,
    output_schema=Recipe,
    prompt='Make a recipe for {dish}',
)

response = await prompt(RecipeInput(dish='pizza'))
response.output.name  # typed as str — IDE knows this is Recipe
```

Dotprompt should work in a similar way but with one additional nuance. When a schema is defined in a `.prompt` file's YAML frontmatter (`output: { schema: Recipe }`), the SDK uses it to constrain the model's JSON output at runtime. But the type checker doesn't know this — `.prompt` files can't carry Python type references — so `response.output` is `Any`. To get typed output, pass the schema at the call site:

```python
# Without output_schema — runtime parsing works, but typing is Any
recipe = ai.prompt('recipe')
response = await recipe({'food': 'pizza'})
response.output  # Any — no autocomplete

# With output_schema — typed
recipe = ai.prompt('recipe', output_schema=Recipe)
response = await recipe({'food': 'pizza'})
response.output.name  # str — IDE knows this is Recipe
```

This is inherent to Python's static type system. The redundancy (schema in both `.prompt` and Python) is the cost of typed output, and it's a cost every framework with external schema files pays. The flat kwarg `output_schema=Recipe` keeps this as lightweight as possible — no wrapper type needed, just name the class.

## 6. Streaming API

The SDK currently has two streaming patterns:

```python
# generate_stream() — returns a tuple
stream, future = ai.generate_stream(prompt="Tell me a story")
async for chunk in stream:
    print(chunk.text, end="")
response = await future

# prompt.stream() — returns an object with .stream accessor
result = prompt.stream({"topic": "AI"})
async for chunk in result.stream:
    print(chunk.text, end="")
response = await result.response
```

The Python standard for streaming is iterators — OpenAI, Anthropic, and every major Python SDK use them.

Genkit can't use a plain async generator (the OpenAI pattern) because Genkit responses carry more than text — structured output parsing, usage statistics, tool request handling, and the assembled `Message` for multi-turn conversations. A plain generator can't expose a final response object after iteration.

**Proposed streaming syntax:**

```python
# Simple case — looks identical to a plain generator
async for chunk in ai.generate_stream(prompt="Tell me a story"):
    print(chunk.text, end="")

# When you need the final response — assign, iterate, then access
result = ai.generate_stream(prompt="Tell me a story")
async for chunk in result:
    print(chunk.text, end="")
response = await result.response  # structured output, usage stats, tool requests
```

**What changes:**
- `generate_stream()` returns a directly iterable object (implements `__aiter__`) with a `.response` property for the final assembled response
- `prompt.stream()` uses the same pattern — one streaming convention across the SDK
- The tuple return is removed — no more destructuring

## 7. Sync and async support

Every Genkit Python method is `async def`. There is no sync API. This is a Python-specific problem — JS is inherently async, Go handles concurrency transparently with goroutines. Python is the only language where the developer has to explicitly choose.

The practical consequences: a Flask route handler can't call `ai.generate()` without managing an event loop. A Jupyter notebook cell needs `await` or `nest_asyncio` workarounds. A CLI script requires wrapping everything in `async def main()` and `ai.run_main()`. These are the most common entry points for developers trying Genkit for the first time.

For context, every major Python LLM SDK offers both sync and async: OpenAI and Anthropic ship dual clients (`OpenAI` / `AsyncOpenAI`), LangChain has dual methods (`.invoke()` / `.ainvoke()`), Google Cloud AI uses a separate async transport. Even Hugging Face, which is sync-only, made a deliberate choice. Genkit is the only async-only SDK in the ecosystem. A developer coming from OpenAI's `client.chat.completions.create()` — no `await`, no `async def` — hits immediate friction.

**Proposal.** Dual clients — `Genkit` (sync) and `AsyncGenkit` (async). This is the industry standard: OpenAI, Anthropic, and Cohere all ship it. The async client holds the real implementation; the sync client delegates to it. We prefer the dual-client pattern (separate classes) over dual methods (`generate()` / `agenerate()` on the same class) because it keeps each class's type signatures clean — every method on `Genkit` returns `T`, every method on `AsyncGenkit` returns `Awaitable[T]` — and avoids polluting autocomplete with `a`-prefixed duplicates of every method.

```python
from genkit import Genkit, AsyncGenkit

# Sync (scripts, Flask, notebooks)
ai = Genkit(plugins=[GoogleAI()])
response = ai.generate(model="googleai/gemini-2.0-flash", prompt="Hi")

# Async (FastAPI, high-concurrency)
ai = AsyncGenkit(plugins=[GoogleAI()])
response = await ai.generate(model="googleai/gemini-2.0-flash", prompt="Hi")
```

The maintenance cost is manageable: the sync client is auto-generated from the async client's method signatures, as OpenAI and Anthropic do. No duplicate implementation, no diverging logic.

## 8. Method signatures

The current `generate()` signature has 20 parameters:

```python
async def generate(
    self,
    model=None, prompt=None, system=None, messages=None,
    tools=None, return_tool_requests=None, tool_choice=None,
    tool_responses=None, config=None, max_turns=None,
    on_chunk=None, context=None,
    output_format=None, output_content_type=None,
    output_instructions=None, output_constrained=None, *,
    output=None, use=None, docs=None,
) -> GenerateResponseWrapper[Any]:
```

Pretty much none are keyword-only. The original decision of where to put the * in the first place seems arbitrary. Several params don't belong.

**What changes:**

- **Add `*`** (section 3) — all params keyword-only.
- **Keep output as flat kwargs** (section 5) — `output_schema`, `output_format`, `output_constrained` stay as individual kwargs with defaults. Remove the `output` param that accepted `OutputConfig | OutputConfigDict | Output[T]`. Net: same param count for output, but one way to configure instead of five.
- **Remove `on_chunk`** — `generate()` has a streaming callback parameter, but streaming belongs on `generate_stream()`.
- **Move `tool_responses` to `resume`** — only used when resuming from a tool interrupt. JS already groups this under a `resume` options object.

**After cleanup:**

```python
async def generate(
    self,
    *,
    model: str | None = None,
    prompt: str | Part | list[Part] | None = None,
    system: str | Part | list[Part] | None = None,
    messages: list[Message] | None = None,
    tools: list[str] | None = None,
    tool_choice: ToolChoice | None = None,
    return_tool_requests: bool | None = None,
    config: GenerationCommonConfig | dict | None = None,
    max_turns: int | None = None,
    context: dict[str, object] | None = None,
    output_schema: type[OutputT] | None = None,
    output_format: str | None = None,
    output_constrained: bool | None = None,
    use: list[ModelMiddleware] | None = None,
    docs: list[DocumentData] | None = None,
) -> GenerateResponse[OutputT]:
```

**`prompt.__call__()` also changes.** Today it takes a JS-style opts dict:

```python
# Before — opts dict, no autocomplete
response = await my_prompt({"name": "Ted"}, opts={"config": {"temperature": 0.4}})

# After — kwargs, full IDE support
response = await my_prompt({"name": "Ted"}, config={"temperature": 0.4})
```

The `opts` dict (a TypedDict with 16 fields) is replaced with individual kwargs:

```python
async def __call__(
    self,
    input: InputT | None = None,
    *,
    model: str | None = None,
    config: GenerationCommonConfig | dict[str, Any] | None = None,
    messages: list[Message] | None = None,
    docs: list[DocumentData] | None = None,
    tools: list[str] | None = None,
    tool_choice: ToolChoice | None = None,
    output_schema: type | dict[str, Any] | None = None,
    output_format: str | None = None,
    output_constrained: bool | None = None,
    return_tool_requests: bool | None = None,
    max_turns: int | None = None,
    use: list[ModelMiddleware] | None = None,
    context: dict[str, Any] | None = None,
) -> GenerateResponse[OutputT]:
```

`input` stays as the one positional arg (the template variables). Everything else is keyword-only. The `resume` options move to a separate `resume()` method or a `resume` kwarg (matching section 8's `generate()` cleanup). `on_chunk` is removed — streaming belongs on `prompt.stream()`.

**`generate_stream()` — after cleanup:**

```python
async def generate_stream(
    self,
    *,
    model: str | None = None,
    prompt: str | Part | list[Part] | None = None,
    system: str | Part | list[Part] | None = None,
    messages: list[Message] | None = None,
    tools: list[str] | None = None,
    tool_choice: ToolChoice | None = None,
    return_tool_requests: bool | None = None,
    config: GenerationCommonConfig | dict | None = None,
    max_turns: int | None = None,
    context: dict[str, object] | None = None,
    output_schema: type[OutputT] | None = None,
    output_format: str | None = None,
    output_constrained: bool | None = None,
    use: list[ModelMiddleware] | None = None,
    docs: list[DocumentData] | None = None,
) -> GenerateStreamResponse[OutputT]:
```

Same params as `generate()`. The return type changes from `tuple[AsyncIterator, Future]` to a single `GenerateStreamResponse` object that is directly async-iterable and exposes `.response` (see section 7).

**`retrieve()` — after cleanup:**

```python
async def retrieve(
    self,
    *,
    retriever: str,
    query: str | DocumentData,
    options: dict[str, object] | None = None,
) -> RetrieverResponse:
```

Already clean — just needs the `*` marker to enforce keyword-only. `retriever` and `query` become required (they were Optional before, but calling without them always fails).

**`embed()` — after cleanup:**

```python
async def embed(
    self,
    *,
    embedder: str,
    content: str | Document | DocumentData,
    metadata: dict[str, object] | None = None,
    options: dict[str, object] | None = None,
) -> list[Embedding]:
```

Same treatment — `*` marker, `embedder` and `content` become required.
