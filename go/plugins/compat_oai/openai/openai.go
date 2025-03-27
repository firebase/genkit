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

package openai

import (
	"context"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/compat_oai"
	openaiGo "github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
)

const provider = "openai"

var (
	supportedModels = map[string]ai.ModelInfo{
		openaiGo.ChatModelGPT4oMini: {
			Label:    "GPT-4o-mini",
			Supports: compat_oai.Multimodal.Supports,
		},
	}

	knownEmbedders = []string{
		openaiGo.EmbeddingModelTextEmbedding3Small,
		openaiGo.EmbeddingModelTextEmbedding3Large,
		openaiGo.EmbeddingModelTextEmbeddingAda002,
	}
)

type OpenAI struct {
	Opts             []option.RequestOption
	openAICompatible compat_oai.OpenAICompatible
}

// Name implements genkit.Plugin.
func (o *OpenAI) Name() string {
	return provider
}

func (o *OpenAI) Init(ctx context.Context, g *genkit.Genkit) error {
	err := o.openAICompatible.Init(ctx, g)
	if err != nil {
		return err
	}

	// define default models
	for model, info := range supportedModels {
		_, err := o.DefineModel(g, model, info)
		if err != nil {
			return err
		}
	}

	// define default embedders
	for _, embedder := range knownEmbedders {
		_, err := o.DefineEmbedder(g, embedder)
		if err != nil {
			return err
		}
	}

	return nil
}

func (o *OpenAI) Model(g *genkit.Genkit, name string) ai.Model {
	return o.openAICompatible.Model(g, name, provider)
}

func (o *OpenAI) DefineModel(g *genkit.Genkit, name string, info ai.ModelInfo) (ai.Model, error) {
	return o.openAICompatible.DefineModel(g, name, info, provider)
}

func (o *OpenAI) DefineEmbedder(g *genkit.Genkit, name string) (ai.Embedder, error) {
	return o.openAICompatible.DefineEmbedder(g, name, provider)
}

func (o *OpenAI) Embedder(g *genkit.Genkit, name string) ai.Embedder {
	return o.openAICompatible.Embedder(g, name, provider)
}
