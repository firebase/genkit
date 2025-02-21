// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package weaviate

import (
	"context"
	"flag"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/internal/fakeembedder"
)

var (
	testAddr   = flag.String("test-weaviate-addr", "", "Weaviate address to use for tests")
	testScheme = flag.String("test-weaviate-scheme", "", "Weaviate scheme to use for tests")
	testAPIKey = flag.String("test-weaviate-api-key", "", "Weaviate API key to use for tests")
	testClass  = flag.String("test-weaviate-class", "", "Weaviate class to use for tests")
)

func TestGenkit(t *testing.T) {
	if *testAddr == "" {
		t.Skip("skipping test because -test-weaviate-addr flag not used")
	}
	if *testClass == "" {
		t.Skip("skipping test because -test-weaviate-class flag not used")
	}

	ctx := context.Background()

	g, err := genkit.Init(context.Background())
	if err != nil {
		t.Fatal(err)
	}

	// Make two very similar vectors and one different vector.
	// Arrange for a fake embedder to return those vectors
	// when provided with documents.

	const dim = 768

	v1 := make([]float32, dim)
	v2 := make([]float32, dim)
	v3 := make([]float32, dim)
	for i := range v1 {
		v1[i] = float32(i)
		v2[i] = float32(i)
		v3[i] = float32(dim - i)
	}
	v2[0] = 1

	d1 := ai.DocumentFromText("hello1", map[string]any{"name": "hello1"})
	d2 := ai.DocumentFromText("hello2", map[string]any{"name": "hello2"})
	d3 := ai.DocumentFromText("goodbye", map[string]any{"name": "goodbye"})

	embedder := fakeembedder.New()
	embedder.Register(d1, v1)
	embedder.Register(d2, v2)
	embedder.Register(d3, v3)

	clientCfg := &ClientConfig{
		Addr:   *testAddr,
		Scheme: *testScheme,
		APIKey: *testAPIKey,
	}
	client, err := Init(ctx, clientCfg)
	if err != nil {
		t.Fatal(err)
	}

	// Delete our test class so that earlier runs don't mess us up.
	if err := client.Schema().ClassDeleter().WithClassName(*testClass).Do(ctx); err != nil {
		t.Fatal(err)
	}

	classCfg := ClassConfig{
		Class:    *testClass,
		Embedder: genkit.DefineEmbedder(g, "fake", "embedder3", embedder.Embed),
	}
	indexer, retriever, err := DefineIndexerAndRetriever(ctx, g, classCfg)
	if err != nil {
		t.Fatal(err)
	}

	err = ai.Index(ctx, indexer, ai.WithIndexerDocs(d1, d2, d3))
	if err != nil {
		t.Fatalf("Index operation failed: %v", err)
	}

	retrieverOptions := &RetrieverOptions{
		Count:        2,
		MetadataKeys: []string{"name"},
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
		name, ok := d.Metadata["name"]
		if !ok {
			t.Errorf("missing metadata entry for name: %v", d.Metadata)
		} else if !strings.HasPrefix(name.(string), "hello") {
			t.Errorf("metadata name entry %q does not start with %q", name, "hello")
		}
	}
}
