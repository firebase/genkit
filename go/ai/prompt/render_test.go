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
	"strings"
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/google/go-cmp/cmp"
)

type HelloPromptInput struct {
	Name string
}

var promptModel = ai.DefineModel(r, "test", "chat",
	&ai.ModelInfo{Supports: &ai.ModelInfoSupports{
		Tools:      true,
		Multiturn:  true,
		ToolChoice: true,
		SystemRole: true,
	}}, func(ctx context.Context, gr *ai.ModelRequest, msc ai.ModelStreamCallback) (*ai.ModelResponse, error) {
		toolCalled := false
		for _, msg := range gr.Messages {
			if msg.Content[0].IsToolResponse() {
				toolCalled = true
			}
		}

		if !toolCalled && len(gr.Tools) == 1 {
			part := ai.NewToolRequestPart(&ai.ToolRequest{
				Name:  "testTool",
				Input: map[string]any{"Test": "Bar"},
			})

			return &ai.ModelResponse{
				Request: gr,
				Message: &ai.Message{
					Role:    ai.RoleModel,
					Content: []*ai.Part{part},
				},
			}, nil
		}

		if msc != nil {
			msc(ctx, &ai.ModelResponseChunk{
				Content: []*ai.Part{ai.NewTextPart("3!")},
			})
			msc(ctx, &ai.ModelResponseChunk{
				Content: []*ai.Part{ai.NewTextPart("2!")},
			})
			msc(ctx, &ai.ModelResponseChunk{
				Content: []*ai.Part{ai.NewTextPart("1!")},
			})
		}

		textResponse := ""
		var contentTexts []string
		for _, m := range gr.Messages {
			if m.Role != ai.RoleUser && m.Role != ai.RoleModel {
				textResponse += fmt.Sprintf("%s: ", m.Role)
			}

			if m.Role == ai.RoleTool {
				contentTexts = append(contentTexts, m.Content[0].ToolResponse.Output.(string))
			}

			for _, c := range m.Content {
				contentTexts = append(contentTexts, c.Text)
			}
		}

		textResponse += strings.Join(contentTexts, "; ")
		textResponse += "; config: " + base.PrettyJSONString(gr.Config)
		textResponse += "; context: " + base.PrettyJSONString(gr.Context)

		return &ai.ModelResponse{
			Request: gr,
			Message: ai.NewModelTextMessage(fmt.Sprintf("Echo: %s", textResponse)),
		}, nil
	})

func TestValidPrompt(t *testing.T) {
	var tests = []struct {
		name           string
		model          ai.Model
		systemText     string
		systemFn       PromptFn
		promptText     string
		promptFn       PromptFn
		messages       []*ai.Message
		messagesFn     MessagesFn
		tools          []ai.Tool
		config         *ai.GenerationCommonConfig
		inputType      any
		input          any
		executeOptions []GenerateOption
		wantTextOutput string
		wantGenerated  *ai.ModelRequest
		state          any
		only           bool
	}{
		{
			name:       "user and system prompt, basic",
			model:      promptModel,
			config:     &ai.GenerationCommonConfig{Temperature: 11},
			inputType:  HelloPromptInput{},
			systemText: "say hello",
			promptText: "my name is foo",
			input:      HelloPromptInput{Name: "foo"},
			executeOptions: []GenerateOption{
				WithInput(HelloPromptInput{Name: "foo"}),
			},
			wantTextOutput: "Echo: system: say hello; my name is foo; config: {\n  \"temperature\": 11\n}; context: null",
			wantGenerated: &ai.ModelRequest{
				Config: &ai.GenerationCommonConfig{
					Temperature: 11,
				},
				Output:     &ai.ModelRequestOutput{},
				ToolChoice: "required",
				Messages: []*ai.Message{
					{
						Role:    ai.RoleSystem,
						Content: []*ai.Part{ai.NewTextPart("say hello")},
					},
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("my name is foo")},
					},
				},
			},
		},
		{
			name:      "user and system prompt, functions",
			model:     promptModel,
			config:    &ai.GenerationCommonConfig{Temperature: 11},
			inputType: HelloPromptInput{},
			systemFn: func(ctx context.Context, input any) (string, error) {
				return "say hello to {{Name}}", nil
			},
			promptFn: func(ctx context.Context, input any) (string, error) {
				return "my name is {{Name}}", nil
			},
			input: HelloPromptInput{Name: "foo"},
			executeOptions: []GenerateOption{
				WithInput(HelloPromptInput{Name: "foo"}),
			},
			wantTextOutput: "Echo: system: say hello to foo; my name is foo; config: {\n  \"temperature\": 11\n}; context: null",
			wantGenerated: &ai.ModelRequest{
				Config: &ai.GenerationCommonConfig{
					Temperature: 11,
				},
				Output:     &ai.ModelRequestOutput{},
				ToolChoice: "required",
				Messages: []*ai.Message{
					{
						Role:    ai.RoleSystem,
						Content: []*ai.Part{ai.NewTextPart("say hello to foo")},
					},
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("my name is foo")},
					},
				},
			},
		},
		{
			name:       "messages prompt, basic",
			model:      promptModel,
			config:     &ai.GenerationCommonConfig{Temperature: 11},
			inputType:  HelloPromptInput{},
			systemText: "say hello",
			promptText: "my name is foo",
			messages: []*ai.Message{
				{
					Role:    ai.RoleUser,
					Content: []*ai.Part{ai.NewTextPart("you're history")},
				}},
			input: HelloPromptInput{Name: "foo"},
			executeOptions: []GenerateOption{
				WithInput(HelloPromptInput{Name: "foo"}),
			},
			wantTextOutput: "Echo: system: say hello; you're history; my name is foo; config: {\n  \"temperature\": 11\n}; context: null",
			wantGenerated: &ai.ModelRequest{
				Config: &ai.GenerationCommonConfig{
					Temperature: 11,
				},
				Output:     &ai.ModelRequestOutput{},
				ToolChoice: "required",
				Messages: []*ai.Message{
					{
						Role:    ai.RoleSystem,
						Content: []*ai.Part{ai.NewTextPart("say hello")},
					},
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("you're history")},
					},
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("my name is foo")},
					},
				},
			},
		},
		{
			name:       "messages prompt, function",
			model:      promptModel,
			config:     &ai.GenerationCommonConfig{Temperature: 11},
			inputType:  HelloPromptInput{},
			systemText: "say hello",
			promptText: "my name is foo",
			messagesFn: func(ctx context.Context, input any) ([]*ai.Message, error) {
				return []*ai.Message{
					{
						Role:    ai.RoleModel,
						Content: []*ai.Part{ai.NewTextPart("your name is {{Name}}")},
					}}, nil
			},
			input: HelloPromptInput{Name: "foo"},
			executeOptions: []GenerateOption{
				WithInput(HelloPromptInput{Name: "foo"}),
			},
			wantTextOutput: "Echo: system: say hello; your name is foo; my name is foo; config: {\n  \"temperature\": 11\n}; context: null",
			wantGenerated: &ai.ModelRequest{
				Config: &ai.GenerationCommonConfig{
					Temperature: 11,
				},
				Output:     &ai.ModelRequestOutput{},
				ToolChoice: "required",
				Messages: []*ai.Message{
					{
						Role:    ai.RoleSystem,
						Content: []*ai.Part{ai.NewTextPart("say hello")},
					},
					{
						Role:    ai.RoleModel,
						Content: []*ai.Part{ai.NewTextPart("your name is foo")},
					},
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("my name is foo")},
					},
				},
			},
		},
		{
			name:       "messages prompt, input struct",
			model:      promptModel,
			config:     &ai.GenerationCommonConfig{Temperature: 11},
			inputType:  HelloPromptInput{},
			systemText: "say hello",
			promptText: "my name is foo",
			messagesFn: func(ctx context.Context, input any) ([]*ai.Message, error) {
				var p HelloPromptInput
				switch param := input.(type) {
				case HelloPromptInput:
					p = param
				}
				return []*ai.Message{
					{
						Role:    ai.RoleModel,
						Content: []*ai.Part{ai.NewTextPart(fmt.Sprintf("your name is %s", p.Name))},
					}}, nil
			},
			input: HelloPromptInput{Name: "foo"},
			executeOptions: []GenerateOption{
				WithInput(HelloPromptInput{Name: "foo"}),
			},
			wantTextOutput: "Echo: system: say hello; your name is foo; my name is foo; config: {\n  \"temperature\": 11\n}; context: null",
			wantGenerated: &ai.ModelRequest{
				Config: &ai.GenerationCommonConfig{
					Temperature: 11,
				},
				Output:     &ai.ModelRequestOutput{},
				ToolChoice: "required",
				Messages: []*ai.Message{
					{
						Role:    ai.RoleSystem,
						Content: []*ai.Part{ai.NewTextPart("say hello")},
					},
					{
						Role:    ai.RoleModel,
						Content: []*ai.Part{ai.NewTextPart("your name is foo")},
					},
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("my name is foo")},
					},
				},
			},
		},
		{
			name:       "prompt with tools",
			model:      promptModel,
			config:     &ai.GenerationCommonConfig{Temperature: 11},
			inputType:  HelloPromptInput{},
			systemText: "say hello",
			promptText: "my name is foo",
			tools:      []ai.Tool{testTool("testTool")},
			input:      HelloPromptInput{Name: "foo"},
			executeOptions: []GenerateOption{
				WithInput(HelloPromptInput{Name: "foo"}),
			},
			wantTextOutput: "Echo: system: tool: say hello; my name is foo; ; Bar; ; config: {\n  \"temperature\": 11\n}; context: null",
			wantGenerated: &ai.ModelRequest{
				Config: &ai.GenerationCommonConfig{
					Temperature: 11,
				},
				Output:     &ai.ModelRequestOutput{},
				ToolChoice: "required",
				Messages: []*ai.Message{
					{
						Role:    ai.RoleSystem,
						Content: []*ai.Part{ai.NewTextPart("say hello")},
					},
					{
						Role:    ai.RoleUser,
						Content: []*ai.Part{ai.NewTextPart("my name is foo")},
					},
					{
						Role:    ai.RoleModel,
						Content: []*ai.Part{ai.NewToolRequestPart(&ai.ToolRequest{Name: "testTool", Input: map[string]any{"Test": "Bar"}})},
					},
					{
						Role:    ai.RoleTool,
						Content: []*ai.Part{ai.NewToolResponsePart(&ai.ToolResponse{Output: "Bar"})},
					},
				},
				Tools: []*ai.ToolDefinition{
					{
						Name:        "testTool",
						Description: "use when need to execute a test",
						InputSchema: map[string]any{
							"additionalProperties": bool(false),
							"properties":           map[string]any{"Test": map[string]any{"type": string("string")}},
							"required":             []any{string("Test")},
							"type":                 string("object"),
						},
						OutputSchema: map[string]any{"type": string("string")},
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
			var opts []PromptOption
			opts = append(opts, WithInputType(test.inputType))
			opts = append(opts, WithDefaultModel(test.model))
			opts = append(opts, WithDefaultConfig(test.config))
			opts = append(opts, WithDefaultToolChoice(ai.ToolChoiceRequired))
			opts = append(opts, WithTools(test.tools...))
			opts = append(opts, WithDefaultMaxTurns(1))

			if test.systemText != "" {
				opts = append(opts, WithSystemText(test.systemText))
			} else {
				opts = append(opts, WithSystemFn(test.systemFn))
			}

			if test.promptText != "" {
				opts = append(opts, WithPromptText(test.promptText))
			} else {
				opts = append(opts, WithPromptFn(test.promptFn))
			}

			if test.messages != nil {
				opts = append(opts, WithDefaultMessages(test.messages))
			} else {
				opts = append(opts, WithDefaultMessagesFn(test.messagesFn))
			}

			p, err := Define(
				r,
				"prompts",
				test.name,
				opts...,
			)
			if err != nil {
				t.Fatal(err)
			}

			// Call model
			output, err := p.Execute(context.Background(), test.executeOptions...)
			if err != nil {
				t.Fatal(err)
			}

			if output.Text() != test.wantTextOutput {
				t.Errorf("got %q want %q", output.Text(), test.wantTextOutput)
			}

			if diff := cmp.Diff(test.wantGenerated, output.Request, cmp.Comparer(cmpPart)); diff != "" {
				t.Errorf("mismatch (-want, +got):\n%s", diff)
			}
		})
	}
}
