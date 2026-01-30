# Genkit Go SessionFlow with Snapshots - Design Document

## Overview

This document describes the design for the `SessionFlow` primitive in Genkit Go with snapshot-based state management. A SessionFlow is a stateful, multi-turn conversational flow with automatic snapshot persistence and turn semantics.

Snapshots provide:
- **State encapsulation**: Messages, user-defined state, and artifacts in a single serializable unit
- **Resumability**: Start new invocations from any previous snapshot
- **Flexibility**: Support for both client-managed and server-managed state patterns
- **Debugging**: Point-in-time state capture for inspection and replay

This design builds on the bidirectional streaming primitives described in [go-bidi-design.md](go-bidi-design.md).

## Package Location

SessionFlow is an AI concept and belongs in `go/ai/x/` (experimental):

```
go/ai/x/
├── session_flow.go          # SessionFlow, SessionFlowFunc, SessionFlowParams, Responder
├── session_flow_options.go  # SessionFlowOption, StreamBidiOption
├── session_flow_state.go    # SessionFlowState, SessionFlowSnapshot, SessionFlowArtifact, SessionFlowInit, SessionFlowResponse, SessionFlowStreamChunk
├── session_flow_store.go    # SnapshotStore interface, InMemorySnapshotStore, SnapshotCallback, SnapshotContext
├── session_flow_test.go     # Tests
```

Import as `aix "github.com/firebase/genkit/go/ai/x"`.

---

## 1. Core Type Definitions

### 1.1 State and Snapshot Types

**SessionFlowState** is the portable state that flows between client and server. It contains only the data needed for conversation continuity.

**SessionFlowSnapshot** is a persisted point-in-time capture with metadata. It wraps SessionFlowState with additional fields for storage, debugging, and restoration.

```go
// SessionFlowState is the portable conversation state.
type SessionFlowState[State any] struct {
    // Messages is the conversation history.
    Messages []*ai.Message `json:"messages,omitempty"`
    // Custom is the user-defined state associated with this conversation.
    Custom State `json:"custom,omitempty"`
    // Artifacts are named collections of parts produced during the conversation.
    Artifacts []*SessionFlowArtifact `json:"artifacts,omitempty"`
}

// SessionFlowSnapshot is a persisted point-in-time capture of session state.
type SessionFlowSnapshot[State any] struct {
    // SnapshotID is the unique identifier for this snapshot (UUID).
    SnapshotID string `json:"snapshotId"`
    // ParentID is the ID of the previous snapshot in this timeline.
    ParentID string `json:"parentId,omitempty"`
    // CreatedAt is when the snapshot was created.
    CreatedAt time.Time `json:"createdAt"`
    // TurnIndex is the turn number when this snapshot was created (0-indexed).
    TurnIndex int `json:"turnIndex"`
    // State is the actual conversation state.
    State SessionFlowState[State] `json:"state"`
}

// SessionFlowArtifact represents a named collection of parts produced during a session.
// Examples: generated files, images, code snippets, diagrams, etc.
type SessionFlowArtifact struct {
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
// SessionFlowInput is the input sent to a session flow during a conversation turn.
// This wrapper allows future extensibility beyond just messages.
type SessionFlowInput struct {
    // Messages contains the user's input for this turn.
    Messages []*ai.Message `json:"messages,omitempty"`
}

// SessionFlowInit is the input for starting a session flow invocation.
// Provide either SnapshotID (to load from store) or State (direct state).
type SessionFlowInit[State any] struct {
    // SnapshotID loads state from a persisted snapshot.
    // Mutually exclusive with State.
    SnapshotID string `json:"snapshotId,omitempty"`
    // State provides direct state for the invocation.
    // Mutually exclusive with SnapshotID.
    State *SessionFlowState[State] `json:"state,omitempty"`
}

// SessionFlowResponse is the output when a session flow invocation completes.
type SessionFlowResponse[State any] struct {
    // State contains the final conversation state.
    State *SessionFlowState[State] `json:"state"`
    // SnapshotID is the ID of the snapshot created at the end of this invocation.
    // Empty if no snapshot was created (callback returned false or no store configured).
    SnapshotID string `json:"snapshotId,omitempty"`
}
```

### 1.3 Stream Types

```go
// SessionFlowStreamChunk represents a single item in the session flow's output stream.
// Multiple fields can be populated in a single chunk.
type SessionFlowStreamChunk[Stream any] struct {
    // Chunk contains token-level generation data.
    Chunk *ai.ModelResponseChunk `json:"chunk,omitempty"`
    // Status contains user-defined structured status information.
    // The Stream type parameter defines the shape of this data.
    Status Stream `json:"status,omitempty"`
    // Artifact contains a newly produced artifact.
    Artifact *SessionFlowArtifact `json:"artifact,omitempty"`
    // SnapshotCreated contains the ID of a snapshot that was just persisted.
    SnapshotCreated string `json:"snapshotCreated,omitempty"`
    // EndTurn signals that the session flow has finished processing the current input.
    // When true, the client should stop iterating and may send the next input.
    EndTurn bool `json:"endTurn,omitempty"`
}
```

### 1.4 Session

The Session provides mutable working state during a session flow invocation. It is propagated via context so that nested operations (tools, sub-flows) can access consistent state.

```go
// Session holds the working state during a session flow invocation.
// It is propagated through context and provides read/write access to state.
type Session[State any] struct {
    mu    sync.RWMutex
    state SessionFlowState[State]
    store SnapshotStore[State]

    // Internal references set by the framework
    onEndTurn func() // set by runWrapped; triggers snapshot + EndTurn chunk
    inCh      <-chan *SessionFlowInput

    // Snapshot tracking
    lastSnapshot *SessionFlowSnapshot[State]
    turnIndex    int
}

// Run loops over the input channel, calling fn for each turn. Each turn is
// wrapped in an OTel span for tracing. Input messages are automatically added
// to the session before fn is called. After fn returns successfully, an EndTurn
// chunk is sent and a snapshot check is triggered.
func (s *Session[State]) Run(
    ctx context.Context,
    fn func(ctx context.Context, input *SessionFlowInput) error,
) error

// State returns a copy of the current session flow state.
func (s *Session[State]) State() *SessionFlowState[State]

// Messages returns the current conversation history.
func (s *Session[State]) Messages() []*ai.Message

// AddMessages appends messages to the conversation history.
func (s *Session[State]) AddMessages(messages ...*ai.Message)

// SetMessages replaces the entire conversation history.
func (s *Session[State]) SetMessages(messages []*ai.Message)

// Custom returns the current user-defined custom state.
func (s *Session[State]) Custom() State

// SetCustom updates the user-defined custom state.
func (s *Session[State]) SetCustom(custom State)

// PatchCustom atomically reads the current custom state, applies the given
// function, and writes the result back. Use this instead of Custom()/SetCustom()
// when concurrent access to state is possible.
func (s *Session[State]) PatchCustom(fn func(State) State)

// Artifacts returns the current artifacts.
func (s *Session[State]) Artifacts() []*SessionFlowArtifact

// AddArtifact adds an artifact to the session. If an artifact with the same
// name already exists, it is replaced.
func (s *Session[State]) AddArtifact(artifact *SessionFlowArtifact)

// SetArtifacts replaces the entire artifact list.
func (s *Session[State]) SetArtifacts(artifacts ...*SessionFlowArtifact)

// Context integration
func NewSessionContext[State any](ctx context.Context, s *Session[State]) context.Context
func SessionFromContext[State any](ctx context.Context) *Session[State]
```

### 1.5 Responder

The Responder wraps the output stream with typed methods for sending different kinds of data.

```go
// Responder provides methods for sending data to the session flow's output stream.
type Responder[Stream any] struct {
    ch      chan<- *SessionFlowStreamChunk[Stream]
    session *Session[any]
}

// Send sends a complete stream chunk. Use this for full control over the chunk contents.
func (r *Responder[Stream]) Send(chunk *SessionFlowStreamChunk[Stream])

// SendChunk sends a generation chunk (token-level streaming).
func (r *Responder[Stream]) SendChunk(chunk *ai.ModelResponseChunk)

// SendStatus sends a user-defined status update.
func (r *Responder[Stream]) SendStatus(status Stream)

// SendArtifact sends an artifact to the stream and adds it to the session.
// If an artifact with the same name already exists in the session, it is replaced.
func (r *Responder[Stream]) SendArtifact(artifact *SessionFlowArtifact)
```

### 1.6 SessionFlow Function and Parameters

```go
// SessionFlowParams contains the parameters passed to a session flow function.
// This struct may be extended with additional fields in the future.
type SessionFlowParams[Stream, State any] struct {
    // Session provides access to the working state.
    Session *Session[State]
}

// SessionFlowFunc is the function signature for session flows.
// Type parameters:
//   - Stream: Type for status updates sent via the responder
//   - State: Type for user-defined state in snapshots
type SessionFlowFunc[Stream, State any] func(
    ctx context.Context,
    resp *Responder[Stream],
    params *SessionFlowParams[Stream, State],
) error
```

### 1.7 SessionFlow

```go
// SessionFlow is a bidirectional streaming action with automatic snapshot management.
type SessionFlow[Stream, State any] struct {
    *corex.BidiAction[*SessionFlowInit[State], *SessionFlowInput, *SessionFlowResponse[State], *SessionFlowStreamChunk[Stream]]
    store            SnapshotStore[State]
    snapshotCallback SnapshotCallback[State]
}
```

---

## 2. Snapshot Store

### 2.1 Store Interface

```go
// SnapshotStore persists and retrieves snapshots.
type SnapshotStore[State any] interface {
    // GetSnapshot retrieves a snapshot by ID. Returns nil if not found.
    GetSnapshot(ctx context.Context, snapshotID string) (*SessionFlowSnapshot[State], error)
    // SaveSnapshot persists a snapshot.
    SaveSnapshot(ctx context.Context, snapshot *SessionFlowSnapshot[State]) error
}
```

### 2.2 In-Memory Implementation

```go
// InMemorySnapshotStore provides a thread-safe in-memory snapshot store.
type InMemorySnapshotStore[State any] struct {
    snapshots map[string]*SessionFlowSnapshot[State]
    mu        sync.RWMutex
}

func NewInMemorySnapshotStore[State any]() *InMemorySnapshotStore[State]
```

---

## 3. Snapshot Callbacks

```go
// SnapshotContext provides context for snapshot decision callbacks.
type SnapshotContext[State any] struct {
    // State is the current state that will be snapshotted if the callback returns true.
    State *SessionFlowState[State]
    // PrevState is the state at the last snapshot, or nil if none exists.
    PrevState *SessionFlowState[State]
    // TurnIndex is the current turn number.
    TurnIndex int
}

// SnapshotCallback decides whether to create a snapshot.
// If not provided and a store is configured, snapshots are always created.
type SnapshotCallback[State any] = func(ctx context.Context, sc *SnapshotContext[State]) bool
```

---

## 4. API Surface

### 4.1 Defining Session Flows

```go
// DefineSessionFlow creates a SessionFlow with automatic snapshot management and registers it.
func DefineSessionFlow[Stream, State any](
    r api.Registry,
    name string,
    fn SessionFlowFunc[Stream, State],
    opts ...SessionFlowOption[State],
) *SessionFlow[Stream, State]

// SessionFlowOption configures a SessionFlow.
type SessionFlowOption[State any] interface {
    applySessionFlow(*sessionFlowOptions[State]) error
}

// WithSnapshotStore sets the store for persisting snapshots.
func WithSnapshotStore[State any](store SnapshotStore[State]) SessionFlowOption[State]

// WithSnapshotCallback configures when snapshots are created.
// If not provided and a store is configured, snapshots are always created.
func WithSnapshotCallback[State any](cb SnapshotCallback[State]) SessionFlowOption[State]
```

### 4.2 Starting Connections

```go
// StreamBidiOption configures a StreamBidi call.
type StreamBidiOption[State any] interface {
    applyStreamBidi(*streamBidiOptions[State]) error
}

// WithState sets the initial state for the invocation.
// Use this for client-managed state where the client sends state directly.
func WithState[State any](state *SessionFlowState[State]) StreamBidiOption[State]

// WithSnapshotID loads state from a persisted snapshot by ID.
// Use this for server-managed state where snapshots are stored.
func WithSnapshotID[State any](id string) StreamBidiOption[State]

// StreamBidi starts a new session flow invocation.
func (sf *SessionFlow[Stream, State]) StreamBidi(
    ctx context.Context,
    opts ...StreamBidiOption[State],
) (*SessionFlowConnection[Stream, State], error)
```

### 4.3 SessionFlow Connection

```go
// SessionFlowConnection wraps BidiConnection with session flow-specific functionality.
type SessionFlowConnection[Stream, State any] struct {
    conn *corex.BidiConnection[*SessionFlowInput, *SessionFlowResponse[State], *SessionFlowStreamChunk[Stream]]
}

// Send sends a SessionFlowInput to the session flow.
// Use this for full control over the input structure.
func (c *SessionFlowConnection[Stream, State]) Send(input *SessionFlowInput) error

// SendMessages sends messages to the session flow.
// This is a convenience method that wraps messages in a SessionFlowInput.
func (c *SessionFlowConnection[Stream, State]) SendMessages(messages ...*ai.Message) error

// SendText sends a single user text message to the session flow.
// This is a convenience method that creates a user message and wraps it in SessionFlowInput.
func (c *SessionFlowConnection[Stream, State]) SendText(text string) error

// Close signals that no more inputs will be sent.
func (c *SessionFlowConnection[Stream, State]) Close() error

// Receive returns an iterator for receiving stream chunks.
func (c *SessionFlowConnection[Stream, State]) Receive() iter.Seq2[*SessionFlowStreamChunk[Stream], error]

// Output returns the final response after the session flow completes.
func (c *SessionFlowConnection[Stream, State]) Output() (*SessionFlowResponse[State], error)

// Done returns a channel closed when the connection completes.
func (c *SessionFlowConnection[Stream, State]) Done() <-chan struct{}
```

### 4.4 High-Level Genkit API

```go
// In go/genkit/session_flow.go

func DefineSessionFlow[Stream, State any](
    g *Genkit,
    name string,
    fn aix.SessionFlowFunc[Stream, State],
    opts ...aix.SessionFlowOption[State],
) *aix.SessionFlow[Stream, State]
```

---

## 5. Snapshot Lifecycle

### 5.1 Snapshot Points

Snapshots are created at two points:

| Event | Trigger | Description |
|-------|---------|-------------|
| Turn end | `Session.Run` completes a turn | After the turn function returns successfully |
| Invocation end | Session flow function returns | Final state capture when invocation completes |

At each point:
1. The snapshot callback is invoked (or defaults to "always" if a store is configured)
2. If callback returns true:
   - Generate a UUID for the snapshot ID
   - Persist to store
   - Send `SnapshotCreated` on the stream
3. The snapshot ID is set in `message.Metadata["snapshotId"]` on the last message, so the client knows which snapshot corresponds to which message and can revert to any point

### 5.2 Resuming from Snapshots

When `WithSnapshotID` is provided to `StreamBidi`:

1. Load the snapshot from the store
2. Extract the `SessionFlowState` from the snapshot
3. Initialize the session with that state (messages, custom state, artifacts)
4. New snapshots will reference this as the parent
5. Conversation continues from the restored state

When `WithState` is provided to `StreamBidi`:

1. Use the provided `SessionFlowState` directly
2. Initialize the session with that state
3. No parent snapshot reference (client-managed mode)

---

## 6. Internal Flow

### 6.1 SessionFlow Wrapping

The user's `SessionFlowFunc` returns `error`. The framework wraps this to produce `SessionFlowResponse`:

```go
func (sf *SessionFlow[Stream, State]) runWrapped(
    ctx context.Context,
    init *SessionFlowInit[State],
    inCh <-chan *SessionFlowInput,
    outCh chan<- *SessionFlowStreamChunk[Stream],
) (*SessionFlowResponse[State], error) {
    session := newSessionFromInit(init, sf.store)
    session.inCh = inCh
    ctx = NewSessionContext(ctx, session)

    responder := &Responder[Stream]{
        ch:               outCh,
        session:          session,
        snapshotCallback: sf.snapshotCallback,
        store:            sf.store,
    }
    session.onEndTurn = responder.endTurn

    params := &SessionFlowParams[Stream, State]{
        Session: session,
    }

    err := sf.fn(ctx, responder, params)
    if err != nil {
        return nil, err
    }

    snapshotID := responder.triggerSnapshot()

    return &SessionFlowResponse[State]{
        State:      session.toState(),
        SnapshotID: snapshotID,
    }, nil
}
```

### 6.2 Session.Run and Turn Lifecycle

`Session.Run` owns the input loop. For each input received from the channel:

1. Create an OTel span (`sessionFlow/turn/{turnIndex}`) with input messages as attributes
2. Add input messages to session
3. Call the user's turn function with the span context
4. On success: trigger snapshot, send `EndTurn` chunk, increment turn index
5. On error: record error on span and return

```go
func (s *Session[State]) Run(
    ctx context.Context,
    fn func(ctx context.Context, input *SessionFlowInput) error,
) error {
    for input := range s.inCh {
        ctx, span := tracer.Start(ctx, fmt.Sprintf("sessionFlow/turn/%d", s.turnIndex))

        s.AddMessages(input.Messages...)

        if err := fn(ctx, input); err != nil {
            span.RecordError(err)
            span.SetStatus(codes.Error, err.Error())
            span.End()
            return err
        }

        s.onEndTurn()
        s.turnIndex++
        span.End()
    }
    return nil
}
```

---

## 7. Example Usage

### 7.1 Chat SessionFlow with Snapshots

```go
package main

import (
    "context"
    "fmt"

    "github.com/firebase/genkit/go/ai"
    aix "github.com/firebase/genkit/go/ai/x"
    "github.com/firebase/genkit/go/genkit"
    "github.com/firebase/genkit/go/plugins/googlegenai"
)

type ChatState struct {
    UserPreferences map[string]string `json:"userPreferences,omitempty"`
    TopicHistory    []string          `json:"topicHistory,omitempty"`
}

type ChatStatus struct {
    Phase   string `json:"phase"`
    Details string `json:"details,omitempty"`
}

func main() {
    ctx := context.Background()
    store := aix.NewInMemorySnapshotStore[ChatState]()

    g := genkit.Init(ctx,
        genkit.WithPlugins(&googlegenai.GoogleAI{}),
        genkit.WithDefaultModel("googleai/gemini-3-flash-preview"),
    )

    chatFlow := genkit.DefineSessionFlow(g, "chatFlow",
        func(ctx context.Context, resp *aix.Responder[ChatStatus], params *aix.SessionFlowParams[ChatStatus, ChatState]) error {
            return params.Session.Run(ctx, func(ctx context.Context, input *aix.SessionFlowInput) error {
                sess := params.Session

                resp.SendStatus(ChatStatus{Phase: "generating"})

                for result, err := range genkit.GenerateStream(ctx, g,
                    ai.WithMessages(sess.Messages()...),
                ) {
                    if err != nil {
                        return err
                    }
                    if result.Done {
                        sess.AddMessages(result.Response.Message)
                    }
                    resp.SendChunk(result.Chunk)
                }

                sess.PatchCustom(func(s ChatState) ChatState {
                    s.TopicHistory = append(s.TopicHistory, extractTopic(input.Messages))
                    return s
                })

                resp.SendStatus(ChatStatus{Phase: "complete"})
                return nil
            })
        },
        aix.WithSnapshotStore(store),
    )

    conn, _ := chatFlow.StreamBidi(ctx)

    conn.SendText("Hello! Tell me about Go programming.")
    for chunk, err := range conn.Receive() {
        if err != nil {
            panic(err)
        }
        if chunk.Chunk != nil {
            fmt.Print(chunk.Chunk.Text())
        }
        if chunk.EndTurn {
            break
        }
    }

    conn.SendText("What are channels used for?")
    for chunk, err := range conn.Receive() {
        if err != nil {
            panic(err)
        }
        if chunk.Chunk != nil {
            fmt.Print(chunk.Chunk.Text())
        }
        if chunk.EndTurn {
            break
        }
    }

    conn.Close()

    response, _ := conn.Output()
    fmt.Printf("Messages in history: %d\n", len(response.State.Messages))
    if response.SnapshotID != "" {
        fmt.Printf("Final snapshot: %s\n", response.SnapshotID)
    }
}
```

### 7.2 Resuming from a Snapshot

```go
snapshotID := "abc123..."

conn, _ := chatFlow.StreamBidi(ctx, aix.WithSnapshotID[ChatState](snapshotID))

conn.SendText("Continue our discussion about channels")
for chunk, err := range conn.Receive() {
    // ... handle response ...
}
```

### 7.3 Client-Managed State

For clients that manage their own state (e.g., web apps with local storage):

```go
clientState := &aix.SessionFlowState[ChatState]{
    Messages: previousMessages,
    Custom:    ChatState{UserPreferences: prefs},
}

conn, _ := chatFlow.StreamBidi(ctx, aix.WithState(clientState))

// ... interact ...

response, _ := conn.Output()
// Client stores response.State locally for next invocation
```

### 7.4 SessionFlow with Artifacts

```go
type CodeState struct {
    Language string `json:"language"`
}

type CodeStatus struct {
    Phase string `json:"phase"`
}

codeFlow := genkit.DefineSessionFlow(g, "codeFlow",
    func(ctx context.Context, resp *aix.Responder[CodeStatus], params *aix.SessionFlowParams[CodeStatus, CodeState]) error {
        return params.Session.Run(ctx, func(ctx context.Context, input *aix.SessionFlowInput) error {
            sess := params.Session

            generatedCode := "func main() { fmt.Println(\"Hello\") }"

            resp.SendStatus(CodeStatus{Phase: "code_generated"})

            resp.SendArtifact(&aix.SessionFlowArtifact{
                Name: "main.go",
                Parts: []*ai.Part{ai.NewTextPart(generatedCode)},
                Metadata: map[string]any{"language": "go"},
            })

            sess.AddMessages(ai.NewModelTextMessage("Here's the code you requested."))
            return nil
        })
    },
    aix.WithSnapshotStore(store),
)
```

---

## 8. Tracing Integration

Each turn executed by `Session.Run` creates an OTel span named `sessionFlow/turn/{turnIndex}`. This provides per-turn visibility into inputs, outputs, and timing.

When a snapshot is created (at turn end or invocation end), metadata is recorded on the current span:

- `genkit:metadata:snapshotId` - The snapshot ID
- `genkit:metadata:sessionFlow` - The session flow name (e.g., `chatFlow`)

This enables the Dev UI to correlate traces with snapshots and fetch snapshot data via the reflection API.

**Recording snapshot in span:**

```go
func (r *Responder[Stream]) triggerSnapshot() string {
    // ... create snapshot ...

    if snapshot != nil {
        span := trace.SpanFromContext(r.ctx)
        span.SetAttributes(
            attribute.String("genkit:metadata:snapshotId", snapshot.SnapshotID),
            attribute.String("genkit:metadata:sessionFlow", r.flowName),
        )
        return snapshot.SnapshotID
    }
    return ""
}
```

---

## 9. Reflection API Integration

Snapshot stores are exposed via the reflection API for Dev UI access.

### 9.1 Action Registration

When `DefineSessionFlow` is called with `WithSnapshotStore`, actions are registered:

| Action | Key | Input | Returns |
|--------|-----|-------|---------|
| getSnapshot | `/snapshot-store/{flow}/getSnapshot` | `{snapshotId: string}` | `SessionFlowSnapshot[State]` |

### 9.2 Action Type

```go
const ActionTypeSnapshotStore api.ActionType = "snapshot-store"
```

### 9.3 Dev UI Flow

1. Dev UI receives a trace with `snapshotId` and `sessionFlow` in span metadata
2. Calls `POST /api/runAction` with key `/snapshot-store/{flow}/getSnapshot`
3. Displays the returned state alongside the trace

This allows developers to inspect the exact session flow state at any traced point in the conversation.

---

## 10. Files to Create/Modify

### New Files

| File | Description |
|------|-------------|
| `go/ai/x/session_flow.go` | SessionFlow, SessionFlowFunc, SessionFlowParams, Responder, Session |
| `go/ai/x/session_flow_state.go` | SessionFlowState, SessionFlowSnapshot, SessionFlowArtifact, SessionFlowInit, SessionFlowResponse, SessionFlowStreamChunk |
| `go/ai/x/session_flow_options.go` | SessionFlowOption, StreamBidiOption, SnapshotCallback, SnapshotContext |
| `go/ai/x/session_flow_store.go` | SnapshotStore interface, InMemorySnapshotStore |
| `go/ai/x/session_flow_test.go` | Tests |

### Modified Files

| File | Change |
|------|--------|
| `go/genkit/session_flow.go` | Add DefineSessionFlow wrapper |
| `go/core/api/action.go` | Add ActionTypeSessionFlow, ActionTypeSnapshotStore constants |

---

## 11. Design Decisions

### Why Separate SessionFlowState from SessionFlowSnapshot?

**SessionFlowState** is the portable state that flows between client and server:
- Just the data: Messages, Custom, Artifacts
- No IDs, timestamps, or metadata
- Time is implicit: it's either input or output
- Clients manage it however they want

**SessionFlowSnapshot** is a persisted point-in-time capture:
- Has a UUID-based ID
- Has timestamps and metadata (ParentID, TurnIndex)
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

### Why UUID Snapshot IDs?

- **Simplicity**: No need to serialize and hash state
- **Uniqueness**: Every snapshot gets its own ID regardless of content
- **Performance**: No serialization overhead for ID generation

### Why Callback-Based Snapshotting?

Rather than always snapshotting or never snapshotting:

- **Efficiency**: Only snapshot when needed
- **Flexibility**: Different strategies for different use cases
- **User control**: Application decides snapshot granularity
- **Sensible default**: Always snapshots when a store is configured, no callback needed for common case

### Why Does SendArtifact Add to Session?

`SendArtifact()` both streams the artifact to the client and adds it to the session state (replacing by name if a duplicate exists). This prevents a common class of bugs where the developer streams an artifact but forgets to add it to session state, resulting in artifacts being lost across snapshots.

---

## 12. Future Considerations

Out of scope for this design:

- **Snapshot expiration**: Automatic cleanup based on age or count
- **Snapshot compression**: Delta/patch-based storage
- **Snapshot branching**: Tree-structured conversation histories
- **Snapshot annotations**: User-provided labels or descriptions
- **Tool iteration snapshots**: Mid-turn snapshots after tool execution
