# Genkit Go v2 — Summary of Changes

## New repository

Genkit Go is moving to a dedicated repository: **github.com/genkit-ai/genkit-go**. The current monorepo contains code for all Genkit languages; the new repo will contain only Go code. This change is meant to improve discoverability of Genkit Go through search engines and LLMs, keep issues and PRs focused on Go, and foster a stronger community around the Go SDK specifically.

---

The sections below summarize every breaking change in Genkit Go v2, with a brief rationale and before/after code for each.

---

## Concrete types replace interfaces

v1 defines `Model`, `Tool`, `Embedder`, `Retriever`, `Evaluator`, and `Prompt` as interfaces with unexported implementations. This has two compounding problems. First, the interfaces are bloated — every one carries a `Register()` method alongside domain methods like `Generate()` or `Embed()`, even though users never call `Register()` themselves. Second, because users can never hold the concrete type, every `With*` option function needs a parallel `*Arg` interface (e.g. `ModelArg`, `EmbedderArg`) plus a `*Ref` struct for lazy references. That's three types per concept just to pass one around.

v2 exports the concrete structs under the clean names. The interfaces that remain (in the `api` package, for registry internals) can be thin and focused — just `Name()` plus the domain method — because infrastructure methods like `Register()` live on the concrete struct. The concrete types can still be passed directly to functions like `genkit.RegisterAction()` or `genkit.Handler()` without casting, since Go resolves methods on the concrete type. One shared `Named` interface and one `ActionRef` struct replace the entire family of `*Arg`/`*Ref` types.

```go
// v1 — interface carries domain + infrastructure methods
type Model interface {
    Name() string
    Generate(ctx context.Context, req *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error)
    Register(r api.Registry) // users never call this, but it's in the interface
}

var m Model = ai.DefineModel(r, "my-model", opts, fn)  // returns interface
ai.Generate(ctx, r, ai.WithModel(m))                   // WithModel accepts ModelArg

ref := ai.NewModelRef("google/gemini-2.5-flash", nil)
ai.Generate(ctx, r, ai.WithModel(ref))                 // ModelRef also satisfies ModelArg

// v2 — concrete struct; api.Model interface is just Name() + Generate()
var m *Model = ai.DefineModel(r, "my-model", fn, opts) // returns concrete *Model
ai.Generate(ctx, r, ai.WithModel(m))                   // WithModel accepts Named

ref := ai.NewActionRef("google/gemini-2.5-flash", nil)
ai.Generate(ctx, r, ai.WithModel(ref))                 // ActionRef also satisfies Named

// Register() is a method on the concrete *Model, not on any interface.
// Works naturally with genkit.RegisterAction(), genkit.Handler(), etc.
```

The same pattern applies to `Embedder`, `Retriever`, `Evaluator`, and `Prompt` — each drops its bloated interface and `*Arg`/`*Ref` types in favor of the concrete struct + `Named`/`ActionRef`. The `api` package interfaces stay thin (just the domain contract), while the concrete types carry infrastructure methods without polluting the interface.

---

## Unified Prompt type

v1 has two separate prompt concepts: `Prompt` (an interface, untyped input, returns `*ModelResponse`) and `DataPrompt[In, Out]` (a generic struct, typed input and output). They have different `Execute` signatures and can't be used interchangeably.

v2 merges them into a single `Prompt[In, Out, Stream]` type. Users never specify `Stream` — the constructor determines it. `DefinePrompt[In]` produces text output; `DefineDataPrompt[In, Out]` produces structured output. Both share the same `Execute` and `ExecuteStream` signatures.

```go
// v1 — two separate types
p := ai.DefinePrompt(r, "greeting", ...)                  // returns Prompt (interface)
resp, err := p.Execute(ctx, ai.WithInput(myInput))        // untyped input via option, returns *ModelResponse

dp := ai.DefineDataPrompt[MyIn, MyOut](r, "extract", ...) // returns *DataPrompt[MyIn, MyOut]
out, resp, err := dp.Execute(ctx, myInput)                // typed input as param, returns (MyOut, *ModelResponse)

// v2 — one type, two constructors
p := ai.DefinePrompt[MyIn](r, "greeting", ...)            // returns *Prompt[MyIn, string, *ModelResponseChunk]
text, resp, err := p.Execute(ctx, myInput)                // typed input, returns (string, *ModelResponse)

dp := ai.DefineDataPrompt[MyIn, MyOut](r, "extract", ...) // returns *Prompt[MyIn, MyOut, MyOut]
out, resp, err := dp.Execute(ctx, myInput)                // same Execute signature
```

This cuts the API surface in half while keeping strong types for all prompts. The naming mirrors `Generate`/`GenerateData` at the generation level.

---

## Streaming: callbacks → channels

v1 streams via a callback function (`func(context.Context, S) error`) passed to action implementations. Channels are the idiomatic Go primitive for streaming data between goroutines and compose naturally with `select`, `range`, and cancellation. This also brings consistency with newer v2 types like `BidiAction`, `BidiFlow`, and `AgentFlow`, which are built on channels from the start.

```go
// v1
type StreamingFunc[In, Out, Stream any] = func(ctx context.Context, input In, cb StreamCallback[Stream]) (Out, error)
// where StreamCallback[S] = func(context.Context, S) error

// v2
type StreamingFunc[In, Out, Stream any] = func(ctx context.Context, input In, streamCh chan<- Stream) (Out, error)
```

---

## Define\* argument order: name, fn, opts

v1 places options before the function in some APIs. v2 standardizes all `Define*` and `New*` functions to put required arguments first (name, function) and optional config last.

```go
// v1
ai.DefineModel(r, "my-model", opts, fn)
ai.DefineEmbedder(r, "my-embedder", opts, fn)

// v2
ai.DefineModel(r, "my-model", fn, opts)
ai.DefineEmbedder(r, "my-embedder", fn, opts)
```

---

## Typed config for models, embedders, and evaluators

`DefineModel`, `DefineEmbedder`, `DefineEvaluator`, and `DefineBatchEvaluator` gain a `Config` type parameter. The JSON schema for the config is inferred from the type automatically, and the framework deserializes the config before calling the plugin function. This eliminates manual `ConfigSchema` declaration and the `configFromRequest()` boilerplate every plugin currently has. It also prevents accidentally passing one provider's config type to another -- only the exact `Config` type or `map[string]any` (from the dev UI / JSON callers) are accepted; mismatched struct types are rejected.

`ConfigSchema` remains in each options struct as an optional override for types whose default JSON schema reflection is insufficient (e.g. third-party types with custom wrapper generics like `Opt[float64]`).

```go
// v1
// DefineModel is not generic. Plugin manually specifies ConfigSchema and
// deserializes config from req.Config (which is `any`) in every implementation.
func DefineModel(g *Genkit, name string, fn ModelFunc, opts *ModelOptions) *Model

type ModelFunc = func(context.Context, *ModelRequest, ModelStreamCallback) (*ModelResponse, error)

genkit.DefineModel(g, "my-model", func(ctx context.Context, req *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
    cfg, err := configFromRequest(req) // type-switch on any, MapToStruct, etc.
    // ...
}, &ModelOptions{
    ConfigSchema: configToMap(&MyConfig{}),
})

// v2
// DefineModel gains a Config type parameter. Config is inferred from the fn
// signature -- no need to specify it explicitly. The framework deserializes
// req.Config into the typed Config before calling fn.
func DefineModel[Config any](g *Genkit, name string, fn ModelFunc[Config], opts *ModelOptions) *Model

type ModelFunc[Config any] = func(context.Context, *ModelRequest, Config, ModelStreamCallback) (*ModelResponse, error)

genkit.DefineModel(g, "my-model", func(ctx context.Context, req *ModelRequest, cfg MyConfig, cb ModelStreamCallback) (*ModelResponse, error) {
    // cfg is already MyConfig -- no manual deserialization
    // ...
}, &ModelOptions{})
```

The same pattern applies to `DefineEmbedder` (`EmbedderFunc[Config]`), `DefineEvaluator` (`EvaluatorFunc[Config]`), `DefineBatchEvaluator` (`BatchEvaluatorFunc[Config]`), and `DefineBackgroundModel` (which embeds `ModelOptions`). The serialization structs (`ModelRequest.Config`, `EmbedRequest.Config`, etc.) remain `any` -- the typed deserialization happens in the wrapper that `Define*` generates.

---

## Field naming cleanup

v1 has inconsistent field names across generated and hand-written types. v2 fixes these to follow Go conventions.

- **`.Options` to `.Config`**: Fields like `EmbedRequest.Options`, `EvaluatorCallbackRequest.Options`, and `EvaluatorRequest.Options` are renamed to `.Config` for consistency with `ModelRequest.Config`.
- **`Id` to `ID`**: Generated types use `Id` (e.g. `EvaluationId`, `SpanId`, `TraceId`) which violates Go naming conventions. v2 renames these to `ID` (e.g. `EvaluationID`, `SpanID`, `TraceID`).
- **`Url` to `URL`**, **`Api` to `API`**, and similar acronym fields follow the same pattern.

This is a mechanical pass across generated types in `gen.go` and any hand-written types that drifted from convention.

---

## Sealed Registry interface

v1's `Registry` is a public interface that anyone can implement. Adding a method to it is a breaking change. v2 adds an unexported `sealed()` method, preventing external implementations while allowing the interface to grow safely.

```go
// v1
type Registry interface {
    RegisterAction(key string, action Action)
    LookupAction(key string) Action
    // ...
}

// v2
type Registry interface {
    RegisterAction(typ ActionType, a Action)
    LookupAction(typ ActionType, name string) Action
    // ...
    sealed() // prevents external implementations
}
```

---

## Remove WithOutputType / WithOutputSchema

v1 allows specifying structured output types via `WithOutputType(val)` or `WithOutputSchema(schema)` as generate options. This creates a class of runtime type errors — the schema and the variable you unmarshal into can easily drift apart. v2 removes both in favor of `GenerateData[Out]` and `DefineDataPrompt[In, Out]`, where the output type is a compile-time generic parameter.

```go
// v1
resp, err := ai.Generate(ctx, r, ai.WithOutputType(MyStruct{}), ...)
var out MyStruct
resp.Output(&out)

// v2
out, resp, err := ai.GenerateData[MyStruct](ctx, r, ...)
// out is already typed — no separate unmarshal step
```

---

## GenerateData returns value, not pointer

v1's `GenerateData[Out]` returns `(*Out, *ModelResponse, error)`. On error or empty output, the caller gets a nil pointer that's easy to dereference without checking. v2 returns `(Out, *ModelResponse, error)` — zero value on error.

```go
// v1
out, resp, err := ai.GenerateData[MyStruct](ctx, r, ...)
// out is *MyStruct — nil on error, easy to panic

// v2
out, resp, err := ai.GenerateData[MyStruct](ctx, r, ...)
// out is MyStruct — zero value on error, no nil pointer
```

---

## New tool APIs

v1 introduced experimental tool APIs in `ai/x` ([PR #4797](https://github.com/firebase/genkit/pull/4797)) that simplify tool definitions, add typed interrupt/resume, and provide runtime helpers for multipart responses and streaming progress. These APIs are built on top of the existing v1 tool infrastructure. v2 promotes them to the standard tool APIs and replaces the v1 internals underneath.

The main changes from v1's `DefineTool` / `DefineMultipartTool` / `ToolContext` / untyped interrupt API:

- **`ToolContext` removed.** v1 wraps `context.Context` in a `ToolContext` struct solely to carry interrupt/resume metadata, forcing every tool function to accept a non-standard context type. Tool functions now receive a plain `context.Context`. Interrupt/resume data and other tool-specific state are accessed through typed helpers in the `tool` package (see below).
- **Unified `DefineTool`** replaces both `DefineTool` and `DefineMultipartTool`. Tool functions return `(Out, error)`. Multipart responses (images, media) are attached via `tool.AttachParts(ctx, parts...)` instead of requiring a separate function signature.
- **`DefineInterruptibleTool`** replaces the untyped `Restart`/`Respond`/`Interrupt` pattern with a typed `*Res` parameter. When the tool is called normally, `*Res` is nil; when resumed after an interrupt, it carries the caller's typed resume data.
- **`tool` runtime helper package** provides functions for use inside tool bodies: `tool.Interrupt(data)` to pause execution, `tool.AttachParts(ctx, ...)` for multipart content, `tool.SendPartial(ctx, data)` for streaming progress updates during execution, and `tool.OriginalInput[In](ctx)` for accessing the pre-restart input.
- **Typed interrupt handling on the caller side** via `tool.InterruptAs[T](part)` for extracting interrupt metadata, and `tool.Resume[Res](part, data)` / `tool.Respond(part, output)` for building restart/response parts. The tool definition itself also has `.Resume()` and `.Respond()` methods that validate the part belongs to that tool.
- **`GenerateActionResume` fields use `[]*Part` directly.** v1's `GenerateActionResume.Restart` and `.Respond` fields are typed as `[]*toolRequestPart` and `[]*toolResponsePart` -- unexported wrapper structs that exist because Go lacks union types and the original implementation modeled tool requests and responses as separate types rather than using `Part` directly. v2 replaces both with `[]*Part`, matching the wire format and aligning with how `tool.Resume` and `tool.Respond` already return `*Part`.
- **Partial tool responses** let tools stream progress updates to the client during execution via `tool.SendPartial(ctx, data)`. Callers distinguish progress from final results using `Part.IsPartial()`.

```go
// v1 — two separate APIs, untyped interrupt
weatherTool := ai.DefineTool(r, "getWeather", "Fetches the weather",
    func(ctx *ai.ToolContext, input WeatherInput) (string, error) { ... })

multipartTool := ai.DefineMultipartTool(r, "screenshot", "Takes a screenshot",
    func(ctx *ai.ToolContext, input ScreenshotInput) (*ai.MultipartToolResponse, error) { ... })

tool.Restart(toolReq, &RestartOptions{ResumedMetadata: rawMeta}) // untyped

// v2 — single DefineTool, typed interrupts
weatherTool := genkit.DefineTool(g, "getWeather", "Fetches the weather",
    func(ctx context.Context, input WeatherInput) (string, error) {
        return "Sunny, 25°C", nil
    },
)

// Multipart via AttachParts instead of a separate function signature
screenshotTool := genkit.DefineTool(g, "screenshot", "Takes a screenshot",
    func(ctx context.Context, input ScreenshotInput) (string, error) {
        img := takeScreenshot(input.URL)
        tool.AttachParts(ctx, ai.NewMediaPart("image/png", img))
        return "Screenshot captured", nil
    },
)

// Typed interrupt/resume via DefineInterruptibleTool
transferTool := genkit.DefineInterruptibleTool(g, "transfer", "Transfers money",
    func(ctx context.Context, input TransferInput, confirm *Confirmation) (string, error) {
        if confirm != nil && !confirm.Approved {
            return "cancelled", nil
        }
        if confirm == nil && input.Amount > 100 {
            return "", tool.Interrupt(TransferInterrupt{Reason: "large_amount", Amount: input.Amount})
        }
        return "completed", nil
    },
)

// Caller-side: typed resume
restart, _ := transferTool.Resume(interrupt, Confirmation{Approved: true})
resp, _ = genkit.Generate(ctx, g,
    ai.WithMessages(resp.History()...),
    ai.WithTools(transferTool),
    ai.WithToolRestarts(restart),
)
```

See [PR #4797](https://github.com/firebase/genkit/pull/4797) for the full API reference, agent flow integration, and additional examples.

---

## Merge FormatHandler and StreamingFormatHandler

v1 has two separate interfaces for format handlers: `FormatHandler` (with `ParseMessage`) and `StreamingFormatHandler` (with `ParseOutput`/`ParseChunk`). This split existed to avoid a breaking change in v1. v2 merges them into a single `FormatHandler` with four methods and drops the legacy `ParseMessage`.

```go
// v1
type FormatHandler interface {
    ParseMessage(message *Message) (*Message, error)
    Instructions() string
    Config() ModelOutputConfig
}
type StreamingFormatHandler interface {
    ParseOutput(message *Message) (any, error)
    ParseChunk(chunk *ModelResponseChunk) (any, error)
}

// v2
type FormatHandler interface {
    Instructions() string
    Config() ModelOutputConfig
    ParseOutput(message *Message) (any, error)
    ParseChunk(chunk *ModelResponseChunk) (any, error)
}
```

---

## DefineFormat drops redundant name parameter

v1's `DefineFormat` takes a `name` string and a `Formatter`, but `Formatter` already has a `Name()` method. The name parameter is redundant and a source of potential mismatch. v2 drops it.

```go
// v1
func DefineFormat(r api.Registry, name string, formatter Formatter)

// v2
func DefineFormat(r api.Registry, formatter Formatter)
// name comes from formatter.Name()
```

---

## Action.RunJSON always returns telemetry

v1 has `RunJSON` (discards telemetry) and `RunJSONWithTelemetry` (returns it). There's no reason to discard telemetry — callers who don't need it can ignore the extra fields. v2 removes `RunJSONWithTelemetry` and makes `RunJSON` always return `*api.ActionRunResult` containing both the output and trace metadata.

```go
// v1
out, err := action.RunJSON(ctx, input, cb)                 // json.RawMessage
result, err := action.RunJSONWithTelemetry(ctx, input, cb) // *ActionRunResult[json.RawMessage]

// v2
result, err := action.RunJSON(ctx, input, streamCh)        // *ActionRunResult[json.RawMessage] (always)
```

---

## ToolArg replaces ToolRef

v1 uses `ToolRef` for passing tool references. v2 introduces a sealed `ToolArg` interface that both `*Tool[In, Out]` and `ToolNamed` (a string/glob type) satisfy. This lets `WithTools` accept concrete tools, exact names, and glob patterns (e.g. `"mcp/*"`) through one type.

```go
// v1
ai.Generate(ctx, r, ai.WithTools(myTool, ai.ToolRef("other-tool")))

// v2
ai.Generate(ctx, r, ai.WithTools(myTool, ai.ToolNamed("other-tool"), ai.ToolNamed("mcp/*")))
```

---

## WithInput removed from prompt execution

v1 passes prompt input as an option (`WithInput(val)`) which is untyped. v2 makes input a typed parameter on `Execute` and `ExecuteStream` directly.

```go
// v1
resp, err := prompt.Execute(ctx, ai.WithInput(myInput))

// v2
out, resp, err := prompt.Execute(ctx, myInput)
```

---

## genkit.Init and plugin functions return errors

v1's `genkit.Init()` returns only a `*Genkit` instance. Plugin functions like `Init()` and `ListActions()` either panic or silently swallow errors. This is wrong for two reasons: any function that accepts a `context.Context` can perform fallible work (network requests, credential validation), and the Go convention is that such functions return an `error`. Panicking when a user forgets an environment variable is a poor experience — it should be a normal error the caller can handle.

v2 adds `error` to the return value of `genkit.Init()` and all plugin functions that take a `context.Context`. This makes the SDK more idiomatic and gives callers control over error handling instead of crashing the process.

```go
// v1
g := genkit.Init(ctx, opts)              // panics on failure
googleai.Init(ctx, &googleai.Config{})   // panics or silently fails

// v2
g, err := genkit.Init(ctx, opts)         // returns error
err := googleai.Init(ctx, &googleai.Config{}) // returns error
```

---

## Move status and error types out of core

v1 puts canonical status codes (`StatusName`, `OK`, `CANCELLED`, `INTERNAL`, etc.), status-to-HTTP mappings (`HTTPStatusCode`, `StatusNameToCode`), and error types (`GenkitError`, `UserFacingError`, `ReflectionError`) directly in the `core` package.

v2 moves these types into a dedicated package (e.g. `core/status` or `core/gerror`) so that error handling has a clear home and `core` stays focused on bigger picture concepts.

```go
// v1
import "github.com/firebase/genkit/go/core"

err := core.NewError(core.NOT_FOUND, "model %q not registered", name)
code := core.HTTPStatusCode(core.NOT_FOUND)

// v2
import "github.com/firebase/genkit/go/core/status" // or similar

err := status.NewError(status.NOT_FOUND, "model %q not registered", name)
code := status.HTTPStatusCode(status.NOT_FOUND)
```

---

## Full removed/replaced type reference

| Removed | Replacement |
|---------|-------------|
| `Model` interface | `*Model` struct |
| `ModelArg`, `ModelRef` | `Named`, `ActionRef` |
| `BackgroundModel` interface | `*BackgroundModel` struct |
| `Tool` interface | `*Tool[In, Out]` struct |
| `ToolDef[In, Out]` | `*Tool[In, Out]` (renamed) |
| `ToolRef` | `ToolArg` sealed interface, `ToolNamed` |
| `ToolContext` | `context.Context` + helpers |
| `Embedder` interface | `*Embedder` struct |
| `EmbedderArg`, `EmbedderRef` | `Named`, `ActionRef` |
| `Retriever` interface | `*Retriever` struct |
| `RetrieverArg`, `RetrieverRef` | `Named`, `ActionRef` |
| `Evaluator` interface | `*Evaluator` struct |
| `EvaluatorArg`, `EvaluatorRef` | `Named`, `ActionRef` |
| `Prompt` interface | `*Prompt[In, Out, Stream]` struct |
| `DataPrompt[In, Out]` | `*Prompt[In, Out, Out]` via `DefineDataPrompt` |
| `StreamCallback[S]` | `chan<- S` |
| `RunJSONWithTelemetry` | `RunJSON` (always returns telemetry) |
| `WithOutputType`, `WithOutputSchema` | `GenerateData[Out]`, `DefineDataPrompt[In, Out]` |
| `WithInput` (prompt option) | Typed `input In` parameter |
| `FormatHandler.ParseMessage` | Removed |
| `StreamingFormatHandler` | Merged into `FormatHandler` |
| `DefineTool`, `DefineMultipartTool` | `DefineTool` (unified), `DefineInterruptibleTool` |
| `Interrupt()`, `InterruptOptions` | `tool.Interrupt(data)` |
| `OriginalInput()` | `tool.OriginalInput[In](ctx)` |
| `Respond`, `Restart` (untyped) | `tool.Resume[Res]`, `tool.Respond`, or typed methods on `*InterruptibleTool` |
| `GenerateActionResume.Restart` / `.Respond` (`[]*toolRequestPart` / `[]*toolResponsePart`) | `[]*Part` |
| `ModelFunc` (untyped) | `ModelFunc[Config]` (typed config param) |
| `EmbedderFunc` (untyped) | `EmbedderFunc[Config]` (typed config param) |
| `EvaluatorFunc` (untyped) | `EvaluatorFunc[Config]` (typed config param) |
| `BatchEvaluatorFunc` (untyped) | `BatchEvaluatorFunc[Config]` (typed config param) |
| `configFromRequest()` per plugin | Removed; framework handles deserialization |

## New types

| New | Purpose |
|-----|---------|
| `Named` | Shared interface for all `With*` options that accept a model, embedder, retriever, or evaluator |
| `ActionRef` | Unified lazy reference replacing `ModelRef`, `EmbedderRef`, `RetrieverRef`, `EvaluatorRef` |
| `ToolArg` | Sealed interface for `WithTools` — distinguishes tool references from other named things |
| `ToolNamed` | String/glob tool reference satisfying `ToolArg` |
| `InterruptibleTool[In, Out, Res]` | Tool with typed interrupt/resume support |
| `tool` package | Runtime helpers for tool bodies: `Interrupt`, `AttachParts`, `SendPartial`, `Resume`, `Respond`, etc. |
