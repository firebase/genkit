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

package ollama

import (
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/api"
)

var _ api.Plugin = (*Ollama)(nil)

func TestConcatMessages(t *testing.T) {
	tests := []struct {
		name     string
		messages []*ai.Message
		roles    []ai.Role
		want     string
	}{
		{
			name: "Single message with matching role",
			messages: []*ai.Message{
				{
					Role:    ai.RoleUser,
					Content: []*ai.Part{ai.NewTextPart("Hello, how are you?")},
				},
			},
			roles: []ai.Role{ai.RoleUser},
			want:  "Hello, how are you?",
		},
		{
			name: "Multiple messages with mixed roles",
			messages: []*ai.Message{
				{
					Role:    ai.RoleUser,
					Content: []*ai.Part{ai.NewTextPart("Tell me a joke.")},
				},
				{
					Role:    ai.RoleModel,
					Content: []*ai.Part{ai.NewTextPart("Why did the scarecrow win an award? Because he was outstanding in his field!")},
				},
			},
			roles: []ai.Role{ai.RoleModel},
			want:  "Why did the scarecrow win an award? Because he was outstanding in his field!",
		},
		{
			name: "No matching role",
			messages: []*ai.Message{
				{
					Role:    ai.RoleUser,
					Content: []*ai.Part{ai.NewTextPart("Any suggestions?")},
				},
			},
			roles: []ai.Role{ai.RoleSystem},
			want:  "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			input := &ai.ModelRequest{Messages: tt.messages}
			got := concatMessages(input, tt.roles)
			if got != tt.want {
				t.Errorf("concatMessages() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestTranslateGenerateChunk(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    *ai.ModelResponseChunk
		wantErr bool
	}{
		{
			name:  "Valid JSON response",
			input: `{"model": "my-model", "created_at": "2024-06-20T12:34:56Z", "response": "This is a test response."}`,
			want: &ai.ModelResponseChunk{
				Content: []*ai.Part{ai.NewTextPart("This is a test response.")},
			},
			wantErr: false,
		},
		{
			name:    "Invalid JSON",
			input:   `{invalid}`,
			want:    nil,
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := translateGenerateChunk(tt.input)
			if (err != nil) != tt.wantErr {
				t.Errorf("translateGenerateChunk() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if !tt.wantErr && !equalContent(got.Content, tt.want.Content) {
				t.Errorf("translateGenerateChunk() got = %v, want %v", got, tt.want)
			}
		})
	}
}

// Helper function to compare content
func equalContent(a, b []*ai.Part) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i].IsText() {
			if !b[i].IsText() || a[i].Text != b[i].Text {
				return false
			}
		} else if a[i].IsReasoning() {
			if !b[i].IsReasoning() || a[i].Text != b[i].Text {
				return false
			}
		} else {
			// For other types, we might need more specific checks,
			// but for now return false if kinds don't match or not handled
			return false
		}
	}
	return true
}

func TestTranslateChatResponse(t *testing.T) {
	tests := []struct {
		name          string
		input         string
		want          *ai.ModelResponse
		wantReasoning string
		wantErr       bool
	}{
		{
			name:  "Thinking field present",
			input: `{"model": "deepseek-r1", "created_at": "2024-06-20T12:34:56Z", "message": {"role": "assistant", "content": "Hello", "thinking": "I should say hello"}}`,
			want: &ai.ModelResponse{
				Message: &ai.Message{
					Role: ai.RoleModel,
					Content: []*ai.Part{
						ai.NewReasoningPart("I should say hello", nil),
						ai.NewTextPart("Hello"),
					},
				},
			},
			wantReasoning: "I should say hello",
		},
		{
			name:  "Thinking in content tag",
			input: `{"model": "deepseek-r1", "created_at": "2024-06-20T12:34:56Z", "message": {"role": "assistant", "content": "<think>I should say hello</think>Hello"}}`,
			want: &ai.ModelResponse{
				Message: &ai.Message{
					Role: ai.RoleModel,
					Content: []*ai.Part{
						ai.NewReasoningPart("I should say hello", nil),
						ai.NewTextPart("Hello"),
					},
				},
			},
			wantReasoning: "I should say hello",
		},
		{
			name:  "Only thinking in content",
			input: `{"model": "deepseek-r1", "created_at": "2024-06-20T12:34:56Z", "message": {"role": "assistant", "content": "<think>Just thinking</think>"}}`,
			want: &ai.ModelResponse{
				Message: &ai.Message{
					Role: ai.RoleModel,
					Content: []*ai.Part{
						ai.NewReasoningPart("Just thinking", nil),
					},
				},
			},
			wantReasoning: "Just thinking",
		},
		{
			name:  "No thinking",
			input: `{"model": "llama3", "created_at": "2024-06-20T12:34:56Z", "message": {"role": "assistant", "content": "Hello"}}`,
			want: &ai.ModelResponse{
				Message: &ai.Message{
					Role: ai.RoleModel,
					Content: []*ai.Part{
						ai.NewTextPart("Hello"),
					},
				},
			},
			wantReasoning: "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := translateChatResponse([]byte(tt.input))
			if (err != nil) != tt.wantErr {
				t.Errorf("translateChatResponse() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if !tt.wantErr {
				if got.Reasoning() != tt.wantReasoning {
					t.Errorf("translateChatResponse() Reasoning = %q, want %q", got.Reasoning(), tt.wantReasoning)
				}
				if !equalContent(got.Message.Content, tt.want.Message.Content) {
					t.Errorf("translateChatResponse() got = %v, want %v", got.Message.Content, tt.want.Message.Content)
				}
			}
		})
	}
}
