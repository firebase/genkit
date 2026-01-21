# Genkit Go Bidirectional Streaming Features - Design Document

## Overview

This document describes the design for bidirectional streaming features in Genkit Go. The implementation introduces three new primitives:

1. **BidiAction** - Core primitive for bidirectional operations (`go/core/x`)
2. **BidiFlow** - BidiAction with observability, intended for user definition (`go/core/x`)
3. **BidiModel** - Specialized bidi action for real-time LLM APIs (`go/ai/x`)

For stateful multi-turn agents with session persistence, see [go-agent-design.md](go-agent-design.md).

## Package Location

```
go/core/x/
├── bidi.go           # BidiAction, BidiFunc, BidiConnection
├── bidi_flow.go      # BidiFlow
├── bidi_options.go   # Options
├── bidi_test.go      # Tests

go/ai/x/
├── bidi_model.go     # BidiModel, BidiModelFunc
├── bidi_model_test.go
```

Import as:
- `corex "github.com/firebase/genkit/go/core/x"`
- `aix "github.com/firebase/genkit/go/ai/x"`

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
// The iterator completes when the action finishes or signals end of turn.
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

---

## 2. BidiModel

### 2.1 Overview

`BidiModel` is a specialized bidi action for real-time LLM APIs like Gemini Live and OpenAI Realtime. These APIs establish a persistent connection where configuration (temperature, system prompt, tools) must be provided upfront, and then the conversation streams bidirectionally.

### 2.2 The Role of `init`

For real-time sessions, the connection to the model API often requires configuration to be established *before* the first user message is received. The `init` payload fulfills this requirement:

- **`init`**: `GenerateRequest` (contains config, tools, system prompt)
- **`inputStream`**: Stream of `GenerateRequest` (contains user messages/turns)
- **`stream`**: Stream of `GenerateResponseChunk`

### 2.3 Type Definitions

```go
// In go/ai/x/bidi_model.go

// BidiModel represents a bidirectional streaming model for real-time LLM APIs.
type BidiModel struct {
    *corex.BidiAction[*ai.GenerateRequest, *ai.GenerateRequest, *ai.GenerateResponse, *ai.GenerateResponseChunk]
}

// BidiModelFunc is the function signature for bidi model implementations.
type BidiModelFunc func(
    ctx context.Context,
    init *ai.GenerateRequest,
    inCh <-chan *ai.GenerateRequest,
    outCh chan<- *ai.GenerateResponseChunk,
) (*ai.GenerateResponse, error)
```

### 2.4 Defining a BidiModel

```go
// DefineBidiModel creates and registers a BidiModel for real-time LLM interactions.
func DefineBidiModel(
    r api.Registry,
    name string,
    fn BidiModelFunc,
) *BidiModel
```

**Example Plugin Implementation:**

```go
// In a plugin like googlegenai

func (g *GoogleAI) defineBidiModel(r api.Registry) *aix.BidiModel {
    return aix.DefineBidiModel(r, "googleai/gemini-2.0-flash-live",
        func(ctx context.Context, init *ai.GenerateRequest, inCh <-chan *ai.GenerateRequest, outCh chan<- *ai.GenerateResponseChunk) (*ai.GenerateResponse, error) {
            // 1. Establish session using configuration from init
            session, err := g.client.ConnectLive(ctx, &genai.LiveConnectConfig{
                Model:        "gemini-2.0-flash-live",
                SystemPrompt: extractSystemPrompt(init),
                Tools:        convertTools(init.Tools),
                Config:       convertConfig(init.Config),
            })
            if err != nil {
                return nil, err
            }
            defer session.Close()

            var totalUsage ai.GenerationUsage

            // 2. Handle conversation stream
            for request := range inCh {
                // Send new user input to the upstream session
                if err := session.SendContent(convertMessages(request.Messages)); err != nil {
                    return nil, err
                }

                // Yield responses from the upstream session
                for chunk := range session.Receive() {
                    outCh <- &ai.GenerateResponseChunk{
                        Content: []*ai.Part{ai.NewTextPart(chunk.Text)},
                    }
                    totalUsage.Add(chunk.Usage)
                }
            }

            // 3. Return final result (usage stats, etc.)
            return &ai.GenerateResponse{
                Usage: &totalUsage,
            }, nil
        },
    )
}
```

### 2.5 Using BidiModel (`GenerateBidi`)

`GenerateBidi` is the high-level API for interacting with bidi models. It provides a session-like interface for real-time conversations.

```go
// In go/genkit/generate.go or go/ai/x/generate_bidi.go

// GenerateBidiSession wraps BidiConnection with model-specific convenience methods.
type GenerateBidiSession struct {
    conn *corex.BidiConnection[*ai.GenerateRequest, *ai.GenerateResponse, *ai.GenerateResponseChunk]
}

// Send sends a user message to the model.
func (s *GenerateBidiSession) Send(messages ...*ai.Message) error {
    return s.conn.Send(&ai.GenerateRequest{Messages: messages})
}

// SendText is a convenience method for sending a text message.
func (s *GenerateBidiSession) SendText(text string) error {
    return s.Send(ai.NewUserTextMessage(text))
}

// Stream returns an iterator for receiving response chunks.
func (s *GenerateBidiSession) Stream() iter.Seq2[*ai.GenerateResponseChunk, error] {
    return s.conn.Responses()
}

// Close signals that the conversation is complete.
func (s *GenerateBidiSession) Close() error {
    return s.conn.Close()
}

// Output returns the final response after the session completes.
func (s *GenerateBidiSession) Output() (*ai.GenerateResponse, error) {
    return s.conn.Output()
}
```

**Usage:**

```go
// GenerateBidi starts a bidirectional streaming session with a model.
func GenerateBidi(ctx context.Context, g *Genkit, opts ...GenerateBidiOption) (*GenerateBidiSession, error)

// GenerateBidiOption configures a bidi generation session.
type GenerateBidiOption interface {
    applyGenerateBidi(*generateBidiOptions) error
}

// WithBidiModel specifies the model to use.
func WithBidiModel(model *aix.BidiModel) GenerateBidiOption

// WithBidiConfig provides generation config (temperature, etc.) passed via init.
func WithBidiConfig(config any) GenerateBidiOption

// WithBidiSystem provides the system prompt passed via init.
func WithBidiSystem(system string) GenerateBidiOption

// WithBidiTools provides tools for the model passed via init.
func WithBidiTools(tools ...ai.Tool) GenerateBidiOption
```

**Example:**

```go
// Start a real-time session
session, err := genkit.GenerateBidi(ctx, g,
    genkit.WithBidiModel(geminiLive),
    genkit.WithBidiConfig(&googlegenai.GenerationConfig{Temperature: ptr(0.7)}),
    genkit.WithBidiSystem("You are a helpful voice assistant"),
)
if err != nil {
    return err
}
defer session.Close()

// Send a message
session.SendText("Hello!")

// Listen for responses (can happen simultaneously with sends)
for chunk, err := range session.Stream() {
    if err != nil {
        return err
    }
    fmt.Print(chunk.Text())
}

// Continue the conversation
session.SendText("Tell me more about that.")
for chunk, err := range session.Stream() {
    // ...
}

// Get final usage stats
response, _ := session.Output()
fmt.Printf("Total tokens: %d\n", response.Usage.TotalTokens)
```

### 2.6 Tool Calling in BidiModel

Real-time models may support tool calling. The pattern follows the standard generate flow but within the streaming context:

```go
session, _ := genkit.GenerateBidi(ctx, g,
    genkit.WithBidiModel(geminiLive),
    genkit.WithBidiTools(weatherTool, calculatorTool),
)

session.SendText("What's the weather in NYC?")

for chunk, err := range session.Stream() {
    if err != nil {
        return err
    }

    // Check for tool calls
    if toolCall := chunk.ToolCall(); toolCall != nil {
        // Execute the tool
        result, _ := toolCall.Tool.Execute(ctx, toolCall.Input)

        // Send tool result back to the model
        session.Send(ai.NewToolResultMessage(toolCall.ID, result))
    } else {
        fmt.Print(chunk.Text())
    }
}
```

---

## 3. API Surface

### 3.1 Defining Bidi Actions

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

### 3.2 Defining Bidi Flows

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

### 3.3 Starting Connections

All bidi types (BidiAction, BidiFlow, BidiModel) use the same `StreamBidi` method to start connections:

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
func WithInit[Init any](init Init) BidiOption[Init]
```

### 3.4 High-Level Genkit API

```go
// In go/genkit/bidi.go

func DefineBidiFlow[Init, In, Out, Stream any](
    g *Genkit,
    name string,
    fn corex.BidiFunc[Init, In, Out, Stream],
) *corex.BidiFlow[Init, In, Out, Stream]

func GenerateBidi(
    ctx context.Context,
    g *Genkit,
    opts ...GenerateBidiOption,
) (*GenerateBidiSession, error)
```

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

Add new action types and schema fields:

```go
// In go/core/api/action.go
const (
    ActionTypeBidiFlow  ActionType = "bidi-flow"
    ActionTypeBidiModel ActionType = "bidi-model"
)

// ActionDesc gets two new optional fields
type ActionDesc struct {
    // ... existing fields ...
    StreamSchema map[string]any `json:"streamSchema,omitempty"` // NEW: schema for streamed chunks
    InitSchema   map[string]any `json:"initSchema,omitempty"`   // NEW: schema for initialization data
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

    // Define echo bidi flow
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

### 5.2 Bidi Flow with Initialization Data

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

### 5.3 Real-Time Voice Model Session

```go
// Using a bidi model for voice-like interactions
session, _ := genkit.GenerateBidi(ctx, g,
    genkit.WithBidiModel(geminiLive),
    genkit.WithBidiSystem("You are a voice assistant. Keep responses brief."),
)
defer session.Close()

// Simulate real-time voice input/output
go func() {
    // In a real app, this would be audio transcription
    session.SendText("What time is it in Tokyo?")
}()

// Stream responses as they arrive
for chunk, err := range session.Stream() {
    if err != nil {
        log.Printf("Error: %v", err)
        break
    }
    // In a real app, this would go to text-to-speech
    fmt.Print(chunk.Text())
}
```

---

## 6. Files to Create/Modify

### New Files

| File | Description |
|------|-------------|
| `go/core/x/bidi.go` | BidiAction, BidiFunc, BidiConnection |
| `go/core/x/bidi_flow.go` | BidiFlow with tracing |
| `go/core/x/bidi_options.go` | BidiOption types |
| `go/core/x/bidi_test.go` | Tests |
| `go/ai/x/bidi_model.go` | BidiModel, BidiModelFunc, GenerateBidiSession |
| `go/ai/x/bidi_model_test.go` | Tests |
| `go/genkit/bidi.go` | High-level API wrappers |

### Modified Files

| File | Change |
|------|--------|
| `go/core/api/action.go` | Add `ActionTypeBidiFlow`, `ActionTypeBidiModel` constants |

---

## 7. Implementation Notes

### Error Handling
- Errors from the bidi function propagate to both `Responses()` iterator and `Output()`
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

### Channels and Backpressure
- Both input and output channels are **unbuffered** by default (size 0)
- This provides natural backpressure: `Send()` blocks until the action reads, output blocks until consumer reads
- If needed, `WithInputBufferSize` / `WithOutputBufferSize` options could be added later for specific use cases

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

---

## 8. Integration with Reflection API

These features align with **Reflection API V2**, which uses WebSockets to support bidirectional streaming between the Runtime and the CLI/Manager.

- `runAction` now supports an `input` stream
- `streamChunk` notifications are bidirectional (Manager <-> Runtime)
