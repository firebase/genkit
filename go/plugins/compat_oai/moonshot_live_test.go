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

package compat_oai_test

import (
	"os"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/plugins/compat_oai"
	"github.com/openai/openai-go"
	"github.com/openai/openai-go/option"
)

// setupFunc creates a ModelGenerator for testing reasoning_content compatibility.
// Each setup function should check for required environment variables and skip
// the test if they are not configured.
type setupFunc func(t *testing.T) *compat_oai.ModelGenerator

// TestToolCallReasoning verifies that the compat_oai plugin correctly handles
// reasoning_content for OpenAI-compatible backends
// that require it (e.g., Moonshot/Kimi).
func TestToolCallReasoning(t *testing.T) {
	testCases := []struct {
		name  string
		setup setupFunc
	}{
		{
			name:  "Moonshot",
			setup: setupMoonshotCompatibleTestClient,
		},
	}

	toolDefs := []*ai.ToolDefinition{weatherTool}
	messages := []*ai.Message{
		ai.NewUserTextMessage("Call the get_weather tool for Paris."),
	}
	req := ai.NewModelRequest(nil)

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			ctx := t.Context()
			g := tc.setup(t)

			// Validate tool request returned from model
			resp, err := g.WithMessages(messages).WithTools(toolDefs).Generate(ctx, req, nil)
			if err != nil {
				t.Fatalf("First generate failed: %v", err)
			}

			toolRequests := resp.ToolRequests()
			if len(toolRequests) != 1 {
				t.Fatalf("Expected 1 tool request, got %d", len(toolRequests))
			}
			if resp.Reasoning() == "" {
				t.Fatal("Expected reasoning on first response, got empty")
			}

			// Send tool response with conversation history
			toolResp := &ai.Message{
				Role: ai.RoleTool,
				Content: []*ai.Part{
					ai.NewToolResponsePart(
						&ai.ToolResponse{
							Name:   toolRequests[0].Name,
							Ref:    toolRequests[0].Ref,
							Output: map[string]any{"temp_c": 21, "condition": "sunny"},
						}),
				},
			}
			history := append(resp.History(), toolResp)

			// Verify second request succeeds with reasoning_content preserved
			resp, err = g.WithMessages(history).Generate(ctx, req, nil)
			if err != nil {
				t.Fatalf("rejected request with tool response: %v", err)
			}

			if resp.Text() == "" {
				t.Fatalf("empty response from the model: %#v", resp)
			}

			t.Logf("model response: %v", resp.Text())
		})
	}
}

// setupMoonshotCompatibleTestClient creates a ModelGenerator for
// Moonshot-compatible backends.
//
// Required environment variables:
//   - MOONSHOT_API_KEY
//   - MOONSHOT_BASE_URL (e.g., "https://api.moonshot.cn/v1")
//   - MOONSHOT_MODEL (e.g., "kimi-k2.5")
//
// Tested with:
//   - Base URL: https://opencode.ai/zen/go/v1
//   - Model: kimi-k2.5
func setupMoonshotCompatibleTestClient(t *testing.T) *compat_oai.ModelGenerator {
	t.Helper()

	vars := []string{
		"MOONSHOT_API_KEY",
		"MOONSHOT_BASE_URL",
		"MOONSHOT_MODEL",
	}
	var missing []string

	for i, envVar := range vars {
		v := os.Getenv(envVar)
		if v == "" {
			missing = append(missing, envVar)
			continue
		}
		vars[i] = v
	}
	if len(missing) != 0 {
		t.Skipf("missing env vars: %s", strings.Join(missing, ", "))
	}

	client := openai.NewClient(
		option.WithAPIKey(vars[0]),
		option.WithBaseURL(vars[1]),
	)
	return compat_oai.NewModelGenerator(
		&client, vars[2])
}

var weatherTool = &ai.ToolDefinition{
	Name:        "get_weather",
	Description: "Get the current weather for a location. Always use this tool when asked about weather.",
	InputSchema: map[string]any{
		"type": "object",
		"properties": map[string]any{
			"city": map[string]any{
				"type":        "string",
				"description": "The city name to get weather for",
			},
		},
		"required": []string{"city"},
	},
}
