// Copyright 2026 Google LLC
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
	"testing"
)

func TestResolveModelID(t *testing.T) {
	availableModels := []string{
		"claude-3-opus-20240229",
		"claude-3-sonnet-20240229",
		"claude-3-haiku-20240307",
		"claude-3-5-sonnet-20240620",
		"claude-3-5-sonnet-20241022",
		"claude-3-5-haiku-20241022",
	}

	tests := []struct {
		input    string
		expected string
		found    bool
	}{
		// Exact match
		{"claude-3-opus-20240229", "claude-3-opus-20240229", true},
		// Alias for Sonnet 3.5 (should pick latest)
		{"claude-3-5-sonnet", "claude-3-5-sonnet-20241022", true},
		// Alias for Haiku 3.5
		{"claude-3-5-haiku", "claude-3-5-haiku-20241022", true},
		// Alias for Sonnet 3
		{"claude-3-sonnet", "claude-3-sonnet-20240229", true},
		// Non-existent
		{"claude-2", "", false},
	}

	for _, tt := range tests {
		t.Run(tt.input, func(t *testing.T) {
			got, found := resolveModelID(tt.input, availableModels)
			if found != tt.found {
				t.Errorf("found = %v, want %v", found, tt.found)
			}
			if got != tt.expected {
				t.Errorf("got = %q, want %q", got, tt.expected)
			}
		})
	}
}
