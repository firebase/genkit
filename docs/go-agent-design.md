# Genkit Go Agent - Design Document

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

```go
// DefineAgent creates an Agent and registers it as a SessionFlow.
// Type parameters:
//   - Stream: Type for status updates (for subagent compatibility)
//   - State: Type for user-defined state (accessible by tools via context)
func DefineAgent[Stream, State any](r api.Registry, name string, opts ...AgentOption[State]) *SessionFlow[Stream, State]
```

---

## 2. Available Options

`AgentOption[State]` is generic, providing **compile-time type safety**. Generate API options are wrapped in `WithGenerateOpts` to avoid needing to pass the `State` type parameter to each:

```go
type AgentOption[State any] interface {
    applyAgent(*agentOptions[State]) error
}

DefineAgent[Stream, State](g, "myAgent",
    WithBasePrompt[State](prompt, input),
    WithGenerateOpts[State](
        ai.WithModel(model),
        ai.WithConfig(config),
        ai.WithTools(tools...),
    ),
    WithSnapshotStore(store),
)
```

### WithGenerateOpts

Wraps non-generic Generate API options:

```go
func WithGenerateOpts[State any](opts ...ai.GenerateOption) AgentOption[State]

// Usage
WithGenerateOpts[ChatState](
    ai.WithModel(model),
    ai.WithConfig(config),
    ai.WithTools(tool1, tool2),
    ai.WithOutputType(MyOutput{}),
)
```

### Snapshot Options (shared with SessionFlow)

These options are shared between `DefineAgent` and `DefineSessionFlow`. The concrete return type implements both `AgentOption` and `SessionFlowOption[State]`.

```go
func WithSnapshotStore[State any](store SnapshotStore[State]) SessionFlowOption[State]
func WithSnapshotCallback[State any](cb SnapshotCallback[State]) SessionFlowOption[State]
```

### Base Prompt Option

```go
// PromptRenderer is satisfied by both Prompt (with In=any) and *DataPrompt[In, Out].
// This enables type-safe input when using DataPrompt.
type PromptRenderer[In any] interface {
    Render(ctx context.Context, input In) (*GenerateActionOptions, error)
}

// Configure agent using a Prompt's settings as defaults.
// The input parameter provides default values for {{variable}} style templates.
// Pass nil if clients will always provide input via WithPromptInput at session start.
//
// At session start, if State.PromptInput is set (via WithPromptInput), it overrides the default.
// This allows the same agent definition to be customized per-session.
//
// When p is a *DataPrompt[In, Out], the input type is enforced at compile time.
// When p is a Prompt, input is any.
func WithBasePrompt[State, In any](p PromptRenderer[In], input In) AgentOption[State]
```

### Options NOT Included

| Option | Reason |
|--------|--------|
| `WithStreaming` | Handled internally |
| `WithReturnToolRequests`, `WithToolResponses/Restarts` | Agent handles tools automatically |

---

## 3. Prompt Integration

### Rendering Strategy

Prompts support two types of template variables:
- `{{variable}}` - Substituted from PromptInput (static per session)
- `{{@state.field}}` - Substituted from current session state (dynamic per turn)

The **entire prompt is re-rendered each turn** because any message (system or user) may contain `{{@state}}` variables.

### What Gets Stored Where

| Data | Storage Location | When Set |
|------|------------------|----------|
| PromptInput | `SessionState.PromptInput` | Session start |
| Conversation messages | `SessionState.Messages` | After each turn |
| Static settings (model, tools, etc.) | `agentOptions` (in-memory) | Definition time |
| Prompt-rendered messages | Re-rendered each turn | N/A |

**SessionState.Messages** contains actual conversation (user inputs, model responses) plus any `WithMessages` initial context—but NOT prompt-rendered messages. Prompt messages are re-rendered fresh each turn.

**Snapshots store:** Messages + Custom + PromptInput. Prompt-rendered messages are not stored.

### Per-Turn Rendering Flow

```
1. User sends message → added to SessionState.Messages
2. Re-render prompt with (PromptInput, @state) → rendered messages
3. Generate with: rendered messages + SessionState.Messages
4. Model response → added to SessionState.Messages
5. Snapshot saved (conversation + PromptInput, no rendered messages)
```

### WithBasePrompt Behavior

When `WithBasePrompt[State](prompt, defaultInput)` is called:

1. **At definition time** (if defaultInput != nil): Render to extract static settings (model, tools, config, outputSchema, etc.)
2. **At session start**: Store effective PromptInput in `SessionState.PromptInput`
3. **Each turn**: Re-render entire prompt with current PromptInput + @state

```go
// DataPrompt with typed input - compile-time type safety
rolePrompt := genkit.DefineDataPrompt[RoleInput, string](g, "roleAgent",
    ai.WithSystem("You are a {{role}} assistant. User mood: {{@state.mood}}"),
)

// Input type is enforced by the compiler
agent := genkit.DefineAgent[Status, State](g, "roleAgent",
    aix.WithBasePrompt[State](rolePrompt, RoleInput{Role: "coding"}),  // ✓ compiles
    // aix.WithBasePrompt[State](rolePrompt, WrongType{}),             // ✗ compile error
)
```

### Session-Start PromptInput Override

Clients can provide `PromptInput` via `WithPromptInput` to override the default:

- **No default input**: Define with `WithBasePrompt[State](prompt, nil)`, client must provide
- **Default with override**: Define with default, client can optionally customize

### Option Precedence

`WithBasePrompt` settings are applied first as defaults. `WithGenerateOpts` can override:

```go
myAgent := genkit.DefineAgent[Status, State](g, "myAgent",
    aix.WithBasePrompt[State](myPrompt, nil),
    aix.WithGenerateOpts[State](
        ai.WithModelName("googleai/gemini-2.5-pro"), // Overrides prompt's model
    ),
)
```

---

## 4. Example Usage

### Basic Agent

```go
chatAgent := genkit.DefineAgent[ChatStatus, ChatState](g, "chatAgent",
    aix.WithGenerateOpts[ChatState](
        ai.WithModelName("googleai/gemini-3-flash"),
        ai.WithSystem("You are a helpful assistant."),
        ai.WithTools(myTool),
    ),
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
    ai.WithModelName("googleai/gemini-3-flash"),
    ai.WithSystem("You are a helpful coding assistant."),
    ai.WithTools(searchTool, calculatorTool),
)

assistantAgent := genkit.DefineAgent[Status, State](g, "assistant",
    aix.WithBasePrompt[State](assistantPrompt, nil),
)
```

### Agent with Initial Context

```go
// Initial messages are added to session once at start, then user inputs append
tutorAgent := genkit.DefineAgent[Status, State](g, "tutorAgent",
    aix.WithGenerateOpts[State](
        ai.WithModelName("googleai/gemini-3-flash"),
        ai.WithSystem("You are a coding tutor."),
        ai.WithMessages(
            ai.NewUserTextMessage("I'm learning Go and want to understand concurrency."),
            ai.NewModelTextMessage("Great! Go's concurrency model is one of its strengths. What would you like to start with?"),
        ),
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
    aix.WithGenerateOpts[State](
        ai.WithModelName("googleai/gemini-3-flash"),
        ai.WithSystem("Break down tasks into actionable steps."),
        ai.WithOutputType(TaskResponse{}),
    ),
)
```

### Agent with Snapshots

```go
store := aix.NewInMemorySnapshotStore[ChatState]()

chatAgent := genkit.DefineAgent[ChatStatus, ChatState](g, "chatAgent",
    aix.WithSnapshotStore(store),
    aix.WithGenerateOpts[ChatState](
        ai.WithModelName("googleai/gemini-3-flash"),
        ai.WithSystem("You are a helpful assistant."),
    ),
)
```

### Agent with Client-Provided Prompt Input

```go
type RoleInput struct {
    Role    string `json:"role"`
    Context string `json:"context"`
}

rolePrompt := genkit.DefineDataPrompt[RoleInput, string](g, "role",
    ai.WithSystem("You are a {{role}} assistant. Context: {{context}}"),
)

// No default input - client must provide
roleAgent := genkit.DefineAgent[Status, State](g, "roleAgent",
    aix.WithBasePrompt[State](rolePrompt, nil),
)

// Client provides input at session start
conn, _ := roleAgent.StreamBidi(ctx,
    aix.WithPromptInput(RoleInput{Role: "coding", Context: "helping with Go"}),
)
```

### Agent with Default Input and Optional Override

```go
// Agent with default input that clients can override
codeAgent := genkit.DefineAgent[Status, State](g, "codeAgent",
    aix.WithBasePrompt[State](rolePrompt, RoleInput{Role: "coding", Context: "general"}),
)

// Client can use default
conn1, _ := codeAgent.StreamBidi(ctx)

// Or override at session start
conn2, _ := codeAgent.StreamBidi(ctx,
    aix.WithPromptInput(RoleInput{Role: "coding", Context: "debugging a memory leak"}),
)
```

### Agent with Dynamic System Prompt (@state)

```go
// State that changes during conversation
type MoodState struct {
    UserMood    string `json:"userMood"`    // Updated by sentiment analysis tool
    TopicFocus  string `json:"topicFocus"`  // Updated as conversation evolves
}

// Prompt with @state variables - re-rendered each turn
moodPrompt := genkit.DefineDataPrompt[RoleInput, string](g, "moodAgent",
    ai.WithSystem(`You are a {{role}} assistant.
Current user mood: {{@state.userMood}}
Current topic: {{@state.topicFocus}}
Adjust your tone accordingly.`),
)

moodAgent := genkit.DefineAgent[Status, MoodState](g, "moodAgent",
    aix.WithBasePrompt[MoodState](moodPrompt, RoleInput{Role: "support"}),
    aix.WithGenerateOpts[MoodState](
        ai.WithTools(sentimentTool), // Tool that updates state.UserMood
    ),
)

// The system prompt is re-rendered each turn with current state values
```

---

## 5. Snapshot Behavior

### What Snapshots Contain

```go
// Snapshot stores SessionState, which includes:
type SessionState[State any] struct {
    Messages    []*ai.Message `json:"messages,omitempty"`    // Conversation only (no system messages)
    Custom      State         `json:"custom,omitempty"`      // User-defined state
    Artifacts   []*Artifact   `json:"artifacts,omitempty"`
    PromptInput any           `json:"promptInput,omitempty"` // For re-rendering prompt
}
```

### Restoring from Snapshot

When a session is restored from a snapshot:

1. Load `SessionState` from snapshot store
2. `PromptInput` is available for prompt re-rendering
3. Each turn re-renders entire prompt with stored PromptInput + current @state
4. Conversation continues from stored Messages

This approach ensures:
- Snapshots are compact (no prompt-rendered messages stored)
- `{{@state}}` always reflects current state, not stale snapshot values
- Prompt changes are picked up on restore (if prompt definition changed)

---

## 7. Files to Create/Modify

| File | Description |
|------|-------------|
| `go/ai/x/agent.go` | DefineAgent function |
| `go/ai/x/agent_options.go` | AgentOption interface and agent-specific options |
| `go/ai/x/session_flow_options.go` | Update snapshot options to return concrete types and implement AgentOption |
