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
	"slices"
	"testing"
	"time"

	"github.com/firebase/genkit/go/core/status"
)

func TestIdleReleaseWaitsForInflightCalls(t *testing.T) {
	ctx := context.Background()
	r := newFakeRunner(nil)
	r.gate = make(chan struct{})
	shout := NewTool[shoutIn, shoutIn](New(newTestGenkit(), r, WithIdleTimeout(20*time.Millisecond)), "shout", "")

	done := make(chan error, 1)
	go func() {
		_, err := shout.RunRaw(ctx, map[string]any{"text": "slow"})
		done <- err
	}()
	waitFor(t, func() bool { _, _, calls := r.snapshot(); return len(calls) == 1 })
	time.Sleep(60 * time.Millisecond) // well past the idle timeout
	if _, rel, _ := r.snapshot(); len(rel) != 0 {
		t.Fatalf("released %v mid-call", rel)
	}
	close(r.gate)
	if err := <-done; err != nil {
		t.Fatal(err)
	}
	waitFor(t, func() bool { _, rel, _ := r.snapshot(); return len(rel) == 1 })
}

func TestNewCallCancelsPendingRelease(t *testing.T) {
	ctx := context.Background()
	r := newFakeRunner(nil)
	shout := NewTool[shoutIn, shoutIn](New(newTestGenkit(), r, WithIdleTimeout(80*time.Millisecond)), "shout", "")
	for range 3 {
		if _, err := shout.RunRaw(ctx, map[string]any{"text": "x"}); err != nil {
			t.Fatal(err)
		}
		time.Sleep(40 * time.Millisecond) // shorter than the idle timeout
	}
	if _, rel, _ := r.snapshot(); len(rel) != 0 {
		t.Fatalf("released %v while calls kept arriving", rel)
	}
	waitFor(t, func() bool { _, rel, _ := r.snapshot(); return len(rel) == 1 })
}

func TestSelfRuntimeGuard(t *testing.T) {
	t.Setenv(SelfIDEnv, "me")
	ctx := context.Background()
	r := newFakeRunner(nil)
	b := New(newTestGenkit(), r, WithName("me"))
	if !b.IsSelfRuntime() {
		t.Fatal("IsSelfRuntime = false under a matching SelfIDEnv")
	}
	if err := b.Warm(ctx, ""); err != nil {
		t.Errorf("Warm in self runtime = %v, want a no-op", err)
	}
	_, err := NewTool[shoutIn, shoutIn](b, "shout", "").RunRaw(ctx, map[string]any{"text": "x"})
	if status.Of(err) != status.FailedPrecondition {
		t.Errorf("proxy call in self runtime: err = %v, want FAILED_PRECONDITION", err)
	}
	if _, err := b.ListActions(ctx, ""); status.Of(err) != status.FailedPrecondition {
		t.Errorf("ListActions in self runtime: err = %v, want FAILED_PRECONDITION", err)
	}
	if acquired, _, _ := r.snapshot(); len(acquired) != 0 {
		t.Errorf("self runtime acquired %v", acquired)
	}
	// A different box in the same process is not this runtime's own.
	if New(newTestGenkit(), newFakeRunner(nil), WithName("other")).IsSelfRuntime() {
		t.Error("a different box reported itself as the self runtime")
	}
}

func TestWarmAndListActions(t *testing.T) {
	ctx := context.Background()
	r := newFakeRunner(nil)
	b := New(newTestGenkit(), r, WithRoute(SessionRoute), WithIdleTimeout(0))
	if err := b.Warm(ctx, "s1"); err != nil {
		t.Fatal(err)
	}
	actions, err := b.ListActions(ctx, "")
	if err != nil {
		t.Fatal(err)
	}
	if _, ok := actions["/tool.v2/shout"]; !ok {
		t.Errorf("ListActions = %v, want /tool.v2/shout", actions)
	}
	waitFor(t, func() bool { _, rel, _ := r.snapshot(); return len(rel) == 2 })
	acquired, _, _ := r.snapshot()
	if !slices.Equal(acquired, []string{"s1", SingletonKey}) {
		t.Errorf("acquired %v, want [s1 %s]", acquired, SingletonKey)
	}
}

func TestCloseClosesRunnerAndRejectsCalls(t *testing.T) {
	ctx := context.Background()
	r := newFakeRunner(nil)
	b := New(newTestGenkit(), r)
	if err := b.Close(ctx); err != nil {
		t.Fatal(err)
	}
	if !r.closed {
		t.Error("runner not closed")
	}
	_, err := NewTool[shoutIn, shoutIn](b, "shout", "").RunRaw(ctx, map[string]any{"text": "x"})
	if status.Of(err) != status.FailedPrecondition {
		t.Errorf("call after Close: err = %v, want FAILED_PRECONDITION", err)
	}
}
