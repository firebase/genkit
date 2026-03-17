// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// SPDX-License-Identifier: Apache-2.0

//go:build integration
// +build integration

package ollama

import (
	"context"
	"encoding/json"
	"net/http"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/genkit"
)

// Integration tests require a running Ollama instance
// Run with: go test -tags=integration ./go/plugins/ollama/...
//
// Prerequisites:
// 1. Ollama must be running (default: http://localhost:11434)
// 2. A model must be available (default: llama3.2 for chat, llama3.2 for generate)
//
// Set environment variables to customize:
// - OLLAMA_SERVER_ADDRESS: Ollama server address (default: http://localhost:11434)
// - OLLAMA_CHAT_MODEL: Chat model to use (default: llama3.2)
// - OLLAMA_GENERATE_MODEL: Generate model to use (default: llama3.2)

const (
	defaultServerAddress = "http://localhost:11434"
	defaultChatModel     = "llama3.2"
	defaultGenerateModel = "llama3.2"
	testTimeout          = 60 // seconds
)

func getServerAddress() string {
	if addr := os.Getenv("OLLAMA_SERVER_ADDRESS"); addr != "" {
		return addr
	}
	return defaultServerAddress
}

func getChatModel() string {
	if model := os.Getenv("OLLAMA_CHAT_MODEL"); model != "" {
		return model
	}
	return defaultChatModel
}

func getGenerateModel() string {
	if model := os.Getenv("OLLAMA_GENERATE_MODEL"); model != "" {
		return model
	}
	return defaultGenerateModel
}

// checkOllamaAvailable checks if Ollama is running and accessible
func checkOllamaAvailable(t *testing.T, serverAddress string) {
	t.Helper()
	
	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Get(serverAddress + "/api/tags")
	if err != nil {
		t.Skipf("Ollama not available at %s: %v", serverAddress, err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		t.Skipf("Ollama returned non-200 status: %d", resp.StatusCode)
	}
}

// checkModelAvailable checks if a specific model is available
func checkModelAvailable(t *testing.T, serverAddress, modelName string) {
	t.Helper()
	
	client := &http.Client{Timeout: 5 * time.Second}
	resp, err := client.Get(serverAddress + "/api/tags")
	if err != nil {
		t.Skipf("Cannot check model availability: %v", err)
	}
	defer resp.Body.Close()
	
	var result struct {
		Models []struct {
			Name string `json:"name"`
		} `json:"models"`
	}
	
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Skipf("Cannot parse model list: %v", err)
	}
	
	for _, model := range result.Models {
		if model.Name == modelName || model.Name == modelName+":latest" {
			return
		}
	}
	
	t.Skipf("Model %s not available. Available models: %v", modelName, result.Models)
}

// TestIntegration_ChatModelWithSchema tests chat model with schema returns structured JSON
// **Validates: Requirements 1.1, 1.2, 1.3, 4.1, 4.2**
func TestIntegration_ChatModelWithSchema(t *testing.T) {
	serverAddress := getServerAddress()
	modelName := getChatModel()
	
	checkOllamaAvailable(t, serverAddress)
	checkModelAvailable(t, serverAddress, modelName)
	
	// Initialize Ollama plugin
	ctx := context.Background()
	g := genkit.Init(ctx)
	
	ollama := &Ollama{
		ServerAddress: serverAddress,
		Timeout:       testTimeout,
	}
	ollama.Init(ctx)
	
	// Define chat model
	model := ollama.DefineModel(g, ModelDefinition{
		Name: modelName,
		Type: "chat",
	}, nil)
	
	// Define schema for person object
	schema := map[string]any{
		"type": "object",
		"properties": map[string]any{
			"name": map[string]any{
				"type":        "string",
				"description": "The person's full name",
			},
			"age": map[string]any{
				"type":        "number",
				"description": "The person's age in years",
			},
			"occupation": map[string]any{
				"type":        "string",
				"description": "The person's job or profession",
			},
		},
		"required": []string{"name", "age"},
	}
	
	// Make request with schema
	request := &ai.ModelRequest{
		Messages: []*ai.Message{
			{
				Role: ai.RoleUser,
				Content: []*ai.Part{
					ai.NewTextPart("Generate information about a software engineer named Alice who is 28 years old."),
				},
			},
		},
		Output: &ai.ModelOutputConfig{
			Format: "json",
			Schema: schema,
		},
	}
	
	response, err := model.Generate(ctx, request, nil)
	if err != nil {
		t.Fatalf("Generate failed: %v", err)
	}
	
	// Verify response structure
	if response == nil {
		t.Fatal("Response is nil")
	}
	
	if response.Message == nil {
		t.Fatal("Response message is nil")
	}
	
	if len(response.Message.Content) == 0 {
		t.Fatal("Response has no content")
	}
	
	if !response.Message.Content[0].IsText() {
		t.Fatal("Response content is not text")
	}
	
	// Parse JSON response
	var result map[string]any
	content := response.Message.Content[0].Text
	if err := json.Unmarshal([]byte(content), &result); err != nil {
		t.Fatalf("Response is not valid JSON: %v\nContent: %s", err, content)
	}
	
	// Verify schema conformance
	if _, ok := result["name"]; !ok {
		t.Errorf("Response missing required field 'name': %v", result)
	}
	
	if _, ok := result["age"]; !ok {
		t.Errorf("Response missing required field 'age': %v", result)
	}
	
	// Verify types
	if name, ok := result["name"].(string); !ok || name == "" {
		t.Errorf("Field 'name' is not a non-empty string: %v", result["name"])
	}
	
	if age, ok := result["age"].(float64); !ok || age <= 0 {
		t.Errorf("Field 'age' is not a positive number: %v", result["age"])
	}
	
	t.Logf("Successfully received structured response: %s", content)
}

// TestIntegration_GenerateModelWithSchema tests generate model with schema returns structured JSON
// **Validates: Requirements 1.1, 1.2, 1.4, 4.1, 4.2**
func TestIntegration_GenerateModelWithSchema(t *testing.T) {
	serverAddress := getServerAddress()
	modelName := getGenerateModel()
	
	checkOllamaAvailable(t, serverAddress)
	checkModelAvailable(t, serverAddress, modelName)
	
	// Initialize Ollama plugin
	ctx := context.Background()
	g := genkit.Init(ctx)
	
	ollama := &Ollama{
		ServerAddress: serverAddress,
		Timeout:       testTimeout,
	}
	ollama.Init(ctx)
	
	// Define generate model
	model := ollama.DefineModel(g, ModelDefinition{
		Name: modelName,
		Type: "generate",
	}, nil)
	
	// Define schema for article object
	schema := map[string]any{
		"type": "object",
		"properties": map[string]any{
			"title": map[string]any{
				"type":        "string",
				"description": "The article title",
			},
			"summary": map[string]any{
				"type":        "string",
				"description": "A brief summary of the article",
			},
			"wordCount": map[string]any{
				"type":        "number",
				"description": "Estimated word count",
			},
		},
		"required": []string{"title", "summary"},
	}
	
	// Make request with schema
	request := &ai.ModelRequest{
		Messages: []*ai.Message{
			{
				Role: ai.RoleUser,
				Content: []*ai.Part{
					ai.NewTextPart("Generate an article about artificial intelligence with title and summary."),
				},
			},
		},
		Output: &ai.ModelOutputConfig{
			Format: "json",
			Schema: schema,
		},
	}
	
	response, err := model.Generate(ctx, request, nil)
	if err != nil {
		t.Fatalf("Generate failed: %v", err)
	}
	
	// Verify response structure
	if response == nil {
		t.Fatal("Response is nil")
	}
	
	if response.Message == nil {
		t.Fatal("Response message is nil")
	}
	
	if len(response.Message.Content) == 0 {
		t.Fatal("Response has no content")
	}
	
	if !response.Message.Content[0].IsText() {
		t.Fatal("Response content is not text")
	}
	
	// Parse JSON response
	var result map[string]any
	content := response.Message.Content[0].Text
	if err := json.Unmarshal([]byte(content), &result); err != nil {
		t.Fatalf("Response is not valid JSON: %v\nContent: %s", err, content)
	}
	
	// Verify schema conformance
	if _, ok := result["title"]; !ok {
		t.Errorf("Response missing required field 'title': %v", result)
	}
	
	if _, ok := result["summary"]; !ok {
		t.Errorf("Response missing required field 'summary': %v", result)
	}
	
	// Verify types
	if title, ok := result["title"].(string); !ok || title == "" {
		t.Errorf("Field 'title' is not a non-empty string: %v", result["title"])
	}
	
	if summary, ok := result["summary"].(string); !ok || summary == "" {
		t.Errorf("Field 'summary' is not a non-empty string: %v", result["summary"])
	}
	
	t.Logf("Successfully received structured response: %s", content)
}

// TestIntegration_SchemalessJSONMode tests schema-less JSON mode
// **Validates: Requirements 2.1, 2.2**
func TestIntegration_SchemalessJSONMode(t *testing.T) {
	serverAddress := getServerAddress()
	modelName := getChatModel()
	
	checkOllamaAvailable(t, serverAddress)
	checkModelAvailable(t, serverAddress, modelName)
	
	// Initialize Ollama plugin
	ctx := context.Background()
	g := genkit.Init(ctx)
	
	ollama := &Ollama{
		ServerAddress: serverAddress,
		Timeout:       testTimeout,
	}
	ollama.Init(ctx)
	
	// Define chat model
	model := ollama.DefineModel(g, ModelDefinition{
		Name: modelName,
		Type: "chat",
	}, nil)
	
	// Make request with format: "json" but no schema
	request := &ai.ModelRequest{
		Messages: []*ai.Message{
			{
				Role: ai.RoleUser,
				Content: []*ai.Part{
					ai.NewTextPart("Respond with a JSON object containing your favorite color and a number between 1 and 10."),
				},
			},
		},
		Output: &ai.ModelOutputConfig{
			Format: "json",
		},
	}
	
	response, err := model.Generate(ctx, request, nil)
	if err != nil {
		t.Fatalf("Generate failed: %v", err)
	}
	
	// Verify response structure
	if response == nil {
		t.Fatal("Response is nil")
	}
	
	if response.Message == nil {
		t.Fatal("Response message is nil")
	}
	
	if len(response.Message.Content) == 0 {
		t.Fatal("Response has no content")
	}
	
	if !response.Message.Content[0].IsText() {
		t.Fatal("Response content is not text")
	}
	
	// Verify response is valid JSON (no schema validation)
	var result map[string]any
	content := response.Message.Content[0].Text
	if err := json.Unmarshal([]byte(content), &result); err != nil {
		t.Fatalf("Response is not valid JSON: %v\nContent: %s", err, content)
	}
	
	t.Logf("Successfully received JSON response: %s", content)
}

// TestIntegration_StreamingWithSchema tests streaming with schemas
// **Validates: Requirements 5.1, 5.2, 5.3, 5.4**
func TestIntegration_StreamingWithSchema(t *testing.T) {
	serverAddress := getServerAddress()
	modelName := getChatModel()
	
	checkOllamaAvailable(t, serverAddress)
	checkModelAvailable(t, serverAddress, modelName)
	
	// Initialize Ollama plugin
	ctx := context.Background()
	g := genkit.Init(ctx)
	
	ollama := &Ollama{
		ServerAddress: serverAddress,
		Timeout:       testTimeout,
	}
	ollama.Init(ctx)
	
	// Define chat model
	model := ollama.DefineModel(g, ModelDefinition{
		Name: modelName,
		Type: "chat",
	}, nil)
	
	// Define schema
	schema := map[string]any{
		"type": "object",
		"properties": map[string]any{
			"city": map[string]any{
				"type":        "string",
				"description": "City name",
			},
			"country": map[string]any{
				"type":        "string",
				"description": "Country name",
			},
			"population": map[string]any{
				"type":        "number",
				"description": "Population count",
			},
		},
		"required": []string{"city", "country"},
	}
	
	// Make streaming request with schema
	request := &ai.ModelRequest{
		Messages: []*ai.Message{
			{
				Role: ai.RoleUser,
				Content: []*ai.Part{
					ai.NewTextPart("Generate information about Tokyo, Japan."),
				},
			},
		},
		Output: &ai.ModelOutputConfig{
			Format: "json",
			Schema: schema,
		},
	}
	
	// Collect chunks
	var chunks []*ai.ModelResponseChunk
	chunkCount := 0
	
	callback := func(ctx context.Context, chunk *ai.ModelResponseChunk) error {
		chunkCount++
		chunks = append(chunks, chunk)
		t.Logf("Received chunk %d with %d parts", chunkCount, len(chunk.Content))
		return nil
	}
	
	response, err := model.Generate(ctx, request, callback)
	if err != nil {
		t.Fatalf("Streaming generate failed: %v", err)
	}
	
	// Verify chunks were received
	if chunkCount == 0 {
		t.Fatal("No chunks received during streaming")
	}
	
	t.Logf("Received %d chunks total", chunkCount)
	
	// Verify final response
	if response == nil {
		t.Fatal("Final response is nil")
	}
	
	if response.Message == nil {
		t.Fatal("Final response message is nil")
	}
	
	if len(response.Message.Content) == 0 {
		t.Fatal("Final response has no content")
	}
	
	// Merge chunks manually to verify completeness
	var mergedContent string
	for _, chunk := range chunks {
		for _, part := range chunk.Content {
			if part.IsText() {
				mergedContent += part.Text
			}
		}
	}
	
	// Verify merged content is valid JSON
	var mergedResult map[string]any
	if err := json.Unmarshal([]byte(mergedContent), &mergedResult); err != nil {
		t.Fatalf("Merged chunks are not valid JSON: %v\nContent: %s", err, mergedContent)
	}
	
	// Verify final response content is valid JSON
	var finalResult map[string]any
	finalContent := ""
	for _, part := range response.Message.Content {
		if part.IsText() {
			finalContent += part.Text
		}
	}
	
	if err := json.Unmarshal([]byte(finalContent), &finalResult); err != nil {
		t.Fatalf("Final response is not valid JSON: %v\nContent: %s", err, finalContent)
	}
	
	// Verify schema conformance
	if _, ok := finalResult["city"]; !ok {
		t.Errorf("Response missing required field 'city': %v", finalResult)
	}
	
	if _, ok := finalResult["country"]; !ok {
		t.Errorf("Response missing required field 'country': %v", finalResult)
	}
	
	t.Logf("Successfully received streaming structured response: %s", finalContent)
	t.Logf("Merged chunks match final response: %v", mergedContent == finalContent)
}

// TestIntegration_ErrorScenarios tests error scenarios with live Ollama
// **Validates: Requirements 6.1, 6.4**
func TestIntegration_ErrorScenarios(t *testing.T) {
	serverAddress := getServerAddress()
	
	checkOllamaAvailable(t, serverAddress)
	
	ctx := context.Background()
	g := genkit.Init(ctx)
	
	ollama := &Ollama{
		ServerAddress: serverAddress,
		Timeout:       testTimeout,
	}
	ollama.Init(ctx)
	
	t.Run("Invalid model name", func(t *testing.T) {
		// Define model with non-existent name
		model := ollama.DefineModel(g, ModelDefinition{
			Name: "nonexistent-model-12345",
			Type: "chat",
		}, nil)
		
		request := &ai.ModelRequest{
			Messages: []*ai.Message{
				{
					Role: ai.RoleUser,
					Content: []*ai.Part{
						ai.NewTextPart("Hello"),
					},
				},
			},
		}
		
		_, err := model.Generate(ctx, request, nil)
		if err == nil {
			t.Fatal("Expected error for invalid model name, got nil")
		}
		
		// Verify error message contains useful information
		errMsg := err.Error()
		if !strings.Contains(errMsg, "server returned non-200 status") && !strings.Contains(errMsg, "failed") {
			t.Errorf("Error message doesn't contain expected information: %s", errMsg)
		}
		
		t.Logf("Received expected error: %v", err)
	})
	
	t.Run("Ollama API error response", func(t *testing.T) {
		// Use a valid model but with a very short timeout to potentially trigger errors
		modelName := getChatModel()
		checkModelAvailable(t, serverAddress, modelName)
		
		shortTimeoutOllama := &Ollama{
			ServerAddress: serverAddress,
			Timeout:       1, // 1 second timeout
		}
		shortTimeoutOllama.Init(ctx)
		
		model := shortTimeoutOllama.DefineModel(g, ModelDefinition{
			Name: modelName,
			Type: "chat",
		}, nil)
		
		// Make a request that might timeout
		request := &ai.ModelRequest{
			Messages: []*ai.Message{
				{
					Role: ai.RoleUser,
					Content: []*ai.Part{
						ai.NewTextPart("Write a very long essay about the history of computing with at least 5000 words."),
					},
				},
			},
		}
		
		_, err := model.Generate(ctx, request, nil)
		// This might or might not error depending on model speed
		// If it errors, verify the error is properly formatted
		if err != nil {
			errMsg := err.Error()
			t.Logf("Received error (expected with short timeout): %v", err)
			
			// Verify error message is descriptive
			if errMsg == "" {
				t.Error("Error message is empty")
			}
		} else {
			t.Log("Request completed within timeout (no error to test)")
		}
	})
}
