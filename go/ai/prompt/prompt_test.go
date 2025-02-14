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
	"testing"

	"github.com/firebase/genkit/go/ai"
	"github.com/firebase/genkit/go/internal/registry"
)

type InputOutput struct {
	Text string `json:"text"`
}

var r, _ = registry.New()

func testTool(name string) *ai.ToolDef[struct{ Test string }, string] {
	return ai.DefineTool(r, name, "use when need to execute a test",
		func(ctx *ai.ToolContext, input struct {
			Test string
		}) (string, error) {
			return input.Test, nil
		},
	)
}

var testModel = ai.DefineModel(r, "defineoptions", "test", nil, testGenerate)

func TestOptionsPatternDefine(t *testing.T) {
	t.Run("WithTypesAndModel", func(t *testing.T) {
		dotPrompt, err := Define(
			r,
			"TestTypes",
			"TestTypes",
			WithTools(testTool("testOptionsPatternDefine")),
			WithDefaultConfig(&ai.GenerationCommonConfig{}),
			WithInputType(InputOutput{}),
			WithOutputType(InputOutput{}),
			WithMetadata(map[string]any{"test": "test"}),
			WithDefaultModel(testModel),
		)
		if err != nil {
			t.Fatal(err)
		}

		if dotPrompt.Tools == nil {
			t.Error("tools not set")
		}
		if dotPrompt.Config.GenerationConfig == nil {
			t.Error("generationConfig not set")
		}
		if dotPrompt.Config.InputSchema == nil {
			t.Error("inputschema not set")
		}
		if dotPrompt.Config.OutputSchema == nil {
			t.Error("outputschema not set")
		}
		if dotPrompt.Config.OutputFormat == "" {
			t.Error("outputschema not set")
		}
		if dotPrompt.Config.DefaultInput == nil {
			t.Error("default input not set")
		}
		if dotPrompt.Config.Metadata == nil {
			t.Error("metadata not set")
		}
		if dotPrompt.Config.Model == nil {
			t.Error("model not set")
		}
	})

	t.Run("WithDefaultMap", func(t *testing.T) {
		dotPrompt, err := Define(
			r,
			"TestDefaultMap",
			"TestDefaultMap",
			WithInputType(map[string]any{"test": "test"}),
		)
		if err != nil {
			t.Fatal(err)
		}
		if dotPrompt.Config.InputSchema == nil {
			t.Error("inputschema not set")
		}
		if dotPrompt.Config.DefaultInput == nil {
			t.Error("Input default not set")
		}
		if dotPrompt.Config.DefaultInput["test"] != "test" {
			t.Error("Input default incorrect")
		}
	})

	t.Run("WithDefaultStruct", func(t *testing.T) {
		dotPrompt, err := Define(
			r,
			"TestDefaultStruct",
			"TestDefaultStruct",
			WithInputType(InputOutput{Text: "test"}),
		)
		if err != nil {
			t.Fatal(err)
		}
		if dotPrompt.Config.InputSchema == nil {
			t.Error("inputschema not set")
		}
		if dotPrompt.Config.DefaultInput == nil {
			t.Error("Input default not set")
		}
		if dotPrompt.Config.DefaultInput["text"] != "test" {
			t.Error("Input default incorrect")
		}
	})
}

func TestOutputFormat(t *testing.T) {
	var tests = []struct {
		name   string
		output any
		format ai.OutputFormat
		err    bool
	}{
		{
			name:   "mismatch",
			output: InputOutput{},
			format: ai.OutputFormatText,
			err:    true,
		},
		{
			name:   "json",
			output: InputOutput{},
			format: ai.OutputFormatJSON,
			err:    false,
		},
		{
			name:   "text",
			format: ai.OutputFormatText,
			err:    false,
		},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			var err error

			if test.output == nil {
				_, err = Define(
					r,
					"aModel",
					"aModel",
					WithInputType(InputOutput{Text: "test"}),
					WithOutputFormat(test.format),
				)
			} else {
				_, err = Define(
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
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			var err error
			var p *Prompt

			if test.inputType != nil {
				p, err = Define(
					r,
					"provider",
					test.name,
					WithDefaultPrompt(test.templateText),
					WithInputType(test.inputType),
				)
			} else {
				p, err = Define(
					r,
					"provider",
					"inputFormat",
					WithDefaultPrompt(test.templateText),
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

func TestPromptOptions(t *testing.T) {
	var tests = []struct {
		name string
		with PromptOption
	}{
		{
			name: "WithTools",
			with: WithTools(testTool("testPromptOptions")),
		},
		{
			name: "WithDefaultConfig",
			with: WithDefaultConfig(&ai.GenerationCommonConfig{}),
		},
		{
			name: "WithInputType",
			with: WithInputType(InputOutput{}),
		},
		{
			name: "WithOutputType",
			with: WithOutputType(InputOutput{}),
		},
		{
			name: "WithOutputFormat",
			with: WithOutputFormat(ai.OutputFormatJSON),
		},
		{
			name: "WithMetadata",
			with: WithMetadata(map[string]any{"test": "test"}),
		},
		{
			name: "WithDefaultModelName",
			with: WithDefaultModelName("defineoptions/test"),
		},
		{
			name: "WithDefaultModel",
			with: WithDefaultModel(testModel),
		},
		{
			name: "WithDefaultSystemText",
			with: WithDefaultSystemText("say hello"),
		},
		{
			name: "WithDefaultPrompt",
			with: WithDefaultPrompt("default prompt"),
		},
		{
			name: "WithDefaultMessages",
			with: WithDefaultMessages(
				[]*ai.Message{{
					Role:    ai.RoleSystem,
					Content: []*ai.Part{ai.NewTextPart("say hello")},
				}},
			),
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			_, err := Define(
				r,
				"TestWith",
				"TestWith",
				test.with,
				test.with,
			)

			if err == nil {
				t.Errorf("%s could be set twice", test.name)
			}
		})
	}
}
