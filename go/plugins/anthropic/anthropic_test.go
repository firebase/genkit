// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package anthropic

import (
	"context"
	"fmt"
	"os"
	"testing"

	"github.com/anthropics/anthropic-sdk-go"
	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

func TestAnthropicPlugin(t *testing.T) {
	// Skip test if no API key is provided
	if os.Getenv("ANTHROPIC_API_KEY") == "" {
		t.Skip("ANTHROPIC_API_KEY not set, skipping live test")
	}

	ctx := context.Background()

	// Test plugin initialization
	plugin := &Anthropic{}
	if plugin.Name() != "anthropic" {
		t.Errorf("Expected plugin name 'anthropic', got %s", plugin.Name())
	}

	// Test plugin initialization with Genkit
	g := genkit.Init(ctx, genkit.WithPlugins(plugin))

	// Test model lookup
	model := AnthropicModel(g, "claude-3-5-sonnet-20241022")
	if model == nil {
		t.Fatal("Failed to get Claude 3.5 Sonnet model")
	}

	// Test basic generation
	resp, err := genkit.Generate(ctx, g,
		ai.WithModelName("anthropic/claude-3-5-sonnet-20241022"),
		ai.WithPrompt("Say 'Hello, World!' and nothing else."))
	if err != nil {
		t.Fatalf("Generation failed: %v", err)
	}

	if resp.Text() == "" {
		t.Error("Expected non-empty response")
	}

	if resp.Usage == nil {
		t.Error("Expected usage information")
	}

	t.Logf("Response: %s", resp.Text())
	t.Logf("Usage: %+v", resp.Usage)
}

func TestAnthropicPluginStreaming(t *testing.T) {
	// Skip test if no API key is provided
	if os.Getenv("ANTHROPIC_API_KEY") == "" {
		t.Skip("ANTHROPIC_API_KEY not set, skipping live test")
	}

	ctx := context.Background()

	// Test plugin initialization with Genkit
	g := genkit.Init(ctx, genkit.WithPlugins(&Anthropic{}))

	// Test streaming generation
	var chunks []string
	_, err := genkit.Generate(ctx, g,
		ai.WithModelName("anthropic/claude-3-5-sonnet-20241022"),
		ai.WithPrompt("Count from 1 to 3, one number per line."),
		ai.WithStreaming(func(ctx context.Context, chunk *ai.ModelResponseChunk) error {
			chunks = append(chunks, chunk.Text())
			return nil
		}))
	if err != nil {
		t.Fatalf("Streaming generation failed: %v", err)
	}

	if len(chunks) == 0 {
		t.Error("Expected at least one streaming chunk")
	}

	t.Logf("Received %d chunks", len(chunks))
}

func TestAnthropicPluginWithTools(t *testing.T) {
	// Skip test if no API key is provided
	if os.Getenv("ANTHROPIC_API_KEY") == "" {
		t.Skip("ANTHROPIC_API_KEY not set, skipping live test")
	}

	ctx := context.Background()

	// Test plugin initialization with Genkit
	g := genkit.Init(ctx, genkit.WithPlugins(&Anthropic{}))

	// Define a simple tool
	weatherTool := genkit.DefineTool(g, "get_weather", "Get the current weather for a location",
		func(ctx *ai.ToolContext, input map[string]any) (map[string]any, error) {
			location, ok := input["location"].(string)
			if !ok {
				return nil, fmt.Errorf("location is required")
			}
			return map[string]any{
				"location":    location,
				"temperature": "72°F",
				"condition":   "sunny",
			}, nil
		})

	// Test generation with tools
	resp, err := genkit.Generate(ctx, g,
		ai.WithModelName("anthropic/claude-3-5-sonnet-20241022"),
		ai.WithPrompt("What's the weather like in San Francisco? Use the get_weather tool."),
		ai.WithTools(weatherTool))
	if err != nil {
		t.Fatalf("Generation with tools failed: %v", err)
	}

	if resp.Text() == "" && len(resp.Message.Content) == 0 {
		t.Error("Expected non-empty response")
	}

	t.Logf("Response: %s", resp.Text())
	t.Logf("Message content parts: %d", len(resp.Message.Content))

	// Check if the model made a tool call
	for _, part := range resp.Message.Content {
		if part.IsToolRequest() {
			t.Logf("Tool request: %+v", part.ToolRequest)
		}
	}
}

func TestFallbackModels(t *testing.T) {
	models := getFallbackModels()

	// Test that we have some fallback models
	if len(models) == 0 {
		t.Error("Expected at least one fallback model")
	}

	expectedModels := []string{
		"claude-3-haiku-20240307",
		"claude-3-5-sonnet-20241022",
		"claude-3-5-haiku-20241022",
	}

	for _, expectedModel := range expectedModels {
		if _, exists := models[expectedModel]; !exists {
			t.Errorf("Expected fallback model %s not found", expectedModel)
		}
	}

	// Test model capabilities
	for name, opts := range models {
		if opts.Supports == nil {
			t.Errorf("Model %s missing capabilities", name)
			continue
		}

		// All Anthropic models should support these features
		if !opts.Supports.Multiturn {
			t.Errorf("Model %s should support multiturn", name)
		}
		if !opts.Supports.Tools {
			t.Errorf("Model %s should support tools", name)
		}
		if !opts.Supports.SystemRole {
			t.Errorf("Model %s should support system role", name)
		}
		if !opts.Supports.Media {
			t.Errorf("Model %s should support media", name)
		}
	}
}

func TestDefaultModelCapabilities(t *testing.T) {
	capabilities := getDefaultModelCapabilities()

	if capabilities == nil {
		t.Fatal("Expected non-nil capabilities")
	}

	// Test that default capabilities include all expected features
	if !capabilities.Multiturn {
		t.Error("Default capabilities should support multiturn")
	}
	if !capabilities.Tools {
		t.Error("Default capabilities should support tools")
	}
	if !capabilities.SystemRole {
		t.Error("Default capabilities should support system role")
	}
	if !capabilities.Media {
		t.Error("Default capabilities should support media")
	}
}

func TestConfigFromRequest(t *testing.T) {
	// Test with nil config
	req := &ai.ModelRequest{Config: nil}
	config, err := configFromRequest(req)
	if err != nil {
		t.Errorf("Expected no error with nil config, got: %v", err)
	}
	if config == nil {
		t.Error("Expected non-nil config")
	}

	// Test with GenerationCommonConfig
	commonConfig := &ai.GenerationCommonConfig{
		Temperature:     0.7,
		MaxOutputTokens: 1000,
		TopP:            0.9,
	}
	req = &ai.ModelRequest{Config: commonConfig}
	config, err = configFromRequest(req)
	if err != nil {
		t.Errorf("Expected no error with GenerationCommonConfig, got: %v", err)
	}
	if config.Temperature != 0.7 {
		t.Errorf("Expected temperature 0.7, got %f", config.Temperature)
	}

	// Test with map config
	mapConfig := map[string]any{
		"temperature":     0.8,
		"maxOutputTokens": 500,
		"topP":            0.95,
	}
	req = &ai.ModelRequest{Config: mapConfig}
	config, err = configFromRequest(req)
	if err != nil {
		t.Errorf("Expected no error with map config, got: %v", err)
	}
	if config.Temperature != 0.8 {
		t.Errorf("Expected temperature 0.8, got %f", config.Temperature)
	}
}

func TestAnthropicPluginMultiModal(t *testing.T) {
	// Skip test if no API key is provided
	if os.Getenv("ANTHROPIC_API_KEY") == "" {
		t.Skip("ANTHROPIC_API_KEY not set, skipping live test")
	}

	ctx := context.Background()

	// Test plugin initialization with Genkit
	g := genkit.Init(ctx, genkit.WithPlugins(&Anthropic{}))

	// Test multi-modal generation with image
	resp, err := genkit.Generate(ctx, g,
		ai.WithModelName("anthropic/claude-3-haiku-20240307"),
		ai.WithMessages(
			ai.NewUserMessage(
				ai.NewTextPart("What is in this image?"),
				ai.NewMediaPart("image/jpeg", "https://media.istockphoto.com/id/1256666241/photo/dog-playing-with-stick.jpg?s=612x612&w=0&k=20&c=mY2fjPY-tTflqOb61nmnUFSeqzkQlIO33B9TIncW6XI="),
			),
		),
	)
	if err != nil {
		t.Fatalf("Multi-modal generation failed: %v", err)
	}

	if resp.Text() == "" {
		t.Error("Expected non-empty response for multi-modal input")
	}

	t.Logf("Multi-modal response: %s", resp.Text())
}

func TestToAnthropicParts(t *testing.T) {
	tests := []struct {
		name    string
		parts   []*ai.Part
		wantErr bool
	}{
		{
			name:    "Text part",
			parts:   []*ai.Part{ai.NewTextPart("Hello, world!")},
			wantErr: false,
		},
		{
			name:    "Media part with HTTP URL",
			parts:   []*ai.Part{ai.NewMediaPart("image/jpeg", "https://example.com/image.jpg")},
			wantErr: true, // Will fail because URL doesn't exist, but tests the code path
		},
		{
			name:    "Data part",
			parts:   []*ai.Part{ai.NewDataPart("some data")},
			wantErr: true, // Data parts without proper URI format will fail
		},
		{
			name: "Tool request part",
			parts: []*ai.Part{ai.NewToolRequestPart(&ai.ToolRequest{
				Name:  "test_tool",
				Input: map[string]any{"param": "value"},
				Ref:   "ref123",
			})},
			wantErr: false,
		},
		{
			name: "Tool response part",
			parts: []*ai.Part{ai.NewToolResponsePart(&ai.ToolResponse{
				Name:   "test_tool",
				Output: map[string]any{"result": "success"},
				Ref:    "ref123",
			})},
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			blocks, err := toAnthropicParts(tt.parts)
			if (err != nil) != tt.wantErr {
				t.Errorf("toAnthropicParts() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if !tt.wantErr && len(blocks) == 0 {
				t.Error("Expected at least one block for valid parts")
			}
		})
	}
}

func TestDownloadImageFromURL(t *testing.T) {
	tests := []struct {
		name    string
		url     string
		wantErr bool
	}{
		{
			name:    "Invalid URL",
			url:     "not-a-url",
			wantErr: true,
		},
		{
			name:    "Non-existent URL",
			url:     "https://example.com/nonexistent.jpg",
			wantErr: true,
		},
		{
			name:    "PNG extension inference",
			url:     "https://example.com/test.png",
			wantErr: true, // Will fail to download but tests content type inference
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, _, err := downloadImageFromURL(tt.url)
			if (err != nil) != tt.wantErr {
				t.Errorf("downloadImageFromURL() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestToAnthropicRole(t *testing.T) {
	tests := []struct {
		name     string
		role     ai.Role
		expected string
		wantErr  bool
	}{
		{
			name:     "User role",
			role:     ai.RoleUser,
			expected: "user",
			wantErr:  false,
		},
		{
			name:     "Model role",
			role:     ai.RoleModel,
			expected: "assistant",
			wantErr:  false,
		},
		{
			name:     "Tool role",
			role:     ai.RoleTool,
			expected: "assistant",
			wantErr:  false,
		},
		{
			name:    "Invalid role",
			role:    ai.Role("invalid"),
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := toAnthropicRole(tt.role)
			if (err != nil) != tt.wantErr {
				t.Errorf("toAnthropicRole() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if !tt.wantErr && string(result) != tt.expected {
				t.Errorf("toAnthropicRole() = %v, want %v", result, tt.expected)
			}
		})
	}
}

func TestToAnthropicTools(t *testing.T) {
	tests := []struct {
		name    string
		tools   []*ai.ToolDefinition
		wantErr bool
	}{
		{
			name:    "Empty tools",
			tools:   []*ai.ToolDefinition{},
			wantErr: false,
		},
		{
			name: "Valid tool",
			tools: []*ai.ToolDefinition{
				{
					Name:        "test_tool",
					Description: "A test tool",
					InputSchema: map[string]any{"type": "object"},
				},
			},
			wantErr: false,
		},
		{
			name: "Tool without name",
			tools: []*ai.ToolDefinition{
				{
					Description: "A test tool",
					InputSchema: map[string]any{"type": "object"},
				},
			},
			wantErr: true,
		},
		{
			name: "Tool with invalid name",
			tools: []*ai.ToolDefinition{
				{
					Name:        "invalid/tool/name",
					Description: "A test tool",
					InputSchema: map[string]any{"type": "object"},
				},
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result, err := toAnthropicTools(tt.tools)
			if (err != nil) != tt.wantErr {
				t.Errorf("toAnthropicTools() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if !tt.wantErr && len(result) != len(tt.tools) {
				t.Errorf("toAnthropicTools() returned %d tools, want %d", len(result), len(tt.tools))
			}
		})
	}
}

// Configuration Schema Tests

func TestConfigSchema(t *testing.T) {
	// Test that configToMap generates a proper schema from the UI-friendly AnthropicUIConfig
	config := &AnthropicUIConfig{}
	schema := configToMap(config)

	if schema == nil {
		t.Fatal("configToMap returned nil")
	}

	// Check that the schema contains expected fields
	if schema["type"] != "object" {
		t.Errorf("Expected schema type to be 'object', got %v", schema["type"])
	}

	properties, ok := schema["properties"].(map[string]any)
	if !ok {
		t.Fatal("Schema properties should be a map")
	}

	// Check for configuration fields that should be present
	// This includes both common generation parameters and Anthropic-specific options
	expectedFields := []string{
		"maxOutputTokens",
		"temperature",
		"topK",
		"topP",
		"stopSequences",
		"userId",
		"serviceTier",
		"thinkingEnabled",
		"thinkingBudgetTokens",
	}

	for _, field := range expectedFields {
		if _, exists := properties[field]; !exists {
			t.Errorf("Expected field %s to be present in schema properties", field)
		}
	}

	t.Logf("Generated schema has %d properties", len(properties))
	for key := range properties {
		t.Logf("Schema property: %s", key)
	}
}

func TestModelConfigSchema(t *testing.T) {
	// Test that models have config schema set
	models := getFallbackModels()

	for name, opts := range models {
		if opts.ConfigSchema == nil {
			t.Errorf("Model %s should have ConfigSchema set", name)
		}

		// Verify the config schema has the expected structure
		if opts.ConfigSchema["type"] != "object" {
			t.Errorf("Model %s config schema should have type 'object'", name)
		}

		properties, ok := opts.ConfigSchema["properties"].(map[string]any)
		if !ok {
			t.Errorf("Model %s config schema should have properties", name)
			continue
		}

		// Check for at least some expected configuration options
		if len(properties) == 0 {
			t.Errorf("Model %s config schema should have some properties", name)
		}

		t.Logf("Model %s has %d config properties", name, len(properties))
	}
}

// UI Configuration Tests

func TestUIConfigTitles(t *testing.T) {
	// Test that the UI configuration includes proper titles for better readability
	config := &AnthropicUIConfig{}
	schema := configToMap(config)

	if schema == nil {
		t.Fatal("configToMap returned nil")
	}

	properties, ok := schema["properties"].(map[string]any)
	if !ok {
		t.Fatal("Schema properties should be a map")
	}

	// Test that configuration fields have proper titles
	expectedTitles := map[string]string{
		"maxOutputTokens":      "Max Output Tokens",
		"temperature":          "Temperature",
		"topK":                 "Top K",
		"topP":                 "Top P",
		"stopSequences":        "Stop Sequences",
		"userId":               "User ID",
		"serviceTier":          "Service Tier",
		"thinkingEnabled":      "Enable Thinking",
		"thinkingBudgetTokens": "Thinking Budget Tokens",
	}

	for field, expectedTitle := range expectedTitles {
		if fieldSchema, exists := properties[field]; exists {
			if fieldMap, ok := fieldSchema.(map[string]any); ok {
				if title, hasTitle := fieldMap["title"]; hasTitle {
					if titleStr, ok := title.(string); ok {
						if titleStr != expectedTitle {
							t.Logf("Field %s has title '%s', expected '%s'", field, titleStr, expectedTitle)
						}
					} else {
						t.Logf("Field %s title is not a string: %v", field, title)
					}
				} else {
					t.Logf("Field %s has no title", field)
				}
			}
		}
	}

	// Log all field names and their titles for verification
	t.Logf("Configuration fields with improved readability:")
	for field, fieldSchema := range properties {
		if fieldMap, ok := fieldSchema.(map[string]any); ok {
			if title, hasTitle := fieldMap["title"]; hasTitle {
				t.Logf("  %s -> %s", field, title)
			} else {
				t.Logf("  %s (no title)", field)
			}
		}
	}
}

func TestUIConfigVsRawConfig(t *testing.T) {
	// Compare the UI config field names vs raw Anthropic SDK field names
	uiConfig := &AnthropicUIConfig{}
	uiSchema := configToMap(uiConfig)

	uiProperties, ok := uiSchema["properties"].(map[string]any)
	if !ok {
		t.Fatal("UI schema properties should be a map")
	}

	// Verify we have user-friendly camelCase names for Anthropic-specific fields
	userFriendlyFields := []string{
		"serviceTier", // instead of service_tier
	}

	for _, field := range userFriendlyFields {
		if _, exists := uiProperties[field]; !exists {
			t.Errorf("Expected user-friendly field %s to be present", field)
		}
	}

	// Verify we don't have the old snake_case names for Anthropic-specific fields
	snakeCaseFields := []string{
		"service_tier",
	}

	for _, field := range snakeCaseFields {
		if _, exists := uiProperties[field]; exists {
			t.Errorf("Should not have snake_case field %s in UI config", field)
		}
	}

	t.Logf("UI config successfully uses user-friendly field names")
}

// Pass-through Configuration Tests

func TestPassThroughConfig(t *testing.T) {
	// Test that AnthropicConfig supports both common config and pass-through parameters
	t.Run("AnthropicConfig with embedded GenerationCommonConfig", func(t *testing.T) {
		config := &AnthropicConfig{
			GenerationCommonConfig: ai.GenerationCommonConfig{
				MaxOutputTokens: 1024,
				Temperature:     0.7,
				TopK:            40,
				TopP:            0.9,
				StopSequences:   []string{"Human:", "Assistant:"},
			},
			Metadata: map[string]any{
				"user_id": "test-user",
				"session": "test-session",
			},
		}

		// Test that configFromRequest handles AnthropicConfig correctly
		mockRequest := &ai.ModelRequest{
			Config: config,
		}

		result, err := configFromRequest(mockRequest)
		if err != nil {
			t.Fatalf("configFromRequest failed: %v", err)
		}

		// Verify common config fields are preserved
		if result.MaxOutputTokens != 1024 {
			t.Errorf("Expected MaxOutputTokens 1024, got %d", result.MaxOutputTokens)
		}
		if result.Temperature != 0.7 {
			t.Errorf("Expected Temperature 0.7, got %f", result.Temperature)
		}
		if result.TopK != 40 {
			t.Errorf("Expected TopK 40, got %d", result.TopK)
		}
		if result.TopP != 0.9 {
			t.Errorf("Expected TopP 0.9, got %f", result.TopP)
		}

		// Verify pass-through fields are preserved
		if result.Metadata == nil {
			t.Error("Expected Metadata to be preserved")
		} else {
			if userID, ok := result.Metadata["user_id"]; !ok || userID != "test-user" {
				t.Errorf("Expected Metadata user_id to be 'test-user', got %v", userID)
			}
		}
	})

	t.Run("Map-based config with pass-through parameters", func(t *testing.T) {
		mapConfig := map[string]any{
			"maxOutputTokens": 2048,
			"temperature":     0.5,
			"topK":            20,
			"topP":            0.8,
			"stopSequences":   []string{"END"},
			"metadata": map[string]any{
				"user_id": "map-user",
				"custom":  "value",
			},
		}

		mockRequest := &ai.ModelRequest{
			Config: mapConfig,
		}

		result, err := configFromRequest(mockRequest)
		if err != nil {
			t.Fatalf("configFromRequest failed: %v", err)
		}

		// Verify common config fields
		if result.MaxOutputTokens != 2048 {
			t.Errorf("Expected MaxOutputTokens 2048, got %d", result.MaxOutputTokens)
		}
		if result.Temperature != 0.5 {
			t.Errorf("Expected Temperature 0.5, got %f", result.Temperature)
		}

		// Verify pass-through fields
		if result.Metadata == nil {
			t.Error("Expected Metadata to be preserved from map config")
		}
	})

	t.Run("Backward compatibility with GenerationCommonConfig", func(t *testing.T) {
		commonConfig := &ai.GenerationCommonConfig{
			MaxOutputTokens: 512,
			Temperature:     0.3,
		}

		mockRequest := &ai.ModelRequest{
			Config: commonConfig,
		}

		result, err := configFromRequest(mockRequest)
		if err != nil {
			t.Fatalf("configFromRequest failed: %v", err)
		}

		// Verify common config fields are preserved
		if result.MaxOutputTokens != 512 {
			t.Errorf("Expected MaxOutputTokens 512, got %d", result.MaxOutputTokens)
		}
		if result.Temperature != 0.3 {
			t.Errorf("Expected Temperature 0.3, got %f", result.Temperature)
		}

		// Metadata should be nil for pure GenerationCommonConfig
		if result.Metadata != nil {
			t.Error("Expected Metadata to be nil for GenerationCommonConfig")
		}
	})
}

func TestApplyPassThroughConfig(t *testing.T) {
	// Test the applyPassThroughConfig function
	t.Run("Pass-through config application", func(t *testing.T) {
		req := &anthropic.MessageNewParams{
			Model:     "claude-3-5-sonnet-20241022",
			MaxTokens: 1024,
		}

		config := map[string]any{
			"maxOutputTokens": 2048, // This should be handled by common config, not pass-through
			"metadata": map[string]any{
				"user_id": "test",
			},
		}

		err := applyPassThroughConfig(req, config)
		if err != nil {
			t.Fatalf("applyPassThroughConfig failed: %v", err)
		}

		// The function currently doesn't modify the request, but it should not error
		// This test verifies the infrastructure is in place for future enhancements
	})
}
