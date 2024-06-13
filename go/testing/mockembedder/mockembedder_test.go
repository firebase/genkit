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

package mockembedder

import (
	"context"
	"slices"
	"testing"

	"github.com/firebase/genkit/go/ai"
)

func TestMockEmbedder(t *testing.T) {
	mock := New()
	embedAction := ai.DefineEmbedder("mock", "embed", mock.Embed)
	d := ai.DocumentFromText("mockembedder test", nil)

	vals := []float32{1, 2}
	mock.Register(d, vals)

	req := &ai.EmbedRequest{
		Document: d,
	}
	ctx := context.Background()
	got, err := ai.Embed(ctx, embedAction, req)
	if err != nil {
		t.Fatal(err)
	}
	if !slices.Equal(got, vals) {
		t.Errorf("lookup returned %v, want %v", got, vals)
	}

	req.Document = ai.DocumentFromText("missing document", nil)
	if _, err = ai.Embed(ctx, embedAction, req); err == nil {
		t.Error("embedding unknown document succeeded unexpectedly")
	}
}
