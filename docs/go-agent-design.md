# Genkit Go Agent - Design Document

## Overview

This document describes the design for the `Agent` primitive in Genkit Go. An Agent is a stateful, multi-turn conversational agent with automatic session persistence and turn semantics.

For the underlying bidirectional streaming primitives (BidiAction, BidiFlow, BidiModel), see [go-bidi-design.md](go-bidi-design.md).

## Package Location

Agent is an AI concept and belongs in `go/ai/x/` (experimental):

```
go/ai/x/
├── agent.go          # Agent, AgentFunc, AgentOutput, AgentResult
├── agent_options.go  # AgentOption types
├── agent_test.go     # Tests
```

Import as `aix "github.com/firebase/genkit/go/ai/x"`.

---

## 1. Core Type Definitions

### 1.1 Responder

`Responder` wraps the output channel for agents, providing methods to send data and signal turn boundaries.

```go
// Responder wraps the output channel with turn signaling for multi-turn agents.
type Responder[T any] struct {
    ch chan<- streamChunk[T]  // internal, unexported
}

// Send sends a streamed chunk to the consumer.
func (r *Responder[T]) Send(data T)

// EndTurn signals that the agent has finished responding to the current input.
// The consumer's Receive() iterator will exit, allowing them to send the next input.
func (r *Responder[T]) EndTurn()
```

### 1.2 Agent Types

> **Note:** The `AgentOutput`, `AgentResult`, and `Artifact` types are generated from the source of truth Zod schemas in `genkit-tools` shared between runtimes.

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
    *corex.BidiFlow[State, In, AgentOutput[State, Out], Stream]
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

### 2.1 Defining Agents

```go
// In go/ai/x/agent.go

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

### 2.2 Starting Connections

Agent uses the same `StreamBidi` method as BidiAction and BidiFlow. Session ID is a connection option, and initial state is passed via `WithInit`:

```go
func (a *Agent[State, In, Out, Stream]) StreamBidi(
    ctx context.Context,
    opts ...corex.BidiOption[State],
) (*corex.BidiConnection[In, AgentOutput[State, Out], Stream], error)

// BidiOption from go/core/x - also used by Agent
// WithInit provides initialization data for the bidi action.
// For Agent, this sets the initial state for new sessions.
func WithInit[Init any](init Init) BidiOption[Init]

// WithSessionID specifies an existing session ID to resume.
// If the session exists in the store, it is loaded (WithInit is ignored).
// If the session doesn't exist, a new session is created with this ID.
// If not provided, a new UUID is generated for new sessions.
func WithSessionID[Init any](id string) BidiOption[Init]
```

### 2.3 High-Level Genkit API

```go
// In go/genkit/bidi.go

func DefineAgent[State, In, Out, Stream any](
    g *Genkit,
    name string,
    fn aix.AgentFunc[State, In, Out, Stream],
    opts ...aix.AgentOption[State],
) *aix.Agent[State, In, Out, Stream]
```

---

## 3. Session Management

### 3.1 Using StreamBidi with Agent

```go
// Define once at startup
chatAgent := genkit.DefineAgent(g, "chatAgent",
    myAgentFunc,
    aix.WithSessionStore(store),
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

### 3.3 Session Integration

Use existing `Session` and `Store` types from `go/core/x/session`:

```go
import "github.com/firebase/genkit/go/core/x/session"

// Agent holds reference to session store
type Agent[State, In, Out, Stream any] struct {
    store session.Store[State]
    // ...
}
```

---

## 4. Turn Signaling

For multi-turn conversations, the consumer needs to know when the agent has finished responding to one input and is ready for the next.

### 4.1 How It Works Internally

1. `BidiConnection.streamCh` is actually `chan streamChunk[Stream]` (internal type)
2. `streamChunk` has `data T` and `endTurn bool` fields (unexported)
3. `resp.Send(data)` sends `streamChunk{data: data}`
4. `resp.EndTurn()` sends `streamChunk{endTurn: true}`
5. `conn.Receive()` unwraps chunks, yielding only the data
6. When `Receive()` sees `endTurn: true`, it exits the iterator without yielding

### 4.2 From the Agent's Perspective

```go
for input := range inCh {
    resp.Send("partial...")
    resp.Send("more...")
    resp.EndTurn()  // Consumer's for loop exits here
}
```

### 4.3 From the Consumer's Perspective

```go
conn.Send("question")
for chunk, err := range conn.Receive() {
    fmt.Print(chunk)  // Just gets string, not streamChunk
}
// Loop exited because agent called EndTurn()

conn.Send("follow-up")
for chunk, err := range conn.Receive() { ... }
```

---

## 5. Example Usage

### 5.1 Chat Agent with Session Persistence

```go
package main

import (
    "context"
    "fmt"

    "github.com/firebase/genkit/go/ai"
    aix "github.com/firebase/genkit/go/ai/x"
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
        func(ctx context.Context, sess *session.Session[ChatState], inCh <-chan string, resp *aix.Responder[string]) (aix.AgentResult[string], error) {
            state := sess.State()
            messages := state.Messages

            for input := range inCh {
                messages = append(messages, ai.NewUserTextMessage(input))

                var respText string
                for result, err := range genkit.GenerateStream(ctx, g,
                    ai.WithMessages(messages...),
                ) {
                    if err != nil {
                        return aix.AgentResult[string]{}, err
                    }
                    if result.Done {
                        respText = result.Response.Text()
                    }
                    resp.Send(result.Chunk.Text())
                }
                resp.EndTurn()  // Signal turn complete, consumer's Receive() exits

                messages = append(messages, ai.NewModelTextMessage(respText))
                sess.UpdateState(ctx, ChatState{Messages: messages})
            }

            return aix.AgentResult[string]{
                Output:    "conversation ended",
                Artifacts: []aix.Artifact{
                    {
                        Name:  "summary",
                        Parts: []*ai.Part{ai.NewTextPart("...")},
                    },
                },
            }, nil
        },
        aix.WithSessionStore(store),
    )

    // Start new session (generates new session ID)
    conn, _ := chatAgent.StreamBidi(ctx)

    // First turn
    conn.Send("Hello! Tell me about Go programming.")
    for chunk, err := range conn.Receive() {
        if err != nil {
            panic(err)
        }
        fmt.Print(chunk)
    }
    // Loop exits when agent calls resp.EndTurn()

    // Second turn
    conn.Send("What are channels used for?")
    for chunk, err := range conn.Receive() {
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

### 5.2 Agent with Artifacts

```go
type CodeState struct {
    History      []*ai.Message `json:"history"`
    GeneratedCode []string     `json:"generatedCode"`
}

codeAgent := genkit.DefineAgent(g, "codeAgent",
    func(ctx context.Context, sess *session.Session[CodeState], inCh <-chan string, resp *aix.Responder[string]) (aix.AgentResult[string], error) {
        state := sess.State()
        var artifacts []aix.Artifact

        for input := range inCh {
            // Generate response with code...
            generatedCode := "func main() { ... }"

            resp.Send("Here's the code you requested:\n")
            resp.Send("```go\n" + generatedCode + "\n```")
            resp.EndTurn()

            // Track generated code in state
            state.GeneratedCode = append(state.GeneratedCode, generatedCode)
            sess.UpdateState(ctx, state)

            // Add as artifact
            artifacts = append(artifacts, aix.Artifact{
                Name:  fmt.Sprintf("code_%d.go", len(artifacts)),
                Parts: []*ai.Part{ai.NewTextPart(generatedCode)},
            })
        }

        return aix.AgentResult[string]{
            Output:    "code generation complete",
            Artifacts: artifacts,
        }, nil
    },
    aix.WithSessionStore(store),
)
```

---

## 6. Files to Create/Modify

### New Files

| File | Description |
|------|-------------|
| `go/ai/x/agent.go` | Agent, AgentFunc, AgentResult, AgentOutput, Artifact, Responder |
| `go/ai/x/agent_options.go` | AgentOption, WithSessionStore |
| `go/ai/x/agent_test.go` | Tests |

### Modified Files

| File | Change |
|------|--------|
| `go/genkit/bidi.go` | Add DefineAgent wrapper |

---

## 7. Implementation Notes

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

### Thread Safety

- BidiConnection uses mutex for state (closed flag)
- Send is safe to call from multiple goroutines
- Session operations are thread-safe (from existing session package)

### Tracing

- Agent inherits tracing from BidiFlow
- Each turn can create nested spans for LLM calls
- Session ID is recorded in trace metadata
