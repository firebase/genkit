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
	"slices"
	"testing"
)

func inc(_ context.Context, x int) (int, error) {
	return x + 1, nil
}

func TestActionRun(t *testing.T) {
	a := NewAction("inc", inc)
	got, err := a.Run(context.Background(), 3, nil)
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
	got, err := a.runJSON(context.Background(), input, nil)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, want) {
		t.Errorf("got %v, want %v", got, want)
	}
}

// count streams the numbers from 0 to n-1, then returns n.
func count(ctx context.Context, n int, cb StreamingCallback[int]) (int, error) {
	if cb != nil {
		for i := 0; i < n; i++ {
			if err := cb(ctx, i); err != nil {
				return 0, err
			}
		}
	}
	return n, nil
}

func TestActionStreaming(t *testing.T) {
	ctx := context.Background()
	a := NewStreamingAction("count", count)
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
