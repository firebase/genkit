// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

package ai

import (
	"context"
	"testing"
)

func TestValidateSupport(t *testing.T) {
	tests := []struct {
		name     string
		supports *ModelInfoSupports
		input    *ModelRequest
		wantErr  bool
	}{
		{
			name: "valid request with no special features",
			supports: &ModelInfoSupports{
				Media:      false,
				Tools:      false,
				Multiturn:  false,
				ToolChoice: false,
				SystemRole: false,
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
			supports: &ModelInfoSupports{
				Media: false,
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
			supports: &ModelInfoSupports{
				Tools: false,
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
			supports: &ModelInfoSupports{
				Multiturn: false,
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
			supports: &ModelInfoSupports{
				ToolChoice: false,
			},
			input: &ModelRequest{
				ToolChoice: ToolChoiceRequired,
			},
			wantErr: true,
		},
		{
			name: "system role not supported but requested",
			supports: &ModelInfoSupports{
				SystemRole: false,
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
			supports: &ModelInfoSupports{
				Media:      true,
				Tools:      true,
				Multiturn:  true,
				ToolChoice: true,
				SystemRole: true,
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
			name:     "nil supports defaults to no features",
			supports: nil,
			input: &ModelRequest{
				Messages: []*Message{
					{Content: []*Part{NewMediaPart("image/png", "data:image/png;base64,...")}},
				},
			},
			wantErr: true,
		},
		{
			name: "mixed content types in message",
			supports: &ModelInfoSupports{
				Media: false,
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
	}

	mockModelFunc := func(ctx context.Context, req *ModelRequest, cb ModelStreamingCallback) (*ModelResponse, error) {
		return &ModelResponse{}, nil
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			handler := ValidateSupport("test-model", tt.supports)(mockModelFunc)
			_, err := handler(context.Background(), tt.input, nil)

			if (err != nil) != tt.wantErr {
				t.Errorf("ValidateSupport() error = %v, wantErr %v", err, tt.wantErr)
				if err != nil {
					t.Logf("Error message: %v", err)
				}
			}
		})
	}
}
