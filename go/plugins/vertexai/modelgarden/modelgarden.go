// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package modelgarden

import (
	"context"
	"fmt"
	"os"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

const (
	AnthropicProvider = "anthropic"
	MistralProvider   = "mistral"
)

// Config for Model Garden
type Config struct {
	ProjectID string
	Location  string
	Models    []string
}

var state struct {
	initted   bool
	clients   *ClientFactory // cache for all clients for available providers
	projectID string
	location  string
	mu        sync.Mutex
}

// Init initializes the ModelGarden plugin
// After calling Init, you may call [DefineModel] to create and register
// any additional generative models
func Init(ctx context.Context, g *genkit.Genkit, cfg *Config) error {
	if cfg == nil {
		cfg = &Config{}
	}

	state.mu.Lock()
	defer state.mu.Unlock()
	if state.initted {
		panic("modelgarden.Init already called")
	}

	state.projectID = cfg.ProjectID
	if state.projectID == "" {
		state.projectID = os.Getenv("GCLOUD_PROJECT")
	}
	if state.projectID == "" {
		state.projectID = os.Getenv("GOOGLE_CLOUD_PROJECT")
	}
	if state.projectID == "" {
		return fmt.Errorf("modelgarden.Init: Model Garden requires setting GCLOUD_PROJECT or GOOGLE_CLOUD_PROJECT in the environment")
	}

	state.location = cfg.Location
	if state.location == "" {
		state.location = "us-central1"
	}

	state.clients = NewClientFactory()
	state.initted = true
	for _, m := range cfg.Models {
		// ANTHROPIC
		if info, ok := AnthropicModels[m]; ok {
			state.clients.Register(AnthropicProvider, Anthropic)

			anthropicClient, err := state.clients.CreateClient(&ClientConfig{
				Provider: AnthropicProvider,
				Project:  state.projectID,
				Location: state.location,
			})
			if err != nil {
				return fmt.Errorf("unable to create client: %v", err)
			}

			anthropicClient.DefineModel(g, m, &info)
			continue
		}
	}

	return nil
}

func Model(g *genkit.Genkit, provider string, name string) ai.Model {
	return genkit.LookupModel(g, provider, name)
}
