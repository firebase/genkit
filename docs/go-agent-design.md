# Genkit Go Agent Abstraction - Design Document

## Overview

This document describes the design for the `DefineAgent` API in Genkit Go. An Agent is a higher-level abstraction over SessionFlow that provides automatic passthrough to the Generate API, eliminating boilerplate conversation loop code.

An Agent:
- Is created via `DefineAgent`
- Returns a `*SessionFlow` as the underlying primitive
- Automatically handles the generate-respond loop for each turn
- Supports configuration via options or by inheriting from a Prompt

This design builds on SessionFlow (as described in [go-session-flow-design.md](go-session-flow-design.md)).

## Package Location

Agent lives alongside SessionFlow in `go/ai/x/` (experimental). Import as `aix "github.com/firebase/genkit/go/ai/x"`.

---

## 1. API Surface

### 1.1 DefineAgent

```go
// DefineAgent creates an Agent and registers it as a SessionFlow.
// Type parameters:
//   - Stream: Type for status updates (for subagent compatibility)
//   - State: Type for user-defined state (accessible by tools via context)
func DefineAgent[Stream, State any](r api.Registry, name string, opts ...AgentOption) *SessionFlow[Stream, State]
```

### 1.2 AgentOption

```go
// AgentOption configures an Agent. Non-generic for clean usage.
type AgentOption interface {
    applyAgent(*agentOptions) error
}
```

---

## 2. Available Options

### Generate API Options (non-generic)

Standard Generate API options, applied to each turn:

`WithModel`, `WithModelName`, `WithConfig`, `WithTools`, `WithToolChoice`, `WithMaxTurns`, `WithResources`, `WithDocs`, `WithTextDocs`, `WithOutputType`, `WithOutputSchema`, `WithOutputFormat`, `WithPrompt`, `WithMessages`

### System Prompt Option (non-generic)

`WithSystem(text string, args ...any)` - Sets the system prompt text.

### Snapshot Options (shared with SessionFlow)

These options are shared between `DefineAgent` and `DefineSessionFlow`. The concrete return type implements both `AgentOption` and `SessionFlowOption[State]`.

```go
// Returns *snapshotStoreOption[State] which implements both interfaces
func WithSnapshotStore[State any](store SnapshotStore[State]) *snapshotStoreOption[State]
func WithSnapshotCallback[State any](cb SnapshotCallback[State]) *snapshotCallbackOption[State]
```

### Base Prompt Option (generic)

```go
// PromptRenderer is satisfied by both Prompt (with In=any) and *DataPrompt[In, Out].
// This enables type-safe input when using DataPrompt.
type PromptRenderer[In any] interface {
    Render(ctx context.Context, input In) (*GenerateActionOptions, error)
}

// Configure agent using a Prompt's settings as defaults.
// Stores a closure that DefineAgent calls once to extract all settings.
//
// The input parameter provides values for {{variable}} style templates.
// Pass nil when the prompt has no input variables.
//
// When p is a *DataPrompt[In, Out], the input type is enforced at compile time.
// When p is a Prompt, input is any.
func WithBasePrompt[In any](p PromptRenderer[In], input In) AgentOption

// Implementation stores a render closure to handle generic type erasure:
//
//   func WithBasePrompt[In any](p PromptRenderer[In], input In) AgentOption {
//       return &basePromptOption{
//           render: func(ctx context.Context) (*GenerateActionOptions, error) {
//               return p.Render(ctx, input)
//           },
//       }
//   }
```

### Options NOT Included

| Option | Reason |
|--------|--------|
| `WithStreaming` | Handled internally |
| `WithReturnToolRequests`, `WithToolResponses/Restarts` | Agent handles tools automatically |

---

## 3. Prompt Integration

### What WithBasePrompt Extracts

When `WithBasePrompt` is called, `prompt.Render(ctx, input)` is invoked once to extract:

- Model, Config, Tools, ToolChoice, MaxTurns, OutputSchema, OutputFormat
- System message(s) → stored as `SystemText`
- Non-system messages (user/model) → stored as `InitialMessages`

All settings are static after definition. Template variables (`{{variable}}`) are substituted at definition time using the provided input.

```go
// DataPrompt with typed input - compile-time type safety
rolePrompt := genkit.DefineDataPrompt[RoleInput, string](g, "roleAgent",
    ai.WithSystem("You are a {{role}} assistant."),
)

// Input type is enforced by the compiler
agent := genkit.DefineAgent[Status, State](g, "roleAgent",
    aix.WithBasePrompt(rolePrompt, RoleInput{Role: "coding"}),  // ✓ compiles
    // aix.WithBasePrompt(rolePrompt, WrongType{}),             // ✗ compile error
)
```

### Option Precedence

`WithBasePrompt` settings are always applied first as defaults. Other options override:

```go
myAgent := genkit.DefineAgent[Status, State](g, "myAgent",
    aix.WithBasePrompt(myPrompt, nil),            // Applied first (defaults)
    aix.WithModelName("googleai/gemini-2.5-pro"), // Overrides prompt's model
)
```

---

## 4. Internal Implementation

### agentOptions Structure

```go
type agentOptions struct {
    // Generate API options (set directly or extracted from basePromptRender)
    Model           ai.ModelArg
    Config          any
    Tools           []ai.ToolRef
    ToolChoice      ai.ToolChoice
    MaxTurns        int
    Resources       []ai.Resource
    Documents       []*ai.Document
    OutputSchema    map[string]any
    OutputFormat    string
    InitialMessages []*ai.Message // Non-system messages, added to session once at start
    SystemText      string        // System prompt text, passed to Generate each turn

    // Base prompt render closure (from WithBasePrompt, called once by DefineAgent)
    basePromptRender func(ctx context.Context) (*ai.GenerateActionOptions, error)

    // Snapshot options
    snapshotStore    any
    snapshotCallback any
}
```

### DefineAgent Implementation

```go
func DefineAgent[Stream, State any](r api.Registry, name string, opts ...AgentOption) *SessionFlow[Stream, State] {
    agentOpts := &agentOptions{}
    for _, opt := range opts {
        opt.applyAgent(agentOpts)
    }

    // If WithBasePrompt was used, call the render closure to extract settings
    if agentOpts.basePromptRender != nil {
        rendered, err := agentOpts.basePromptRender(context.Background())
        if err != nil {
            panic(fmt.Errorf("failed to render base prompt: %w", err))
        }

        // Extract settings (only if not already set by other options)
        if agentOpts.Model == nil && rendered.Model != "" {
            agentOpts.Model = ai.ModelName(rendered.Model)
        }
        if agentOpts.Config == nil {
            agentOpts.Config = rendered.Config
        }
        // ... extract tools, toolChoice, maxTurns, outputSchema, outputFormat ...

        // Separate system from non-system messages
        for _, msg := range rendered.Messages {
            if msg.Role == ai.RoleSystem {
                if agentOpts.SystemText == "" {
                    agentOpts.SystemText = msg.Text()
                }
            } else {
                agentOpts.InitialMessages = append(agentOpts.InitialMessages, msg)
            }
        }
    }

    // Create SessionFlow with automatic generate loop
    fn := func(ctx context.Context, resp *Responder[Stream], params *SessionFlowParams[Stream, State]) error {
        // Add initial messages to session once at start
        if len(agentOpts.InitialMessages) > 0 {
            params.Session.AddMessages(agentOpts.InitialMessages...)
        }

        return params.Session.Run(ctx, func(ctx context.Context, input *SessionFlowInput) error {
            genOpts := []ai.GenerateOption{ai.WithMessages(params.Session.Messages()...)}

            // Add configured options
            if agentOpts.Model != nil {
                genOpts = append(genOpts, ai.WithModel(agentOpts.Model))
            }
            if agentOpts.Config != nil {
                genOpts = append(genOpts, ai.WithConfig(agentOpts.Config))
            }
            if len(agentOpts.Tools) > 0 {
                genOpts = append(genOpts, ai.WithTools(agentOpts.Tools...))
            }
            if len(agentOpts.OutputSchema) > 0 {
                genOpts = append(genOpts, ai.WithOutputSchema(agentOpts.OutputSchema))
            }
            if agentOpts.OutputFormat != "" {
                genOpts = append(genOpts, ai.WithOutputFormat(agentOpts.OutputFormat))
            }
            if agentOpts.SystemText != "" {
                genOpts = append(genOpts, ai.WithSystem(agentOpts.SystemText))
            }
            // ... other options ...

            // Stream generation
            for result, err := range ai.GenerateStream(ctx, r, genOpts...) {
                if err != nil {
                    return err
                }
                if result.Done {
                    params.Session.AddMessages(result.Response.Message)
                } else {
                    resp.SendChunk(result.Chunk)
                }
            }
            return nil
        })
    }

    return DefineSessionFlow[Stream, State](r, name, fn, /* snapshot options */)
}
```

---

## 5. Example Usage

### Basic Agent

```go
chatAgent := genkit.DefineAgent[ChatStatus, ChatState](g, "chatAgent",
    aix.WithModelName("googleai/gemini-3-flash-preview"),
    aix.WithSystem("You are a helpful assistant."),
    aix.WithTools(myTool),
)

conn, _ := chatAgent.StreamBidi(ctx)
conn.SendText("Hello!")
for chunk, err := range conn.Receive() {
    if chunk.Chunk != nil {
        fmt.Print(chunk.Chunk.Text())
    }
    if chunk.EndTurn {
        break
    }
}
conn.Close()
```

### Agent from Prompt

```go
assistantPrompt := genkit.DefinePrompt(g, "assistant",
    ai.WithModelName("googleai/gemini-3-flash-preview"),
    ai.WithSystem("You are a helpful coding assistant."),
    ai.WithTools(searchTool, calculatorTool),
)

assistantAgent := genkit.DefineAgent[Status, State](g, "assistant",
    aix.WithBasePrompt(assistantPrompt, nil),
)
```

### Agent with Initial Context

```go
// Initial messages are added to session once at start, then user inputs append
tutorAgent := genkit.DefineAgent[Status, State](g, "tutorAgent",
    aix.WithModelName("googleai/gemini-3-flash-preview"),
    aix.WithSystem("You are a coding tutor."),
    aix.WithMessages(
        ai.NewUserTextMessage("I'm learning Go and want to understand concurrency."),
        ai.NewModelTextMessage("Great! Go's concurrency model is one of its strengths. What would you like to start with?"),
    ),
)
```

### Agent with Structured Output

```go
type TaskResponse struct {
    Task     string   `json:"task"`
    Steps    []string `json:"steps"`
    Priority string   `json:"priority"`
}

taskAgent := genkit.DefineAgent[Status, State](g, "taskAgent",
    aix.WithModelName("googleai/gemini-3-flash-preview"),
    aix.WithSystem("You are a task planning assistant. Break down tasks into steps."),
    aix.WithOutputType(TaskResponse{}),
)
```

### Agent with Snapshots

```go
store := aix.NewInMemorySnapshotStore[ChatState]()

chatAgent := genkit.DefineAgent[ChatStatus, ChatState](g, "chatAgent",
    aix.WithModelName("googleai/gemini-3-flash-preview"),
    aix.WithSystem("You are a helpful assistant."),
    aix.WithSnapshotStore(store),
)
```

---

## 6. Design Decisions

### Why Return SessionFlow?

Returning `*SessionFlow` directly avoids API duplication and makes clear that Agent IS a SessionFlow with automatic behavior.

### Why Non-Generic Options?

Most options don't involve `State`, so generic options would add verbosity. Only snapshot options need type parameters (usually inferred from arguments).

### How Snapshot Options Work With Both Agent and SessionFlow

Snapshot options return a concrete generic type that implements both interfaces:

```go
type snapshotStoreOption[State any] struct {
    store SnapshotStore[State]
}

func (o *snapshotStoreOption[State]) applySessionFlow(opts *sessionFlowOptions[State]) error {
    opts.SnapshotStore = o.store
    return nil
}

func (o *snapshotStoreOption[State]) applyAgent(opts *agentOptions) error {
    opts.snapshotStore = o.store // stored as any
    return nil
}

func WithSnapshotStore[State any](store SnapshotStore[State]) *snapshotStoreOption[State] {
    return &snapshotStoreOption[State]{store: store}
}
```

Go's structural typing allows `*snapshotStoreOption[State]` to satisfy both `SessionFlowOption[State]` and `AgentOption`.

### Why Does WithBasePrompt Store a Closure?

`WithBasePrompt[In any]` is generic, but `agentOptions` is not. We can't store the prompt directly because Go doesn't allow type assertions like `prompt.(PromptRenderer[any])` when the actual type is `*DataPrompt[MyInput, Out]`. The closure captures the concrete generic types at option creation time, allowing `DefineAgent` to call it without knowing the types.

---

## 7. Files to Create/Modify

| File | Description |
|------|-------------|
| `go/ai/x/agent.go` | DefineAgent function |
| `go/ai/x/agent_options.go` | AgentOption interface and agent-specific options |
| `go/ai/x/session_flow_options.go` | Update snapshot options to return concrete types and implement AgentOption |

---

## 8. Future Considerations

Out of scope for this design:
- Per-turn system prompt rendering with `{{@state.field}}` support
- Subagents, agent hooks, agent composition, agent routing
