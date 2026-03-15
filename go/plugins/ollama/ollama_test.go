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
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/core/api"
)

var _ api.Plugin = (*Ollama)(nil)
var _ api.DynamicPlugin = (*Ollama)(nil)

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
		if a[i].Text != b[i].Text || !a[i].IsText() || !b[i].IsText() {
			return false
		}
	}
	return true
}

func newTestOllama(serverAddress string) *Ollama {
	o := &Ollama{ServerAddress: serverAddress, Timeout: 30}
	o.Init(context.Background())
	return o
}

func TestDynamicPlugin(t *testing.T) {
	t.Run("listLocalModels", func(t *testing.T) {
		tests := []struct {
			name       string
			response   ollamaTagsResponse
			statusCode int
			wantCount  int
			wantErr    bool
		}{
			{
				name: "successful response with multiple models",
				response: ollamaTagsResponse{
					Models: []ollamaLocalModel{
						{Name: "llama3:latest", Model: "llama3:latest"},
						{Name: "mistral:7b", Model: "mistral:7b"},
					},
				},
				statusCode: http.StatusOK,
				wantCount:  2,
			},
			{
				name:       "empty model list",
				response:   ollamaTagsResponse{Models: []ollamaLocalModel{}},
				statusCode: http.StatusOK,
				wantCount:  0,
			},
			{
				name:       "server error",
				statusCode: http.StatusInternalServerError,
				wantErr:    true,
			},
		}

		for _, tt := range tests {
			t.Run(tt.name, func(t *testing.T) {
				server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
					if r.URL.Path != "/api/tags" {
						t.Errorf("unexpected path: %s", r.URL.Path)
					}
					if r.Method != http.MethodGet {
						t.Errorf("unexpected method: %s", r.Method)
					}
					w.WriteHeader(tt.statusCode)
					if tt.statusCode == http.StatusOK {
						json.NewEncoder(w).Encode(tt.response)
					}
				}))
				defer server.Close()

				models, err := listLocalModels(context.Background(), server.URL)
				if (err != nil) != tt.wantErr {
					t.Errorf("listLocalModels() error = %v, wantErr %v", err, tt.wantErr)
					return
				}
				if !tt.wantErr && len(models) != tt.wantCount {
					t.Errorf("listLocalModels() returned %d models, want %d", len(models), tt.wantCount)
				}
			})
		}
	})

	t.Run("ListActions", func(t *testing.T) {
		t.Run("filters embed models", func(t *testing.T) {
			response := ollamaTagsResponse{
				Models: []ollamaLocalModel{
					{Name: "llama3:latest", Model: "llama3:latest"},
					{Name: "nomic-embed-text:latest", Model: "nomic-embed-text:latest"},
					{Name: "moondream:v2", Model: "moondream:v2"},
				},
			}

			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				json.NewEncoder(w).Encode(response)
			}))
			defer server.Close()

			o := newTestOllama(server.URL)
			actions := o.ListActions(context.Background())

			if len(actions) != 2 {
				t.Fatalf("ListActions() returned %d actions, want 2", len(actions))
			}

			names := make(map[string]bool)
			for _, a := range actions {
				names[a.Name] = true
			}
			if !names["ollama/llama3:latest"] {
				t.Error("ListActions() missing ollama/llama3:latest")
			}
			if !names["ollama/moondream:v2"] {
				t.Error("ListActions() missing ollama/moondream:v2")
			}
			if names["ollama/nomic-embed-text:latest"] {
				t.Error("ListActions() should have filtered out embed model")
			}
		})

		t.Run("server unreachable", func(t *testing.T) {
			o := newTestOllama("http://localhost:0")
			actions := o.ListActions(context.Background())
			if actions != nil {
				t.Errorf("ListActions() should return nil when server is unreachable, got %v", actions)
			}
		})
	})

	t.Run("ResolveAction", func(t *testing.T) {
		o := newTestOllama("http://localhost:11434")

		t.Run("model action type", func(t *testing.T) {
			action := o.ResolveAction(api.ActionTypeModel, "llama3:latest")
			if action == nil {
				t.Fatal("ResolveAction() returned nil for model type")
			}
			desc := action.Desc()
			if desc.Name != "ollama/llama3:latest" {
				t.Errorf("ResolveAction() name = %q, want %q", desc.Name, "ollama/llama3:latest")
			}
		})

		t.Run("non-model action type", func(t *testing.T) {
			action := o.ResolveAction(api.ActionTypeExecutablePrompt, "llama3:latest")
			if action != nil {
				t.Error("ResolveAction() should return nil for non-model action type")
			}
		})
	})

	t.Run("newModel", func(t *testing.T) {
		o := newTestOllama("http://localhost:11434")
		model := o.newModel("test-model", ai.ModelOptions{Supports: &defaultOllamaSupports})
		if model == nil {
			t.Fatal("newModel() returned nil")
		}
		action, ok := model.(api.Action)
		if !ok {
			t.Fatal("newModel() result does not implement api.Action")
		}
		desc := action.Desc()
		if desc.Name != "ollama/test-model" {
			t.Errorf("newModel() name = %q, want %q", desc.Name, "ollama/test-model")
		}
	})
}
