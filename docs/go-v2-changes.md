# Genkit Go v2 — Summary of Changes

This document summarizes every breaking change in Genkit Go v2, with a brief rationale and before/after code for each.

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

## ToolContext → context.Context + helpers

v1 wraps `context.Context` in a `ToolContext` struct solely to carry interrupt/resume metadata. This forces every tool function to accept a non-standard context type. v2 drops the wrapper and stores interrupt data in the context directly, accessed through typed helper functions.

```go
// v1
type ToolFunc[In, Out any] = func(ctx *ToolContext, input In) (Out, error)

resumed := ctx.Resumed             // map[string]any
original := ctx.OriginalInput      // any

// v2
type ToolFunc[In, Out any] = func(ctx context.Context, input In) (Out, error)

resumed, ok := ai.ResumedMetadata[MyMeta](ctx) // strongly typed
original, err := ai.OriginalInputAs[MyIn](ctx) // strongly typed
```

The untyped accessors (`Resumed`, `OriginalInput`) and `InterruptOptions` are removed. Only the typed variants remain.

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

## Typed interrupt/restart API

v1 uses untyped `Restart`/`Respond` methods with `*RestartOptions` (all `any` fields) and an untyped `Interrupt` function. v2 removes the untyped variants entirely. `RestartWith`/`RespondWith` are generic methods on `*Tool[In, Out]`, and `InterruptWith[T]` replaces `Interrupt`.

```go
// v1
tool.Restart(toolReq, &RestartOptions{
    ReplaceInput:    rawInput,     // any
    ResumedMetadata: rawMeta,      // any
})

// v2
tool.RestartWith(toolReq,
    ai.WithNewInput[MyIn](typedInput),
    ai.WithResumedMetadata[MyIn](typedMeta),
)
```

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
| `Interrupt()`, `InterruptOptions` | `InterruptWith[T]` |
| `OriginalInput()` | `OriginalInputAs[T]` |
| `Respond`, `Restart` (untyped) | `RespondWith`, `RestartWith` (typed) |

## New types

| New | Purpose |
|-----|---------|
| `Named` | Shared interface for all `With*` options that accept a model, embedder, retriever, or evaluator |
| `ActionRef` | Unified lazy reference replacing `ModelRef`, `EmbedderRef`, `RetrieverRef`, `EvaluatorRef` |
| `ToolArg` | Sealed interface for `WithTools` — distinguishes tool references from other named things |
| `ToolNamed` | String/glob tool reference satisfying `ToolArg` |
