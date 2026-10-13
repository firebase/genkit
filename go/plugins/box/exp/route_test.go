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
	"testing"
	"time"

	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/genkit"
)

func newTestGenkit() *genkit.Genkit { return genkit.Init(context.Background()) }

type shoutIn struct {
	Text string `json:"text"`
}

func TestAttachAndName(t *testing.T) {
	r := newFakeRunner(nil)
	b := New(newTestGenkit(), r, WithName("tools"))
	if b.ID() != "tools" || r.attachedTo != "tools" {
		t.Errorf("ID = %q, attached to %q; want both %q", b.ID(), r.attachedTo, "tools")
	}
	if other := New(newTestGenkit(), newFakeRunner(nil)); other.ID() == "" {
		t.Error("unnamed box got an empty id")
	}
}

func TestSingletonRoutesEverythingToOneBox(t *testing.T) {
	ctx := context.Background()
	r := newFakeRunner(nil)
	shout := NewTool[shoutIn, shoutIn](New(newTestGenkit(), r), "shout", "")
	for _, s := range []string{"a", "b"} {
		out, err := shout.RunRaw(ctx, map[string]any{"text": s})
		if err != nil {
			t.Fatal(err)
		}
		// RunRaw reports the output in its JSON form.
		if got := out.(map[string]any)["text"]; got != s {
			t.Errorf("output = %q, want %q", got, s)
		}
	}
	acquired, released, calls := r.snapshot()
	if !slices.Equal(acquired, []string{SingletonKey, SingletonKey}) || len(released) != 0 {
		t.Errorf("acquired %v, released %v; want two singleton acquires, no release", acquired, released)
	}
	if calls[0].req.Key != "/tool.v2/shout" {
		t.Errorf("box key = %q, want /tool.v2/shout", calls[0].req.Key)
	}
}

func TestPerRequestReleasesEachBox(t *testing.T) {
	ctx := context.Background()
	r := newFakeRunner(nil)
	shout := NewTool[shoutIn, shoutIn](New(newTestGenkit(), r, WithRoute(PerRequest)), "shout", "")
	for range 2 {
		if _, err := shout.RunRaw(ctx, map[string]any{"text": "x"}); err != nil {
			t.Fatal(err)
		}
	}
	waitFor(t, func() bool { _, rel, _ := r.snapshot(); return len(rel) == 2 })
	acquired, released, _ := r.snapshot()
	if acquired[0] == acquired[1] {
		t.Errorf("perRequest reused key %q", acquired[0])
	}
	slices.Sort(acquired)
	slices.Sort(released)
	if !slices.Equal(acquired, released) {
		t.Errorf("released %v, want %v", released, acquired)
	}
}

func TestRouteSeesRequestAndContext(t *testing.T) {
	r := newFakeRunner(nil)
	var seenKey string
	route := RouteFunc(func(_ context.Context, req *RunActionRequest) (string, error) {
		seenKey = req.Key
		tenant, _ := req.Context["tenant"].(string)
		return tenant, nil
	})
	shout := NewTool[shoutIn, shoutIn](New(newTestGenkit(), r, WithRoute(route)), "shout", "")
	ctx := core.WithActionContext(context.Background(), core.ActionContext{"tenant": "t1"})
	if _, err := shout.RunRaw(ctx, map[string]any{"text": "x"}); err != nil {
		t.Fatal(err)
	}
	acquired, _, calls := r.snapshot()
	if seenKey != "/tool.v2/shout" || !slices.Equal(acquired, []string{"t1"}) {
		t.Errorf("route saw %q and acquired %v; want /tool.v2/shout and [t1]", seenKey, acquired)
	}
	if calls[0].req.Context["tenant"] != "t1" {
		t.Errorf("box got context %v, want the caller's", calls[0].req.Context)
	}
}

func TestSessionRoute(t *testing.T) {
	ctx := context.Background()
	tests := []struct {
		name string
		req  RunActionRequest
		want string
	}{
		{"context wins", RunActionRequest{Key: "/agent/a", Context: core.ActionContext{"sessionId": "ctx"}, Init: json.RawMessage(`{"sessionId":"init"}`)}, "ctx"},
		{"server init", RunActionRequest{Key: "/agent/a", Init: json.RawMessage(`{"sessionId":"s1"}`)}, "s1"},
		{"client init", RunActionRequest{Key: "/agent/a", Init: json.RawMessage(`{"state":{"sessionId":"s2"}}`)}, "s2"},
		{"snapshot read", RunActionRequest{Key: "/agent-snapshot/a", Input: json.RawMessage(`{"sessionId":"s3"}`)}, "s3"},
		{"snapshot id only", RunActionRequest{Key: "/agent/a", Init: json.RawMessage(`{"snapshotId":"snap"}`)}, SharedKey},
		{"not an agent", RunActionRequest{Key: "/flow/f", Input: json.RawMessage(`{"sessionId":"x"}`)}, SharedKey},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := SessionRoute.Route(ctx, &tc.req)
			if err != nil || got != tc.want {
				t.Errorf("Route = %q, %v; want %q", got, err, tc.want)
			}
		})
	}
}

func TestDefaultIdleTimeouts(t *testing.T) {
	g := newTestGenkit()
	custom := RouteFunc(func(context.Context, *RunActionRequest) (string, error) { return "k", nil })
	for _, tc := range []struct {
		name string
		opts []Option
		want time.Duration
	}{
		{"singleton", nil, NeverRelease},
		{"perRequest", []Option{WithRoute(PerRequest)}, 0},
		{"session", []Option{WithRoute(SessionRoute)}, DefaultSessionIdleTimeout},
		{"custom", []Option{WithRoute(custom)}, DefaultSessionIdleTimeout},
		{"explicit zero", []Option{WithRoute(SessionRoute), WithIdleTimeout(0)}, 0},
	} {
		if got := New(g, newFakeRunner(nil), tc.opts...).idle; got != tc.want {
			t.Errorf("%s: idle = %v, want %v", tc.name, got, tc.want)
		}
	}
}

// waitFor polls cond for up to two seconds.
func waitFor(t *testing.T, cond func() bool) {
	t.Helper()
	deadline := time.Now().Add(2 * time.Second)
	for !cond() {
		if time.Now().After(deadline) {
			t.Fatal("condition not met in time")
		}
		time.Sleep(5 * time.Millisecond)
	}
}
