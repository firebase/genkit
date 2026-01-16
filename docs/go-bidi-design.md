# Genkit Go Bidirectional Streaming Features - Design Document

## Overview

This document describes the design for bidirectional streaming features in Genkit Go. The implementation introduces three new primitives:

1. **BidiAction** - Core primitive for bidirectional operations
2. **BidiFlow** - BidiAction with observability, intended for user definition
3. **SessionFlow** - Stateful, multi-turn agent interactions with automatic persistence and turn semantics

## Package Location

All bidi types go in `go/core/x/` (experimental), which will move to `go/core/` when stabilized:

```
go/core/x/
├── bidi.go           # BidiActionDef, BidiFunc, BidiConnection
├── bidi_flow.go      # BidiFlow with tracing
├── bidi_options.go   # Option types for bidi
├── session_flow.go   # SessionFlow implementation
├── bidi_test.go      # Tests
```

High-level wrappers in `go/genkit/bidi.go`.

Import as `corex "github.com/firebase/genkit/go/core/x"`.

---

## 1. Core Type Definitions

### 1.1 BidiAction

```go
// BidiActionDef represents a bidirectional streaming action.
// Type parameters:
//   - In: Type of each message sent to the action
//   - Out: Type of the final output
//   - Init: Type of initialization data (use struct{} if not needed)
//   - Stream: Type of each streamed output chunk
type BidiActionDef[In, Out, Init, Stream any] struct {
    name     string
    fn       BidiFunc[In, Out, Init, Stream]
    registry api.Registry
    desc     *api.ActionDesc
}

// BidiFunc is the function signature for bidi actions.
type BidiFunc[In, Out, Init, Stream any] func(
    ctx context.Context,
    inputStream <-chan In,
    init Init,
    streamCallback core.StreamCallback[Stream],
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

// Stream returns an iterator for receiving streamed chunks.
// Each call returns a new iterator over the same underlying channel.
// Breaking out of the loop does NOT close the connection - you can call Stream()
// again to continue receiving. The iterator completes when the action finishes.
func (c *BidiConnection[In, Out, Stream]) Stream() iter.Seq2[Stream, error]

// Output returns the final output after the action completes.
// Blocks until done or context cancelled.
func (c *BidiConnection[In, Out, Stream]) Output() (Out, error)

// Done returns a channel closed when the connection completes.
func (c *BidiConnection[In, Out, Stream]) Done() <-chan struct{}
```

**Why iterators work for multi-turn:** Each call to `Stream()` returns an iterator over a new channel for that turn. When the agent finishes responding to an input (loops back to wait for the next input), the stream channel for that turn closes, causing the user's `for range` loop to exit naturally. Call `Stream()` again after sending the next input to get the next turn's response.

### 1.3 BidiFlow

```go
// BidiFlow wraps a BidiAction with flow semantics (tracing, monitoring).
type BidiFlow[In, Out, Init, Stream any] struct {
    *BidiActionDef[In, Out, Init, Stream]
    // Uses BidiActionDef.Name() for flow name - no separate field needed
}
```

### 1.4 SessionFlow

SessionFlow adds session state management on top of BidiFlow.

```go
// SessionFlowOutput wraps the output with session info for persistence.
type SessionFlowOutput[State, Out any] struct {
    SessionID string `json:"sessionId"`
    Output    Out    `json:"output"`
    State     State  `json:"state"`
}

// SessionFlow is a bidi flow with automatic session state management.
// Init = State: the initial state for new sessions (ignored when resuming an existing session).
type SessionFlow[State, In, Out, Stream any] struct {
    *BidiFlow[In, SessionFlowOutput[State, Out], State, Stream]
    store       session.Store[State]
    persistMode PersistMode
}

// SessionFlowFunc is the function signature for session flows.
type SessionFlowFunc[State, In, Out, Stream any] func(
    ctx context.Context,
    inputStream <-chan In,
    sess *session.Session[State],
    cb core.StreamCallback[Stream],
) (Out, error)

// PersistMode controls when session state is persisted.
type PersistMode int

const (
    PersistOnClose  PersistMode = iota // Persist only when connection closes (default)
    PersistOnUpdate                     // Persist after each input message is processed
)
```

**Turn semantics**: The `SessionStreamCallback` includes a `turnDone` parameter. When the agent finishes responding to an input message, it calls `cb(ctx, lastChunk, true)` to signal the turn is complete. This allows clients to know when to prompt for the next user message.

---

## 2. API Surface

### 2.1 Defining Bidi Actions

```go
// In go/core/x/bidi.go

// NewBidiAction creates a BidiAction without registering it.
func NewBidiAction[In, Out, Init, Stream any](
    name string,
    fn BidiFunc[In, Out, Init, Stream],
) *BidiActionDef[In, Out, Init, Stream]

// DefineBidiAction creates and registers a BidiAction.
func DefineBidiAction[In, Out, Init, Stream any](
    r api.Registry,
    name string,
    fn BidiFunc[In, Out, Init, Stream],
) *BidiActionDef[In, Out, Init, Stream]
```

Schemas for `In`, `Out`, `Init`, and `Stream` types are automatically inferred from the type parameters using the existing JSON schema inference in `go/internal/base/json.go`.

### 2.2 Defining Bidi Flows

```go
// In go/core/x/bidi_flow.go

func DefineBidiFlow[In, Out, Init, Stream any](
    r api.Registry,
    name string,
    fn BidiFunc[In, Out, Init, Stream],
) *BidiFlow[In, Out, Init, Stream]
```

### 2.3 Defining Session Flows

```go
// In go/core/x/session_flow.go

func DefineSessionFlow[State, In, Out, Stream any](
    r api.Registry,
    name string,
    fn SessionFlowFunc[State, In, Out, Stream],
    opts ...SessionFlowOption[State],
) *SessionFlow[State, In, Out, Stream]

// SessionFlowOption configures a SessionFlow.
type SessionFlowOption[State any] interface {
    applySessionFlow(*sessionFlowOptions[State]) error
}

func WithSessionStore[State any](store session.Store[State]) SessionFlowOption[State]
func WithPersistMode[State any](mode PersistMode) SessionFlowOption[State]
```

### 2.4 Starting Connections

All bidi types (BidiAction, BidiFlow, SessionFlow) use the same `StreamBidi` method to start connections:

```go
// BidiAction/BidiFlow
func (a *BidiActionDef[In, Out, Init, Stream]) StreamBidi(
    ctx context.Context,
    opts ...BidiOption[Init],
) (*BidiConnection[In, Out, Stream], error)

// BidiOption for streaming
type BidiOption[Init any] interface {
    applyBidi(*bidiOptions[Init]) error
}

func WithInit[Init any](init Init) BidiOption[Init]

// SessionFlow uses the same StreamBidi, with Init = State
// Additional option for session ID
func WithSessionID[Init any](id string) BidiOption[Init]

func (sf *SessionFlow[State, In, Out, Stream]) StreamBidi(
    ctx context.Context,
    opts ...BidiOption[State],
) (*BidiConnection[In, SessionFlowOutput[State, Out], Stream], error)
```

### 2.5 High-Level Genkit API

```go
// In go/genkit/bidi.go

func DefineBidiFlow[In, Out, Init, Stream any](
    g *Genkit,
    name string,
    fn corex.BidiFunc[In, Out, Init, Stream],
) *corex.BidiFlow[In, Out, Init, Stream]

func DefineSessionFlow[State, In, Out, Stream any](
    g *Genkit,
    name string,
    fn corex.SessionFlowFunc[State, In, Out, Stream],
    opts ...corex.SessionFlowOption[State],
) *corex.SessionFlow[State, In, Out, Stream]
```

---

## 3. Session Flow Details

### 3.1 Using StreamBidi with SessionFlow

SessionFlow uses the same `StreamBidi` method as BidiAction and BidiFlow. Session ID is a connection option, and initial state is passed via `WithInit`:

```go
// Define once at startup
chatAgent := genkit.DefineSessionFlow[ChatState, string, string, string](g, "chatAgent",
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

The SessionFlow internally handles session creation/loading:
- If `WithSessionID` is provided and session exists in store → load existing session (WithInit ignored)
- If `WithSessionID` is provided but session doesn't exist → create new session with that ID and initial state from WithInit
- If no `WithSessionID` → generate new UUID and create session with initial state from WithInit

The session ID is returned in `SessionFlowOutput.SessionID`, so callers can retrieve it from the final output:

```go
output, _ := conn.Output()
sessionID := output.SessionID  // Save this to resume later
```

### 3.2 State Persistence

Persistence mode is configurable:

```go
// Usage:
chatAgent := genkit.DefineSessionFlow[ChatState, string, string, string](g, "chatAgent",
    fn,
    corex.WithSessionStore(store),
    corex.WithPersistMode(corex.PersistOnUpdate), // or PersistOnClose (default)
)
```

- **PersistOnClose** (default): State is persisted only when the connection closes. Better performance.
- **PersistOnUpdate**: State is persisted after each input message is processed. More durable.

**Note**: `PersistOnUpdate` persists after each input from `inputStream` is processed, not on every `sess.UpdateState()` call. This covers the main use case (persist after each conversation turn) without requiring interface changes to `session.Session`.

---

## 4. Integration with Existing Infrastructure

### 4.1 Tracing Integration

BidiFlows create spans that remain open for the lifetime of the connection, enabling streaming trace visualization in the Dev UI.

```go
func (f *BidiFlow[In, Out, Init, Stream]) StreamBidi(
    ctx context.Context,
    opts ...BidiOption[Init],
) (*BidiConnection[In, Out, Stream], error) {
    // Inject flow context
    fc := &flowContext{flowName: f.Name()}
    ctx = flowContextKey.NewContext(ctx, fc)

    // Start span (NOT RunInNewSpan - we manage lifecycle manually)
    spanMeta := &tracing.SpanMetadata{
        Name:    f.Name(),
        Type:    "action",
        Subtype: "bidiFlow",
    }
    ctx, span := tracing.StartSpan(ctx, spanMeta)

    // Create connection, passing span for lifecycle management
    conn, err := f.BidiActionDef.streamBidiWithSpan(ctx, span, opts...)
    if err != nil {
        span.End()  // End span on error
        return nil, err
    }
    return conn, nil
}

// Inside BidiConnection, the span is ended when the action completes:
func (c *BidiConnection[...]) run() {
    defer c.span.End()  // End span when bidi flow completes

    // Run the action, recording events/nested spans as needed
    output, err := c.fn(c.ctx, c.inputCh, c.init, c.streamCallback)
    // ...
}
```

**Important**: The span stays open while the connection is active, allowing:
- Streaming traces to the Dev UI in real-time
- Nested spans for sub-operations (e.g., each LLM call)
- Events recorded as they happen

### 4.2 Action Registration

Add new action type:

```go
// In go/core/api/action.go
const (
    ActionTypeBidiFlow ActionType = "bidi-flow"
)
```

### 4.3 Session Integration

Use existing `Session` and `Store` types from `go/core/x/session` (remains a separate subpackage):

```go
import "github.com/firebase/genkit/go/core/x/session"

// SessionFlow holds reference to session store
type SessionFlow[State, In, Out, Stream any] struct {
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

    "github.com/firebase/genkit/go/core"
    "github.com/firebase/genkit/go/genkit"
)

func main() {
    ctx := context.Background()
    g := genkit.Init(ctx)

    // Define echo bidi flow (low-level, no turn semantics)
    echoFlow := genkit.DefineBidiFlow[string, string, struct{}, string](g, "echo",
        func(ctx context.Context, inputStream <-chan string, init struct{}, cb core.StreamCallback[string]) (string, error) {
            var count int
            for input := range inputStream {
                count++
                if err := cb(ctx, fmt.Sprintf("echo: %s", input)); err != nil {
                    return "", err
                }
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
    for chunk, err := range conn.Stream() {
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
    "github.com/firebase/genkit/go/core"
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

    // Define a session flow for multi-turn chat
    chatAgent := genkit.DefineSessionFlow[ChatState, string, string, string](g, "chatAgent",
        func(ctx context.Context, inputStream <-chan string, sess *session.Session[ChatState], cb core.StreamCallback[string]) (string, error) {
            state := sess.State()
            messages := state.Messages

            for userInput := range inputStream {
                messages = append(messages, ai.NewUserTextMessage(userInput))

                var responseText string
                for result, err := range genkit.GenerateStream(ctx, g,
                    ai.WithMessages(messages...),
                ) {
                    if err != nil {
                        return "", err
                    }
                    if result.Done {
                        responseText = result.Response.Text()
                    }
                    cb(ctx, result.Chunk.Text())
                }
                // Stream channel closes here when we loop back to wait for next input

                messages = append(messages, ai.NewModelTextMessage(responseText))
                sess.UpdateState(ctx, ChatState{Messages: messages})
            }

            return "conversation ended", nil
        },
        corex.WithSessionStore(store),
        corex.WithPersistMode(corex.PersistOnClose),
    )

    // Start new session (generates new session ID)
    conn, _ := chatAgent.StreamBidi(ctx)

    // First turn
    conn.Send("Hello! Tell me about Go programming.")
    for chunk, err := range conn.Stream() {
        if err != nil {
            panic(err)
        }
        fmt.Print(chunk)
    }
    // Loop exits when stream closes (agent finished responding)

    // Second turn - call Stream() again for next response
    conn.Send("What are channels used for?")
    for chunk, err := range conn.Stream() {
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

configuredChat := genkit.DefineBidiFlow[string, string, ChatInit, string](g, "configuredChat",
    func(ctx context.Context, inputStream <-chan string, init ChatInit, cb core.StreamCallback[string]) (string, error) {
        // Use init.SystemPrompt and init.Temperature
        for input := range inputStream {
            resp, _ := genkit.GenerateText(ctx, g,
                ai.WithSystem(init.SystemPrompt),
                ai.WithConfig(&genai.GenerateContentConfig{Temperature: &init.Temperature}),
                ai.WithPrompt(input),
            )
            cb(ctx, resp)
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
| `go/core/x/bidi.go` | BidiActionDef, BidiFunc, BidiConnection |
| `go/core/x/bidi_flow.go` | BidiFlow with tracing |
| `go/core/x/bidi_options.go` | BidiOption types |
| `go/core/x/session_flow.go` | SessionFlow implementation |
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
- This provides natural backpressure: `Send()` blocks until agent reads, `cb()` blocks until user consumes
- If needed, a `WithInputBufferSize` option could be added later for specific use cases

### Iterator Implementation and Turn Semantics
- `Stream()` returns `iter.Seq2[Stream, error]` - a Go 1.23 iterator
- Each call to `Stream()` returns an iterator over a **new channel** for that turn
- When the agent finishes responding (loops back to wait for next input), the stream channel closes
- The user's `for range` loop exits naturally when the channel closes
- Call `Stream()` again after sending the next input to get the next turn's response
- The iterator yields `(chunk, nil)` for each streamed value
- On error, the iterator yields `(zero, err)` and stops

### Tracing
- Span is started when connection is created, ended when action completes
- Nested spans work normally within the bidi function
- Events can be recorded throughout the connection lifecycle
- Dev UI can show traces in real-time as they stream
