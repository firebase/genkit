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

func TestEmbedInvalidModel(t *testing.T) {
	req := &ai.EmbedRequest{
		Documents: []*ai.Document{
			ai.DocumentFromText("test", nil),
		},
		Options: &EmbedOptions{Model: "invalid-model"},
	}

	_, err := embed(context.Background(), "http://localhost:11434", req)
	if err == nil || !strings.Contains(err.Error(), "invalid embedding model") {
		t.Fatalf("expected invalid model error, got %v", err)
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
