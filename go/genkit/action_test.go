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
	"bytes"
	"context"
	"testing"
)

func inc(_ context.Context, x int) (int, error) {
	return x + 1, nil
}

func TestActionRun(t *testing.T) {
	a := NewAction("inc", inc)
	got, err := a.Run(context.Background(), 3)
	if err != nil {
		t.Fatal(err)
	}
	if want := 4; got != want {
		t.Errorf("got %d, want %d", got, want)
	}
}

func TestActionRunJSON(t *testing.T) {
	a := NewAction("inc", inc)
	input := []byte("3")
	want := []byte("4")
	got, err := a.runJSON(context.Background(), input)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, want) {
		t.Errorf("got %v, want %v", got, want)
	}
}
