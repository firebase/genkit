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
