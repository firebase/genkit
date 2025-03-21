// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// Parts of this file are copied into vertexai, because the code is identical
// except for the import path of the Gemini SDK.
//go:generate go run ../../internal/cmd/copy -dest ../vertexai googleai.go

package googleai

import (
	"context"
	"errors"
	"fmt"
	"os"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/internal/gemini"

	"google.golang.org/genai"
)

const (
	provider    = "googleai"
	labelPrefix = "Google AI"
)

var (
	supportedModels = map[string]ai.ModelInfo{
		"gemini-1.5-flash": {
			Label: labelPrefix + " - " + "Gemini 1.5 Flash",
			Versions: []string{
				"gemini-1.5-flash-latest",
				"gemini-1.5-flash-001",
				"gemini-1.5-flash-002",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-1.5-pro": {
			Label: labelPrefix + " - " + "Gemini 1.5 Pro",
			Versions: []string{
				"gemini-1.5-pro-latest",
				"gemini-1.5-pro-001",
				"gemini-1.5-pro-002",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-1.5-flash-8b": {
			Label: labelPrefix + " - " + "Gemini 1.5 Flash 8B",
			Versions: []string{
				"gemini-1.5-flash-8b-latest",
				"gemini-1.5-flash-8b-001",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-2.0-flash": {
			Label: labelPrefix + " - " + "Gemini 2.0 Flash",
			Versions: []string{
				"gemini-2.0-flash-001",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-2.0-flash-lite": {
			Label: labelPrefix + " - " + "Gemini 2.0 Flash Lite",
			Versions: []string{
				"gemini-2.0-flash-lite-001",
			},
			Supports: &gemini.Multimodal,
		},
		"gemini-2.0-pro-exp-02-05": {
			Label:    labelPrefix + " - " + "Gemini 2.0 Pro Exp 02-05",
			Versions: []string{},
			Supports: &gemini.Multimodal,
		},
		"gemini-2.0-flash-thinking-exp-01-21": {
			Label:    labelPrefix + " - " + "Gemini 2.0 Flash Thinking Exp 01-21",
			Versions: []string{},
			Supports: &gemini.Multimodal,
		},
	}

	knownEmbedders = []string{
		"text-embedding-004",
		"embedding-001",
	}
)

// VertexAI is a Genkit plugin for interacting with the Google Vertex AI service.
type GoogleAI struct {
	APIKey string // API key to access the service. If empty, the values of the environment variables GOOGLE_GENAI_API_KEY or GOOGLE_API_KEY will be consulted, in that order.

	gclient *genai.Client // Client for the Google AI service.
	mu      sync.Mutex    // Mutex to control access.
	initted bool          // Whether the plugin has been initialized.
}

// Init initializes the plugin and all known models and embedders.
// After calling Init, you may call [DefineModel] and [DefineEmbedder] to create
// and register any additional generative models and embedders
func (ga *GoogleAI) Init(ctx context.Context, g *genkit.Genkit) (err error) {
	if ga == nil {
		ga = &GoogleAI{}
	}

	ga.mu.Lock()
	defer ga.mu.Unlock()

	if ga.initted {
		return errors.New("plugin already initialized")
	}
	defer func() {
		if err != nil {
			err = fmt.Errorf("googleai.Init: %w", err)
		}
	}()

	apiKey := ga.APIKey
	if apiKey == "" {
		apiKey = os.Getenv("GOOGLE_GENAI_API_KEY")
		if apiKey == "" {
			apiKey = os.Getenv("GOOGLE_API_KEY")
		}
		if apiKey == "" {
			return fmt.Errorf("Google AI requires setting GOOGLE_GENAI_API_KEY or GOOGLE_API_KEY in the environment. You can get an API key at https://ai.google.dev")
		}
	}

	client, err := genai.NewClient(ctx, &genai.ClientConfig{
		APIKey:  apiKey,
		Backend: genai.BackendGeminiAPI,
		HTTPOptions: genai.HTTPOptions{
			Headers: gemini.GenkitClientHeader,
		},
	})
	if err != nil {
		return err
	}

	ga.gclient = client
	ga.initted = true

	for model, details := range supportedModels {
		gemini.DefineModel(g, ga.gclient, model, details)
	}

	for _, e := range knownEmbedders {
		gemini.DefineEmbedder(g, ga.gclient, e)
	}

	return nil
}

// DefineModel defines an unknown model with the given name.
// The second argument describes the capability of the model.
// Use [IsDefinedModel] to determine if a model is already defined.
// After [Init] is called, only the known models are defined.
func (ga *GoogleAI) DefineModel(g *genkit.Genkit, name string, info *ai.ModelInfo) (ai.Model, error) {
	ga.mu.Lock()
	defer ga.mu.Unlock()
	if !ga.initted {
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
	return gemini.DefineModel(g, ga.gclient, name, mi), nil
}

// IsDefinedModel reports whether the named [Model] is defined by this plugin.
func IsDefinedModel(g *genkit.Genkit, name string) bool {
	return genkit.IsDefinedModel(g, provider, name)
}

// DefineEmbedder defines an embedder with a given name.
func (ga *GoogleAI) DefineEmbedder(g *genkit.Genkit, name string) ai.Embedder {
	ga.mu.Lock()
	defer ga.mu.Unlock()
	if !ga.initted {
		panic(provider + ".Init not called")
	}
	return gemini.DefineEmbedder(g, ga.gclient, name)
}

// IsDefinedEmbedder reports whether the named [Embedder] is defined by this plugin.
func IsDefinedEmbedder(g *genkit.Genkit, name string) bool {
	return genkit.LookupEmbedder(g, provider, name) != nil
}

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
