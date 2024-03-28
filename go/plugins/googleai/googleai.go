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

	"github.com/FirebasePrivate/genkit/go/genkit"
	"github.com/google/generative-ai-go/genai"
	"google.golang.org/api/option"
)

func embed(ctx context.Context, client *genai.Client, model string, input []genai.Part) ([]float32, error) {
	em := client.EmbeddingModel(model)
	res, err := em.EmbedContent(ctx, input...)
	if err != nil {
		return nil, err
	}
	return res.Embedding.Values, nil
}

func newClient(ctx context.Context, apiKey string) (*genai.Client, error) {
	return genai.NewClient(ctx, option.WithAPIKey(apiKey))
}

// NewTextEmbedder returns an action which computes the embedding of
// the input string in the given google AI model.
func NewTextEmbedder(ctx context.Context, model, apiKey string) (*genkit.Action[string, []float32], error) {
	client, err := newClient(ctx, apiKey)
	if err != nil {
		return nil, err
	}
	return genkit.NewAction(
		"google-genai/text"+model,
		func(ctx context.Context, input string) ([]float32, error) {
			return embed(ctx, client, model, []genai.Part{genai.Text(input)})
		}), nil
}

// Init registers all the actions in this package with genkit.
func Init(ctx context.Context, model, apiKey string) error {
	t, err := NewTextEmbedder(ctx, model, apiKey)
	if err != nil {
		return err
	}
	genkit.RegisterAction(genkit.ActionTypeEmbedder, t.Name(), t)
	return nil
}
