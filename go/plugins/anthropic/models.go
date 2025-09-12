// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package anthropic

import (
	"context"
	"fmt"
	"strings"

	"github.com/anthropics/anthropic-sdk-go"
	"github.com/anthropics/anthropic-sdk-go/option"
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core"
)

// getDefaultModelCapabilities returns default capabilities for Claude models
func getDefaultModelCapabilities() *ai.ModelSupports {
	return &ai.ModelSupports{
		Multiturn:   true,
		Tools:       true,
		ToolChoice:  true,
		SystemRole:  true,
		Media:       true, // Most Claude models support multimodal input
		Constrained: ai.ConstrainedSupportNoTools,
	}
}

// getFallbackModels returns a minimal set of fallback models if API discovery fails
func getFallbackModels() map[string]ai.ModelOptions {
	capabilities := getDefaultModelCapabilities()
	configSchema := core.InferSchemaMap(AnthropicUIConfig{})

	return map[string]ai.ModelOptions{
		"claude-3-haiku-20240307": {
			Label:        fmt.Sprintf("%s - %s", anthropicLabelPrefix, "Claude 3 Haiku"),
			Stage:        ai.ModelStageStable,
			Versions:     []string{},
			Supports:     capabilities,
			ConfigSchema: configSchema,
		},
		"claude-3-5-sonnet-20241022": {
			Label:        fmt.Sprintf("%s - %s", anthropicLabelPrefix, "Claude 3.5 Sonnet"),
			Stage:        ai.ModelStageStable,
			Versions:     []string{},
			Supports:     capabilities,
			ConfigSchema: configSchema,
		},
		"claude-3-5-haiku-20241022": {
			Label:        fmt.Sprintf("%s - %s", anthropicLabelPrefix, "Claude 3.5 Haiku"),
			Stage:        ai.ModelStageStable,
			Versions:     []string{},
			Supports:     capabilities,
			ConfigSchema: configSchema,
		},
	}
}

// listAnthropicModels fetches available models from the Anthropic API
func listAnthropicModels(ctx context.Context, client anthropic.Client, useBetaAPI bool, betaFeatures []string) (map[string]ai.ModelOptions, error) {
	models := make(map[string]ai.ModelOptions)

	// Try to use the Models service to list available models
	// Note: The Models API might not be available yet, so we'll fall back to fallback models
	modelService := client.Models

	// Prepare request options for Beta API if enabled
	var opts []option.RequestOption
	if useBetaAPI && len(betaFeatures) > 0 {
		betaHeader := strings.Join(betaFeatures, ",")
		opts = append(opts, option.WithHeader("anthropic-beta", betaHeader))
	}

	// List models with Beta API headers if configured
	page, err := modelService.List(ctx, anthropic.ModelListParams{}, opts...)
	if err != nil {
		// Models API might not be available yet, fall back to fallback list
		return getFallbackModels(), nil
	}

	// Process each model from the API response
	for _, modelInfo := range page.Data {
		modelName := modelInfo.ID
		displayName := modelInfo.DisplayName

		// Skip models that don't look like Claude models
		if !strings.Contains(strings.ToLower(modelName), "claude") {
			continue
		}

		// Use default capabilities for all Claude models
		capabilities := getDefaultModelCapabilities()

		// Create model options
		configSchema := core.InferSchemaMap(AnthropicUIConfig{})
		modelOpts := ai.ModelOptions{
			Label:        fmt.Sprintf("%s - %s", anthropicLabelPrefix, displayName),
			Stage:        ai.ModelStageStable,
			Versions:     []string{}, // Anthropic doesn't expose version info in the API
			Supports:     capabilities,
			ConfigSchema: configSchema,
		}

		models[modelName] = modelOpts
	}

	// If no models were found from API, fall back to fallback list
	if len(models) == 0 {
		return getFallbackModels(), nil
	}

	return models, nil
}
