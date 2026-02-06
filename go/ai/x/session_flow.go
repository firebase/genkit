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

// SessionFlowInput is the input sent to a session flow during a conversation turn.
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
	State *SessionState[State] `json:"state,omitempty"`
	// PromptInput overrides the default prompt input for this invocation.
	// Used by prompt-backed session flows (DefineSessionFlowFromPrompt).
	PromptInput any `json:"promptInput,omitempty"`
}

// SessionFlowOutput is the output when a session flow invocation completes.
type SessionFlowOutput[State any] struct {
	// SnapshotID is the ID of the snapshot created at the end of this invocation.
	// Empty if no snapshot was created (callback returned false or no store configured).
	SnapshotID string `json:"snapshotId,omitempty"`
	// State contains the final conversation state.
	State *SessionState[State] `json:"state"`
}

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

// --- Session ---

// Session holds the working state during a session flow invocation.
// It is propagated through context and provides read/write access to state.
type Session[State any] struct {
	mu    sync.RWMutex
	state SessionState[State]
	store SnapshotStore[State]

	snapshotCallback SnapshotCallback[State]

	// onEndTurn is set by the framework; triggers snapshot + EndTurn chunk.
	onEndTurn func(ctx context.Context)
	inCh      <-chan *SessionFlowInput

	// Snapshot tracking
	lastSnapshot *SessionSnapshot[State]
	turnIndex    int
}

// Run loops over the input channel, calling fn for each turn. Each turn is
// wrapped in a trace span for observability. Input messages are automatically
// added to the session before fn is called. After fn returns successfully, an
// EndTurn chunk is sent and a snapshot check is triggered.
func (s *Session[State]) Run(
	ctx context.Context,
	fn func(ctx context.Context, input *SessionFlowInput) error,
) error {
	for input := range s.inCh {
		spanMeta := &tracing.SpanMetadata{
			Name:    fmt.Sprintf("sessionFlow/turn/%d", s.turnIndex),
			Type:    "sessionFlowTurn",
			Subtype: "sessionFlowTurn",
		}

		_, err := tracing.RunInNewSpan(ctx, spanMeta, input,
			func(ctx context.Context, input *SessionFlowInput) (struct{}, error) {
				s.AddMessages(input.Messages...)

				if err := fn(ctx, input); err != nil {
					return struct{}{}, err
				}

				s.onEndTurn(ctx)
				s.turnIndex++
				return struct{}{}, nil
			},
		)
		if err != nil {
			return err
		}
	}
	return nil
}

// State returns a copy of the current session flow state.
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
func (s *Session[State]) Artifacts() []*SessionFlowArtifact {
	s.mu.RLock()
	defer s.mu.RUnlock()
	arts := make([]*SessionFlowArtifact, len(s.state.Artifacts))
	copy(arts, s.state.Artifacts)
	return arts
}

// AddArtifacts adds artifacts to the session. If an artifact with the same
// name already exists, it is replaced.
func (s *Session[State]) AddArtifacts(artifacts ...*SessionFlowArtifact) {
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
func (s *Session[State]) SetArtifacts(artifacts []*SessionFlowArtifact) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.state.Artifacts = artifacts
}

// maybeSnapshot creates a snapshot if conditions are met (store configured,
// callback approves). Returns the snapshot ID or empty string.
func (s *Session[State]) maybeSnapshot(ctx context.Context, event SnapshotEvent) string {
	if s.store == nil {
		return ""
	}

	s.mu.RLock()
	currentState := s.copyStateLocked()
	turnIndex := s.turnIndex
	s.mu.RUnlock()

	shouldSnapshot := true
	if s.snapshotCallback != nil {
		var prevState *SessionState[State]
		if s.lastSnapshot != nil {
			prevState = &s.lastSnapshot.State
		}
		shouldSnapshot = s.snapshotCallback(ctx, &SnapshotContext[State]{
			State:     &currentState,
			PrevState: prevState,
			TurnIndex: turnIndex,
			Event:     event,
		})
	}

	if !shouldSnapshot {
		return ""
	}

	snapshot := &SessionSnapshot[State]{
		SnapshotID: uuid.New().String(),
		CreatedAt:  time.Now(),
		TurnIndex:  turnIndex,
		Event:      event,
		State:      currentState,
	}
	if s.lastSnapshot != nil {
		snapshot.ParentID = s.lastSnapshot.SnapshotID
	}

	if err := s.store.SaveSnapshot(ctx, snapshot); err != nil {
		slog.Error("session flow: failed to save snapshot", "err", err)
		return ""
	}

	// Set snapshotId in last message metadata.
	s.mu.Lock()
	if msgs := s.state.Messages; len(msgs) > 0 {
		lastMsg := msgs[len(msgs)-1]
		if lastMsg.Metadata == nil {
			lastMsg.Metadata = make(map[string]any)
		}
		lastMsg.Metadata["snapshotId"] = snapshot.SnapshotID
	}
	s.mu.Unlock()

	s.lastSnapshot = snapshot

	// Record on OTel span.
	span := oteltrace.SpanFromContext(ctx)
	span.SetAttributes(
		attribute.String("genkit:metadata:snapshotId", snapshot.SnapshotID),
	)

	return snapshot.SnapshotID
}

// copyStateLocked returns a deep copy of the state. Caller must hold mu (read or write).
func (s *Session[State]) copyStateLocked() SessionState[State] {
	bytes, err := json.Marshal(s.state)
	if err != nil {
		panic(fmt.Sprintf("session flow: failed to marshal state: %v", err))
	}
	var copied SessionState[State]
	if err := json.Unmarshal(bytes, &copied); err != nil {
		panic(fmt.Sprintf("session flow: failed to unmarshal state: %v", err))
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

// --- Responder ---

// Responder is the output channel for a session flow. Chunks sent through it
// are automatically inspected: if a chunk contains an artifact, it is added to
// the session before being forwarded to the client.
//
// Convenience methods are provided for common chunk types.
type Responder[Stream any] chan<- *SessionFlowStreamChunk[Stream]

// SendChunk sends a generation chunk (token-level streaming).
func (r Responder[Stream]) SendChunk(chunk *ai.ModelResponseChunk) {
	r <- &SessionFlowStreamChunk[Stream]{Chunk: chunk}
}

// SendStatus sends a user-defined status update.
func (r Responder[Stream]) SendStatus(status Stream) {
	r <- &SessionFlowStreamChunk[Stream]{Status: status}
}

// SendArtifact sends an artifact to the stream and adds it to the session.
// If an artifact with the same name already exists in the session, it is replaced.
func (r Responder[Stream]) SendArtifact(artifact *SessionFlowArtifact) {
	r <- &SessionFlowStreamChunk[Stream]{Artifact: artifact}
}

// --- SessionFlowParams ---

// SessionFlowParams contains the parameters passed to a session flow function.
type SessionFlowParams[State any] struct {
	// Session provides access to the working state.
	Session *Session[State]
}

// --- SessionFlowFunc ---

// SessionFlowFunc is the function signature for session flows.
// Type parameters:
//   - Stream: Type for status updates sent via the responder
//   - State: Type for user-defined state in snapshots
type SessionFlowFunc[Stream, State any] func(
	ctx context.Context,
	resp Responder[Stream],
	params *SessionFlowParams[State],
) error

// --- SessionFlow ---

// SessionFlow is a bidirectional streaming flow with automatic snapshot management.
type SessionFlow[Stream, State any] struct {
	flow             *core.Flow[*SessionFlowInput, *SessionFlowOutput[State], *SessionFlowStreamChunk[Stream], *SessionFlowInit[State]]
	store            SnapshotStore[State]
	snapshotCallback SnapshotCallback[State]
}

// DefineSessionFlow creates a SessionFlow with automatic snapshot management and registers it.
func DefineSessionFlow[Stream, State any](
	r api.Registry,
	name string,
	fn SessionFlowFunc[Stream, State],
	opts ...SessionFlowOption[State],
) *SessionFlow[Stream, State] {
	sfOpts := &sessionFlowOptions[State]{}
	for _, opt := range opts {
		if err := opt.applySessionFlow(sfOpts); err != nil {
			panic(fmt.Errorf("DefineSessionFlow %q: %w", name, err))
		}
	}

	sf := &SessionFlow[Stream, State]{
		store:            sfOpts.store,
		snapshotCallback: sfOpts.callback,
	}

	bidiFn := func(
		ctx context.Context,
		init *SessionFlowInit[State],
		inCh <-chan *SessionFlowInput,
		outCh chan<- *SessionFlowStreamChunk[Stream],
	) (*SessionFlowOutput[State], error) {
		return sf.runWrapped(ctx, init, inCh, outCh, fn)
	}

	sf.flow = core.DefineBidiFlow(r, name, bidiFn)

	// Register snapshot store action for reflection API.
	if sfOpts.store != nil {
		registerSnapshotStoreAction(r, name, sfOpts.store)
	}

	return sf
}

// StreamBidi starts a new session flow invocation.
func (sf *SessionFlow[Stream, State]) StreamBidi(
	ctx context.Context,
	opts ...StreamBidiOption[State],
) (*SessionFlowConnection[Stream, State], error) {
	sbOpts := &streamBidiOptions[State]{}
	for _, opt := range opts {
		if err := opt.applyStreamBidi(sbOpts); err != nil {
			return nil, fmt.Errorf("SessionFlow.StreamBidi %q: %w", sf.flow.Name(), err)
		}
	}

	init := &SessionFlowInit[State]{
		SnapshotID:  sbOpts.snapshotID,
		State:       sbOpts.state,
		PromptInput: sbOpts.promptInput,
	}

	conn, err := sf.flow.StreamBidi(ctx, init)
	if err != nil {
		return nil, err
	}

	return &SessionFlowConnection[Stream, State]{conn: conn}, nil
}

// runWrapped is the BidiFunc implementation. It sets up the session,
// responder, and wiring, then delegates to the user's function.
func (sf *SessionFlow[Stream, State]) runWrapped(
	ctx context.Context,
	init *SessionFlowInit[State],
	inCh <-chan *SessionFlowInput,
	outCh chan<- *SessionFlowStreamChunk[Stream],
	fn SessionFlowFunc[Stream, State],
) (*SessionFlowOutput[State], error) {
	session, err := newSessionFromInit(ctx, init, sf.store, sf.snapshotCallback)
	if err != nil {
		return nil, err
	}
	session.inCh = inCh
	ctx = NewSessionContext(ctx, session)

	// Intermediary channel: intercepts artifacts before forwarding to outCh.
	respCh := make(chan *SessionFlowStreamChunk[Stream])
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
	session.onEndTurn = func(turnCtx context.Context) {
		snapshotID := session.maybeSnapshot(turnCtx, SnapshotEventTurnEnd)
		if snapshotID != "" {
			respCh <- &SessionFlowStreamChunk[Stream]{SnapshotCreated: snapshotID}
		}
		respCh <- &SessionFlowStreamChunk[Stream]{EndTurn: true}
	}

	params := &SessionFlowParams[State]{
		Session: session,
	}

	fnErr := fn(ctx, Responder[Stream](respCh), params)
	close(respCh)
	wg.Wait()

	if fnErr != nil {
		return nil, fnErr
	}

	// Final snapshot at invocation end.
	snapshotID := session.maybeSnapshot(ctx, SnapshotEventInvocationEnd)

	return &SessionFlowOutput[State]{
		State:      session.State(),
		SnapshotID: snapshotID,
	}, nil
}

// newSessionFromInit creates a session from initialization data.
func newSessionFromInit[State any](
	ctx context.Context,
	init *SessionFlowInit[State],
	store SnapshotStore[State],
	cb SnapshotCallback[State],
) (*Session[State], error) {
	s := &Session[State]{
		store:            store,
		snapshotCallback: cb,
	}

	if init != nil {
		if init.SnapshotID != "" && store != nil {
			snapshot, err := store.GetSnapshot(ctx, init.SnapshotID)
			if err != nil {
				return nil, core.NewError(core.INTERNAL, "failed to load snapshot %q: %v", init.SnapshotID, err)
			}
			if snapshot == nil {
				return nil, core.NewError(core.NOT_FOUND, "snapshot %q not found", init.SnapshotID)
			}
			s.state = snapshot.State
			s.lastSnapshot = snapshot
			s.turnIndex = snapshot.TurnIndex
		} else if init.State != nil {
			s.state = *init.State
		}
		if init.PromptInput != nil {
			s.state.PromptInput = init.PromptInput
		}
	}

	return s, nil
}

// --- Snapshot store reflection action ---

type getSnapshotInput struct {
	SnapshotID string `json:"snapshotId"`
}

func registerSnapshotStoreAction[State any](r api.Registry, flowName string, store SnapshotStore[State]) {
	core.DefineAction(r, flowName+"/getSnapshot", api.ActionTypeSnapshotStore, nil, nil,
		func(ctx context.Context, input getSnapshotInput) (*SessionSnapshot[State], error) {
			return store.GetSnapshot(ctx, input.SnapshotID)
		},
	)
}

// --- SessionFlowConnection ---

// SessionFlowConnection wraps BidiConnection with session flow-specific functionality.
// It provides a Receive() iterator that supports multi-turn patterns: breaking out
// of the iterator between turns does not cancel the underlying connection.
type SessionFlowConnection[Stream, State any] struct {
	conn *core.BidiConnection[*SessionFlowInput, *SessionFlowOutput[State], *SessionFlowStreamChunk[Stream]]

	// chunks buffers stream chunks from the underlying connection so that
	// breaking from Receive() between turns doesn't cancel the context.
	chunks   chan *SessionFlowStreamChunk[Stream]
	chunkErr error
	initOnce sync.Once
}

// initReceiver starts a goroutine that drains the underlying BidiConnection's
// Receive into a channel. This goroutine never breaks from the underlying
// iterator, preventing context cancellation.
func (c *SessionFlowConnection[Stream, State]) initReceiver() {
	c.initOnce.Do(func() {
		c.chunks = make(chan *SessionFlowStreamChunk[Stream], 1)
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

// Send sends a SessionFlowInput to the session flow.
func (c *SessionFlowConnection[Stream, State]) Send(input *SessionFlowInput) error {
	return c.conn.Send(input)
}

// SendMessages sends messages to the session flow.
func (c *SessionFlowConnection[Stream, State]) SendMessages(messages ...*ai.Message) error {
	return c.conn.Send(&SessionFlowInput{Messages: messages})
}

// SendText sends a single user text message to the session flow.
func (c *SessionFlowConnection[Stream, State]) SendText(text string) error {
	return c.conn.Send(&SessionFlowInput{
		Messages: []*ai.Message{ai.NewUserTextMessage(text)},
	})
}

// Close signals that no more inputs will be sent.
func (c *SessionFlowConnection[Stream, State]) Close() error {
	return c.conn.Close()
}

// Receive returns an iterator for receiving stream chunks.
// Unlike the underlying BidiConnection.Receive, breaking out of this iterator
// does not cancel the connection. This enables multi-turn patterns where the
// caller breaks on EndTurn, sends the next input, then calls Receive again.
func (c *SessionFlowConnection[Stream, State]) Receive() iter.Seq2[*SessionFlowStreamChunk[Stream], error] {
	c.initReceiver()
	return func(yield func(*SessionFlowStreamChunk[Stream], error) bool) {
		for {
			chunk, ok := <-c.chunks
			if !ok {
				if err := c.chunkErr; err != nil {
					var zero *SessionFlowStreamChunk[Stream]
					yield(zero, err)
				}
				return
			}
			if !yield(chunk, nil) {
				return
			}
		}
	}
}

// Output returns the final response after the session flow completes.
func (c *SessionFlowConnection[Stream, State]) Output() (*SessionFlowOutput[State], error) {
	return c.conn.Output()
}

// Done returns a channel closed when the connection completes.
func (c *SessionFlowConnection[Stream, State]) Done() <-chan struct{} {
	return c.conn.Done()
}

// --- Prompt-backed SessionFlow ---

// PromptRenderer renders a prompt with typed input into GenerateActionOptions.
// This interface is satisfied by both ai.Prompt (with In=any) and
// *ai.DataPrompt[In, Out].
type PromptRenderer[In any] interface {
	Render(ctx context.Context, input In) (*ai.GenerateActionOptions, error)
}

// DefineSessionFlowFromPrompt creates a prompt-backed SessionFlow with an
// automatic conversation loop. Each turn renders the prompt, appends
// conversation history, calls GenerateWithRequest, streams chunks to the
// client, and adds the model response to the session.
//
// The defaultInput is used for prompt rendering unless overridden per
// invocation via WithPromptInput.
func DefineSessionFlowFromPrompt[Stream, State, PromptIn any](
	r api.Registry,
	name string,
	p PromptRenderer[PromptIn],
	defaultInput PromptIn,
	opts ...SessionFlowOption[State],
) *SessionFlow[Stream, State] {
	fn := func(ctx context.Context, resp Responder[Stream], params *SessionFlowParams[State]) error {
		return params.Session.Run(ctx, func(ctx context.Context, input *SessionFlowInput) error {
			sess := params.Session

			// Resolve prompt input: session state override > default.
			var promptInput PromptIn
			if stored := sess.PromptInput(); stored != nil {
				typed, ok := stored.(PromptIn)
				if !ok {
					return fmt.Errorf("prompt input type mismatch: got %T, want %T", stored, promptInput)
				}
				promptInput = typed
			} else {
				promptInput = defaultInput
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

	return DefineSessionFlow(r, name, fn, opts...)
}
