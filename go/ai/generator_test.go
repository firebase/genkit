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
	"context"
	"math"
	"strings"
	"testing"

	test_utils "github.com/firebase/genkit/go/tests/utils"
	"github.com/google/go-cmp/cmp"
)

// structured output
type GameCharacter struct {
	Name      string
	Backstory string
}

var echoModel = DefineModel("test", "echo", nil, func(ctx context.Context, gr *GenerateRequest, msc ModelStreamingCallback) (*GenerateResponse, error) {
	if msc != nil {
		msc(ctx, &GenerateResponseChunk{
			Index:   0,
			Content: []*Part{NewTextPart("stream!")},
		})
	}
	return &GenerateResponse{
		Request: gr,
		Candidates: []*Candidate{
			{
				Message: NewUserTextMessage(gr.Messages[0].Content[0].Text),
			},
		},
	}, nil
})

// with tools
var gablorkenTool = DefineTool("gablorken", "use when need to calculate a gablorken",
	func(ctx context.Context, input struct {
		Value float64
		Over  float64
	}) (float64, error) {
		return math.Pow(input.Value, input.Over), nil
	},
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
		text := candidate.Text()
		if strings.TrimSpace(text) != strings.TrimSpace(json) {
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

func TestGenerate(t *testing.T) {
	t.Run("constructs request", func(t *testing.T) {
		charJson := "{\"Name\": \"foo\", \"Backstory\": \"bar\"}"
		wantText := charJson
		wantRequest := &GenerateRequest{
			Messages: []*Message{
				{
					Content: []*Part{
						{ContentType: "plain/text", Text: charJson},
						{
							ContentType: "plain/text",
							Text:        "!!Ignored!!", // structured output prompt, noisy, ignored
						},
					}, Role: "user"},
			},
			Config:     GenerationCommonConfig{Temperature: 1},
			Candidates: 3,
			Context:    []any{[]any{string("Banana")}},
			Output: &GenerateRequestOutput{
				Format: "json",
				Schema: map[string]any{
					"$id":                  string("https://github.com/firebase/genkit/go/ai/game-character"),
					"additionalProperties": bool(false),
					"properties": map[string]any{
						"Backstory": map[string]any{"type": string("string")},
						"Name":      map[string]any{"type": string("string")},
					},
					"required": []any{string("Name"), string("Backstory")},
					"type":     string("object"),
				},
			},
			Tools: []*ToolDefinition{
				{
					Description: "use when need to calculate a gablorken",
					InputSchema: map[string]any{
						"additionalProperties": bool(false),
						"properties": map[string]any{
							"Over":  map[string]any{"type": string("number")},
							"Value": map[string]any{"type": string("number")},
						},
						"required": []any{
							string("Value"),
							string("Over"),
						},
						"type": string("object"),
					},
					Name:         "gablorken",
					OutputSchema: map[string]any{"type": string("number")},
				},
			},
		}

		wantStreamText := "stream!"
		streamText := ""
		res, err := echoModel.Generate(context.Background(),
			WithTextPrompt(charJson),
			WithConfig(GenerationCommonConfig{
				Temperature: 1,
			}),
			WithCandidates(3),
			WithContext([]any{"Banana"}),
			WithOutputSchema(&GameCharacter{}),
			WithTools(gablorkenTool),
			WithStreaming(func(ctx context.Context, grc *GenerateResponseChunk) error {
				streamText += grc.Text()
				return nil
			}),
		)
		if err != nil {
			t.Error(err)
		}
		gotText := res.Text()
		if diff := cmp.Diff(gotText, wantText); diff != "" {
			t.Errorf("Text() diff (+got -want):\n%s", diff)
		}
		if diff := cmp.Diff(streamText, wantStreamText); diff != "" {
			t.Errorf("Text() diff (+got -want):\n%s", diff)
		}
		if diff := cmp.Diff(res.Request, wantRequest, test_utils.IgnoreNoisyParts([]string{
			"{*ai.GenerateRequest}.Messages[0].Content[1].Text",
		})); diff != "" {
			t.Errorf("Request diff (+got -want):\n%s", diff)
		}
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
