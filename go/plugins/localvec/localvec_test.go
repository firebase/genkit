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

package localvec

import (
	"context"
	"math"
	"strings"
	"testing"

	"github.com/google/genkit/go/ai"
	"github.com/google/genkit/go/internal/fakeembedder"
)

func TestLocalVec(t *testing.T) {
	ctx := context.Background()

	// Make two very similar vectors and one different vector.
	// Arrange for a fake embedder to return those vector
	// when provided with documents.

	const dim = 32
	v1 := make([]float32, dim)
	v2 := make([]float32, dim)
	v3 := make([]float32, dim)
	for i := range v1 {
		v1[i] = float32(i)
		v2[i] = float32(i)
		v3[i] = float32(dim - i)
	}
	v2[0] = 1

	d1 := ai.DocumentFromText("hello1", nil)
	d2 := ai.DocumentFromText("hello2", nil)
	d3 := ai.DocumentFromText("goodbye", nil)

	embedder := fakeembedder.New()
	embedder.Register(d1, v1)
	embedder.Register(d2, v2)
	embedder.Register(d3, v3)

	r, err := newRetriever(ctx, t.TempDir(), "testLocalVec", embedder, nil)
	if err != nil {
		t.Fatal(err)
	}

	indexerReq := &ai.IndexerRequest{
		Documents: []*ai.Document{d1, d2, d3},
	}
	err = r.Index(ctx, indexerReq)
	if err != nil {
		t.Fatalf("Index operation failed: %v", err)
	}

	retrieverOptions := &RetrieverOptions{
		K: 2,
	}

	retrieverReq := &ai.RetrieverRequest{
		Document: d1,
		Options:  retrieverOptions,
	}
	retrieverResp, err := r.Retrieve(ctx, retrieverReq)
	if err != nil {
		t.Fatalf("Retrieve operation failed: %v", err)
	}

	docs := retrieverResp.Documents
	if len(docs) != 2 {
		t.Errorf("got %d results, expected 2", len(docs))
	}
	for _, d := range docs {
		text := d.Content[0].Text()
		if !strings.HasPrefix(text, "hello") {
			t.Errorf("returned doc text %q does not start with %q", text, "hello")
		}
	}
}

func TestSimilarity(t *testing.T) {
	x := []float32{5, 23, 2, 5, 9}
	y := []float32{3, 21, 2, 5, 14}
	got := similarity(x, y)
	want := 0.975
	if math.Abs(got-want) > 0.001 {
		t.Errorf("got %f, want %f", got, want)
	}
}
