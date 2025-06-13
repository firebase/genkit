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

package core

import (
	"bytes"
	"context"
	"fmt"
	"slices"
	"testing"

	"github.com/firebase/genkit/go/core/tracing"
	"github.com/firebase/genkit/go/internal/registry"
)

func inc(_ context.Context, x int, _ noStream) (int, error) {
	return x + 1, nil
}

func TestActionRun(t *testing.T) {
	r, err := registry.New()
	if err != nil {
		t.Fatal(err)
	}
	a := defineAction(r, "test", "inc", ActionTypeCustom, nil, nil, inc)
	got, err := a.Run(context.Background(), 3, nil)
	if err != nil {
		t.Fatal(err)
	}
	if want := 4; got != want {
		t.Errorf("got %d, want %d", got, want)
	}
}

func TestActionRunJSON(t *testing.T) {
	r, err := registry.New()
	if err != nil {
		t.Fatal(err)
	}
	a := defineAction(r, "test", "inc", ActionTypeCustom, nil, nil, inc)
	input := []byte("3")
	want := []byte("4")
	got, err := a.RunJSON(context.Background(), input, nil)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, want) {
		t.Errorf("got %v, want %v", got, want)
	}
}

// count streams the numbers from 0 to n-1, then returns n.
func count(ctx context.Context, n int, cb func(context.Context, int) error) (int, error) {
	if cb != nil {
		for i := range n {
			if err := cb(ctx, i); err != nil {
				return 0, err
			}
		}
	}
	return n, nil
}

func TestActionStreaming(t *testing.T) {
	ctx := context.Background()
	r, err := registry.New()
	if err != nil {
		t.Fatal(err)
	}
	a := defineAction(r, "test", "count", ActionTypeCustom, nil, nil, count)
	const n = 3

	// Non-streaming.
	got, err := a.Run(ctx, n, nil)
	if err != nil {
		t.Fatal(err)
	}
	if got != n {
		t.Fatalf("got %d, want %d", got, n)
	}

	// Streaming.
	var gotStreamed []int
	got, err = a.Run(ctx, n, func(_ context.Context, i int) error {
		gotStreamed = append(gotStreamed, i)
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	wantStreamed := []int{0, 1, 2}
	if !slices.Equal(gotStreamed, wantStreamed) {
		t.Errorf("got %v, want %v", gotStreamed, wantStreamed)
	}
	if got != n {
		t.Errorf("got %d, want %d", got, n)
	}
}

func TestActionTracing(t *testing.T) {
	r, err := registry.New()
	if err != nil {
		t.Fatal(err)
	}
	provider := "test"
	tc := tracing.NewTestOnlyTelemetryClient()
	r.TracingState().WriteTelemetryImmediate(tc)
	const actionName = "TestTracing-inc"
	a := defineAction(r, provider, actionName, ActionTypeCustom, nil, nil, inc)
	if _, err := a.Run(context.Background(), 3, nil); err != nil {
		t.Fatal(err)
	}
	// The same trace store is used for all tests, so there might be several traces.
	// Look for this one, which has a unique name.
	fullActionName := fmt.Sprintf("%s/%s", provider, actionName)
	for _, td := range tc.Traces {
		if td.DisplayName == fullActionName {
			// Spot check: expect a single span.
			if g, w := len(td.Spans), 1; g != w {
				t.Errorf("got %d spans, want %d", g, w)
			}
			return
		}
	}
	t.Fatalf("did not find trace named %q", actionName)
}
