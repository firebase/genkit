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
	"io"
	"log"
	"net/http"
	"strings"

	"github.com/firebase/genkit/go/ai"
)

const (
	defaultEmbeddingModel = "all-minilm"
	defaultOllamaAddress  = "http://localhost:11434"
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
		body, _ := io.ReadAll(resp.Body)
		fmt.Printf("Ollama embed request failed with status code %d. Response body: %s\n", resp.StatusCode, string(body))
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
	fmt.Println("Concatenating text for document:")
	for _, part := range doc.Content {
		builder.WriteString(part.Text)
	}
	result := builder.String()
	fmt.Printf("Concatenated result: %s\n", result)
	return result
}

// DefineEmbedder defines an embedder with a given server address.
func DefineEmbedder(serverAddress string) ai.Embedder {
	state.mu.Lock()
	defer state.mu.Unlock()
	if !state.initted {
		panic("ollama.Init not called")
	}
	log.Printf("Defining embedder with server address: %s", serverAddress)
	return defineEmbedder(serverAddress)
}

// defineEmbedder creates and returns an ai.Embedder for the given server address
func defineEmbedder(serverAddress string) ai.Embedder {
	log.Printf("Defining embedder function for server address: %s", serverAddress)
	return ai.DefineEmbedder(provider, serverAddress, func(ctx context.Context, req *ai.EmbedRequest) (*ai.EmbedResponse, error) {
		log.Printf("Embedding request received for server address: %s", serverAddress)
		return embed(ctx, serverAddress, req)
	})
}

// IsDefinedEmbedder reports whether the embedder with the given server address is defined by this plugin.
func IsDefinedEmbedder(serverAddress string) bool {
	isDefined := ai.IsDefinedEmbedder(provider, serverAddress)
	log.Printf("Checking if embedder is defined for server address %s: %v", serverAddress, isDefined)
	return isDefined
}

// Embedder returns the [ai.Embedder] with the given server address.
// It returns nil if the embedder was not defined.
func Embedder(serverAddress string) ai.Embedder {
	embedder := ai.LookupEmbedder(provider, serverAddress)
	if embedder == nil {
		log.Printf("No embedder found for server address: %s", serverAddress)
	} else {
		log.Printf("Found embedder for server address: %s", serverAddress)
	}
	return embedder
}
