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
	"fmt"
	"os"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/compat_oai"
	openaiGo "github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
)

const provider = "openai"

var (
	// Supported models: https://platform.openai.com/docs/models
	supportedModels = map[string]ai.ModelInfo{
		"gpt-4.1": {
			Label:    "OpenAI GPT-4.1",
			Supports: compat_oai.Multimodal.Supports,
			Versions: []string{"gpt-4.1", "gpt-4.1-2025-04-14"},
		},
		"gpt-4.1-mini": {
			Label:    "OpenAI GPT-4.1-mini",
			Supports: compat_oai.Multimodal.Supports,
			Versions: []string{"gpt-4.1-mini", "gpt-4.1-mini-2025-04-14"},
		},
		"gpt-4.1-nano": {
			Label:    "OpenAI GPT-4.1-nano",
			Supports: compat_oai.Multimodal.Supports,
			Versions: []string{"gpt-4.1-nano", "gpt-4.1-nano-2025-04-14"},
		},
		openaiGo.ChatModelO3Mini: {
			Label:    "OpenAI o3-mini",
			Supports: compat_oai.BasicText.Supports,
			Versions: []string{"o3-mini", "o3-mini-2025-01-31"},
		},
		openaiGo.ChatModelO1: {
			Label:    "OpenAI o1",
			Supports: compat_oai.BasicText.Supports,
			Versions: []string{"o1", "o1-2024-12-17"},
		},
		openaiGo.ChatModelO1Preview: {
			Label: "OpenAI o1-preview",
			Supports: &ai.ModelSupports{
				Multiturn:  true,
				Tools:      false,
				SystemRole: false,
				Media:      false,
			},
			Versions: []string{"o1-preview", "o1-preview-2024-09-12"},
		},
		openaiGo.ChatModelO1Mini: {
			Label: "OpenAI o1-mini",
			Supports: &ai.ModelSupports{
				Multiturn:  true,
				Tools:      false,
				SystemRole: false,
				Media:      false,
			},
			Versions: []string{"o1-mini", "o1-mini-2024-09-12"},
		},
		openaiGo.ChatModelGPT4_5Preview: {
			Label:    "OpenAI GPT-4.5-preview",
			Supports: compat_oai.Multimodal.Supports,
			Versions: []string{"gpt-4.5-preview", "gpt-4.5-preview-2025-02-27"},
		},
		openaiGo.ChatModelGPT4o: {
			Label:    "OpenAI GPT-4o",
			Supports: compat_oai.Multimodal.Supports,
			Versions: []string{"gpt-4o", "gpt-4o-2024-11-20", "gpt-4o-2024-08-06", "gpt-4o-2024-05-13"},
		},
		openaiGo.ChatModelGPT4oMini: {
			Label:    "OpenAI GPT-4o-mini",
			Supports: compat_oai.Multimodal.Supports,
			Versions: []string{"gpt-4o-mini", "gpt-4o-mini-2024-07-18"},
		},
		openaiGo.ChatModelGPT4Turbo: {
			Label:    "OpenAI GPT-4-turbo",
			Supports: compat_oai.Multimodal.Supports,
			Versions: []string{"gpt-4-turbo", "gpt-4-turbo-2024-04-09", "gpt-4-turbo-preview", "gpt-4-0125-preview"},
		},
		openaiGo.ChatModelGPT4: {
			Label: "OpenAI GPT-4",
			Supports: &ai.ModelSupports{
				Multiturn:  true,
				Tools:      false,
				SystemRole: true,
				Media:      false,
			},
			Versions: []string{"gpt-4", "gpt-4-0613", "gpt-4-0314"},
		},
		openaiGo.ChatModelGPT3_5Turbo: {
			Label: "OpenAI GPT-3.5-turbo",
			Supports: &ai.ModelSupports{
				Multiturn:  true,
				Tools:      false,
				SystemRole: true,
				Media:      false,
			},
			Versions: []string{"gpt-3.5-turbo", "gpt-3.5-turbo-0125", "gpt-3.5-turbo-1106", "gpt-3.5-turbo-instruct"},
		},
	}

	// Known embedders: https://platform.openai.com/docs/guides/embeddings
	knownEmbedders = []string{
		openaiGo.EmbeddingModelTextEmbedding3Small,
		openaiGo.EmbeddingModelTextEmbedding3Large,
		openaiGo.EmbeddingModelTextEmbeddingAda002,
	}
)

type OpenAI struct {
	// APIKey is the API key for the OpenAI API. If empty, the values of the environment variable "OPENAI_API_KEY" will be consulted.
	// Request a key at https://platform.openai.com/api-keys
	APIKey string
	// Optional: Opts are additional options for the OpenAI client.
	// Can include other options like WithOrganization, WithBaseURL, etc.
	Opts []option.RequestOption

	openAICompatible *compat_oai.OpenAICompatible
}

// Name implements genkit.Plugin.
func (o *OpenAI) Name() string {
	return provider
}

// Init implements genkit.Plugin.
func (o *OpenAI) Init(ctx context.Context, g *genkit.Genkit) error {
	apiKey := o.APIKey

	// if api key is not set, get it from environment variable
	if apiKey == "" {
		apiKey = os.Getenv("OPENAI_API_KEY")
	}

	if apiKey == "" {
		return fmt.Errorf("openai plugin initialization failed: apiKey is required")
	}

	if o.openAICompatible == nil {
		o.openAICompatible = &compat_oai.OpenAICompatible{}
	}

	// set the options
	o.openAICompatible.Opts = []option.RequestOption{
		option.WithAPIKey(apiKey),
	}
	if len(o.Opts) > 0 {
		o.openAICompatible.Opts = append(o.openAICompatible.Opts, o.Opts...)
	}

	if err := o.openAICompatible.Init(ctx, g); err != nil {
		return err
	}

	// define default models
	for model, info := range supportedModels {
		if _, err := o.DefineModel(g, model, info); err != nil {
			return err
		}
	}

	// define default embedders
	for _, embedder := range knownEmbedders {
		if _, err := o.DefineEmbedder(g, embedder); err != nil {
			return err
		}
	}

	return nil
}

func (o *OpenAI) Model(g *genkit.Genkit, name string) ai.Model {
	return o.openAICompatible.Model(g, name, provider)
}

func (o *OpenAI) DefineModel(g *genkit.Genkit, name string, info ai.ModelInfo) (ai.Model, error) {
	return o.openAICompatible.DefineModel(g, provider, name, info)
}

func (o *OpenAI) DefineEmbedder(g *genkit.Genkit, name string) (ai.Embedder, error) {
	return o.openAICompatible.DefineEmbedder(g, provider, name)
}

func (o *OpenAI) Embedder(g *genkit.Genkit, name string) ai.Embedder {
	return o.openAICompatible.Embedder(g, name, provider)
}
