// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0


package genkit

import (
	"context"
	"encoding/json"
	"errors"
	"slices"
	"testing"

	"github.com/firebase/genkit/go/core"
	"github.com/google/go-cmp/cmp"
	"github.com/google/go-cmp/cmp/cmpopts"
)

func incFlow(_ context.Context, i int, _ noStream) (int, error) {
	return i + 1, nil
}

func TestFlowStart(t *testing.T) {
	ai, err := New(nil)
	if err != nil {
		t.Fatal(err)
	}
	f := DefineStreamingFlow(ai, "inc", incFlow)
	ss, err := core.NewFileFlowStateStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	f.stateStore = ss
	state, err := f.start(context.Background(), 1, nil)
	if err != nil {
		t.Fatal(err)
	}
	got := state.Operation
	want := &operation[int]{
		Done: true,
		Result: &FlowResult[int]{
			Response: 2,
		},
	}
	diff := cmp.Diff(want, got,
		cmpopts.IgnoreFields(operation[int]{}, "FlowID"),
		cmpopts.IgnoreUnexported(FlowResult[int]{}, flowState[int, int]{}))
	if diff != "" {
		t.Errorf("mismatch (-want, +got):\n%s", diff)
	}
}

func TestFlowRun(t *testing.T) {
	ai, err := New(nil)
	if err != nil {
		t.Fatal(err)
	}
	n := 0
	stepf := func() (int, error) {
		n++
		return n, nil
	}

	flow := DefineFlow(ai, "run", func(ctx context.Context, s string) ([]int, error) {
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
	ai, err := New(nil)
	if err != nil {
		t.Fatal(err)
	}
	f := defineFlow(ai.reg, "inc", incFlow)
	got, err := f.Run(context.Background(), 2)
	if err != nil {
		t.Fatal(err)
	}
	if want := 3; got != want {
		t.Errorf("got %d, want %d", got, want)
	}
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
		Operation: &operation[int]{
			FlowID: "id",
			BlockedOnStep: &struct {
				Name   string `json:"name"`
				Schema string `json:"schema"`
			}{Name: "bos", Schema: "s"},
			Done:     true,
			Metadata: "meta",
			Result: &FlowResult[int]{
				Response:   6,
				err:        errors.New("err"),
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
	diff := cmp.Diff(fs, got, cmpopts.IgnoreUnexported(flowState[int, int]{}, FlowResult[int]{}))
	if diff != "" {
		t.Errorf("mismatch (-want, +got):\n%s", diff)
	}
}
