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
)

func TestStreamFlow(t *testing.T) {
	f := DefineStreamingFlow("count", count)
	iter := f.Stream(context.Background(), 2)
	want := 0

	for {
		got, done := iter.Next()
		if done {
			break
		}
		if *got != want {
			t.Errorf("got %d, want %d", got, want)
		}
		want++
	}

	finalOutput, err := iter.FinalOutput()
	if err != nil {
		t.Fatal(err)
	}
	if *finalOutput != want {
		t.Errorf("got %d, want %d", finalOutput, want)
	}
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
