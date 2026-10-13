# Genkit [in a] Box (Go)

Run Genkit actions (tools, flows, agents) somewhere other than your main
process, and call them as if they were local. "Somewhere" can be a subprocess,
a local OS sandbox, a container, or a remote runtime. You swap a runner, not
your code.

Two reasons to box:

- **Isolation**: you don't fully trust the code (e.g. a shell tool an LLM
  drives). Box the dangerous tool; keep the agent and model keys outside.
- **Relocation**: run an action elsewhere (another process, another language,
  another machine) behind the same call site.

> Status: experimental. This is the Go port of `@genkit-ai/box`.

```go
import box "github.com/firebase/genkit/go/plugins/box/exp"
```

## Proxies

A box hands out proxies: real Genkit actions that forward each call to the box.
They compose anywhere a local action does (`ai.WithTools(...)`, the registry,
other flows).

```go
b := box.New(g, runner)
defer b.Close(ctx)

// Same language: hand over the real tool, no schema restatement.
boxedRunShell := box.NewToolFrom(b, runShell)

// Different language (or no local copy): declare the shape.
search := box.NewTool[SearchIn, SearchOut](b, "search", "Search the repo.")

resp, err := genkit.Generate(ctx, g,
	ai.WithModelName("googleai/gemini-flash-latest"),
	ai.WithTools(boxedRunShell, search),
	ai.WithPrompt("What's in the repo?"),
)
```

Flows work the same way (`box.NewFlow`, `box.NewStreamingFlow`,
`box.NewFlowFrom`), and streamed chunks flow back through the proxy.

When all you have is JSON Schema (config, or the box's `ListActions`
metadata), use `any` type parameters and pass the schemas:

```go
summarize := box.DefineFlow[any, any](b, "summarize",
	box.WithInputSchema(map[string]any{"type": "object", "properties": map[string]any{"url": map[string]any{"type": "string"}}}),
	box.WithOutputSchema(map[string]any{"type": "string"}),
)
```

`NewX` proxies are unregistered. The `DefineX` variants also register the proxy
so it shows up in the Dev UI. `DefineXFrom` proxies must be renamed, since the
original already occupies its name; a renamed proxy still calls the original
action in the box:

```go
box.DefineToolFrom(b, runShell, "boxedRunShell") // calls /tool.v2/runShell in the box
```

Tool proxies call the box's `tool.v2` action, so content parts the boxed tool
attaches (`tool.AttachParts`) reach the caller too.

## Lifecycle: route + idle timeout

`WithRoute` decides which box a call goes to; `WithIdleTimeout` decides how long
an idle box lives.

```go
box.New(g, runner)                                      // Singleton: one box, never released
box.New(g, runner, box.WithRoute(box.PerRequest))        // a fresh box per call, released on return
box.New(g, runner, box.WithRoute(box.SessionRoute))      // one box per session, 5 min idle
box.New(g, runner, box.WithRoute(box.SessionRoute),
	box.WithIdleTimeout(10*time.Minute))                 // override the preset's timeout
```

A route sees the outgoing request (key, input, init, the caller's action
context) and returns a routing key:

```go
box.WithRoute(box.RouteFunc(func(ctx context.Context, req *box.RunActionRequest) (string, error) {
	if tenant, ok := req.Context["tenant"].(string); ok {
		return tenant, nil
	}
	return "default", nil
}))
```

The route owns any key mapping; the box keeps none. A box is released once no
call is in flight and the idle timeout has passed; a new call cancels a pending
release, and a box is never released mid-call.

### One box per session

`SessionRoute` keys by the context's `sessionId`, else the session the payload
names (`box.SessionIDOf(req)`: an agent turn's `init.sessionId` or
`init.state.sessionId`, a snapshot read's `sessionId`), else one shared box. It
is stateless, so every instance of a deployment computes the same key for the
same call.

Calls that only carry a `snapshotId` go to the shared box. Give the boxed agent
a durable session store that every box can read: **routing decides placement,
the store decides whether a conversation survives**.

### Warm-up and discovery

```go
err := b.Warm(ctx, "")                 // start the singleton box now: fail fast, no cold first call
actions, err := b.ListActions(ctx, "") // may start a box just to answer
```

In the box's own runtime (self mode), `Warm` is a no-op and `ListActions`
refuses.

## Tracing

Each proxied call is a real action span on the caller's side, marked with
`genkit:metadata:box` (the box id). `genkit:metadata:box:traceId` links it to
the trace the box records for the same call.

## Runners

A runner owns box lifecycle and the routing-key to instance mapping:

```go
type Runner interface {
	Name() string
	Acquire(ctx context.Context, key string) (box.Conn, error)
	Release(ctx context.Context, key string) error
	Close(ctx context.Context) error
}
```

Runners that start runtimes implement `box.Attacher` to learn the box id, which
they pass to each runtime as `GENKIT_BOX_SELF_ID`.
