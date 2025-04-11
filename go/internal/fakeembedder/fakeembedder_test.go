// Copyright 2025 Google LLC
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
//
// SPDX-License-Identifier: Apache-2.0

package fakeembedder

import (
	"context"
	"slices"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/internal/registry"
)

func TestFakeEmbedder(t *testing.T) {
	r, err := registry.New()
	if err != nil {
		t.Fatal(err)
	}

	embed := New()
	emb := ai.DefineEmbedder(r, "fake", "embed", embed.Embed)
	d := ai.DocumentFromText("fakeembedder test", nil)

	vals := []float32{1, 2}
	embed.Register(d, vals)

	ctx := context.Background()
	res, err := ai.Embed(ctx, emb, ai.WithDocs(d))
	if err != nil {
		t.Fatal(err)
	}
	got := res.Embeddings[0].Embedding
	if !slices.Equal(got, vals) {
		t.Errorf("lookup returned %v, want %v", got, vals)
	}

	if _, err = ai.Embed(ctx, emb, ai.WithTextDocs("missing document")); err == nil {
		t.Error("embedding unknown document succeeded unexpectedly")
	}
}
