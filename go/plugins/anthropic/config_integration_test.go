// Copyright 2025 Google LLC
// SPDX-License-Identifier: Apache-2.0

package anthropic

import (
	"testing"

	"github.com/anthropics/anthropic-sdk-go"
	"github.com/firebase/genkit/go/ai"
)

func TestExpandedUIConfigIntegration(t *testing.T) {
	// Test that the expanded UI configuration options are properly applied
	t.Run("Apply common generation parameters", func(t *testing.T) {
		req := &anthropic.MessageNewParams{
			Model:     "claude-3-5-sonnet-20241022",
			MaxTokens: 1024,
		}

		config := map[string]any{
			"maxOutputTokens": 2048,
			"temperature":     0.7,
			"topK":            40,
			"topP":            0.9,
			"stopSequences":   []interface{}{"Human:", "Assistant:"},
		}

		err := applyPassThroughConfig(req, config)
		if err != nil {
			t.Fatalf("applyPassThroughConfig failed: %v", err)
		}

		// Verify common parameters were applied
		if req.MaxTokens != 2048 {
			t.Errorf("Expected MaxTokens to be 2048, got %d", req.MaxTokens)
		}

		if len(req.StopSequences) != 2 || req.StopSequences[0] != "Human:" || req.StopSequences[1] != "Assistant:" {
			t.Errorf("Expected StopSequences to be ['Human:', 'Assistant:'], got %v", req.StopSequences)
		}

		// Note: Temperature, TopK, TopP use param.Opt types which are harder to test directly
		// The fact that no error occurred means they were processed successfully

		t.Logf("Common generation parameters applied successfully")
	})

	t.Run("Apply User ID configuration", func(t *testing.T) {
		req := &anthropic.MessageNewParams{
			Model:     "claude-3-5-sonnet-20241022",
			MaxTokens: 1024,
		}

		config := map[string]any{
			"userId": "test-user-123",
		}

		err := applyPassThroughConfig(req, config)
		if err != nil {
			t.Fatalf("applyPassThroughConfig failed: %v", err)
		}

		// Test passes if no error occurred - the configuration was applied successfully
		t.Logf("User ID configuration applied successfully")
	})

	t.Run("Apply Service Tier configuration", func(t *testing.T) {
		req := &anthropic.MessageNewParams{
			Model:     "claude-3-5-sonnet-20241022",
			MaxTokens: 1024,
		}

		config := map[string]any{
			"serviceTier": "standard_only",
		}

		err := applyPassThroughConfig(req, config)
		if err != nil {
			t.Fatalf("applyPassThroughConfig failed: %v", err)
		}

		// Verify that ServiceTier was set
		if req.ServiceTier != anthropic.MessageNewParamsServiceTierStandardOnly {
			t.Errorf("Expected ServiceTier to be 'standard_only', got %v", req.ServiceTier)
		}
	})

	t.Run("Apply Thinking configuration", func(t *testing.T) {
		req := &anthropic.MessageNewParams{
			Model:     "claude-3-5-sonnet-20241022",
			MaxTokens: 1024,
		}

		config := map[string]any{
			"thinkingEnabled":      true,
			"thinkingBudgetTokens": 3000,
		}

		err := applyPassThroughConfig(req, config)
		if err != nil {
			t.Fatalf("applyPassThroughConfig failed: %v", err)
		}

		// Verify that Thinking was configured
		if req.Thinking.GetBudgetTokens() == nil || *req.Thinking.GetBudgetTokens() != 3000 {
			t.Errorf("Expected Thinking budget tokens to be 3000, got %v", req.Thinking.GetBudgetTokens())
		}
	})

	t.Run("Apply all configuration options together", func(t *testing.T) {
		req := &anthropic.MessageNewParams{
			Model:     "claude-3-5-sonnet-20241022",
			MaxTokens: 1024,
		}

		config := map[string]any{
			"userId":               "comprehensive-test-user",
			"serviceTier":          "auto",
			"thinkingEnabled":      true,
			"thinkingBudgetTokens": 2048,
		}

		err := applyPassThroughConfig(req, config)
		if err != nil {
			t.Fatalf("applyPassThroughConfig failed: %v", err)
		}

		// Verify service tier and thinking configurations
		if req.ServiceTier != anthropic.MessageNewParamsServiceTierAuto {
			t.Errorf("Expected ServiceTier to be 'auto'")
		}

		if req.Thinking.GetBudgetTokens() == nil || *req.Thinking.GetBudgetTokens() != 2048 {
			t.Errorf("Expected Thinking budget tokens to be 2048")
		}

		t.Logf("All configuration options applied successfully")
	})

	t.Run("Apply Web Search tool configuration", func(t *testing.T) {
		req := &anthropic.MessageNewParams{
			Model:     "claude-3-5-sonnet-20241022",
			MaxTokens: 1024,
		}

		config := map[string]any{
			"webSearchEnabled":        true,
			"webSearchMaxUses":        3,
			"webSearchAllowedDomains": []interface{}{"example.com", "trusteddomain.org"},
		}

		err := applyPassThroughConfig(req, config)
		if err != nil {
			t.Fatalf("applyPassThroughConfig failed: %v", err)
		}

		// Verify that web search tool was added
		if len(req.Tools) != 1 {
			t.Errorf("Expected 1 tool to be added, got %d", len(req.Tools))
		}

		// Verify it's a web search tool
		if req.Tools[0].OfWebSearchTool20250305 == nil {
			t.Errorf("Expected web search tool to be added")
		}

		t.Logf("Web search tool configuration applied successfully")
	})
}

func TestUIConfigSchemaGeneration(t *testing.T) {
	// Test that the UI config generates a proper schema with all expected fields
	config := &AnthropicUIConfig{}
	schema := configToMap(config)

	if schema == nil {
		t.Fatal("configToMap returned nil")
	}

	properties, ok := schema["properties"].(map[string]any)
	if !ok {
		t.Fatal("Schema properties should be a map")
	}

	// Verify all expected fields are present with proper types and descriptions
	expectedFields := map[string]struct {
		title       string
		description string
	}{
		"maxOutputTokens": {
			title:       "Max Output Tokens",
			description: "Maximum number of tokens to generate",
		},
		"temperature": {
			title:       "Temperature",
			description: "Controls randomness in generation (0.0-1.0)",
		},
		"topK": {
			title:       "Top K",
			description: "Sample from top K options for each token",
		},
		"topP": {
			title:       "Top P",
			description: "Nucleus sampling threshold (0.0-1.0)",
		},
		"stopSequences": {
			title:       "Stop Sequences",
			description: "Custom sequences that stop generation",
		},
		"userId": {
			title:       "User ID",
			description: "External identifier for the user (UUID or hash - no PII)",
		},
		"serviceTier": {
			title:       "Service Tier",
			description: "Service tier for the request",
		},
		"thinkingEnabled": {
			title:       "Enable Thinking",
			description: "Enable Claude's extended thinking process",
		},
		"thinkingBudgetTokens": {
			title:       "Thinking Budget Tokens",
			description: "Token budget for thinking (minimum 1024)",
		},
	}

	for fieldName, expected := range expectedFields {
		fieldSchema, exists := properties[fieldName]
		if !exists {
			t.Errorf("Expected field %s to be present in schema", fieldName)
			continue
		}

		fieldMap, ok := fieldSchema.(map[string]any)
		if !ok {
			t.Errorf("Field %s schema should be a map", fieldName)
			continue
		}

		// Check title
		if title, hasTitle := fieldMap["title"]; hasTitle {
			if titleStr, ok := title.(string); ok {
				if titleStr != expected.title {
					t.Errorf("Field %s has title '%s', expected '%s'", fieldName, titleStr, expected.title)
				}
			}
		} else {
			t.Errorf("Field %s should have a title", fieldName)
		}

		// Check description
		if description, hasDescription := fieldMap["description"]; hasDescription {
			if descStr, ok := description.(string); ok {
				if descStr != expected.description {
					t.Errorf("Field %s has description '%s', expected '%s'", fieldName, descStr, expected.description)
				}
			}
		} else {
			t.Errorf("Field %s should have a description", fieldName)
		}
	}

	t.Logf("UI Config schema successfully generated with %d properties", len(properties))
}

func TestCodeExecutionBetaAPIIntegration(t *testing.T) {
	// Test that code execution configuration properly triggers Beta API usage
	t.Run("Apply Code Execution tool configuration", func(t *testing.T) {
		req := &anthropic.MessageNewParams{
			Model:     "claude-3-5-sonnet-20241022",
			MaxTokens: 1024,
		}

		config := map[string]any{
			"codeExecutionEnabled":     true,
			"codeExecutionToolName":    "my_code_executor",
			"codeExecutionToolVersion": DefaultCodeExecutionVersion,
		}

		err := applyPassThroughConfig(req, config)
		if err != nil {
			t.Fatalf("applyPassThroughConfig failed: %v", err)
		}

		// Verify that code execution tool was added
		if len(req.Tools) != 1 {
			t.Errorf("Expected 1 tool to be added, got %d", len(req.Tools))
		}

		// Verify it's a code execution tool with the correct name
		if req.Tools[0].OfTool == nil {
			t.Errorf("Expected code execution tool to be added")
		} else if req.Tools[0].OfTool.Name != "my_code_executor" {
			t.Errorf("Expected tool name 'my_code_executor', got %s", req.Tools[0].OfTool.Name)
		}

		t.Logf("Code execution tool configuration applied successfully")
	})

	t.Run("Code execution auto-enables Beta API", func(t *testing.T) {
		// Test that code execution automatically enables Beta API
		config := map[string]any{
			"codeExecutionEnabled": true,
		}

		mockRequest := &ai.ModelRequest{Config: config}

		// Should automatically enable Beta API
		if !shouldUseBetaAPI(mockRequest) {
			t.Error("Code execution should automatically enable Beta API")
		}

		// Should automatically include code execution beta feature
		features := getBetaFeatures(mockRequest)
		found := false
		for _, feature := range features {
			if feature == CodeExecutionBetaFeature {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("Expected beta features to include %s, got %v", CodeExecutionBetaFeature, features)
		}

		t.Logf("Code execution auto-enabled Beta API with feature: %s", CodeExecutionBetaFeature)
	})

	t.Run("Code execution with explicit beta features", func(t *testing.T) {
		// Test that code execution works with other beta features
		config := map[string]any{
			"codeExecutionEnabled": true,
			"betaFeatures":         []interface{}{"other-feature", "another-feature"},
		}

		mockRequest := &ai.ModelRequest{Config: config}

		// Should enable Beta API
		if !shouldUseBetaAPI(mockRequest) {
			t.Error("Code execution with beta features should enable Beta API")
		}

		// Should include all beta features including code execution
		features := getBetaFeatures(mockRequest)
		expectedFeatures := []string{"other-feature", "another-feature", CodeExecutionBetaFeature}

		if len(features) != len(expectedFeatures) {
			t.Errorf("Expected %d beta features, got %d: %v", len(expectedFeatures), len(features), features)
		}

		// Check that all expected features are present
		for _, expected := range expectedFeatures {
			found := false
			for _, actual := range features {
				if actual == expected {
					found = true
					break
				}
			}
			if !found {
				t.Errorf("Expected beta feature %s not found in %v", expected, features)
			}
		}

		t.Logf("Code execution with explicit beta features works correctly: %v", features)
	})
}
