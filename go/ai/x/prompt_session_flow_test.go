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
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/internal/registry"
)

// setupPromptTestRegistry creates a registry with an echo model and generate action.
func setupPromptTestRegistry(t *testing.T) *registry.Registry {
	t.Helper()
	reg := registry.New()
	ctx := context.Background()

	ai.ConfigureFormats(reg)
	ai.DefineModel(reg, "test/echo", &ai.ModelOptions{Supports: &ai.ModelSupports{Multiturn: true}},
		func(ctx context.Context, req *ai.ModelRequest, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
			// Echo back the last user message text.
			var text string
			for i := len(req.Messages) - 1; i >= 0; i-- {
				if req.Messages[i].Role == ai.RoleUser {
					text = req.Messages[i].Text()
					break
				}
			}
			if text == "" {
				text = "no input"
			}

			resp := &ai.ModelResponse{
				Message: ai.NewModelTextMessage("echo: " + text),
			}

			if cb != nil {
				if err := cb(ctx, &ai.ModelResponseChunk{
					Content: resp.Message.Content,
				}); err != nil {
					return nil, err
				}
			}

			return resp, nil
		},
	)
	ai.DefineGenerateAction(ctx, reg)
	return reg
}

func TestPromptSessionFlow_Basic(t *testing.T) {
	ctx := context.Background()
	reg := setupPromptTestRegistry(t)

	prompt := ai.DefinePrompt(reg, "testPrompt",
		ai.WithModelName("test/echo"),
		ai.WithSystem("You are a test assistant."),
	)

	sf := DefineSessionFlowFromPrompt[testState](
		reg, "promptFlow", prompt, nil,
	)

	conn, err := sf.StreamBidi(ctx)
	if err != nil {
		t.Fatalf("StreamBidi failed: %v", err)
	}

	// Turn 1.
	if err := conn.SendText("hello"); err != nil {
		t.Fatalf("SendText failed: %v", err)
	}

	var gotChunk bool
	for chunk, err := range conn.Receive() {
		if err != nil {
			t.Fatalf("Receive error: %v", err)
		}
		if chunk.Chunk != nil {
			gotChunk = true
		}
		if chunk.EndTurn {
			break
		}
	}
	if !gotChunk {
		t.Error("expected at least one streaming chunk")
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

	// 2 user messages + 2 model replies = 4.
	if got := len(response.State.Messages); got != 4 {
		t.Errorf("expected 4 messages, got %d", got)
		for i, m := range response.State.Messages {
			t.Logf("  msg[%d]: role=%s text=%s", i, m.Role, m.Text())
		}
	}
}

func TestPromptSessionFlow_PromptInputOverride(t *testing.T) {
	ctx := context.Background()
	reg := setupPromptTestRegistry(t)

	type greetInput struct {
		Name string `json:"name"`
	}

	prompt := ai.DefineDataPrompt[greetInput, string](reg, "greetPrompt",
		ai.WithModelName("test/echo"),
		ai.WithPrompt("Hello {{name}}!"),
	)

	sf := DefineSessionFlowFromPrompt[testState](
		reg, "promptInputFlow", prompt, greetInput{Name: "default"},
	)

	// Use WithPromptInput to override.
	conn, err := sf.StreamBidi(ctx,
		WithPromptInput[testState](greetInput{Name: "override"}),
	)
	if err != nil {
		t.Fatalf("StreamBidi failed: %v", err)
	}

	if err := conn.SendText("hi"); err != nil {
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

	// Verify the override was stored in session state.
	if response.State.PromptInput == nil {
		t.Fatal("expected PromptInput in state")
	}

	// The model echoes the last user message, which is "hi".
	// But the prompt was rendered with "override" so "Hello override!" should appear
	// in the messages sent to the model (verified via the echo).
	// We primarily verify the state was set correctly.
	inputMap, ok := response.State.PromptInput.(map[string]any)
	if !ok {
		t.Fatalf("expected PromptInput to be map[string]any, got %T", response.State.PromptInput)
	}
	if name, _ := inputMap["name"].(string); name != "override" {
		t.Errorf("expected PromptInput name='override', got %q", name)
	}
}

func TestPromptSessionFlow_MultiTurnHistory(t *testing.T) {
	ctx := context.Background()
	reg := setupPromptTestRegistry(t)

	// Use a model that echoes all message count so we can verify history grows.
	ai.DefineModel(reg, "test/history", &ai.ModelOptions{Supports: &ai.ModelSupports{Multiturn: true}},
		func(ctx context.Context, req *ai.ModelRequest, cb ai.ModelStreamCallback) (*ai.ModelResponse, error) {
			// Count total messages received (includes prompt-rendered + history).
			var parts []string
			for _, m := range req.Messages {
				parts = append(parts, string(m.Role)+":"+m.Text())
			}
			text := strings.Join(parts, "|")

			resp := &ai.ModelResponse{
				Message: ai.NewModelTextMessage(text),
			}
			if cb != nil {
				cb(ctx, &ai.ModelResponseChunk{Content: resp.Message.Content})
			}
			return resp, nil
		},
	)

	prompt := ai.DefinePrompt(reg, "historyPrompt",
		ai.WithModelName("test/history"),
		ai.WithSystem("system prompt"),
	)

	sf := DefineSessionFlowFromPrompt[testState](
		reg, "historyFlow", prompt, nil,
	)

	conn, err := sf.StreamBidi(ctx)
	if err != nil {
		t.Fatalf("StreamBidi failed: %v", err)
	}

	// Turn 1.
	conn.SendText("turn1")
	var turn1Response string
	for chunk, err := range conn.Receive() {
		if err != nil {
			t.Fatalf("Receive error: %v", err)
		}
		if chunk.Chunk != nil {
			turn1Response += chunk.Chunk.Text()
		}
		if chunk.EndTurn {
			break
		}
	}

	// Turn 1 should have: system message + user message "turn1" (2 messages total from prompt + history).
	// The system message comes from the prompt, "turn1" from session history.
	if !strings.Contains(turn1Response, "turn1") {
		t.Errorf("turn1 response should contain 'turn1', got: %s", turn1Response)
	}

	// Turn 2.
	conn.SendText("turn2")
	var turn2Response string
	for chunk, err := range conn.Receive() {
		if err != nil {
			t.Fatalf("Receive error: %v", err)
		}
		if chunk.Chunk != nil {
			turn2Response += chunk.Chunk.Text()
		}
		if chunk.EndTurn {
			break
		}
	}

	// Turn 2 should have: system + turn1 user + turn1 model reply + turn2 user (4 messages from prompt + history).
	if !strings.Contains(turn2Response, "turn1") || !strings.Contains(turn2Response, "turn2") {
		t.Errorf("turn2 response should contain both 'turn1' and 'turn2', got: %s", turn2Response)
	}

	conn.Close()

	response, err := conn.Output()
	if err != nil {
		t.Fatalf("Output failed: %v", err)
	}

	// Session should have: turn1 user + turn1 model + turn2 user + turn2 model = 4 messages.
	if got := len(response.State.Messages); got != 4 {
		t.Errorf("expected 4 messages in session, got %d", got)
		for i, m := range response.State.Messages {
			t.Logf("  msg[%d]: role=%s text=%s", i, m.Role, m.Text())
		}
	}
}

func TestPromptSessionFlow_SnapshotPersistsPromptInput(t *testing.T) {
	ctx := context.Background()
	reg := setupPromptTestRegistry(t)
	store := NewInMemorySnapshotStore[testState]()

	prompt := ai.DefinePrompt(reg, "snapPrompt",
		ai.WithModelName("test/echo"),
		ai.WithSystem("You are a test assistant."),
	)

	sf := DefineSessionFlowFromPrompt[testState](
		reg, "snapPromptFlow", prompt, nil,
		WithSnapshotStore(store),
	)

	// Start with prompt input.
	conn, err := sf.StreamBidi(ctx,
		WithPromptInput[testState](map[string]any{"key": "value"}),
	)
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

	resp, err := conn.Output()
	if err != nil {
		t.Fatalf("Output failed: %v", err)
	}

	if resp.SnapshotID == "" {
		t.Fatal("expected snapshot ID")
	}

	// Verify the snapshot contains PromptInput.
	snap, err := store.GetSnapshot(ctx, resp.SnapshotID)
	if err != nil {
		t.Fatalf("GetSnapshot failed: %v", err)
	}
	if snap.State.PromptInput == nil {
		t.Error("expected PromptInput in snapshot state")
	}

	// Resume from snapshot — the PromptInput should be preserved.
	conn2, err := sf.StreamBidi(ctx, WithSnapshotID[testState](resp.SnapshotID))
	if err != nil {
		t.Fatalf("StreamBidi with snapshot failed: %v", err)
	}

	conn2.SendText("continued")
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

	// Should have messages from both invocations.
	if got := len(resp2.State.Messages); got != 4 {
		t.Errorf("expected 4 messages after resume, got %d", got)
	}

	// PromptInput should still be present.
	if resp2.State.PromptInput == nil {
		t.Error("expected PromptInput preserved after resume")
	}
}
