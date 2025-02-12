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
				Media:     false,
				Tools:     false,
				Multiturn: false,
			},
			input: &ModelRequest{
				Messages: []*Message{
					{Content: []*Part{NewTextPart("hello")}},
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
					{Content: []*Part{NewTextPart("message 1")}},
					{Content: []*Part{NewTextPart("message 2")}},
				},
			},
			wantErr: true,
		},
		{
			name: "all features supported and used",
			supports: &ModelInfoSupports{
				Media:     true,
				Tools:     true,
				Multiturn: true,
			},
			input: &ModelRequest{
				Messages: []*Message{
					{Content: []*Part{NewMediaPart("image/png", "data:image/png;base64,...")}},
					{Content: []*Part{NewTextPart("follow-up message")}},
				},
				Tools: []*ToolDefinition{
					{
						Name:        "test-tool",
						Description: "A test tool",
					},
				},
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

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			middleware := ValidateSupport("test-model", tt.supports)

			_, err := middleware(context.Background(), tt.input, nil,
				func(ctx context.Context, req *ModelRequest, cb ModelStreamingCallback) (*ModelResponse, error) {
					return &ModelResponse{}, nil
				})

			if (err != nil) != tt.wantErr {
				t.Errorf("ValidateSupport() error = %v, wantErr %v", err, tt.wantErr)
				if err != nil {
					t.Logf("Error message: %v", err)
				}
			}
		})
	}
}
