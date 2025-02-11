// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package modelgarden

import (
	"context"
	"fmt"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

const (
	AnthropicProvider = "anthropic"
	MistralProvider   = "mistral"
)

type ModelGardenOptions struct {
	ProjectID string
	Region    string
	Models    []string
}

// A cache where all clients and its creators will be stored
var clients = NewClientFactory()

// Init initializes the ModelGarden plugin
// After calling Init, you may call [DefineModel] to create and register
// any additional generative models
func Init(ctx context.Context, g *genkit.Genkit, cfg *ModelGardenOptions) error {
	for _, m := range cfg.Models {
		// ANTHROPIC
		if info, ok := AnthropicModels[m]; ok {
			clients.Register(AnthropicProvider, Anthropic)

			anthropicClient, err := clients.CreateClient(&ClientConfig{
				Provider: AnthropicProvider,
				Project:  cfg.ProjectID,
				Region:   cfg.Region,
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
