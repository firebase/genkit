# Genkit Go Session Snapshots - Design Document

## Overview

This document describes the design for session snapshots in Genkit Go. This feature builds on the bidirectional streaming primitives described in [go-bidi-design.md](./go-bidi-design.md), extending the session management system with point-in-time state capture and restoration capabilities.

Session snapshots enable:
- **Debugging**: Inspect session state at any point in a conversation
- **Restoration**: Resume conversations from previous states
- **Dev UI Integration**: Display state alongside traces for better observability

---

# Part 1: API Definitions

## 1. Core Types

### 1.1 Snapshot

```go
// Snapshot represents a point-in-time capture of session state.
// Snapshots are immutable once created.
type Snapshot[S any] struct {
    // ID is the content-addressed identifier (SHA256 of JSON-serialized state).
    ID string `json:"id"`

    // ParentID is the ID of the previous snapshot in this session's timeline.
    // Empty for the first snapshot in a session.
    ParentID string `json:"parentId,omitempty"`

    // SessionID is the session this snapshot belongs to.
    SessionID string `json:"sessionId"`

    // CreatedAt is when the snapshot was created.
    CreatedAt time.Time `json:"createdAt"`

    // State is the complete session state at the time of the snapshot.
    State S `json:"state"`

    // Index is a monotonically increasing sequence number for ordering snapshots
    // within a session. This is independent of turn boundaries.
    Index int `json:"index"`

    // TurnIndex is the turn number when this snapshot was created (0-indexed).
    // Turn 0 is after the first user input and agent response.
    TurnIndex int `json:"turnIndex"`

    // Event is the snapshot event that triggered this snapshot.
    Event SnapshotEvent `json:"event"`

    // Orphaned indicates this snapshot is no longer on the main timeline.
    // This occurs when a user restores from an earlier snapshot, causing
    // all subsequent snapshots to be marked as orphaned.
    Orphaned bool `json:"orphaned,omitempty"`
}
```

### 1.2 SnapshotEvent

```go
// SnapshotEvent identifies when a snapshot opportunity occurs.
type SnapshotEvent int

const (
    // SnapshotEventTurnEnd occurs after resp.EndTurn() is called,
    // when control returns to the user.
    SnapshotEventTurnEnd SnapshotEvent = iota

    // SnapshotEventToolIterationEnd occurs after all tool calls in a single
    // model iteration complete, before the results are sent back to the model.
    // This captures state after tools have mutated it but before the next
    // model response.
    SnapshotEventToolIterationEnd

    // SnapshotEventInvocationEnd occurs when the agent function returns,
    // capturing the final state of the invocation.
    SnapshotEventInvocationEnd
)
```

### 1.3 SnapshotContext

```go
// SnapshotContext provides context for snapshot decision callbacks.
type SnapshotContext[S any] struct {
    // Event is the snapshot event that triggered this callback.
    Event SnapshotEvent

    // State is the current session state that will be snapshotted if the callback returns true.
    State S

    // PrevState is the state at the last snapshot, or nil if no previous snapshot exists.
    // Useful for comparing states to decide whether a snapshot is needed.
    PrevState *S

    // Index is the sequence number this snapshot would have if created.
    Index int

    // TurnIndex is the current turn number.
    TurnIndex int
}
```

### 1.4 SnapshotCallback

```go
// SnapshotCallback decides whether to create a snapshot at a given event.
// It receives the context and snapshot context, returning true if a snapshot
// should be created.
//
// The callback is invoked at each snapshot opportunity. Users can filter
// by event type, inspect state, compare with previous state, or apply any
// custom logic to decide.
type SnapshotCallback[S any] = func(ctx context.Context, snap *SnapshotContext[S]) bool
```

---

## 2. Store Interface

The existing `Store[S]` interface in `go/core/x/session` is extended with snapshot methods:

```go
type Store[S any] interface {
    // Existing session methods
    Get(ctx context.Context, sessionID string) (*Data[S], error)
    Save(ctx context.Context, sessionID string, data *Data[S]) error

    // GetSnapshot retrieves a snapshot by ID. Returns nil if not found.
    GetSnapshot(ctx context.Context, snapshotID string) (*Snapshot[S], error)

    // SaveSnapshot persists a snapshot. If a snapshot with the same ID already
    // exists (content-addressed deduplication), this is a no-op and returns nil.
    SaveSnapshot(ctx context.Context, snapshot *Snapshot[S]) error

    // ListSnapshots returns snapshots for a session, ordered by Index ascending.
    // If includeOrphaned is false, only active (non-orphaned) snapshots are returned.
    ListSnapshots(ctx context.Context, sessionID string, includeOrphaned bool) ([]*Snapshot[S], error)

    // InvalidateSnapshotsAfter marks all snapshots with Index > afterIndex as orphaned.
    // Called when restoring from a snapshot to mark "future" snapshots as no longer active.
    InvalidateSnapshotsAfter(ctx context.Context, sessionID string, afterIndex int) error
}
```

---

## 3. Agent Options

### 3.1 WithSnapshotCallback

```go
// WithSnapshotCallback configures when snapshots are created.
// The callback is invoked at each snapshot opportunity (turn end, tool iteration
// end, invocation end) and decides whether to create a snapshot.
//
// If no callback is provided, snapshots are never created automatically.
// Requires WithSessionStore to be configured; otherwise snapshots cannot be persisted.
func WithSnapshotCallback[S any](cb SnapshotCallback[S]) AgentOption[S]
```

### 3.2 Convenience Callbacks

```go
// SnapshotAlways returns a callback that always creates snapshots at all events.
func SnapshotAlways[S any]() SnapshotCallback[S] {
    return func(ctx context.Context, snap *SnapshotContext[S]) bool {
        return true
    }
}

// SnapshotNever returns a callback that never creates snapshots.
// This is the default behavior when no callback is configured.
func SnapshotNever[S any]() SnapshotCallback[S] {
    return func(ctx context.Context, snap *SnapshotContext[S]) bool {
        return false
    }
}

// SnapshotOn returns a callback that creates snapshots only for the specified events.
func SnapshotOn[S any](events ...SnapshotEvent) SnapshotCallback[S] {
    eventSet := make(map[SnapshotEvent]bool)
    for _, e := range events {
        eventSet[e] = true
    }
    return func(ctx context.Context, snap *SnapshotContext[S]) bool {
        return eventSet[snap.Event]
    }
}

// SnapshotOnChange returns a callback that creates snapshots only when state has changed
// since the last snapshot.
func SnapshotOnChange[S any](events ...SnapshotEvent) SnapshotCallback[S] {
    eventSet := make(map[SnapshotEvent]bool)
    for _, e := range events {
        eventSet[e] = true
    }
    return func(ctx context.Context, snap *SnapshotContext[S]) bool {
        if !eventSet[snap.Event] {
            return false
        }
        // Always snapshot if this is the first one
        if snap.PrevState == nil {
            return true
        }
        // Compare by computing content-addressed IDs
        return computeStateHash(snap.State) != computeStateHash(*snap.PrevState)
    }
}
```

---

## 4. Invocation Options

### 4.1 WithSnapshotID

```go
// WithSnapshotID specifies a snapshot to restore from when starting the agent.
// This loads the session state from the snapshot and marks all subsequent
// snapshots in that session as orphaned.
//
// The session continues with the same session ID as the snapshot.
//
// Requires the agent to be configured with WithSessionStore; returns an error
// if no store is available to load the snapshot from.
func WithSnapshotID[Init any](id string) BidiOption[Init]
```

---

## 5. AgentOutput

```go
// AgentOutput wraps the output with session info for persistence.
type AgentOutput[State, Out any] struct {
    SessionID   string     `json:"sessionId"`
    Output      Out        `json:"output"`
    State       State      `json:"state"`
    Artifacts   []Artifact `json:"artifacts,omitempty"`

    // SnapshotIDs contains the IDs of all snapshots created during this agent invocation.
    // Empty if no snapshots were created (callback returned false or not configured).
    SnapshotIDs []string `json:"snapshotIds,omitempty"`
}
```

---

# Part 2: Behaviors

## 6. Snapshot Creation

Snapshots are created at three points, each corresponding to a `SnapshotEvent`:

| Event | Trigger |
|-------|---------|
| `SnapshotEventTurnEnd` | When `resp.EndTurn()` is called, signaling control returns to the user |
| `SnapshotEventToolIterationEnd` | After all tool calls in a single model iteration complete |
| `SnapshotEventInvocationEnd` | When the agent function returns |

At each point, the snapshot callback is invoked. If it returns true:
1. Compute the snapshot ID by hashing the state (SHA256)
2. Create the snapshot with the next sequence index
3. Set the parent snapshot ID to the previous snapshot (if any)
4. Persist to the store (no-op if ID already exists due to identical state)
5. Record the snapshot ID in the current trace span

### 6.1 Snapshot ID Computation

Snapshot IDs are content-addressed using SHA256 of the JSON-serialized state:
- **Deduplication**: Identical states produce identical IDs
- **Verification**: State integrity can be verified against the ID
- **Determinism**: No dependency on timestamps for uniqueness

---

## 7. Snapshot Restoration

When `WithSnapshotID` is provided to `StreamBidi`:

1. Load the snapshot from the store
2. Call `InvalidateSnapshotsAfter(sessionID, snapshot.Index)` to orphan subsequent snapshots
3. Update the session with the snapshot's state
4. Continue from the snapshot's turn and index
5. Track the snapshot ID as the parent for new snapshots

### 7.1 Option Validation

| Combination | Result |
|-------------|--------|
| `WithSnapshotID` + `WithInit` | **Error**: Cannot specify initial state when restoring |
| `WithSnapshotID` + `WithSessionID` (mismatched) | **Error**: Session ID must match snapshot |
| `WithSnapshotID` + `WithSessionID` (matching) | Allowed but redundant |

---

## 8. Tracing Integration

When a snapshot is created, span metadata is recorded:
- `genkit:metadata:snapshotId` - The snapshot ID
- `genkit:metadata:agent` - The agent name (e.g., `chatAgent`)

This enables the Dev UI to fetch snapshot data via the reflection API.

---

# Part 3: Examples

## 9. Usage Examples

### 9.1 Defining an Agent with Snapshots

```go
type ChatState struct {
    Messages []*ai.Message `json:"messages"`
}

chatAgent := genkit.DefineAgent(g, "chatAgent",
    func(ctx context.Context, sess *session.Session[ChatState], inCh <-chan string, resp *corex.Responder[string]) (corex.AgentResult[string], error) {
        state := sess.State()

        for input := range inCh {
            state.Messages = append(state.Messages, ai.NewUserTextMessage(input))
            resp := generateResponse(ctx, g, state.Messages)
            state.Messages = append(state.Messages, resp.Message)
            sess.UpdateState(ctx, state)
            resp.EndTurn()  // SnapshotEventTurnEnd fires here
        }

        return corex.AgentResult[string]{Output: "done"}, nil
        // SnapshotEventInvocationEnd fires after return
    },
    corex.WithSessionStore(store),
    corex.WithSnapshotCallback(session.SnapshotOn[ChatState](
        session.SnapshotEventTurnEnd,
        session.SnapshotEventInvocationEnd,
    )),
)
```

### 9.2 Restoring from a Snapshot

```go
snapshotID := previousOutput.SnapshotIDs[0]

conn, _ := chatAgent.StreamBidi(ctx,
    corex.WithSnapshotID[ChatState](snapshotID),
)

conn.Send("Actually, tell me about channels instead")
// ... conversation continues from restored state ...
```

### 9.3 Custom Snapshot Callback

```go
// Snapshot every 5 messages at turn end, always at invocation end
corex.WithSnapshotCallback(func(ctx context.Context, snap *session.SnapshotContext[ChatState]) bool {
    switch snap.Event {
    case session.SnapshotEventTurnEnd:
        return len(snap.State.Messages) % 5 == 0
    case session.SnapshotEventInvocationEnd:
        return true
    default:
        return false
    }
})
```

### 9.4 Snapshot Only When State Changed

```go
// Only snapshot if messages have been added since last snapshot
corex.WithSnapshotCallback(func(ctx context.Context, snap *session.SnapshotContext[ChatState]) bool {
    if snap.Event != session.SnapshotEventTurnEnd {
        return false
    }
    // Always snapshot if this is the first one
    if snap.PrevState == nil {
        return true
    }
    // Only snapshot if message count increased
    return len(snap.State.Messages) > len(snap.PrevState.Messages)
})
```

### 9.5 Snapshot Based on Index

```go
// Snapshot every 3rd snapshot opportunity
corex.WithSnapshotCallback(func(ctx context.Context, snap *session.SnapshotContext[ChatState]) bool {
    return snap.Index % 3 == 0
})
```

### 9.6 Listing Snapshots

```go
activeSnapshots, _ := store.ListSnapshots(ctx, sessionID, false)
allSnapshots, _ := store.ListSnapshots(ctx, sessionID, true)  // includes orphaned
```

---

# Part 4: Implementation Details

## 10. Reflection API Integration

Session stores are exposed via the reflection API for Dev UI access.

### 10.1 Action Registration

When `DefineAgent` is called with `WithSessionStore`, actions are registered:

| Action | Key | Returns |
|--------|-----|---------|
| getSnapshot | `/session-store/{agent}/getSnapshot` | `Snapshot[S]` |
| listSnapshots | `/session-store/{agent}/listSnapshots` | `[]*Snapshot[S]` |
| getSession | `/session-store/{agent}/getSession` | `*Data[S]` |

### 10.2 Action Type

```go
const ActionTypeSessionStore api.ActionType = "session-store"
```

### 10.3 Dev UI Flow

1. Dev UI extracts `snapshotId` and `agent` from span metadata
2. Calls `POST /api/runAction` with key `/session-store/{agent}/getSnapshot`
3. Displays the returned state alongside the trace

---

## 11. Session Snapshot Fields

The `Session` struct is extended with fields to track snapshot state. These are persisted with the session so that loading a session restores the snapshot tracking state.

```go
type Session[S any] struct {
    // ... existing fields (id, state, store, mu) ...

    // LastSnapshot is the most recent snapshot for this session.
    // Used to derive ParentID (LastSnapshot.ID), PrevState (LastSnapshot.State),
    // and next index (LastSnapshot.Index + 1).
    // Nil if no snapshots have been created.
    LastSnapshot *Snapshot[S] `json:"lastSnapshot,omitempty"`

    // TurnIndex tracks the current turn number.
    TurnIndex int `json:"turnIndex"`
}
```

The `snapshotIDs` list (for `AgentOutput.SnapshotIDs`) is tracked transiently during an invocation and does not need to be persisted.

When building `SnapshotContext` for the callback:
- `PrevState` = `session.LastSnapshot.State` (or nil if `LastSnapshot` is nil)
- `Index` = `session.LastSnapshot.Index + 1` (or 0 if `LastSnapshot` is nil)
- `ParentID` for new snapshot = `session.LastSnapshot.ID` (or empty if nil)

---

## 12. Tool Iteration Snapshot Mechanism

The `SnapshotEventToolIterationEnd` event requires coordination between the agent layer (typed state) and Generate layer (untyped).

This is accomplished via a context-based trigger:

1. Agent layer creates a closure capturing the typed callback
2. Stores an untyped trigger function in context
3. Generate calls `TriggerSnapshot(ctx, SnapshotEventToolIterationEnd)` after tool iterations
4. Trigger retrieves session from context, gets state, invokes callback
5. If callback returns true, snapshot is created

This keeps Generate decoupled from session types.

---

# Part 5: Design Decisions

## 13. Rationale

### Why a Single Callback with Event Types?

Rather than separate options for each trigger:
- **Extensibility**: New events can be added without new options
- **Flexibility**: Filter by event AND inspect state in one place
- **Composability**: Logic like "every N messages at turn end, always at invocation end" is natural

### Why Content-Addressed IDs?

- **Automatic deduplication**: Identical states share the same snapshot
- **Verification**: State integrity can be verified against the ID
- **Determinism**: No dependency on sequence numbers or timestamps

### Why Orphaned Instead of Deleted?

When restoring from an earlier snapshot, subsequent snapshots are marked orphaned:
- **Audit trail**: Complete history preserved for debugging
- **Recovery**: Accidentally orphaned snapshots can be recovered
- **Visualization**: Dev UI can show the full conversation tree

### Why IDs Only in Traces?

- **Lightweight traces**: Avoid bloating with large state objects
- **Single source of truth**: State lives in the session store
- **On-demand retrieval**: Dev UI fetches when needed

### Why Both Index and TurnIndex?

- **Index**: Monotonically increasing for ordering and invalidation
- **TurnIndex**: Human-comprehensible ("after turn 3")

### Why Separate Session and Snapshot?

- **Session state**: Working copy that changes frequently
- **Snapshots**: Explicit, immutable captures (like git commits)

This provides efficiency (not every change needs snapshot overhead) and user control via callbacks.

---

## 14. Future Considerations

Out of scope for this design:

- **Snapshot expiration**: Automatic cleanup based on age or count
- **Snapshot compression**: Delta/patch-based storage
- **Snapshot annotations**: User-provided labels or descriptions
