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

package aix

import (
	"context"
	"encoding/json"
	"sync"
	"time"

	"github.com/firebase/genkit/go/ai"
)

// SessionState is the portable conversation state that flows between client
// and server. It contains only the data needed for conversation continuity.
type SessionState[State any] struct {
	// Messages is the conversation history (user/model exchanges).
	// Does NOT include prompt-rendered messages — those are rendered fresh each turn.
	Messages []*ai.Message `json:"messages,omitempty"`
	// Custom is the user-defined state associated with this conversation.
	Custom State `json:"custom,omitempty"`
	// Artifacts are named collections of parts produced during the conversation.
	Artifacts []*SessionFlowArtifact `json:"artifacts,omitempty"`
	// PromptInput is the input used for prompt rendering in prompt-backed session flows.
	// Stored as any to support type-erased persistence across snapshot boundaries.
	PromptInput any `json:"promptInput,omitempty"`
}

// SnapshotEvent identifies what triggered a snapshot.
type SnapshotEvent string

const (
	// TurnEnd indicates the snapshot was triggered at the end of a turn.
	SnapshotEventTurnEnd SnapshotEvent = "turnEnd"
	// InvocationEnd indicates the snapshot was triggered at the end of the invocation.
	SnapshotEventInvocationEnd SnapshotEvent = "invocationEnd"
)

// SessionSnapshot is a persisted point-in-time capture of session state.
type SessionSnapshot[State any] struct {
	// SnapshotID is the unique identifier for this snapshot (UUID).
	SnapshotID string `json:"snapshotId"`
	// ParentID is the ID of the previous snapshot in this timeline.
	ParentID string `json:"parentId,omitempty"`
	// CreatedAt is when the snapshot was created.
	CreatedAt time.Time `json:"createdAt"`
	// TurnIndex is the turn number when this snapshot was created (0-indexed).
	TurnIndex int `json:"turnIndex"`
	// Event is what triggered this snapshot.
	Event SnapshotEvent `json:"event"`
	// State is the actual conversation state.
	State SessionState[State] `json:"state"`
}

// SnapshotContext provides context for snapshot decision callbacks.
type SnapshotContext[State any] struct {
	// State is the current state that will be snapshotted if the callback returns true.
	State *SessionState[State]
	// PrevState is the state at the last snapshot, or nil if none exists.
	PrevState *SessionState[State]
	// TurnIndex is the current turn number.
	TurnIndex int
	// Event is what triggered this snapshot check.
	Event SnapshotEvent
}

// SnapshotCallback decides whether to create a snapshot.
// If not provided and a store is configured, snapshots are always created.
type SnapshotCallback[State any] = func(ctx context.Context, sc *SnapshotContext[State]) bool

// SnapshotStore persists and retrieves snapshots.
type SnapshotStore[State any] interface {
	// GetSnapshot retrieves a snapshot by ID. Returns nil if not found.
	GetSnapshot(ctx context.Context, snapshotID string) (*SessionSnapshot[State], error)
	// SaveSnapshot persists a snapshot.
	SaveSnapshot(ctx context.Context, snapshot *SessionSnapshot[State]) error
}

// InMemorySnapshotStore provides a thread-safe in-memory snapshot store.
type InMemorySnapshotStore[State any] struct {
	snapshots map[string]*SessionSnapshot[State]
	mu        sync.RWMutex
}

// NewInMemorySnapshotStore creates a new in-memory snapshot store.
func NewInMemorySnapshotStore[State any]() *InMemorySnapshotStore[State] {
	return &InMemorySnapshotStore[State]{
		snapshots: make(map[string]*SessionSnapshot[State]),
	}
}

// GetSnapshot retrieves a snapshot by ID. Returns nil if not found.
func (s *InMemorySnapshotStore[State]) GetSnapshot(_ context.Context, snapshotID string) (*SessionSnapshot[State], error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	snap, exists := s.snapshots[snapshotID]
	if !exists {
		return nil, nil
	}

	copied, err := copySnapshot(snap)
	if err != nil {
		return nil, err
	}
	return copied, nil
}

// SaveSnapshot persists a snapshot.
func (s *InMemorySnapshotStore[State]) SaveSnapshot(_ context.Context, snapshot *SessionSnapshot[State]) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	copied, err := copySnapshot(snapshot)
	if err != nil {
		return err
	}
	s.snapshots[copied.SnapshotID] = copied
	return nil
}

// copySnapshot creates a deep copy of a snapshot using JSON marshaling.
func copySnapshot[State any](snap *SessionSnapshot[State]) (*SessionSnapshot[State], error) {
	if snap == nil {
		return nil, nil
	}
	bytes, err := json.Marshal(snap)
	if err != nil {
		return nil, err
	}
	var copied SessionSnapshot[State]
	if err := json.Unmarshal(bytes, &copied); err != nil {
		return nil, err
	}
	return &copied, nil
}

// SnapshotOn returns a SnapshotCallback that only allows snapshots for the
// specified events. For example, SnapshotOn[MyState](TurnEnd) will skip the
// invocation-end snapshot.
func SnapshotOn[State any](events ...SnapshotEvent) SnapshotCallback[State] {
	set := make(map[SnapshotEvent]struct{}, len(events))
	for _, e := range events {
		set[e] = struct{}{}
	}
	return func(_ context.Context, sc *SnapshotContext[State]) bool {
		_, ok := set[sc.Event]
		return ok
	}
}
