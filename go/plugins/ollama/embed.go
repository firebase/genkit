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
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"

	"github.com/firebase/genkit/go/ai"
)

var supportedEmbeddingModels = []string{
	"mxbai-embed-large",
	"nomic-embed-text",
	"all-minilm", // Default if not specified
}

type EmbedOptions struct {
	Model string `json:"model,omitempty"`
}

type ollamaEmbedRequest struct {
	Model   string                 `json:"model"`
	Input   interface{}            `json:"input"` // Change to interface{} to handle both string and []string
	Options map[string]interface{} `json:"options,omitempty"`
}

type ollamaEmbedResponse struct {
	Embeddings [][]float32 `json:"embeddings"`
}

// embed performs the actual embedding request to the Ollama server
func embed(ctx context.Context, serverAddress string, req *ai.EmbedRequest) (*ai.EmbedResponse, error) {
	options, ok := req.Options.(*EmbedOptions)
	if !ok && req.Options != nil {
		return nil, fmt.Errorf("invalid options type: expected *EmbedOptions")
	}

	model := getEmbeddingModel(options)

	if model == "" {
		return nil, fmt.Errorf("invalid embedding model: model cannot be empty")
	}

	if serverAddress == "" {
		return nil, fmt.Errorf("invalid server address: address cannot be empty")
	}

	ollamaReq := newOllamaEmbedRequest(model, req.Documents)

	jsonData, err := json.Marshal(ollamaReq)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal embed request: %w", err)
	}

	resp, err := sendEmbedRequest(ctx, serverAddress, jsonData)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("ollama embed request failed with status code %d", resp.StatusCode)
	}

	var ollamaResp ollamaEmbedResponse
	if err := json.NewDecoder(resp.Body).Decode(&ollamaResp); err != nil {
		return nil, fmt.Errorf("failed to decode embed response: %w", err)
	}

	return newEmbedResponse(ollamaResp.Embeddings), nil
}

// getEmbeddingModel determines the appropriate embedding model to use
func getEmbeddingModel(options *EmbedOptions) string {
	model := options.Model
	for _, supportedModel := range supportedEmbeddingModels {
		if model == supportedModel {
			return model
		}
	}
	return ""
}

// sendEmbedRequest sends the actual HTTP request to the Ollama server
func sendEmbedRequest(ctx context.Context, serverAddress string, jsonData []byte) (*http.Response, error) {
	client := &http.Client{}
	httpReq, err := http.NewRequestWithContext(ctx, "POST", serverAddress+"/api/embed", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	httpReq.Header.Set("Content-Type", "application/json")
	return client.Do(httpReq)
}

func newOllamaEmbedRequest(model string, documents []*ai.Document) ollamaEmbedRequest {
	var input interface{}
	if len(documents) == 1 {
		input = concatenateText(documents[0])
	} else {
		texts := make([]string, len(documents))
		for i, doc := range documents {
			texts[i] = concatenateText(doc)
		}
		input = texts
	}

	return ollamaEmbedRequest{
		Model: model,
		Input: input,
	}
}

func newEmbedResponse(embeddings [][]float32) *ai.EmbedResponse {
	resp := &ai.EmbedResponse{
		Embeddings: make([]*ai.DocumentEmbedding, len(embeddings)),
	}
	for i, embedding := range embeddings {
		resp.Embeddings[i] = &ai.DocumentEmbedding{Embedding: embedding}
	}
	return resp
}

// concatenateText combines all text content from a document into a single string.
func concatenateText(doc *ai.Document) string {
	var builder strings.Builder
	for _, part := range doc.Content {
		builder.WriteString(part.Text)
	}
	result := builder.String()
	return result
}

// DefineEmbedder defines an embedder with a given server address.
func DefineEmbedder(serverAddress string) ai.Embedder {
	state.mu.Lock()
	defer state.mu.Unlock()
	if !state.initted {
		panic("ollama.Init not called")
	}
	return ai.DefineEmbedder(provider, serverAddress, func(ctx context.Context, req *ai.EmbedRequest) (*ai.EmbedResponse, error) {
		return embed(ctx, serverAddress, req)
	})
}

// IsDefinedEmbedder reports whether the embedder with the given server address is defined by this plugin.
func IsDefinedEmbedder(serverAddress string) bool {
	isDefined := ai.IsDefinedEmbedder(provider, serverAddress)
	return isDefined
}

// Embedder returns the [ai.Embedder] with the given server address.
// It returns nil if the embedder was not defined.
func Embedder(serverAddress string) ai.Embedder {
	return ai.LookupEmbedder(provider, serverAddress)
}
