# Genkit Go Bidirectional Streaming Features - Design Document

## Overview

This document describes the design for bidirectional streaming features in Genkit Go. The implementation introduces three new primitives:

1. **BidiAction** - Core primitive for bidirectional operations
2. **BidiFlow** - BidiAction with observability, intended for user definition
3. **Agent** - Stateful, multi-turn agent interactions with automatic persistence and turn semantics

## Package Location

All bidi types go in `go/core/x/` (experimental), which will move to `go/core/` when stabilized:

```
go/core/x/
├── bidi.go           # BidiAction, BidiFunc, BidiConnection
├── bidi_flow.go      # BidiFlow
├── agent.go          # Agent implementation
├── option.go         # Options
├── bidi_test.go      # Tests
```

Import as `corex "github.com/firebase/genkit/go/core/x"`.

---

## 1. Core Type Definitions

### 1.1 BidiAction

```go
// BidiAction represents a bidirectional streaming action.
// Type parameters:
//   - Init: Type of initialization data (use struct{} if not needed)
//   - In: Type of each message sent to the action
//   - Out: Type of the final output
//   - Stream: Type of each streamed output chunk
type BidiAction[Init, In, Out, Stream any] struct {
    name     string
    fn       BidiFunc[Init, In, Out, Stream]
    registry api.Registry
    desc     *api.ActionDesc
}

// BidiFunc is the function signature for bidi actions.
type BidiFunc[Init, In, Out, Stream any] func(
    ctx context.Context,
    init Init,
    inCh <-chan In,
    outCh chan<- Stream,
) (Out, error)
```

### 1.2 BidiConnection

```go
// BidiConnection represents an active bidirectional streaming session.
type BidiConnection[In, Out, Stream any] struct {
    inputCh  chan In                     // Internal, accessed via Send()
    streamCh chan Stream                 // Internal output stream channel
    doneCh   chan struct{}               // Closed when action completes
    output   Out                         // Final output (valid after done)
    err      error                       // Error if any (valid after done)
    ctx      context.Context
    cancel   context.CancelFunc
    span     tracing.Span               // Trace span, ended on completion
    mu       sync.Mutex
    closed   bool
}

// Send sends an input message to the bidi action.
func (c *BidiConnection[In, Out, Stream]) Send(input In) error

// Close signals that no more inputs will be sent.
func (c *BidiConnection[In, Out, Stream]) Close() error

// Responses returns an iterator for receiving streamed response chunks.
// For Agents, the iterator exits when the agent calls resp.EndTurn(), allowing
// multi-turn conversations. Call Responses() again after Send() for the next turn.
// The iterator completes permanently when the action finishes.
func (c *BidiConnection[In, Out, Stream]) Responses() iter.Seq2[Stream, error]

// Output returns the final output after the action completes.
// Blocks until done or context cancelled.
func (c *BidiConnection[In, Out, Stream]) Output() (Out, error)

// Done returns a channel closed when the connection completes.
func (c *BidiConnection[In, Out, Stream]) Done() <-chan struct{}
```

### 1.3 BidiFlow

```go
type BidiFlow[Init, In, Out, Stream any] struct {
    *BidiAction[Init, In, Out, Stream]
}
```

### 1.4 Responder

`Responder` wraps the output channel for agents, providing methods to send data and signal turn boundaries.

```go
// Responder wraps the output channel with turn signaling for multi-turn agents.
type Responder[T any] struct {
    ch chan<- streamChunk[T]  // internal, unexported
}

// Send sends a streamed chunk to the consumer.
func (r *Responder[T]) Send(data T)

// EndTurn signals that the agent has finished responding to the current input.
// The consumer's Stream() iterator will exit, allowing them to send the next input.
func (r *Responder[T]) EndTurn()
```

### 1.5 Agent

Agent adds session state management on top of BidiFlow with turn semantics.

```go
// Artifact represents a named collection of parts produced during a session.
// Examples: generated files, images, code snippets, etc.
type Artifact struct {
    Name  string     `json:"name"`
    Parts []*ai.Part `json:"parts"`
}

// AgentOutput wraps the output with session info for persistence.
type AgentOutput[State, Out any] struct {
    SessionID string     `json:"sessionId"`
    Output    Out        `json:"output"`
    State     State      `json:"state"`
    Artifacts []Artifact `json:"artifacts,omitempty"`
}

// Agent is a bidi flow with automatic session state management.
// Init = State: the initial state for new sessions (ignored when resuming an existing session).
type Agent[State, In, Out, Stream any] struct {
    *BidiFlow[State, In, AgentOutput[State, Out], Stream]
    store session.Store[State]
}

// AgentResult is the return type for agent functions.
type AgentResult[Out any] struct {
    Output    Out
    Artifacts []Artifact
}

// AgentFunc is the function signature for agents.
type AgentFunc[State, In, Out, Stream any] func(
    ctx context.Context,
    sess *session.Session[State],
    inCh <-chan In,
    resp *Responder[Stream],
) (AgentResult[Out], error)
```

---

## 2. API Surface

### 2.1 Defining Bidi Actions

```go
// In go/core/x/bidi.go

// NewBidiAction creates a BidiAction without registering it.
func NewBidiAction[Init, In, Out, Stream any](
    name string,
    fn BidiFunc[Init, In, Out, Stream],
) *BidiAction[Init, In, Out, Stream]

// DefineBidiAction creates and registers a BidiAction.
func DefineBidiAction[Init, In, Out, Stream any](
    r api.Registry,
    name string,
    fn BidiFunc[Init, In, Out, Stream],
) *BidiAction[Init, In, Out, Stream]
```

Schemas for `In`, `Out`, `Init`, and `Stream` types are automatically inferred from the type parameters using the existing JSON schema inference in `go/internal/base/json.go`.

### 2.2 Defining Bidi Flows

```go
// In go/core/x/bidi_flow.go

// DefineBidiFlow creates a BidiFlow with tracing and registers it.
// Use this for user-defined bidirectional streaming operations.
func DefineBidiFlow[Init, In, Out, Stream any](
    r api.Registry,
    name string,
    fn BidiFunc[Init, In, Out, Stream],
) *BidiFlow[Init, In, Out, Stream]
```

### 2.3 Defining Agents

```go
// In go/core/x/agent.go

// DefineAgent creates an Agent with automatic session management and registers it.
// Use this for multi-turn conversational agents that need to persist state across turns.
func DefineAgent[State, In, Out, Stream any](
    r api.Registry,
    name string,
    fn AgentFunc[State, In, Out, Stream],
    opts ...AgentOption[State],
) *Agent[State, In, Out, Stream]

// AgentOption configures an Agent.
type AgentOption[State any] interface {
    applyAgent(*agentOptions[State]) error
}

// WithSessionStore sets the session store for persisting session state.
// If not provided, sessions exist only in memory for the connection lifetime.
func WithSessionStore[State any](store session.Store[State]) AgentOption[State]
```

### 2.4 Starting Connections

All bidi types (BidiAction, BidiFlow, Agent) use the same `StreamBidi` method to start connections:

```go
// BidiAction/BidiFlow
func (a *BidiAction[Init, In, Out, Stream]) StreamBidi(
    ctx context.Context,
    opts ...BidiOption[Init],
) (*BidiConnection[In, Out, Stream], error)

// BidiOption configures a bidi connection.
type BidiOption[Init any] interface {
    applyBidi(*bidiOptions[Init]) error
}

// WithInit provides initialization data for the bidi action.
// For Agent, this sets the initial state for new sessions.
func WithInit[Init any](init Init) BidiOption[Init]

// WithSessionID specifies an existing session ID to resume.
// If the session exists in the store, it is loaded (WithInit is ignored).
// If the session doesn't exist, a new session is created with this ID.
// If not provided, a new UUID is generated for new sessions.
func WithSessionID[Init any](id string) BidiOption[Init]

func (a *Agent[State, In, Out, Stream]) StreamBidi(
    ctx context.Context,
    opts ...BidiOption[State],
) (*BidiConnection[In, AgentOutput[State, Out], Stream], error)
```

### 2.5 High-Level Genkit API

```go
// In go/genkit/bidi.go

func DefineBidiFlow[Init, In, Out, Stream any](
    g *Genkit,
    name string,
    fn corex.BidiFunc[Init, In, Out, Stream],
) *corex.BidiFlow[Init, In, Out, Stream]

func DefineAgent[State, In, Out, Stream any](
    g *Genkit,
    name string,
    fn corex.AgentFunc[State, In, Out, Stream],
    opts ...corex.AgentOption[State],
) *corex.Agent[State, In, Out, Stream]
```

---

## 3. Agent Details

### 3.1 Using StreamBidi with Agent

Agent uses the same `StreamBidi` method as BidiAction and BidiFlow. Session ID is a connection option, and initial state is passed via `WithInit`:

```go
// Define once at startup
chatAgent := genkit.DefineAgent(g, "chatAgent",
    myAgentFunc,
    corex.WithSessionStore(store),
)

// NEW USER: Start fresh session (generates new ID, zero state)
conn1, _ := chatAgent.StreamBidi(ctx)

// RETURNING USER: Resume existing session by ID
conn2, _ := chatAgent.StreamBidi(ctx, corex.WithSessionID[ChatState]("user-123-session"))

// NEW USER WITH INITIAL STATE: Start with pre-populated state
conn3, _ := chatAgent.StreamBidi(ctx, corex.WithInit(ChatState{Messages: preloadedHistory}))

// NEW USER WITH SPECIFIC ID AND INITIAL STATE
conn4, _ := chatAgent.StreamBidi(ctx,
    corex.WithSessionID[ChatState]("custom-session-id"),
    corex.WithInit(ChatState{Messages: preloadedHistory}),
)
```

The Agent internally handles session creation/loading:
- If `WithSessionID` is provided and session exists in store → load existing session (WithInit ignored)
- If `WithSessionID` is provided but session doesn't exist → create new session with that ID and initial state from WithInit
- If no `WithSessionID` → generate new UUID and create session with initial state from WithInit

The session ID is returned in `AgentOutput.SessionID`, so callers can retrieve it from the final output:

```go
output, _ := conn.Output()
sessionID := output.SessionID  // Save this to resume later
```

### 3.2 State Persistence

State is persisted automatically when `sess.UpdateState()` is called - the existing `session.Session` implementation already persists to the configured store. No special persistence mode is needed; the user controls when to persist by calling `UpdateState()`.

---

## 4. Integration with Existing Infrastructure

### 4.1 Tracing Integration

BidiFlows create spans that remain open for the lifetime of the connection, enabling streaming trace visualization in the Dev UI.

**Key behaviors:**
- Span starts when `StreamBidi()` is called
- Span ends when the bidi function returns (via `defer` in the connection goroutine)
- Flow context is injected so `core.Run()` works inside the bidi function
- Nested spans for sub-operations (e.g., each LLM call) work normally

**Important**: The span stays open while the connection is active, allowing:
- Streaming traces to the Dev UI in real-time
- Nested spans for sub-operations (e.g., each LLM call)
- Events recorded as they happen

### 4.2 Action Registration

Add new action type and schema fields:

```go
// In go/core/api/action.go
const (
    ActionTypeBidiFlow ActionType = "bidi-flow"
)

// ActionDesc gets two new optional fields
type ActionDesc struct {
    // ... existing fields ...
    StreamSchema map[string]any `json:"streamSchema,omitempty"` // NEW: schema for streamed chunks
    InitSchema   map[string]any `json:"initSchema,omitempty"`   // NEW: schema for initialization data
}
```

### 4.3 Session Integration

Use existing `Session` and `Store` types from `go/core/x/session` (remains a separate subpackage):

```go
import "github.com/firebase/genkit/go/core/x/session"

// Agent holds reference to session store
type Agent[State, In, Out, Stream any] struct {
    store session.Store[State]
    // ...
}
```

---

## 5. Example Usage

### 5.1 Basic Echo Bidi Flow

```go
package main

import (
    "context"
    "fmt"

    "github.com/firebase/genkit/go/genkit"
)

func main() {
    ctx := context.Background()
    g := genkit.Init(ctx)

    // Define echo bidi flow (low-level, no turn semantics)
    echoFlow := genkit.DefineBidiFlow(g, "echo",
        func(ctx context.Context, init struct{}, inCh <-chan string, outCh chan<- string) (string, error) {
            var count int
            for input := range inCh {
                count++
                outCh <- fmt.Sprintf("echo: %s", input)
            }
            return fmt.Sprintf("processed %d messages", count), nil
        },
    )

    // Start streaming connection
    conn, err := echoFlow.StreamBidi(ctx)
    if err != nil {
        panic(err)
    }

    // Send messages
    conn.Send("hello")
    conn.Send("world")
    conn.Close()

    // Consume stream via iterator
    for chunk, err := range conn.Responses() {
        if err != nil {
            panic(err)
        }
        fmt.Println(chunk) // "echo: hello", "echo: world"
    }

    // Get final output
    output, _ := conn.Output()
    fmt.Println(output) // "processed 2 messages"
}
```

### 5.2 Chat Agent with Session Persistence

```go
package main

import (
    "context"
    "fmt"

    "github.com/firebase/genkit/go/ai"
    corex "github.com/firebase/genkit/go/core/x"
    "github.com/firebase/genkit/go/core/x/session"
    "github.com/firebase/genkit/go/genkit"
    "github.com/firebase/genkit/go/plugins/googlegenai"
)

type ChatState struct {
    Messages []*ai.Message `json:"messages"`
}

func main() {
    ctx := context.Background()
    store := session.NewInMemoryStore[ChatState]()

    g := genkit.Init(ctx,
        genkit.WithPlugins(&googlegenai.GoogleAI{}),
        genkit.WithDefaultModel("googleai/gemini-2.5-flash"),
    )

    // Define an agent for multi-turn chat
    chatAgent := genkit.DefineAgent(g, "chatAgent",
        func(ctx context.Context, sess *session.Session[ChatState], inCh <-chan string, resp *corex.Responder[string]) (corex.AgentResult[string], error) {
            state := sess.State()
            messages := state.Messages

            for userInput := range inCh {
                messages = append(messages, ai.NewUserTextMessage(userInput))

                var respText string
                for result, err := range genkit.GenerateStream(ctx, g,
                    ai.WithMessages(messages...),
                ) {
                    if err != nil {
                        return corex.AgentResult[string]{}, err
                    }
                    if result.Done {
                        respText = result.Response.Text()
                    }
                    resp.Send(result.Chunk.Text())
                }
                resp.EndTurn()  // Signal turn complete, consumer's Stream() exits

                messages = append(messages, ai.NewModelTextMessage(respText))
                sess.UpdateState(ctx, ChatState{Messages: messages})
            }

            return corex.AgentResult[string]{
                Output:    "conversation ended",
                Artifacts: []corex.Artifact{
                    {
                        Name:  "summary",
                        Parts: []*ai.Part{ai.NewTextPart("...")},
                    },
                },
            }, nil
        },
        corex.WithSessionStore(store),
    )

    // Start new session (generates new session ID)
    conn, _ := chatAgent.StreamBidi(ctx)

    // First turn
    conn.Send("Hello! Tell me about Go programming.")
    for chunk, err := range conn.Responses() {
        if err != nil {
            panic(err)
        }
        fmt.Print(chunk)
    }
    // Loop exits when agent calls resp.EndTurn()

    // Second turn
    conn.Send("What are channels used for?")
    for chunk, err := range conn.Responses() {
        if err != nil {
            panic(err)
        }
        fmt.Print(chunk)
    }

    conn.Close()

    // Get session ID from final output to resume later
    output, _ := conn.Output()
    sessionID := output.SessionID

    // Resume session later with the saved ID
    conn2, _ := chatAgent.StreamBidi(ctx, corex.WithSessionID[ChatState](sessionID))
    conn2.Send("Continue our discussion")
    // ...
}
```

### 5.3 Bidi Flow with Initialization Data

```go
type ChatInit struct {
    SystemPrompt string  `json:"systemPrompt"`
    Temperature  float64 `json:"temperature"`
}

configuredChat := genkit.DefineBidiFlow(g, "configuredChat",
    func(ctx context.Context, init ChatInit, inCh <-chan string, outCh chan<- string) (string, error) {
        // Use init.SystemPrompt and init.Temperature
        for input := range inCh {
            resp, _ := genkit.GenerateText(ctx, g,
                ai.WithSystem(init.SystemPrompt),
                ai.WithConfig(&genai.GenerateContentConfig{Temperature: &init.Temperature}),
                ai.WithPrompt(input),
            )
            outCh <- resp
        }
        return "done", nil
    },
)

conn, _ := configuredChat.StreamBidi(ctx,
    corex.WithInit(ChatInit{
        SystemPrompt: "You are a helpful assistant.",
        Temperature:  0.7,
    }),
)
```

---

## 6. Files to Create/Modify

### New Files

| File | Description |
|------|-------------|
| `go/core/x/bidi.go` | BidiAction, BidiFunc, BidiConnection |
| `go/core/x/bidi_flow.go` | BidiFlow with tracing |
| `go/core/x/bidi_options.go` | BidiOption types |
| `go/core/x/agent.go` | Agent implementation |
| `go/core/x/bidi_test.go` | Tests |
| `go/genkit/bidi.go` | High-level API wrappers |

### Modified Files

| File | Change |
|------|--------|
| `go/core/api/action.go` | Add `ActionTypeBidiFlow` constant |

---

## 7. Implementation Notes

### Error Handling
- Errors from the bidi function propagate to both `Stream()` iterator and `Output()`
- Context cancellation closes all channels and terminates the action
- Send after Close returns an error
- Errors are yielded as the second value in the `iter.Seq2[Stream, error]` iterator

### Goroutine Management
- BidiConnection spawns a goroutine to run the action
- Proper cleanup on context cancellation using `defer` and `sync.Once`
- Channel closure follows Go idioms (sender closes)
- Trace span is ended in the goroutine's defer

### Thread Safety
- BidiConnection uses mutex for state (closed flag)
- Send is safe to call from multiple goroutines
- Session operations are thread-safe (from existing session package)

### Channels and Backpressure
- Both input and output channels are **unbuffered** by default (size 0)
- This provides natural backpressure: `Send()` blocks until agent reads, `resp.Send()` blocks until consumer reads
- If needed, `WithInputBufferSize` / `WithOutputBufferSize` options could be added later for specific use cases

### Turn Signaling (Agents)

For multi-turn conversations, the consumer needs to know when the agent has finished responding to one input and is ready for the next.

**How it works internally:**

1. `BidiConnection.streamCh` is actually `chan streamChunk[Stream]` (internal type)
2. `streamChunk` has `data T` and `endTurn bool` fields (unexported)
3. `resp.Send(data)` sends `streamChunk{data: data}`
4. `resp.EndTurn()` sends `streamChunk{endTurn: true}`
5. `conn.Responses()` unwraps chunks, yielding only the data
6. When `Stream()` sees `endTurn: true`, it exits the iterator without yielding

**From the agent's perspective:**
```go
for input := range inCh {
    resp.Send("partial...")
    resp.Send("more...")
    resp.EndTurn()  // Consumer's for loop exits here
}
```

**From the consumer's perspective:**
```go
conn.Send("question")
for chunk, err := range conn.Responses() {
    fmt.Print(chunk)  // Just gets string, not streamChunk
}
// Loop exited because agent called EndTurn()

conn.Send("follow-up")
for chunk, err := range conn.Responses() { ... }
```

### Tracing
- Span is started when connection is created, ended when action completes
- Nested spans work normally within the bidi function
- Events can be recorded throughout the connection lifecycle
- Dev UI can show traces in real-time as they stream
- Implementation uses the existing tracer infrastructure (details left to implementation)

### Shutdown Sequence
When `Close()` is called on a BidiConnection:
1. The input channel is closed, signaling no more inputs
2. The bidi function's `for range inputStream` loop exits
3. The function returns its final output
4. The stream channel is closed
5. The `Done()` channel is closed
6. `Output()` unblocks and returns the result

On context cancellation:
1. Context error propagates to the bidi function
2. All channels are closed
3. `Output()` returns the context error

### Agent Internal Wrapping
The user's `AgentFunc` returns `AgentResult[Out]`, but `Agent.StreamBidi()` returns `AgentOutput[State, Out]`. Internally, Agent wraps the user function:

```go
// Simplified internal logic
result, err := userFunc(ctx, wrappedInCh, outCh, sess)
if err != nil {
    return AgentOutput[State, Out]{}, err
}
return AgentOutput[State, Out]{
    SessionID: sess.ID(),
    Output:    result.Output,
    State:     sess.State(),
    Artifacts: result.Artifacts,
}, nil
```

