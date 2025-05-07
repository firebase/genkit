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

package compat_oai

import (
	"context"
	"errors"
	"strings"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	openaiGo "github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
)

var (
	// BasicText describes model capabilities for text-only GPT models.
	BasicText = ai.ModelInfo{
		Supports: &ai.ModelSupports{
			Multiturn:  true,
			Tools:      true,
			SystemRole: true,
			Media:      false,
		},
	}

	// Multimodal describes model capabilities for multimodal GPT models.
	Multimodal = ai.ModelInfo{
		Supports: &ai.ModelSupports{
			Multiturn:  true,
			Tools:      true,
			SystemRole: true,
			Media:      true,
			ToolChoice: true,
		},
	}
)

// OpenAICompatible is a plugin that provides compatibility with OpenAI's Compatible APIs.
// It allows defining models and embedders that can be used with Genkit.
type OpenAICompatible struct {
	// mu protects concurrent access to the client and initialization state
	mu sync.Mutex

	// initted tracks whether the plugin has been initialized
	initted bool

	// client is the OpenAI client used for making API requests
	// see https://github.com/openai/openai-go
	client *openaiGo.Client

	// Opts contains request options for the OpenAI client.
	// Required: Must include at least WithAPIKey for authentication.
	// Optional: Can include other options like WithOrganization, WithBaseURL, etc.
	Opts []option.RequestOption

	// Provider is a unique identifier for the plugin.
	// This will be used as a prefix for model names (e.g., "myprovider/model-name").
	// Should be lowercase and match the plugin's Name() method.
	Provider string
}

// Init implements genkit.Plugin.
func (o *OpenAICompatible) Init(ctx context.Context, g *genkit.Genkit) error {
	o.mu.Lock()
	defer o.mu.Unlock()
	if o.initted {
		return errors.New("compat_oai.Init already called")
	}

	// create client
	client := openaiGo.NewClient(o.Opts...)
	o.client = client
	o.initted = true

	return nil
}

// Name implements genkit.Plugin.
func (o *OpenAICompatible) Name() string {
	return o.Provider
}

// DefineModel defines a model in the registry
func (o *OpenAICompatible) DefineModel(g *genkit.Genkit, provider, name string, info ai.ModelInfo) (ai.Model, error) {
	o.mu.Lock()
	defer o.mu.Unlock()
	if !o.initted {
		return nil, errors.New("OpenAICompatible.Init not called")
	}

	// Strip provider prefix if present to check against supportedModels
	modelName := strings.TrimPrefix(name, provider+"/")

	return genkit.DefineModel(g, provider, name, &info, func(
		ctx context.Context,
		input *ai.ModelRequest,
		cb func(context.Context, *ai.ModelResponseChunk) error,
	) (*ai.ModelResponse, error) {

		// Configure the response generator with input
		generator := NewModelGenerator(o.client, modelName).WithMessages(input.Messages).WithConfig(input.Config).WithTools(input.Tools, input.ToolChoice)

		// Generate response
		resp, err := generator.Generate(ctx, cb)
		if err != nil {
			return nil, err
		}

		return resp, nil
	}), nil
}

// DefineEmbedder defines an embedder with a given name.
func (o *OpenAICompatible) DefineEmbedder(g *genkit.Genkit, provider, name string) (ai.Embedder, error) {
	o.mu.Lock()
	defer o.mu.Unlock()
	if !o.initted {
		return nil, errors.New("OpenAICompatible.Init not called")
	}

	return genkit.DefineEmbedder(g, provider, name, func(ctx context.Context, input *ai.EmbedRequest) (*ai.EmbedResponse, error) {
		var data openaiGo.EmbeddingNewParamsInputArrayOfStrings
		for _, doc := range input.Input {
			for _, p := range doc.Content {
				data = append(data, p.Text)
			}
		}

		params := openaiGo.EmbeddingNewParams{
			Input:          openaiGo.F[openaiGo.EmbeddingNewParamsInputUnion](data),
			Model:          openaiGo.F(name),
			EncodingFormat: openaiGo.F(openaiGo.EmbeddingNewParamsEncodingFormatFloat),
		}

		embeddingResp, err := o.client.Embeddings.New(ctx, params)
		if err != nil {
			return nil, err
		}

		resp := &ai.EmbedResponse{}
		for _, emb := range embeddingResp.Data {
			embedding := make([]float32, len(emb.Embedding))
			for i, val := range emb.Embedding {
				embedding[i] = float32(val)
			}
			resp.Embeddings = append(resp.Embeddings, &ai.Embedding{Embedding: embedding})
		}
		return resp, nil
	}), nil
}

// IsDefinedEmbedder reports whether the named [Embedder] is defined by this plugin.
func (o *OpenAICompatible) IsDefinedEmbedder(g *genkit.Genkit, name string, provider string) bool {
	return genkit.LookupEmbedder(g, provider, name) != nil
}

// Embedder returns the [ai.Embedder] with the given name.
// It returns nil if the embedder was not defined.
func (o *OpenAICompatible) Embedder(g *genkit.Genkit, name string, provider string) ai.Embedder {
	return genkit.LookupEmbedder(g, provider, name)
}

// Model returns the [ai.Model] with the given name.
// It returns nil if the model was not defined.
func (o *OpenAICompatible) Model(g *genkit.Genkit, name string, provider string) ai.Model {
	return genkit.LookupModel(g, provider, name)
}

// IsDefinedModel reports whether the named [Model] is defined by this plugin.
func (o *OpenAICompatible) IsDefinedModel(g *genkit.Genkit, name string, provider string) bool {
	return genkit.LookupModel(g, provider, name) != nil
}
