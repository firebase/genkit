// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package google

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

type Config struct {
	// API Key for GoogleAI
	// If empty, the values of the environment variables GOOGLE_GENAI_API_KEY
	// and GOOGLE_API_KEY will be consulted, in that order.
	APIKey string
	// GCP Project ID for VertexAI
	ProjectID string
	// GCP Location/Region for VertexAI
	Location string
	// Toggle to use VertexAI instead of GoogleAI plugin
	VertexAI bool
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
		panic("google.Init already called")
	}
	defer func() {
		if err != nil {
			err = fmt.Errorf("google.Init: %w", err)
		}
	}()

	gc := genai.ClientConfig{
		Backend: genai.BackendGeminiAPI,
		HTTPOptions: genai.HTTPOptions{
			Headers: gemini.GenkitClientHeader,
		},
	}

	if cfg.VertexAI || cfg.Location != "" || cfg.ProjectID != "" {
		gc.Backend = genai.BackendVertexAI
	}

	switch gc.Backend {
	case genai.BackendGeminiAPI:
		gc.APIKey = cfg.APIKey
	case genai.BackendVertexAI:
		gc.Project = cfg.ProjectID
		gc.Location = cfg.Location
	default:
		fmt.Errorf("unknown backend detected: %q", gc.Backend)
	}

	client, err := genai.NewClient(ctx, &gc)
	if err != nil {
		return err
	}
	state.gclient = client

	models, err := getSupportedModels(gc.Backend)
	if err != nil {
		return err
	}
	for k, v := range models {
		gemini.DefineModel(g, state.gclient, k, *v)
	}

	embedders, err := getSupportedEmbedders(gc.Backend)
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
	provider := googleAIProvider
	if state.gclient.ClientConfig().Backend == genai.BackendVertexAI {
		provider = vertexAIProvider
	}
	return genkit.LookupModel(g, provider, name)
}

// Embedder returns the [ai.Embedder] with the given name.
// It returns nil if the embedder was not defined.
func Embedder(g *genkit.Genkit, name string) ai.Embedder {
	provider := googleAIProvider
	if state.gclient.ClientConfig().Backend == genai.BackendVertexAI {
		provider = vertexAIProvider
	}
	return genkit.LookupEmbedder(g, provider, name)
}
