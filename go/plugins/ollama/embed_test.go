// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package ollama

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
)

func TestEmbedValidRequest(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(ollamaEmbedResponse{
			Embeddings: [][]float32{{0.1, 0.2, 0.3}},
		})
	}))
	defer server.Close()

	req := &ai.EmbedRequest{
		Documents: []*ai.Document{
			ai.DocumentFromText("test", nil),
		},
		Options: &EmbedOptions{Model: "all-minilm"},
	}

	resp, err := embed(context.Background(), server.URL, req)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}

	if len(resp.Embeddings) != 1 {
		t.Fatalf("expected 1 embedding, got %d", len(resp.Embeddings))
	}
}

func TestEmbedInvalidServerAddress(t *testing.T) {
	req := &ai.EmbedRequest{
		Documents: []*ai.Document{
			ai.DocumentFromText("test", nil),
		},
		Options: &EmbedOptions{Model: "all-minilm"},
	}

	_, err := embed(context.Background(), "", req)
	if err == nil || !strings.Contains(err.Error(), "invalid server address") {
		t.Fatalf("expected invalid server address error, got %v", err)
	}
}
