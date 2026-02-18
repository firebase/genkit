// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

// Package aix provides experimental AI primitives for Genkit.
//
// APIs in this package are under active development and may change in any
// minor version release.
package aix

import (
	"context"
	"fmt"
	"iter"
	"sync"
	"time"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/core/logger"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/google/uuid"
)

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

// AgentFlowInput is the input sent to an agent flow during a conversation turn.
type AgentFlowInput struct {
	// Messages contains the user's input for this turn.
	Messages []*ai.Message `json:"messages,omitempty"`
}

// AgentFlowInit is the input for starting an agent flow invocation.
// Provide either SnapshotID (to load from store) or State (direct state).
type AgentFlowInit[State any] struct {
	// SnapshotID loads state from a persisted snapshot.
	// Mutually exclusive with State.
	SnapshotID string `json:"snapshotId,omitempty"`
	// State provides direct state for the invocation.
	// Mutually exclusive with SnapshotID.
	State *SessionState[State] `json:"state,omitempty"`
}

// AgentFlowResult is the return value from an AgentFlowFunc.
// It contains the user-specified outputs of the agent invocation.
type AgentFlowResult struct {
	// Message is the last model response message from the conversation.
	Message *ai.Message `json:"message,omitempty"`
	// Artifacts contains artifacts produced during the session.
	Artifacts []*Artifact `json:"artifacts,omitempty"`
}

// AgentFlowOutput is the output when an agent flow invocation completes.
// It wraps AgentFlowResult with framework-managed fields.
type AgentFlowOutput[State any] struct {
	// SnapshotID is the ID of the snapshot created at the end of this invocation.
	// Empty if no snapshot was created (callback returned false or no store configured).
	SnapshotID string `json:"snapshotId,omitempty"`
	// State contains the final conversation state.
	// Only populated when state is client-managed (no store configured).
	State *SessionState[State] `json:"state,omitempty"`
	// Message is the last model response message from the conversation.
	Message *ai.Message `json:"message,omitempty"`
	// Artifacts contains artifacts produced during the session.
	Artifacts []*Artifact `json:"artifacts,omitempty"`
}

// AgentFlowStreamChunk represents a single item in the agent flow's output stream.
// Multiple fields can be populated in a single chunk.
type AgentFlowStreamChunk[Stream any] struct {
	// ModelChunk contains generation tokens from the model.
	ModelChunk *ai.ModelResponseChunk `json:"modelChunk,omitempty"`
	// Status contains user-defined structured status information.
	// The Stream type parameter defines the shape of this data.
	Status Stream `json:"status,omitempty"`
	// Artifact contains a newly produced artifact.
	Artifact *Artifact `json:"artifact,omitempty"`
	// SnapshotID contains the ID of a snapshot that was just persisted.
	SnapshotID string `json:"snapshotId,omitempty"`
	// EndTurn signals that the agent flow has finished processing the current input.
	// When true, the client should stop iterating and may send the next input.
	EndTurn bool `json:"endTurn,omitempty"`
}

// --- AgentSession ---

// AgentSession extends Session with agent-flow-specific functionality:
// turn management, snapshot persistence, and input channel handling.
type AgentSession[State any] struct {
	*Session[State]

	// InputCh is the channel that delivers per-turn inputs from the client.
	// It is consumed automatically by [AgentSession.Run], but is exposed
	// for advanced use cases that need direct access to the input stream
	// (e.g., custom turn loops or fan-out patterns).
	InputCh <-chan *AgentFlowInput
	// TurnIndex is the zero-based index of the current conversation turn.
	// It is incremented automatically by [AgentSession.Run], but is exposed
	// for advanced use cases that need to track or manipulate turn ordering
	// directly.
	TurnIndex int

	snapshotCallback  SnapshotCallback[State]
	onEndTurn         func(ctx context.Context)
	lastSnapshot      *SessionSnapshot[State]
	collectTurnOutput func() any
}

// Run loops over the input channel, calling fn for each turn. Each turn is
// wrapped in a trace span for observability. Input messages are automatically
// added to the session before fn is called. After fn returns successfully, an
// EndTurn chunk is sent and a snapshot check is triggered.
func (a *AgentSession[State]) Run(ctx context.Context, fn func(ctx context.Context, input *AgentFlowInput) error) error {
	for input := range a.InputCh {
		spanMeta := &tracing.SpanMetadata{
			Name:    fmt.Sprintf("agentFlow/turn/%d", a.TurnIndex),
			Type:    "agentFlowTurn",
			Subtype: "agentFlowTurn",
		}

		_, err := tracing.RunInNewSpan(ctx, spanMeta, input,
			func(ctx context.Context, input *AgentFlowInput) (any, error) {
				a.AddMessages(input.Messages...)

				if err := fn(ctx, input); err != nil {
					return nil, err
				}

				a.onEndTurn(ctx)
				a.TurnIndex++

				if a.collectTurnOutput != nil {
					return a.collectTurnOutput(), nil
				}
				return nil, nil
			},
		)
		if err != nil {
			return err
		}
	}
	return nil
}

// maybeSnapshot creates a snapshot if conditions are met (store configured,
// callback approves). Returns the snapshot ID or empty string.
func (a *AgentSession[State]) maybeSnapshot(ctx context.Context, event SnapshotEvent) string {
	if a.store == nil {
		return ""
	}

	a.mu.RLock()
	currentState := a.copyStateLocked()
	a.mu.RUnlock()

	if a.snapshotCallback != nil {
		var prevState *SessionState[State]
		if a.lastSnapshot != nil {
			prevState = &a.lastSnapshot.State
		}
		if !a.snapshotCallback(ctx, &SnapshotContext[State]{
			State:     &currentState,
			PrevState: prevState,
			TurnIndex: a.TurnIndex,
			Event:     event,
		}) {
			return ""
		}
	}

	snapshot := &SessionSnapshot[State]{
		SnapshotID: uuid.New().String(),
		CreatedAt:  time.Now(),
		Event:      event,
		State:      currentState,
	}
	if a.lastSnapshot != nil {
		snapshot.ParentID = a.lastSnapshot.SnapshotID
	}

	if err := a.store.SaveSnapshot(ctx, snapshot); err != nil {
		logger.FromContext(ctx).Error("agent flow: failed to save snapshot", "err", err)
		return ""
	}

	// Set snapshotId in last message metadata.
	a.mu.Lock()
	if msgs := a.state.Messages; len(msgs) > 0 {
		lastMsg := msgs[len(msgs)-1]
		if lastMsg.Metadata == nil {
			lastMsg.Metadata = make(map[string]any)
		}
		lastMsg.Metadata["snapshotId"] = snapshot.SnapshotID
	}
	a.mu.Unlock()

	a.lastSnapshot = snapshot

	return snapshot.SnapshotID
}

// --- Responder ---

// Responder is the output channel for an agent flow. Artifacts sent through
// it are automatically added to the session before being forwarded to the
// client.
type Responder[Stream any] chan<- *AgentFlowStreamChunk[Stream]

// SendModelChunk sends a generation chunk (token-level streaming).
func (r Responder[Stream]) SendModelChunk(chunk *ai.ModelResponseChunk) {
	r <- &AgentFlowStreamChunk[Stream]{ModelChunk: chunk}
}

// SendStatus sends a user-defined status update.
func (r Responder[Stream]) SendStatus(status Stream) {
	r <- &AgentFlowStreamChunk[Stream]{Status: status}
}

// SendArtifact sends an artifact to the stream and adds it to the session.
// If an artifact with the same name already exists in the session, it is replaced.
func (r Responder[Stream]) SendArtifact(artifact *Artifact) {
	r <- &AgentFlowStreamChunk[Stream]{Artifact: artifact}
}

// --- AgentFlow ---

// AgentFlowFunc is the function signature for agent flows.
// Type parameters:
//   - Stream: Type for status updates sent via the responder
//   - State: Type for user-defined state in snapshots
type AgentFlowFunc[Stream, State any] = func(ctx context.Context, resp Responder[Stream], sess *AgentSession[State]) (*AgentFlowResult, error)

// AgentFlow is a bidirectional streaming flow with automatic snapshot management.
type AgentFlow[Stream, State any] struct {
	flow *core.Flow[*AgentFlowInput, *AgentFlowOutput[State], *AgentFlowStreamChunk[Stream], *AgentFlowInit[State]]
}

// DefineCustomAgent creates an AgentFlow with automatic snapshot management and registers it.
func DefineCustomAgent[Stream, State any](
	r api.Registry,
	name string,
	fn AgentFlowFunc[Stream, State],
	opts ...AgentFlowOption[State],
) *AgentFlow[Stream, State] {
	afOpts := &agentFlowOptions[State]{}
	for _, opt := range opts {
		if err := opt.applyAgentFlow(afOpts); err != nil {
			panic(fmt.Errorf("DefineCustomAgent %q: %w", name, err))
		}
	}

	store := afOpts.store
	snapshotCallback := afOpts.callback

	flow := core.DefineBidiFlow(r, name, func(
		ctx context.Context,
		init *AgentFlowInit[State],
		inCh <-chan *AgentFlowInput,
		outCh chan<- *AgentFlowStreamChunk[Stream],
	) (*AgentFlowOutput[State], error) {
		session, snapshot, err := newSessionFromInit(ctx, init, store)
		if err != nil {
			return nil, err
		}
		ctx = NewSessionContext(ctx, session)

		agentSess := &AgentSession[State]{
			Session:          session,
			snapshotCallback: snapshotCallback,
			InputCh:          inCh,
			lastSnapshot:     snapshot,
		}

		// Turn output accumulator: collects content chunks per turn for span output.
		var (
			turnMu     sync.Mutex
			turnChunks []*AgentFlowStreamChunk[Stream]
		)

		agentSess.collectTurnOutput = func() any {
			turnMu.Lock()
			defer turnMu.Unlock()
			result := turnChunks
			turnChunks = nil
			return result
		}

		// Intermediary channel: intercepts artifacts, accumulates turn output,
		// and forwards to outCh.
		respCh := make(chan *AgentFlowStreamChunk[Stream])
		var wg sync.WaitGroup
		wg.Add(1)
		go func() {
			defer wg.Done()
			for chunk := range respCh {
				if chunk.Artifact != nil {
					session.AddArtifacts(chunk.Artifact)
				}
				// Accumulate content chunks (exclude control signals from onEndTurn).
				if !chunk.EndTurn && chunk.SnapshotID == "" {
					turnMu.Lock()
					turnChunks = append(turnChunks, chunk)
					turnMu.Unlock()
				}
				outCh <- chunk
			}
		}()

		// Wire up onEndTurn: triggers snapshot + sends EndTurn chunk.
		// Writes through respCh to preserve ordering with user chunks.
		agentSess.onEndTurn = func(turnCtx context.Context) {
			snapshotID := agentSess.maybeSnapshot(turnCtx, SnapshotEventTurnEnd)
			if snapshotID != "" {
				respCh <- &AgentFlowStreamChunk[Stream]{SnapshotID: snapshotID}
			}
			respCh <- &AgentFlowStreamChunk[Stream]{EndTurn: true}
		}

		result, fnErr := fn(ctx, Responder[Stream](respCh), agentSess)
		close(respCh)
		wg.Wait()

		if fnErr != nil {
			return nil, fnErr
		}

		// Final snapshot at invocation end.
		snapshotID := agentSess.maybeSnapshot(ctx, SnapshotEventInvocationEnd)

		out := &AgentFlowOutput[State]{
			SnapshotID: snapshotID,
		}
		if result != nil {
			out.Message = result.Message
			out.Artifacts = result.Artifacts
		}

		// Only include full state when client-managed (no store).
		if store == nil {
			out.State = session.State()
		}

		return out, nil
	})

	return &AgentFlow[Stream, State]{flow: flow}
}

// PromptRenderer renders a prompt with typed input into GenerateActionOptions.
// This interface is satisfied by both ai.Prompt (with In=any) and
// *ai.DataPrompt[In, Out].
type PromptRenderer[In any] interface {
	Render(ctx context.Context, input In) (*ai.GenerateActionOptions, error)
}

// promptMessageKey is the metadata key used to tag prompt-rendered messages
// so they can be excluded from session history after generation.
const promptMessageKey = "_genkit_prompt"

// DefinePromptAgent creates a prompt-backed AgentFlow with an
// automatic conversation loop. Each turn renders the prompt, appends
// conversation history, calls GenerateWithRequest, streams chunks to the
// client, and adds the model response to the session.
//
// The defaultInput is used for prompt rendering unless overridden per
// invocation via WithPromptInput.
func DefinePromptAgent[State, PromptIn any](
	r api.Registry,
	name string,
	p PromptRenderer[PromptIn],
	defaultInput PromptIn,
	opts ...AgentFlowOption[State],
) *AgentFlow[any, State] {
	fn := func(ctx context.Context, resp Responder[any], sess *AgentSession[State]) (*AgentFlowResult, error) {
		var lastModelMessage *ai.Message
		err := sess.Run(ctx, func(ctx context.Context, input *AgentFlowInput) error {
			// Resolve prompt input: session state override > default.
			promptInput := defaultInput
			if stored := sess.InputVariables(); stored != nil {
				typed, ok := stored.(PromptIn)
				if !ok {
					return core.NewError(core.INVALID_ARGUMENT, "prompt input type mismatch: got %T, want %T", stored, promptInput)
				}
				promptInput = typed
			}

			// Render the prompt template.
			genOpts, err := p.Render(ctx, promptInput)
			if err != nil {
				return fmt.Errorf("prompt render: %w", err)
			}

			// Tag prompt-rendered messages so we can exclude them from
			// session history after generation.
			for _, m := range genOpts.Messages {
				if m.Metadata == nil {
					m.Metadata = make(map[string]any)
				}
				m.Metadata[promptMessageKey] = true
			}

			// Append conversation history after the prompt-rendered messages.
			genOpts.Messages = append(genOpts.Messages, sess.Messages()...)

			// Call the model with streaming.
			modelResp, err := ai.GenerateWithRequest(ctx, r, genOpts, nil,
				func(ctx context.Context, chunk *ai.ModelResponseChunk) error {
					resp.SendModelChunk(chunk)
					return nil
				},
			)
			if err != nil {
				return fmt.Errorf("generate: %w", err)
			}

			lastModelMessage = modelResp.Message

			// Replace session messages with the full history minus prompt
			// messages. This captures intermediate tool call/response
			// messages from the tool loop, not just the final response.
			if modelResp.Request != nil {
				var msgs []*ai.Message
				for _, m := range modelResp.History() {
					if m.Metadata != nil && m.Metadata[promptMessageKey] == true {
						continue
					}
					msgs = append(msgs, m)
				}
				sess.SetMessages(msgs)
			} else if modelResp.Message != nil {
				sess.AddMessages(modelResp.Message)
			}

			// If generation was interrupted, stream the interrupted message
			// so the client can see the tool request parts with interrupt metadata.
			if modelResp.FinishReason == ai.FinishReasonInterrupted && modelResp.Message != nil {
				resp.SendModelChunk(&ai.ModelResponseChunk{
					Content: modelResp.Message.Content,
					Role:    modelResp.Message.Role,
				})
			}

			return nil
		})
		if err != nil {
			return nil, err
		}
		return &AgentFlowResult{
			Message:   lastModelMessage,
			Artifacts: sess.Artifacts(),
		}, nil
	}

	return DefineCustomAgent(r, name, fn, opts...)
}

// StreamBidi starts a new agent flow invocation.
func (af *AgentFlow[Stream, State]) StreamBidi(
	ctx context.Context,
	opts ...StreamBidiOption[State],
) (*AgentFlowConnection[Stream, State], error) {
	sbOpts := &streamBidiOptions[State]{}
	for _, opt := range opts {
		if err := opt.applyStreamBidi(sbOpts); err != nil {
			return nil, fmt.Errorf("AgentFlow.StreamBidi %q: %w", af.flow.Name(), err)
		}
	}

	init := &AgentFlowInit[State]{
		SnapshotID: sbOpts.snapshotID,
		State:      sbOpts.state,
	}
	if sbOpts.promptInput != nil {
		if init.State == nil {
			init.State = &SessionState[State]{}
		}
		init.State.InputVariables = sbOpts.promptInput
	}

	conn, err := af.flow.StreamBidi(ctx, init)
	if err != nil {
		return nil, err
	}

	return &AgentFlowConnection[Stream, State]{conn: conn}, nil
}

// newSessionFromInit creates a Session from initialization data.
// If resuming from a snapshot, the loaded snapshot is also returned.
func newSessionFromInit[State any](
	ctx context.Context,
	init *AgentFlowInit[State],
	store SessionStore[State],
) (*Session[State], *SessionSnapshot[State], error) {
	s := &Session[State]{store: store}

	var snapshot *SessionSnapshot[State]
	if init != nil {
		if init.SnapshotID != "" && init.State != nil {
			return nil, nil, core.NewError(core.INVALID_ARGUMENT, "snapshotId and state are mutually exclusive")
		}
		if init.SnapshotID != "" && store == nil {
			return nil, nil, core.NewError(core.FAILED_PRECONDITION, "snapshot ID %q provided but no session store configured", init.SnapshotID)
		}
		if init.SnapshotID != "" && store != nil {
			var err error
			snapshot, err = store.GetSnapshot(ctx, init.SnapshotID)
			if err != nil {
				return nil, nil, core.NewError(core.INTERNAL, "failed to load snapshot %q: %v", init.SnapshotID, err)
			}
			if snapshot == nil {
				return nil, nil, core.NewError(core.NOT_FOUND, "snapshot %q not found", init.SnapshotID)
			}
			s.state = snapshot.State
		} else if init.State != nil {
			s.state = *init.State
		}
	}

	return s, snapshot, nil
}

// --- AgentFlowConnection ---

// AgentFlowConnection wraps BidiConnection with agent flow-specific functionality.
// It provides a Receive() iterator that supports multi-turn patterns: breaking out
// of the iterator between turns does not cancel the underlying connection.
type AgentFlowConnection[Stream, State any] struct {
	conn *core.BidiConnection[*AgentFlowInput, *AgentFlowOutput[State], *AgentFlowStreamChunk[Stream]]

	// chunks buffers stream chunks from the underlying connection so that
	// breaking from Receive() between turns doesn't cancel the context.
	chunks   chan *AgentFlowStreamChunk[Stream]
	chunkErr error
	initOnce sync.Once
}

// initReceiver starts a goroutine that drains the underlying BidiConnection's
// Receive into a channel. This goroutine never breaks from the underlying
// iterator, preventing context cancellation.
func (c *AgentFlowConnection[Stream, State]) initReceiver() {
	c.initOnce.Do(func() {
		c.chunks = make(chan *AgentFlowStreamChunk[Stream], 1)
		go func() {
			defer close(c.chunks)
			for chunk, err := range c.conn.Receive() {
				if err != nil {
					c.chunkErr = err
					return
				}
				c.chunks <- chunk
			}
		}()
	})
}

// Send sends an AgentFlowInput to the agent flow.
func (c *AgentFlowConnection[Stream, State]) Send(input *AgentFlowInput) error {
	return c.conn.Send(input)
}

// SendMessages sends messages to the agent flow.
func (c *AgentFlowConnection[Stream, State]) SendMessages(messages ...*ai.Message) error {
	return c.conn.Send(&AgentFlowInput{Messages: messages})
}

// SendText sends a single user text message to the agent flow.
func (c *AgentFlowConnection[Stream, State]) SendText(text string) error {
	return c.conn.Send(&AgentFlowInput{
		Messages: []*ai.Message{ai.NewUserTextMessage(text)},
	})
}

// Close signals that no more inputs will be sent.
func (c *AgentFlowConnection[Stream, State]) Close() error {
	return c.conn.Close()
}

// Receive returns an iterator for receiving stream chunks.
// Unlike the underlying BidiConnection.Receive, breaking out of this iterator
// does not cancel the connection. This enables multi-turn patterns where the
// caller breaks on EndTurn, sends the next input, then calls Receive again.
func (c *AgentFlowConnection[Stream, State]) Receive() iter.Seq2[*AgentFlowStreamChunk[Stream], error] {
	c.initReceiver()
	return func(yield func(*AgentFlowStreamChunk[Stream], error) bool) {
		for {
			chunk, ok := <-c.chunks
			if !ok {
				if err := c.chunkErr; err != nil {
					yield(nil, err)
				}
				return
			}
			if !yield(chunk, nil) {
				return
			}
		}
	}
}

// Output returns the final response after the agent flow completes.
func (c *AgentFlowConnection[Stream, State]) Output() (*AgentFlowOutput[State], error) {
	return c.conn.Output()
}

// Done returns a channel closed when the connection completes.
func (c *AgentFlowConnection[Stream, State]) Done() <-chan struct{} {
	return c.conn.Done()
}
