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

	"github.com/firebase/genkit/go/ai"
)

// NewEmbedder returns an [ai.Embedder] that can compute the embedding
// of an input document given the Google AI model.
func NewEmbedder(ctx context.Context, model, apiKey string) (ai.Embedder, error) {
	client, err := newClient(ctx, apiKey)
	if err != nil {
		return nil, err
	}
	e := ai.DefineEmbedder("google-genai", model, func(ctx context.Context, input *ai.EmbedRequest) ([]float32, error) {
		em := client.EmbeddingModel(model)
		parts, err := convertParts(input.Document.Content)
		if err != nil {
			return nil, err
		}
		res, err := em.EmbedContent(ctx, parts...)
		if err != nil {
			return nil, err
		}
		return res.Embedding.Values, nil
	})
	return e, nil
}
