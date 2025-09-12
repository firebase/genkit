// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package anthropic

import (
	"context"
	"errors"
	"fmt"
	"os"
	"sync"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
	"github.com/firebase/genkit/go/core/api"
	"github.com/firebase/genkit/go/genkit"

	"github.com/anthropics/anthropic-sdk-go"
)

const (
	anthropicProvider    = "anthropic"
	anthropicLabelPrefix = "Anthropic"
)

// Anthropic is a Genkit plugin for interacting with the Anthropic API service.
type Anthropic struct {
	APIKey       string   // API key to access the Anthropic API. If empty, the value of the environment variable ANTHROPIC_API_KEY will be consulted.
	UseBetaAPI   bool     // Whether to use the Anthropic Beta API by default. Can be overridden per-request.
	BetaFeatures []string // List of beta features to enable by default (e.g. "token-efficient-tools-2025-02-19")

	client  anthropic.Client // Client for the Anthropic API service.
	mu      sync.Mutex       // Mutex to control access.
	initted bool             // Whether the plugin has been initialized.
}

// Name returns the name of the plugin.
func (a *Anthropic) Name() string {
	return anthropicProvider
}

// Init initializes the Anthropic plugin and all known models.
// After calling Init, you may call [DefineModel] to create
// and register any additional generative models.
func (a *Anthropic) Init(ctx context.Context) []api.Action {
	if a == nil {
		a = &Anthropic{}
	}
	a.mu.Lock()
	defer a.mu.Unlock()
	if a.initted {
		panic("plugin already initialized")
	}

	apiKey := a.APIKey
	if apiKey == "" {
		apiKey = os.Getenv("ANTHROPIC_API_KEY")
		if apiKey == "" {
			panic("Anthropic requires setting ANTHROPIC_API_KEY in the environment. You can get an API key at https://console.anthropic.com/")
		}
	}

	// Set the API key as environment variable for the client
	os.Setenv("ANTHROPIC_API_KEY", apiKey)

	client := anthropic.NewClient()
	a.client = client
	a.initted = true

	var actions []api.Action

	// Use dynamic model discovery during initialization
	// Pass Beta API configuration to model discovery
	models, err := listAnthropicModels(ctx, a.client, a.UseBetaAPI, a.BetaFeatures)
	if err != nil {
		// If dynamic discovery fails, use fallback models
		models = getFallbackModels()
	}

	for name, modelOpts := range models {
		model := newModel(a.client, name, modelOpts)
		actions = append(actions, model.(api.Action))
	}

	return actions
}

// DefineModel defines an unknown model with the given name.
// The second argument describes the capability of the model.
// Use [IsDefinedModel] to determine if a model is already defined.
// After [Init] is called, only the known models are defined.
func (a *Anthropic) DefineModel(g *genkit.Genkit, name string, opts *ai.ModelOptions) (ai.Model, error) {
	a.mu.Lock()
	defer a.mu.Unlock()
	if !a.initted {
		return nil, errors.New("Anthropic plugin not initialized")
	}

	if opts == nil {
		// Use default capabilities for unknown models
		configSchema := core.InferSchemaMap(AnthropicUIConfig{})
		opts = &ai.ModelOptions{
			Label:        fmt.Sprintf("%s - %s", anthropicLabelPrefix, name),
			Stage:        ai.ModelStageStable,
			Versions:     []string{},
			Supports:     getDefaultModelCapabilities(),
			ConfigSchema: configSchema,
		}
	}

	return newModel(a.client, name, *opts), nil
}

// IsDefinedModel reports whether the named [Model] is defined by this plugin.
func (a *Anthropic) IsDefinedModel(g *genkit.Genkit, name string) bool {
	return genkit.LookupModel(g, api.NewName(anthropicProvider, name)) != nil
}

// AnthropicModelRef creates a new ModelRef for an Anthropic model with the given name and configuration.
func AnthropicModelRef(name string, config *ai.GenerationCommonConfig) ai.ModelRef {
	return ai.NewModelRef(anthropicProvider+"/"+name, config)
}

// AnthropicModel returns the [ai.Model] with the given name.
// It returns nil if the model was not defined.
func AnthropicModel(g *genkit.Genkit, name string) ai.Model {
	return genkit.LookupModel(g, api.NewName(anthropicProvider, name))
}

// ListActions returns a list of available actions for this plugin.
func (a *Anthropic) ListActions(ctx context.Context) []api.ActionDesc {
	actions := []api.ActionDesc{}

	// Try to fetch models dynamically from the API
	// Pass Beta API configuration to model discovery
	dynamicModels, err := listAnthropicModels(ctx, a.client, a.UseBetaAPI, a.BetaFeatures)
	if err != nil {
		// Fall back to fallback models if API call fails
		dynamicModels = getFallbackModels()
	}

	for name, opts := range dynamicModels {
		metadata := map[string]any{
			"model": map[string]any{
				"supports": map[string]any{
					"media":       opts.Supports.Media,
					"multiturn":   opts.Supports.Multiturn,
					"systemRole":  opts.Supports.SystemRole,
					"tools":       opts.Supports.Tools,
					"toolChoice":  opts.Supports.ToolChoice,
					"constrained": string(opts.Supports.Constrained),
				},
				"versions":      opts.Versions,
				"stage":         string(opts.Stage),
				"customOptions": opts.ConfigSchema,
			},
		}
		metadata["label"] = opts.Label

		actions = append(actions, api.ActionDesc{
			Type:     api.ActionTypeModel,
			Name:     api.NewName(anthropicProvider, name),
			Key:      api.NewKey(api.ActionTypeModel, anthropicProvider, name),
			Metadata: metadata,
		})
	}

	return actions
}

// ResolveAction resolves an action by type and name.
func (a *Anthropic) ResolveAction(atype api.ActionType, name string) api.Action {
	switch atype {
	case api.ActionTypeModel:
		capabilities := getDefaultModelCapabilities()
		configSchema := core.InferSchemaMap(AnthropicUIConfig{})
		return newModel(a.client, name, ai.ModelOptions{
			Label:        fmt.Sprintf("%s - %s", anthropicLabelPrefix, name),
			Stage:        ai.ModelStageStable,
			Versions:     []string{},
			Supports:     capabilities,
			ConfigSchema: configSchema,
		}).(api.Action)
	}
	return nil
}
