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
	"fmt"
	"strings"
	"testing"

	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/internal/registry"
	"github.com/google/go-cmp/cmp"
)

type InputOutput struct {
	Text string `json:"text"`
}

var reg, _ = registry.New()

func testTool(name string) *ToolDef[struct{ Test string }, string] {
	return DefineTool(reg, name, "use when need to execute a test",
		func(ctx *ToolContext, input struct {
			Test string
		}) (string, error) {
			return input.Test, nil
		},
	)
}

var testModel = DefineModel(reg, "defineoptions", "test", nil, testGenerate)

func TestOutputFormat(t *testing.T) {
	var tests = []struct {
		name   string
		output any
		format OutputFormat
		err    bool
	}{
		{
			name:   "mismatch",
			output: InputOutput{},
			format: OutputFormatText,
			err:    true,
		},
		{
			name:   "json",
			output: InputOutput{},
			format: OutputFormatJSON,
			err:    false,
		},
		{
			name:   "text",
			format: OutputFormatText,
			err:    false,
		},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			var err error

			if test.output == nil {
				_, err = DefinePrompt(
					r,
					"aModel",
					"aModel",
					WithInputType(InputOutput{Text: "test"}),
					WithOutputFormat(test.format),
				)
			} else {
				_, err = DefinePrompt(
					r,
					"bModel",
					"bModel",
					WithInputType(InputOutput{Text: "test"}),
					WithOutputType(test.output),
					WithOutputFormat(test.format),
				)
			}
			if err != nil {
				if test.err {
					t.Logf("got expected error %v", err)
					return
				}
				t.Fatal(err)
			}
		})
	}
}

func TestInputFormat(t *testing.T) {
	type hello struct {
		Name string `json:"name"`
	}

	var tests = []struct {
		name         string
		templateText string
		inputType    any
		input        map[string]any
		render       string
	}{
		{
			name:         "noInput",
			templateText: "hello world",
			input:        nil,
			render:       "hello world",
		},
		{
			name:         "structInput",
			templateText: "hello {{name}}",
			inputType:    hello{},
			input:        map[string]any{"name": "world"},
			render:       "hello world",
		},
		{
			name:         "stringInput",
			templateText: "hello {{input}}",
			inputType:    "world",
			input:        map[string]any{"input": "world"},
			render:       "hello world",
		},
		{
			name:         "intInput",
			templateText: "hello {{input}}",
			inputType:    1,
			input:        map[string]any{"input": 1},
			render:       "hello 1",
		},
		{
			name:         "floatInput",
			templateText: "the value of pi is {{input}}",
			inputType:    3.14159,
			input:        map[string]any{"input": 3.14159},
			render:       "the value of pi is 3.14159",
		},
		{
			name:         "mapInput",
			templateText: "hello {{name}}",
			inputType:    map[string]any{"name": "world"},
			input:        map[string]any{"name": "world"},
			render:       "hello world",
		},
		{
			name:         "bool",
			templateText: "that is {{input}}",
			inputType:    true,
			input:        map[string]any{"input": true},
			render:       "that is true",
		},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			var err error
			var p *Prompt

			if test.inputType != nil {
				p, err = DefinePrompt(
					r,
					"provider",
					test.name,
					WithPromptText(test.templateText),
					WithInputType(test.inputType),
				)
			} else {
				p, err = DefinePrompt(
					r,
					"provider",
					"inputFormat",
					WithPromptText(test.templateText),
				)
			}

			if err != nil {
				t.Fatal(err)
			}

			req, err := p.Render(context.Background(), test.input)
			if err != nil {
				t.Fatal(err)
			}

			if req.Messages[0].Content[0].Text != test.render {
				t.Errorf("got %q want %q", req.Messages[0].Content[0].Text, test.render)
			}
		})
	}
}

type HelloPromptInput struct {
	Name string
}

var promptModel = DefineModel(r, "test", "chat",
	&ModelInfo{Supports: &ModelInfoSupports{
		Tools:      true,
		Multiturn:  true,
		ToolChoice: true,
		SystemRole: true,
	}}, func(ctx context.Context, gr *ModelRequest, msc ModelStreamCallback) (*ModelResponse, error) {
		toolCalled := false
		for _, msg := range gr.Messages {
			if msg.Content[0].IsToolResponse() {
				toolCalled = true
			}
		}

		if !toolCalled && len(gr.Tools) == 1 {
			part := NewToolRequestPart(&ToolRequest{
				Name:  "testTool",
				Input: map[string]any{"Test": "Bar"},
			})

			return &ModelResponse{
				Request: gr,
				Message: &Message{
					Role:    RoleModel,
					Content: []*Part{part},
				},
			}, nil
		}

		if msc != nil {
			msc(ctx, &ModelResponseChunk{
				Content: []*Part{NewTextPart("3!")},
			})
			msc(ctx, &ModelResponseChunk{
				Content: []*Part{NewTextPart("2!")},
			})
			msc(ctx, &ModelResponseChunk{
				Content: []*Part{NewTextPart("1!")},
			})
		}

		textResponse := ""
		var contentTexts []string
		for _, m := range gr.Messages {
			if m.Role != RoleUser && m.Role != RoleModel {
				textResponse += fmt.Sprintf("%s: ", m.Role)
			}

			if m.Role == RoleTool {
				contentTexts = append(contentTexts, m.Content[0].ToolResponse.Output.(string))
			}

			for _, c := range m.Content {
				contentTexts = append(contentTexts, c.Text)
			}
		}

		textResponse += strings.Join(contentTexts, "; ")
		textResponse += "; config: " + base.PrettyJSONString(gr.Config)
		textResponse += "; context: " + base.PrettyJSONString(gr.Context)

		return &ModelResponse{
			Request: gr,
			Message: NewModelTextMessage(fmt.Sprintf("Echo: %s", textResponse)),
		}, nil
	})

func TestValidPrompt(t *testing.T) {
	var tests = []struct {
		name           string
		model          Model
		systemText     string
		systemFn       promptFn
		promptText     string
		promptFn       promptFn
		messages       []*Message
		messagesFn     messagesFn
		tools          []Tool
		config         *GenerationCommonConfig
		inputType      any
		input          any
		executeOptions []PromptRequestOption
		wantTextOutput string
		wantGenerated  *ModelRequest
		state          any
		only           bool
	}{
		{
			name:       "user and system prompt, basic",
			model:      promptModel,
			config:     &GenerationCommonConfig{Temperature: 11},
			inputType:  HelloPromptInput{},
			systemText: "say hello",
			promptText: "my name is foo",
			input:      HelloPromptInput{Name: "foo"},
			executeOptions: []PromptRequestOption{
				WithInput(HelloPromptInput{Name: "foo"}),
			},
			wantTextOutput: "Echo: system: say hello; my name is foo; config: {\n  \"temperature\": 11\n}; context: null",
			wantGenerated: &ModelRequest{
				Config: &GenerationCommonConfig{
					Temperature: 11,
				},
				Output:     &ModelRequestOutput{},
				ToolChoice: "required",
				Messages: []*Message{
					{
						Role:    RoleSystem,
						Content: []*Part{NewTextPart("say hello")},
					},
					{
						Role:    RoleUser,
						Content: []*Part{NewTextPart("my name is foo")},
					},
				},
			},
		},
		{
			name:      "user and system prompt, functions",
			model:     promptModel,
			config:    &GenerationCommonConfig{Temperature: 11},
			inputType: HelloPromptInput{},
			systemFn: func(ctx context.Context, input any) (string, error) {
				return "say hello to {{Name}}", nil
			},
			promptFn: func(ctx context.Context, input any) (string, error) {
				return "my name is {{Name}}", nil
			},
			input: HelloPromptInput{Name: "foo"},
			executeOptions: []PromptRequestOption{
				WithInput(HelloPromptInput{Name: "foo"}),
			},
			wantTextOutput: "Echo: system: say hello to foo; my name is foo; config: {\n  \"temperature\": 11\n}; context: null",
			wantGenerated: &ModelRequest{
				Config: &GenerationCommonConfig{
					Temperature: 11,
				},
				Output:     &ModelRequestOutput{},
				ToolChoice: "required",
				Messages: []*Message{
					{
						Role:    RoleSystem,
						Content: []*Part{NewTextPart("say hello to foo")},
					},
					{
						Role:    RoleUser,
						Content: []*Part{NewTextPart("my name is foo")},
					},
				},
			},
		},
		{
			name:       "messages prompt, basic",
			model:      promptModel,
			config:     &GenerationCommonConfig{Temperature: 11},
			inputType:  HelloPromptInput{},
			systemText: "say hello",
			promptText: "my name is foo",
			messages: []*Message{
				{
					Role:    RoleUser,
					Content: []*Part{NewTextPart("you're history")},
				}},
			input: HelloPromptInput{Name: "foo"},
			executeOptions: []PromptRequestOption{
				WithInput(HelloPromptInput{Name: "foo"}),
			},
			wantTextOutput: "Echo: system: say hello; you're history; my name is foo; config: {\n  \"temperature\": 11\n}; context: null",
			wantGenerated: &ModelRequest{
				Config: &GenerationCommonConfig{
					Temperature: 11,
				},
				Output:     &ModelRequestOutput{},
				ToolChoice: "required",
				Messages: []*Message{
					{
						Role:    RoleSystem,
						Content: []*Part{NewTextPart("say hello")},
					},
					{
						Role:    RoleUser,
						Content: []*Part{NewTextPart("you're history")},
					},
					{
						Role:    RoleUser,
						Content: []*Part{NewTextPart("my name is foo")},
					},
				},
			},
		},
		{
			name:       "messages prompt, function",
			model:      promptModel,
			config:     &GenerationCommonConfig{Temperature: 11},
			inputType:  HelloPromptInput{},
			systemText: "say hello",
			promptText: "my name is foo",
			messagesFn: func(ctx context.Context, input any) ([]*Message, error) {
				return []*Message{
					{
						Role:    RoleModel,
						Content: []*Part{NewTextPart("your name is {{Name}}")},
					}}, nil
			},
			input: HelloPromptInput{Name: "foo"},
			executeOptions: []PromptRequestOption{
				WithInput(HelloPromptInput{Name: "foo"}),
			},
			wantTextOutput: "Echo: system: say hello; your name is foo; my name is foo; config: {\n  \"temperature\": 11\n}; context: null",
			wantGenerated: &ModelRequest{
				Config: &GenerationCommonConfig{
					Temperature: 11,
				},
				Output:     &ModelRequestOutput{},
				ToolChoice: "required",
				Messages: []*Message{
					{
						Role:    RoleSystem,
						Content: []*Part{NewTextPart("say hello")},
					},
					{
						Role:    RoleModel,
						Content: []*Part{NewTextPart("your name is foo")},
					},
					{
						Role:    RoleUser,
						Content: []*Part{NewTextPart("my name is foo")},
					},
				},
			},
		},
		{
			name:       "messages prompt, input struct",
			model:      promptModel,
			config:     &GenerationCommonConfig{Temperature: 11},
			inputType:  HelloPromptInput{},
			systemText: "say hello",
			promptText: "my name is foo",
			messagesFn: func(ctx context.Context, input any) ([]*Message, error) {
				var p HelloPromptInput
				switch param := input.(type) {
				case HelloPromptInput:
					p = param
				}
				return []*Message{
					{
						Role:    RoleModel,
						Content: []*Part{NewTextPart(fmt.Sprintf("your name is %s", p.Name))},
					}}, nil
			},
			input: HelloPromptInput{Name: "foo"},
			executeOptions: []PromptRequestOption{
				WithInput(HelloPromptInput{Name: "foo"}),
			},
			wantTextOutput: "Echo: system: say hello; your name is foo; my name is foo; config: {\n  \"temperature\": 11\n}; context: null",
			wantGenerated: &ModelRequest{
				Config: &GenerationCommonConfig{
					Temperature: 11,
				},
				Output:     &ModelRequestOutput{},
				ToolChoice: "required",
				Messages: []*Message{
					{
						Role:    RoleSystem,
						Content: []*Part{NewTextPart("say hello")},
					},
					{
						Role:    RoleModel,
						Content: []*Part{NewTextPart("your name is foo")},
					},
					{
						Role:    RoleUser,
						Content: []*Part{NewTextPart("my name is foo")},
					},
				},
			},
		},
		{
			name:       "prompt with tools",
			model:      promptModel,
			config:     &GenerationCommonConfig{Temperature: 11},
			inputType:  HelloPromptInput{},
			systemText: "say hello",
			promptText: "my name is foo",
			tools:      []Tool{testTool("testTool")},
			input:      HelloPromptInput{Name: "foo"},
			executeOptions: []PromptRequestOption{
				WithInput(HelloPromptInput{Name: "foo"}),
			},
			wantTextOutput: "Echo: system: tool: say hello; my name is foo; ; Bar; ; config: {\n  \"temperature\": 11\n}; context: null",
			wantGenerated: &ModelRequest{
				Config: &GenerationCommonConfig{
					Temperature: 11,
				},
				Output:     &ModelRequestOutput{},
				ToolChoice: "required",
				Messages: []*Message{
					{
						Role:    RoleSystem,
						Content: []*Part{NewTextPart("say hello")},
					},
					{
						Role:    RoleUser,
						Content: []*Part{NewTextPart("my name is foo")},
					},
					{
						Role:    RoleModel,
						Content: []*Part{NewToolRequestPart(&ToolRequest{Name: "testTool", Input: map[string]any{"Test": "Bar"}})},
					},
					{
						Role:    RoleTool,
						Content: []*Part{NewToolResponsePart(&ToolResponse{Output: "Bar"})},
					},
				},
				Tools: []*ToolDefinition{
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

	cmpPart := func(a, b *Part) bool {
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
			opts = append(opts, WithModel(test.model))
			opts = append(opts, WithConfig(test.config))
			opts = append(opts, WithToolChoice(ToolChoiceRequired))
			opts = append(opts, WithTools(test.tools...))
			opts = append(opts, WithMaxTurns(1))

			if test.messages != nil {
				opts = append(opts, WithMessages(test.messages...))
			} else {
				opts = append(opts, WithMessagesFn(test.messagesFn))
			}

			p, err := DefinePrompt(
				r,
				"prompts",
				test.name,
				opts...,
			)
			if err != nil {
				t.Fatal(err)
			}

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

func testGenerate(ctx context.Context, req *ModelRequest, cb func(context.Context, *ModelResponseChunk) error) (*ModelResponse, error) {
	input := req.Messages[0].Content[0].Text
	output := fmt.Sprintf("AI reply to %q", input)

	if req.Output.Format == "json" {
		output = `{"text": "AI reply to JSON"}`
	}

	if cb != nil {
		cb(ctx, &ModelResponseChunk{
			Content: []*Part{NewTextPart("stream!")},
		})
	}

	r := &ModelResponse{
		Message: &Message{
			Content: []*Part{
				NewTextPart(output),
			},
		},
		Request: req,
	}
	return r, nil
}

func TestOptionsPatternExecute(t *testing.T) {
	testModel := DefineModel(r, "options", "test", nil, testGenerate)

	t.Run("Streaming", func(t *testing.T) {
		p, err := DefinePrompt(r, "TestExecute", "TestExecute", WithInputType(InputOutput{}), WithPromptText("TestExecute"))
		if err != nil {
			t.Fatal(err)
		}

		streamText := ""
		resp, err := p.Execute(
			context.Background(),
			WithInput(InputOutput{
				Text: "TestExecute",
			}),
			WithStreaming(func(ctx context.Context, grc *ModelResponseChunk) error {
				streamText += grc.Text()
				return nil
			}),
			WithModel(testModel),
			WithContext(&Document{Content: []*Part{NewTextPart("Banana")}}),
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
		p, err := DefinePrompt(r, "TestModelname", "TestModelname", WithInputType(InputOutput{}), WithPromptText("TestModelname"))
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

func TestDefaultsOverride(t *testing.T) {
	msgsFn := func(ctx context.Context, input any) ([]*Message, error) {
		return []*Message{
			{
				Role:    RoleUser,
				Content: []*Part{NewTextPart("you're history")},
			}}, nil
	}

	var tests = []struct {
		name           string
		define         []PromptOption
		execute        []PromptRequestOption
		wantTextOutput string
		wantGenerated  *ModelRequest
	}{
		{
			name: "Messages",
			define: []PromptOption{
				WithPromptText("my name is default"),
				WithMessages(&Message{
					Role:    RoleUser,
					Content: []*Part{NewTextPart("you're default")},
				}),
				WithModel(promptModel),
			},
			execute: []PromptRequestOption{
				WithConfig(&GenerationCommonConfig{Temperature: 12}),
				WithMessages(NewUserTextMessage("you're history")),
			},
			wantTextOutput: "Echo: you're history; my name is default; config: {\n  \"temperature\": 12\n}; context: null",
			wantGenerated: &ModelRequest{
				Config: &GenerationCommonConfig{
					Temperature: 12,
				},
				Output: &ModelRequestOutput{},
				Messages: []*Message{
					NewUserTextMessage("you're history"),
					NewUserTextMessage("my name is default"),
				},
			},
		},
		{
			name: "MessagesFn",
			define: []PromptOption{
				WithPromptText("my name is default"),
				WithMessages(&Message{
					Role:    RoleUser,
					Content: []*Part{NewTextPart("you're default")},
				}),
				WithModel(promptModel),
			},
			execute: []PromptRequestOption{
				WithConfig(&GenerationCommonConfig{Temperature: 12}),
				WithMessagesFn(msgsFn),
			},
			wantTextOutput: "Echo: you're history; my name is default; config: {\n  \"temperature\": 12\n}; context: null",
			wantGenerated: &ModelRequest{
				Config: &GenerationCommonConfig{
					Temperature: 12,
				},
				Output: &ModelRequestOutput{},
				Messages: []*Message{
					{
						Role:    RoleUser,
						Content: []*Part{NewTextPart("you're history")},
					},
					{
						Role:    RoleUser,
						Content: []*Part{NewTextPart("my name is default")},
					},
				},
			},
		},
		{
			name: "Config",
			define: []PromptOption{
				WithPromptText("my name is foo"),
				WithConfig(&GenerationCommonConfig{Temperature: 11}),
				WithModel(promptModel),
			},
			execute: []PromptRequestOption{
				WithConfig(&GenerationCommonConfig{Temperature: 12}),
			},
			wantTextOutput: "Echo: my name is foo; config: {\n  \"temperature\": 12\n}; context: null",
			wantGenerated: &ModelRequest{
				Config: &GenerationCommonConfig{
					Temperature: 12,
				},
				Output: &ModelRequestOutput{},
				Messages: []*Message{
					{
						Role:    RoleUser,
						Content: []*Part{NewTextPart("my name is foo")},
					},
				},
			},
		},
		{
			name: "Model",
			define: []PromptOption{
				WithPromptText("my name is foo"),
				WithModel(promptModel),
			},
			execute: []PromptRequestOption{
				WithConfig(&GenerationCommonConfig{Temperature: 12}),
				WithModel(testModel),
			},
			wantTextOutput: "AI reply to \"my name is foo\"",
			wantGenerated: &ModelRequest{
				Config: &GenerationCommonConfig{
					Temperature: 12,
				},
				Output: &ModelRequestOutput{},
				Messages: []*Message{
					{
						Role:    RoleUser,
						Content: []*Part{NewTextPart("my name is foo")},
					},
				},
			},
		},
		{
			name: "ModelName",
			define: []PromptOption{
				WithPromptText("my name is foo"),
				WithModelName("test/chat"),
			},
			execute: []PromptRequestOption{
				WithConfig(&GenerationCommonConfig{Temperature: 12}),
				WithModelName("defineoptions/test"),
			},
			wantTextOutput: "AI reply to \"my name is foo\"",
			wantGenerated: &ModelRequest{
				Config: &GenerationCommonConfig{
					Temperature: 12,
				},
				Output: &ModelRequestOutput{},
				Messages: []*Message{
					{
						Role:    RoleUser,
						Content: []*Part{NewTextPart("my name is foo")},
					},
				},
			},
		},
	}

	cmpPart := func(a, b *Part) bool {
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
			p, err := DefinePrompt(
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

func assertResponse(t *testing.T, resp *ModelResponse, want string) {
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
