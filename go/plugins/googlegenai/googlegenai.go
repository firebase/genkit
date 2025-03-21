// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package googlegenai

import (
	"context"
	"fmt"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/plugins/internal/gemini"
	"google.golang.org/genai"
)

const (
	googleAIProvider = "googleai"
	vertexAIProvider = "vertexai"

	googleAILabelPrefix = "Google AI"
	vertexAILabelPrefix = "Vertex AI"
)

var state struct {
	gclient *genai.Client
	mu      sync.Mutex
	initted bool
}

type GoogleAIConfig struct {
	// API Key for Google AI
	// If empty, GOOGLE_API_KEY environment variable will be consulted
	APIKey string
}

type VertexAIConfig struct {
	// GCP Project ID for Vertex AI
	ProjectID string
	// GCP Location/Region for Vertex AI
	// If empty, GOOGLE_CLOUD_LOCATION and GOOGLE_CLOUD_REGION environment variables
	// will be consulted in that order
	Location string
}

// InitGoogleAI initializes the plugin and all known models and embedders.
// After calling InitGoogleAI, you may call [DefineModel] and [DefineEmbedder] to create
// and register any additional generative models and embedders
func InitGoogleAI(ctx context.Context, g *genkit.Genkit, cfg *GoogleAIConfig) (err error) {
	if cfg == nil {
		cfg = &GoogleAIConfig{}
	}
	state.mu.Lock()
	defer state.mu.Unlock()
	if state.initted {
		panic("googlegenai.InitGoogleAI already called")
	}
	defer func() {
		if err != nil {
			err = fmt.Errorf("googlegenai.InitGoogleAI: %w", err)
		}
	}()

	gc := genai.ClientConfig{
		Backend: genai.BackendGeminiAPI,
		HTTPOptions: genai.HTTPOptions{
			Headers: gemini.GenkitClientHeader,
		},
	}

	client, err := genai.NewClient(ctx, &gc)
	if err != nil {
		return err
	}
	state.gclient = client

	models, err := listModels(gc.Backend)
	if err != nil {
		return err
	}
	for k, v := range models {
		gemini.DefineModel(g, state.gclient, k, *v)
	}

	embedders, err := listEmbedders(gc.Backend)
	if err != nil {
		return err
	}
	for _, e := range embedders {
		gemini.DefineEmbedder(g, state.gclient, e)
	}

	return nil
}

// InitVertexAI initializes the plugin and all known models and embedders.
// After calling InitVertexAI, you may call [DefineModel] and [DefineEmbedder] to create
// and register any additional generative models and embedders
func InitVertexAI(ctx context.Context, g *genkit.Genkit, cfg *VertexAIConfig) (err error) {
	if cfg == nil {
		cfg = &VertexAIConfig{}
	}
	state.mu.Lock()
	defer state.mu.Unlock()
	if state.initted {
		panic("googlegenai.InitVertexAI already called")
	}
	defer func() {
		if err != nil {
			err = fmt.Errorf("googlegenai.InitVertexAI: %w", err)
		}
	}()

	gc := genai.ClientConfig{
		Backend:  genai.BackendVertexAI,
		Project:  cfg.ProjectID,
		Location: cfg.Location,
		HTTPOptions: genai.HTTPOptions{
			Headers: gemini.GenkitClientHeader,
		},
	}

	client, err := genai.NewClient(ctx, &gc)
	if err != nil {
		return err
	}
	state.gclient = client

	models, err := listModels(gc.Backend)
	if err != nil {
		return err
	}
	for k, v := range models {
		gemini.DefineModel(g, state.gclient, k, *v)
	}

	embedders, err := listEmbedders(gc.Backend)
	if err != nil {
		return err
	}
	for _, e := range embedders {
		gemini.DefineEmbedder(g, state.gclient, e)
	}

	return nil
}

// Model returns the [ai.Model] with the given name.
// It returns nil if the model was not defined.
func Model(g *genkit.Genkit, name string) ai.Model {
	provider := provider()
	return genkit.LookupModel(g, provider, name)
}

// Embedder returns the [ai.Embedder] with the given name.
// It returns nil if the embedder was not defined.
func Embedder(g *genkit.Genkit, name string) ai.Embedder {
	provider := provider()
	return genkit.LookupEmbedder(g, provider, name)
}

// DefineModel defines an unknown model with the given name.
// The second argument describes the capability of the model.
// Use [IsDefinedModel] to determine if a model is already defined.
// After [Init] is called, only the known models are defined.
func DefineModel(g *genkit.Genkit, name string, info *ai.ModelInfo) (ai.Model, error) {
	state.mu.Lock()
	defer state.mu.Unlock()
	provider := provider()
	if !state.initted {
		panic(provider + ".Init not called")
	}

	models, err := listModels(state.gclient.ClientConfig().Backend)
	if err != nil {
		return nil, err
	}

	var mi *ai.ModelInfo
	if info == nil {
		var ok bool
		mi, ok = models[name]
		if !ok {
			return nil, fmt.Errorf("%s.DefineModel: called with unknown model %q and nil ModelInfo", provider, name)
		}
	} else {
		// TODO: unknown models could also specify versions?
		mi = info
	}
	return gemini.DefineModel(g, state.gclient, name, *mi), nil
}

// IsDefinedModel reports whether the named [Model] is defined by this plugin.
func IsDefinedModel(g *genkit.Genkit, name string) bool {
	provider := provider()
	return genkit.IsDefinedModel(g, provider, name)
}

// DefineEmbedder defines an embedder with a given name.
func DefineEmbedder(g *genkit.Genkit, name string) ai.Embedder {
	provider := provider()
	state.mu.Lock()
	defer state.mu.Unlock()
	if !state.initted {
		panic(provider + ".Init not called")
	}
	return gemini.DefineEmbedder(g, state.gclient, name)
}

// IsDefinedEmbedder reports whether the named [Embedder] is defined by this plugin.
func IsDefinedEmbedder(g *genkit.Genkit, name string) bool {
	provider := provider()
	return genkit.IsDefinedEmbedder(g, provider, name)
}

// provider checks the backend used in the Genai SDK and returns the
// appropriate provider name
func provider() string {
	switch state.gclient.ClientConfig().Backend {
	case genai.BackendGeminiAPI:
		return googleAIProvider
	case genai.BackendVertexAI:
		return vertexAIProvider
	default:
		return ""
	}
}
