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

package ai

import (
	"strings"
	"testing"
)

func TestValidCandidate(t *testing.T) {
	t.Parallel()

	t.Run("Valid candidate with text format", func(t *testing.T) {
		candidate := &Candidate{
			Message: &Message{
				Content: []*Part{
					NewTextPart("Hello, World!"),
				},
			},
		}
		outputSchema := &GenerateRequestOutput{
			Format: OutputFormatText,
		}
		_, err := validCandidate(candidate, outputSchema)
		if err != nil {
			t.Fatal(err)
		}
	})

	t.Run("Valid candidate with JSON format and matching schema", func(t *testing.T) {
		json := `{
			"name": "John",
			"age": 30,
			"address": {
				"street": "123 Main St",
				"city": "New York",
				"country": "USA"
			}
		}`
		candidate := &Candidate{
			Message: &Message{
				Content: []*Part{
					NewTextPart(JSONMarkdown(json)),
				},
			},
		}
		outputSchema := &GenerateRequestOutput{
			Format: OutputFormatJSON,
			Schema: map[string]any{
				"type":     "object",
				"required": []string{"name", "age", "address"},
				"properties": map[string]any{
					"name": map[string]any{"type": "string"},
					"age":  map[string]any{"type": "integer"},
					"address": map[string]any{
						"type":     "object",
						"required": []string{"street", "city", "country"},
						"properties": map[string]any{
							"street":  map[string]any{"type": "string"},
							"city":    map[string]any{"type": "string"},
							"country": map[string]any{"type": "string"},
						},
					},
					"phone": map[string]any{"type": "string"},
				},
			},
		}
		candidate, err := validCandidate(candidate, outputSchema)
		if err != nil {
			t.Fatal(err)
		}
		text, err := candidate.Text()
		if err != nil {
			t.Fatal(err)
		}
		if text != json {
			t.Fatalf("got %q, want %q", json, text)
		}
	})

	t.Run("Invalid candidate with JSON format and non-matching schema", func(t *testing.T) {
		candidate := &Candidate{
			Message: &Message{
				Content: []*Part{
					NewTextPart(JSONMarkdown(`{"name": "John", "age": "30"}`)),
				},
			},
		}
		outputSchema := &GenerateRequestOutput{
			Format: OutputFormatJSON,
			Schema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"name": map[string]any{"type": "string"},
					"age":  map[string]any{"type": "integer"},
				},
			},
		}
		_, err := validCandidate(candidate, outputSchema)
		errorContains(t, err, "data did not match expected schema")
	})

	t.Run("Candidate with invalid JSON", func(t *testing.T) {
		candidate := &Candidate{
			Message: &Message{
				Content: []*Part{
					NewTextPart(JSONMarkdown(`{"name": "John", "age": 30`)), // Missing trailing }.
				},
			},
		}
		outputSchema := &GenerateRequestOutput{
			Format: OutputFormatJSON,
		}
		_, err := validCandidate(candidate, outputSchema)
		errorContains(t, err, "data is not valid JSON")
	})

	t.Run("Candidate with no message", func(t *testing.T) {
		candidate := &Candidate{}
		outputSchema := &GenerateRequestOutput{
			Format: OutputFormatJSON,
		}
		_, err := validCandidate(candidate, outputSchema)
		errorContains(t, err, "candidate has no message")
	})

	t.Run("Candidate with message but no content", func(t *testing.T) {
		candidate := &Candidate{
			Message: &Message{},
		}
		outputSchema := &GenerateRequestOutput{
			Format: OutputFormatJSON,
		}
		_, err := validCandidate(candidate, outputSchema)
		errorContains(t, err, "candidate message has no content")
	})

	t.Run("Candidate contains unexpected field", func(t *testing.T) {
		candidate := &Candidate{
			Message: &Message{
				Content: []*Part{
					NewTextPart(JSONMarkdown(`{"name": "John", "height": 190}`)),
				},
			},
		}
		outputSchema := &GenerateRequestOutput{
			Format: OutputFormatJSON,
			Schema: map[string]any{
				"type": "object",
				"properties": map[string]any{
					"name": map[string]any{"type": "string"},
					"age":  map[string]any{"type": "integer"},
				},
				"additionalProperties": false,
			},
		}
		_, err := validCandidate(candidate, outputSchema)
		errorContains(t, err, "data did not match expected schema")
	})

	t.Run("Invalid expected schema", func(t *testing.T) {
		candidate := &Candidate{
			Message: &Message{
				Content: []*Part{
					NewTextPart(JSONMarkdown(`{"name": "John", "age": 30}`)),
				},
			},
		}
		outputSchema := &GenerateRequestOutput{
			Format: OutputFormatJSON,
			Schema: map[string]any{
				"type": "invalid",
			},
		}
		_, err := validCandidate(candidate, outputSchema)
		errorContains(t, err, "failed to validate data against expected schema")
	})
}

func JSONMarkdown(text string) string {
	return "```json\n" + text + "\n```"
}

func errorContains(t *testing.T, err error, want string) {
	t.Helper()
	if err == nil {
		t.Error("got nil, want error")
	} else if !strings.Contains(err.Error(), want) {
		t.Errorf("got error message %q, want it to contain %q", err, want)
	}
}
