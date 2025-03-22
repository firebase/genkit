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

package ai

import (
	"context"
	"reflect"
	"testing"
)

func TestValidateSupport(t *testing.T) {
	tests := []struct {
		name    string
		info    *ModelInfo
		input   *ModelRequest
		wantErr bool
	}{
		{
			name: "valid request with no special features",
			info: &ModelInfo{
				Supports: &ModelSupports{
					Media:      false,
					Tools:      false,
					Multiturn:  false,
					ToolChoice: false,
					SystemRole: false,
				},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewUserTextMessage("hello"),
				},
			},
			wantErr: false,
		},
		{
			name: "media not supported but requested",
			info: &ModelInfo{
				Supports: &ModelSupports{
					Media: false,
				},
			},
			input: &ModelRequest{
				Messages: []*Message{
					{Content: []*Part{NewMediaPart("image/png", "data:image/png;base64,...")}},
				},
			},
			wantErr: true,
		},
		{
			name: "tools not supported but requested",
			info: &ModelInfo{
				Supports: &ModelSupports{
					Tools: false,
				},
			},
			input: &ModelRequest{
				Tools: []*ToolDefinition{
					{
						Name:        "test-tool",
						Description: "A test tool",
					},
				},
			},
			wantErr: true,
		},
		{
			name: "multiturn not supported but requested",
			info: &ModelInfo{
				Supports: &ModelSupports{
					Multiturn: false,
				},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewUserTextMessage("message 1"),
					NewUserTextMessage("message 2"),
				},
			},
			wantErr: true,
		},
		{
			name: "tool choice not supported but requested",
			info: &ModelInfo{
				Supports: &ModelSupports{
					ToolChoice: false,
				},
			},
			input: &ModelRequest{
				ToolChoice: ToolChoiceRequired,
			},
			wantErr: true,
		},
		{
			name: "system role not supported but requested",
			info: &ModelInfo{
				Supports: &ModelSupports{
					SystemRole: false,
				},
			},
			input: &ModelRequest{
				Messages: []*Message{
					{Role: RoleSystem, Content: []*Part{NewTextPart("system instruction")}},
				},
			},
			wantErr: true,
		},
		{
			name: "all features supported and used",
			info: &ModelInfo{
				Supports: &ModelSupports{
					Media:      true,
					Tools:      true,
					Multiturn:  true,
					ToolChoice: true,
					SystemRole: true,
				},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewSystemTextMessage("be helpful"),
					NewUserTextMessage("hello! look at this image"),
					{Content: []*Part{NewMediaPart("image/png", "data:image/png;base64,...")}},
				},
				Tools: []*ToolDefinition{
					{
						Name:        "test-tool",
						Description: "A test tool",
					},
				},
				ToolChoice: ToolChoiceNone,
			},
			wantErr: false,
		},
		{
			name: "nil supports defaults to no features",
			info: nil,
			input: &ModelRequest{
				Messages: []*Message{
					{Content: []*Part{NewMediaPart("image/png", "data:image/png;base64,...")}},
				},
			},
			wantErr: true,
		},
		{
			name: "mixed content types in message",
			info: &ModelInfo{
				Supports: &ModelSupports{
					Media: false,
				},
			},
			input: &ModelRequest{
				Messages: []*Message{
					{Content: []*Part{
						NewTextPart("text content"),
						NewMediaPart("image/png", "data:image/png;base64,..."),
					}},
				},
			},
			wantErr: true,
		},
		{
			name: "supported version",
			info: &ModelInfo{
				Supports: &ModelSupports{},
				Versions: []string{"v1", "v2"},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewUserTextMessage("hello"),
				},
				Config: map[string]any{"version": "v1"},
			},
			wantErr: false,
		},
		{
			name: "unsupported version",
			info: &ModelInfo{
				Supports: &ModelSupports{},
				Versions: []string{"v1", "v2"},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewUserTextMessage("hello"),
				},
				Config: map[string]any{"version": "v3"},
			},
			wantErr: true,
		},
		{
			name: "non-string version",
			info: &ModelInfo{
				Supports: &ModelSupports{},
				Versions: []string{"v1", "v2"},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewUserTextMessage("hello"),
				},
				Config: map[string]any{"version": 1},
			},
			wantErr: true,
		},
		{
			name: "struct with supported version",
			info: &ModelInfo{
				Supports: &ModelSupports{},
				Versions: []string{"v1", "v2"},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewUserTextMessage("hello"),
				},
				Config: &GenerationCommonConfig{Version: "v1"},
			},
			wantErr: false,
		},
		{
			name: "struct with unsupported version",
			info: &ModelInfo{
				Supports: &ModelSupports{},
				Versions: []string{"v1", "v2"},
			},
			input: &ModelRequest{
				Messages: []*Message{
					NewUserTextMessage("hello"),
				},
				Config: &GenerationCommonConfig{Version: "v3"},
			},
			wantErr: true,
		},
	}

	mockModelFunc := func(ctx context.Context, req *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
		return &ModelResponse{}, nil
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			handler := validateSupport("test-model", tt.info)(mockModelFunc)
			_, err := handler(context.Background(), tt.input, nil)

			if (err != nil) != tt.wantErr {
				t.Errorf("validateSupport() error = %v, wantErr %v", err, tt.wantErr)
				if err != nil {
					t.Logf("Error message: %v", err)
				}
			}
		})
	}
}

func TestSimulateSystemPrompt(t *testing.T) {
	testCases := []struct {
		name        string
		info        *ModelInfo
		options     map[string]string
		input       *ModelRequest
		expected    *ModelRequest
		supportsSys bool
	}{
		{
			name: "system role not supported, system message present",
			info: &ModelInfo{Supports: &ModelSupports{SystemRole: false}},
			input: &ModelRequest{
				Messages: []*Message{
					{Role: "system", Content: []*Part{NewTextPart("Be helpful.")}},
					{Role: "user", Content: []*Part{NewTextPart("Hello.")}},
				},
			},
			expected: &ModelRequest{
				Messages: []*Message{
					{Role: "user", Content: []*Part{NewTextPart("SYSTEM INSTRUCTIONS:\n"), NewTextPart("Be helpful.")}},
					{Role: "model", Content: []*Part{NewTextPart("Understood.")}},
					{Role: "user", Content: []*Part{NewTextPart("Hello.")}},
				},
			},
			supportsSys: true,
		},
		{
			name: "system role supported, no system message",
			info: &ModelInfo{Supports: &ModelSupports{SystemRole: true}},
			input: &ModelRequest{
				Messages: []*Message{
					{Role: "user", Content: []*Part{NewTextPart("Hello.")}},
				},
			},
			expected: &ModelRequest{
				Messages: []*Message{
					{Role: "user", Content: []*Part{NewTextPart("Hello.")}},
				},
			},
			supportsSys: true,
		},
		{
			name: "system role supported, with system message",
			info: &ModelInfo{Supports: &ModelSupports{SystemRole: true}},
			input: &ModelRequest{
				Messages: []*Message{
					{Role: "system", Content: []*Part{NewTextPart("Be helpful.")}},
					{Role: "user", Content: []*Part{NewTextPart("Hello.")}},
				},
			},
			expected: &ModelRequest{
				Messages: []*Message{
					{Role: "system", Content: []*Part{NewTextPart("Be helpful.")}},
					{Role: "user", Content: []*Part{NewTextPart("Hello.")}},
				},
			},
			supportsSys: false,
		},
		{
			name: "custom preface and acknowledgement",
			info: &ModelInfo{Supports: &ModelSupports{SystemRole: false}},
			options: map[string]string{
				"preface":         "CUSTOM PREFACE:\n",
				"acknowledgement": "OKAY!",
			},
			input: &ModelRequest{
				Messages: []*Message{
					{Role: "system", Content: []*Part{NewTextPart("Be helpful.")}},
					{Role: "user", Content: []*Part{NewTextPart("Hello.")}},
				},
			},
			expected: &ModelRequest{
				Messages: []*Message{
					{Role: "user", Content: []*Part{NewTextPart("CUSTOM PREFACE:\n"), NewTextPart("Be helpful.")}},
					{Role: "model", Content: []*Part{NewTextPart("OKAY!")}},
					{Role: "user", Content: []*Part{NewTextPart("Hello.")}},
				},
			},
			supportsSys: true,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			next := func(ctx context.Context, input *ModelRequest, cb ModelStreamCallback) (*ModelResponse, error) {
				if !reflect.DeepEqual(input, tc.expected) {
					t.Errorf("Input messages were not modified as expected. got: %+v, want: %+v", input, tc.expected)
				}
				return &ModelResponse{}, nil
			}
			middleware := simulateSystemPrompt(tc.info, tc.options)
			_, _ = middleware(next)(context.Background(), tc.input, nil)
		})
	}
}
