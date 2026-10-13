// Copyright 2026 Google LLC
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

// This sample boxes a whole agent: it lives in ./boxed, one process per chat
// session, and this program only routes. box.DefineAgent registers it here,
// so it shows up and is chattable in the Dev UI like a local one.
//
// Run it:
//
//	export GEMINI_API_KEY=...
//	genkit start -- go run .
//
// Then chat with notesAgent in the Dev UI. Start a second session and note
// that takeNote reports a different pid. The chatWithNotes flow drives the
// agent in-process and streams its reply, the way an app backend would.
package main

import (
	"context"
	"encoding/json"
	"os"
	"os/signal"
	"syscall"
	"time"

	aix "github.com/firebase/genkit/go/ai/exp"
	"github.com/firebase/genkit/go/genkit"
	box "github.com/firebase/genkit/go/plugins/box/exp"
)

// NotesState mirrors the boxed agent's custom state, for the Dev UI.
type NotesState struct {
	Notes []string `json:"notes,omitempty"`
}

type ChatInput struct {
	SessionID string `json:"sessionId"`
	Message   string `json:"message"`
}

type ChatOutput struct {
	Text  string   `json:"text"`
	Notes []string `json:"notes"`
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	// No model and no tools here; the box has both.
	g := genkit.Init(ctx)

	agentBox := box.New(g, box.ExecRunner(
		// A separate entry point. "go run" builds it on first start, hence
		// the longer ready timeout. The box inherits this process's env,
		// GEMINI_API_KEY included: the model runs there.
		box.Cmd("go", "run", "./boxed"),
		box.WithReadyTimeout(2*time.Minute),
	),
		// One box per chat session, keyed by the session the call names (in
		// the agent's init: the Dev UI and WithSessionID send it). Calls that
		// name none go to a shared box; the file store lets it pick the
		// conversation up.
		box.WithRoute(box.SessionRoute),
		// Release a session's box after 10 idle minutes (default 5).
		box.WithIdleTimeout(10*time.Minute),
	)
	defer agentBox.Close(context.Background())

	// Declared from a spec: the agent lives only in the box. StateManagement
	// must match it (it has a session store, so server).
	notes := box.DefineAgent(agentBox, box.AgentSpec{
		Name:            "notesAgent",
		Description:     "Takes notes, one box process per chat session.",
		StateManagement: aix.AgentStateManagementServer,
		StateSchema:     box.SchemaFor[NotesState](),
	})

	// Drives the boxed agent in-process, streaming its reply token by token as
	// a chat backend would. The caller picks the session id, so every turn
	// (the first one too) routes to that session's box.
	genkit.DefineStreamingFlow(g, "chatWithNotes", func(ctx context.Context, in ChatInput, sendChunk func(context.Context, string) error) (ChatOutput, error) {
		turn := notes.StreamText(ctx, in.Message, aix.WithSessionID[json.RawMessage](in.SessionID))
		for chunk, err := range turn.Receive() {
			if err != nil {
				return ChatOutput{}, err
			}
			if chunk.ModelChunk != nil && sendChunk != nil {
				if err := sendChunk(ctx, chunk.ModelChunk.Text()); err != nil {
					return ChatOutput{}, err
				}
			}
		}
		out, err := turn.Output()
		if err != nil {
			return ChatOutput{}, err
		}
		res := ChatOutput{Notes: []string{}}
		if out.Message != nil {
			res.Text = out.Message.Text()
		}
		// A server-managed agent keeps its state in the store; read it from
		// the turn's snapshot (through the box, like the turn itself).
		if out.SnapshotID == "" {
			return res, nil
		}
		snap, err := notes.GetSnapshot(ctx, out.SnapshotID)
		if err != nil {
			return ChatOutput{}, err
		}
		if snap.State != nil && len(snap.State.Custom) > 0 {
			var state NotesState
			if err := json.Unmarshal(snap.State.Custom, &state); err != nil {
				return ChatOutput{}, err
			}
			if state.Notes != nil {
				res.Notes = state.Notes
			}
		}
		return res, nil
	})

	<-ctx.Done()
}
