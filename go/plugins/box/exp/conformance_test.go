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
	"net"
	"slices"
	"testing"
	"time"

	"github.com/firebase/genkit/go/core/status"
)

// conformance runs the same checks against any Conn backed by a real runtime
// serving the fixture actions.
//
// TODO: run this against a JS runtime too (a small app under testdata,
// skipped without node) once the JS box plugin (the #6458 stack) is merged.
// Two interop bugs, null optional fields and a missing agent init, got past
// these Go-only runs.
func conformance(t *testing.T, conn Conn) {
	ctx := context.Background()

	t.Run("tool envelope", func(t *testing.T) {
		res, err := conn.RunAction(ctx, &RunActionRequest{Key: "/tool.v2/draw", Input: json.RawMessage(`{"text":"cat"}`)}, nil)
		if err != nil {
			t.Fatal(err)
		}
		var env struct {
			Output  string `json:"output"`
			Content []any  `json:"content"`
		}
		if err := json.Unmarshal(res.Result, &env); err != nil {
			t.Fatal(err)
		}
		if env.Output != "drew cat" || len(env.Content) != 1 || res.TraceID == "" {
			t.Errorf("result = %s (trace %q), want output and one part with a trace id", res.Result, res.TraceID)
		}
	})

	t.Run("streaming", func(t *testing.T) {
		var chunks []int
		var traceID string
		res, err := conn.RunAction(ctx, &RunActionRequest{Key: "/flow/count", Input: json.RawMessage(`3`)}, &RunOptions{
			OnChunk: func(_ context.Context, raw json.RawMessage) error {
				var c countChunk
				if err := json.Unmarshal(raw, &c); err != nil {
					return err
				}
				chunks = append(chunks, c.N)
				return nil
			},
			OnTraceID: func(tid string) { traceID = tid },
		})
		if err != nil {
			t.Fatal(err)
		}
		if !slices.Equal(chunks, []int{1, 2, 3}) || string(res.Result) != `"counted 3"` {
			t.Errorf("chunks %v, result %s; want [1 2 3], counted 3", chunks, res.Result)
		}
		if traceID == "" || traceID != res.TraceID {
			t.Errorf("early trace id %q, result trace id %q; want the same, non-empty", traceID, res.TraceID)
		}
	})

	t.Run("error keeps status", func(t *testing.T) {
		_, err := conn.RunAction(ctx, &RunActionRequest{Key: "/flow/fail", Input: json.RawMessage(`"x"`)}, nil)
		if status.Of(err) != status.InvalidArgument {
			t.Errorf("err = %v (status %s), want INVALID_ARGUMENT", err, status.Of(err))
		}
	})

	t.Run("unknown action", func(t *testing.T) {
		_, err := conn.RunAction(ctx, &RunActionRequest{Key: "/flow/nope"}, nil)
		if status.Of(err) != status.NotFound {
			t.Errorf("err = %v (status %s), want NOT_FOUND", err, status.Of(err))
		}
	})

	t.Run("cancel", func(t *testing.T) {
		cctx, cancel := context.WithCancel(ctx)
		done := make(chan error, 1)
		go func() {
			_, err := conn.RunAction(cctx, &RunActionRequest{Key: "/flow/block", Input: json.RawMessage(`"x"`)}, nil)
			done <- err
		}()
		time.Sleep(200 * time.Millisecond)
		cancel()
		select {
		case err := <-done:
			if err == nil {
				t.Error("cancelled call returned no error")
			}
		case <-time.After(5 * time.Second):
			t.Fatal("cancelled call did not return")
		}
	})

	t.Run("listActions", func(t *testing.T) {
		actions, err := conn.ListActions(ctx)
		if err != nil {
			t.Fatal(err)
		}
		for _, key := range []string{"/tool.v2/shout", "/flow/count"} {
			if _, ok := actions[key]; !ok {
				t.Errorf("ListActions is missing %s", key)
			}
		}
	})
}

// freePort returns a loopback port that was free a moment ago.
func freePort(t *testing.T) int {
	t.Helper()
	l, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer l.Close()
	return l.Addr().(*net.TCPAddr).Port
}
