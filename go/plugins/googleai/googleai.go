// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// Parts of this file are copied into vertexai, because the code is identical
// except for the import path of the Gemini SDK.
//go:generate go run ../../internal/cmd/copy -dest ../vertexai googleai.go

package googleai

import (
	"context"
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

	// supported model names
	gemini15Flash                = "gemini-1.5-flash"
	gemini15Pro                  = "gemini-1.5-pro"
	gemini15Flash8b              = "gemini-1.5-flash-8b"
	gemini20Flash                = "gemini-2.0-flash"
	gemini20FlashLite            = "gemini-2.0-flash-lite"
	gemini20ProExp0205           = "gemini-2.0-pro-exp-02-05"
	gemini20FlashThinkingExp0121 = "gemini-2.0-flash-thinking-exp-01-21"
)

var state struct {
	gclient *genai.Client
	mu      sync.Mutex
	initted bool
}

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
		gemini15Flash8b: {
			Label: labelPrefix + " - " + gemini15Flash8b,
			Versions: []string{
				"gemini-1.5-flash-8b-latest",
				"gemini-1.5-flash-8b-001",
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
		"text-embedding-004",
		"embedding-001",
	}
)

// Config is the configuration for the plugin.
type Config struct {
	// The API key to access the service.
	// If empty, the values of the environment variables GOOGLE_GENAI_API_KEY
	// and GOOGLE_API_KEY will be consulted, in that order.
	APIKey string
}

// Init initializes the plugin and all known models and embedders.
// After calling Init, you may call [DefineModel] and [DefineEmbedder] to create
// and register any additional generative models and embedders
func Init(ctx context.Context, g *genkit.Genkit, cfg *Config) (err error) {
	if cfg == nil {
		cfg = &Config{}
	}
	state.mu.Lock()
	defer state.mu.Unlock()
	if state.initted {
		panic("googleai.Init already called")
	}
	defer func() {
		if err != nil {
			err = fmt.Errorf("googleai.Init: %w", err)
		}
	}()

	apiKey := cfg.APIKey
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
	})
	if err != nil {
		return err
	}

	state.gclient = client
	state.initted = true
	for model, details := range supportedModels {
		gemini.DefineModel(g, state.gclient, model, details)
	}
	for _, e := range knownEmbedders {
		gemini.DefineEmbedder(g, state.gclient, e)
	}
	return nil
}

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
	return gemini.DefineModel(g, state.gclient, name, mi), nil
}

// IsDefinedModel reports whether the named [Model] is defined by this plugin.
func IsDefinedModel(g *genkit.Genkit, name string) bool {
	return genkit.IsDefinedModel(g, provider, name)
}

// DefineEmbedder defines an embedder with a given name.
func DefineEmbedder(g *genkit.Genkit, name string) ai.Embedder {
	state.mu.Lock()
	defer state.mu.Unlock()
	if !state.initted {
		panic(provider + ".Init not called")
	}
	return gemini.DefineEmbedder(g, state.gclient, name)
}

// IsDefinedEmbedder reports whether the named [Embedder] is defined by this plugin.
func IsDefinedEmbedder(g *genkit.Genkit, name string) bool {
	return genkit.IsDefinedEmbedder(g, provider, name)
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
