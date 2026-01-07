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
	"reflect"
	"testing"

	"github.com/firebase/genkit/go/ai"
)

func TestOllamaChatRequest_ApplyOptions(t *testing.T) {
	seed := 42
	temp := 0.7

	tests := []struct {
		name    string
		cfg     any
		want    *ollamaChatRequest
		wantErr bool
	}{
		{
			name: "GenerateContentConfig pointer",
			cfg: &GenerateContentConfig{
				Seed:        &seed,
				Temperature: &temp,
				Think:       true,
			},
			want: &ollamaChatRequest{
				Think: true,
				Options: map[string]any{
					"seed":        seed,
					"temperature": temp,
				},
			},
		},
		{
			name: "GenerateContentConfig value",
			cfg: GenerateContentConfig{
				Seed:  &seed,
				Think: true,
			},
			want: &ollamaChatRequest{
				Think: true,
				Options: map[string]any{
					"seed": seed,
				},
			},
		},
		{
			name: "map[string]any with opts only",
			cfg: map[string]any{
				"temperature": 0.5,
				"top_k":       40,
			},
			want: &ollamaChatRequest{
				Options: map[string]any{
					"temperature": 0.5,
					"top_k":       40,
				},
			},
		},
		{
			name: "map[string]any with top level fields",
			cfg: map[string]any{
				"think":      true,
				"keep_alive": "10m",
			},
			want: &ollamaChatRequest{
				Think:     true,
				KeepAlive: "10m",
			},
		},
		{
			name: "map[string]any mixed main and opts",
			cfg: map[string]any{
				"temperature": 0.9,
				"think":       true,
			},
			want: &ollamaChatRequest{
				Think: true,
				Options: map[string]any{
					"temperature": 0.9,
				},
			},
		},
		{
			name: "GenerationCommonConfig pointer",
			cfg: &ai.GenerationCommonConfig{
				Temperature: temp,
				TopK:        1,
				TopP:        2.0,
			},
			want: &ollamaChatRequest{
				Options: map[string]any{
					"temperature": temp,
					"top_k":       1,
					"top_p":       2.0,
				},
			},
		},
		{
			name: "nil config",
			cfg:  nil,
			want: &ollamaChatRequest{},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := &ollamaChatRequest{}

			err := req.ApplyOptions(tt.cfg)

			if tt.wantErr {
				if err == nil {
					t.Fatalf("expected error, got nil")
				}
				return
			}

			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}

			if !reflect.DeepEqual(req, tt.want) {
				t.Errorf(
					"unexpected result:\nwant: %#v\n got: %#v",
					tt.want,
					req,
				)
			}
		})
	}
}
