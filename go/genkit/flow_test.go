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
	"slices"
	"testing"

	"github.com/google/go-cmp/cmp"
	"github.com/google/go-cmp/cmp/cmpopts"
)

func TestFlowStart(t *testing.T) {
	f := DefineFlow("inc", inc)
	ss, err := NewFileFlowStateStore(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	f.stateStore = ss
	state, err := f.start(context.Background(), 1)
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

	flow := DefineFlow("run", func(ctx context.Context, s string) ([]int, error) {
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
	state, err := flow.start(context.Background(), "")
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
