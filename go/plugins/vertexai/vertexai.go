// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package vertexai

import (
	"context"
	"fmt"
	"os"
	"sync"

	aiplatform "cloud.google.com/go/aiplatform/apiv1"
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/internal/gemini"
	"google.golang.org/api/option"
	"google.golang.org/genai"
)

const (
	provider    = "vertexai"
	labelPrefix = "Vertex AI"

	// supported model names
	gemini15Flash                = "gemini-1.5-flash"
	gemini15Pro                  = "gemini-1.5-pro"
	gemini20Flash                = "gemini-2.0-flash"
	gemini20FlashLite            = "gemini-2.0-flash-lite"
	gemini20FlashLitePrev0205    = "gemini-2.0-flash-lite-preview-02-05"
	gemini20ProExp0205           = "gemini-2.0-pro-exp-02-05"
	gemini20FlashThinkingExp0121 = "gemini-2.0-flash-thinking-exp-01-21"
)

var (
	supportedModels = map[string]ai.ModelInfo{
		gemini15Flash: {
			Label: labelPrefix + " - " + gemini15Flash,
			Versions: []string{
				"gemini-1.5-flash-latest",
				"gemini-1.5-flash-001",
				"gemini-1.5-flash-002",
			},
			Supports: &gemini.Multimodal,
		},
		gemini15Pro: {
			Label: labelPrefix + " - " + gemini15Pro,
			Versions: []string{
				"gemini-1.5-pro-latest",
				"gemini-1.5-pro-001",
				"gemini-1.5-pro-002",
			},
			Supports: &gemini.Multimodal,
		},
		gemini20Flash: {
			Label: labelPrefix + " - " + gemini20Flash,
			Versions: []string{
				"gemini-2.0-flash-001",
			},
			Supports: &gemini.Multimodal,
		},
		gemini20FlashLite: {
			Label: labelPrefix + " - " + gemini20FlashLite,
			Versions: []string{
				"gemini-2.0-flash-lite-001",
			},
			Supports: &gemini.Multimodal,
		},
		gemini20FlashLitePrev0205: {
			Label:    labelPrefix + " - " + gemini20FlashLitePrev0205,
			Versions: []string{},
			Supports: &gemini.Multimodal,
		},
		gemini20ProExp0205: {
			Label:    labelPrefix + " - " + gemini20ProExp0205,
			Versions: []string{},
			Supports: &gemini.Multimodal,
		},
		gemini20FlashThinkingExp0121: {
			Label:    labelPrefix + " - " + gemini20FlashThinkingExp0121,
			Versions: []string{},
			Supports: &gemini.Multimodal,
		},
	}

	knownEmbedders = []string{
		"textembedding-gecko@003",
		"textembedding-gecko@002",
		"textembedding-gecko@001",
		"text-embedding-004",
		"textembedding-gecko-multilingual@001",
		"text-multilingual-embedding-002",
		"multimodalembedding",
	}
)

var state struct {
	mu        sync.Mutex
	initted   bool
	projectID string
	location  string
	gclient   *genai.Client
	pclient   *aiplatform.PredictionClient
}

// Config is the configuration for the plugin.
type Config struct {
	// The cloud project to use for Vertex AI.
	// If empty, the values of the environment variables GCLOUD_PROJECT
	// and GOOGLE_CLOUD_PROJECT will be consulted, in that order.
	ProjectID string
	// The location of the Vertex AI service. The default is "us-central1".
	Location string
	// Options to the Vertex AI client.
	ClientOptions []option.ClientOption
}

// Init initializes the plugin and all known models and embedders.
// After calling Init, you may call [DefineModel] and [DefineEmbedder] to create
// and register any additional generative models and embedders
func Init(ctx context.Context, g *genkit.Genkit, cfg *Config) error {
	if cfg == nil {
		cfg = &Config{}
	}
	state.mu.Lock()
	defer state.mu.Unlock()
	if state.initted {
		panic("vertexai.Init already called")
	}

	state.projectID = cfg.ProjectID
	if state.projectID == "" {
		state.projectID = os.Getenv("GCLOUD_PROJECT")
	}
	if state.projectID == "" {
		state.projectID = os.Getenv("GOOGLE_CLOUD_PROJECT")
	}
	if state.projectID == "" {
		return fmt.Errorf("vertexai.Init: Vertex AI requires setting GCLOUD_PROJECT or GOOGLE_CLOUD_PROJECT in the environment")
	}

	state.location = cfg.Location
	if state.location == "" {
		state.location = "us-central1"
	}
	var err error
	// Client for Gemini SDK.
	state.gclient, err = genai.NewClient(ctx, &genai.ClientConfig{
		Backend:  genai.BackendVertexAI,
		Project:  state.projectID,
		Location: state.location,
	})
	if err != nil {
		return err
	}

	state.initted = true
	for model, info := range supportedModels {
		defineModel(g, model, info)
	}
	for _, e := range knownEmbedders {
		defineEmbedder(g, e)
	}
	return nil
}

//copy:sink defineModel from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

// DefineModel defines an unknown model with the given name.
// The second argument describes the capability of the model.
// Use [IsDefinedModel] to determine if a model is already defined.
// After [Init] is called, only the known models are defined.
func DefineModel(g *genkit.Genkit, name string, info *ai.ModelInfo) (ai.Model, error) {
	state.mu.Lock()
	defer state.mu.Unlock()
	if !state.initted {
		panic(provider + ".Init not called")
	}
	var mi ai.ModelInfo
	if info == nil {
		var ok bool
		mi, ok = supportedModels[name]
		if !ok {
			return nil, fmt.Errorf("%s.DefineModel: called with unknown model %q and nil ModelInfo", provider, name)
		}
	} else {
		// TODO: unknown models could also specify versions?
		mi = *info
	}
	return defineModel(g, name, mi), nil
}

// requires state.mu
func defineModel(g *genkit.Genkit, name string, info ai.ModelInfo) ai.Model {
	meta := &ai.ModelInfo{
		Label:    labelPrefix + " - " + name,
		Supports: info.Supports,
		Versions: info.Versions,
	}
	return genkit.DefineModel(g, provider, name, meta, func(
		ctx context.Context,
		input *ai.ModelRequest,
		cb func(context.Context, *ai.ModelResponseChunk) error,
	) (*ai.ModelResponse, error) {
		return gemini.Generate(ctx, state.gclient, name, input, cb)
	})
}

// IsDefinedModel reports whether the named [Model] is defined by this plugin.
func IsDefinedModel(g *genkit.Genkit, name string) bool {
	return genkit.IsDefinedModel(g, provider, name)
}

// DO NOT MODIFY above ^^^^
//copy:endsink defineModel

//copy:sink defineEmbedder from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

// DefineEmbedder defines an embedder with a given name.
func DefineEmbedder(g *genkit.Genkit, name string) ai.Embedder {
	state.mu.Lock()
	defer state.mu.Unlock()
	if !state.initted {
		panic(provider + ".Init not called")
	}
	return defineEmbedder(g, name)
}

// IsDefinedEmbedder reports whether the named [Embedder] is defined by this plugin.
func IsDefinedEmbedder(g *genkit.Genkit, name string) bool {
	return genkit.IsDefinedEmbedder(g, provider, name)
}

// DO NOT MODIFY above ^^^^
//copy:endsink defineEmbedder

// requires state.mu
func defineEmbedder(g *genkit.Genkit, name string) ai.Embedder {
	fullName := fmt.Sprintf("projects/%s/locations/%s/publishers/google/models/%s", state.projectID, state.location, name)
	return genkit.DefineEmbedder(g, provider, name, func(ctx context.Context, req *ai.EmbedRequest) (*ai.EmbedResponse, error) {
		return embed(ctx, fullName, state.pclient, req)
	})
}

//copy:sink lookups from ../googleai/googleai.go
// DO NOT MODIFY below vvvv

// Model returns the [ai.Model] with the given name.
// It returns nil if the model was not defined.
func Model(g *genkit.Genkit, name string) ai.Model {
	return genkit.LookupModel(g, provider, name)
}

// Embedder returns the [ai.Embedder] with the given name.
// It returns nil if the embedder was not defined.
func Embedder(g *genkit.Genkit, name string) ai.Embedder {
	return genkit.LookupEmbedder(g, provider, name)
}

// DO NOT MODIFY above ^^^^
