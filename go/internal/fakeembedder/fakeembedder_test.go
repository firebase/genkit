// Copyright 2024 Google LLC
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
	res, err := ai.Embed(ctx, emb, ai.WithEmbedDocs(d))
	if err != nil {
		t.Fatal(err)
	}
	got := res.Embeddings[0].Embedding
	if !slices.Equal(got, vals) {
		t.Errorf("lookup returned %v, want %v", got, vals)
	}

	if _, err = ai.Embed(ctx, emb, ai.WithEmbedText("missing document")); err == nil {
		t.Error("embedding unknown document succeeded unexpectedly")
	}
}
