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

	"github.com/aymerick/raymond"
	"github.com/firebase/genkit/go/internal/base"
	"github.com/firebase/genkit/go/internal/registry"
	"github.com/google/go-cmp/cmp"
	"github.com/google/go-cmp/cmp/cmpopts"
)

type InputOutput struct {
	Text string `json:"text"`
}

func testTool(reg *registry.Registry, name string) *ToolDef[struct{ Test string }, string] {
	return DefineTool(reg, name, "use when need to execute a test",
		func(ctx *ToolContext, input struct {
			Test string
		}) (string, error) {
			return input.Test, nil
		},
	)
}

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
					r, "aModel",
					WithInputType(InputOutput{Text: "test"}),
					WithOutputFormat(test.format),
				)
			} else {
				_, err = DefinePrompt(
					r, "bModel",
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
	reg, err := registry.New()
	if err != nil {
		t.Fatal(err)
	}

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
			name:         "structInput",
			templateText: "hello {{name}}",
			inputType:    hello{},
			input:        map[string]any{"name": "world"},
			render:       "hello world",
		},
		{
			name:         "mapInput",
			templateText: "hello {{name}}",
			inputType:    map[string]any{"name": "world"},
			input:        map[string]any{"name": "world"},
			render:       "hello world",
		},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			var err error
			var p *Prompt

			if test.inputType != nil {
				p, err = DefinePrompt(reg, test.name,
					WithPromptText(test.templateText),
					WithInputType(test.inputType),
				)
			} else {
				p, err = DefinePrompt(reg, test.name, WithPromptText(test.templateText))
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

func definePromptModel(reg *registry.Registry) Model {
	return DefineModel(reg, "test", "chat",
		&ModelInfo{Supports: &ModelSupports{
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
			textResponse += "; context: " + base.PrettyJSONString(gr.Docs)

			return &ModelResponse{
				Request: gr,
				Message: NewModelTextMessage(fmt.Sprintf("Echo: %s", textResponse)),
			}, nil
		})
}

func TestValidPrompt(t *testing.T) {
	reg, err := registry.New()
	if err != nil {
		t.Fatal(err)
	}

	model := definePromptModel(reg)
	tool := testTool(reg, "testTool")

	var tests = []struct {
		name           string
		model          Model
		config         *GenerationCommonConfig
		inputType      any
		systemText     string
		promptText     string
		tools          []ToolRef
		input          any
		executeOptions []PromptGenerateOption
		wantGenerated  *ModelRequest
		wantErr        bool
	}{
		{
			name:       "prompt with tools",
			model:      model,
			config:     &GenerationCommonConfig{Temperature: 11},
			inputType:  HelloPromptInput{},
			systemText: "say hello",
			promptText: "my name is foo",
			tools:      []ToolRef{ToolName(tool.Name())},
			input:      HelloPromptInput{Name: "foo"},
			executeOptions: []PromptGenerateOption{
				WithToolChoice(ToolChoiceRequired),
			},
			wantGenerated: &ModelRequest{
				Config: &GenerationCommonConfig{
					Temperature: 11,
				},
				Output:     &ModelOutputConfig{},
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
				Tools: []*ToolDefinition{tool.Definition()},
			},
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			var opts []PromptOption
			opts = append(opts, WithInputType(test.inputType))
			opts = append(opts, WithModel(test.model))
			opts = append(opts, WithConfig(test.config))
			opts = append(opts, WithToolChoice(ToolChoiceRequired))
			opts = append(opts, WithTools(test.tools...))
			opts = append(opts, WithSystemText(test.systemText))
			opts = append(opts, WithPromptText(test.promptText))

			p, err := DefinePrompt(reg, test.name, opts...)
			if err != nil {
				t.Fatal(err)
			}

			generated, err := p.Execute(context.Background(), test.executeOptions...)
			if (err != nil) != test.wantErr {
				t.Fatalf("Generate() error = %v, wantErr %v", err, test.wantErr)
			}

			if diff := cmp.Diff(test.wantGenerated, generated.Request, cmpopts.IgnoreUnexported(ModelRequest{})); diff != "" {
				t.Errorf("Generate() mismatch (-want +got):\n%s", diff)
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
	reg, err := registry.New()
	if err != nil {
		t.Fatal(err)
	}

	testModel := DefineModel(reg, "options", "test", nil, testGenerate)

	t.Run("Streaming", func(t *testing.T) {
		p, err := DefinePrompt(reg, "TestExecute", WithInputType(InputOutput{}), WithPromptText("TestExecute"))
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
			WithDocs(&Document{Content: []*Part{NewTextPart("Banana")}}),
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
		p, err := DefinePrompt(reg, "TestModelname", WithInputType(InputOutput{}), WithPromptText("TestModelname"))
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
	reg, err := registry.New()
	if err != nil {
		t.Fatal(err)
	}

	testModel := DefineModel(reg, "defineoptions", "test", nil, testGenerate)
	model := definePromptModel(reg)

	var tests = []struct {
		name           string
		define         []PromptOption
		execute        []PromptGenerateOption
		wantTextOutput string
		wantGenerated  *ModelRequest
	}{
		{
			name: "Config",
			define: []PromptOption{
				WithPromptText("my name is foo"),
				WithConfig(&GenerationCommonConfig{Temperature: 11}),
				WithModel(model),
			},
			execute: []PromptGenerateOption{
				WithConfig(&GenerationCommonConfig{Temperature: 12}),
			},
			wantTextOutput: "Echo: my name is foo; config: {\n  \"temperature\": 12\n}; context: null",
			wantGenerated: &ModelRequest{
				Config: &GenerationCommonConfig{
					Temperature: 12,
				},
				Output: &ModelOutputConfig{},
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
				WithModel(model),
			},
			execute: []PromptGenerateOption{
				WithConfig(&GenerationCommonConfig{Temperature: 12}),
				WithModel(testModel),
			},
			wantTextOutput: "AI reply to \"my name is foo\"",
			wantGenerated: &ModelRequest{
				Config: &GenerationCommonConfig{
					Temperature: 12,
				},
				Output: &ModelOutputConfig{},
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
			execute: []PromptGenerateOption{
				WithConfig(&GenerationCommonConfig{Temperature: 12}),
				WithModelName("defineoptions/test"),
			},
			wantTextOutput: "AI reply to \"my name is foo\"",
			wantGenerated: &ModelRequest{
				Config: &GenerationCommonConfig{
					Temperature: 12,
				},
				Output: &ModelOutputConfig{},
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
			p, err := DefinePrompt(reg, test.name, test.define...)
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

			if diff := cmp.Diff(test.wantGenerated, output.Request, cmp.Comparer(cmpPart), cmpopts.EquateEmpty()); diff != "" {
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

func TestDefinePartialAndHelperJourney(t *testing.T) {
	// Initialize a registry
	r, err := registry.New()
	if err != nil {
		t.Fatal(err)
	}

	// Register default template helpers (json, role, media)
	tpl, err := raymond.Parse("")
	if err != nil {
		t.Fatal(err)
	}
	r.Dotprompt.RegisterHelpers(nil, tpl)

	// Step 1: Define custom partials for reuse across multiple prompts
	// A header partial for consistent headers
	headerPartial := `# {{title}}
Author: {{author}}
Date: {{date}}`
	definePartial(r, "header", headerPartial)

	// A section partial for document structure
	sectionPartial := `
## {{sectionTitle}}
{{content}}`
	definePartial(r, "section", sectionPartial)

	// A footer partial for consistent footers
	footerPartial := `
---
© {{year}} - Generated with Genkit`
	definePartial(r, "footer", footerPartial)

	// Step 2: Define custom helpers to extend templating capabilities
	// A helper to capitalize text
	defineHelper(r, "capitalize", func(text string) raymond.SafeString {
		if text == "" {
			return raymond.SafeString("")
		}
		return raymond.SafeString(strings.ToUpper(text[:1]) + text[1:])
	})

	// A helper to create list items
	defineHelper(r, "listItem", func(content string) raymond.SafeString {
		return raymond.SafeString("* " + content)
	})

	// Step 3: Create a template that uses both partials and helpers
	mainTemplate := `{{> header}}

{{> section sectionTitle="Introduction" content="This is a demonstration of using partials and helpers in Genkit."}}

{{> section sectionTitle="Features" content="Key features include:"}}
{{listItem "Reusable partials for consistent styling"}}
{{listItem "Custom helpers for formatting"}}
{{listItem "The capitalize helper transforms text: Hello"}}

{{> footer}}`

	// Step 4: Parse and execute the template
	tpl, err = raymond.Parse(mainTemplate)
	if err != nil {
		t.Fatalf("Failed to parse template: %v", err)
	}

	// Register the same partials with the test template
	tpl.RegisterPartial("header", headerPartial)
	tpl.RegisterPartial("section", sectionPartial)
	tpl.RegisterPartial("footer", footerPartial)

	// Register the same helpers with the test template
	tpl.RegisterHelper("capitalize", func(text string) raymond.SafeString {
		if text == "" {
			return raymond.SafeString("")
		}
		return raymond.SafeString(strings.ToUpper(text[:1]) + text[1:])
	})
	tpl.RegisterHelper("listItem", func(content string) raymond.SafeString {
		return raymond.SafeString("* " + content)
	})

	// Execute the template with data
	data := map[string]any{
		"title":  "Using Partials and Helpers",
		"author": "Genkit Team",
		"date":   "2024-03-28",
		"year":   "2024",
	}

	result, err := tpl.Exec(data)
	if err != nil {
		t.Fatalf("Failed to execute template: %v", err)
	}

	// Log the actual output for debugging
	t.Logf("Actual template output:\n%s", result)

	// Verify the output includes content from partials and helpers
	expectedContent := []string{
		"# Using Partials and Helpers",
		"Author: Genkit Team",
		"Date: 2024-03-28",
		"## Introduction",
		"This is a demonstration of using partials and helpers in Genkit.",
		"## Features",
		"Key features include:",
		"* Reusable partials for consistent styling",
		"* Custom helpers for formatting",
		"* The capitalize helper transforms text: Hello",
		"© 2024 - Generated with Genkit",
	}

	for _, content := range expectedContent {
		if !strings.Contains(result, content) {
			t.Errorf("Expected content '%s' not found in result", content)
		}
	}

	t.Log("Successfully demonstrated definePartial and defineHelper usage")
}
