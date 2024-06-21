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

package ollama

import (
	"testing"

	"github.com/firebase/genkit/go/ai"
)

func TestConcatMessages(t *testing.T) {
	tests := []struct {
		name     string
		messages []*ai.Message
		role     ai.Role
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
			role: ai.RoleUser,
			want: "Hello, how are you?",
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
			role: ai.RoleModel,
			want: "Why did the scarecrow win an award? Because he was outstanding in his field!",
		},
		{
			name: "No matching role",
			messages: []*ai.Message{
				{
					Role:    ai.RoleUser,
					Content: []*ai.Part{ai.NewTextPart("Any suggestions?")},
				},
			},
			role: ai.RoleSystem,
			want: "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			input := &ai.GenerateRequest{Messages: tt.messages}
			got := concatMessages(input, tt.role)
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
		want    *ai.GenerateResponseChunk
		wantErr bool
	}{
		{
			name:  "Valid JSON response",
			input: `{"model": "my-model", "created_at": "2024-06-20T12:34:56Z", "response": "This is a test response."}`,
			want: &ai.GenerateResponseChunk{
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
		if a[i].Text != b[i].Text || !a[i].IsText() || !b[i].IsText() {
			return false
		}
	}
	return true
}
