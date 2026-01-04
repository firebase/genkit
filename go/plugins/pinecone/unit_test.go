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

package pinecone

import (
	"context"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/api"
)

// mockEmbedder is a simple mock for ai.Embedder
type mockEmbedder struct{}

func (m *mockEmbedder) Embed(ctx context.Context, req *ai.EmbedRequest) (*ai.EmbedResponse, error) {
	return &ai.EmbedResponse{}, nil
}

func (m *mockEmbedder) Name() string {
	return "mock-embedder"
}

func (m *mockEmbedder) Register(r api.Registry) {
}

func TestPineconeCache(t *testing.T) {
	// Initialize Pinecone with a dummy API key to pass the check in Init
	p := &Pinecone{
		APIKey: "dummy-key",
	}

	// Manually initialize the plugin to set up the client and cache
	p.Init(context.Background())

	// Define a fake index ID and fake index data
	fakeIndexID := "fake-index"
	fakeHost := "fake-host.pinecone.io"
	fakeData := &indexData{
		Name: fakeIndexID,
		Host: fakeHost,
	}

	// Pre-populate the cache with the fake data
	p.indexDataCache[fakeIndexID] = fakeData

	// Create a config that uses the fake index ID
	cfg := Config{
		IndexID:  fakeIndexID,
		Embedder: &mockEmbedder{},
	}

	// Call newDocstore.
	// If the cache works, it should use fakeData.Host.
	// If the cache fails, it will try to make a network call with the dummy key and fail,
	// or it will fail because the dummy key is invalid.
	// Note: p.client.indexData will fail if called because "dummy-key" is likely invalid
	// or network is unreachable or simply because we don't want it to run.

	// Actually, if it tries to call indexData, it will likely return an error because
	// the API key is fake. So if newDocstore returns success (or fails later at index creation),
	// we know it passed the indexData step.

	// However, newDocstore also calls `p.client.index(ctx, indexData.Host)`.
	// `client.index` just returns a struct, it doesn't make a network call.

	ds, err := p.newDocstore(context.Background(), cfg)
	if err != nil {
		t.Fatalf("newDocstore failed: %v", err)
	}

	// Verify that the returned Docstore has the correct index host
	if ds.Index.host != fakeHost {
		t.Errorf("expected host %q, got %q", fakeHost, ds.Index.host)
	}

	// Verify that the cache entry is still there
	if cached, ok := p.indexDataCache[fakeIndexID]; !ok || cached != fakeData {
		t.Error("cache entry missing or incorrect")
	}
}

func TestPineconeCacheMiss(t *testing.T) {
	// Initialize Pinecone with a dummy API key
	p := &Pinecone{
		APIKey: "dummy-key",
	}
	p.Init(context.Background())

	// Use an index ID that is NOT in the cache
	cfg := Config{
		IndexID:  "missing-index",
		Embedder: &mockEmbedder{},
	}

	// This should fail because it tries to call indexData with a dummy key
	_, err := p.newDocstore(context.Background(), cfg)
	if err == nil {
		t.Error("expected newDocstore to fail on cache miss with dummy key, but it succeeded")
	}
}
