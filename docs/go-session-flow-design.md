# Genkit Go Session Flow - Design Document

## Overview

This document describes the design for the Session Flow API in Genkit Go. A Session Flow is a stateful, multi-turn conversational flow with automatic snapshot persistence and turn semantics.

Session Flows provide:
- **State encapsulation**: Messages, user-defined state, and artifacts in a single serializable unit
- **Resumability**: Start new invocations from any previous snapshot
- **Flexibility**: Support for both client-managed and server-managed state patterns
- **Streaming**: Token-level streaming via bidirectional connections
- **Debugging**: Point-in-time state capture for inspection and replay

Two entry points:
- `DefineSessionFlow` for full control over the generate loop
- `DefineSessionFlowFromPrompt` for prompt-backed flows with an automatic conversation loop

This design builds on the bidirectional streaming primitives described in [go-bidi-design.md](go-bidi-design.md).

## Package Location

Session Flow is an AI concept and lives in `go/ai/exp/` (experimental):

```
go/ai/exp/
├── gen.go                  # Generated wire types (SessionFlowInit, SessionFlowInput, SessionFlowOutput, etc.)
├── option.go               # SessionFlowOption, InvocationOption
├── session.go              # Session, SessionStore, SessionSnapshot, context helpers
├── session_flow.go         # SessionFlow, SessionFlowFunc, SessionRunner, Responder, DefineSessionFlow, DefineSessionFlowFromPrompt
├── session_flow_test.go    # Tests
```

Import as `aix "github.com/firebase/genkit/go/ai/exp"`.

High-level wrappers in `go/genkit/genkit.go`:
```go
genkit.DefineSessionFlow(g, ...)
genkit.DefineSessionFlowFromPrompt(g, ...)
```

---

## 1. Core Type Definitions

### 1.1 State and Snapshot Types

**SessionState** is the portable state that flows between client and server. It contains only the data needed for conversation continuity.

**SessionSnapshot** is a persisted point-in-time capture with metadata. It wraps SessionState with additional fields for storage, debugging, and restoration.

```go
// SessionState is the portable conversation state that flows between client
// and server. It contains only the data needed for conversation continuity.
type SessionState[State any] struct {
    // Messages is the conversation history (user/model exchanges).
    // Does NOT include prompt-rendered messages -- those are rendered fresh each turn.
    Messages []*ai.Message `json:"messages,omitempty"`
    // Custom is the user-defined state associated with this conversation.
    Custom State `json:"custom,omitempty"`
    // Artifacts are named collections of parts produced during the conversation.
    Artifacts []*Artifact `json:"artifacts,omitempty"`
    // InputVariables is the input used for session flows that require input variables
    // (e.g., prompt-backed session flows).
    InputVariables any `json:"inputVariables,omitempty"`
}

// SessionSnapshot is a persisted point-in-time capture of session state.
type SessionSnapshot[State any] struct {
    // SnapshotID is the unique identifier for this snapshot (UUID).
    SnapshotID string `json:"snapshotId"`
    // ParentID is the ID of the previous snapshot in this timeline.
    ParentID string `json:"parentId,omitempty"`
    // CreatedAt is when the snapshot was created.
    CreatedAt time.Time `json:"createdAt"`
    // Event is what triggered this snapshot.
    Event SnapshotEvent `json:"event"`
    // State is the actual conversation state.
    State SessionState[State] `json:"state"`
}

// Artifact represents a named collection of parts produced during a session.
// Examples: generated files, images, code snippets, diagrams, etc.
type Artifact struct {
    // Name identifies the artifact (e.g., "generated_code.go", "diagram.png").
    Name string `json:"name,omitempty"`
    // Parts contains the artifact content (text, media, etc.).
    Parts []*ai.Part `json:"parts"`
    // Metadata contains additional artifact-specific data.
    Metadata map[string]any `json:"metadata,omitempty"`
}
```

### 1.2 Input/Output Types

```go
// SessionFlowInit is the input for starting a session flow invocation.
// Provide either SnapshotID (to load from store) or State (direct state).
type SessionFlowInit[State any] struct {
    // SnapshotID loads state from a persisted snapshot.
    // Mutually exclusive with State.
    SnapshotID string `json:"snapshotId,omitempty"`
    // State provides direct state for the invocation.
    // Mutually exclusive with SnapshotID.
    State *SessionState[State] `json:"state,omitempty"`
}

// SessionFlowInput is the input sent to a session flow during a conversation turn.
type SessionFlowInput struct {
    // Messages contains the user's input for this turn.
    Messages []*ai.Message `json:"messages,omitempty"`
    // ToolRestarts contains tool request parts to re-execute interrupted tools.
    // Use ai.ToolDef.RestartWith to create these parts from an interrupted
    // tool request. When set, the generate call resumes with these restarts
    // instead of treating Messages as tool responses.
    ToolRestarts []*ai.Part `json:"toolRestarts,omitempty"`
}

// SessionFlowOutput is the output when a session flow invocation completes.
// It wraps SessionFlowResult with framework-managed fields.
type SessionFlowOutput[State any] struct {
    // Artifacts contains artifacts produced during the session.
    Artifacts []*Artifact `json:"artifacts,omitempty"`
    // Message is the last model response message from the conversation.
    Message *ai.Message `json:"message,omitempty"`
    // SnapshotID is the ID of the snapshot created at the end of this invocation.
    // Empty if no snapshot was created (callback returned false or no store configured).
    SnapshotID string `json:"snapshotId,omitempty"`
    // State contains the final conversation state.
    // Only populated when state is client-managed (no store configured).
    State *SessionState[State] `json:"state,omitempty"`
}

// SessionFlowResult is the return value from a SessionFlowFunc.
// It contains the user-specified outputs of the session invocation.
type SessionFlowResult struct {
    // Artifacts contains artifacts produced during the session.
    Artifacts []*Artifact `json:"artifacts,omitempty"`
    // Message is the last model response message from the conversation.
    Message *ai.Message `json:"message,omitempty"`
}
```

### 1.3 Stream Types

```go
// SessionFlowStreamChunk represents a single item in the session flow's output stream.
type SessionFlowStreamChunk[Stream any] struct {
    // ModelChunk contains generation tokens from the model.
    ModelChunk *ai.ModelResponseChunk `json:"modelChunk,omitempty"`
    // Status contains user-defined structured status information.
    // The Stream type parameter defines the shape of this data.
    Status Stream `json:"status,omitempty"`
    // Artifact contains a newly produced artifact.
    Artifact *Artifact `json:"artifact,omitempty"`
    // SnapshotID contains the ID of a snapshot that was just persisted.
    SnapshotID string `json:"snapshotId,omitempty"`
    // EndTurn signals that the session flow has finished processing the current input.
    // When true, the client should stop iterating and may send the next input.
    EndTurn bool `json:"endTurn,omitempty"`
}
```

### 1.4 Snapshot Events

```go
// SnapshotEvent identifies what triggered a snapshot.
type SnapshotEvent string

const (
    // SnapshotEventTurnEnd indicates the snapshot was triggered at the end of a turn.
    SnapshotEventTurnEnd SnapshotEvent = "turnEnd"
    // SnapshotEventInvocationEnd indicates the snapshot was triggered at the end of the invocation.
    SnapshotEventInvocationEnd SnapshotEvent = "invocationEnd"
)
```

---

## 2. Session

Session holds conversation state and provides thread-safe read/write access to messages, input variables, custom state, and artifacts. It is propagated via context so that nested operations (tools, sub-flows) can access consistent state.

```go
type Session[State any] struct {
    mu      sync.RWMutex
    state   SessionState[State]
    store   SessionStore[State]
    version uint64 // incremented on every mutation; used to skip redundant snapshots
}

// State returns a deep copy of the current state.
func (s *Session[State]) State() *SessionState[State]

// Conversation history
func (s *Session[State]) Messages() []*ai.Message
func (s *Session[State]) AddMessages(messages ...*ai.Message)
func (s *Session[State]) SetMessages(messages []*ai.Message)
func (s *Session[State]) UpdateMessages(fn func([]*ai.Message) []*ai.Message)

// Custom state
func (s *Session[State]) Custom() State
func (s *Session[State]) UpdateCustom(fn func(State) State)

// Input variables (prompt-backed flows)
func (s *Session[State]) InputVariables() any

// Artifacts
func (s *Session[State]) Artifacts() []*Artifact
func (s *Session[State]) AddArtifacts(artifacts ...*Artifact)
func (s *Session[State]) UpdateArtifacts(fn func([]*Artifact) []*Artifact)

// Context helpers
func NewSessionContext[State any](ctx context.Context, s *Session[State]) context.Context
func SessionFromContext[State any](ctx context.Context) *Session[State]
```

`UpdateCustom`, `UpdateMessages`, and `UpdateArtifacts` use an update-function pattern for atomic read-modify-write under the lock.

`AddArtifacts` replaces any existing artifact with the same name.

---

## 3. SessionRunner

SessionRunner extends Session with turn management and snapshot persistence. It is passed as the `sess` parameter to `SessionFlowFunc`.

```go
// SessionRunner extends Session with session-flow-specific functionality:
// turn management, snapshot persistence, and input channel handling.
type SessionRunner[State any] struct {
    *Session[State]

    // InputCh is the channel that delivers per-turn inputs from the client.
    // It is consumed automatically by SessionRunner.Run, but is exposed
    // for advanced use cases that need direct access to the input stream.
    InputCh <-chan *SessionFlowInput
    // TurnIndex is the zero-based index of the current conversation turn.
    // It is incremented automatically by SessionRunner.Run.
    TurnIndex int
}
```

### SessionRunner.Run

`Run` owns the input loop. For each input received from the channel:

1. Create a trace span (`sessionFlow/turn/{turnIndex}`) with input as the span input
2. Add input messages to session
3. Call the user's turn function with the span context
4. On success: trigger snapshot check, send `EndTurn` chunk, increment turn index
5. On error: record error on span and return

```go
func (a *SessionRunner[State]) Run(
    ctx context.Context,
    fn func(ctx context.Context, input *SessionFlowInput) error,
) error
```

### SessionRunner.Result

Returns a `SessionFlowResult` populated from the current session state: the last message in the conversation history and all artifacts. Convenience for custom session flows that don't need to construct the result manually.

```go
func (a *SessionRunner[State]) Result() *SessionFlowResult
```

---

## 4. Responder

Responder is the output channel for a session flow. It is a typed channel with convenience methods. Artifacts sent through it are automatically added to the session before being forwarded to the client (handled by an intermediary goroutine in the framework).

```go
// Responder is a typed output channel.
type Responder[Stream any] chan<- *SessionFlowStreamChunk[Stream]

// SendModelChunk sends a generation chunk (token-level streaming).
func (r Responder[Stream]) SendModelChunk(chunk *ai.ModelResponseChunk)

// SendStatus sends a user-defined status update.
func (r Responder[Stream]) SendStatus(status Stream)

// SendArtifact sends an artifact to the stream and adds it to the session.
// If an artifact with the same name already exists in the session, it is replaced.
func (r Responder[Stream]) SendArtifact(artifact *Artifact)
```

---

## 5. SessionFlow and SessionFlowFunc

### SessionFlowFunc

```go
// SessionFlowFunc is the function signature for custom session flows.
// It receives a responder for streaming output, a session runner for state
// management, and returns an optional SessionFlowResult with the final output.
type SessionFlowFunc[Stream, State any] = func(
    ctx context.Context,
    resp Responder[Stream],
    sess *SessionRunner[State],
) (*SessionFlowResult, error)
```

The function returns `(*SessionFlowResult, error)`. Returning a `SessionFlowResult` lets the user control what gets sent back to the client in the `SessionFlowOutput` (the `Message` and `Artifacts` fields). `sess.Result()` is a convenience that populates the result from session state.

### SessionFlow

```go
// SessionFlow is a bidirectional streaming flow with automatic snapshot management.
type SessionFlow[Stream, State any] struct {
    flow *core.Flow[
        *SessionFlowInit[State],
        *SessionFlowOutput[State],
        *SessionFlowStreamChunk[Stream],
        *SessionFlowInput,
    ]
}
```

---

## 6. API Surface

### 6.1 Defining Session Flows

#### DefineSessionFlow

Full control: you write the turn loop.

```go
func DefineSessionFlow[Stream, State any](
    r api.Registry,
    name string,
    fn SessionFlowFunc[Stream, State],
    opts ...SessionFlowOption[State],
) *SessionFlow[Stream, State]
```

#### DefineSessionFlowFromPrompt

Creates a prompt-backed session flow with an automatic conversation loop. Each turn renders the prompt, appends conversation history, calls the model with streaming, and updates session state.

The prompt is looked up by name from the registry. The `defaultInput` provides template variables for prompt rendering (e.g., personality, tone) and can be overridden per invocation via `WithInputVariables`.

```go
func DefineSessionFlowFromPrompt[State, PromptIn any](
    r api.Registry,
    promptName string,
    defaultInput PromptIn,
    opts ...SessionFlowOption[State],
) *SessionFlow[any, State]
```

Internally, this looks up the prompt via `ai.LookupDataPrompt[PromptIn, string]` and builds a `SessionFlowFunc` that:
1. Resolves prompt input (session override > default)
2. Renders the prompt template
3. Tags prompt-rendered messages so they can be excluded from session history
4. Appends conversation history after prompt messages
5. Calls the model with streaming, forwarding chunks via the responder
6. Updates session messages from the full response history (minus prompt messages)
7. Handles tool restarts and interrupts

#### SessionFlowOption[State]

```go
type SessionFlowOption[State any] interface {
    applySessionFlow(*sessionFlowOptions[State]) error
}

// WithSessionStore sets the store for persisting snapshots.
func WithSessionStore[State any](store SessionStore[State]) SessionFlowOption[State]

// WithSnapshotCallback configures when snapshots are created.
// If not provided and a store is configured, snapshots are always created.
func WithSnapshotCallback[State any](cb SnapshotCallback[State]) SessionFlowOption[State]

// WithSnapshotOn configures snapshots to be created only for the specified events.
// Convenience wrapper around WithSnapshotCallback.
func WithSnapshotOn[State any](events ...SnapshotEvent) SessionFlowOption[State]
```

#### High-Level Genkit API

```go
// In go/genkit/genkit.go

func DefineSessionFlow[Stream, State any](
    g *Genkit,
    name string,
    fn aix.SessionFlowFunc[Stream, State],
    opts ...aix.SessionFlowOption[State],
) *aix.SessionFlow[Stream, State]

func DefineSessionFlowFromPrompt[State, PromptIn any](
    g *Genkit,
    promptName string,
    defaultInput PromptIn,
    opts ...aix.SessionFlowOption[State],
) *aix.SessionFlow[any, State]
```

### 6.2 Starting Invocations

#### StreamBidi

Starts a new session flow invocation with bidirectional streaming. Use this for multi-turn interactions where you need to send multiple inputs and receive streaming chunks.

```go
func (sf *SessionFlow[Stream, State]) StreamBidi(
    ctx context.Context,
    opts ...InvocationOption[State],
) (*SessionFlowConnection[Stream, State], error)
```

#### Run

Starts a single-turn session flow invocation with the given input. It sends the input, waits for the flow to complete, and returns the output.

```go
func (sf *SessionFlow[Stream, State]) Run(
    ctx context.Context,
    input *SessionFlowInput,
    opts ...InvocationOption[State],
) (*SessionFlowOutput[State], error)
```

#### RunText

Convenience method that starts a single-turn session flow invocation with a user text message. Equivalent to calling Run with a `SessionFlowInput` containing a single user text message.

```go
func (sf *SessionFlow[Stream, State]) RunText(
    ctx context.Context,
    text string,
    opts ...InvocationOption[State],
) (*SessionFlowOutput[State], error)
```

#### InvocationOption[State]

Configures a session flow invocation (StreamBidi, Run, or RunText).

```go
type InvocationOption[State any] interface {
    applyInvocation(*invocationOptions[State]) error
}

// WithSnapshotID loads state from a persisted snapshot by ID.
// Use this for server-managed state where snapshots are stored.
func WithSnapshotID[State any](id string) InvocationOption[State]

// WithState sets the initial state for the invocation.
// Use this for client-managed state where the client sends state directly.
func WithState[State any](state *SessionState[State]) InvocationOption[State]

// WithInputVariables overrides the default input variables for a
// prompt-backed session flow. Used with DefineSessionFlowFromPrompt.
func WithInputVariables[State any](input any) InvocationOption[State]
```

### 6.3 SessionFlowConnection

Wraps `BidiConnection` with session flow-specific functionality. Unlike the underlying `BidiConnection`, breaking from `Receive()` does **not** cancel the connection, enabling multi-turn patterns where the caller breaks on `EndTurn`, sends the next input, then calls `Receive` again.

This is implemented via an internal goroutine that drains the underlying connection's `Receive` into a buffered channel, ensuring the underlying iterator is never broken.

```go
type SessionFlowConnection[Stream, State any] struct { ... }

// Send sends a SessionFlowInput to the session flow.
func (c *SessionFlowConnection) Send(input *SessionFlowInput) error

// SendMessages sends messages to the session flow.
func (c *SessionFlowConnection) SendMessages(messages ...*ai.Message) error

// SendText sends a single user text message to the session flow.
func (c *SessionFlowConnection) SendText(text string) error

// SendToolRestarts sends tool restart parts to resume interrupted tool calls.
// Parts should be created via ai.ToolDef.RestartWith.
func (c *SessionFlowConnection) SendToolRestarts(parts ...*ai.Part) error

// Close signals that no more inputs will be sent.
func (c *SessionFlowConnection) Close() error

// Receive returns an iterator for receiving stream chunks.
func (c *SessionFlowConnection) Receive() iter.Seq2[*SessionFlowStreamChunk[Stream], error]

// Output returns the final response after the session flow completes.
func (c *SessionFlowConnection) Output() (*SessionFlowOutput[State], error)

// Done returns a channel closed when the connection completes.
func (c *SessionFlowConnection) Done() <-chan struct{}
```

---

## 7. Snapshot System

### 7.1 Store Interface

```go
// SessionStore persists and retrieves snapshots.
type SessionStore[State any] interface {
    // GetSnapshot retrieves a snapshot by ID. Returns nil if not found.
    GetSnapshot(ctx context.Context, snapshotID string) (*SessionSnapshot[State], error)
    // SaveSnapshot persists a snapshot.
    SaveSnapshot(ctx context.Context, snapshot *SessionSnapshot[State]) error
}

// InMemorySessionStore provides a thread-safe in-memory snapshot store.
func NewInMemorySessionStore[State any]() *InMemorySessionStore[State]
```

### 7.2 Snapshot Callbacks

```go
// SnapshotContext provides context for snapshot decision callbacks.
type SnapshotContext[State any] struct {
    // State is the current state that will be snapshotted if the callback returns true.
    State *SessionState[State]
    // PrevState is the state at the last snapshot, or nil if none exists.
    PrevState *SessionState[State]
    // TurnIndex is the turn number in the current invocation.
    TurnIndex int
    // Event is what triggered this snapshot check.
    Event SnapshotEvent
}

// SnapshotCallback decides whether to create a snapshot.
// If not provided and a store is configured, snapshots are always created.
type SnapshotCallback[State any] = func(ctx context.Context, sc *SnapshotContext[State]) bool
```

### 7.3 Snapshot Lifecycle

Snapshots are checked at two points:

| Event | Trigger | Description |
|-------|---------|-------------|
| `SnapshotEventTurnEnd` | `SessionRunner.Run` completes a turn | After the turn function returns successfully |
| `SnapshotEventInvocationEnd` | Session flow function returns | Final state capture when invocation completes |

At each point:
1. If no store is configured, skip
2. Check if state has changed since the last snapshot (version-based). If unchanged, skip. This deduplication prevents redundant snapshots, commonly at invocation end after a single-turn `Run`/`RunText` where the turn-end snapshot already captured the final state
3. If a callback is configured, invoke it. If it returns false, skip
4. Generate a UUID for the snapshot ID, persist to store
5. Send `SnapshotID` on the stream
6. Set `snapshotId` in the last message's `Metadata`, so the client knows which snapshot corresponds to which message

When an invocation-end snapshot is skipped due to deduplication, the output's `SnapshotID` falls back to the last snapshot that was created (typically the turn-end snapshot). If the `SessionFlowFunc` mutates state after `sess.Run()` returns, the invocation-end snapshot fires normally.

### 7.4 Resuming from Snapshots

When `WithSnapshotID` is provided:

1. Load the snapshot from the store
2. Extract the `SessionState` from the snapshot
3. Initialize the session with that state (messages, custom state, artifacts, input variables)
4. New snapshots will reference this as the parent
5. Conversation continues from the restored state

When `WithState` is provided:

1. Use the provided `SessionState` directly
2. Initialize the session with that state
3. No parent snapshot reference (client-managed mode)

---

## 8. Internal Flow

### 8.1 SessionFlow Wrapping

When `DefineSessionFlow` is called, it registers a `core.BidiFlow` that wraps the user's `SessionFlowFunc`:

```go
core.DefineBidiFlow(r, name, func(
    ctx context.Context,
    in *SessionFlowInit[State],
    inCh <-chan *SessionFlowInput,
    outCh chan<- *SessionFlowStreamChunk[Stream],
) (*SessionFlowOutput[State], error) {
    // 1. Create session from init (load snapshot or use direct state)
    session, snapshot, _ := newSessionFromInit(ctx, in, store)
    ctx = NewSessionContext(ctx, session)

    // 2. Create SessionRunner with turn management
    runner := &SessionRunner[State]{
        Session:          session,
        snapshotCallback: snapshotCallback,
        InputCh:          inCh,
        lastSnapshot:     snapshot,
    }

    // 3. Create intermediary channel that intercepts artifacts
    //    and accumulates turn output for tracing
    respCh := make(chan *SessionFlowStreamChunk[Stream])
    // ... goroutine forwards from respCh to outCh, adds artifacts to session

    // 4. Wire up onEndTurn: triggers snapshot + sends EndTurn chunk
    runner.onEndTurn = func(turnCtx context.Context) {
        snapshotID := runner.maybeSnapshot(turnCtx, SnapshotEventTurnEnd)
        if snapshotID != "" {
            respCh <- &SessionFlowStreamChunk[Stream]{SnapshotID: snapshotID}
        }
        respCh <- &SessionFlowStreamChunk[Stream]{EndTurn: true}
    }

    // 5. Call user's function
    result, err := fn(ctx, Responder[Stream](respCh), runner)
    close(respCh)

    // 6. Final snapshot at invocation end
    snapshotID := runner.maybeSnapshot(ctx, SnapshotEventInvocationEnd)
    if snapshotID == "" && runner.lastSnapshot != nil {
        snapshotID = runner.lastSnapshot.SnapshotID
    }

    // 7. Build output
    out := &SessionFlowOutput[State]{SnapshotID: snapshotID}
    if result != nil {
        out.Message = result.Message
        out.Artifacts = result.Artifacts
    }
    // Only include full state when client-managed (no store)
    if store == nil {
        out.State = session.State()
    }
    return out, nil
})
```

---

## 9. Tracing Integration

Each turn executed by `SessionRunner.Run` creates a trace span named `sessionFlow/turn/{turnIndex}`. The span captures:
- **Input**: The `SessionFlowInput` for the turn
- **Output**: Accumulated stream chunks for the turn (model chunks, status, artifacts)

This provides per-turn visibility into inputs, outputs, and timing.

---

## 10. Example Usage

### 10.1 Custom Session Flow with Streaming

```go
chatFlow := genkit.DefineSessionFlow(g, "chat",
    func(ctx context.Context, resp aix.Responder[any], sess *aix.SessionRunner[struct{}]) (*aix.SessionFlowResult, error) {
        if err := sess.Run(ctx, func(ctx context.Context, input *aix.SessionFlowInput) error {
            for chunk, err := range genkit.GenerateStream(ctx, g,
                ai.WithModelName("googleai/gemini-3-flash-preview"),
                ai.WithMessages(sess.Messages()...),
            ) {
                if err != nil {
                    return err
                }
                if chunk.Done {
                    sess.AddMessages(chunk.Response.Message)
                    break
                }
                resp.SendModelChunk(chunk.Chunk) // stream tokens to client
            }
            return nil
        }); err != nil {
            return nil, err
        }
        return sess.Result(), nil
    },
)
```

### 10.2 Prompt-Backed Session Flow

Given a `.prompt` file:

```yaml
# prompts/chat.prompt
---
model: googleai/gemini-3-flash-preview
input:
  schema:
    personality: string
  default:
    personality: a helpful assistant
---
{{ role "system" }}
You are {{ personality }}. Keep responses concise.
```

```go
type ChatInput struct {
    Personality string `json:"personality"`
}

chatFlow := genkit.DefineSessionFlowFromPrompt[any](
    g, "chat", ChatInput{Personality: "a sarcastic pirate"},
)
```

### 10.3 Multi-Turn Streaming Conversation

```go
conn, _ := chatFlow.StreamBidi(ctx)

conn.SendText("What is Go?")
for chunk, err := range conn.Receive() {
    if chunk.ModelChunk != nil {
        fmt.Print(chunk.ModelChunk.Text())
    }
    if chunk.EndTurn {
        break // turn complete, ready for next input
    }
}

conn.SendText("Tell me more about its concurrency model")
// ... iterate conn.Receive() again ...

conn.Close()
output, _ := conn.Output() // SessionFlowOutput with final state/snapshot
```

### 10.4 Single-Turn Usage

```go
output, _ := chatFlow.RunText(ctx, "What is Go?")
fmt.Println(output.Message.Text())
```

### 10.5 Snapshots and Resumption

```go
store := aix.NewInMemorySessionStore[MyState]()

chatFlow := genkit.DefineSessionFlow(g, "chat", myFunc,
    aix.WithSessionStore(store),
    aix.WithSnapshotOn[MyState](aix.SnapshotEventTurnEnd),
)

// Resume from a server-stored snapshot:
output, _ := chatFlow.RunText(ctx, "continue",
    aix.WithSnapshotID[MyState]("snapshot-abc-123"),
)

// Or resume from client-kept state (no server store needed):
output, _ := chatFlow.RunText(ctx, "continue", aix.WithState(&aix.SessionState[MyState]{
    Messages: previousMessages,
    Custom:   MyState{Topic: "concurrency"},
}))
```

### 10.6 Custom Session State

```go
type ChatState struct {
    TopicsDiscussed []string `json:"topicsDiscussed"`
}

chatFlow := genkit.DefineSessionFlow(g, "chat",
    func(ctx context.Context, resp aix.Responder[any], sess *aix.SessionRunner[ChatState]) (*aix.SessionFlowResult, error) {
        if err := sess.Run(ctx, func(ctx context.Context, input *aix.SessionFlowInput) error {
            // ... generate response ...

            sess.UpdateCustom(func(s ChatState) ChatState {
                s.TopicsDiscussed = append(s.TopicsDiscussed, extractTopic(input))
                return s
            })
            return nil
        }); err != nil {
            return nil, err
        }
        return sess.Result(), nil
    },
    aix.WithSessionStore(aix.NewInMemorySessionStore[ChatState]()),
)
```

### 10.7 Controlling the SessionFlowResult

`sess.Result()` returns the last message and all artifacts. If you need to control what gets sent back (e.g., returning only artifacts without a message, or omitting certain artifacts), construct the result directly:

```go
return &aix.SessionFlowResult{Artifacts: sess.Artifacts()}, nil
```

### 10.8 Snapshot Callback

```go
chatFlow := genkit.DefineSessionFlowFromPrompt(
    g, "chat", ChatInput{Personality: "a sarcastic pirate"},
    aix.WithSessionStore(aix.NewInMemorySessionStore[any]()),
    aix.WithSnapshotCallback(func(ctx context.Context, sc *aix.SnapshotContext[any]) bool {
        // Only snapshot at invocation end or every 5 turns
        return sc.Event == aix.SnapshotEventInvocationEnd || sc.TurnIndex%5 == 0
    }),
)
```

---

## 11. Design Decisions

### Why Separate SessionState from SessionSnapshot?

**SessionState** is the portable state that flows between client and server:
- Just the data: Messages, Custom, Artifacts, InputVariables
- No IDs, timestamps, or metadata
- Clients manage it however they want

**SessionSnapshot** is a persisted point-in-time capture:
- Has a UUID-based ID
- Has timestamps and metadata (ParentID, Event)
- Used for storage, debugging, branching/restoration
- Managed by the framework and store

This separation provides:
- **Clarity**: Users know exactly what fields are relevant for their use case
- **Simplicity**: Client-managed state doesn't deal with server metadata
- **Flexibility**: Server can add snapshot metadata without affecting client API

### Why Mandate Messages in State?

Messages are fundamental to conversation continuity. By including them in the state schema:

- Ensures consistent conversation history across invocations
- Prevents common bugs where messages are lost between turns
- Enables the framework to optimize message handling
- Provides a standard structure that tools and middleware can rely on

### Why Session and SessionRunner Instead of One Type?

`Session` holds the core state and provides read/write methods. `SessionRunner` adds turn management, snapshot logic, and the input channel. This separation exists because:

- `Session` can be accessed via context from anywhere (tools, sub-flows) via `SessionFromContext`
- `SessionRunner` is only needed by the top-level session flow function
- It avoids exposing turn-management internals to code that just needs state access

### Why Is Responder a Channel Type?

`Responder` is `chan<- *SessionFlowStreamChunk[Stream]` with convenience methods. This design:

- Allows the framework to set up an intermediary goroutine that intercepts chunks (for artifact tracking, turn output accumulation)
- Keeps the user-facing API simple (just call methods)
- Enables the framework to close the channel to signal completion

### Why Does SessionFlowFunc Return (*SessionFlowResult, error)?

Earlier designs had the function return just `error`, with the framework extracting results from session state. Returning `SessionFlowResult` gives the user explicit control over what goes in the output without requiring them to populate session state in a specific way.

`sess.Result()` provides a zero-effort default that extracts the last message and all artifacts from session state.

### Why Version-Based Snapshot Deduplication?

The session tracks a `version` counter that increments on every mutation. Before creating a snapshot, the runner compares the current version to the version at the last snapshot. If unchanged, the snapshot is skipped.

This prevents a common redundancy: after a single-turn `Run`/`RunText`, the turn-end snapshot captures the final state, and the invocation-end snapshot would be identical. Without deduplication, every single-turn call would create two identical snapshots.

### Why Does SendArtifact Add to Session?

`SendArtifact()` both streams the artifact to the client and adds it to the session state (replacing by name if a duplicate exists). This prevents a common class of bugs where the developer streams an artifact but forgets to add it to session state, resulting in artifacts being lost across snapshots.

### Why Does DefineSessionFlowFromPrompt Take a Prompt Name?

Rather than taking a `PromptRenderer` interface, it takes a prompt name string and looks it up from the registry. This aligns with how prompts are typically used in Genkit (defined once, looked up by name) and ensures the prompt is registered and available for reflection/tooling.

### SessionRunner.Run Design (Session Owns the Loop)

The function does not receive the input channel directly. The session runner holds the channel internally, and `Run` handles the loop:

```go
err := sess.Run(ctx, func(ctx context.Context, input *aix.SessionFlowInput) error {
    // ... turn logic
    return nil
})
```

This was chosen because:
- It provides the simplest API for the common case
- It eliminates a class of bugs (forgetting to handle turns, incorrect loop handling)
- The channel is an implementation detail that users rarely need to interact with directly
- Setup and teardown remain possible before/after `sess.Run`
- For advanced cases, `sess.InputCh` and `sess.TurnIndex` are exposed for direct access

---

## 12. Known Issues

- **Empty trace on zero-turn connections**: `StreamBidi` creates a trace span immediately when the connection is established. If the connection is closed without sending any messages (zero turns), an empty single-span trace is still emitted. A future change could defer span creation until the first input arrives.
- **Missing `Stream()` and `StreamText()` convenience methods**: `SessionFlow` has `Run()` and `RunText()` for single-turn non-streaming usage, but lacks corresponding `Stream()` and `StreamText()` methods that would return an iterator of stream chunks for single-turn streaming. Currently, single-turn streaming requires using `StreamBidi` directly. Adding these would improve DX.

---

## 13. Files

### New Files (in `go/ai/exp/`)

| File | Description |
|------|-------------|
| `gen.go` | Generated wire types: SessionFlowInit, SessionFlowInput, SessionFlowOutput, SessionFlowResult, SessionFlowStreamChunk, SessionState, Artifact, SnapshotEvent |
| `option.go` | SessionFlowOption (WithSessionStore, WithSnapshotCallback, WithSnapshotOn), InvocationOption (WithState, WithSnapshotID, WithInputVariables) |
| `session.go` | Session, SessionStore interface, InMemorySessionStore, SessionSnapshot, SnapshotContext, SnapshotCallback, context helpers |
| `session_flow.go` | SessionFlow, SessionFlowFunc, SessionRunner, Responder, DefineSessionFlow, DefineSessionFlowFromPrompt, SessionFlowConnection |
| `session_flow_test.go` | Tests |

### Modified Files

| File | Change |
|------|--------|
| `go/genkit/genkit.go` | Add DefineSessionFlow and DefineSessionFlowFromPrompt wrappers |

---

## 14. Future Considerations

Out of scope for this design:

- **Snapshot expiration**: Automatic cleanup based on age or count
- **Snapshot compression**: Delta/patch-based storage
- **Snapshot branching**: Tree-structured conversation histories
- **Snapshot annotations**: User-provided labels or descriptions
- **Tool iteration snapshots**: Mid-turn snapshots after tool execution
