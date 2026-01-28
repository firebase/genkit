# Genkit Go Agent with Snapshots - Design Document

## Overview

This document describes the design for the `Agent` primitive in Genkit Go with snapshot-based state management. An Agent is a stateful, multi-turn conversational agent with automatic snapshot persistence and turn semantics.

Snapshots provide:
- **State encapsulation**: Messages, user-defined state, and artifacts in a single serializable unit
- **Resumability**: Start new invocations from any previous snapshot
- **Flexibility**: Support for both client-managed and server-managed state patterns
- **Debugging**: Point-in-time state capture for inspection and replay

This design builds on the bidirectional streaming primitives described in [go-bidi-design.md](go-bidi-design.md).

## Package Location

Agent is an AI concept and belongs in `go/ai/x/` (experimental):

```
go/ai/x/
├── agent.go          # Agent, AgentFunc, AgentParams, Responder
├── agent_options.go  # AgentOption, StreamBidiOption
├── agent_test.go     # Tests
```

Import as `aix "github.com/firebase/genkit/go/ai/x"`.

---

## 1. Core Type Definitions

### 1.1 State and Snapshot Types

**AgentState** is the portable state that flows between client and server. It contains only the data needed for conversation continuity.

**AgentSnapshot** is a persisted point-in-time capture with metadata. It wraps AgentState with additional fields for storage, debugging, and restoration.

```go
// AgentState is the portable conversation state.
type AgentState[State any] struct {
    // Messages is the conversation history.
    Messages []*ai.Message `json:"messages,omitempty"`
    // Custom is the user-defined state associated with this conversation.
    Custom State `json:"custom,omitempty"`
    // Artifacts are named collections of parts produced during the conversation.
    Artifacts []*AgentArtifact `json:"artifacts,omitempty"`
}

// AgentSnapshot is a persisted point-in-time capture of agent state.
type AgentSnapshot[State any] struct {
    // SnapshotID is the unique identifier for this snapshot (content-addressed).
    SnapshotID string `json:"snapshotId"`
    // SessionID identifies the session this snapshot belongs to.
    SessionID string `json:"sessionId"`
    // ParentID is the ID of the previous snapshot in this session's timeline.
    ParentID string `json:"parentId,omitempty"`
    // CreatedAt is when the snapshot was created.
    CreatedAt time.Time `json:"createdAt"`
    // TurnIndex is the turn number when this snapshot was created (0-indexed).
    TurnIndex int `json:"turnIndex"`
    // Event is the snapshot event that triggered this snapshot.
    Event SnapshotEvent `json:"event"`
    // State is the actual conversation state.
    State AgentState[State] `json:"state"`
}

// AgentArtifact represents a named collection of parts produced during a session.
// Examples: generated files, images, code snippets, diagrams, etc.
type AgentArtifact struct {
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
// AgentInput is the input sent to an agent during a conversation turn.
// This wrapper allows future extensibility beyond just messages.
type AgentInput struct {
    // Messages contains the user's input for this turn.
    Messages []*ai.Message `json:"messages,omitempty"`
}

// AgentInit is the input for starting an agent invocation.
// Provide either SnapshotID (to load from store) or State (direct state).
type AgentInit[State any] struct {
    // SnapshotID loads state from a persisted snapshot.
    // Mutually exclusive with State.
    SnapshotID string `json:"snapshotId,omitempty"`
    // State provides direct state for the invocation.
    // Mutually exclusive with SnapshotID.
    State *AgentState[State] `json:"state,omitempty"`
}

// AgentResponse is the output when an agent invocation completes.
type AgentResponse[State any] struct {
    // SessionID identifies the session for this conversation.
    // Use this to list snapshots via store.ListSnapshots(ctx, sessionID).
    SessionID string `json:"sessionId"`
    // State contains the final conversation state.
    State *AgentState[State] `json:"state"`
    // SnapshotIDs contains the IDs of snapshots created during this invocation.
    // Empty if no snapshots were created (callback returned false or not configured).
    SnapshotIDs []string `json:"snapshotIds,omitempty"`
}
```

### 1.3 Stream Types

```go
// AgentStreamChunk represents a single item in the agent's output stream.
// Multiple fields can be populated in a single chunk.
type AgentStreamChunk[Stream any] struct {
    // Chunk contains token-level generation data.
    Chunk *ai.ModelResponseChunk `json:"chunk,omitempty"`
    // Status contains user-defined structured status information.
    // The Stream type parameter defines the shape of this data.
    Status Stream `json:"status,omitempty"`
    // Artifact contains a newly produced artifact.
    Artifact *AgentArtifact `json:"artifact,omitempty"`
    // SnapshotCreated contains the ID of a snapshot that was just persisted.
    SnapshotCreated string `json:"snapshotCreated,omitempty"`
    // EndTurn signals that the agent has finished processing the current input.
    // When true, the client should stop iterating and may send the next input.
    EndTurn bool `json:"endTurn,omitempty"`
}
```

### 1.4 Session

The Session provides mutable working state during an agent invocation. It is propagated via context so that nested operations (tools, sub-agents) can access consistent state.

```go
// Session holds the working state during an agent invocation.
// It is propagated through context and provides read/write access to state.
type Session[State any] struct {
    mu    sync.RWMutex
    id    string
    state AgentState[State]
    store SnapshotStore[State]

    // Snapshot tracking
    lastSnapshot   *AgentSnapshot[State]
    turnIndex      int
    newSnapshotIDs []string // IDs of snapshots created this invocation
}

// ID returns the session identifier.
func (s *Session[State]) ID() string

// State returns a copy of the current agent state.
func (s *Session[State]) State() *AgentState[State]

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

// Artifacts returns the current artifacts.
func (s *Session[State]) Artifacts() []*AgentArtifact

// AddArtifact appends an artifact.
func (s *Session[State]) AddArtifact(artifact *AgentArtifact)

// SetArtifacts replaces the entire artifact list.
func (s *Session[State]) SetArtifacts(artifacts ...*AgentArtifact)

// NewSnapshotIDs returns the IDs of snapshots created during this invocation.
func (s *Session[State]) NewSnapshotIDs() []string

// Context integration
func NewSessionContext[State any](ctx context.Context, s *Session[State]) context.Context
func SessionFromContext[State any](ctx context.Context) *Session[State]
```

### 1.5 Responder

The Responder wraps the output stream with typed methods for sending different kinds of data.

```go
// Responder provides methods for sending data to the agent's output stream.
type Responder[Stream any] struct {
    ch      chan<- *AgentStreamChunk[Stream]
    session *Session[any] // for snapshot notifications
}

// Send sends a complete stream chunk. Use this for full control over the chunk contents.
func (r *Responder[Stream]) Send(chunk *AgentStreamChunk[Stream])

// SendChunk sends a generation chunk (token-level streaming).
func (r *Responder[Stream]) SendChunk(chunk *ai.ModelResponseChunk)

// SendStatus sends a user-defined status update.
func (r *Responder[Stream]) SendStatus(status Stream)

// SendArtifact sends an artifact to the stream.
func (r *Responder[Stream]) SendArtifact(artifact *AgentArtifact)

// EndTurn signals that the agent has finished responding to the current input.
// This triggers a snapshot check (based on the configured callback) and sends
// a chunk with EndTurn: true. The client should check for this field and break
// out of their Receive() loop to send the next input.
func (r *Responder[Stream]) EndTurn()
```

### 1.6 Agent Function and Parameters

```go
// AgentParams contains the parameters passed to an agent function.
// This struct may be extended with additional fields in the future.
type AgentParams[Stream, State any] struct {
    // Session provides access to the working state.
    Session *Session[State]
    // Init contains the initialization data provided when starting the invocation.
    Init *AgentInit[State]
}

// AgentFunc is the function signature for agents.
// Type parameters:
//   - Stream: Type for status updates sent via the responder
//   - State: Type for user-defined state in snapshots
type AgentFunc[Stream, State any] func(
    ctx context.Context,
    inCh <-chan *AgentInput,
    resp *Responder[Stream],
    params *AgentParams[Stream, State],
) error
```

### 1.7 Agent

```go
// Agent is a bidirectional streaming action with automatic snapshot management.
type Agent[Stream, State any] struct {
    *corex.BidiAction[*AgentInit[State], *AgentInput, *AgentResponse[State], *AgentStreamChunk[Stream]]
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
    GetSnapshot(ctx context.Context, snapshotID string) (*AgentSnapshot[State], error)
    // SaveSnapshot persists a snapshot.
    // The snapshot ID is computed from the content (content-addressed).
    // If a snapshot with the same ID exists, this is a no-op.
    SaveSnapshot(ctx context.Context, snapshot *AgentSnapshot[State]) error
    // ListSnapshots returns snapshots for a session, ordered by creation time.
    ListSnapshots(ctx context.Context, sessionID string) ([]*AgentSnapshot[State], error)
}
```

### 2.2 In-Memory Implementation

```go
// InMemorySnapshotStore provides a thread-safe in-memory snapshot store.
type InMemorySnapshotStore[State any] struct {
    snapshots map[string]*AgentSnapshot[State]
    mu        sync.RWMutex
}

func NewInMemorySnapshotStore[State any]() *InMemorySnapshotStore[State]
```

---

## 3. Snapshot Callbacks

### 3.1 Callback Types

```go
// SnapshotEvent identifies when a snapshot opportunity occurs.
type SnapshotEvent int

const (
    // SnapshotEventTurnEnd occurs after resp.EndTurn() is called.
    SnapshotEventTurnEnd SnapshotEvent = iota
    // SnapshotEventInvocationEnd occurs when the agent function returns.
    SnapshotEventInvocationEnd
)

// SnapshotContext provides context for snapshot decision callbacks.
type SnapshotContext[State any] struct {
    // Event is the snapshot event that triggered this callback.
    Event SnapshotEvent
    // State is the current state that will be snapshotted if the callback returns true.
    State *AgentState[State]
    // PrevState is the state at the last snapshot, or nil if none exists.
    PrevState *AgentState[State]
    // TurnIndex is the current turn number.
    TurnIndex int
}

// SnapshotCallback decides whether to create a snapshot at a given event.
type SnapshotCallback[State any] func(ctx context.Context, sc *SnapshotContext[State]) bool
```

### 3.2 Convenience Callbacks

```go
// SnapshotAlways returns a callback that always creates snapshots.
func SnapshotAlways[State any]() SnapshotCallback[State] {
    return func(ctx context.Context, sc *SnapshotContext[State]) bool {
        return true
    }
}

// SnapshotNever returns a callback that never creates snapshots.
func SnapshotNever[State any]() SnapshotCallback[State] {
    return func(ctx context.Context, sc *SnapshotContext[State]) bool {
        return false
    }
}

// SnapshotOn returns a callback that creates snapshots only for specified events.
func SnapshotOn[State any](events ...SnapshotEvent) SnapshotCallback[State] {
    eventSet := make(map[SnapshotEvent]bool)
    for _, e := range events {
        eventSet[e] = true
    }
    return func(ctx context.Context, sc *SnapshotContext[State]) bool {
        return eventSet[sc.Event]
    }
}
```

---

## 4. API Surface

### 4.1 Defining Agents

```go
// DefineAgent creates an Agent with automatic snapshot management and registers it.
func DefineAgent[Stream, State any](
    r api.Registry,
    name string,
    fn AgentFunc[Stream, State],
    opts ...AgentOption[State],
) *Agent[Stream, State]

// AgentOption configures an Agent.
type AgentOption[State any] interface {
    applyAgent(*agentOptions[State]) error
}

// WithSnapshotStore sets the store for persisting snapshots.
func WithSnapshotStore[State any](store SnapshotStore[State]) AgentOption[State]

// WithSnapshotCallback configures when snapshots are created.
// If not provided, snapshots are never created automatically.
func WithSnapshotCallback[State any](cb SnapshotCallback[State]) AgentOption[State]
```

### 4.2 Starting Connections

```go
// StreamBidiOption configures a StreamBidi call.
type StreamBidiOption[State any] interface {
    applyStreamBidi(*streamBidiOptions[State]) error
}

// WithState sets the initial state for the invocation.
// Use this for client-managed state where the client sends state directly.
func WithState[State any](state *AgentState[State]) StreamBidiOption[State]

// WithSnapshotID loads state from a persisted snapshot by ID.
// Use this for server-managed state where snapshots are stored.
func WithSnapshotID[State any](id string) StreamBidiOption[State]

// StreamBidi starts a new agent invocation.
func (a *Agent[Stream, State]) StreamBidi(
    ctx context.Context,
    opts ...StreamBidiOption[State],
) (*AgentConnection[Stream, State], error)
```

### 4.3 Agent Connection

```go
// AgentConnection wraps BidiConnection with agent-specific functionality.
type AgentConnection[Stream, State any] struct {
    conn *corex.BidiConnection[*AgentInput, *AgentResponse[State], *AgentStreamChunk[Stream]]
}

// Send sends an AgentInput to the agent.
// Use this for full control over the input structure.
func (c *AgentConnection[Stream, State]) Send(input *AgentInput) error

// SendMessages sends messages to the agent.
// This is a convenience method that wraps messages in an AgentInput.
func (c *AgentConnection[Stream, State]) SendMessages(messages ...*ai.Message) error

// SendText sends a single user text message to the agent.
// This is a convenience method that creates a user message and wraps it in AgentInput.
func (c *AgentConnection[Stream, State]) SendText(text string) error

// Close signals that no more inputs will be sent.
func (c *AgentConnection[Stream, State]) Close() error

// Receive returns an iterator for receiving stream chunks.
func (c *AgentConnection[Stream, State]) Receive() iter.Seq2[*AgentStreamChunk[Stream], error]

// Output returns the final response after the agent completes.
func (c *AgentConnection[Stream, State]) Output() (*AgentResponse[State], error)

// Done returns a channel closed when the connection completes.
func (c *AgentConnection[Stream, State]) Done() <-chan struct{}
```

### 4.4 High-Level Genkit API

```go
// In go/genkit/agent.go

func DefineAgent[Stream, State any](
    g *Genkit,
    name string,
    fn aix.AgentFunc[Stream, State],
    opts ...aix.AgentOption[State],
) *aix.Agent[Stream, State]
```

---

## 5. Snapshot Lifecycle

### 5.1 Snapshot Points

Snapshots are created at two points:

| Event | Trigger | Description |
|-------|---------|-------------|
| `SnapshotEventTurnEnd` | `resp.EndTurn()` | After processing user input and generating a response |
| `SnapshotEventInvocationEnd` | Agent function returns | Final state capture when invocation completes |

At each point:
1. The snapshot callback is invoked
2. If callback returns true:
   - Compute snapshot ID (SHA256 of JSON-serialized state)
   - Persist to store (no-op if ID already exists)
   - Send `SnapshotCreated` on the stream
   - Record ID in `session.newSnapshotIDs`

### 5.2 Snapshot ID Computation

Snapshot IDs are content-addressed using SHA256 of the state (not the full snapshot with metadata):

```go
func computeSnapshotID[State any](state *AgentState[State]) string {
    data, _ := json.Marshal(state)
    hash := sha256.Sum256(data)
    return hex.EncodeToString(hash[:])
}
```

Benefits:
- **Deduplication**: Identical states produce identical IDs
- **Verification**: State integrity can be verified against ID
- **Determinism**: No dependency on timestamps for uniqueness

### 5.3 Resuming from Snapshots

When `WithSnapshotID` is provided to `StreamBidi`:

1. Load the snapshot from the store
2. Extract the `AgentState` from the snapshot
3. Initialize the session with that state (messages, state, artifacts)
4. New snapshots will reference this as the parent
5. Conversation continues from the restored state

When `WithState` is provided to `StreamBidi`:

1. Use the provided `AgentState` directly
2. Initialize the session with that state
3. No parent snapshot reference (client-managed mode)

---

## 6. Internal Flow

### 6.1 Agent Wrapping

The user's `AgentFunc` returns `error`. The framework wraps this to produce `AgentResponse`:

```go
// Simplified internal logic
func (a *Agent[Stream, State]) runWrapped(
    ctx context.Context,
    init *AgentInit[State],
    inCh <-chan *AgentInput,
    outCh chan<- *AgentStreamChunk[Stream],
) (*AgentResponse[State], error) {
    // Initialize session from snapshot
    session := newSessionFromInit(init, a.store)
    ctx = NewSessionContext(ctx, session)

    // Create responder with snapshot callback
    responder := &Responder[Stream]{
        ch:               outCh,
        session:          session,
        snapshotCallback: a.snapshotCallback,
        store:            a.store,
    }

    params := &AgentParams[Stream, State]{
        Session: session,
        Init:    init,
    }

    // Run user function
    err := a.fn(ctx, params, inCh, responder)
    if err != nil {
        return nil, err
    }

    // Trigger invocation-end snapshot
    responder.triggerSnapshot(SnapshotEventInvocationEnd)

    // Build response from session state
    return &AgentResponse[State]{
        State: session.toState(),
    }, nil
}
```

### 6.2 Turn Signaling

When `resp.EndTurn()` is called:

1. Trigger snapshot callback with `SnapshotEventTurnEnd`
2. If callback returns true, create and persist snapshot
3. Send `SnapshotCreated` notification on stream
4. Send end-of-turn signal so consumer's `Receive()` exits

```go
func (r *Responder[Stream]) EndTurn() {
    // Trigger snapshot check
    r.triggerSnapshot(SnapshotEventTurnEnd)

    // Signal end of turn to client
    r.ch <- &AgentStreamChunk[Stream]{EndTurn: true}
}
```

---

## 7. Example Usage

### 7.1 Chat Agent with Snapshots

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

// ChatState holds user-defined state for the chat agent.
type ChatState struct {
    UserPreferences map[string]string `json:"userPreferences,omitempty"`
    TopicHistory    []string          `json:"topicHistory,omitempty"`
}

// ChatStatus represents status updates streamed to the client.
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

    chatAgent := genkit.DefineAgent(g, "chatAgent",
        func(ctx context.Context, inCh <-chan *aix.AgentInput, resp *aix.Responder[ChatStatus], params *aix.AgentParams[ChatStatus, ChatState]) error {
            sess := params.Session

            for input := range inCh {
                // Add user messages to session
                sess.AddMessages(input.Messages...)

                // Send status update
                resp.SendStatus(ChatStatus{Phase: "generating"})

                // Generate response
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

                // Update custom state
                custom := sess.Custom()
                custom.TopicHistory = append(custom.TopicHistory, extractTopic(input.Messages))
                sess.SetCustom(custom)

                resp.SendStatus(ChatStatus{Phase: "complete"})
                resp.EndTurn() // Triggers snapshot check
            }

            return nil
        },
        aix.WithSnapshotStore(store),
        aix.WithSnapshotCallback(aix.SnapshotOn[ChatState](
            aix.SnapshotEventTurnEnd,
            aix.SnapshotEventInvocationEnd,
        )),
    )

    // Start new conversation
    conn, _ := chatAgent.StreamBidi(ctx)

    conn.SendText("Hello! Tell me about Go programming.")
    for chunk, err := range conn.Receive() {
        if err != nil {
            panic(err)
        }
        if chunk.Chunk != nil {
            fmt.Print(chunk.Chunk.Text())
        }
        if chunk.SnapshotCreated != "" {
            fmt.Printf("\n[Snapshot created: %s]\n", chunk.SnapshotCreated)
        }
        if chunk.EndTurn {
            break // Agent finished processing, ready for next input
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
    fmt.Printf("\nSession ID: %s\n", response.SessionID)
    fmt.Printf("Messages in history: %d\n", len(response.State.Messages))

    // List all snapshots for this session
    snapshots, _ := store.ListSnapshots(ctx, response.SessionID)
    fmt.Printf("Total snapshots in session: %d\n", len(snapshots))
}
```

### 7.2 Resuming from a Snapshot

```go
// Later, resume from a saved snapshot
snapshotID := "abc123..."

conn, _ := chatAgent.StreamBidi(ctx, aix.WithSnapshotID[ChatState](snapshotID))

conn.SendText("Continue our discussion about channels")
for chunk, err := range conn.Receive() {
    // ... handle response ...
}
```

### 7.3 Client-Managed State

For clients that manage their own state (e.g., web apps with local storage):

```go
// Client sends state directly on each invocation
clientState := &aix.AgentState[ChatState]{
    Messages: previousMessages,
    Custom:    ChatState{UserPreferences: prefs},
}

conn, _ := chatAgent.StreamBidi(ctx, aix.WithState(clientState))

// ... interact ...

response, _ := conn.Output()
// Client stores response.State locally for next invocation
```

### 7.4 Agent with Artifacts

```go
type CodeState struct {
    Language string `json:"language"`
}

type CodeStatus struct {
    Phase string `json:"phase"`
}

codeAgent := genkit.DefineAgent(g, "codeAgent",
    func(ctx context.Context, inCh <-chan *aix.AgentInput, resp *aix.Responder[CodeStatus], params *aix.AgentParams[CodeStatus, CodeState]) error {
        sess := params.Session

        for input := range inCh {
            sess.AddMessages(input.Messages...)

            // Generate code...
            generatedCode := "func main() { fmt.Println(\"Hello\") }"

            resp.SendStatus(CodeStatus{Phase: "code_generated"})

            // Send artifact
            resp.SendArtifact(&aix.AgentArtifact{
                Name: "main.go",
                Parts: []*ai.Part{ai.NewTextPart(generatedCode)},
                Metadata: map[string]any{"language": "go"},
            })

            sess.AddMessages(ai.NewModelTextMessage("Here's the code you requested."))
            resp.EndTurn()
        }

        return nil
    },
    aix.WithSnapshotStore(store),
    aix.WithSnapshotCallback(aix.SnapshotAlways[CodeState]()),
)
```

---

## 8. Tracing Integration

When a snapshot is created, metadata is recorded on the current trace span:

- `genkit:metadata:snapshotId` - The snapshot ID
- `genkit:metadata:agent` - The agent name (e.g., `chatAgent`)

This enables the Dev UI to correlate traces with snapshots and fetch snapshot data via the reflection API.

**Recording snapshot in span:**

```go
func (r *Responder[Stream]) triggerSnapshot(event SnapshotEvent) {
    // ... create snapshot ...

    if snapshot != nil {
        // Record in current span for Dev UI correlation
        span := trace.SpanFromContext(r.ctx)
        span.SetAttributes(
            attribute.String("genkit:metadata:snapshotId", snapshot.SnapshotID),
            attribute.String("genkit:metadata:agent", r.agentName),
        )
    }
}
```

---

## 9. Reflection API Integration

Snapshot stores are exposed via the reflection API for Dev UI access.

### 9.1 Action Registration

When `DefineAgent` is called with `WithSnapshotStore`, actions are registered:

| Action | Key | Input | Returns |
|--------|-----|-------|---------|
| getSnapshot | `/snapshot-store/{agent}/getSnapshot` | `{snapshotId: string}` | `AgentSnapshot[State]` |
| listSnapshots | `/snapshot-store/{agent}/listSnapshots` | `{sessionId: string}` | `[]*AgentSnapshot[State]` |

### 9.2 Action Type

```go
const ActionTypeSnapshotStore api.ActionType = "snapshot-store"
```

### 9.3 Dev UI Flow

1. Dev UI receives a trace with `snapshotId` and `agent` in span metadata
2. Calls `POST /api/runAction` with key `/snapshot-store/{agent}/getSnapshot`
3. Displays the returned state alongside the trace

This allows developers to inspect the exact agent state at any traced point in the conversation.

---

## 10. Files to Create/Modify

### New Files

| File | Description |
|------|-------------|
| `go/ai/x/agent.go` | Agent, AgentFunc, AgentParams, Responder, Session |
| `go/ai/x/agent_state.go` | AgentState, AgentSnapshot, AgentArtifact, AgentInit, AgentResponse, AgentStreamChunk |
| `go/ai/x/agent_options.go` | AgentOption, StreamBidiOption, SnapshotCallback, SnapshotContext |
| `go/ai/x/agent_store.go` | SnapshotStore interface, InMemorySnapshotStore |
| `go/ai/x/agent_test.go` | Tests |

### Modified Files

| File | Change |
|------|--------|
| `go/genkit/agent.go` | Add DefineAgent wrapper |
| `go/core/api/action.go` | Add ActionTypeAgent, ActionTypeSnapshotStore constants |

---

## 11. Design Decisions

### Why Separate AgentState from AgentSnapshot?

**AgentState** is the portable state that flows between client and server:
- Just the data: Messages, State, Artifacts
- No IDs, timestamps, or metadata
- Time is implicit: it's either input or output
- Clients manage it however they want

**AgentSnapshot** is a persisted point-in-time capture:
- Has an ID (content-addressed)
- Has timestamps and metadata (ParentID, TurnIndex, Event)
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

### Why Content-Addressed Snapshot IDs?

- **Deduplication**: Identical states don't create duplicate snapshots
- **Verification**: Snapshot integrity can be verified
- **Determinism**: Same state always produces same ID, regardless of timing

### Why Callback-Based Snapshotting?

Rather than always snapshotting or never snapshotting:

- **Efficiency**: Only snapshot when needed
- **Flexibility**: Different strategies for different use cases
- **User control**: Application decides snapshot granularity

---

## 12. Open Questions

### Artifact and Session State Relationship

**TODO**: Should `resp.SendArtifact()` automatically add the artifact to session state?

Options:
1. **Automatic**: `SendArtifact()` adds to session AND streams to client
2. **Manual**: User must call both `sess.AddArtifact()` and `resp.SendArtifact()`
3. **Configurable**: Option to control the behavior

Considerations:
- Automatic reduces boilerplate and prevents forgetting one call
- Manual provides more control (e.g., stream without persisting)
- Similar question applies to `SendChunk()` and message accumulation

---

## 13. Future Considerations

Out of scope for this design:

- **Snapshot expiration**: Automatic cleanup based on age or count
- **Snapshot compression**: Delta/patch-based storage
- **Snapshot branching**: Tree-structured conversation histories
- **Snapshot annotations**: User-provided labels or descriptions
- **Tool iteration snapshots**: Snapshots after tool execution (could be added as new SnapshotEvent)
