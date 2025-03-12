// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package google

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"sync"

	"github.com/firebase/genkit/go/genkit"
	"github.com/firebase/genkit/go/internal"
	"google.golang.org/genai"
)

const (
	GoogleAIProvider = "googleai"
	VertexAIProvider = "vertexai"
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
}

func resolveBackend(cfg *Config) (genai.Backend, *Config, error) {
	backend := genai.BackendUnspecified
	var config Config

	// GoogleAI
	apiKey := cfg.APIKey
	if apiKey == "" {
		apiKey = os.Getenv("GOOGLE_GENAI_API_KEY")
		if apiKey == "" {
			apiKey = os.Getenv("GOOGLE_API_KEY")
		}
	}

	// make sure no VertexAI config is present
	projectId := os.Getenv("GOOGLE_CLOUD_PROJECT")
	location := os.Getenv("GOOGLE_CLOUD_LOCATION")
	if apiKey != "" && cfg.ProjectID != "" && projectId != "" {
		return backend, nil, fmt.Errorf("APIKey and ProjectID are mutually exclusive")
	}
	if apiKey != "" && cfg.Location != "" && location != "" {
		return backend, nil, fmt.Errorf("APIKey and Location are mutually exclusive")
	}
	if apiKey != "" {
		return genai.BackendGeminiAPI, &Config{APIKey: apiKey}, nil
	}

	// VertexAI
	if cfg.ProjectID == "" {
		if projectId == "" {
			return backend, nil, fmt.Errorf("ProjectID required for VertexAI, make sure to provide Config.ProjectID or set GOOGLE_CLOUD_PROJECT env var")
		}
		config.ProjectID = projectId
	}
	if cfg.Location == "" {
		if location == "" {
			return backend, nil, fmt.Errorf("Location required for VertexAI, make sure to provide config.Location or set GOOGLE_CLOUD_LOCATION env var")
		}
		config.Location = location
	}

	return genai.BackendVertexAI, &config, nil
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

	backend, c, err := resolveBackend(cfg)
	if err != nil {
		return err
	}

	xGoogleApiClientHeader := http.CanonicalHeaderKey("x-goog-api-client")
	gc := genai.ClientConfig{
		HTTPOptions: genai.HTTPOptions{
			Headers: http.Header{
				xGoogleApiClientHeader: {fmt.Sprintf("genkit-go/%s", internal.Version)},
			},
		},
	}
	gc.Backend = backend
	switch backend {
	case genai.BackendGeminiAPI:
		gc.APIKey = c.APIKey
	case genai.BackendVertexAI:
		gc.Project = c.ProjectID
		gc.Location = c.Location
	default:
		fmt.Errorf("unknown backend detected: %q", backend)
	}

	client, err := genai.NewClient(ctx, &gc)
	if err != nil {
		return err
	}
	state.gclient = client

	// TODO: define model and embedders
	return nil
}
