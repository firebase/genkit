// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0


package genkit

import (
	"context"
	"testing"
)

func TestStreamFlow(t *testing.T) {
	ai, err := New(nil)
	if err != nil {
		t.Fatal(err)
	}
	f := DefineStreamingFlow(ai, "count", count)
	iter := f.Stream(context.Background(), 2)
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

// count streams the numbers from 0 to n-1, then returns n.
func count(ctx context.Context, n int, cb func(context.Context, int) error) (int, error) {
	if cb != nil {
		for i := 0; i < n; i++ {
			if err := cb(ctx, i); err != nil {
				return 0, err
			}
		}
	}
	return n, nil
}
