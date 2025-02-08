// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package modelgarden

import (
	"context"
	"fmt"

	"github.com/firebase/genkit/go/genkit"
)

type ModelGardenOptions struct {
	ProjectID string
	Region    string
	Models    []string
}

// Init initializes the ModelGarden plugin
// After calling Init, you may call [DefineModel] to create and register
// any additional generative models
func Init(ctx context.Context, g *genkit.Genkit, cfg *ModelGardenOptions) error {
	clients := NewClientFactory()
	for _, m := range cfg.Models {
		// ANTHROPIC
		if info, ok := AnthropicModels[m]; ok {
			anthropicClient, err := clients.CreateClient(&ClientConfig{
				Provider: "anthropic",
				Project:  "anthropic-project",
				Region:   "us-west-1",
			})
			if err != nil {
				return fmt.Errorf("unable to create client: %v", err)
			}

			anthropicClient.DefineModel(m, &info)
			continue
		}
	}

	return nil
}
