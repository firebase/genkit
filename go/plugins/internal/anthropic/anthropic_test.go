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
	req := &ai.ModelRequest{
		Config: &anthropic.MessageNewParams{
			MaxTokens:     *anthropic.IntPtr(1024),
			Temperature:   anthropic.Float(0.5),
			TopK:          anthropic.Int(2),
			TopP:          anthropic.Float(1.0),
			StopSequences: []string{"tool_use"},
		},
		Messages: []*ai.Message{
			ai.NewSystemTextMessage("greet the user"),
			ai.NewUserTextMessage("hello Claude"),
			ai.NewModelTextMessage("hello User"),
		},
		Tools: []*ai.ToolDefinition{
			{
				Description: "foo description",
				InputSchema: map[string]any{},
				Name:        "foo-tool",
			},
		},
	}
	t.Run("to anthropic request", func(t *testing.T) {
		ar, err := toAnthropicRequest("claude-3.7-opus", req)
		if err != nil {
			t.Fatal(err)
		}
		cfg, _ := req.Config.(*ai.GenerationCommonConfig)
		if ar.MaxTokens != int64(cfg.MaxOutputTokens) {
			t.Errorf("want: %d, got: %d", int64(cfg.MaxOutputTokens), ar.MaxTokens)
		}
		if ar.Temperature.Value != cfg.Temperature {
			t.Errorf("want: %f, got: %f", cfg.Temperature, ar.Temperature.Value)
		}
		if ar.TopK.Value != int64(cfg.TopK) {
			t.Errorf("want: %d, got: %d", int64(cfg.TopK), ar.TopK.Value)
		}
		if ar.TopP.Value != float64(cfg.TopP) {
			t.Errorf("want: %f, got: %f", float64(cfg.TopP), ar.TopP.Value)
		}
		if string(ar.Model) != cfg.Version {
			t.Errorf("want: %q, got: %q", cfg.Version, ar.Model)
		}
		if ar.Tools == nil {
			t.Errorf("expecting tools, got nil")
		}
		if ar.Tools[0].OfTool.Name != req.Tools[0].Name {
			t.Errorf("want: %q, got: %q", req.Tools[0].Name, ar.Tools[0].OfTool.Name)
		}
		if ar.Tools[0].OfTool.Description.Value != req.Tools[0].Description {
			t.Errorf("want: %q, got: %q", req.Tools[0].Name, ar.Tools[0].OfTool.Name)
		}
		if ar.Tools[0].OfTool.InputSchema.Properties == nil {
			t.Errorf("expecting input schema, got nil")
		}
		if len(ar.Messages) == 0 {
			t.Errorf("expecting messages, got empty")
		}
		if ar.System[0].Text == "" {
			t.Errorf("expecting system message, got empty")
		}
		if len(ar.Messages) != 2 {
			t.Errorf("expecting 2 messages, got: %d", len(ar.Messages))
		}
	})
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
	emptyConfig := ai.GenerationCommonConfig{}
	expectedConfig := ai.GenerationCommonConfig{
		Temperature: 0.1,
		TopK:        1,
	}

	tests := []struct {
		name           string
		inputReq       *ai.ModelRequest
		expectedConfig *ai.GenerationCommonConfig
		expectedErr    string
	}{
		{
			name: "Input is ai.GenerationCommonConfig struct",
			inputReq: &ai.ModelRequest{
				Config: ai.GenerationCommonConfig{
					Temperature: 0.1,
					TopK:        1,
				},
			},
			expectedConfig: &expectedConfig,
			expectedErr:    "",
		},
		{
			name: "Input is *ai.GenerationCommonConfig struct",
			inputReq: &ai.ModelRequest{
				Config: &ai.GenerationCommonConfig{
					Temperature: 0.1,
					TopK:        1,
				},
			},
			expectedConfig: &expectedConfig,
			expectedErr:    "",
		},
		{
			name: "Input is map[string]any",
			inputReq: &ai.ModelRequest{
				Config: map[string]any{
					"temperature": 0.1,
					"topK":        1,
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
