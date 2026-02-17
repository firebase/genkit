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
	"fmt"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/internal/registry"
)

type testState struct {
	Counter int      `json:"counter"`
	Topics  []string `json:"topics,omitempty"`
}

type testStatus struct {
	Phase string `json:"phase"`
}

func newTestRegistry(t *testing.T) *registry.Registry {
	t.Helper()
	return registry.New()
}

func TestAgentFlow_BasicMultiTurn(t *testing.T) {
	ctx := context.Background()
	reg := newTestRegistry(t)

	af := DefineCustomAgent(reg, "basicFlow",
		func(ctx context.Context, resp Responder[testStatus], sess *AgentSession[testState]) error {
			return sess.Run(ctx, func(ctx context.Context, input *AgentFlowInput) error {
				resp.SendStatus(testStatus{Phase: "generating"})
				// Echo back the user's message.
				if len(input.Messages) > 0 {
					reply := ai.NewModelTextMessage("echo: " + input.Messages[0].Content[0].Text)
					sess.AddMessages(reply)
				}
				sess.UpdateCustom(func(s testState) testState {
					s.Counter++
					return s
				})
				resp.SendStatus(testStatus{Phase: "complete"})
				return nil
			})
		},
	)

	conn, err := af.StreamBidi(ctx)
	if err != nil {
		t.Fatalf("StreamBidi failed: %v", err)
	}

	// Turn 1.
	if err := conn.SendText("hello"); err != nil {
		t.Fatalf("SendText failed: %v", err)
	}
	var turn1Chunks int
	for chunk, err := range conn.Receive() {
		if err != nil {
			t.Fatalf("Receive error: %v", err)
		}
		turn1Chunks++
		if chunk.EndTurn {
			break
		}
	}
	if turn1Chunks < 2 { // at least status + endTurn
		t.Errorf("expected at least 2 chunks in turn 1, got %d", turn1Chunks)
	}

	// Turn 2.
	if err := conn.SendText("world"); err != nil {
		t.Fatalf("SendText failed: %v", err)
	}
	for chunk, err := range conn.Receive() {
		if err != nil {
			t.Fatalf("Receive error: %v", err)
		}
		if chunk.EndTurn {
			break
		}
	}

	conn.Close()

	response, err := conn.Output()
	if err != nil {
		t.Fatalf("Output failed: %v", err)
	}

	// 2 user messages + 2 echo replies = 4.
	if got := len(response.State.Messages); got != 4 {
		t.Errorf("expected 4 messages, got %d", got)
	}
	if got := response.State.Custom.Counter; got != 2 {
		t.Errorf("expected counter=2, got %d", got)
	}
}

func TestAgentFlow_WithSessionStore(t *testing.T) {
	ctx := context.Background()
	reg := newTestRegistry(t)
	store := NewInMemorySessionStore[testState]()

	af := DefineCustomAgent(reg, "snapshotFlow",
		func(ctx context.Context, resp Responder[testStatus], sess *AgentSession[testState]) error {
			return sess.Run(ctx, func(ctx context.Context, input *AgentFlowInput) error {
				if len(input.Messages) > 0 {
					sess.AddMessages(ai.NewModelTextMessage("reply"))
				}
				sess.UpdateCustom(func(s testState) testState {
					s.Counter++
					return s
				})
				return nil
			})
		},
		WithSessionStore[testState](store),
	)

	conn, err := af.StreamBidi(ctx)
	if err != nil {
		t.Fatalf("StreamBidi failed: %v", err)
	}

	conn.SendText("turn1")

	var snapshotIDs []string
	for chunk, err := range conn.Receive() {
		if err != nil {
			t.Fatalf("Receive error: %v", err)
		}
		if chunk.SnapshotID != "" {
			snapshotIDs = append(snapshotIDs, chunk.SnapshotID)
		}
		if chunk.EndTurn {
			break
		}
	}

	if len(snapshotIDs) != 1 {
		t.Fatalf("expected 1 snapshot from turn, got %d", len(snapshotIDs))
	}

	// Verify the snapshot was persisted.
	snap, err := store.GetSnapshot(ctx, snapshotIDs[0])
	if err != nil {
		t.Fatalf("GetSnapshot failed: %v", err)
	}
	if snap == nil {
		t.Fatal("expected snapshot, got nil")
	}
	if snap.State.Custom.Counter != 1 {
		t.Errorf("expected counter=1 in snapshot, got %d", snap.State.Custom.Counter)
	}
	if snap.TurnIndex != 0 {
		t.Errorf("expected turnIndex=0, got %d", snap.TurnIndex)
	}

	conn.Close()

	response, err := conn.Output()
	if err != nil {
		t.Fatalf("Output failed: %v", err)
	}

	// Final snapshot at invocation end.
	if response.SnapshotID == "" {
		t.Error("expected final snapshot ID")
	}
}

func TestAgentFlow_ResumeFromSnapshot(t *testing.T) {
	ctx := context.Background()
	reg := newTestRegistry(t)
	store := NewInMemorySessionStore[testState]()

	af := DefineCustomAgent(reg, "resumeFlow",
		func(ctx context.Context, resp Responder[testStatus], sess *AgentSession[testState]) error {
			return sess.Run(ctx, func(ctx context.Context, input *AgentFlowInput) error {
				if len(input.Messages) > 0 {
					sess.AddMessages(ai.NewModelTextMessage("reply"))
				}
				sess.UpdateCustom(func(s testState) testState {
					s.Counter++
					return s
				})
				return nil
			})
		},
		WithSessionStore[testState](store),
	)

	// First invocation: create a snapshot.
	conn1, err := af.StreamBidi(ctx)
	if err != nil {
		t.Fatalf("StreamBidi failed: %v", err)
	}
	conn1.SendText("first message")
	for chunk, err := range conn1.Receive() {
		if err != nil {
			t.Fatalf("Receive error: %v", err)
		}
		if chunk.EndTurn {
			break
		}
	}
	conn1.Close()
	resp1, err := conn1.Output()
	if err != nil {
		t.Fatalf("Output failed: %v", err)
	}
	if resp1.SnapshotID == "" {
		t.Fatal("expected snapshot ID from first invocation")
	}

	// Second invocation: resume from snapshot.
	conn2, err := af.StreamBidi(ctx, WithSnapshotID[testState](resp1.SnapshotID))
	if err != nil {
		t.Fatalf("StreamBidi with snapshot failed: %v", err)
	}
	conn2.SendText("continued message")
	for chunk, err := range conn2.Receive() {
		if err != nil {
			t.Fatalf("Receive error: %v", err)
		}
		if chunk.EndTurn {
			break
		}
	}
	conn2.Close()
	resp2, err := conn2.Output()
	if err != nil {
		t.Fatalf("Output failed: %v", err)
	}

	// Should have messages from both invocations:
	// first: user + reply (2) + second: user + reply (2) = 4.
	if got := len(resp2.State.Messages); got != 4 {
		t.Errorf("expected 4 messages after resume, got %d", got)
	}
	// Counter should be 2 (1 from first + 1 from second).
	if got := resp2.State.Custom.Counter; got != 2 {
		t.Errorf("expected counter=2, got %d", got)
	}

	// The new snapshot should reference the previous as parent.
	if resp2.SnapshotID == "" {
		t.Fatal("expected snapshot ID from second invocation")
	}
	snap2, err := store.GetSnapshot(ctx, resp2.SnapshotID)
	if err != nil {
		t.Fatalf("GetSnapshot failed: %v", err)
	}
	// The parent chain: snap2's parent is a turn-end snapshot from the second invocation,
	// which itself has a parent from the first invocation's final snapshot.
	// We just verify that the parent chain exists (not empty).
	if snap2.ParentID == "" {
		t.Error("expected parent ID on resumed snapshot")
	}
}

func TestAgentFlow_ClientManagedState(t *testing.T) {
	ctx := context.Background()
	reg := newTestRegistry(t)

	af := DefineCustomAgent(reg, "clientStateFlow",
		func(ctx context.Context, resp Responder[testStatus], sess *AgentSession[testState]) error {
			return sess.Run(ctx, func(ctx context.Context, input *AgentFlowInput) error {
				if len(input.Messages) > 0 {
					sess.AddMessages(ai.NewModelTextMessage("reply"))
				}
				sess.UpdateCustom(func(s testState) testState {
					s.Counter++
					return s
				})
				return nil
			})
		},
	)

	// Start with client-provided state.
	clientState := &SessionState[testState]{
		Messages: []*ai.Message{
			ai.NewUserTextMessage("previous message"),
			ai.NewModelTextMessage("previous reply"),
		},
		Custom: testState{Counter: 5},
	}

	conn, err := af.StreamBidi(ctx, WithState(clientState))
	if err != nil {
		t.Fatalf("StreamBidi failed: %v", err)
	}

	conn.SendText("new message")
	for chunk, err := range conn.Receive() {
		if err != nil {
			t.Fatalf("Receive error: %v", err)
		}
		if chunk.EndTurn {
			break
		}
	}
	conn.Close()

	response, err := conn.Output()
	if err != nil {
		t.Fatalf("Output failed: %v", err)
	}

	// 2 previous + 1 new user + 1 reply = 4.
	if got := len(response.State.Messages); got != 4 {
		t.Errorf("expected 4 messages, got %d", got)
	}
	// Counter should be 6 (started at 5, incremented once).
	if got := response.State.Custom.Counter; got != 6 {
		t.Errorf("expected counter=6, got %d", got)
	}
	// No snapshot since no store was configured.
	if response.SnapshotID != "" {
		t.Errorf("expected no snapshot ID without store, got %q", response.SnapshotID)
	}
}

func TestAgentFlow_Artifacts(t *testing.T) {
	ctx := context.Background()
	reg := newTestRegistry(t)

	af := DefineCustomAgent(reg, "artifactFlow",
		func(ctx context.Context, resp Responder[testStatus], sess *AgentSession[testState]) error {
			return sess.Run(ctx, func(ctx context.Context, input *AgentFlowInput) error {

				resp.SendArtifact(&AgentArtifact{
					Name:  "code.go",
					Parts: []*ai.Part{ai.NewTextPart("package main")},
				})

				// Replace artifact with same name.
				resp.SendArtifact(&AgentArtifact{
					Name:  "code.go",
					Parts: []*ai.Part{ai.NewTextPart("package main\nfunc main() {}")},
				})

				// Add another artifact.
				resp.SendArtifact(&AgentArtifact{
					Name:  "readme.md",
					Parts: []*ai.Part{ai.NewTextPart("# README")},
				})

				sess.AddMessages(ai.NewModelTextMessage("done"))
				return nil
			})
		},
	)

	conn, err := af.StreamBidi(ctx)
	if err != nil {
		t.Fatalf("StreamBidi failed: %v", err)
	}

	conn.SendText("generate code")
	var receivedArtifacts []*AgentArtifact
	for chunk, err := range conn.Receive() {
		if err != nil {
			t.Fatalf("Receive error: %v", err)
		}
		if chunk.Artifact != nil {
			receivedArtifacts = append(receivedArtifacts, chunk.Artifact)
		}
		if chunk.EndTurn {
			break
		}
	}
	conn.Close()

	if len(receivedArtifacts) != 3 { // all 3 sends are streamed
		t.Errorf("expected 3 streamed artifacts, got %d", len(receivedArtifacts))
	}

	response, err := conn.Output()
	if err != nil {
		t.Fatalf("Output failed: %v", err)
	}

	// Session should have 2 unique artifacts (code.go was replaced).
	if got := len(response.State.Artifacts); got != 2 {
		t.Errorf("expected 2 artifacts in state, got %d", got)
	}
}

func TestAgentFlow_SnapshotCallback(t *testing.T) {
	ctx := context.Background()
	reg := newTestRegistry(t)
	store := NewInMemorySessionStore[testState]()

	// Only snapshot on even turns.
	callbackCalls := 0
	af := DefineCustomAgent(reg, "callbackFlow",
		func(ctx context.Context, resp Responder[testStatus], sess *AgentSession[testState]) error {
			return sess.Run(ctx, func(ctx context.Context, input *AgentFlowInput) error {
				sess.AddMessages(ai.NewModelTextMessage("reply"))
				sess.UpdateCustom(func(s testState) testState {
					s.Counter++
					return s
				})
				return nil
			})
		},
		WithSessionStore[testState](store),
		WithSnapshotCallback(func(ctx context.Context, sc *SnapshotContext[testState]) bool {
			callbackCalls++
			return sc.TurnIndex%2 == 0 // only snapshot on even turns
		}),
	)

	conn, err := af.StreamBidi(ctx)
	if err != nil {
		t.Fatalf("StreamBidi failed: %v", err)
	}

	var snapshotIDs []string
	for i := 0; i < 3; i++ {
		conn.SendText(fmt.Sprintf("turn %d", i))
		for chunk, err := range conn.Receive() {
			if err != nil {
				t.Fatalf("Receive error on turn %d: %v", i, err)
			}
			if chunk.SnapshotID != "" {
				snapshotIDs = append(snapshotIDs, chunk.SnapshotID)
			}
			if chunk.EndTurn {
				break
			}
		}
	}
	conn.Close()
	conn.Output() // drain

	// Turn 0 (even) → snapshot, Turn 1 (odd) → no, Turn 2 (even) → snapshot.
	// That's 2 turn snapshots from the callback.
	if got := len(snapshotIDs); got != 2 {
		t.Errorf("expected 2 turn snapshots, got %d", got)
	}
	// Callback should have been called 3 times (once per turn).
	if callbackCalls < 3 {
		t.Errorf("expected at least 3 callback calls, got %d", callbackCalls)
	}
}

func TestAgentFlow_SendMessages(t *testing.T) {
	ctx := context.Background()
	reg := newTestRegistry(t)

	af := DefineCustomAgent(reg, "sendMsgsFlow",
		func(ctx context.Context, resp Responder[testStatus], sess *AgentSession[testState]) error {
			return sess.Run(ctx, func(ctx context.Context, input *AgentFlowInput) error {
				return nil
			})
		},
	)

	conn, err := af.StreamBidi(ctx)
	if err != nil {
		t.Fatalf("StreamBidi failed: %v", err)
	}

	// Send multiple messages at once.
	err = conn.SendMessages(
		ai.NewUserTextMessage("msg1"),
		ai.NewUserTextMessage("msg2"),
	)
	if err != nil {
		t.Fatalf("SendMessages failed: %v", err)
	}
	for chunk, err := range conn.Receive() {
		if err != nil {
			t.Fatalf("Receive error: %v", err)
		}
		if chunk.EndTurn {
			break
		}
	}
	conn.Close()

	response, err := conn.Output()
	if err != nil {
		t.Fatalf("Output failed: %v", err)
	}

	// Both messages should have been added.
	if got := len(response.State.Messages); got != 2 {
		t.Errorf("expected 2 messages, got %d", got)
	}
}

func TestAgentFlow_SessionContext(t *testing.T) {
	ctx := context.Background()
	reg := newTestRegistry(t)

	var retrievedCounter int
	af := DefineCustomAgent(reg, "contextFlow",
		func(ctx context.Context, resp Responder[testStatus], sess *AgentSession[testState]) error {
			return sess.Run(ctx, func(ctx context.Context, input *AgentFlowInput) error {
				// Session should be retrievable from context.
				ctxSess := SessionFromContext[testState](ctx)
				if ctxSess == nil {
					t.Error("expected session from context")
					return nil
				}
				ctxSess.UpdateCustom(func(s testState) testState {
					s.Counter = 42
					return s
				})
				retrievedCounter = ctxSess.Custom().Counter
				return nil
			})
		},
	)

	conn, err := af.StreamBidi(ctx)
	if err != nil {
		t.Fatalf("StreamBidi failed: %v", err)
	}

	conn.SendText("test")
	for chunk, err := range conn.Receive() {
		if err != nil {
			t.Fatalf("Receive error: %v", err)
		}
		if chunk.EndTurn {
			break
		}
	}
	conn.Close()
	conn.Output()

	if retrievedCounter != 42 {
		t.Errorf("expected counter=42 from context, got %d", retrievedCounter)
	}
}

func TestAgentFlow_ErrorInTurn(t *testing.T) {
	ctx := context.Background()
	reg := newTestRegistry(t)

	af := DefineCustomAgent(reg, "errorFlow",
		func(ctx context.Context, resp Responder[testStatus], sess *AgentSession[testState]) error {
			return sess.Run(ctx, func(ctx context.Context, input *AgentFlowInput) error {
				return fmt.Errorf("turn failed")
			})
		},
	)

	conn, err := af.StreamBidi(ctx)
	if err != nil {
		t.Fatalf("StreamBidi failed: %v", err)
	}

	conn.SendText("trigger error")
	conn.Close()

	_, err = conn.Output()
	if err == nil {
		t.Fatal("expected error from failed turn")
	}
}

func TestAgentFlow_SetMessages(t *testing.T) {
	ctx := context.Background()
	reg := newTestRegistry(t)

	af := DefineCustomAgent(reg, "setMsgsFlow",
		func(ctx context.Context, resp Responder[testStatus], sess *AgentSession[testState]) error {
			return sess.Run(ctx, func(ctx context.Context, input *AgentFlowInput) error {
				// Replace all messages with just one.
				sess.SetMessages([]*ai.Message{ai.NewModelTextMessage("replaced")})
				return nil
			})
		},
	)

	conn, err := af.StreamBidi(ctx)
	if err != nil {
		t.Fatalf("StreamBidi failed: %v", err)
	}

	conn.SendText("original")
	for chunk, err := range conn.Receive() {
		if err != nil {
			t.Fatalf("Receive error: %v", err)
		}
		if chunk.EndTurn {
			break
		}
	}
	conn.Close()

	response, err := conn.Output()
	if err != nil {
		t.Fatalf("Output failed: %v", err)
	}

	// SetMessages replaced everything with 1 message.
	if got := len(response.State.Messages); got != 1 {
		t.Errorf("expected 1 message after SetMessages, got %d", got)
	}
}

func TestAgentFlow_SnapshotIDInMessageMetadata(t *testing.T) {
	ctx := context.Background()
	reg := newTestRegistry(t)
	store := NewInMemorySessionStore[testState]()

	af := DefineCustomAgent(reg, "metadataFlow",
		func(ctx context.Context, resp Responder[testStatus], sess *AgentSession[testState]) error {
			return sess.Run(ctx, func(ctx context.Context, input *AgentFlowInput) error {
				sess.AddMessages(ai.NewModelTextMessage("reply"))
				return nil
			})
		},
		WithSessionStore[testState](store),
	)

	conn, err := af.StreamBidi(ctx)
	if err != nil {
		t.Fatalf("StreamBidi failed: %v", err)
	}

	conn.SendText("hello")
	for chunk, err := range conn.Receive() {
		if err != nil {
			t.Fatalf("Receive error: %v", err)
		}
		if chunk.EndTurn {
			break
		}
	}
	conn.Close()

	response, err := conn.Output()
	if err != nil {
		t.Fatalf("Output failed: %v", err)
	}

	// The last message should have snapshotId in its metadata.
	msgs := response.State.Messages
	if len(msgs) == 0 {
		t.Fatal("expected messages in response")
	}
	lastMsg := msgs[len(msgs)-1]
	if lastMsg.Metadata == nil {
		t.Fatal("expected metadata on last message")
	}
	if _, ok := lastMsg.Metadata["snapshotId"]; !ok {
		t.Error("expected snapshotId in last message metadata")
	}
}

func TestInMemorySessionStore(t *testing.T) {
	ctx := context.Background()
	store := NewInMemorySessionStore[testState]()

	// Get non-existent.
	snap, err := store.GetSnapshot(ctx, "nonexistent")
	if err != nil {
		t.Fatalf("GetSnapshot failed: %v", err)
	}
	if snap != nil {
		t.Errorf("expected nil, got %v", snap)
	}

	// Save and retrieve.
	snapshot := &SessionSnapshot[testState]{
		SnapshotID: "snap-1",
		TurnIndex:  0,
		State: SessionState[testState]{
			Custom: testState{Counter: 1},
		},
	}
	if err := store.SaveSnapshot(ctx, snapshot); err != nil {
		t.Fatalf("SaveSnapshot failed: %v", err)
	}

	retrieved, err := store.GetSnapshot(ctx, "snap-1")
	if err != nil {
		t.Fatalf("GetSnapshot failed: %v", err)
	}
	if retrieved == nil {
		t.Fatal("expected snapshot")
	}
	if retrieved.State.Custom.Counter != 1 {
		t.Errorf("expected counter=1, got %d", retrieved.State.Custom.Counter)
	}

	// Verify isolation.
	snapshot.State.Custom.Counter = 999
	retrieved2, _ := store.GetSnapshot(ctx, "snap-1")
	if retrieved2.State.Custom.Counter != 1 {
		t.Errorf("expected counter=1 (isolation), got %d", retrieved2.State.Custom.Counter)
	}
}

func TestAgentFlow_SessionStoreReflectionAction(t *testing.T) {
	_ = context.Background()
	reg := newTestRegistry(t)
	store := NewInMemorySessionStore[testState]()

	DefineCustomAgent(reg, "reflectFlow",
		func(ctx context.Context, resp Responder[testStatus], sess *AgentSession[testState]) error {
			return nil
		},
		WithSessionStore[testState](store),
	)

	// The getSnapshot action should be registered.
	action := reg.LookupAction("/session-store/reflectFlow/getSnapshot")
	if action == nil {
		t.Fatal("expected getSnapshot action to be registered")
	}
}
