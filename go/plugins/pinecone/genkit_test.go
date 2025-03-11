// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package pinecone

import (
	"context"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/internal/fakeembedder"
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

	g, err := genkit.Init(context.Background())
	if err != nil {
		t.Fatal(err)
	}

	// Get information about the index.

	client, err := newClient(ctx, *testAPIKey)
	if err != nil {
		t.Fatal(err)
	}
	indexData, err := client.indexData(ctx, *testIndex)
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

	if err := Init(ctx, *testAPIKey); err != nil {
		t.Fatal(err)
	}
	cfg := Config{
		IndexID:  *testIndex,
		Embedder: genkit.DefineEmbedder(g, "fake", "embedder3", embedder.Embed),
	}
	indexer, err := DefineIndexer(ctx, g, cfg)
	if err != nil {
		t.Fatal(err)
	}
	retriever, err := DefineRetriever(ctx, g, cfg)
	if err != nil {
		t.Fatal(err)
	}

	indexerOptions := &IndexerOptions{
		Namespace: namespace,
	}

	t.Logf("index flag = %q, indexData.Host = %q", *testIndex, indexData.Host)
	err = ai.Index(ctx, indexer, ai.WithIndexerOpts(indexerOptions), ai.WithIndexerDocs(d1, d2, d3))
	if err != nil {
		t.Fatalf("Index operation failed: %v", err)
	}

	defer func() {
		idx, err := client.index(ctx, indexData.Host)
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

		if err := idx.deleteByID(ctx, ids, namespace); err != nil {
			t.Errorf("error deleting test vectors: %v", err)
		}
	}()

	retrieverOptions := &RetrieverOptions{
		Count:     2,
		Namespace: namespace,
	}
	retrieverResp, err := ai.Retrieve(ctx, retriever,
		ai.WithRetrieverDoc(d1),
		ai.WithRetrieverOpts(retrieverOptions))
	if err != nil {
		t.Fatalf("Retrieve operation failed: %v", err)
	}

	docs := retrieverResp.Documents
	if len(docs) != 2 {
		t.Errorf("got %d results, expected 2", len(docs))
	}
	for _, d := range docs {
		text := d.Content[0].Text
		if !strings.HasPrefix(text, "hello") {
			t.Errorf("returned doc text %q does not start with %q", text, "hello")
		}
	}
}
