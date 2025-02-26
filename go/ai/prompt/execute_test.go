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

package prompt

import (
	"context"
	"fmt"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/google/go-cmp/cmp"
)

func testGenerate(ctx context.Context, req *ai.ModelRequest, cb func(context.Context, *ai.ModelResponseChunk) error) (*ai.ModelResponse, error) {
	input := req.Messages[0].Content[0].Text
	output := fmt.Sprintf("AI reply to %q", input)

	if req.Output.Format == "json" {
		output = `{"text": "AI reply to JSON"}`
	}

	if cb != nil {
		cb(ctx, &ai.ModelResponseChunk{
			Content: []*ai.Part{ai.NewTextPart("stream!")},
		})
	}

	r := &ai.ModelResponse{
		Message: &ai.Message{
			Content: []*ai.Part{
				ai.NewTextPart(output),
			},
		},
		Request: req,
	}
	return r, nil
}

func TestOptionsPatternExecute(t *testing.T) {
	testModel := ai.DefineModel(r, "options", "test", nil, testGenerate)

	t.Run("Streaming", func(t *testing.T) {
		p, err := Define(r, "TestExecute", "TestExecute", WithInputType(InputOutput{}), WithPromptText("TestExecute"))
		if err != nil {
			t.Fatal(err)
		}

		streamText := ""
		resp, err := p.Execute(
			context.Background(),
			WithInput(InputOutput{
				Text: "TestExecute",
			}),
			WithStreaming(func(ctx context.Context, grc *ai.ModelResponseChunk) error {
				streamText += grc.Text()
				return nil
			}),
			WithModel(testModel),
			WithContext([]any{"context"}),
		)
		if err != nil {
			t.Fatal(err)
		}

		assertResponse(t, resp, `AI reply to "TestExecute"`)
		if diff := cmp.Diff(streamText, "stream!"); diff != "" {
			t.Errorf("Text() diff (+got -want):\n%s", diff)
		}
	})

	t.Run("WithModelName", func(t *testing.T) {
		p, err := Define(r, "TestModelname", "TestModelname", WithInputType(InputOutput{}), WithPromptText("TestModelname"))
		if err != nil {
			t.Fatal(err)
		}

		resp, err := p.Execute(
			context.Background(),
			WithInput(InputOutput{
				Text: "testing",
			}),
			WithModelName("options/test"),
		)
		if err != nil {
			t.Fatal(err)
		}

		assertResponse(t, resp, `AI reply to "TestModelname"`)
	})
}

func TestExecuteOptions(t *testing.T) {
	p, err := Define(r, "TestWithGenerate", "TestWithGenerate", WithInputType(InputOutput{}))
	if err != nil {
		t.Fatal(err)
	}

	var tests = []struct {
		name string
		with GenerateOption
	}{
		{
			name: "WithInput",
			with: WithInput(map[string]any{"test": "test"}),
		},
		{
			name: "WithConfig",
			with: WithConfig(&ai.GenerationCommonConfig{}),
		},
		{
			name: "WithContext",
			with: WithContext([]any{"context"}),
		},
		{
			name: "WithModelName",
			with: WithModelName("defineoptions/test"),
		},
		{
			name: "WithModel",
			with: WithModel(testModel),
		},
		{
			name: "WithMessages",
			with: WithMessages(
				[]*ai.Message{{
					Role:    ai.RoleSystem,
					Content: []*ai.Part{ai.NewTextPart("say hello")},
				}},
			),
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			_, err = p.Execute(
				context.Background(),
				test.with,
			)

			if err == nil {
				t.Errorf("%s could be set twice", test.name)
			}
		})
	}
}

func TestDefaultsOverride(t *testing.T) {
	msgsFn := func(ctx context.Context, input any) ([]*ai.Message, error) {
		return []*ai.Message{
			{
				Role:    ai.RoleUser,
				Content: []*ai.Part{ai.NewTextPart("you're history")},
			}}, nil
	}

	var tests = []struct {
		name           string
		define         []PromptOption
		execute        []GenerateOption
		wantTextOutput string
		wantGenerated  *ai.ModelRequest
	}{
		{
			name: "Messages",
			define: []PromptOption{
				WithPromptText("my name is default"),
				WithDefaultMessages([]*ai.Message{
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("you're default")},
					}}),
				WithDefaultModel(promptModel),
			},
			execute: []GenerateOption{
				WithConfig(&ai.GenerationCommonConfig{Temperature: 12}),
				WithMessages([]*ai.Message{
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("you're history")},
					}}),
			},
			wantTextOutput: "Echo: you're history; my name is default; config: {\n  \"temperature\": 12\n}; context: null",
			wantGenerated: &ai.ModelRequest{
				Config: &ai.GenerationCommonConfig{
					Temperature: 12,
				},
				Output: &ai.ModelRequestOutput{},
				Messages: []*ai.Message{
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("you're history")},
					},
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("my name is default")},
					},
				},
			},
		},
		{
			name: "MessagesFn",
			define: []PromptOption{
				WithPromptText("my name is default"),
				WithDefaultMessages([]*ai.Message{
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("you're default")},
					}}),
				WithDefaultModel(promptModel),
			},
			execute: []GenerateOption{
				WithConfig(&ai.GenerationCommonConfig{Temperature: 12}),
				WithMessagesFn(msgsFn),
			},
			wantTextOutput: "Echo: you're history; my name is default; config: {\n  \"temperature\": 12\n}; context: null",
			wantGenerated: &ai.ModelRequest{
				Config: &ai.GenerationCommonConfig{
					Temperature: 12,
				},
				Output: &ai.ModelRequestOutput{},
				Messages: []*ai.Message{
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("you're history")},
					},
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("my name is default")},
					},
				},
			},
		},
		{
			name: "Config",
			define: []PromptOption{
				WithPromptText("my name is foo"),
				WithDefaultConfig(&ai.GenerationCommonConfig{Temperature: 11}),
				WithDefaultModel(promptModel),
			},
			execute: []GenerateOption{
				WithConfig(&ai.GenerationCommonConfig{Temperature: 12}),
			},
			wantTextOutput: "Echo: my name is foo; config: {\n  \"temperature\": 12\n}; context: null",
			wantGenerated: &ai.ModelRequest{
				Config: &ai.GenerationCommonConfig{
					Temperature: 12,
				},
				Output: &ai.ModelRequestOutput{},
				Messages: []*ai.Message{
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("my name is foo")},
					},
				},
			},
		},
		{
			name: "Model",
			define: []PromptOption{
				WithPromptText("my name is foo"),
				WithDefaultModel(promptModel),
			},
			execute: []GenerateOption{
				WithConfig(&ai.GenerationCommonConfig{Temperature: 12}),
				WithModel(testModel),
			},
			wantTextOutput: "AI reply to \"my name is foo\"",
			wantGenerated: &ai.ModelRequest{
				Config: &ai.GenerationCommonConfig{
					Temperature: 12,
				},
				Output: &ai.ModelRequestOutput{},
				Messages: []*ai.Message{
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("my name is foo")},
					},
				},
			},
		},
		{
			name: "ModelName",
			define: []PromptOption{
				WithPromptText("my name is foo"),
				WithDefaultModelName("test/chat"),
			},
			execute: []GenerateOption{
				WithConfig(&ai.GenerationCommonConfig{Temperature: 12}),
				WithModelName("defineoptions/test"),
			},
			wantTextOutput: "AI reply to \"my name is foo\"",
			wantGenerated: &ai.ModelRequest{
				Config: &ai.GenerationCommonConfig{
					Temperature: 12,
				},
				Output: &ai.ModelRequestOutput{},
				Messages: []*ai.Message{
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("my name is foo")},
					},
				},
			},
		},
	}

	cmpPart := func(a, b *ai.Part) bool {
		if a.IsText() != b.IsText() {
			return false
		}
		if a.Text != b.Text {
			return false
		}
		if a.ContentType != b.ContentType {
			return false
		}
		return true
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			p, err := Define(
				r,
				"prompts",
				test.name,
				test.define...,
			)
			if err != nil {
				t.Fatal(err)
			}

			output, err := p.Execute(
				context.Background(),
				test.execute...,
			)
			if err != nil {
				t.Fatal(err)
			}

			if diff := cmp.Diff(test.wantGenerated, output.Request, cmp.Comparer(cmpPart)); diff != "" {
				t.Errorf("mismatch (-want, +got):\n%s", diff)
			}

			if output.Text() != test.wantTextOutput {
				t.Errorf("got %q want %q", output.Text(), test.wantTextOutput)
			}
		})
	}
}

func assertResponse(t *testing.T, resp *ai.ModelResponse, want string) {
	if resp.Message == nil {
		t.Fatal("response has candidate with no message")
	}
	if len(resp.Message.Content) != 1 {
		t.Errorf("got %d message parts, want 1", len(resp.Message.Content))
		if len(resp.Message.Content) < 1 {
			t.FailNow()
		}
	}
	got := resp.Message.Content[0].Text
	if got != want {
		t.Errorf("fake model replied with %q, want %q", got, want)
	}
}
