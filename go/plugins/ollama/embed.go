// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package ollama

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

type EmbedOptions struct {
	Model string `json:"model"`
}

type ollamaEmbedRequest struct {
	Model   string                 `json:"model"`
	Input   interface{}            `json:"input"` // todo: using interface{} to handle both string and []string, figure out better solution
	Options map[string]interface{} `json:"options,omitempty"`
}

type ollamaEmbedResponse struct {
	Embeddings [][]float32 `json:"embeddings"`
}

func embed(ctx context.Context, serverAddress string, req *ai.EmbedRequest) (*ai.EmbedResponse, error) {
	options, ok := req.Options.(*EmbedOptions)
	if !ok && req.Options != nil {
		return nil, fmt.Errorf("invalid options type: expected *EmbedOptions")
	}
	if options == nil || options.Model == "" {
		return nil, fmt.Errorf("invalid embedding model: model must be specified")
	}

	if serverAddress == "" {
		return nil, fmt.Errorf("invalid server address: address cannot be empty")
	}

	ollamaReq := newOllamaEmbedRequest(options.Model, req.Documents)

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

func concatenateText(doc *ai.Document) string {
	var builder strings.Builder
	for _, part := range doc.Content {
		builder.WriteString(part.Text)
	}
	result := builder.String()
	return result
}

// DefineEmbedder defines an embedder with a given server address.
func DefineEmbedder(g *genkit.Genkit, serverAddress string, model string) ai.Embedder {
	state.mu.Lock()
	defer state.mu.Unlock()
	if !state.initted {
		panic("ollama.Init not called")
	}
	return genkit.DefineEmbedder(g, provider, serverAddress, func(ctx context.Context, req *ai.EmbedRequest) (*ai.EmbedResponse, error) {
		if req.Options == nil {
			req.Options = &EmbedOptions{Model: model}
		}
		if req.Options.(*EmbedOptions).Model == "" {
			req.Options.(*EmbedOptions).Model = model
		}
		return embed(ctx, serverAddress, req)
	})
}

// IsDefinedEmbedder reports whether the embedder with the given server address is defined by this plugin.
func IsDefinedEmbedder(g *genkit.Genkit, serverAddress string) bool {
	isDefined := genkit.IsDefinedEmbedder(g, provider, serverAddress)
	return isDefined
}

// Embedder returns the [ai.Embedder] with the given server address.
// It returns nil if the embedder was not defined.
func Embedder(g *genkit.Genkit, serverAddress string) ai.Embedder {
	return genkit.LookupEmbedder(g, provider, serverAddress)
}
