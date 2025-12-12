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

package anthropic

import (
	"reflect"
	"strings"
	"testing"

	"github.com/anthropics/anthropic-sdk-go"
	"github.com/firebase/genkit/go/ai"
)

func TestAnthropic(t *testing.T) {
	t.Run("to anthropic role", func(t *testing.T) {
		r, err := toAnthropicRole(ai.RoleModel)
		if err != nil {
			t.Error(err)
		}
		if r != anthropic.MessageParamRoleAssistant {
			t.Errorf("want: %q, got: %q", anthropic.MessageParamRoleAssistant, r)
		}
		r, err = toAnthropicRole(ai.RoleUser)
		if err != nil {
			t.Error(err)
		}
		if r != anthropic.MessageParamRoleUser {
			t.Errorf("want: %q, got: %q", anthropic.MessageParamRoleUser, r)
		}
		r, err = toAnthropicRole(ai.RoleSystem)
		if err == nil {
			t.Errorf("should have failed, got: %q", r)
		}
		r, err = toAnthropicRole(ai.RoleTool)
		if err != nil {
			t.Error(err)
		}
		if r != anthropic.MessageParamRoleAssistant {
			t.Errorf("want: %q, got: %q", anthropic.MessageParamRoleAssistant, r)
		}
		r, err = toAnthropicRole("unknown")
		if err == nil {
			t.Errorf("should have failed, got: %q", r)
		}
	})
}

func TestAnthropicConfig(t *testing.T) {
	emptyConfig := anthropic.MessageNewParams{}
	expectedConfig := anthropic.MessageNewParams{
		Temperature: anthropic.Float(1.0),
		TopK:        anthropic.Int(1),
	}

	tests := []struct {
		name           string
		inputReq       *ai.ModelRequest
		expectedConfig *anthropic.MessageNewParams
		expectedErr    string
	}{
		{
			name: "Input is anthropic.MessageNewParams struct",
			inputReq: &ai.ModelRequest{
				Config: anthropic.MessageNewParams{
					Temperature: anthropic.Float(1.0),
					TopK:        anthropic.Int(1),
				},
			},
			expectedConfig: &expectedConfig,
			expectedErr:    "",
		},
		{
			name: "Input is *anthropic.MessageNewParams struct",
			inputReq: &ai.ModelRequest{
				Config: &anthropic.MessageNewParams{
					Temperature: anthropic.Float(1.0),
					TopK:        anthropic.Int(1),
				},
			},
			expectedConfig: &expectedConfig,
			expectedErr:    "",
		},
		{
			name: "Input is map[string]any",
			inputReq: &ai.ModelRequest{
				Config: map[string]any{
					"temperature": 1.0,
					"top_k":       1,
				},
			},
			expectedConfig: &expectedConfig,
			expectedErr:    "",
		},
		{
			name: "Input is map[string]any (empty)",
			inputReq: &ai.ModelRequest{
				Config: map[string]any{},
			},
			expectedConfig: &emptyConfig,
			expectedErr:    "",
		},
		{
			name: "Input is nil",
			inputReq: &ai.ModelRequest{
				Config: nil,
			},
			expectedConfig: &emptyConfig,
			expectedErr:    "",
		},
		{
			name: "Input is an unexpected type",
			inputReq: &ai.ModelRequest{
				Config: 123,
			},
			expectedConfig: &emptyConfig,
			expectedErr:    "unexpected config type: int",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			gotConfig, err := configFromRequest(tt.inputReq)
			if tt.expectedErr != "" {
				if err == nil {
					t.Errorf("expecting error containing %q, got nil", tt.expectedErr)
				} else if !strings.Contains(err.Error(), tt.expectedErr) {
					t.Errorf("expecting error to contain %q, but got: %q", tt.expectedErr, err.Error())
				}
				return
			}
			if err != nil {
				t.Errorf("expected no error, got: %v", err)
			}
			if !reflect.DeepEqual(gotConfig, tt.expectedConfig) {
				t.Errorf("configFromRequest() got config = %+v, want %+v", gotConfig, tt.expectedConfig)
			}
		})
	}
}

func TestToAnthropicTools(t *testing.T) {
	tests := []struct {
		name        string
		tools       []*ai.ToolDefinition
		expected    []anthropic.ToolUnionParam
		expectedErr string
	}{
		{
			name: "valid tool",
			tools: []*ai.ToolDefinition{
				{
					Name:        "my-tool",
					Description: "my tool description",
				},
			},
			expected: []anthropic.ToolUnionParam{
				{
					OfTool: &anthropic.ToolParam{
						Name:        "my-tool",
						Description: anthropic.String("my tool description"),
						InputSchema: anthropic.ToolInputSchemaParam{
							Type:       "object",
							Properties: map[string]any{},
						},
					},
				},
			},
		},
		{
			name: "valid tool with schema",
			tools: []*ai.ToolDefinition{
				{
					Name:        "weather",
					Description: "get weather",
					InputSchema: map[string]any{
						"type": "object",
						"properties": map[string]any{
							"location": map[string]any{
								"type": "string",
							},
						},
						"required": []string{"location"},
					},
				},
			},
			expected: []anthropic.ToolUnionParam{
				{
					OfTool: &anthropic.ToolParam{
						Name:        "weather",
						Description: anthropic.String("get weather"),
						InputSchema: anthropic.ToolInputSchemaParam{
							Type: "object",
							Properties: map[string]any{
								"location": map[string]any{
									"type": "string",
								},
							},
							Required: []string{"location"},
						},
					},
				},
			},
		},
		{
			name: "empty tool name",
			tools: []*ai.ToolDefinition{
				{
					Name:        "",
					Description: "my tool description",
				},
			},
			expectedErr: "tool name is required",
		},
		{
			name: "invalid tool name",
			tools: []*ai.ToolDefinition{
				{
					Name:        "invalid tool name",
					Description: "my tool description",
				},
			},
			expectedErr: "tool name must match regex",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := toAnthropicTools(tt.tools)
			if tt.expectedErr != "" {
				if err == nil {
					t.Errorf("expecting error containing %q, got nil", tt.expectedErr)
				} else if !strings.Contains(err.Error(), tt.expectedErr) {
					t.Errorf("expecting error to contain %q, but got: %q", tt.expectedErr, err.Error())
				}
				return
			}
			if err != nil {
				t.Errorf("expected no error, got: %v", err)
			}
			if !reflect.DeepEqual(got, tt.expected) {
				t.Errorf("toAnthropicTools() got = %+v, want %+v", got, tt.expected)
			}
		})
	}
}

func TestToAnthropicParts(t *testing.T) {
	tests := []struct {
		name        string
		parts       []*ai.Part
		expected    []anthropic.ContentBlockParamUnion
		expectedErr string
	}{
		{
			name: "text part",
			parts: []*ai.Part{
				ai.NewTextPart("hello"),
			},
			expected: []anthropic.ContentBlockParamUnion{
				anthropic.NewTextBlock("hello"),
			},
		},
		{
			name: "tool request part",
			parts: []*ai.Part{
				ai.NewToolRequestPart(&ai.ToolRequest{
					Ref:   "ref1",
					Input: map[string]any{"arg": "value"},
					Name:  "tool1",
				}),
			},
			expected: []anthropic.ContentBlockParamUnion{
				anthropic.NewToolUseBlock("ref1", map[string]any{"arg": "value"}, "tool1"),
			},
		},
		{
			name: "tool response part",
			parts: []*ai.Part{
				ai.NewToolResponsePart(&ai.ToolResponse{
					Ref:    "ref1",
					Output: map[string]any{"result": "ok"},
				}),
			},
			expected: []anthropic.ContentBlockParamUnion{
				anthropic.NewToolResultBlock("ref1", `{"result":"ok"}`, false),
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := toAnthropicParts(tt.parts)
			if tt.expectedErr != "" {
				if err == nil {
					t.Errorf("expecting error containing %q, got nil", tt.expectedErr)
				} else if !strings.Contains(err.Error(), tt.expectedErr) {
					t.Errorf("expecting error to contain %q, but got: %q", tt.expectedErr, err.Error())
				}
				return
			}
			if err != nil {
				t.Errorf("expected no error, got: %v", err)
			}
			if !reflect.DeepEqual(got, tt.expected) {
				t.Errorf("toAnthropicParts() got = %+v, want %+v", got, tt.expected)
			}
		})
	}
}

func TestToAnthropicRequest(t *testing.T) {
	tests := []struct {
		name        string
		req         *ai.ModelRequest
		expected    *anthropic.MessageNewParams
		expectedErr string
	}{
		{
			name: "simple request",
			req: &ai.ModelRequest{
				Messages: []*ai.Message{
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("hello")},
					},
				},
				Config: map[string]any{
					"max_tokens": 10,
				},
			},
			expected: &anthropic.MessageNewParams{
				MaxTokens: 10,
				Messages: []anthropic.MessageParam{
					anthropic.NewUserMessage(anthropic.NewTextBlock("hello")),
				},
			},
		},
		{
			name: "with system prompt",
			req: &ai.ModelRequest{
				Messages: []*ai.Message{
					{
						Role:    ai.RoleSystem,
						Content: []*ai.Part{ai.NewTextPart("system prompt")},
					},
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("hello")},
					},
				},
				Config: map[string]any{
					"max_tokens": 10,
				},
			},
			expected: &anthropic.MessageNewParams{
				MaxTokens: 10,
				System: []anthropic.TextBlockParam{
					{Text: "system prompt"},
				},
				Messages: []anthropic.MessageParam{
					anthropic.NewUserMessage(anthropic.NewTextBlock("hello")),
				},
			},
		},
		{
			name: "no max tokens",
			req: &ai.ModelRequest{
				Messages: []*ai.Message{
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("hello")},
					},
				},
			},
			expectedErr: "maxTokens not set",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := toAnthropicRequest(tt.req)
			if tt.expectedErr != "" {
				if err == nil {
					t.Errorf("expecting error containing %q, got nil", tt.expectedErr)
				} else if !strings.Contains(err.Error(), tt.expectedErr) {
					t.Errorf("expecting error to contain %q, but got: %q", tt.expectedErr, err.Error())
				}
				return
			}
			if err != nil {
				t.Errorf("expected no error, got: %v", err)
			}
			// Can't directly compare because of function pointers in schema
			if got.MaxTokens != tt.expected.MaxTokens {
				t.Errorf("toAnthropicRequest() got MaxTokens = %d, want %d", got.MaxTokens, tt.expected.MaxTokens)
			}
			if len(got.System) != len(tt.expected.System) {
				t.Errorf("toAnthropicRequest() got System len = %d, want %d", len(got.System), len(tt.expected.System))
			}
			if len(got.Messages) != len(tt.expected.Messages) {
				t.Errorf("toAnthropicRequest() got Messages len = %d, want %d", len(got.Messages), len(tt.expected.Messages))
			}
		})
	}
}
