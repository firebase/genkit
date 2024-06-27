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

package fakeembedder

import (
	"context"
	"slices"
	"testing"

	"github.com/firebase/genkit/go/ai"
)

func TestFakeEmbedder(t *testing.T) {
	embed := New()
	emb := ai.DefineEmbedder("fake", "embed", embed.Embed)
	d := ai.DocumentFromText("fakeembedder test", nil)

	vals := []float32{1, 2}
	embed.Register(d, vals)

	req := &ai.EmbedRequest{
		Document: d,
	}
	ctx := context.Background()
	got, err := emb.Embed(ctx, req)
	if err != nil {
		t.Fatal(err)
	}
	if !slices.Equal(got, vals) {
		t.Errorf("lookup returned %v, want %v", got, vals)
	}

	req.Document = ai.DocumentFromText("missing document", nil)
	if _, err = emb.Embed(ctx, req); err == nil {
		t.Error("embedding unknown document succeeded unexpectedly")
	}
}
