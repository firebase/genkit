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

package pinecone

import (
	"context"
	"strings"
	"testing"

	"github.com/google/genkit/go/ai"
	"github.com/google/genkit/go/internal/fakeembedder"
)

func TestGenkit(t *testing.T) {
	if *testAPIKey == "" {
		t.Skip("skipping test because -test-pinecone-api-key flag not used")
	}
	if *testIndex == "" {
		t.Skip("skipping test because -test-pinecone-index flag not used")
	}

	// We use a different namespace for each test to avoid confusion.
	namespace := *testNamespace + "TestGenkit"

	ctx := context.Background()

	// Get information about the index.

	client, err := NewClient(ctx, *testAPIKey)
	if err != nil {
		t.Fatal(err)
	}
	indexData, err := client.IndexData(ctx, *testIndex)
	if err != nil {
		t.Fatal(err)
	}

	dim := indexData.Dimension

	// Make two very similar vectors and one different vector.
	// Arrange for a fake embedder to return those vector
	// when provided with documents.

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

	r, err := newRetriever(ctx, *testAPIKey, indexData.Host, embedder, nil, "")
	if err != nil {
		t.Fatal(err)
	}

	indexerOptions := &IndexerOptions{
		Namespace: namespace,
	}

	indexerReq := &ai.IndexerRequest{
		Documents: []*ai.Document{d1, d2, d3},
		Options:   indexerOptions,
	}
	err = r.Index(ctx, indexerReq)
	if err != nil {
		t.Fatalf("Index operation failed: %v", err)
	}

	defer func() {
		idx, err := client.Index(ctx, indexData.Host)
		if err != nil {
			t.Fatal(err)
		}
		var ids []string
		addID := func(d *ai.Document) {
			id, err := docID(d)
			if err != nil {
				t.Error("can't get document ID")
				return
			}
			ids = append(ids, id)
		}
		addID(d1)
		addID(d2)
		addID(d3)

		if err := idx.DeleteByID(ctx, ids, namespace); err != nil {
			t.Errorf("error deleting test vectors: %v", err)
		}
	}()

	retrieverOptions := &RetrieverOptions{
		Count:     2,
		Namespace: namespace,
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
