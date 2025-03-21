// Copyright 2024 Google LLC
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

package ai

import (
	"context"
	"testing"

	test_utils "github.com/firebase/genkit/go/tests/utils"
	"github.com/google/go-cmp/cmp"
)

func TestSimulateConstrainedGeneration(t *testing.T) {
	tests := []struct {
		name       string
		info       *ModelInfo
		input      *ModelRequest
		wantMsgs   []*Message
		wantConfig *OutputConfig
	}{
		{
			name: "simulates constraint if no model support",
			info: &ModelInfo{
				Supports: &ModelInfoSupports{
					Constrained: ModelInfoSupportsConstrainedNone,
				},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewSystemTextMessage("You are a helpful assistant."),
					NewUserTextMessage("hello!"),
				},
				Output: &OutputConfig{
					Format:      string(OutputFormatJSON),
					Constrained: true,
					Schema: map[string]any{
						"type":     "object",
						"required": []string{"name"},
						"properties": map[string]any{
							"name": map[string]any{"type": "string"},
						},
					},
				},
			},
			wantMsgs: []*Message{
				{
					Role: RoleSystem,
					Content: []*Part{
						NewTextPart("You are a helpful assistant."),
						NewTextPart("Output should be in JSON format and conform to the following schema:\n\n```\"{\\\"properties\\\":{\\\"name\\\":{\\\"type\\\":\\\"string\\\"}},\\\"required\\\":[\\\"name\\\"],\\\"type\\\":\\\"object\\\"}\"```"),
					},
				},
				NewUserTextMessage("hello!"),
			},
			wantConfig: &OutputConfig{
				Format:      string(OutputFormatJSON),
				Constrained: false,
				Schema: map[string]any{
					"type":     "object",
					"required": []string{"name"},
					"properties": map[string]any{
						"name": map[string]any{"type": "string"},
					},
				},
			},
		},
		{
			name: "simulates constraint if no tool support and tools are in request",
			info: &ModelInfo{
				Supports: &ModelInfoSupports{
					Constrained: ModelInfoSupportsConstrainedNoTools,
				},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewSystemTextMessage("You are a helpful assistant."),
					NewUserTextMessage("hello!"),
				},
				Output: &OutputConfig{
					Format:      string(OutputFormatJSON),
					Constrained: true,
					Schema: map[string]any{
						"type":     "object",
						"required": []string{"name"},
						"properties": map[string]any{
							"name": map[string]any{"type": "string"},
						},
					},
				},
				Tools: []*ToolDefinition{
					{
						Name:        "test-tool",
						Description: "A test tool",
					},
				},
			},
			wantMsgs: []*Message{
				{
					Role: RoleSystem,
					Content: []*Part{
						NewTextPart("You are a helpful assistant."),
						NewTextPart("Output should be in JSON format and conform to the following schema:\n\n```\"{\\\"properties\\\":{\\\"name\\\":{\\\"type\\\":\\\"string\\\"}},\\\"required\\\":[\\\"name\\\"],\\\"type\\\":\\\"object\\\"}\"```"),
					},
				},
				NewUserTextMessage("hello!"),
			},
			wantConfig: &OutputConfig{
				Format:      string(OutputFormatJSON),
				Constrained: false,
				Schema: map[string]any{
					"type":     "object",
					"required": []string{"name"},
					"properties": map[string]any{
						"name": map[string]any{"type": "string"},
					},
				},
			},
		},
	}

	// input: &ModelRequest{
	// 	Messages: []*Message{
	// 		NewSystemTextMessage("be helpful"),
	// 		NewUserTextMessage("hello! look at this image"),
	// 		{Content: []*Part{NewMediaPart("image/png", "data:image/png;base64,...")}},
	// 	},
	// 	Tools: []*ToolDefinition{
	// 		{
	// 			Name:        "test-tool",
	// 			Description: "A test tool",
	// 		},
	// 	},
	// 	ToolChoice: ToolChoiceNone,
	// },

	mockModelFunc := func(ctx context.Context, req *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
		return &ModelResponse{Request: req}, nil
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			handler := SimulateConstrainedGeneration("test-model", tt.info)(mockModelFunc)
			resp, err := handler(context.Background(), tt.input, nil)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}

			if diff := cmp.Diff(resp.Request.Messages, tt.wantMsgs, test_utils.IgnoreNoisyParts([]string{})); diff != "" {
				t.Errorf("Request msgs diff (+got -want):\n%s", diff)
			}

			if diff := cmp.Diff(resp.Request.Output, tt.wantConfig, test_utils.IgnoreNoisyParts([]string{})); diff != "" {
				t.Errorf("Request config diff (+got -want):\n%s", diff)
			}
		})
	}
}
