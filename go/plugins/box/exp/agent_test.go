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
//
// SPDX-License-Identifier: Apache-2.0

package exp

import (
	"context"
	"encoding/json"
	"slices"
	"strings"
	"sync"
	"testing"

	"github.com/firebase/genkit/go/ai"
	aix "github.com/firebase/genkit/go/ai/exp"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/genkit"
)

// sessionAgent fakes a boxed server-managed agent: it echoes the session,
// mints a snapshot per turn, and streams one chunk per turn.
func sessionAgent() *fakeRunner {
	var mu sync.Mutex
	turns := 0
	return newFakeRunner(func(ctx context.Context, req *RunActionRequest, opts *RunOptions) (any, error) {
		switch {
		case strings.HasPrefix(req.Key, "/agent/"):
			mu.Lock()
			turns++
			n := turns
			mu.Unlock()
			var init aix.AgentInit[json.RawMessage]
			_ = json.Unmarshal(req.Init, &init)
			sid := init.SessionID
			if sid == "" {
				sid = "minted"
			}
			if opts != nil && opts.OnChunk != nil {
				_ = opts.OnChunk(ctx, json.RawMessage(`{"modelChunk":{"content":[{"text":"tok"}]}}`))
			}
			return aix.AgentOutput[json.RawMessage]{
				SessionID:  sid,
				SnapshotID: "snap-" + string(rune('0'+n)),
				Message:    ai.NewModelTextMessage("ok"),
			}, nil
		case strings.HasPrefix(req.Key, "/agent-snapshot/"):
			return aix.SessionSnapshot[json.RawMessage]{SnapshotID: "snap-1", Status: aix.SnapshotStatusCompleted}, nil
		case strings.HasPrefix(req.Key, "/agent-abort/"):
			return aix.AgentAbortResponse{SnapshotID: "snap-1", Status: aix.SnapshotStatusAborted}, nil
		}
		return nil, nil
	})
}

func TestAgentHandleRoutesByContext(t *testing.T) {
	ctx := context.Background()
	r := sessionAgent()
	b := New(newTestGenkit(), r, WithRoute(SessionRoute))
	for _, sid := range []string{"s-1", "s-2"} {
		if _, err := Agent(b, "a", core.ActionContext{"sessionId": sid}).RunText(ctx, "hi"); err != nil {
			t.Fatal(err)
		}
	}
	if _, err := Agent(b, "a", nil).GetSnapshot(ctx, "snap"); err != nil {
		t.Fatal(err)
	}
	_, _, calls := r.snapshot()
	var got [][2]string
	for _, c := range calls {
		got = append(got, [2]string{c.routeKey, c.req.Key})
	}
	want := [][2]string{{"s-1", "/agent/a"}, {"s-2", "/agent/a"}, {SharedKey, "/agent-snapshot/a"}}
	if !slices.Equal(got, want) {
		t.Errorf("calls = %v, want %v", got, want)
	}
	// A turn with no session sends the empty init, which a JS agent requires.
	if got := string(calls[0].req.Init); got != `{}` {
		t.Errorf("fresh turn init = %q, want {}", got)
	}
	if calls[0].req.Context["sessionId"] != "s-1" {
		t.Errorf("boxed agent got context %v", calls[0].req.Context)
	}
}

func TestDefineAgentRegistersWithMetadata(t *testing.T) {
	g := newTestGenkit()
	b := New(g, sessionAgent())
	type notes struct {
		Notes []string `json:"notes"`
	}
	h := DefineAgent(b, AgentSpec{
		Name: "notesAgent", Description: "Takes notes.",
		StateManagement: aix.AgentStateManagementServer, Abortable: true, StateSchema: SchemaFor[notes](),
	})
	if h == nil {
		t.Fatal("DefineAgent returned nil")
	}
	for _, typ := range []api.ActionType{api.ActionTypeAgent, api.ActionTypeAgentSnapshot, api.ActionTypeAgentWait, api.ActionTypeAgentAbort} {
		if genkit.LookupAction(g, api.KeyFromName(typ, "notesAgent")) == nil {
			t.Errorf("%s not registered", typ)
		}
	}
	desc := genkit.LookupAction(g, api.KeyFromName(api.ActionTypeAgent, "notesAgent")).Desc()
	if desc.Description != "Takes notes." {
		t.Errorf("description = %q", desc.Description)
	}
	meta := h.Metadata()
	if meta == nil || meta.StateManagement != aix.AgentStateManagementServer || !meta.Abortable || meta.StateSchema == nil {
		t.Errorf("metadata = %+v, want the spec's", meta)
	}

	// Not abortable: no abort companion, and Abort is refused by status.
	DefineAgent(b, AgentSpec{Name: "plain", StateManagement: aix.AgentStateManagementClient})
	if genkit.LookupAction(g, api.KeyFromName(api.ActionTypeAgentAbort, "plain")) != nil {
		t.Error("non-abortable agent registered an abort companion")
	}
}

func TestDefineAgentThreadsTurns(t *testing.T) {
	ctx := context.Background()
	g := newTestGenkit()
	r := sessionAgent()
	DefineAgent(New(g, r, WithRoute(SessionRoute)), AgentSpec{Name: "a", StateManagement: aix.AgentStateManagementServer})
	act := genkit.LookupAction(g, api.KeyFromName(api.ActionTypeAgent, "a")).(api.BidiAction)

	conn, err := act.ConnectJSON(ctx, &api.BidiJSONOptions{Init: json.RawMessage(`{"sessionId":"s1"}`)})
	if err != nil {
		t.Fatal(err)
	}
	for range 2 {
		if err := conn.Send(json.RawMessage(`{"message":{"role":"user","content":[{"text":"hi"}]}}`)); err != nil {
			t.Fatal(err)
		}
	}
	_ = conn.Close()
	chunks := 0
	for _, err := range conn.Receive() {
		if err != nil {
			t.Fatal(err)
		}
		chunks++
	}
	out, err := conn.Output()
	if err != nil {
		t.Fatal(err)
	}
	var final aix.AgentOutput[json.RawMessage]
	_ = json.Unmarshal(out, &final)
	if final.SnapshotID != "snap-2" || chunks != 2 {
		t.Errorf("final snapshot %q with %d chunks, want snap-2 and 2", final.SnapshotID, chunks)
	}
	_, _, calls := r.snapshot()
	var inits []string
	for _, c := range calls {
		inits = append(inits, string(c.req.Init))
	}
	want := []string{`{"sessionId":"s1"}`, `{"sessionId":"s1","snapshotId":"snap-1"}`}
	if !slices.Equal(inits, want) {
		t.Errorf("inits = %v, want %v", inits, want)
	}
	// Both turns route to the session's box.
	if calls[0].routeKey != "s1" || calls[1].routeKey != "s1" {
		t.Errorf("route keys = %q, %q; want s1 for both", calls[0].routeKey, calls[1].routeKey)
	}
}

func TestDefineAgentStopsOnFailedTurn(t *testing.T) {
	ctx := context.Background()
	g := newTestGenkit()
	r := newFakeRunner(func(context.Context, *RunActionRequest, *RunOptions) (any, error) {
		return aix.AgentOutput[json.RawMessage]{FinishReason: aix.AgentFinishReasonFailed}, nil
	})
	DefineAgent(New(g, r), AgentSpec{Name: "a", StateManagement: aix.AgentStateManagementClient})
	act := genkit.LookupAction(g, api.KeyFromName(api.ActionTypeAgent, "a")).(api.BidiAction)
	conn, err := act.ConnectJSON(ctx, nil)
	if err != nil {
		t.Fatal(err)
	}
	for range 3 {
		_ = conn.Send(json.RawMessage(`{"message":{"role":"user","content":[{"text":"hi"}]}}`))
	}
	_ = conn.Close()
	for range conn.Receive() {
	}
	if _, err := conn.Output(); err != nil {
		t.Fatal(err)
	}
	if _, _, calls := r.snapshot(); len(calls) != 1 {
		t.Errorf("%d boxed turns, want 1: a failed turn ends the invocation", len(calls))
	}
}

func TestNextInitClientState(t *testing.T) {
	state := &aix.SessionState[json.RawMessage]{SessionID: "c1"}
	got := nextInit(nil, &aix.AgentOutput[json.RawMessage]{State: state}, aix.AgentStateManagementClient)
	if got.State != state || got.SnapshotID != "" {
		t.Errorf("client init = %+v, want the returned state", got)
	}
	prev := &aix.AgentInit[json.RawMessage]{SessionID: "s"}
	if got := nextInit(prev, &aix.AgentOutput[json.RawMessage]{}, aix.AgentStateManagementServer); got != prev {
		t.Errorf("no snapshot: init = %+v, want the previous one", got)
	}
}

func TestDefineAgentFromCopiesMetadata(t *testing.T) {
	g := genkit.Init(context.Background(), genkit.WithExperimental())
	real := aix.NewCustomAgent("coder", func(ctx context.Context, _ aix.Responder, sess *aix.SessionRunner[any]) (*aix.AgentResult, error) {
		return sess.Result(), nil
	}, aix.WithDescription[any]("Writes code."))
	h := DefineAgentFrom(New(g, sessionAgent()), real, "boxedCoder")
	if h.Metadata() == nil || h.Metadata().StateManagement != aix.AgentStateManagementClient {
		t.Errorf("metadata = %+v, want the original's (client-managed)", h.Metadata())
	}
	if d := genkit.LookupAction(g, api.KeyFromName(api.ActionTypeAgent, "boxedCoder")).Desc().Description; d != "Writes code." {
		t.Errorf("description = %q", d)
	}
	defer func() {
		if recover() == nil {
			t.Error("DefineAgentFrom with the original name did not panic")
		}
	}()
	DefineAgentFrom(New(g, sessionAgent()), real, "coder")
}

// TestDefineAgentHandleStreams streams a boxed turn through the handle
// DefineAgent returns: box chunks flow through the proxy to the caller.
func TestDefineAgentHandleStreams(t *testing.T) {
	ctx := context.Background()
	h := DefineAgent(New(newTestGenkit(), sessionAgent()), AgentSpec{Name: "a", StateManagement: aix.AgentStateManagementServer})
	turn := h.StreamText(ctx, "hi", aix.WithSessionID[json.RawMessage]("s1"))
	var text string
	for chunk, err := range turn.Receive() {
		if err != nil {
			t.Fatal(err)
		}
		if chunk.ModelChunk != nil {
			text += chunk.ModelChunk.Text()
		}
	}
	out, err := turn.Output()
	if err != nil {
		t.Fatal(err)
	}
	if text != "tok" || out.SnapshotID != "snap-1" {
		t.Errorf("streamed %q, snapshot %q; want tok and snap-1", text, out.SnapshotID)
	}
}
