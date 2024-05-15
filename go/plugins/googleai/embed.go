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

package googleai

import (
	"context"

	"github.com/google/generative-ai-go/genai"
	"github.com/google/genkit/go/ai"
)

type embedder struct {
	model  string
	client *genai.Client
}

func (e *embedder) Embed(ctx context.Context, input *ai.EmbedRequest) ([]float32, error) {
	em := e.client.EmbeddingModel(e.model)
	parts := convertParts(input.Document.Content)
	res, err := em.EmbedContent(ctx, parts...)
	if err != nil {
		return nil, err
	}
	return res.Embedding.Values, nil
}

// NewEmbedder returns an embedder which can compute the embedding
// of an input document given the Google AI model.
func NewEmbedder(ctx context.Context, model, apiKey string) (ai.Embedder, error) {
	client, err := newClient(ctx, apiKey)
	if err != nil {
		return nil, err
	}
	return &embedder{
		model:  model,
		client: client,
	}, nil
}
