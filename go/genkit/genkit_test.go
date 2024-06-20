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
