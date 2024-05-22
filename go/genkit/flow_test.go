// Copyright 2024 Google LLC
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

package genkit

import (
	"context"
	"encoding/json"
	"slices"
	"testing"

	"github.com/google/go-cmp/cmp"
	"github.com/google/go-cmp/cmp/cmpopts"
)

func incFlow(_ context.Context, i int, _ NoStream) (int, error) {
	return i + 1, nil
}

func TestFlowStart(t *testing.T) {
	f := DefineFlow("inc", incFlow)
	ss, err := NewFileFlowStateStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	f.stateStore = ss
	state, err := f.start(context.Background(), 1, nil)
	if err != nil {
		t.Fatal(err)
	}
	got := state.Operation
	want := &Operation[int]{
		Done: true,
		Result: &FlowResult[int]{
			Response: 2,
		},
	}
	if diff := cmp.Diff(want, got, cmpopts.IgnoreFields(Operation[int]{}, "FlowID")); diff != "" {
		t.Errorf("mismatch (-want, +got):\n%s", diff)
	}
}

func TestFlowRun(t *testing.T) {
	n := 0
	stepf := func() (int, error) {
		n++
		return n, nil
	}

	flow := DefineFlow("run", func(ctx context.Context, s string, _ NoStream) ([]int, error) {
		g1, err := Run(ctx, "s1", stepf)
		if err != nil {
			return nil, err
		}
		g2, err := Run(ctx, "s2", stepf)
		if err != nil {
			return nil, err
		}
		return []int{g1, g2}, nil
	})
	state, err := flow.start(context.Background(), "", nil)
	if err != nil {
		t.Fatal(err)
	}
	op := state.Operation
	if !op.Done {
		t.Fatal("not done")
	}
	got := op.Result.Response
	want := []int{1, 2}
	if !slices.Equal(got, want) {
		t.Errorf("got %v, want %v", got, want)
	}
}

func TestRunFlow(t *testing.T) {
	reg, err := newRegistry()
	if err != nil {
		t.Fatal(err)
	}
	f := defineFlow(reg, "inc", incFlow)
	got, err := RunFlow(context.Background(), f, 2)
	if err != nil {
		t.Fatal(err)
	}
	if want := 3; got != want {
		t.Errorf("got %d, want %d", got, want)
	}
}

func TestStreamFlow(t *testing.T) {
	reg, err := newRegistry()
	if err != nil {
		t.Fatal(err)
	}
	f := defineFlow(reg, "count", count)
	iter := StreamFlow(context.Background(), f, 2)
	want := 0
	iter(func(val *StreamFlowValue[int, int], err error) bool {
		if err != nil {
			t.Fatal(err)
		}
		var got int
		if val.Done {
			got = val.Output
		} else {
			got = val.Stream
		}
		if got != want {
			t.Errorf("got %d, want %d", got, want)
		}
		want++
		return true
	})
}

func TestFlowState(t *testing.T) {
	// A flowState is an action output, so it must support JSON marshaling.
	// Verify that a fully populated flowState can round-trip via JSON.

	fs := &flowState[int, int]{
		FlowID:          "id",
		FlowName:        "name",
		StartTime:       1,
		Input:           2,
		Cache:           map[string]json.RawMessage{"x": json.RawMessage([]byte("3"))},
		EventsTriggered: map[string]any{"a": "b"},
		Executions:      []*flowExecution{{StartTime: 4, EndTime: 5, TraceIDs: []string{"c"}}},
		Operation: &Operation[int]{
			FlowID:        "id",
			BlockedOnStep: &blockedOnStep{Name: "bos", Schema: "s"},
			Done:          true,
			Metadata:      "meta",
			Result: &FlowResult[int]{
				Response:   6,
				Error:      "err",
				StackTrace: "st",
			},
		},
		TraceContext: "tc",
	}
	data, err := json.Marshal(fs)
	if err != nil {
		t.Fatal(err)
	}
	var got *flowState[int, int]
	if err := json.Unmarshal(data, &got); err != nil {
		t.Fatal(err)
	}
	diff := cmp.Diff(fs, got, cmpopts.IgnoreUnexported(flowState[int, int]{}))
	if diff != "" {
		t.Errorf("mismatch (-want, +got):\n%s", diff)
	}
}
