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
	"encoding/json"
	"fmt"
	"iter"
	"log/slog"
	"sync"
	"time"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/core/tracing"
	"github.com/google/uuid"
	"go.opentelemetry.io/otel/attribute"
	oteltrace "go.opentelemetry.io/otel/trace"
)

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
	// InputVariables overrides the default input variables for this invocation.
	// Used by agent flows that require input variables (DefinePromptAgent).
	InputVariables any `json:"inputVariables,omitempty"`
}

// AgentFlowOutput is the output when an agent flow invocation completes.
type AgentFlowOutput[State any] struct {
	// SnapshotID is the ID of the snapshot created at the end of this invocation.
	// Empty if no snapshot was created (callback returned false or no store configured).
	SnapshotID string `json:"snapshotId,omitempty"`
	// State contains the final conversation state.
	State *SessionState[State] `json:"state"`
}

// AgentFlowStreamChunk represents a single item in the agent flow's output stream.
// Multiple fields can be populated in a single chunk.
type AgentFlowStreamChunk[Stream any] struct {
	// Chunk contains token-level generation data.
	Chunk *ai.ModelResponseChunk `json:"chunk,omitempty"`
	// Status contains user-defined structured status information.
	// The Stream type parameter defines the shape of this data.
	Status Stream `json:"status,omitempty"`
	// Artifact contains a newly produced artifact.
	Artifact *AgentArtifact `json:"artifact,omitempty"`
	// SnapshotID contains the ID of a snapshot that was just persisted.
	SnapshotID string `json:"snapshotId,omitempty"`
	// EndTurn signals that the agent flow has finished processing the current input.
	// When true, the client should stop iterating and may send the next input.
	EndTurn bool `json:"endTurn,omitempty"`
}

// --- Session ---

// Session holds conversation state and provides thread-safe read/write access to messages,
// input variables, custom state, and artifacts.
type Session[State any] struct {
	mu    sync.RWMutex
	state SessionState[State]
	store SessionStore[State]
}

// State returns a copy of the current state.
func (s *Session[State]) State() *SessionState[State] {
	s.mu.RLock()
	defer s.mu.RUnlock()
	copied := s.copyStateLocked()
	return &copied
}

// Messages returns the current conversation history.
func (s *Session[State]) Messages() []*ai.Message {
	s.mu.RLock()
	defer s.mu.RUnlock()
	msgs := make([]*ai.Message, len(s.state.Messages))
	copy(msgs, s.state.Messages)
	return msgs
}

// AddMessages appends messages to the conversation history.
func (s *Session[State]) AddMessages(messages ...*ai.Message) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.state.Messages = append(s.state.Messages, messages...)
}

// SetMessages replaces the entire conversation history.
func (s *Session[State]) SetMessages(messages []*ai.Message) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.state.Messages = messages
}

// Custom returns the current user-defined custom state.
func (s *Session[State]) Custom() State {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.state.Custom
}

// SetCustom updates the user-defined custom state.
func (s *Session[State]) SetCustom(custom State) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.state.Custom = custom
}

// UpdateCustom atomically reads the current custom state, applies the given
// function, and writes the result back.
func (s *Session[State]) UpdateCustom(fn func(State) State) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.state.Custom = fn(s.state.Custom)
}

// PromptInput returns the prompt input stored in the session state.
func (s *Session[State]) PromptInput() any {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.state.PromptInput
}

// Artifacts returns the current artifacts.
func (s *Session[State]) Artifacts() []*AgentArtifact {
	s.mu.RLock()
	defer s.mu.RUnlock()
	arts := make([]*AgentArtifact, len(s.state.Artifacts))
	copy(arts, s.state.Artifacts)
	return arts
}

// AddArtifacts adds artifacts to the session. If an artifact with the same
// name already exists, it is replaced.
func (s *Session[State]) AddArtifacts(artifacts ...*AgentArtifact) {
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, a := range artifacts {
		replaced := false
		if a.Name != "" {
			for i, existing := range s.state.Artifacts {
				if existing.Name == a.Name {
					s.state.Artifacts[i] = a
					replaced = true
					break
				}
			}
		}
		if !replaced {
			s.state.Artifacts = append(s.state.Artifacts, a)
		}
	}
}

// SetArtifacts replaces the entire artifact list.
func (s *Session[State]) SetArtifacts(artifacts []*AgentArtifact) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.state.Artifacts = artifacts
}

// copyStateLocked returns a deep copy of the state. Caller must hold mu (read or write).
func (s *Session[State]) copyStateLocked() SessionState[State] {
	bytes, err := json.Marshal(s.state)
	if err != nil {
		panic(fmt.Sprintf("agent flow: failed to marshal state: %v", err))
	}
	var copied SessionState[State]
	if err := json.Unmarshal(bytes, &copied); err != nil {
		panic(fmt.Sprintf("agent flow: failed to unmarshal state: %v", err))
	}
	return copied
}

// --- Session context ---

type sessionContextKey struct{}

type sessionHolder struct {
	session any
}

// NewSessionContext returns a new context with the session attached.
func NewSessionContext[State any](ctx context.Context, s *Session[State]) context.Context {
	return context.WithValue(ctx, sessionContextKey{}, &sessionHolder{session: s})
}

// SessionFromContext retrieves the current session from context.
// Returns nil if no session is in context or if the type doesn't match.
func SessionFromContext[State any](ctx context.Context) *Session[State] {
	holder, ok := ctx.Value(sessionContextKey{}).(*sessionHolder)
	if !ok || holder == nil {
		return nil
	}
	session, ok := holder.session.(*Session[State])
	if !ok {
		return nil
	}
	return session
}

// --- AgentSession ---

// AgentSession extends Session with agent-flow-specific functionality:
// turn management, snapshot persistence, and input channel handling.
type AgentSession[State any] struct {
	*Session[State]
	snapshotCallback SnapshotCallback[State]
	onEndTurn        func(ctx context.Context)
	inCh             <-chan *AgentFlowInput
	lastSnapshot     *SessionSnapshot[State]
	turnIndex        int
}

// Run loops over the input channel, calling fn for each turn. Each turn is
// wrapped in a trace span for observability. Input messages are automatically
// added to the session before fn is called. After fn returns successfully, an
// EndTurn chunk is sent and a snapshot check is triggered.
func (a *AgentSession[State]) Run(ctx context.Context, fn func(ctx context.Context, input *AgentFlowInput) error) error {
	for input := range a.inCh {
		spanMeta := &tracing.SpanMetadata{
			Name:    fmt.Sprintf("agentFlow/turn/%d", a.turnIndex),
			Type:    "agentFlowTurn",
			Subtype: "agentFlowTurn",
		}

		_, err := tracing.RunInNewSpan(ctx, spanMeta, input,
			func(ctx context.Context, input *AgentFlowInput) (struct{}, error) {
				a.AddMessages(input.Messages...)

				if err := fn(ctx, input); err != nil {
					return struct{}{}, err
				}

				a.onEndTurn(ctx)
				a.turnIndex++
				return struct{}{}, nil
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
			TurnIndex: a.turnIndex,
			Event:     event,
		}) {
			return ""
		}
	}

	snapshot := &SessionSnapshot[State]{
		SnapshotID: uuid.New().String(),
		CreatedAt:  time.Now(),
		TurnIndex:  a.turnIndex,
		Event:      event,
		State:      currentState,
	}
	if a.lastSnapshot != nil {
		snapshot.ParentID = a.lastSnapshot.SnapshotID
	}

	if err := a.store.SaveSnapshot(ctx, snapshot); err != nil {
		slog.Error("agent flow: failed to save snapshot", "err", err)
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

	// Record on OTel span.
	span := oteltrace.SpanFromContext(ctx)
	span.SetAttributes(
		attribute.String("genkit:metadata:snapshotId", snapshot.SnapshotID),
	)

	return snapshot.SnapshotID
}

// --- Responder ---

// Responder is the output channel for an agent flow. Artifacts sent through
// it are automatically added to the session before being forwarded to the
// client.
type Responder[Stream any] chan<- *AgentFlowStreamChunk[Stream]

// SendChunk sends a generation chunk (token-level streaming).
func (r Responder[Stream]) SendChunk(chunk *ai.ModelResponseChunk) {
	r <- &AgentFlowStreamChunk[Stream]{Chunk: chunk}
}

// SendStatus sends a user-defined status update.
func (r Responder[Stream]) SendStatus(status Stream) {
	r <- &AgentFlowStreamChunk[Stream]{Status: status}
}

// SendArtifact sends an artifact to the stream and adds it to the session.
// If an artifact with the same name already exists in the session, it is replaced.
func (r Responder[Stream]) SendArtifact(artifact *AgentArtifact) {
	r <- &AgentFlowStreamChunk[Stream]{Artifact: artifact}
}

// --- AgentFlowFunc ---

// AgentFlowFunc is the function signature for agent flows.
// Type parameters:
//   - Stream: Type for status updates sent via the responder
//   - State: Type for user-defined state in snapshots
type AgentFlowFunc[Stream, State any] func(
	ctx context.Context,
	resp Responder[Stream],
	sess *AgentSession[State],
) error

// --- AgentFlow ---

// AgentFlow is a bidirectional streaming flow with automatic snapshot management.
type AgentFlow[Stream, State any] struct {
	flow             *core.Flow[*AgentFlowInput, *AgentFlowOutput[State], *AgentFlowStreamChunk[Stream], *AgentFlowInit[State]]
	store            SessionStore[State]
	snapshotCallback SnapshotCallback[State]
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

	af := &AgentFlow[Stream, State]{
		store:            afOpts.store,
		snapshotCallback: afOpts.callback,
	}

	bidiFn := func(
		ctx context.Context,
		init *AgentFlowInit[State],
		inCh <-chan *AgentFlowInput,
		outCh chan<- *AgentFlowStreamChunk[Stream],
	) (*AgentFlowOutput[State], error) {
		return af.runWrapped(ctx, init, inCh, outCh, fn)
	}

	af.flow = core.DefineBidiFlow(r, name, bidiFn)

	// Register snapshot store action for reflection API.
	if afOpts.store != nil {
		registerSessionStoreAction(r, name, afOpts.store)
	}

	return af
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
		SnapshotID:     sbOpts.snapshotID,
		State:          sbOpts.state,
		InputVariables: sbOpts.promptInput,
	}

	conn, err := af.flow.StreamBidi(ctx, init)
	if err != nil {
		return nil, err
	}

	return &AgentFlowConnection[Stream, State]{conn: conn}, nil
}

// runWrapped is the BidiFunc implementation. It sets up the session,
// responder, and wiring, then delegates to the user's function.
func (af *AgentFlow[Stream, State]) runWrapped(
	ctx context.Context,
	init *AgentFlowInit[State],
	inCh <-chan *AgentFlowInput,
	outCh chan<- *AgentFlowStreamChunk[Stream],
	fn AgentFlowFunc[Stream, State],
) (*AgentFlowOutput[State], error) {
	session, snapshot, err := newSessionFromInit(ctx, init, af.store)
	if err != nil {
		return nil, err
	}
	ctx = NewSessionContext(ctx, session)

	agentSess := &AgentSession[State]{
		Session:          session,
		snapshotCallback: af.snapshotCallback,
		inCh:             inCh,
		lastSnapshot:     snapshot,
	}
	if snapshot != nil {
		agentSess.turnIndex = snapshot.TurnIndex
	}

	// Intermediary channel: intercepts artifacts before forwarding to outCh.
	respCh := make(chan *AgentFlowStreamChunk[Stream])
	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		for chunk := range respCh {
			if chunk.Artifact != nil {
				session.AddArtifacts(chunk.Artifact)
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

	fnErr := fn(ctx, Responder[Stream](respCh), agentSess)
	close(respCh)
	wg.Wait()

	if fnErr != nil {
		return nil, fnErr
	}

	// Final snapshot at invocation end.
	snapshotID := agentSess.maybeSnapshot(ctx, SnapshotEventInvocationEnd)

	return &AgentFlowOutput[State]{
		State:      session.State(),
		SnapshotID: snapshotID,
	}, nil
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
		if init.InputVariables != nil {
			s.state.PromptInput = init.InputVariables
		}
	}

	return s, snapshot, nil
}

// --- Snapshot store reflection action ---

type getSnapshotInput struct {
	SnapshotID string `json:"snapshotId"`
}

func registerSessionStoreAction[State any](r api.Registry, flowName string, store SessionStore[State]) {
	core.DefineAction(r, flowName+"/getSnapshot", api.ActionTypeSessionStore, nil, nil,
		func(ctx context.Context, input getSnapshotInput) (*SessionSnapshot[State], error) {
			return store.GetSnapshot(ctx, input.SnapshotID)
		},
	)
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

// --- Prompt-backed AgentFlow ---

// PromptRenderer renders a prompt with typed input into GenerateActionOptions.
// This interface is satisfied by both ai.Prompt (with In=any) and
// *ai.DataPrompt[In, Out].
type PromptRenderer[In any] interface {
	Render(ctx context.Context, input In) (*ai.GenerateActionOptions, error)
}

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
) *AgentFlow[struct{}, State] {
	fn := func(ctx context.Context, resp Responder[struct{}], sess *AgentSession[State]) error {
		return sess.Run(ctx, func(ctx context.Context, input *AgentFlowInput) error {
			// Resolve prompt input: session state override > default.
			promptInput := defaultInput
			if stored := sess.PromptInput(); stored != nil {
				typed, ok := stored.(PromptIn)
				if !ok {
					return fmt.Errorf("prompt input type mismatch: got %T, want %T", stored, promptInput)
				}
				promptInput = typed
			}

			// Render the prompt template.
			actionOpts, err := p.Render(ctx, promptInput)
			if err != nil {
				return fmt.Errorf("prompt render: %w", err)
			}

			// Append conversation history after the prompt-rendered messages.
			actionOpts.Messages = append(actionOpts.Messages, sess.Messages()...)

			// Call the model with streaming.
			modelResp, err := ai.GenerateWithRequest(ctx, r, actionOpts, nil,
				func(ctx context.Context, chunk *ai.ModelResponseChunk) error {
					resp.SendChunk(chunk)
					return nil
				},
			)
			if err != nil {
				return fmt.Errorf("generate: %w", err)
			}

			// Add the model response message to session history.
			if modelResp.Message != nil {
				sess.AddMessages(modelResp.Message)
			}

			return nil
		})
	}

	return DefineCustomAgent(r, name, fn, opts...)
}
